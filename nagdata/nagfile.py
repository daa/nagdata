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

from parser import ObjectParser, StatusParser, ConfigParser, LogParser
from factory import NagiosFactory
from exceptions import NagiosSyntaxError
import model

import os

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

class NagConfigFile(NagFile):
    """
    Parse nagios.cfg file
    """

    def __init__(self, filename, factory=NagiosFactory):
        super(NagConfigFile, self).__init__(filename, ConfigParser(factory))

class NagLogFile(NagFile):
    """
    Parse nagios.log file
    """

    def __init__(self, filename, factory=NagiosFactory):
        super(NagLogFile, self).__init__(filename, LogParser(factory))

    def parse(self, add_file_info=False, pos=None):
        """
        Parse lines and return list of kw (it also has obj_type which should be
        removed when creating object), may read starting from pos
        """
        fd = os.open(self.filename, os.O_RDONLY)
        if pos:
            os.lseek(fd, pos, 0)
        s = os.read(fd, 4096)
        buf = ''
        while s:
            buf += s
            s = os.read(fd, 4096)
        pos = len(buf)
        try:
            if add_file_info:
                c = self.parser.parse(buf, add_pos=True,
                        add_attrs={'__filename': self.filename,
                            '__byte_pos': pos})
            else:
                c = self.parser.parse(buf)
        except NagiosSyntaxError, e:
            os.close(fd)
            raise NagiosSyntaxError("File \"%s\": %s" % (self.filename, str(e)))
        os.close(fd)
        return c

