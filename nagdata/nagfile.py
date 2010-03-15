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
Nagios file with objects.

"""

from parser import ObjectParser, StatusParser, ConfigParser
from factory import NagiosFactory
from exceptions import NagiosSyntaxError
import model

class NagFile(object):
    """
    Base class to link nagios files and parser to retrieve objects
    """

    def __init__(self, filename, parser):
        self.filename = filename
        self.parser = parser

    def parse(self, add_file_info=False):
        """
        Parse lines and return list of kw (it also has obj_type which should be
        removed when creating object)
        """
        f = open(self.filename)
        try:
            if add_file_info:
                c = self.parser.parse(f.read(), add_pos=True,
                        add_attrs={'__filename': self.filename})
            else:
                c = self.parser.parse(f.read())
        except NagiosSyntaxError, e:
            f.close()
            raise NagiosSyntaxError("File \"%s\": %s" % (self.filename, str(e)))
        f.close()
        return c

class NagObjectFile(NagFile):
    """
    Handle nagios object file
    """

    def __init__(self, filename, factory=NagiosFactory):
        super(NagObjectFile, self).__init__(filename, ObjectParser(factory))

class NagStatusFile(NagFile):
    """
    Handle nagios status file
    """

    def __init__(self, filename, factory=NagiosFactory):
        super(NagStatusFile, self).__init__(filename, StatusParser(factory))

class NagConfigFile(NagStatusFile):
    """
    Parse nagios.cfg file
    """

    def __init__(self, filename, factory=NagiosFactory):
        super(NagConfigFile, self).__init__(filename, factory)
        self.parser = ConfigParser(factory)

