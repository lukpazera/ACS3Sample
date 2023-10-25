

from . import const as c


class EventHandler(object):
    """ This class is used to implement handling events.
    
    Event handler is a persistent object that is instantiated upon
    rigging system initialisation.
    
    When an event of a given type is sent the system will iterate
    through all event handlers and will try to call appropriate event handling
    funciton from each handler.
    
    Attributes
    ----------
    descIdentifier : str
        Unique identifier for this handler.
    
    descUsername : str
        Username that will be printed out in logs, etc.
    """
    
    descIdentifier = ''
    descUsername = ''
    
    @property
    def eventCallbacks(self):
        """ Defines what event types are handled by this handler.

        This property needs to return a dictionary of event type code/callback pairs.
        When parsing an event system will query this property to see if an event
        has a callback assigned and if it has - it'll call it.
        """
        return {}
    
    # -------- Private methods
    
    def __init__(self):
        try:
            self.init()
        except AttributeError:
            pass
