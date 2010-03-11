"""
This module contains class factory to produce different Nagios objects and
status objects based on their obj_type
"""

class NagiosFactoryError(Exception):
    pass

class NagiosFactory(object):
    """
    Factory to produce different Nagios objects and statuses based on their obj_type
    """
    obj_types = {}

    def __new__(cls, obj_type):
        """
        Just create Nagios object of given obj_type
        """
        if obj_type in cls.obj_types:
            C = cls.obj_types[obj_type]
        else:
            return None
            #raise NagiosFactoryError(
            #    "Object type '%s' is not registered with this factory" % \
            #    obj_type)
        return C()

    @classmethod
    def register_class(cls, nagobj_class):
        """
        Register mapping between ojb_type and corresponding class
        """
        cls.obj_types[nagobj_class.obj_type] = nagobj_class

    @classmethod
    def from_parse(cls, obj_type, args, fmt):
        """
        Create object from result of parse
        """
        if obj_type in cls.obj_types:
            C = cls.obj_types[obj_type]
        else:
            return None
            #raise NagiosFactoryError(
            #    "Object type '%s' is not registered with this factory" % \
            #    obj_type)
        return C.from_parse(args, fmt)

    @classmethod
    def from_structure(cls, data):
        """
        Produce object from its structure
        """
        obj_type = data.get('obj_type', None)
        if obj_type is None:
            raise NagiosFactoryError(
                    "obj_type is not defined in data structure")
        if not obj_type in cls.obj_types:
            raise NagiosFactoryError(
                    "Object type '%s' is not registered with this factory" % \
                    obj_type)
        c = cls.obj_types[obj_type].from_structure(data.get('fields', []), data.get('__id'))
        return c

