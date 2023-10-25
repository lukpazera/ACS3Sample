
""" Events operator.

    This module is used to register and dispatch events.
        
    Copyright (C) 2017-2019 Lukasz Pazera.
"""

from collections import Iterable

import lx

from .log import log as log
from .debug import debug


class EventsOperator (object):
    """ Registers and dispatches events.
    """

    def registerEvent(self, eventClass):
        """ Registers new event.
        
        Parameters
        ----------
        eventClass : Event
            Class presenting Event interface.
        """
        eventType = eventClass.descType
        
        if eventType in self._events:
            if debug.output:
                log.out('%s event type already registered!' % eventType, log.MSG_ERROR)
            return

        self._events[eventType] = eventClass
        
        if debug.output:
            log.out("Event type registered: %s" % eventClass.getUsernameOrType(), log.MSG_INFO)

    def registerHandler(self, eventHandlerClass):
        """ Registers event handler.

        Registered event handler class will be instantiated and its interface will
        be queried for callbacks when various events happen.
        
        Parameters
        ----------
        eventHandlerClass : EventHandler
        """
        if eventHandlerClass.descIdentifier in self._eventHandlers:
            if debug.output:
                log.out('Even handler with the same id has already been registered!', log.MSG_ERROR)
            return False
        
        self._eventHandlers[eventHandlerClass.descIdentifier] = eventHandlerClass()
        if debug.output:
            log.out('Event handler subscribed: %s' % eventHandlerClass.descUsername)
        return True

    @property
    def eventsCount(self):
        """ Gets number of registered event classes.
        """
        return len(self._events)
    
    @property
    def handlersCount(self):
        """ Gets number of registered event handlers.
        """
        return len(self._eventHandlers)

    def send(self, eventType, **kwargs):
        """ Sends an event of a given type.
        
        Parameters
        ----------
        eventType : str
            Type of an event to send.
        
        **kwargs : dict
            Keyword arguments required by the event. This will be different for different events.
            Lookup information in the given event interface.
        """
        for eventHandler in list(self._eventHandlers.values()):
            try:
                callback = eventHandler.eventCallbacks[eventType]
            except KeyError:
                continue
            callback(**kwargs)

    # -------- Private methods

    def __init__ (self):
        self._events = {}
        self._eventHandlers = {}
