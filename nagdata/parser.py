"""
Parser of Nagios status and object definitions
"""

from collection import NagCollection
from factory import NagiosFactory
from exceptions import NagiosSyntaxError
import cparser_fmt
import cparser_fast

class NagiosParser(object):
    """
    Base class to parse Nagios object representation.
    Its descendants should override parse_line to actually parse and retrieve
    attributes and their values
    """

    def __init__(self, factory=NagiosFactory):
        self.factory = factory

    def parse_string(self, buf):
        """
        Parse string and return list of (obj_type, kw, elem_type) where
        elem_type - real|imag for real nagios object, comments, blanks
        obj_type  - type of object
        args      - its fields
        fmt       - its format as was in file
        """
        raise NotImplementedError(
            'You should override parse_string method for actual use')

    def parse(self, buf, add_pos=False, add_attrs=None):
        """
        Parse lines and postprocess its return (create collection of objects,
        etc)
        Returns NagCollection of objects
        """
        c = NagCollection(notags=True)
        try:
            l = self.parse_string(buf);
        except Exception, e:
            raise NagiosSyntaxError(str(e))
        n = 0
        for elem_type, obj_type, args, fmt in l:
            o = self.factory.from_parse(obj_type, args, fmt)
            if o:
                if add_pos:
                    o['__pos'] = n
                    n += 1
                if add_attrs:
                    for k, v in add_attrs.items():
                        o[k] = v
                c.add(o)
        return c

class ObjectParser(NagiosParser):
    """
    Parse lines like object definition files and return collection of Nagios
    objects
    """

    def parse_string(self, buf):
        return cparser_fmt.parse_object_string(buf, 'PARSE_OBJ')

class StatusParser(NagiosParser):
    """
    Parse lines like status.dat file and return collection of status objects
    """

    def parse_string(self, buf):
        return cparser_fast.parse_status_string(buf, 'PARSE_OBJ')

class ConfigParser(StatusParser):
    """
    Parse lines from nagios.cfg
    """

    def parse_string(self, buf):
        return cparser_fmt.parse_status_string(buf, 'PARSE_ARG')

    def parse(self, buf, add_pos=False, add_attrs=None):
        c = super(ConfigParser, self).parse(buf, add_pos, add_attrs)
        return list(c)[0]

