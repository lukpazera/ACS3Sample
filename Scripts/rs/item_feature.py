

import json

import modox

from .item import Item
from .sys_component import SystemComponent
from .item_feature_settings import ItemFeatureSettings
from . import const as c


class ItemFeature(SystemComponent):
    """ Item Feature is functionality that can be attached to rig item.
       
    Features will be listed in rig properties form so user can add/remove
    them from a given item at will.
    
    Initialising item feature on an object that doesn't have
    this feature attached will throw TypeError exception.
    
    Parameters
    ----------
    item : Item, modo.Item
        Item that has the feature applied.

    Raises
    ------
    TypeError
        When trying to initialize feature on an item that doesn't
        have this feature.

    Attributes
    ----------
    descCategory : str
        Item features with the same category will show up bundled together in UI.
        Categories are predefined in c.ItemFeatureCategory.
        General category is assigned by default.
        
    descPackages : list
        Package or list of packages that feature is paired with.
        These packages will be automatically added to an item to install a feature
        and also removed when the feature is removed.
    
    descListed : bool
        When True the feature will be listed in rig properties, if available
        for a given item. When false - the feature is meant to be either added manually
        or placed somewhere else in the UI.

    descExclusiveItemType : Item, None
        When not None the feature will only show up on rig items of a given type.

    descExclusiveModoItemType : str, None
        When not None the feature will only show up on items of a given modo item type.
        
    Methods
    -------
    init()
        Gets called from item feature constructor.
        
    onAdd()
        Gets called when feature is added to an item.
        
    onRemove()
        Gets called when features is removed from an item.
    
    onSelected()
        Gets called when item the feature is based on is selected in viewport.

    onStandardize()
        Gets called when item feature is standardized.

    Class methods
    -------------
    customTest(modoItem)
        If you want to limit feature to specific items or item types manually -
        implement this classmethod.
    """
    
    descIdentifier = ''
    descUsername = ''
    descCategory = c.ItemFeatureCategory.GENERAL
    descPackages = []
    descListed = True
    descExclusiveItemType = None
    descExclusiveModoItemType = None
    
    # -------- System Component
    
    @classmethod
    def sysType(cls):
        return c.SystemComponentType.ITEM_FEATURE
    
    @classmethod
    def sysIdentifier(cls):
        return cls.descIdentifier
    
    @classmethod
    def sysUsername(cls):
        return cls.descUsername + ' Item Feature'

    # -------- Public class methods
    
    @classmethod
    def test(cls, modoItem):
        """ Tests whether the feature is applicable to a given item.
        
        Exclusive item types are checked first, then custom test is performed (if any).
        If either rig or modo exclusive item type is set and custom test is present all need to
        evaluate to True for the item to pass the test.
        
        Parameters
        ----------
        modoItem : modo.Item
        
        Returns
        -------
        bool
            When feature is not exclusive to any rig item type and customTest()
            is not implemented the test will return True.
        """
        if cls.descExclusiveItemType is not None:
            if Item.getTypeFromModoItem(modoItem) != cls.descExclusiveItemType:
                return False

        if cls.descExclusiveModoItemType is not None:
            if modoItem.type != cls.descExclusiveModoItemType:
                return False
                
        try:
            customTest = cls.customTest(modoItem)
        except AttributeError:
            customTest = True
        
        return customTest

    @classmethod
    def isAddedToItemFast(cls, rawItem):
        """ Tests if feature is added to a raw item.
        
        Parameters
        ----------
        rawItem : lx.object.Item
        
        Returns
        -------
        bool
        """
        return ItemFeatureSettings.isFeatureAddedFast(cls.descIdentifier, rawItem)

    # -------- Public methods

    @property
    def item(self):
        """ Gets rig item the item feature is added to.
        """
        return self._item

    @property
    def modoItem(self):
        return self._item.modoItem

    # -------- Private methods

    def __init__(self, item):
        try:
            rigItem = Item.getFromOther(item)
        except TypeError:
            raise
        
        self._item = rigItem
        self._settings = ItemFeatureSettings(self._item.modoItem)
        if not self.descIdentifier in self._settings.featureIdentifiers:
            raise TypeError
        
        try:
            self.init()
        except AttributeError:
            pass

    def __eq__(self, other):
        return self.item == other.item


class LocatorSuperTypeItemFeature(ItemFeature):
    """ Variant of item feature that should be available on locator supertype items only.
    """
    
    @classmethod
    def customTest(cls, modoItem):
        xitem = modox.Item(modoItem.internalItem)
        return xitem.isOfXfrmCoreSuperType