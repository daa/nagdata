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
"Imaginary" format object to keep object file format
"""


from factory import NagiosFactory

class __fmt__(dict):
    """
    Represent nagios object's format
    """
    # define with which object type will factory associate this class (None
    # to not associate)
    obj_type = '__fmt__'
    obj_group = None
    # what fields to index and perform search
    _base_tags = set(['obj_type', '__filename', '__id'])
    tags = set()

    @classmethod
    def from_parse(cls, args, fmt):
        self = cls()
        self.fmt = fmt
        return self

    def __init__(self):
        self.__id = object.__hash__(self)
        self['obj_type'] = self.obj_type
        self['__id'] = self.__id
        self.tags.update(self._base_tags)

    def __str__(self):
        return ''.join([ a for t, a, l in self.fmt ])

    def __hash__(self):
        """
        To be hashable as objects
        """
        return self.__id

def register_fmt_classes(factory=NagiosFactory):
    factory.register_class(__fmt__)

