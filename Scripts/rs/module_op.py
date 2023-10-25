
""" Module operator.

"""


import os.path

import lx
import modo
import modox

from .log import log as log
from .items.root_item import RootItem
from .items.module_root import ModuleRoot
from .items.guide import GuideItem
from .item_features.controller_guide import ControllerGuideItemFeature
from .rig_structure import RigStructure
from .module_map import ModuleMap
from .module import Module
from .module_set import ModuleSet
from .core import service
from .util import run
from . import const as c


class ModuleOperator(object):
    """ Module operator allows for managing modules for the rig.
    
    Parameters
    ----------
    rigRootItem : modo.Item or RootItem

    Attributes
    ----------
    silentDrop : bool
        This is static attribute, don't localize it.
        When it's True dropping module will not execute drop action and will not
        refresh the context. Use this if you want to add modules in controlled way.
    """
    
    GRAPH_MODULES = c.Graph.MODULES
    GRAPH_EDIT_MODULE = c.Graph.EDIT_MODULE
    DEFAULT_MODULE_NAME = 'Module'
    BASE_MODULE_IDENTIFIER = 'base'
    MODULE_BUFFER_ID = 'modLastAdded'

    # -------- Public methods

    def newModule(self, name=None):
        """ Adds new module to the rig the operator runs on.
        """
        name = self._renderUniqueDefaultModuleName(name)
        newModule = Module.new()
    
        rigStructure = RigStructure(self._rigRoot)
        rigStructure.addComponent(newModule)
        
        newModule.name = name # name is set only after module has rig context
        self.editModule = newModule
        service.events.send(c.EventTypes.MODULE_NEW, module=newModule)
        return newModule

    def newModuleFromAssembly(self, assmModoItem, name=None):
        """ Creates new module from an existing setup.
        
        Parameters
        ----------
        assmModoItem : modo.Item
            The assembly item that holds the setup that will be converted
            into a module.
        """
        side = c.Side.CENTER

        if name is None:
            name = self._renderUniqueDefaultModuleName(name)
        
        newModule = Module.new(assemblyModoItem=assmModoItem)
    
        rigStructure = RigStructure(self._rigRoot)
        rigStructure.addComponent(newModule)

        newModule.setup.selfValidate()
        
        newModule.name = name # name is set only after module has rig context
        newModule.side = side

        self.editModule = newModule
        service.events.send(c.EventTypes.MODULE_LOAD_POST, module=newModule)
        return newModule

    def addModuleSet(self, moduleSetToAdd):
        """
        Adds existing module set to the rig.

        Existing module set is a preset that was added to scene but is not added to rig yet.
        Such preset contains multiple modules.
        """
        # In module set the first module is the main one and the rest are submodules.
        # Therefore then adding modules to rig we reverse the order so the main one is added last
        # and will be "seen" as added by the system.
        modules = moduleSetToAdd.modules
        modules.reverse()

        for module in modules:
            self.addModule(module)
        moduleSetToAdd.selfDelete()

    def addModule(self, moduleToAdd):
        """ Adds existing module to the rig.
        """
        if not isinstance(moduleToAdd, Module):
            try:
                moduleToAdd = Module(moduleToAdd)
            except TypeError:
                raise

        rigStructure = RigStructure(self._rigRoot)
        rigStructure.addComponent(moduleToAdd)

        # This is needed to clean up any orphaned transform link connections.
        # TODO: Disabling this for now, it's not needed as all plugs get examined
        # TODO: when dropping module to the rig that has base.
        # moduleToAdd.cleanUpPlugConnections()

        # When module is added to rig its drop script has to be cleared.
        # Otherwise when rig is saved and dropped back the drop script
        # will run again.
        modox.ItemUtils.clearCreateDropScript(moduleToAdd.rootModoItem)

        try:
            moduleToAdd.onAddedToRig()
        except AttributeError:
            pass

        moduleToAdd.name = moduleToAdd.name

        service.buffer.put(moduleToAdd.rootModoItem.id, self.MODULE_BUFFER_ID)
        service.events.send(c.EventTypes.MODULE_LOAD_POST, module=moduleToAdd)
        return moduleToAdd

    def addModuleFromPreset(self, presetFilename):
        """ Adds module from preset.

        The preset will be searched for in 2 paths: modules and internal modules
        (and in that order).

        Parameters
        ----------
        presetFilename : str
            Name of the preset file (without path).
            File extension can be skipped.
        
        Returns
        -------
        Module
        
        Raises
        ------
        LookupError
            When requested module cannot be found or the method failed
            in some other way.
        """
        lowFilename = presetFilename.lower()
        if not lowFilename.endswith('.lxp'):
            presetFilename += '.lxp'

        fullFilename = None
        for path in [c.Path.MODULES, c.Path.MODULES_INTERNAL]:
            try:
                fullFilename = service.path.getFullPathToFile(path, presetFilename)
                break
            except LookupError:
                continue

        if fullFilename is None:
            raise LookupError

        run('preset.do {%s}' % fullFilename)
        try:
            moduleRootItemId = service.buffer.take(self.MODULE_BUFFER_ID)
        except LookupError:
            raise
        try:
            return Module(moduleRootItemId)
        except TypeError:
            raise LookupError
        raise LookupError
        
    def duplicateModule(self, module, name=None):
        """ Duplicates module in the scene.
        
        This is done by saving a module to a temp location and loading
        it back.
        Module has to be one from the rig module op was initialised with.

        Parameters
        ----------
        module : Module

        name : str, optional
            Name for duplicated module.

        Returns
        -------
        Module
            Duplicated module object or None if module could not be duplicated.
        """
        if not self.hasModule(module):
            return None

        service.globalState.ControlledDrop = True

        # Save
        tempPath = service.path.get(c.Path.TEMP_FILES)
        filename = 'TEMP_AssemblyDuplicate.lxp'
        fullpath = os.path.join(tempPath, filename)

        # Saving module has to be done via module op saveModule and not via save module directly
        # because we may need to save entire module set.
        self.saveModule(module, fullpath, captureThumb=False)

        # Load back and clean up
        lx.eval('!preset.do {%s}' % fullpath)
        os.remove(fullpath)

        service.globalState.ControlledDrop = False

        try:
            moduleRootItemId = service.buffer.take(self.MODULE_BUFFER_ID)
        except LookupError:
            return None

        try:
            module = Module(moduleRootItemId)
        except TypeError:
            return None

        if name is not None:
            module.name = name

        return module

    def saveModule(self, module, filename=None, captureThumb=False):
        """
        Saves module as a preset.

        Saving supports module sets and also variants.
        Each variant is saved out as separate preset.
        """
        subModules = module.submodules
        if subModules:
            # save as module set.
            if filename is None:
                filename = module.autoPathAndFilename
            self.saveModuleSet([module] + subModules, filename, captureThumb)
        else:
            module.save(filename, captureThumb)

    def saveModuleSet(self, modules, filename, captureThumb=False, cleanUp=True):
        """
        Saves multiple modules as a single preset.

        Parameters
        ----------
        modules : [Module]
            List of modules to save in the set.

        filename : str
            Full filename including path.

        captureThumb : bool
            When True module set will be saved with a thumb.

        cleanUp : bool
            Saving modules as set requires destructive changes to the scene.
            These changes have to be cleaned up unless you're saving module set
            from a command that does an undo step when done automatically.
        """
        modSet = ModuleSet.new()
        # Parent all modules quickly.
        assmItem = modSet.assemblyModoItem
        parentCache = []
        for module in modules:
            # Be sure to send module save pre event!
            service.events.send(c.EventTypes.MODULE_SAVE_PRE, module=module)
            if cleanUp:
                parentCache.append((module.assemblyModoItem, module.assemblyModoItem.parent))
            modox.Assembly.addSubassembly(module.assemblyModoItem, assmItem)
        modSet.save(filename, captureThumb)

        if cleanUp:
            for entry in parentCache:
                modox.Assembly.addSubassembly(entry[0], entry[1])
            modSet.selfDelete()

        # Don't forget about post event for each module too!
        for module in modules:
            service.events.send(c.EventTypes.MODULE_SAVE_POST, module=module)

    def clearSymmetry(self, module):
        """
        Clears symmetry setting for a given module.

        Parameters
        ----------
        module : Module
            Module to clear symmetry for.
        """
        guides = module[c.ElementSetType.GUIDES]
        for modoItem in guides:
            try:
                guideCtrl = ControllerGuideItemFeature(modoItem)
            except TypeError:
                continue
            guideCtrl.item.symmetricGuide = None

        module.symmetricModule = None

    def setSymmetry(self, module, refModule):
        """ Sets symmetry between two modules.
        
        Parameters
        ----------
        module : Module
            Module to which symmetry will be applied.
        
        refModule : Module
            Reference module which will be the source of transforms to mirror.
        """
        # Modules have to be the same type of module.
        #if module.ident != refModule.ident:
            #log.out("Cannot set symmetry between two different modules!", log.MSG_ERROR)
            #return False

        if not self._areOppositeSides(module.side, refModule.side):
            log.out('Symmetry can be set only between modules that are on opposite sides', log.MSG_ERROR)
            return False

        # Create dictionaries of guides keyed by their names.
        # This way it'll be easy to match them.
        # We only care about matching controller guides.
        sourceGuides = self._createCtrlGuidesDictByIdents(refModule[c.ElementSetType.GUIDES])
        targetGuides = self._createCtrlGuidesDictByIdents(module[c.ElementSetType.GUIDES])

        # Now we iterate through all target module guides.
        for name in list(targetGuides.keys()):
            if name not in list(sourceGuides.keys()):
                continue
            if not self._areOppositeSides(sourceGuides[name].side, targetGuides[name].side):
                continue
            targetGuides[name].symmetricGuide = sourceGuides[name]

        module.symmetricModule = refModule

    def hasModule(self, module):
        """ Tests whether given module belongs to this rig.
        """
        for m in self.allModules:
            if module == m:
                return True
        return False

    def getModuleByName(self, name):
        """
        Gets first module that fits given name.
        Side is not tested so it really works best for center modules.

        Returns
        -------
        Module, None
        """
        for m in self.allModules:
            if m.name == name:
                return m
        return None

    def getModuleByReferenceName(self, refName):
        """
        Gets first module with given reference name.

        Returns
        -------
        Module, None
        """
        for m in self.allModules:
            if m.referenceName == refName:
                return m
        return None

    def getFeaturedModule(self, identifier):
        """
        Gets feature module by its identifier.

        Parameters
        ----------
        identifier : str
            This is the identifier under which featured module is registered in a system.

        Returns
        -------
        FeaturedModule, Module, None
            If module with given identifier is in the rig but it does not have featured module class
            registered the object will be returned as default Module.
        """
        for m in self.allModules:
            if m.identifier == identifier:
                try:
                    featuredModuleClass = service.systemComponent.get(c.SystemComponentType.FEATURED_MODULE, identifier)
                    return featuredModuleClass(m)
                except LookupError:
                    return m
        return None

    @property
    def allModules(self):
        """ Gets a list of all modules in the rig.
        
        Returns
        -------
        list of Module
        """
        graph = self._rigRoot.modoItem.itemGraph(self.GRAPH_MODULES)
        moduleRoots = graph.reverse()

        modules = []
        for root in moduleRoots:
            modules.append(Module(root))
        return modules

    @property
    def allModulesByReferenceNames(self):
        """
        Gets all the modules keyed by their reference names.

        It's possible that multiple modules have the same reference name therefore
        modules are returned in lists under each reference name.

        Returns
        -------
        {str: [Module]}
            Gets dictionary where module reference name is a key and list of modules
            with that key is a value.
        """
        modulesByReferenceNames = {}
        for module in self.allModules:
            refName = module.referenceName
            if refName not in modulesByReferenceNames:
                modulesByReferenceNames[refName] = []

            modulesByReferenceNames[refName].append(module)
        return modulesByReferenceNames

    @property
    def firstModule(self):
        """
        Gets first module that's on the list of modules.

        It's not alphabetical, just picks the first module link available.

        Returns
        -------
        Module, None
            None is returned when rig has no modules.
        """
        graph = self._rigRoot.modoItem.itemGraph(self.GRAPH_MODULES)
        try:
            moduleRoot = graph.reverse(0)
        except LookupError:
            return None
        return Module(moduleRoot)

    @property
    def baseModule(self):
        """ Returns base module for the rig.
        
        Returns
        -------
        Module, None
            Base module or None if rig doesn't have one.
        """
        for module in self.allModules:
            if str(module.identifier).lower() == self.BASE_MODULE_IDENTIFIER:
                return module
        return None
        
    @property
    def editModule(self):
        """ Returns current edit module.

        Returns
        -------
        Module
            Returns module set as edit module, first module on graph link list
            if edit module is not set explicitly or None if there are no modules in the rig.
        """
        graphRigRootItem = self._rigRoot.modoItem.itemGraph(self.GRAPH_EDIT_MODULE)
        connectedItems = graphRigRootItem.forward()
        if not connectedItems or len(connectedItems) == 0:
            return self.firstModule

        return Module(connectedItems[0])

    @editModule.setter
    def editModule(self, mod):
        """ Sets new edit module.
        
        Parameters
        ----------
        newEditModule : Module, ModuleRoot, modo.Item, str
            Either module object itself, module root rig item, 
            module root modo item or scene identifier string.
        """
        if not isinstance(mod, Module):
            try:
                mod = Module(mod)
            except TypeError:
                return False

        # Don't change anything if given module is the same as current edit one.
        if self.editModule == mod:
            return
        
        graphRigRootItem = self._rigRoot.modoItem.itemGraph(self.GRAPH_EDIT_MODULE)
        graphModuleRootItem = mod.rootModoItem.itemGraph(self.GRAPH_EDIT_MODULE)

        # Delete any existing forward connections from rig.
        for item in graphRigRootItem.forward():
            item.itemGraph(self.GRAPH_EDIT_MODULE) << graphRigRootItem

        graphRigRootItem >> graphModuleRootItem

        return True

    @property
    def modulesMap(self):
        """ Gets modules map for a rig.
        
        Returns
        -------
        ModuleMap
        """
        return ModuleMap(self._rigRoot)

    # -------- Private methods

    def _areOppositeSides(self, side1, side2):
        if side1 == c.Side.LEFT and side2 == c.Side.RIGHT:
            return True
        elif side1 == c.Side.RIGHT and side2 == c.Side.LEFT:
            return True
        return False

    def _createCtrlGuidesDictByIdents(self, guidesList):
        """ Gets a dictionary of controller guides assigned by their idents or names.
        
        Returns
        -------
        dict of GuideItem
        """
        d = {}
        for item in guidesList:
            try:
                ctrlGuide = ControllerGuideItemFeature(item)
            except TypeError:
                continue

            guide = ctrlGuide.item
            key = guide.name # TODO: This should be name or alias - once controller alias is introduced
            
            if key:
                d[key] = guide
        return d

    def _renderUniqueDefaultModuleName(self, name=None):
        names = [module.name for module in self.allModules]
        if name and name not in names:
            return name

        prefix = self.DEFAULT_MODULE_NAME
        maxModules = 100
        defaultName = prefix
        for x in range(1, maxModules):
            defaultName = prefix + str(x)
            if defaultName in names:
                continue
            break
        return defaultName

    def __init__ (self, rigRootItem):
        if isinstance(rigRootItem, modo.Item):
            try:
                rigRootItem = RootItem(rigRootItem)
            except TypeError:
                raise
        if not isinstance(rigRootItem, RootItem):
            raise TypeError
        self._rigRoot = rigRootItem
