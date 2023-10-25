

import lx
import modo
import modox

from ..item_mesh import MeshItem
from ..item_mesh import MeshItemResolutionsEventHandler
from .. import const as c
from ..log import log
from ..util import run
from ..bind_map import BindMap


class BindMeshItem(MeshItem):

    descType = c.RigItemType.BIND_MESH
    descUsername = 'Bind Mesh'
    descDefaultName = 'BindMesh'
    descPackages = ['glDraw', 'rs.pkg.bindMesh']
    descSynthName = False
    descDropScriptSource = c.DropScript.ITEM_ON_ITEM_SOURCE
    descDropScriptDestination = c.DropScript.ITEM_ON_ITEM_DESTINATION

    _BOUND_MESHES_GRAPH = 'rs.boundMeshes'

    def onAdd(self, subtype):
        modoItem = self.modoItem
        ident = modoItem.id
        
        run('!item.channel locator$wireColor {0.5225 0.5225 0.5225} item:{%s}' % ident)

    @property
    def isBound(self):
        """ Tests whether the mesh is already bound to the rig.
        
        Returns
        -------
        bool
        """
        sysVer = self.rigSystemVersion
        if sysVer > 0:
            connections = modox.ItemUtils.getForwardGraphConnections(self.modoItem, self._BOUND_MESHES_GRAPH)
            if not connections:
                return False
            return True
        else:
            return modox.DeformedItem(self.modoItem).isDeformed

    @isBound.setter
    def isBound(self, state):
        """
        Set bind mesh item as bound or unbound.

        Parameters
        ----------
        bool
        """
        rigRoot = self.rigRootItem
        if rigRoot is None:
            return
        if state:
            modox.ItemUtils.addForwardGraphConnections(self.modoItem, rigRoot.modoItem, self._BOUND_MESHES_GRAPH)
        else:
            modox.ItemUtils.clearForwardGraphConnections(self.modoItem, self._BOUND_MESHES_GRAPH)

    @property
    def deformerModoItems(self):
        """ Gets a list of deformers affecting this mesh.

        Returns
        -------
        list of modo.Item
        """
        return modox.DeformedItem(self.modoItem).deformers

    @property
    def effectorsModoItems(self):
        """ Gets a list of items that are driving deformers affecting this bind mesh.
        
        Returns
        -------
        list of modo.Item
            Empty list is returned when this mesh is not affected by any effectors.
        """
        deformedItem = modox.DeformedItem(self.modoItem)
        effectors = []
        for modoItem in deformedItem.deformers:
            try:
                deformer = modox.Deformer(modoItem)
            except TypeError:
                continue
            effModoItem = deformer.effector
            if effModoItem is not None:
                effectors.append(effModoItem)
        return effectors

    @property
    def bindMap(self):
        return self._getBindMap()
    
    def init(self):
        self.__bmap = None
    
    # -------- Private methods

    def _getBindMap(self):
        if self.__bmap is None:
            self.__bmap = BindMap(self)
        return self.__bmap
    

class BindMeshEventHandler(MeshItemResolutionsEventHandler):
    """
    Event handler for updating item mesh resolution data.
    """
    descIdentifier = 'bmeshmres'
    descUsername = 'Bind Mesh Resolutions'
    descElementSet = c.ElementSetType.BIND_MESHES