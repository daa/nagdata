"""
Collection of Nagios objects
"""

import copy
from factory import NagiosFactory
from exceptions import NotUnique

class NagCollection(object):
    """
    Collection of Nagios objects.
    Provides methods to filter objects based on fields and their values.
    """

    def __init__(self, notags=False):
        """
        if notags is set then no indexing will be performed and no search will
        be possible (it is useful when creating intermediary collections which
        are used only to keep set of objects)
        """
        self._set = set()
        self.notags = notags
        self._groups = {}

    def add(self, nagobj):
        """
        Add object to collection. Also adds this object to necessary groups
        """
        if self.check_pk(nagobj):
            self._set.add(nagobj)
        else:
            raise NotUnique(
            "Object '%s' with %s already exists in collection" % \
                    (nagobj.obj_type, nagobj.pkey_value()))
        if not self.notags:
            nagobj.collection = self
            for g in nagobj.tags:
                if g in nagobj:
                    self._add_to_group(g, nagobj)

    def get_similar(self, nagobj):
        """
        Returns set of objects with the same primary key.
        """
        return self.filter(__id=nagobj['__id'])

    def check_pk(self, nagobj):
        """
        Check if primary key is correct (does not exist in collection)
        """
        return self.notags or not bool(self.get_similar(nagobj))

    def _add_to_group(self, g, nagobj):
        f = nagobj[g]
        if g in self._groups:
            gr = self._groups[g]
            if f in gr:
                gr[f].add(nagobj)
            else:
                gr[f] = set([nagobj])
        else:
            self._groups[g] = {f: set([nagobj])}

    def all(self):
        """
        Return set of all objects
        """
        return copy.copy(self._set)

    def flush(self):
        """
        Clear collection
        """
        for gr in self._groups:
            gr.clear()
        self._groups.clear()
        for o in self._set:
            o.collection = None
        self._set.clear()

    def filter(self, **tags):
        """
        Return set of objects matching given tags
        """
        items = tags.items()
        k, v = items[0]
        gr = self._groups
        if k in gr and v in gr[k]:
            x = gr[k][v]
            if items[1:] == []:
                x = copy.copy(x)
            else:
                for k, v in items[1:]:
                        if k in gr and v in gr[k]:
                            x = x.intersection(gr[k][v])
                        else:
                            x = set()
                            break
        else:
            x = set()
        return x

    def extend(self, coll):
        """
        Extend collection with another
        """
        for o in coll:
            self.add(o)

    def remove(self, nagobj):
        """
        Remove object from collection
        """
        for g in nagobj.tags:
            self._groups[g][nagobj[g]].remove(nagobj)
        self._set.discard(nagobj)
        nagobj.collection = None

    def update_tag(self, tag, prev, cur, nagobj):
        """
        Update collection's tag sets when nagobj's tag changes its value from
        prev to cur.
        """
        if not self.notags:
            if tag in nagobj.tags:
                gr = self._groups
                if tag in gr:
                    if not prev is None and prev in gr[tag]:
                        gr[tag][prev].remove(nagobj)
                    if not cur is None:
                        if cur in gr[tag]:
                            gr[tag][cur].add(nagobj)
                        else:
                            gr[tag][cur] = set([nagobj])
                elif not cur is None:
                    gr[tag] = { cur: set([nagobj]) }

    def __iter__(self):
        return self._set.__iter__()

    def __len__(self):
            return len(self._set)


