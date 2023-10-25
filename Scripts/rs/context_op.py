
""" Context operator.

    Copyright (C) 2017-2019 Lukasz Pazera.
"""


import time

import lx
import lxu
import modo
from modox import SetupMode
from .log import log as log
from .core import service as service
from . import const as c
from . import context
from .rig_structure import RigStructure


class ContextOperator(object):
    """ Used to perform operations on scene contexts.

    Parameters
    ----------
    rsScene : Scene
        Rig system scene object is required to initialize context operator.
    """

    _TAG_CONTEXT = 'RSCX'
    _TAG_CONTEXT_ID = lxu.lxID4(_TAG_CONTEXT)

    SETTING_CONTEXT = 'context'
    SETTING_ISOLATE_EDIT_MODULE = 'isolEditMod'

    _sceneService = lx.service.Scene()
    _SCENE_ITEM_INT_CODE = _sceneService.ItemTypeLookup(lx.symbol.sITYPE_SCENE)
    
    # -------- Class methods
    
    @classmethod
    def getContextIdentFast(cls):
        """ Gets context identifier fast, works for current scene only.

        If no context is found it'll return default context whether it's set or not.

        Returns
        -------
        str
        """
        rawScene = lxu.select.SceneSelection().current()
        rawSceneItem = lx.object.Item(rawScene.AnyItemOfType(cls._SCENE_ITEM_INT_CODE))
        tag = lx.object.StringTag(rawSceneItem)

        try:
            return tag.Get(cls._TAG_CONTEXT_ID)
        except LookupError:
            pass
        
        return c.DefaultValue.CONTEXT
        
    # -------- Public methods
    
    @property
    def current(self):
        """ Gets current context object.
        
        When no context is set yet the default context is returned.
        
        Returns
        -------
        context.Context inherited object
        """
        currentId = self._getContextIdent(c.DefaultValue.CONTEXT)
        return service.systemComponent.get(context.Context.sysType(), currentId)

    @current.setter
    def current(self, newContext):
        """ Sets new scene context.
        
        Parameters
        ----------
        newContext : str or context.Context inherited object
            Either context string ident or the context object itself.
        
        Raises
        ------
        TypeError
            If newContext argument is incorrect.
        """
        startTime = time.time()

        currentContextId = self._getContextIdent()

        # Grab new context object
        try:
            contextObject = self._getContextObject(newContext)
        except TypeError:
            raise TypeError

        switchingToNewContext = contextObject.descIdentifier != currentContextId

        self._leavePreviousContext(contextObject.descIdentifier)
        
        leaveTime = time.time()

        if switchingToNewContext:
            self._setSetupMode(contextObject)
        
        setupTime = time.time()
        
        try:
            edit = contextObject.edit
        except AttributeError:
            edit = False
        
        # For edit context leave only current edit rig visible.
        if edit:
            rigsToHide = self._scene.rigs
            editRig = self._scene.editRig
            if editRig is not None:
                for x in range(len(rigsToHide)):
                    if editRig == rigsToHide[x]:
                        rigsToHide.pop(x)
                        break
                rigsToShow = [editRig]
            else:
                rigsToShow = rigsToHide
                rigsToHide = []
        else:
            rigsToHide = []
            rigsToShow = self._scene.rigs
        
        for rig in rigsToHide:
            rig.visible = c.ItemVisible.NO_CHILDREN

        hideRigsTime = time.time()
        
        for rig in rigsToShow:
            self._setHierarchyVisibility(contextObject, rig)
            self._setElementsVisibility(contextObject, rig)
            self._setElementsSelectability(contextObject, rig)

        # If new context is different than previous one
        # we do onSet().
        # If it's the same context we do onRefresh()
        if switchingToNewContext:
            try:
                contextObject.onSet()
            except AttributeError:
                pass
            try:
                contextObject.onSubcontextSet()
            except AttributeError:
                pass
        else:
            try:
                contextObject.onRefresh()
            except AttributeError:
                pass

        self._scene.sceneItem.setTag(self._TAG_CONTEXT, contextObject.descIdentifier)
    
        endTime = time.time()
        if service.debug.output:
            log.out('Setting context took: %f' % (endTime - startTime))
            log.startChildEntries()
            log.out('Leave previous context: %f' % (leaveTime - startTime))
            log.out('Set setup mode time: %f' % (setupTime - leaveTime))
            log.out('Hiding rigs time: %f' % (hideRigsTime - setupTime))
            log.out('Showing rigs time: %f' % (endTime - hideRigsTime))
            log.stopChildEntries()
    
    def getSubcontext(self, contextid):
        """ Gets subcontext ident for a given context.
        
        Parameters
        ----------
        contextid : str, Context

        Returns
        -------
        str
            String identifier of the subcontext or None if bad context was given or context
            has not subcontexts defined.
        """
        if not isinstance(contextid, context.Context):
            try:
                contextid = service.systemComponent.get(c.SystemComponentType.CONTEXT, contextid)
            except LookupError:
                return None
        
        return contextid.subcontext
    
    def setSubcontext(self, contextid, subcontextid):
        """ Sets subcontext for a given context.
        
        You should use this function to set subcontext rather then the one on the Context interface.
        This is because from context operator level changing subcontext can refresh current context.
        It will not happen otherwise.
        
        Parameters
        ----------
        contextid : str, Context
        
        subcontextid : str
        """
        if not isinstance(contextid, context.Context):
            try:
                contextid = service.systemComponent.get(c.SystemComponentType.CONTEXT, contextid)
            except LookupError:
                return None
        
        previous = contextid.subcontext

        try:
            contextid.onSubcontextLeave()
        except AttributeError:
            pass

        contextid.subcontext = subcontextid

        try:
            contextid.onSubcontextSet()
        except AttributeError:
            pass

        try:
            refresh = contextid.refreshOnSubcontextChange(previous, subcontextid)
        except AttributeError:
            refresh = False
            
        if refresh and self.current == contextid:
            self.refreshCurrent()
            
    def resetChanges(self):
        """ Resets all the changes that current context does to scene.
        
        This is equivalent to what is happening when a context is left
        but new one is not set. Note that this does not clear the context setting,
        just its effect on the scene.
        This can be used to temporarily remove any effect context has on item's
        visibility and selectability.
        """
        self._leavePreviousContext()

    def refreshCurrent(self):
        """ Reapplies current context.
    
        This is to update rig elements states like visibility, selectability, etc.
        """
        currentContext = self.current
        self.current = currentContext

    @property
    def isolateEditModule(self):
        return self._scene.settings.get(self.SETTING_ISOLATE_EDIT_MODULE, False)
    
    @isolateEditModule.setter
    def isolateEditModule(self, state):
        """ Toggles isolate edit module mode.
        
        This only has an effect on edit contexts that allow that.
        
        Parameters
        ----------
        state : bool
        """
        self._scene.settings.set(self.SETTING_ISOLATE_EDIT_MODULE, state)
        
    # -------- Private methods

    def _getContextIdent(self, default=None):
        try:
            return self._scene.sceneItem.readTag(self._TAG_CONTEXT)
        except LookupError:
            pass
        
        return default
        
    def _getContextObject(self, newContext):
        if isinstance(newContext, str):
            try:
                contextObject = service.systemComponent.get(context.Context.sysType(), newContext)
            except LookupError:
                contextObject = None
        elif isinstance(newContext, context.Context):
            contextObject = newContext
        else:
            contextObject = None
    
        if contextObject is None:
            raise TypeError
        return contextObject

    def _leavePreviousContext(self, newContextId=None):
        currentId = self._getContextIdent()
        if currentId is None:
            return
        
        currentContext = service.systemComponent.get(context.Context.sysType(), currentId)
        
        for rig in self._scene.rigs:
            self._resetElements(currentContext, rig)

        if newContextId is None or newContextId != currentId:
            try:
                currentContext.onLeave()
            except AttributeError:
                pass
            try:
                currentContext.onSubcontextLeave()
            except AttributeError:
                pass

    def _setSetupMode(self, contextObject):
        try:
            setupState = contextObject.setup
        except AttributeError:
            return
        if setupState is None:
            return
        setup = SetupMode()
        setup.state = setupState

    def _resetElements(self, context, rig):
        startTime = time.time()
        
        rig.visible = True
        struct = RigStructure(rig.rootItem)
        for component in struct.components:
            component.visible = True

        moduleVisTime = time.time()
        
        # Reset visibility
        # This is done for entire rig.
        elementsVis = context.getElementsVisibilityToProcess()
        for elsetId in list(elementsVis.keys()):
            try:
                elset = rig[elsetId]
            except LookupError:
                continue
            elset.resetVisible()

        resetVisTime = time.time()
        
        # Send an event so others can react.
        service.events.send(c.EventTypes.CONTEXT_RIG_VIS_RESET, context=context, rig=rig)

        # Reset selectability
        elementsSel = self._getElementsSelectabilityToProcess(context)
        for elsetId in list(elementsSel.keys()):
            try:
                elset = rig[elsetId]
            except LookupError:
                continue
            elset.resetSelectable()
        
        endTime = time.time()
        if service.debug.output:
            log.out('Reset Elements time: %f' % (endTime - startTime))
            log.startChildEntries()
            log.out('Module visibility reset time: %f' % (moduleVisTime - startTime))
            log.out('Elements visibility reset time: %f' % (resetVisTime - moduleVisTime))
            log.out('Elements selectability reset time: %f' % (endTime - resetVisTime))
            log.stopChildEntries()
        
    def _setHierarchyVisibility(self, context, rig):
        """ Needs to set visibility not only for hierarchy but also other components.
        
        Hierarchy will be set according to is hierarchy visible, other components need to be set to false.
        And the actual rig to true.
        """
        rig.visible = True
        struct = RigStructure(rig.rootItem)
        for component in struct.components:
            component.visible = False
        
        try:
            vis = context.isHierarchyVisible
        except AttributeError:
            vis = True # Should true really be the default?

        if vis:
            if context.isolateEditModule and self.isolateEditModule:
                editMod = rig.modules.editModule
                if editMod:
                    editMod.visible = True
            else:
                for module in rig.modules.allModules:
                    module.visible = True

    def _setElementsVisibility(self, context, rig):
        elementsVisibility = context.getElementsVisibilityToProcess()

        if context.isolateEditModule and self.isolateEditModule:
            self._setElementsVisibilityForModules(elementsVisibility, rig)
        else:
            self._setElementsVisibilityForRig(elementsVisibility, rig)
        
        # Send an event so others can react.
        service.events.send(c.EventTypes.CONTEXT_RIG_VIS_SET, context=context, rig=rig)

    def _setElementsVisibilityForRig(self, elementsVisibility, rig):
        for elsetId in list(elementsVisibility.keys()):
            value = elementsVisibility[elsetId]
            try:
                elset = rig[elsetId]
            except LookupError:
                continue
            elset.setVisible(value)

    def _setElementsVisibilityForModules(self, elementsVisibility, rig):
        editMod = rig.modules.editModule
        if editMod:
            for elsetId in list(elementsVisibility.keys()):
                value = elementsVisibility[elsetId]
                try:
                    elset = rig[elsetId]
                except LookupError:
                    continue
                # elset is a list of items, not the element set.
                elset.setModuleFilter(editMod)
                elset.setVisible(value)
        else:
            # If there is no edit module just do the entire rig.
            self._setElementsVisibilityForRig(elementsVisibility, rig)

    def _getElementsSelectabilityToProcess(self, context):
        try:
            return context.elementsSelectable
        except AttributeError:
            return {}

    def _setElementsSelectability(self, context, rig):
        elementsSelectability = self._getElementsSelectabilityToProcess(context)
        
        for elsetId in list(elementsSelectability.keys()):
            value = elementsSelectability[elsetId]
            try:
                elset = rig[elsetId]
            except LookupError:
                continue
            elset.setSelectable(value)

    def __init__(self, rsScene):
        if rsScene is None:
            raise TypeError
        self._scene = rsScene