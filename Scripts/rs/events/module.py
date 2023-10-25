
""" Events concering modules.

    Copyright (C) 2017-2019 Lukasz Pazera.
"""


import rs.event
import rs.const as c


class EventModuleNew(rs.event.Event):
    """ Event sent after new module is created.

    Callback
    --------
    module : Module
        Callback takes single argument which is module that was created.
    """
    descType = c.EventTypes.MODULE_NEW
    descUsername = 'Module New'


class EventModuleLoadPost(rs.event.Event):
    """ Event sent after module was loaded and merged with the rig.

    Callback
    --------
    module : Module
        Callback takes single argument which is module that was loaded.
    """
    descType = c.EventTypes.MODULE_LOAD_POST
    descUsername = 'Module Post Load'


class EventModuleDropActionPre(rs.event.Event):
    """ Event sent right before module drop action is going to be applied (if any).

    Callback
    --------
    module : Module
    action : rs.c.ModuleDropAction.XXX
    position : modo.Vector3
        Callback takes 3 arguments, a module that was loaded,
        a drop action that will be performed on this module
        and the position at which module will be dropped.
    """
    descType = c.EventTypes.MODULE_DROP_ACTION_PRE
    descUsername = 'Module Pre Drop Action'


class EventModuleDropActionPost(rs.event.Event):
    """ Event sent after module drop action was applied.

    Note that this event is called ONLY if one of drop actions actually happened.

    Callback
    --------
    module : Module
    action : rs.c.ModuleDropAction.XXX
    position : modo.Vector3
        Callback takes 3 arguments, a module that was loaded,
        a drop action that was already performed on this module
        and the position at which module was dropped.
    """
    descType = c.EventTypes.MODULE_DROP_ACTION_POST
    descUsername = 'Module Post Drop Action'


class EventModuleSavePre(rs.event.Event):
    """ Event to send when module is about to be saved.

    Callback
    --------
    module : Module
        Callback takes single argument which is module that is about to be saved.
    """
    descType = c.EventTypes.MODULE_SAVE_PRE
    descUsername = 'Module Pre Save'


class EventModuleSavePost(rs.event.Event):
    """ Event sent right after module was saved.

    Callback
    --------
    module : Module
        Callback takes single argument which is module that was saved.
    """
    
    descType = c.EventTypes.MODULE_SAVE_POST
    descUsername = 'Module Post Save'


class EventModuleDeletePre(rs.event.Event):
    """ Event sent right before module is deleted.

    Callback
    --------
    module : Module
        Callback takes a single argument that is the module about to be deleted.
    """

    descType = c.EventTypes.MODULE_DELETE_PRE
    descUsername = 'Module Pre Delete'


class EventModuleNameChanged(rs.event.Event):
    """ Event sent when module name was changed.

    Callback
    --------
    module : Module
        Module which name has changed.

    oldName : str
        Old module name.

    newName : str
        New module name.
    """

    descType = c.EventTypes.MODULE_NAME_CHANGED
    descUsername = 'Module Name Changed'


class EventPlugConnected(rs.event.Event):
    """ Event sent after a plug was connected to a socket.

    Callback
    --------
    plug : PlugItem
    socket : SocketItem
        Callback takes two arguments, a plug that was connected and a socket the plug was connected to.
    """
    descType = c.EventTypes.PLUG_CONNECTED
    descUsername = 'Plug Connected'


class EventPlugDisconnected(rs.event.Event):
    """ Event sent after a plug was disconnected from a socket.

    Callback
    --------
    plug : PlugItem
    socket : SocketItem
        Callback takes two arguments, a plug that was disconnected and a socket the plug was disconnected from.
    """
    descType = c.EventTypes.PLUG_DISCONNECTED
    descUsername = 'Plug Disconnected'


class EventPieceNew(rs.event.Event):
    """ Event sent after new piece was created.

    Callback
    --------
    piece : Piece
        Callback takes single argument which is piece that was created.
    """
    descType = c.EventTypes.PIECE_NEW
    descUsername = 'Piece New'


class EventPiecePreSave(rs.event.Event):
    """ Event sent before piece is saved.

    Callback
    --------
    piece : Piece
        Callback takes single argument which is piece will be saved.
    """
    descType = c.EventTypes.PIECE_SAVE_PRE
    descUsername = 'Piece Pre Save'


class EventPieceLoadPost(rs.event.Event):
    """ Event sent after piece assembly was added to a module.

    Callback
    --------
    piece : Piece
        Callback takes single argument which is piece that was loaded.
    """
    descType = c.EventTypes.PIECE_LOAD_POST
    descUsername = 'Piece Post Load'
