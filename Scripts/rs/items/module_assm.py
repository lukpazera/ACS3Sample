
""" Module assembly item.

    Copyright (C) 2017-2019 Lukasz Pazera.
"""


import lx
from ..item import Item
from ..const import *
from ..component_setups.module import ModuleComponentSetup
from ..items.module_root import ModuleRoot


class ModuleAssembly(Item):
    
    descType = RigItemType.MODULE_ASSM
    descUsername = 'Module Assembly Item'
    descModoItemType = 'group'
    descModoItemSubtype = 'assembly'
    descDefaultName = 'Module Assembly'
    descPackages = []

    # -------- Public interface

    def onAdd(self, subtype):
        lx.eval('select.item {%s} set' % self.modoItem.id)
        lx.eval('item.editorColor white')
        
    @property
    def name(self):
        """ Gets module assembly name.
        
        Module assembly doesn't have its own name, it takes it from module.
        """
        try:
            modSetup = ModuleComponentSetup(self.modoItem)
        except TypeError:
            return ''
        modRoot = ModuleRoot(modSetup.rootModoItem)
        return modRoot.name

    @name.setter
    def name(self, name):
        pass