

import json

import lx
import modo

from . import const as c
from .item_feature import ItemFeature
from .item_feature_settings import ItemFeatureSettings
from .item import Item
from .item_cache import ItemCache
from .core import service


class ItemFeatureOperator(object):
    """ Used to manage features on a rig item.

    Parameters
    ----------
    item : Item, modo.Item, lx.object.Item, str
    """

    def startBatchMode(self):
        """ Starts batch mode.
        
        If you want to affect multiple item features on a single item
        use batch mode. Batch mode makes sure all necessary changes and
        events are sent out when endBatchMode() is called.
        """
        self._batchMode = True
    
    def endBatchMode(self):
        """ Ends batch mode.
        """
        self._batchMode = False
        self._item.renderAndSetName()
        service.events.send(c.EventTypes.ITEM_CHANGED, item=self.modoItem)

    @property
    def item(self):
        return self._item

    @property
    def modoItem(self):
        return self._item.modoItem

    def addFeature(self, identifier):
        """ Adds feature to the item.

        If item feature has a list of packages defined these packages
        will be added to the item automatically so inheriting class
        doesn't need to do that in the onAdd() method.

        Parameters
        ----------
        identifier : str
            Identifier of the feature to be added, as registered with the system.

        Returns
        -------
        ItemFeature
            ItemFeature interface of the feature that was added.
            
        Raises
        ------
        LookupError
            When feature with given identifier cannot be found.
        """
        try:
            featureClass = service.systemComponent.get(c.SystemComponentType.ITEM_FEATURE, identifier)
        except LookupError:
            raise

        featureObj = self._installFeature(featureClass)
        
        try:
            featureObj.onAdd()
        except AttributeError:
            pass

        if not self._batchMode:
            self._item.renderAndSetName()
            service.events.send(c.EventTypes.ITEM_CHANGED, item=self.modoItem)

        return featureObj

    def removeFeature(self, identifier):
        """ Removes feature from an item.
        
        Parameters
        ----------
        identifier : ItemFeature, str
            Identifier of the feature to be removed, as registered with the system.
    
        Returns
        -------
        Boolean 
            True if feature was successfully removed.
            
        Raises
        ------
        LookupError
            If feature cannot be found.
        """
        if isinstance(identifier, str):
            try:
                featureClass = service.systemComponent.get(c.SystemComponentType.ITEM_FEATURE, identifier)
            except LookupError:
                raise
       
            try:
                featureObj = featureClass(self._item)
            except TypeError:
                raise LookupError
        else:
            featureObj = identifier

        # Call on remove first - in case it depends on the feature still being valid
        try:
            featureObj.onRemove()
        except AttributeError:
            pass

        self._uninstallFeature(featureObj)
        
        if not self._batchMode:
            self._item.renderAndSetName()
            service.events.send(c.EventTypes.ITEM_CHANGED, item=self.modoItem)
    
        return True

    def hasFeature(self, identifier):
        """ Tests whether given feature is added to an item.
        
        Parameters
        ----------
        identifier : str
            Identifier of a feature to be tested (as registered with the system)

        Returns
        -------
        Boolean
            True if feature is present on an item, False otherwise.
        """
        return identifier in self._settings.featureIdentifiers

    def getFeature(self, identifier):
        """ Returns feature with a given ident.
        
        Returns
        -------
        ItemFeature

        Raises
        ------
        LookupError
            If feature cannot be found or item does not have this feature.
        """
        try:
            featureClass = service.systemComponent.get(c.SystemComponentType.ITEM_FEATURE, identifier)
        except LookupError:
            raise 

        try:
            featureObj = featureClass(self._item)
        except TypeError:
            raise LookupError
        return featureObj

    @property
    def allFeatures(self):
        """ Gets list of all features on the item.
        
        Returns
        -------
        list : ItemFeature.
        """
        featureIdents = self._settings.featureIdentifiers
        features = []
        for identifier in featureIdents:
            try:
                featureClass = service.systemComponent.get(c.SystemComponentType.ITEM_FEATURE, identifier)
            except LookupError:
                continue
            try:
                featureObj = featureClass(self._item)
            except TypeError:
                continue
            
            features.append(featureObj)
        
        return features

    def preStandardizeAllFeatures(self):
        """
        Call this right before standardization happens while there's still full rig context.
        """
        features = self.allFeatures
        for feature in features:
            try:
                feature.onStandardize()
            except AttributeError:
                pass

    def standardizeAllFeatures(self):
        """
        Standardizing removes features but first it backs up and recreates all links to rig.

        This is done to make sure that if there are any links from/to feature channels they won't
        be gone when item is standardized. Linked feature channels are recreated as user channels with the same name.
        """
        features = self.allFeatures
        cacheList = []
        for feature in features:

            cache = ItemCache()
            cache.cacheChannels(self.modoItem, feature.descPackages)
            cacheList.append(cache)

        self.removeAllFeatures(silent=True)

        for cache in cacheList:
            cache.restoreChannels(self.modoItem)

    def removeAllFeatures(self, silent=False):
        """ Removes all item features from an item.
        
        Parameters
        ----------
        silent : bool, optional
            When silent is true no notifications will be sent.
            This should be used only right before the item
            is standardized or removed from rig.
        """
        self.startBatchMode()
        features = self.allFeatures
        for f in features:
            self.removeFeature(f)
        if not silent:
            self.endBatchMode()
        
    # -------- Private methods

    def _installFeature(self, featureClass):
        # Feature already installed?
        if featureClass.descIdentifier in self._settings.featureIdentifiers:
            return featureClass(self._item)
        
        # Add Packages
        packages = featureClass.descPackages
        if packages is not None:
            if not isinstance(packages, list):
                packages = [packages]
            for package in packages:
                self._item.modoItem.internalItem.PackageAdd(package)
        
        self._settings.addFeatureIdent(featureClass.descIdentifier)

        return featureClass(self._item)
    
    def _uninstallFeature(self, featureObj):
        if featureObj.descIdentifier not in self._settings.featureIdentifiers:
            return False

        packages = featureObj.descPackages
        if packages is not None:
            if not isinstance(packages, list):
                packages = [packages]
            for package in packages:
                try:
                    self._item.modoItem.internalItem.PackageRemove(package)
                except LookupError:
                    pass

        self._settings.removeFeatureIdent(featureObj.descIdentifier)
        return True

    def __init__(self, item):
        try:
            rigItem = Item.getFromOther(item)
        except TypeError:
            raise
        self._item = rigItem
        self._settings = ItemFeatureSettings(self._item.modoItem)
        self._batchMode = False