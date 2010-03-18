# Copyright 2010 Alexander Duryagin
#
# This file is part of NagData.
#
# NagData is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# NagData is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with NagData.  If not, see <http://www.gnu.org/licenses/>.
#

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

class UnsuitableObjGroup(NagDataError):
    """
    Raised when trying to add object with wrong obj_group (not 'config' to
    config collection
    """
    def __init__(self, obj_group, wrong_obj_group):
        self._obj_group = obj_group
        self._wrong_obj_group = wrong_obj_group
    def __str__(self):
        return "Only objects of '%s' group allowed, " + \
                "but given with obj_group='%s'" % \
                (self._obj_group, self._wrong_obj_group)

class NotInConfig(NagDataError):
    """
    File we trying to save object to is not in cfg_dir and not one of cfg_file
    """
    def __init__(self, filename):
        self._filename = filename
    def __str__(self):
        return "Fle '%s' is not in one of config directories and not one of " +\
                "config files" % self._filename

class ConfigNotGiven(NagDataError):
    """
    When load_config, configuration file is not given as parameter and not set
    as object's nagios_cfg attribute.
    """
    pass

