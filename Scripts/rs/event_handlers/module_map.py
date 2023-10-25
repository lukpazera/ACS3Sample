
""" Event handler for modules map.

    Copyright (C) 2017-2019 Lukasz Pazera.
"""


import modo

from ..event_handler import EventHandler
from ..const import EventTypes as e
from ..const import Context as cxt
from ..log import log
from ..module_map import ModuleMap
from ..module_op import ModuleOperator
from ..module import Module
from ..scene import Scene


class ModulesMapEventHandler(EventHandler):
    """ Handles events concerning modules.
    """

    descIdentifier = 'modmap'
    descUsername = 'Modules Map'
  
    @property
    def eventCallbacks(self):
        return {e.MODULE_NEW: self.event_moduleLoadPost,
                e.MODULE_LOAD_POST: self.event_moduleLoadPost,
                e.PLUG_CONNECTED: self.event_plugConnected,
                e.PLUG_DISCONNECTED: self.event_plugDisconnected,
                e.RIG_ITEM_SELECTED: self.event_rigItemSelected
                }

    def event_moduleLoadPost(self, **kwargs):
        """ Called after new module was created or a module was loaded and added to rig.
        """
        try:
            module = kwargs['module']
        except KeyError:
            return

        modMap = ModuleMap(module)
        modMap.addModuleToMap(module)
        modulesList = modMap.map
        self._updateModulesItemListOrder(modulesList)

    def event_plugConnected(self, **kwargs):
        """ Called after plug was connected to a socket.
        """
        try:
            plug = kwargs['plug']
        except KeyError:
            return

        try:
            socket = kwargs['socket']
        except KeyError:
            return

        module = Module(plug.moduleRootItem)
        targetModule = Module(socket.moduleRootItem)

        modMap = ModuleMap(plug.rigRootItem)
        modMap.addModuleDependency(module, targetModule)
        modulesList = modMap.map
        self._updateModulesItemListOrder(modulesList)
    
    def event_plugDisconnected(self, **kwargs):
        """ Called after plug was disconnected from a socket.
        """
        try:
            plug = kwargs['plug']
        except KeyError:
            return

        try:
            socket = kwargs['socket']
        except KeyError:
            return

        module = Module(plug.moduleRootItem)
        targetModule = Module(socket.moduleRootItem)
    
        modMap = ModuleMap(plug.rigRootItem)
        modMap.clearModuleDependency(module, targetModule)
        modulesList = modMap.map
        self._updateModulesItemListOrder(modulesList)
    
    def event_rigItemSelected(self, **kwargs):
        """ Called when rig item was selected.
        """
        rigItem = kwargs['item']
        rsScene = Scene()
        
        if rsScene.contexts.current not in [cxt.ASSEMBLY, cxt.GUIDE]:
            return
            
        modRootItem = rigItem.moduleRootItem
        if modRootItem is None:
            return
        try:
            mod = Module(modRootItem)
        except TypeError:
            return
        try:
            op = ModuleOperator(mod.rigRootItem)
        except TypeError:
            return
        op.editModule = mod
        
    # -------- Private methods
    
    def _updateModulesItemListOrder(self, modulesList):
        for x in range(len(modulesList)):
            modulesList[x].setItemListOrder(x)
        