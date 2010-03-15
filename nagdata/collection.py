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
        # tag -> value -> set of objects
        self.tags = {}

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
            for t in nagobj.tags:
                if t in nagobj:
                    self._add_to_tags(t, nagobj)

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

    def _add_to_tags(self, t, nagobj):
        f = nagobj[t]
        if t in self.tags:
            tgs = self.tags[t]
            if f in tgs:
                tgs[f].add(nagobj)
            else:
                tgs[f] = set([nagobj])
        else:
            self.tags[t] = {f: set([nagobj])}

    def all(self):
        """
        Return set of all objects
        """
        return copy.copy(self._set)

    def flush(self):
        """
        Clear collection
        """
        for tgs in self.tags:
            tgs.clear()
        self.tags.clear()
        for o in self._set:
            o.collection = None
        self._set.clear()

    def filter(self, **tags):
        """
        Return set of objects matching given tags
        """
        items = tags.items()
        k, v = items[0]
        tgs = self.tags
        if k in tgs and v in tgs[k]:
            x = tgs[k][v]
            if items[1:] == []:
                x = copy.copy(x)
            else:
                for k, v in items[1:]:
                        if k in tgs and v in tgs[k]:
                            x = x.intersection(tgs[k][v])
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
            self.tags[g][nagobj[g]].discard(nagobj)
        self._set.discard(nagobj)
        nagobj.collection = None

    def update_tag(self, tag, prev, cur, nagobj):
        """
        Update collection's tag sets when nagobj's tag changes its value from
        prev to cur.
        """
        if not self.notags:
            if tag in nagobj.tags:
                tgs = self.tags
                if tag in tgs:
                    if not prev is None and prev in tgs[tag]:
                        tgs[tag][prev].discard(nagobj)
                    if not cur is None:
                        if cur in tgs[tag]:
                            tgs[tag][cur].add(nagobj)
                        else:
                            tgs[tag][cur] = set([nagobj])
                elif not cur is None:
                    tgs[tag] = { cur: set([nagobj]) }

    def __iter__(self):
        return self._set.__iter__()

    def __len__(self):
            return len(self._set)


