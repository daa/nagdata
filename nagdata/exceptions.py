"""
Nagdata exceptions
"""

class NagDataError(Exception):
    pass

class NagiosSyntaxError(NagDataError):
    """
    Syntax error while parsing config or status file
    """
    pass

class NagObjectError(NagDataError):
    """
    Error when working with objects
    """
    pass

class NotFound(NagObjectError):
    """
    Nagios object not found
    """
    pass

class TooMany(NagObjectError):
    """
    Too many objects found while trying get only one
    """
    pass

class AlreadyExists(NagObjectError):
    """
    Object we trying to add already exists in collection
    """
    pass

