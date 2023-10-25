
""" Scene object module.

    Scene object provides access to rigs in a given modo scene.
    
    Copyright (C) 2017-2019 Lukasz Pazera.
"""


import lx
import lxu.select
import modo
import modox

from .core import service as service
from .log import log as log
from .items.root_item import RootItem
from . import context_op
from . import rig
from . import item
from . import item_settings
from . import const as c


class Scene(object):
    """ Gives access to rigs in the scene.

    Parameters
    ----------
    sceneItem : modo.Scene, lx.object.Scene, lxu.object.Scene, optional 
        If not provided current scene will be used.

    Raises
    ------
    TypeError
        If passed sceneItem is of incorrect type.
    """

    GRAPH_EDIT_RIG = c.Graph.EDIT_RIG

    _SETTING_ACCESS_LEVEL = 'alev'
    _DEFAULT_ACCESS_LEVEL = c.AccessLevel.EDIT
    _sceneService = lx.service.Scene()
    _RIG_ROOT_ITEM_INT_CODE = _sceneService.ItemTypeLookup(RootItem.descModoItemType)
    _SCENE_ITEM_INT_CODE = _sceneService.ItemTypeLookup(lx.symbol.sITYPE_SCENE)
    
    # -------- Class methods
    
    @classmethod
    def getAccessLevelFast(cls):
        rawScene = lxu.select.SceneSelection().current()
        rawSceneItem = lx.object.Item(rawScene.AnyItemOfType(cls._SCENE_ITEM_INT_CODE))
        return item_settings.ItemSettings(modo.Item(rawSceneItem)).get(cls._SETTING_ACCESS_LEVEL, cls._DEFAULT_ACCESS_LEVEL)

    @classmethod
    def anyRigsInSceneFast(cls):
        """ Tests whether there are any rigs in current scene.
        
        This is performance optimised, use it whenever you do not need
        particular Scene object for anything else!
        
        Returns
        -------
        bool
        """
        rawScene = lxu.select.SceneSelection().current()
        return rawScene.ItemCount(cls._RIG_ROOT_ITEM_INT_CODE) > 0
    
    @classmethod
    def getEditRigRootItemFast(cls):
        """ Gets current edit rig item fast.
        
        This is performance optimised, use it whenever you do not need
        particular Scene object for anything else!
        
        Returns
        -------
        RootItem, None
        """
        rawScene = lxu.select.SceneSelection().current()
        rawSceneItem = lx.object.Item(rawScene.AnyItemOfType(cls._SCENE_ITEM_INT_CODE))
        graph = lx.object.ItemGraph(rawScene.GraphLookup(cls.GRAPH_EDIT_RIG))
        linkCount = graph.FwdCount(rawSceneItem)
        if linkCount <= 0:
            return None

        rootModoItem = graph.FwdByIndex(rawSceneItem, 0)
        try:
            return RootItem(rootModoItem)
        except TypeError:
            pass
        return None
    
    @classmethod
    def getRigRootModoItemsFast(cls):
        """ Gets all rig root items as raw item objects fast.
        
        Returns
        -------
        list : lx.object.Item
        """
        rawScene = lxu.select.SceneSelection().current()
        rootsCount = rawScene.ItemCount(cls._RIG_ROOT_ITEM_INT_CODE)
        roots = []
        for x in range(rootsCount):
            roots.append(lx.object.Item(rawScene.ItemByIndex(cls._RIG_ROOT_ITEM_INT_CODE, x)))
        return roots

    @classmethod
    def getRigRootItemsFast(cls):
        """ Gets all rig root items as RootItem objects fast.
    
        Returns
        -------
        list : RootItem
        """
        roots = cls.getRigRootModoItemsFast()
        rootItems = []
        for rootRaw in roots:
            rootItems.append(RootItem(rootRaw))
        return rootItems

    @classmethod
    def getSelectedRootItemsFast(cls):
        """
        Gets root items for selected rigs fast.

        Returns
        -------
        list : RootItem
        """
        roots = cls.getRigRootItemsFast()
        selectedRootItems = []
        for rootItem in roots:
            if rootItem.selected:
                selectedRootItems.append(rootItem)
        if selectedRootItems:
            return selectedRootItems
        return roots

    @classmethod
    def getRigRootItemSelectionFast(cls):
        """ Gets selected rig root items fast.
        
        These are not roots selected within rigging system but ones selected
        as modo item selection.
        
        Returns
        -------
        list : RootItem
        """
        roots = []
        items = lxu.select.ItemSelection().current()
        rootModoTypeCode = lx.service.Scene().ItemTypeLookup(RootItem.descModoItemType)
        for item in items:
            if item.Type() == rootModoTypeCode:
                try:
                    roots.append(RootItem(item))
                except TypeError:
                    continue
        return roots

    @classmethod
    def getFirstRigRootItemSelectionFast(cls):
        """ Gets first rig root item from MODO item selection.

        Returns
        -------
        RootItem, None
        """
        items = lxu.select.ItemSelection().current()
        rootModoTypeCode = lx.service.Scene().ItemTypeLookup(RootItem.descModoItemType)
        for item in items:
            if item.Type() == rootModoTypeCode:
                try:
                    return RootItem(item)
                except TypeError:
                    continue
        return None

    @classmethod
    def getCurrentContextIdentifierFast(cls):
        """
        Gets current context identifier fast.

        Returns
        -------
        str
        """
        return context_op.ContextOperator.getContextIdentFast()

    @classmethod
    def getCurrentContextFast(cls):
        """
        Gets current context object fast.

        Returns
        -------
        Context
        """
        ident = cls.getCurrentContextIdentifierFast()
        return service.systemComponent.get(c.SystemComponentType.CONTEXT, ident)

    # -------- Public methods and properties
        
    def scan(self):
        self._scan()

    @property
    def hasAnyRigs(self):
        """ Test whether there are any rigs in the scene.
        
        Note that this is slower version and should be used only when you
        already have scene object for something.
        
        Returns
        -------
        bool
            True when there's at least one rig in the scene, false otherwise.
        """
        return self._scene.itemCount(RootItem.descModoItemType) > 0

    @property
    def rigsCount(self):
        """ Gets number of rigs in the scene.
        
        Returns
        -------
        int
            Number of rigs in the scene.
        """
        return self._scene.itemCount(RootItem.descModoItemType)

    @property
    def rigs (self):
        """ Gets a list of rigs in scene.
        
        Returns
        -------
        list of Rig
             Returns a list of rigs in scene.
        """
        return self._getRigs()

    @property
    def accessLevel(self):
        return self.settings.get(self._SETTING_ACCESS_LEVEL, defaultValue=self._DEFAULT_ACCESS_LEVEL)
    
    @accessLevel.setter
    def accessLevel(self, level):
        self.settings.set(self._SETTING_ACCESS_LEVEL, level)

    @property
    def firstRig(self):
        """
        Gets first rig in the scene.

        Returns
        -------
        Rig, None
        """
        try:
            return self.getRigByIndex(0)
        except LookupError:
            pass
        return None

    @property
    def editRig(self):
        """ Gets a rig currently selected for editing.

        Returns
        -------
        Rig
            None when edit rig cannot be found.
        """
        graphSceneItem = self._scene.sceneItem.itemGraph(self.GRAPH_EDIT_RIG)
        connectedItems = graphSceneItem.forward()
        if not connectedItems or len(connectedItems) == 0:
            return self.firstRig

        try:
            editRig = rig.Rig(connectedItems[0])
        except TypeError:
            return self.firstRig
        return editRig

    @editRig.setter
    def editRig(self, editRig):
        """ Sets new rig for editing.
        
        Parameters
        ----------
        rig : Rig, str, RootItem, modoItem, None
            Rig to set as edit rig. Rig can be defined by Rig object directly 
            but it also can be RootItem or an ident string of modo item that is
            the root of the rig.
            Use None to clear edit rig link completely.
        """
        sceneItem = self._scene.sceneItem
        
        if editRig is None:
            modox.ItemUtils.clearForwardGraphConnections(sceneItem, self.GRAPH_EDIT_RIG)
            return
        elif not isinstance(editRig, rig.Rig):
            # In this case if argument was set to something but it was not
            # valid we want to not affect edit rig setting.
            try:
                editRig = rig.Rig(editRig)
            except TypeError:
                return

        # Don't do anything if new edit rig is the same as old one.
        try:
            currentEditRigRootModoItem = modox.ItemUtils.getForwardGraphConnections(sceneItem, self.GRAPH_EDIT_RIG)[0]
        except IndexError:
            pass
        else:
            if editRig == currentEditRigRootModoItem:
                return

        modox.ItemUtils.clearForwardGraphConnections(sceneItem, self.GRAPH_EDIT_RIG)
        rootItem = editRig.rootModoItem
        modox.ItemUtils.addForwardGraphConnections(sceneItem, [rootItem], self.GRAPH_EDIT_RIG)

        service.events.send(c.EventTypes.EDIT_RIG_CHANGED)

    def resetEditRig(self):
        """ Resets edit rig to first available rig or to None if there are no rigs in scene.
        """
        if len(self._rigs) > 0:
            self.editRig = self._rigs[0]
        else:
            self.editRig = None

    def newRig (self, name=None):
        """ Adds new rig to scene.
        
        Returns
        -------
        Rig
        """
        name = self._getUniqueRigName(name)
        newRig = rig.Rig.new(name)
        
        if newRig is not None:
            self._rigs.append(newRig)
            self.editRig = newRig

        return newRig
    
    @property
    def selectedRigs(self):
        """ Returns a list of rigs selected in scene.
        
        When no rigs are selected all rigs are considered to be selected.

        Returns
        -------
        list of Rig
        """
        selected = []
        for rig in self.rigs:
            if rig.selected:
                selected.append(rig)
        if selected:
            return selected
        return self.rigs

    @property
    def firstSelectedRig(self):
        """
        Returns first selected rig in scene.

        Returns
        -------
        Rig, None
            None is returned when there's no selected rig (more likely no rigs in scene).
        """
        for rig in self.rigs:
            if rig.selected:
                return rig
        if len(self.rigs) > 0:
            return self.rigs[0]
        return None

    @property
    def directlySelectedRigsCount(self):
        """ Gets number of directly selected rigs in scene.
        
        Returns
        -------
        int
        """
        count = 0
        for rig in self.rigs:
            if rig.selected:
                count += 1
        return count
    
    def getSelectedRigByIndex(self, index):
        """ Gets one of selected rigs by its index.
        
        Parameters
        ----------
        index : int
        
        Returns
        -------
        Rig
        
        Raises
        ------
        IndexError
        """
        selRigs = self.selectedRigs
        if not selRigs:
            raise IndexError
        
        if index >= len(selRigs):
            raise IndexError
        
        return selRigs[index]

    def standardizeRig(self, rigToStandardize):
        """ Standardizes chosen rig.
        
        Standardizing strips the rig from any custom items, packages, tags, etc.
        Standardized rig can be loaded in MODO with no rigging system installed.
        """
        rigToStandardize = self._getRigFromCompatibleObject(rigToStandardize)
        if rigToStandardize is None:
            return
        self.editRig = None

        rigToStandardize.standardize()
        self._scan()
        self.resetEditRig()
        
    def deleteRig(self, rigToDelete=None):
        """ Deletes given rig from scene.
        
        Parameters
        ----------
        rig : str, Rig, modoItem, list or None
            String is scene ident of the rig, Rig is rig object directly.
            Pass a list to delete multiple rigs in one go.
            None deletes current edit rig.
        
        Returns
        -------
        bool
            True when rig was deleted, False otherwise.
        """
        rigs = []
        if rigToDelete is None:
            rigs = [self.editRig]
        else:
            if type(rigToDelete) not in (tuple, list):
                rigToDelete = [rigToDelete]
            
            for rigInitialiser in rigToDelete:
                delrig = self._getRigFromCompatibleObject(rigInitialiser)
                if delrig is None:
                    continue
                rigs.append(delrig)
                
        if not rigs:
            log.out("Cannot find rig(s) to delete...", log.MSG_ERROR)
            return False

        for delrig in rigs:
            delrig.selfDelete()

        self._scan()
        self.resetEditRig()

        # Clear any scene settings when all rigs are removed from scene.
        if not self.anyRigsInSceneFast():
            self.settings.clear()
            
        return True

    @property
    def contexts(self):
        return self._contexts

    @property
    def context(self):
        """ Returns current context object.

        Returns
        -------
        Context 
            Context object.
        """
        return self._contexts.current

    @context.setter
    def context(self, newContext):
        """ Sets new context for all rigs in scene.
        
        Parameters
        ----------
        newContext : str or Context
            Context identifier or context object directly.
        """    
        try:
            self._contexts.current = newContext
        except TypeError:
            return False
        return True

    def refreshContext(self):
        """ Reapplies current context.
        
        This is to update rig elements states like visibility, selectability, etc.
        """
        self._contexts.refreshCurrent()

    def resetContextSceneChanges(self):
        """ Resets any changes current context did to item visibilities, etc.
        
        This is useful if you want to temporarily disable any changes
        that given context does to rig items so they are not saved
        with these changes. Right now it really means changed item
        visibility settings.
        
        To avoid this problem all visibility changes need to be somehow done
        on group level rather then on individual items level.
        """
        contextOp = context_op.ContextOperator(self)
        contextOp.resetChanges()

    def select(self, rigs, state=True, replace=True):
        """ Select given rigs.
        
        Parameters
        ----------
        state : bool
            Choose whether rigs should be selected or deselected.
            
        replace : bool
            Whether to replace current selection or add (remove) to it.
        """
        if type(rigs) not in (tuple, list):
            rigs = [rigs]
        
        if replace and state:
            for rigObj in self.rigs:
                rigObj.selected = False
        
        rigObjs = []
        for rigInitialiser in rigs:
            try:
                rigObj = rig.Rig.getFromOther(rigInitialiser)
            except TypeError:
                continue
            else:
                rigObjs.append(rigObj)
                rigObj.selected = state
        
        # Handle edit rig.
        if rigObjs:
            if state:
                self.editRig = rigObjs[-1]
            else:
                self.resetEditRig()

    @property
    def settings(self):
        """ Gets item settings interface for the scene.
        
        Returns
        -------
        item_settings.ItemSettings
        """
        return self._getSettings()

    @property
    def sceneItem(self):
        """ Gets the scene modo item for this scene.
        
        Returns
        -------
        modo.Item
        """
        return self._scene.sceneItem

    def getRigByIndex(self, index):
        """ Gets rig by its index in the scene. 
        
        Parameters
        ----------
        index : int

        Returns
        -------
        Rig

        Raises
        ------
        LookupError
            When bad rig index was passed (no rig with this index in the scene).
        """
        try:
            self._validateRigElement(index)
        except IndexError:
            raise LookupError
        return self._rigs[index]

    # --- Private methods

    def _scan(self):
        """ Builds a list of rigs in the scene.
        
        This method is called automatically when the scene object is instantiated.
        To optimise performance the list contains only rig root items instead of Rig
        objects if there is no undo context (which means scene object was initialised
        from command's query or enable method most likely).

        Returns
        -------
        bool
            True when any rigs were found.
        """
        self._clear()

        for n, rootModoItem in enumerate(self._scene.iterItemsFast(RootItem.descModoItemType)):
            if self._hasUndoContext():
                self._rigs.append(rig.Rig(rootModoItem))
                self._rigsByIdents[rootModoItem.id] = n
            else:
                self._rigs.append(rootModoItem)
                self._rigsByIdents[rootModoItem.id] = n

        return len(self._rigs) > 0

    def _getRigFromCompatibleObject(self, obj):
        """ Initialises rig from given object.
        
        Parameters
        ----------
        obj : Rig, modo.Item, str
        
        Returns
        -------
        Rig, None
        """
        if isinstance(obj, rig.Rig):
            return obj
        elif issubclass(obj.__class__, item.Item) or issubclass(obj.__class__, modo.Item):
            try:
                return rig.Rig(obj)
            except TypeError:
                return None
        elif isinstance(obj, str):
            try:
                rootItem = modo.Scene().item(obj)
            except LookupError:
                return None
            try:
                return rig.Rig(rootItem)
            except TypeError:
                return None
        return None
    
    def _hasUndoContext(self):
        if lx.symbol.iUNDO_ACTIVE == self._undoService.State():
            return True
        return False

    def _getUniqueRigName(self, name):
        """ Gets unique default name for the rig.
        
        If the name passed is unique it's returned as-is.
        A new, default name is generated otherwise.
        """
        names = [sceneRig.name for sceneRig in self.rigs]
        if name and name not in names:
            return name

        prefix = 'Char'
        maxRigs = 100
        defaultName = prefix
        for x in range(1, maxRigs):
            defaultName = prefix + str(x)
            if defaultName in names:
                continue
            break
        return defaultName

    def _getRigs(self):
        """ Gets a list of rigs as Rig objects.
        
        This method should always be used to get list of rigs instead of accessing
        the internal _rigs list directly.
        """
        for x in range(len(self._rigs)):
            self._validateRigElement(x)
        return self._rigs

    def _validateRigElement(self, index):
        """ Validates element in an internal rigs list.
        
        If the element is rig root item instead of Rig object
        this method will initialise Rig object with the
        root item and put Rig object on the list.
        """
        if not isinstance(self._rigs[index], rig.Rig):
            self._rigs[index] = rig.Rig(self._rigs[index])

    def _clear(self):
        """ Clears internal information about rigs.
        """
        self._rigs = []
        self._rigsByIdents = {}

    def _getSceneItem(self, sceneItem=None):
        if sceneItem is None:
            return modo.Scene(lxu.select.SceneSelection().current())
        else:
            if isinstance(sceneItem, lx.object.Scene) or isinstance(sceneItem, lxu.object.Scene):
                return modo.Scene(sceneItem)
            elif isinstance(sceneItem, modo.Scene):
                return sceneItem

        return None

    def _getSettings(self):
        if self._settings is None:
            self._settings = item_settings.ItemSettings(self._scene)
        return self._settings

    @property
    def _contexts(self):
        if self.__contextOp is None:
            self.__contextOp = context_op.ContextOperator(self)
        return self.__contextOp

    def __init__(self, sceneItem=None):
        self._scene = self._getSceneItem(sceneItem)
        if self._scene is None:
            raise TypeError
        self._undoService = lx.service.Undo()
        self._scan()
        self._settings = None
        
        self.__contextOp = None


