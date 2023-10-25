
import lx

from ..context import Context
from ..context import ContextElementStatesDesc
from .. import const as c
from ..util import run
from ..const import ElementSetType as e
from ..const import ItemVisible as v
from ..const import TriState as t
from ..const import Context as cxt
from ..core import service


class ContextAssembly(Context):
    
    SETTINGS_GROUP = 'asmCxt'
    SETTING_DEV_MODE = 'dev'

    SET_HIERARCHY = 'hrch'
    SET_CONTROLLERS = 'ctrl'
    SET_BIND_SKELETON = 'bskel'
    SET_GUIDES = 'guide'
    SET_CONNECTORS = 'connect'

    TO_VIS = {True: v.YES, False: v.NO}

    # -------- Attributes and properties

    descIdentifier = cxt.ASSEMBLY
    descUsername = 'Assemble'
    descSubcontexts = [c.AssemblySubcontexts.DEVELOP, c.AssemblySubcontexts.ASSEMBLY, c.AssemblySubcontexts.GENERAL]
    descDefaultSubcontext = c.AssemblySubcontexts.ASSEMBLY
    
    enable = True
    setup = True
    edit = True
    isolateEditModule = True 

    @property
    def isHierarchyVisible(self):
        """ Returns whether rig hierarchy should be visible or not.
        
        Hierarchy can only be visible in development mode, otherwise it's hidden.
        """
        if self.subcontext == c.AssemblySubcontexts.DEVELOP:
            return self.readHierarchyVisibility()
        else:
            return False

    def readHierarchyVisibility(self):
        return self.settings.getFromGroup(self.SETTINGS_GROUP, self.SET_HIERARCHY, True)
        
    def storeHierarchyVisibility(self, state):
        """ Sets hierarchy visible to a given value and stores that in the scene.
        
        This is special property to handle hierarchy visibility in assembly context.
        This could be turned into general toggle if other contexts need that.
        """
        self.settings.setInGroup(self.SETTINGS_GROUP, self.SET_HIERARCHY, state)
    
    @property
    def elementsVisibleToggle(self):
        """ These elements can be toggled via UI.

        For toggleable sets elementsVisible define default values.
        """
        dev = [e.CONTROLLERS, e.BIND_SKELETON, e.GUIDES, e.PLUGS, e.SOCKETS]
        rig = [e.CONTROLLERS, e.BIND_SKELETON, e.PLUGS, e.SOCKETS]
        
        return {c.AssemblySubcontexts.DEVELOP: dev,
                c.AssemblySubcontexts.GENERAL: rig}

    @property
    def elementsVisible(self):
        """ Gets a dictionary of element set id/visibility value pairs.
    
        Visibility settings depend on development mode.
        In dev mode settings that can be changed by user on per element set basis.
        Settings are stored as booleans
        and need to be converted to visibility values on the fly.
        
        Note that due to the way context refresh works in both cases (in and out of
        development mode) returned dictionary needs to have the same element sets included!
        """
        generic = ContextElementStatesDesc(
            {e.CONTROLLERS: False,
             e.BIND_SKELETON: True,
             e.GUIDES: False,
             e.PLUGS: True,
             e.SOCKETS: True,
             e.RESOLUTION_BIND_MESHES: True,
             e.RESOLUTION_RIGID_MESHES: True,
             e.RESOLUTION_BIND_PROXIES: True})

        dev = ContextElementStatesDesc(
            {e.CONTROLLERS: True,
             e.BIND_SKELETON: True,
             e.GUIDES: True,
             e.PLUGS: True,
             e.SOCKETS: True,
             e.RESOLUTION_BIND_MESHES: True,
             e.RESOLUTION_RIGID_MESHES: True,
             e.RESOLUTION_BIND_PROXIES: True},
             subcontext=c.AssemblySubcontexts.DEVELOP)

        rig = ContextElementStatesDesc(
            {e.CONTROLLERS: True,
             e.BIND_SKELETON: True,
             e.GUIDES: False,
             e.PLUGS: True,
             e.SOCKETS: True,
             e.RESOLUTION_BIND_MESHES: True,
             e.RESOLUTION_RIGID_MESHES: True,
             e.RESOLUTION_BIND_PROXIES: True},
             subcontext=c.AssemblySubcontexts.GENERAL)
        
        return [generic, dev, rig]
    
    @property
    def elementsSelectable(self):
        """ Selectability depends on development mode.
        
        In dev mode all items can be selected, some of them are locked otherwise.
        Note that in both cases returned dictionary has the same element sets included!
        """
        subcontext = self.subcontext
        if subcontext == c.AssemblySubcontexts.GENERAL:
            return {e.BIND_SKELETON: t.DEFAULT,
                    e.CONTROLLERS: t.DEFAULT,
                    e.BIND_MESHES: t.OFF,
                    e.RIGID_MESHES: t.OFF,
                    e.BIND_PROXIES: t.OFF}
        elif subcontext == c.AssemblySubcontexts.DEVELOP:
            return {e.BIND_SKELETON: t.DEFAULT,
                    e.CONTROLLERS: t.DEFAULT,
                    e.BIND_MESHES: t.DEFAULT,
                    e.RIGID_MESHES: t.DEFAULT,
                    e.BIND_PROXIES: t.DEFAULT}
        else:
            return {e.BIND_SKELETON: t.DEFAULT,
                    e.CONTROLLERS: t.OFF,
                    e.BIND_MESHES: t.OFF,
                    e.RIGID_MESHES: t.OFF,
                    e.BIND_PROXIES: t.OFF}            

    @property
    def developmentMode(self):
        return self.subcontext == c.AssemblySubcontexts.DEVELOP

    def refreshOnSubcontextChange(self, previous, new):
        return True

    def onSet(self):
        run('!view3d.overlay true')
