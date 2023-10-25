

import modox

from . import const as c
from .module import Module
from .items.root_item import RootItem
from .items.plug import PlugItem


class ModuleMap(object):
    """ Module map allows for creating and maintaining dependencies between modules.
    
    Parameters
    ----------
    initItem : Module, RootItem
    """
    
    GRAPH_NAME = 'rs.modulesMap'

    def addModuleToMap(self, module):
        """ Adds module to a map.
        
        Module is added as root module by default (is not dependent on any
        other modules).
        """
        modox.ItemUtils.clearForwardGraphConnections(module.rootModoItem, self.GRAPH_NAME)
        modox.ItemUtils.addForwardGraphConnections(module.rootModoItem, self._rigRoot.modoItem, self.GRAPH_NAME)
    
    def addModuleDependency(self, module, targetModule):
        """ Adds dependency between modules.
        
        Module will be dependent on target module.
        It is not stricly parent/child relationship as single module can be
        dependent on multiple other modules (think muscle with two endings,
        each plugged to different module).
        """
        modox.ItemUtils.clearForwardGraphConnections(module.rootModoItem, self.GRAPH_NAME, self._rigRoot.modoItem)
        modox.ItemUtils.addForwardGraphConnections(module.rootModoItem, targetModule.rootModoItem, self.GRAPH_NAME)
    
    def clearModuleDependency(self, module, targetModule=None):
        """ Clears dependency between modules.

        Dependency is cleared ONLY if there are no plugs of a module
        connected to any sockets of the target module!!!!
        
        If module doesn't have any more dependencies it becomes root module.
        """
        if self._isRelatedToTargetModule(module, targetModule):
            return

        if targetModule:
            targetItem = targetModule.rootModoItem
            modox.ItemUtils.clearForwardGraphConnections(module.rootModoItem, self.GRAPH_NAME, [targetItem])
        
        # This should be done only if module is not depenend on any other modules
        if self.isModuleIndependent(module):
            self.addModuleToMap(module)
    
    def isModuleIndependent(self, module):
        """ Tests whether given module is independent.
        
        That means that module is not connected to any other module in the map.
        """
        connections = modox.ItemUtils.getForwardGraphConnections(module.rootModoItem, self.GRAPH_NAME)
        if not connections:
            return True
        if len(connections) == 1 and connections[0] == self._rigRoot.modoItem:
            return True
        return False

    def isModuleDependentOnOtherModule(self, module, otherModule):
        """ Tests if one module is dependent on another module.
        
        A module is dependent on another if all its plugs are connected to the other module.
        In such situation dependent module is considered to be a child one.
        """
        plugsModoItems = module.getElementsFromSet(c.ElementSetType.PLUGS)
        plugs = [PlugItem(modoItem) for modoItem in plugsModoItems]
        for plug in plugs:
            socket = plug.socket
            # If plug is not connected the module cannot be dependent.
            if socket is None:
                return False
            # TODO: We're special casing connecting to base here, think if there's better way to solve it.
            if socket.moduleRootItem.identifier == c.ModuleIdentifier.BASE:
                continue
            if otherModule.rootItem != socket.moduleRootItem:
                return False
        return True

    @property
    def map(self):
        """ Returns modules in dependency order.
        """
        tree = []
        self._traverseMap(self._rigRoot.modoItem, tree)
        modulesMap = [Module(item) for item in tree]
        return modulesMap
    
    def getDependentModules(self, module, recursive=False):
        """ Gets modules that depend on a given module.
        
        Returns
        -------
        list of Module
        """
        dependentModules = []
        if recursive:
            tree = []
            self._traverseDependentModules(module, tree)
            dependentModules = tree
        else:
            moduleRoots = modox.ItemUtils.getReverseGraphConnections(module.rootModoItem, self.GRAPH_NAME)
            modules = [Module(rootModoItem) for rootModoItem in moduleRoots]
            filteredModules = []
            for mod in modules:
                if self.isModuleDependentOnOtherModule(mod, module):
                    filteredModules.append(mod)
            dependentModules = filteredModules
        return dependentModules
    
    # -------- Private methods

    def _traverseMap(cls, modoItem, tree):
        """ Traverses map to find all modules starting with give one.
        
        Parameters
        ----------
        modoItem : modo.Item
            Root of a module that traversal starts with.
            
        tree : list of modo.Item
            Results will be appended to this list.
            The list will be modules root modo items.
        """
        children = modox.ItemUtils.getReverseGraphConnections(modoItem, cls.GRAPH_NAME)
        if children:
            for child in children:
                if child not in tree:
                    tree.append(child)
                cls._traverseMap(child, tree)

    def _traverseDependentModules(self, module, tree):
        """ Traverses map to find all modules dependent on a module that function starts with.
        
        Parameters
        ----------
        module : Module
            The module the traversal starts with.
        
        tree : list of Module
            Results will be appended to the list.
        """
        children = modox.ItemUtils.getReverseGraphConnections(module.rootModoItem, self.GRAPH_NAME)
        if children:
            for child in children:
                childModule = Module(child)
                if self.isModuleDependentOnOtherModule(childModule, module):
                    if child not in tree:
                        tree.append(childModule)
                    self._traverseDependentModules(childModule, tree)

    def _isRelatedToTargetModule(self, module, targetModule):
        """ Tests if a module is related to the target module.
        
        A module is related to another module if there's at least one plug
        that is connected to the target module.
        """
        plugsModoItems = module.getElementsFromSet(c.ElementSetType.PLUGS)
        plugs = [PlugItem(modoItem) for modoItem in plugsModoItems]
        for plug in plugs:
            socket = plug.socket
            if socket is None:
                continue
            if socket.moduleRootItem == targetModule:
                return True # if there is a plug that is connected to the target module.
        return False

    def __init__(self, initItem):
        if isinstance(initItem, Module):
            initItem = initItem.rigRootItem

        try:
            self._rigRoot = RootItem.getFromOther(initItem)
        except TypeError:
            raise
