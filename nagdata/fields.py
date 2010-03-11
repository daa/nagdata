"""
Attribute types of Nagios object
"""

class nag_str(str):
    """
    String attribute
    """
    def add(self, vl):
        pass

class value_list(list):
    """
    Just list of values with another __str__
    """

    def __str__(self):
        return ','.join([ str(x) for x in self ])

    def add(self, vl):
        self.extend(vl)

    @classmethod
    def from_string(cls, s):
        """
        create list from comma-separated string
        """
        return cls([ x.strip() for x in s.split(',')])

class tuple_list(value_list):
    """
    Just list of tuples with specific __str__
    """
    def __str__(self):
        return ','.join([ "%s,%s" % (x, y) for x, y in self ])

    @classmethod
    def from_string(cls, s):
        """
        create list from comma-separated string
        """
        l = [ x.strip() for x in s.split(',') ]
        return cls([ (p0, p1) for p0, p1 in zip(l[::2], l[1::2]) ])

class group_list(object):
    def __new__(self, list_class):
        class grouplist(list_class):
            _list_class = list_class
            def __init__(self, init=None):
                if init is None:
                    super(grouplist, self).__init__()
                    self.groups = []
                else:
                    super(grouplist, self).__init__(init)
                    self.groups = [init]
            def add(self, l):
                self.groups.append(l)
                super(grouplist, self).add(l)
            def new_group(self):
                self.groups.append(self._list_class())
            def append(self, v):
                self.groups[-1].append(v)
                super(grouplist, self).append(v)
            def __str__(self):
                return super(grouplist, self).__str__()
            @classmethod
            def from_string(cls, s):
                return cls(cls._list_class.from_string(s))
            def add_from_string(self, s):
                self.add(self._list_class.from_string(s))
        return grouplist

