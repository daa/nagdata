"""
"Imaginary" format object to keep object file format
"""

from factory import NagiosFactory

class __fmt__(dict):
    """
    Base class for objects and statuses. Its ancestors should provide __str__
    method to represent it in correct Nagios syntax.
    """
    # define with which object type will factory associate this class (None
    # to not associate)
    obj_type = '__fmt__'
    # what fields to index and perform search
    _base_tags = set(['__filename', '__id'])
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

