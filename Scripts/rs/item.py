
""" Base Item module.

    All custom rigging system items should be implemented via this interface.
    
    Copyright (C) 2017-2019 Lukasz Pazera.
"""


import lx
import lxu
import modo
import modox

from . import sys_component
from . import const as c
from . import name_op
from .core import service as service
from .log import log as log
from .debug import debug
from .component_setup import ComponentSetup
from .component_setups.rig import RigComponentSetup
from .component_setups.module import ModuleComponentSetup
from .item_settings import ItemSettings
from .item_feature_settings import ItemFeatureSettings
from .item_cache import ItemCache
from .util import run


class Item(sys_component.SystemComponent):
    """ Base class for implementing rig items.
    
    Parameters
    ----------
    modoItem : modo.Item
        Item that is a base for the rig item.

    Attributes
    ----------
    descType : str
        Identifier is an unique string identifier for the item type.
        Similar to analogue identifiers for standard modo items.
        
    descUsername : str
        User friendly name that will be shown in log outputs, etc.

    descSynthName : bool
        When False item name will not be changed by the system.
        Set to True by default.

    descModoItemType : str
        The type of a modo item this rig item is tied to. If this is set to None
        this rig item can be added on top of any MODO item.
        #TODO: make sure the item type can be set both as string and int.
    
    descModoItemSubtype : str
        Subtype is only for rig items based on groups really.
        Groups in MODO are all single item type but there a few group types
        within that. The type of the group is defined via a string value stored
        in a special tag on the group modo item. A subtype in this case is
        value of this special tag defining the exact type of the group.

    descFixedModoItemType : bool
        When True the rig item can only be based on the descModoItemType.
        It will not be possible to create rig item from modo item of any other item type.
        When False the descModoItemType is only a default item type and the rig item
        can be based on other modo item types.
        The default is True. 
        This attribute is ignored if descModoItemType is None.
    
    descExportModoItemType : str
        Type of the standard (vanilla) item to which rig item will be changed
        when preparing rig for export.
        The idea is that exported rig has to be default MODO scene
        so only standard MODO items are allowed as export ones.
        When left at default None the item will not be converted.
        This is fine for rig items that are based on standard MODO items.

    descDefaultName : str
        Default name for the rig item.
    
    descPackages : list, tuple, optional
        Rig items can work by adding packages over standard MODO items.
        Packages listed in this attribute will be automatically added to
        relevant modo item when rig item is added to the scene.
    
    descUserChannels : list
        A list of user channels to create on the item can be provided.
        This is a list of 4 element tuples in format:
        (channel_name, channel_username, channel_type, default_value)
        Channel type is one of lx.symbol.sTYPE_XXXX.
        
    descLookupGraph : str, optional
        Graph used for faster lookup of items of this type.
        The connection will be made between item of this type and its rig core item.
        This allows for fast lookup of items of this type in a rig.
    
    descItemCommand : str
        Name of the command that should be set as item commmand (one that
        get fired when an item is selected). Note that this will work only on locator
        items! This property is disabled on meshes.

    Methods
    -------
    onDroppedOnItem(self, destinationItem, context)
        destinationItem : modo.Item
        context : Context
        Called when this item is dropped on another item. This other item is
        passed as an argument.
    
    onItemDropped(self, sourceItem, context)
        sourceItem : modo.Item
        context : Context
        Called when some other item is dropped onto this item.
        The other item is passed as an argument.
    
    onSelected()
        Called when this item is selected in viewport.

    Raises
    ------
    TypeError
        When class is initialised with modo base item that is not valid rig item
        of this type.
    """

    SYS_COMPONENT_ITEM = c.SystemComponentType.ITEM
    TAG_ITEM = 'RSIT'
    _TAG_IDENTIFIER = 'RSID'

    CHAN_NAME = 'rsName'
    CHAN_IDENT = 'rsIdentifier'
    CHAN_SIDE = 'rsSide'
    CHAN_SIDE_FROM_MODULE = 'rsSideFromModule'

    # -------- Attributes forming a description of this item type.
    
    descType = ''
    descUsername = ''
    descSynthName = True
    descModoItemType = None
    descModoItemSubtype = '' # empty string means standard group by default
    descFixedModoItemType = True
    descExportModoItemType = None
    descDefaultName = ''
    descPackages = []
    descUserChannels = []
    descItemCommand = None
    descLookupGraph = ''
    descDropScriptSource = None
    descDropScriptDestination = None
    descDropScriptCreate = None
    descSelectable = True

    # -------- Optional, public methods to implement by the user.

    def init(self):
        """ Called when object is initialized.
        """
        pass
    
    def onAdd(self, subtype=None):
        """ Called when item instance is added to the scene.
        """
        pass

    def onConvert(self, subtype=None):
        """ Called when an already eisting item is converted to this item type.
        """
        pass

    def onStandardise(self):
        """ Called when an item is standardised.
        """
        pass

    # -------- System component attributes, do not touch.

    @classmethod
    def sysType(cls):
        return cls.SYS_COMPONENT_ITEM
    
    @classmethod
    def sysIdentifier(cls):
        return cls.descType
   
    @classmethod
    def sysUsername(cls):
        return cls.descUsername + ' Item'

    # -------- Public methods.

    @classmethod
    def new(self, name=None, subtype=None, componentSetup=None):
        """ Adds new item to the given scene.

        Parameters
        ----------
        name : str, optional
            Name of the new rig.
            
        subtype : str, optional
            Allows for adding variant of an item.
        
        componentSetup : ComponentSetup, modo.Item, optional
            Item will be automatically added to given component setup.
            If modo.Item is passed it's assumed to be the assembly the item should be added to.
            Use this to add item to component setup subassembly.
        
        Returns
        -------
            New rig item.
            
        Raises
        ------
        TypeError
        """
        if self.descModoItemType is None:
            return None

        modoScene = modo.Scene()

        if name is None or not name:
            name = self.descDefaultName

        if self.descModoItemType == 'group':
            newModoItem = modoScene.addGroup(name, gtype=self.descModoItemSubtype)
        else:
            newModoItem = modoScene.addItem(self.descModoItemType, name)

        newRigItem = self.newFromExistingItem(newModoItem, subtype, name, componentSetup)
        return newRigItem

    @classmethod
    def newFromExistingItem(cls, modoItem, subtype=None, name=None, componentSetup=None):
        """ Creates new rig item from existing modo item.

        Parameters
        ----------
        name : str, optional
            Name of the new rig.
            
        subtype : str, optional
            Allows for adding variant of an item.
        
        componentSetup : ComponentSetup, modo.Item, optional
            Item will be automatically added to given component setup.
            If modo.Item is passed it's assumed to be the assembly the item should be added to.
            Use this to add item to component setup subassembly.

        Raises
        ------
        TypeError
            When rig item requires fixed modo item type and given modo item type
            does not match the required modo item type.
            Note that for rig items that do not define modo item type or don't
            have fixed modo item type you need to make sure yourself that the match
            is correct. The exception will not be raised in such circumstances.
        """
        if cls.isRigItem(modoItem):
            # If we are dealing with rig item we should standardise it first.
            # This is to make sure it doesn't contain any left-over/corrupted data.
            # TODO: The problem with this though is that because there's no access to item features
            # from Item level the standardise will not deal with item features.
            # This has to be fixed but it requires considerable refactoring work.
            try:
                newRigItem = Item.getFromModoItem(modoItem)
            except TypeError:
                log.out("%s is an unknown rig item (probably corrupted)" % modoItem.name, log.MSG_ERROR)
                raise TypeError
            newRigItem.standardise()

        # Note: if the base item is standard group the subtype will be empty string.
        # This is weird but that's what modoItem.type returns for standard group items.
        # It returns empty string which means the GTYP tag value. This tag does not exist
        # on standard groups, it only exists on other groups such as actors, assemblies, etc.
        if cls.descModoItemType == 'group':
            rigModoItemType = cls.descModoItemSubtype
        else:
            rigModoItemType = cls.descModoItemType
        
        if (cls.descFixedModoItemType and
            cls.descModoItemType is not None and
            modoItem.type != rigModoItemType):
            raise TypeError

        newRigItem = cls._setupItemTypeOnItem(modoItem, subtype)
    
        # If component setup was passed we need to add the item to that setup.

        # If component setup is modo item we assume this is the specific assembly
        # that the item needs to be added to.
        # We get component from the assembly and add the item to this assembly directly.

        # If item was already in the same setup we only send item added event
        # to give the rig a chance to update its meta data.

        # If component setup was not passed but the item is in some setup
        # already we also need to send the item added event to notify the rest
        # of the rig that there is a new rig item.

        currentSetup = ComponentSetup.getSetupFromModoItem(modoItem)

        if componentSetup is None:
            if currentSetup is not None:
                service.events.send(c.EventTypes.ITEM_ADDED, item=modoItem)
            else:
                if debug.output:
                    log.out('The %s item has no rig context!' % modoItem.name)
        elif issubclass(componentSetup.__class__, modo.Item):
            assmModoItem = componentSetup
            componentSetup = ComponentSetup.getSetupFromModoItem(assmModoItem)
            componentSetup.addItem(modoItem, assmModoItem)
        else:
            if componentSetup == currentSetup:
                service.events.send(c.EventTypes.ITEM_ADDED, item=modoItem)
            else:
                componentSetup.addItem(modoItem)

        # onAdd() needs to be called after item was added to component setup!
        # There's still no guarantee that the item will have rig context
        # but at this point everything that was possible was done towards that goal.
        newRigItem.onAdd(subtype)
        
        try:
            newRigItem.name = name
        except AttributeError:
            pass

        return newRigItem

    @classmethod
    def isRigItem(cls, modoItem):
        """ Tests whether given item is already a rig item.
        
        Very simplistic method, simply tests for the presence of the rig item tag on an item.
        When called from particular item class it'll test the item to be of the same type
        as the class.
        
        Use it on base class to generally test if the item is rig item.
        Use on particular class to test whether item is a rig item of that class.
        """
        try:
            v = modoItem.readTag(cls.TAG_ITEM)
        except LookupError:
            return False
        if cls.descType:
            return v == cls.descType
        return True

    @classmethod
    def getClass(cls):
        """ Gets class that implements that item.
        """
        return cls

    @classmethod
    def getFromModoItem(cls, modoItem):
        """ Gets proper rig item object from standard modo item.
        
        Parameters
        ----------
        modoItem : modo.Item
            modo item that is the basis of the rig item (has its properties added).
        
        Returns
        -------
        RigItem
        
        Raises
        ------
        TypeError
            if modoItem was not recognized to be of any registered rig item type.
        """
        rigItemType = cls._getType(modoItem)
        if rigItemType is None:
            raise TypeError
        try:
            itemTypeClass = service.systemComponent.get(cls.SYS_COMPONENT_ITEM, rigItemType)
        except LookupError:
            raise TypeError
        return itemTypeClass(modoItem)

    @classmethod
    def getFromOther(cls, other):
        """ Gets rig item from other object.
        
        If passed object is the rig item itself it's simply returned.
        
        Parameters
        ----------
        other : Item, modo.Item, lx.object.Item, lxu.object.Item, str
        
        Raises
        ------
        TypeError
            If 'other' cannot be converted to rig item.
        """
        if issubclass(other.__class__, Item):
            return other

        if isinstance(other, modo.Item) or issubclass(other.__class__, modo.Item):
            return cls.getFromModoItem(other)
        elif isinstance(other, lx.object.Item):
            return cls.getFromModoItem(modo.Item(lxu.object.Item(other)))
        elif isinstance(other, lxu.object.Item):
            return cls.getFromModoItem(modo.Item(other))
        elif isinstance(other, str):
            try:
                scene = lxu.select.SceneSelection().current()
                rawItem = lxu.object.Item(scene.ItemLookup(other))
                return cls.getFromModoItem(modo.Item(rawItem))
            except LookupError:
                raise TypeError
        raise TypeError

    @classmethod
    def getTypeFromModoItem(cls, modoItem):
        """ Gets rig item type from modo item.
        
        Returns
        -------
        str, None
            String identifier of the rig type will be returned or None if modo item
            has no rig item type on it.
        """
        return cls._getType(modoItem)

    @classmethod
    def convert(self, modoItem, subtype = None, itemBasename=None):
        """ Convert existing item to the item of given type.

        This assumes we're converting standard modo item, not rig item
        of different item type.
        """
        if not self.allowAnyModoItemType:
            # change item type here.
            # TODO: This needs rethinking. Either don't allow to convert
            # to rig item types that depend on modoItemType or change
            # modo item type as well.
            pass

        itemInstance = self._setupItemTypeOnItem(modoItem, subtype)
        if itemBasename is None:
            itemBasename = modoItem.name
        itemInstance.baseName = itemBasename
        itemInstance.onConvert(subtype)
        return itemInstance

    @classmethod
    def testModoItem(cls, modoItem):
        """ Tests passed item against being of the implemented type.

        Override this method to implement custom way of testing modo
        basis item to see if it's a rig item of desired type.

        Returns
        -------
        bool
        """
        return cls._getType(modoItem) == cls.descType

    @classmethod
    def isHiddenFast(cls, modoItem):
        """
        Tests whether this item is hidden rig item.

        Returns
        -------
        bool
            It tests hidden property on the rig item.
            If passed item was modo item this function returns False since
            regular modo item cannot be set to be hidden.
        """
        hiddenChan = modoItem.channel('rsHidden')
        if hiddenChan is None:
            return False
        return bool(hiddenChan.get())

    @property
    def systemVersion(self):
        """
        Gets system version from this item.

        NOTE: This only makes sense to use on items that store system version
        such as rig or module root items.

        Returns
        -------
        int
            0 is returned when system version tag is not set on the item.
        """
        try:
            return int(self.modoItem.readTag('RSVR'))
        except LookupError:
            pass
        return 0

    def setSystemVersion(self):
        """
        Sets system version on the item.

        System version is stored in a tag.
        """
        self.modoItem.setTag('RSVR', str(service.systemVersion))

    @property
    def rigSystemVersion(self):
        """
        Gets version of a system with which the rig containing this item was created.

        Returns
        -------
        int

        Raises
        ------
        LookupError
            When system version cannot be retrieved (item is not part of any rig).
        """
        rigRoot = self.rigRootItem
        if rigRoot is None:
            raise LookupError
        return rigRoot.systemVersion

    @property
    def moduleSystemVersion(self):
        """
        Gets version of a system with which the module containing this item was created.

        Returns
        -------
        int

        Raises
        ------
        LookupError
            When system version cannot be retrieved (item is not part of any module).
        """
        moduleRoot = self.moduleRootItem
        if moduleRoot is None:
            raise LookupError
        return moduleRoot.systemVersion()

    @property
    def modoItem(self):
        """ Returns modo item that this rig item is tied to.
        """
        return self._modoItem

    @property
    def name(self):
        """
        Gets rig item name.

        It's possible that rig item does not have generic item package and doesn't have name channel.
        In this case name will be empty string.
        """
        try:
            return self.getChannelProperty(self.CHAN_NAME)
        except LookupError:
            return ''

    @name.setter
    def name(self, name):
        """ Gets/sets name to use for generating full modo item name.
    
        Setting name renders new full modo item name automatically.
        
        By default name is taken from a 'rsName' channel. If rig item
        has such channel this property will function correctly.
        It has to be reimplemented otherwise.
        """
        try:
            result = self.setChannelProperty(self.CHAN_NAME, name)
            if result:
                self.renderAndSetName()
            return result
        except LookupError:
            return False
        return False

    @property
    def identifier(self):
        try:
            tagVal = self.modoItem.readTag(self._TAG_IDENTIFIER)
        except LookupError:
            tagVal = None
        return tagVal

    @identifier.setter
    def identifier(self, ident):
        """ Gets/sets item identifier.
        
        Parameters
        ----------
        ident : str, None
            Optional string identifier for an item. Pass None to clear the identifier from item.
        
        Returns
        -------
        str, None
            None is returned when item has no identifier set.
        """
        if type(ident) == str:
            if not ident:
                ident = None
        elif ident is not None:
            return
        self.modoItem.setTag(self._TAG_IDENTIFIER, ident)

    @property
    def identifierOrName(self):
        """ Gets either identifier of an item or if not set - the name.
        """
        identifier = self.identifier
        if identifier:
            return identifier
        return self.name

    @property
    def identifierOrNameType(self):
        """ Gets either identifier of an item or its name with type if there's no ident.
        
        Name with type is simply a string of 'name.type'
        
        Returns
        -------
        str
        """
        identifier = self.identifier
        if identifier:
            return identifier
        return self.name + '.' + self.type
    
    @property
    def side(self):
        """ Gets evaluated side property.
        
        This will always be right/center/left.
        Evaluation takes item's side own setting and if it's not
        present or set to inherit from module - module's one will be returned.
        
        Returns
        -------
        c.SIDE.XXX
        """
        # TypeError happens if this item does not have its own side setting.
        try:
            sideSameAsModule = self.sideSameAsModule
            itemSide = self.itemSide
        except TypeError:
            return self._moduleSide

        if sideSameAsModule:
            return self._moduleSide
        return itemSide

    @property
    def nameAndSide(self):
        """ Returns name with side added formatted according to rig's naming scheme.
        
        Returns
        -------
        str
            Rendered side+name string.
        """
        rigRoot = self.rigRootItem
        if rigRoot is None:
            # Don't use name scheme, apply default naming
            sideString = {c.Side.CENTER: '', c.Side.LEFT: 'Left ', c.Side.RIGHT: 'Right '}
            return sideString[self.side] + self.name

        namingScheme = rigRoot.namingScheme
        nameOp = name_op.NameOperator(namingScheme)

        components = {}
        components[c.NameToken.SIDE] = self.side
        components[c.NameToken.BASE_NAME] = self.name
        
        return nameOp.renderName(components)

    @property
    def referenceUserName(self):
        """
        Gets reference user name. Reference name is independent from naming scheme.
        It's always the same. It's user friendly meaning it contains spaces.

        Reference name is composed of:
        side moduleName basename

        Parameters
        ----------
        addSide : bool
            When False side is not added to reference user name.

        Returns
        -------
        str

        Raises
        ------
        TypeError
            When reference name cannot be created - this is when rig item does not have a name.
        """
        moduleRootItem = self.moduleRootItem
        name = self.name

        if not name:
            raise TypeError

        sideString = {c.Side.CENTER: '', c.Side.LEFT: 'Left ', c.Side.RIGHT: 'Right '}
        if moduleRootItem is not None:
            refName = ''
            refName += sideString[self.side]
            refName += self.moduleRootItem.name + ' '
            refName += self.name
        else:
            refName = sideString[self.itemSide] + self.name
        return refName

    def getReferenceName(self, side=True, moduleName=True, basename=True):
        """
        Gets reference name for this item. It's string built from max. 3 components.

        Parameters
        ----------
        side : bool

        moduleName : bool

        basename : bool

        Returns
        -------
        str
        """
        refName = ''
        if side:
            sideString = {c.Side.CENTER: 'C', c.Side.LEFT: 'L', c.Side.RIGHT: 'R'}
            refName += sideString[self.side]
        if moduleName:
            refName += self.moduleRootItem.name
        if basename:
            refName += self.name
        return refName

    def getMirroredReferenceName(self, module=True, basename=True):
        """
        Gets mirrored reference name for this item.

        The difference to the getReferenceName() is that right side items
        are begin returned as left side ones and vice versa.
        Center items are not affected.
        """
        refName = self.getReferenceName(True, module, basename)
        if refName.startswith('R'):
            refName = 'L' + refName[1:]
        elif refName.startswith('L'):
            refName = 'R' + refName[1:]
        return refName


    def renderNameFromTokens(self, tokens):
        """ Renders name from given name tokens.
        
        The name will be rendered according to the current rig naming scheme.

        Parameters
        ----------
        tokens : list of rs.c.NameToken
        """
        rigRoot = self.rigRootItem
        if rigRoot is None:
            return ''

        allComponents = self._nameComponents
        componentsDict = {}
        for compToAdd in tokens:
            try:
                componentsDict[compToAdd] = allComponents[compToAdd]
            except KeyError:
                continue

        namingScheme = rigRoot.namingScheme
        nameOp = name_op.NameOperator(namingScheme)
        return nameOp.renderName(componentsDict)

    @property
    def sideSameAsModule(self):
        """ Returns true if item takes its side from module.
        
        Raises
        ------
        TypeError
            When item does not support side on item level.
        """
        try:
            return self.getChannelProperty(self.CHAN_SIDE_FROM_MODULE)
        except LookupError:
            raise TypeError

    @sideSameAsModule.setter
    def sideSameAsModule(self, state):
        self.setChannelProperty(self.CHAN_SIDE_FROM_MODULE, state)
        # Only update stuff when state is True.
        # It'll be updated by the itemSide otherwise.
        # Crappy code, I know.
        if state:
            self.renderAndSetName()
            service.events.send(c.EventTypes.ITEM_SIDE_CHANGED, item=self)

    @property
    def itemSide(self):
        """ Returns item's own side setting.
        
        Raises
        ------
        TypeError
            When item does not support side setting.
        """
        try:
            return self.getChannelProperty(self.CHAN_SIDE)
        except LookupError:
            raise TypeError

    @itemSide.setter
    def itemSide(self, side):
        if side not in [c.Side.CENTER, c.Side.LEFT, c.Side.RIGHT]:
            return False
        try:
            self.setChannelProperty(self.CHAN_SIDE, side)
        except LookupError:
            raise TypeError
        self.renderAndSetName()
        service.events.send(c.EventTypes.ITEM_SIDE_CHANGED, item=self)

    @property
    def hidden(self):
        """
        Tests if the item is a hidden one.

        Hidden item is one that we do not want to see in contexts or make it not availble in some other way.
        For example a controller that should not show up in viewport.

        Returns
        -------
        bool
        """
        hiddenChan = self._modoItem.channel('rsHidden')
        if hiddenChan is None:
            return False
        return bool(hiddenChan.get())

    @hidden.setter
    def hidden(self, state):
        """
        Marks rig item as hidden or visible.
        When item is hidden it doesn't get shown in its context.

        Parameters
        ----------
        state : bool
        """
        hiddenChan = self._modoItem.channel('rsHidden')
        if hiddenChan is None:
            return
        hiddenChan.set(state, 0.0, key=False, action=lx.symbol.s_ACTIONLAYER_SETUP)

    @property
    def visible(self):
        return self._modoItem.channel('visible').get(time=0.0, action=lx.symbol.s_ACTIONLAYER_EDIT)

    @visible.setter
    def visible(self, value):
        """ Toggles item visibility.
        
        Paramters
        ---------
        value : c.ItemVisible.XXX, bool
            Either item visible state as used in MODO or a bool.
            Bool is converted such that True means default visibility value
            and False means hide just that item (don't affect children).
        """
        if type(value) == bool:
            if value:
                value = c.ItemVisible.DEFAULT
            else:
                value = c.ItemVisible.NO
        self._modoItem.channel('visible').set(value, time=0.0, key=False, action=lx.symbol.s_ACTIONLAYER_SETUP)

    def renderAndSetName(self):
        """ Renders and sets full item name.

        Name will be set according to a name scheme used by
        the rig the item belongs to.

        TODO: This method doesn't work when item does not
        belong to a rig. It should still work, only rig name
        and module names parts should not be added to the name.
        """
        if not self.descSynthName or self.rigRootItem is None:
            return

        nameScheme = self.rigRootItem.namingScheme
        if nameScheme is None:
            return False
        
        nameOp = name_op.NameOperator(nameScheme)

        components = self._nameComponents
        newName = nameOp.renderName(components)
        self.modoItem.name = newName
        return True

    @property
    def type(self):
        """ Gets rig item type as string.
        
        Returns
        -------
        str
            None if type cannot be determined.
        """
        return self._getType(self.modoItem)
    
    @property
    def moduleRootItem(self):
        """ Gets this item's ModuleRoot.

        Returns
        -------
        ModuleRoot
            Or None if item doesn't belong to any module
        """
        # TODO: I could potentially cache the resulting module
        # if the lookup is slow. Rendering and setting name
        # needs to get module twice for example, might be slowing
        # it down.
        try:
            setup = ModuleComponentSetup(self.modoItem)
        except TypeError:
            return None

        return self.getFromModoItem(setup.rootModoItem)

    @property
    def rigRootItem(self):
        """ Returns RigItem interface for this item rig's root item.
        
        Returns
        -------
        RootItem
            Or None if item does not belong to any rig.
        """
        if self.__rigRootItem is None:
            try:
                setup = RigComponentSetup(self.modoItem)
            except TypeError:
                return None
            
            try:
                self.__rigRootItem = self.getFromModoItem(setup.rootModoItem)
            except TypeError:
                return None
        return self.__rigRootItem

    @property
    def componentSetup(self):
        """ Returns the closest component setup the item is in.
        
        Returns
        -------
        ComponentSetup or None
            The ComponentSetup will be of correct setup type.
        """
        return ComponentSetup.getSetupFromModoItem(self.modoItem)

    def getFeature(self, ident):
        pass

    @property
    def features(self):
        pass

    @property
    def isPartOfRig(self):
        pass

    @property
    def settings(self):
        return self._settings

    def getChannelProperty(self, channelName):
        """ Gets property stored on this item's channel.
        
        Parameters
        ----------
        channelName : str
            Name of the channel that stores the property
        
        Returns
        -------
        Value of the type matching channel type.
        Also works with ChannelTriple, returns a tuple of 3 floats then.
        For integer channels with hints - a hint is returned.
        
        Raises
        ------
        LookupError
            When channel cannot be found.
        """
        chan = self.modoItem.channel(channelName)
        if chan is None:
            raise LookupError
        
        val = chan.get(time=0.0, action=lx.symbol.s_ACTIONLAYER_EDIT)
        try:
            if chan.storageType == 'boolean':
                val = bool(val)
        except AttributeError: # This will happen if it's ChannelTriple, not regular Channel
            pass
        return val

    def setChannelProperty(self, channelName, value):
        """ Stores property in a given channel.
        
        Parameters
        ----------
        channelName : str
            Name of the channel that stores the property.
        
        value :
            Value to be stored.
        
        Returns
        -------
        bool
            True when property was set successfully, false otherwise.
        """
        chan = self.modoItem.channel(channelName)
        if chan is None:
            return False
        chan.set(value, time=0.0, key=False, action=lx.symbol.s_ACTIONLAYER_SETUP)
        return True
    
    def standardise(self):
        """ Standardises an item so it can be loaded on vanilla MODO.
        
        Note that this does not handle item features.
        Item features should be removed prior to calling this method.
        
        Also, this method affects item selection!
        """
        self.modoItem.setTag(Item.TAG_ITEM, None)
        self.modoItem.setTag('IDSS', None)
        self.settings.clear()

        cache = ItemCache()
        cache.cacheChannels(self.modoItem)

        # Remove rigging system packages only
        if self.descPackages:
            for package in self.descPackages:
                if not package.startswith(c.String.SYSTEM_PACKAGE_PREFIX):
                    continue
                # For some reason removing package via SDK raises LookupError
                # even if package is on the item and it was removed successfully.
                try:
                    self.modoItem.internalItem.PackageRemove(package)
                except LookupError:
                    pass

        # Remove any rs item links.
        # The assumption is that rs graph names start with 'rs.'.
        graphNames = self.modoItem.itemGraphNames
        for graphName in graphNames:
            if not graphName.startswith('rs.'):
                continue
            modox.ItemUtils.clearForwardGraphConnections(self.modoItem, graphName)
            modox.ItemUtils.clearReverseGraphConnections(self.modoItem, graphName)

        # Remove any remaining rigging system tags
        remainingTags = self._modoItem.getTags(values=False)

        for tag in remainingTags:
            # Python 3 compatibility!!!
            # Tags are getting returned in byte mode in python 3
            # not as str so I have to force convert it,
            # startswith tries to compare bytes otherwise.
            if str(tag).startswith('RS'):
                self._modoItem.setTag(tag, None)

        # Clear item command if it's set to standard item command
        itemCmdString = modox.ItemUtils.getItemCommand(self.modoItem)
        if itemCmdString is not None and itemCmdString == c.ItemCommand.GENERIC:
            modox.ItemUtils.removeItemCommand(self.modoItem)

        # Clear drop scripts
        modox.ItemUtils.setCreateDropScript(self.modoItem, None)
        modox.ItemUtils.setSourceDropScript(self.modoItem, None)
        modox.ItemUtils.setDestinationDropScript(self.modoItem, None)

        # Change item type to standard item.
        # Internally changing item type is really adding new item in place of old one.
        # So any references to the item become invalid after changing type and will
        # crash modo. You have to obtain the changed item and work on that one instead.
        restoreItem = self.modoItem
        if self.descExportModoItemType is not None:
            self.modoItem.select(replace=True)
            run('item.setType {%s}' % self.descExportModoItemType)
            restoreItem = modox.ItemSelection().getLastModo()
            
        # Restore any cached channels as user channels.
        # Cache has to be restored on the restoredItem, not the original item if its type was changed.
        if restoreItem is not None:
            cache.restoreChannels(restoreItem)

    # -------- Private methods

    @classmethod
    def _setupItemTypeOnItem(cls, newModoItem, subtype):
        """ Sets up new rig item type on an existing MODO item.
        """
        newModoItem.setTag(cls.TAG_ITEM, cls.descType)
    
        if cls.descPackages:
            for package in cls.descPackages:
                newModoItem.PackageAdd(package)

        if cls.descUserChannels:
            xitem = modox.Item(newModoItem.internalItem)
            for userChannelDefinition in cls.descUserChannels:
                chan = xitem.addUserChannel(userChannelDefinition[0], userChannelDefinition[2], userChannelDefinition[1])
                chan.set(userChannelDefinition[3], time=0.0, key=False, action=lx.symbol.s_ACTIONLAYER_SETUP)
                
        cls._addDropScripts(newModoItem)
        cls._setItemCommand(newModoItem)
        cls._setSelectable(newModoItem)
        
        return cls(newModoItem)

    @classmethod
    def _addDropScripts(cls, modoItem):
        """ Adds drop scripts to the given item.

        Create drop script, if present, is added to any type of item.
        Item source and destination scripts are added to locator supertype
        items only with exception of group locators since they don't show up in viewports anyway.
        """
        if cls.descDropScriptCreate:
            modox.ItemUtils.setCreateDropScript(modoItem, cls.descDropScriptCreate)

        if not modox.Item(modoItem.internalItem).isOfXfrmCoreSuperType:
            return
        if modoItem.type == modox.c.ItemType.GROUP_LOCATOR:
            return

        try:
            sourceDrop = cls.descDropScriptSource
        except AttributeError:
            sourceDrop = None
        
        if sourceDrop:
            modoItem.setTag('IDSS', sourceDrop)
        
        try:
            destDrop = cls.descDropScriptDestination
        except AttributeError:
            destDrop = None
        
        if destDrop:
            modoItem.setTag('IDSD', destDrop)

    @classmethod
    def _setItemCommand(cls, modoItem):
        """ Sets item command.

        This has to replicate everything that item command does.
        I use this code sometimes because item.command can fail for some mysterious reason.
        """
        if cls.descItemCommand:
            modox.ItemUtils.setItemCommandManually(modoItem, cls.descItemCommand)

    @classmethod
    def _setSelectable(cls, modoItem):
        # Change selectability only if the item is meant to be non-selectable.
        # TODO: This should only really be called on locator supertype items.
        if not cls.descSelectable:
            run('item.channel select off mode:set item:{%s}' % (modoItem.id))

    @classmethod
    def _getType(cls, modoItem):
        try:
            tagVal = modoItem.readTag(cls.TAG_ITEM)
        except LookupError:
            tagVal = None
        return tagVal

    @property
    def _settings(self):
        if self.__settings is None:
            self.__settings = ItemSettings(self._modoItem)
        return self.__settings

    @property
    def _moduleSide(self):
        """
        Gets module side.

        If item does not belong to any module it returns item side.
        If item side is not defined CENTER is returned.
        """
        modRoot = self.moduleRootItem
        if modRoot is not None:
            return modRoot.side
        try:
            return self.itemSide
        except TypeError:
            pass
        return c.Side.CENTER

    @property
    def _nameComponents(self):
        """ Gets all name components.
        
        Returns
        -------
        dict
            The dictionary will be empty if item does not belong to any rigs.
        """
        rigName = ''
        rigRootItem = self.rigRootItem
        if rigRootItem is None:
            return {}
        
        rigName = rigRootItem.name
        baseName = self.name
        
        side = self.side

        mod = self.moduleRootItem
        if mod is not None:
            moduleName = mod.name
        else:
            moduleName = ''

        components = {}
        components[c.NameToken.RIG_NAME] = rigName
        components[c.NameToken.MODULE_NAME] = moduleName
        components[c.NameToken.BASE_NAME] = baseName
        components[c.NameToken.SIDE] = side
        components[c.NameToken.ITEM_TYPE] = self.type
        components[c.NameToken.MODO_ITEM_TYPE] = self.modoItem.type

        # Add item feature idents
        features = ItemFeatureSettings(self.modoItem).featureIdentifiers
        components[c.NameToken.ITEM_FEATURE] = features

        return components

    def __init__ (self, modoItem):
        if isinstance(modoItem, lx.object.Item):
            modoItem = lxu.object.Item(modoItem)
        if isinstance(modoItem, lxu.object.Item):
            modoItem = modo.Item(modoItem)
        result = self.testModoItem(modoItem)
        if not result:
            raise TypeError
        self._modoItem = modoItem
        self.__settings = None
        self.__rigRootItem = None # cache rig root item
        self.init()
        
    def __eq__(self, other):
        if issubclass(other.__class__, Item):
            return self.modoItem == other.modoItem
        elif isinstance(other, str):
            return self.modoItem.id == other
        elif hasattr(other, 'id'):
            return self.modoItem.id == other.id
        return False

    def __ne__(self, other):
        """ != operator """
        return not self.__eq__(other)