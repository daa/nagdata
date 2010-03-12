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

class NotUnique(NagObjectError):
    """
    Object's primary key is not unique. Raised when trying to add object to
    collection or changing attributes which are part of pkey.
    """
    pass

class NotInConfig(NagDataError):
    """
    File we trying to save object to is not in cfg_dir and not one of cfg_file
    """
    pass

