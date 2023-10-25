

import lx
import modo
import modox

import rs.context
from ..util import run
from ..const import ElementSetType as e
from ..const import ItemVisible as v
from ..const import TriState as t
from ..const import Context as cxt
from ..scene import Scene
from ..items.bind_mesh import BindMeshItem
from .. import const as c
from ..rig import Rig


class ContextWeight(rs.context.Context):
    
    descIdentifier = cxt.WEIGHT
    descUsername = 'Form'
    descSubcontexts = [c.FormSubcontexts.BIND, c.FormSubcontexts.WEIGHT]
    descDefaultSubcontext = c.FormSubcontexts.BIND

    @property
    def setup(self):
        """ Going to bind subcontext switches to setup, don't change setup otherwise.
        """
        if self.subcontext == c.FormSubcontexts.BIND:
            return True
        return None

    edit = True
    isHierarchyVisible = False

    elementsVisible = {e.BIND_SKELETON: True,
                       e.RESOLUTION_BIND_MESHES: True}
    
    elementsSelectable = {e.BIND_SKELETON: t.ON,
                          e.RESOLUTION_BIND_MESHES: t.ON}

    def refreshOnSubcontextChange(self, previous, new):
        if previous == c.FormSubcontexts.BIND or new == c.FormSubcontexts.BIND:
            return True
        return False
    
    def onSet(self):
        # select all bind meshes
        editRig = Rig(Scene.getEditRigRootItemFast())
        if editRig is not None:
            # Select all bind meshes to make them active.
            # Restore selection afterwards.
            currentBindMeshes = editRig[e.RESOLUTION_BIND_MESHES].elements
            scene = modo.Scene()
            bkpSelection = scene.selected
            scene.select(currentBindMeshes)
            scene.select(bkpSelection)
        
        allBindMeshes = editRig[e.BIND_MESHES].elements
        self._setBindMeshesDrawing(allBindMeshes)
        self._setBindMeshesBoundingBoxDrawing(allBindMeshes, True)

    def onLeave(self):
        editRig = Rig(Scene.getEditRigRootItemFast())
        allBindMeshes = editRig[e.BIND_MESHES].elements
        self._resetBindMeshesDrawing(allBindMeshes)
        self._setBindMeshesBoundingBoxDrawing(allBindMeshes, False)

    def onRefresh(self):
        self.onLeave()
        self.onSet()

    # -------- Private methods
    
    def _setBindMeshesDrawing(self, bindMeshesList):
        if self.subcontext == c.FormSubcontexts.BIND:
            
            for modoItem in bindMeshesList:
                try:
                    bmesh = BindMeshItem(modoItem)
                except TypeError:
                    continue
                if bmesh.isBound:
                    continue
                run('!item.channel locator$style wire item:{%s}' % (modoItem.id))

    def _resetBindMeshesDrawing(self, bindMeshesList):
        for modoItem in bindMeshesList:
            run('!item.channel locator$style default item:{%s}' % (modoItem.id))

    def _setBindMeshesBoundingBoxDrawing(self, bmeshes, state):
        for modoItem in bmeshes:
            modoItem.channel('rsbmDraw').set(state, time=0.0, action=lx.symbol.s_ACTIONLAYER_SETUP)