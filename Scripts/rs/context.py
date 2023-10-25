
import lx
import lxu

import modo

from . import sys_component
from . import const as c
from .item_settings import ItemSettings
from .const import ItemVisible as v
from .log import log as log


class ContextElementStatesDesc(object):
    """ Use this class to define element sets visibility for a subcontext.
    """
    def __init__(self, statesDict, subcontext=None):
        self.subcontextIdentifier = subcontext
        self.elementStates = statesDict
    
    
class Context(sys_component.SystemComponent):
    """ Represents scene context for viewing rigs.
    
    Context is a singleton system component so there's always a single instance of it.
    This means that various attributes can be either static variables or properties,
    whichever works better for implementation.
    Some attributes have defaults defined as static variables. You can still reimplement them
    as properties if needed, properties override static variables of the same name.
    
    Attributes
    ----------
    descIdentifier : str
        Unique identifier for a context within all other contexts.

    descUsername : str
        User friendly name of the context.
    
    descSubcontexts : list of str
        If context can have subcontexts the list of their identifiers should be returned from this attribute.

    descDefaultSubcontext : str, optional
        Only valid id descSubcontexts is not None.

    descDisableMessageKey : str
        key to disable message table to display when context is disabled.

    setup : boolean, optional
        Set whether context changes setup mode to a specific state (on or off).
        When not defined or returns None setup mode is not affected.
        
    enable : boolean, optional
        Enable is queried whenever system needs to determine whether a context
        should be available to switch to or not. When not defined a default behaviour
        will be used which makes a context enabled whenever there is at least one
        rig in the scene.
    
    edit : boolean, optional
        When True the context operates on a current edit rig.
        All other rigs will be hidden. False is the assumed default.

    isolateEditModule : boolean, optional
        This works in edit contexts only. When True it's possible to isolate
        current edit module.
        
    isHierarchyVisible : boolean, optional
        Defaults to True which means that switching to a context will not hide
        rig hierarchy. Set it to False to hide entire hierarchy and then use
        elementsVisible attribute to set elements of the rig that should be visible.

    elementsVisible : dict, optional
        Use this static variable/property to define a list of elements that need to have
        their visibility set to a particular value.
    
    elementsVisibleToggle : dict{str : list[str]}, optional
        Use this property to define element sets which visibility can be toggled on/off.
        Keys in returned dictionary are subcontext identifiers (None for main context),
        values are element set identifiers.
        
    elementsRender : dict, optional
        Same as above but for setting renderable state for rig elements.
    
    elementsSelectable : dict, optional
        Same as above for setting item's selectable properties.
        
    elementsLocked : dict, optional
        Same as above but for elements locked state.

    Methods
    -------
    onSet()
        Called when a context is set.
        Perform any actions required to apply the context properly.
    
    onLeave()
        Called right before a context is switched to another one.
        Perform any clean up actions in here.

    onRefresh()
        Called when we're not switching to different context but
        setting the same context again.

    onSubcontextSet()
        Called when subcontext was switched inside the main context.
        Use self.subcontext to know which subcontext you are switched to.

    onSubcontextLeave()
        Called when leaving one subcontext and switching to another.
        Use self.subcontext to know which subcontext you are leaving.

    refreshOnSubcontextChange(previous, new)
        Called when subcontext was switched.
        Takes 2 string arguments: the subcontext that was previously set
        and new one that has just been set.
        This callback should return True if context should be refreshed when subcontext changed.
        False otherwise.
    """

    _SET_GROUP = 'subcxt'
    _VISIBILITY_MAP = {True: v.YES, False: v.DEFAULT}
    _VIS_TOGGLE_SETTING_GROUP_BASENAME = 'cxtvis'
    
    # -------- Attributes
    
    descIdentifier = ''
    descUsername = ''
    descSubcontexts = None
    descDefaultSubcontext = None
    descDisableMessageKey = None

    edit = False
    isHierarchyVisible = True
    isolateEditModule = False

    # -------- System component attributes, do not touch.

    SYS_COMPONENT_CONTEXT = c.SystemComponentType.CONTEXT
    
    @classmethod
    def sysType(cls):
        return cls.SYS_COMPONENT_CONTEXT
    
    @classmethod
    def sysIdentifier(cls):
        return cls.descIdentifier
   
    @classmethod
    def sysUsername(cls):
        return cls.descUsername
    
    @classmethod
    def sysSingleton(cls):
        return True

    # -------- Public methods
    
    @property
    def subcontext(self):
        sublist = self.descSubcontexts
        if sublist is None:
            return None
        
        subcontext = self.settings.getFromGroup(self._SET_GROUP, self.descIdentifier, self.descDefaultSubcontext)
        if subcontext not in sublist:
            return None
        return subcontext
    
    @subcontext.setter
    def subcontext(self, ident):
        """ Gets/sets subcontext for this context.
        
        Parameters
        ----------
        ident : str
            Ident of the subcontext to set. 
        
        Returns
        -------
        str, None
            Gets subcontext string identifier or None if this context has no subcontexts defined.
        """
        sublist = self.descSubcontexts
        if sublist is None:
            return
        
        if ident not in sublist:
            return

        self.settings.setInGroup(self._SET_GROUP, self.descIdentifier, ident)
   
    def getElementSetVisibility(self, elementSetId, subcontext=None):
        """ Gets visibility setting for given element set in a given subcontext.
        
        This works with element sets that can have their visibility change dynamically.

        Parameters
        ----------
        elementSetId : str
            Name of the element set to get the visibility for.

        subcontext : str, None
            None means general context, without taking subcontext into consideration.

        Returns
        -------
        bool

        Raises
        ------
        LookupError
            If element set visibility is not defined for this particular context.
        """
        if subcontext is None:
            subcontextTxt = ''
        else:
            subcontextTxt = subcontext
        settingsGroup = self.descIdentifier + subcontextTxt + self._VIS_TOGGLE_SETTING_GROUP_BASENAME
        visValue = self.settings.getFromGroup(settingsGroup, elementSetId, None)
        if visValue is None:
            # No setting for this one, return default value.
            # If no value return False (hidden)
            try:
                visValue = self._defaultVisibility[subcontext][elementSetId]
            except KeyError:
                return False
        return visValue

    def setElementSetVisibility(self, elementSetId, state, subcontext=None):
        """ Sets visibility state for a given element set.
        
        The state is stored in scene file so it will be preserved when the scene is reloaded.
        
        Parameters
        ----------
        elementSetId : str
        
        state : bool

        subcontext : str, None
            Pass None if context has no subcontexts.
        """
        if subcontext is None:
            subcontextTxt = ''
        else:
            subcontextTxt = subcontext
        settingsGroup = self.descIdentifier + subcontextTxt + self._VIS_TOGGLE_SETTING_GROUP_BASENAME
        self.settings.setInGroup(settingsGroup, elementSetId, state)

    def getElementsVisibilityToProcess(self):
        """ Gets item visibility values as a dictionary.

        Returns
        -------
        dict(str : c.ItemVisible)
            Key is element set identifier, value is a visibility value as used in MODO.
        """
        subcontext = self.subcontext
        vis = {}
        try:
            vis = self._defaultVisibility[subcontext]
        except KeyError:
            # If subcontext visibility is not defined fall back on the generic one.
            # This is important if subcontext do not change elements visibility.
            subcontext = None
            try:
                vis = self._defaultVisibility[subcontext]
            except KeyError:
                return {}

        # Now we need to test if there are toggleable states.
        # If there are these override default values.
        toggleableElementSetIds = self._getToggleableElementSets(subcontext)
        if toggleableElementSetIds:
            for setid in toggleableElementSetIds:
                value = self.getElementSetVisibility(setid, subcontext)
                if value is not None:
                    vis[setid] = self._VISIBILITY_MAP[value]

        return vis

    @property
    def settings(self):
        # Context initialisation happens too early,
        # scene object cannot be taken as argument to __init__.
        # For now, we're creating scene settings object on the fly
        # when it's needed.
        # It makes contexts work on a current scene only though.
        # TODO: ?
        return ItemSettings(modo.Scene())

    # -------- Private methods

    def _getToggleableElementSets(self, subcontext=None):
        """ Gets a list of identifiers of element sets that are toggleable.
        Returns
        -------
        list[str]
        """
        try:
            toggleableSets = self.elementsVisibleToggle
        except AttributeError:
            return []

        try:
            return toggleableSets[subcontext]
        except KeyError:
            pass

        return []

    def _parseElementsVisible(self):
        """
        Parses elementsVisible property to create dictionary of default visibilities for elements.

        Returns
        -------
        dict{str, None: dict}
            Key is either subcontext string identifier or None for general context.
            Value is a dictionary with visibility bool values keyed by element set ids.
        """
        try:
            vispack = self.elementsVisible
        except AttributeError:
            return {}

        if isinstance(vispack, dict):
            return {None: vispack}

        defaultVisValues = {}
        for entry in vispack:
            defaultVisValues[entry.subcontextIdentifier] = entry.elementStates

        return defaultVisValues

    def _getElementSetDefaultVisibility(self, elementSetId, subcontext=None):
        try:
            return self._defaultVisibility[subcontext][elementSetId]
        except TypeError:
            return False

    def __init__(self):
        self._defaultVisibility = self._parseElementsVisible()
    
    def __eq__(self, other):
        if isinstance(other, str):
            return self.descIdentifier == other
        elif isinstance(other, Context):
            return self.descIdentifier == other.descIdentifier
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)