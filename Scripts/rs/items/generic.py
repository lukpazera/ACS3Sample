
""" Generic rig item module.

    Generic item can be applied to any modo item, it adds
    a set of generic rig properties.

    Copyright (C) 2017-2019 Lukasz Pazera.
"""


import lx
import modo
from modox import ItemUtils

from .. import item
from .. import const as c


class GenericItem(item.Item):
    
    SUBTYPE_JOINT = 'joint'

    descType = c.RigItemType.GENERIC
    descUsername = 'Generic Item'
    descModoItemType = 'locator'
    descFixedModoItemType = False
    descDefaultName = 'Item'
    descPackages = ['rs.pkg.generic']
    descItemCommand = c.ItemCommand.GENERIC
    descDropScriptSource = c.DropScript.ITEM_ON_ITEM_SOURCE
    descDropScriptDestination = c.DropScript.ITEM_ON_ITEM_DESTINATION

    def onAdd(self, subtype):
        if subtype != self.SUBTYPE_JOINT:
            return

        modoItem = self.modoItem
        ident = modoItem.id

        #ItemUtils.autoPlaceInChain(modoItem, modo.Vector3(0.0, 0.0, 0.2))

        if not modoItem.internalItem.PackageTest("glItemShape"):
            modoItem.PackageAdd("glItemShape")

        if not modoItem.internalItem.PackageTest("glLinkShape"):
            modoItem.PackageAdd("glLinkShape")

        # Set shape
        lx.eval('!channel.value custom channel:{%s:drawShape}' % ident)
        lx.eval('!channel.value circle channel:{%s:isShape}' % ident)
        lx.eval('!channel.value true channel:{%s:isAlign}' % ident)
        lx.eval('!channel.value 0.005 channel:{%s:isRadius}' % ident)

        # Set link shape
        lx.eval('!channel.value custom channel:{%s:link}' % ident)
        lx.eval('!channel.value box channel:{%s:lsShape}' % ident)
        lx.eval('!channel.value true channel:{%s:lsSolid}' % ident)
        lx.eval('!channel.value true channel:{%s:lsAuto}' % ident)


class GenericGroupLocator(GenericItem):
    """ This is the generic item really, it's just a variant built on group locator.
    """
    
    descModoItemType = 'groupLocator'