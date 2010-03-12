"""
Nagios elementary object
"""

from factory import NagiosFactory
from exceptions import NotUnique
import fields

class BaseNagObj(dict):
    """
    Base class for objects and statuses. Its ancestors should provide __str__
    method to represent it in correct Nagios syntax.
    """
    # define with which object type will factory associate this class (None
    # to not associate)
    obj_type = None
    # primary key
    pkey = None
    # what fields to index and to perform search
    # (search may be performed only on this tags)
    _base_tags = set(['obj_type', '__id', '__filename'])
    tags = set()
    # collection containing this object
    collection = None
    # original object whether object is cloned
    _cloned = None
    # object's format
    fmt = None

    def __init__(self):
        self.__id = object.__hash__(self)
        sup = super(BaseNagObj, self)
        sup.__setitem__('obj_type', self.obj_type)
        sup.__setitem__('__id', self.__id)
        #self['obj_type'] = self.obj_type
        #self['__id'] = self.__id
        idxs = self.tags
        pk = self.pkey
        idxs.update(self._base_tags)
        if isinstance(pk, tuple):
            idxs.update(pk)
        else:
            idxs.add(pk)

    def pkey_value(self):
        pk = self.pkey
        if pk is None:
            val = "__id='%s'" % self.__id
        elif isinstance(pk, tuple):
            val = ','.join([ "%s=%s" % (k, repr(self.get(k)))
                for k in pk if self.get(k)])
        else:
            val = "%s=%s" % (pk, repr(self.get(pk)))
        return val

    @classmethod
    def from_parse(cls, args, fmt):
        """
        Create object from result of parse
        """
        self = cls()
        self.fmt = fmt
        sup = super(BaseNagObj, self)
        for a, v in args:
            if hasattr(cls, a):
                o_v = getattr(cls, a).from_string(v)
            else:
                o_v = v
            if a in self:
                try:
                    self[a].add(o_v)
                except:
                    pass
            else:
                sup.__setitem__(a, o_v)
        self.update_pk()
        return self

    def fields(self):
        """
        Return object's fields
        """
        return [ (a, v)
            for a, v in self.items()
                if not a.startswith('_') and a != 'obj_type' ]

    def update_pk(self):
        """
        Update pkey and __id. It should be called when attributes in self.pkey
        change
        """
        pk = self.pkey
        if isinstance(pk, str) and pk in self:
            self.__id = hash((self.obj_type, pk, self[pk]))
        elif isinstance(pk, tuple):
            pks = [self.obj_type]
            for k in pk:
                pks.append(k)
                if k in self:
                    pks.append(self[k])
                else:
                    pks.append(None)
            self.__id = hash(tuple(pks))
        super(BaseNagObj, self).__setitem__('__id', self.__id)

    def is_pk(self, attr):
        """
        Check if attr is primary key or its part
        """
        if attr == '__id':
            return True
        pk = self.pkey
        if isinstance(pk, str):
            return attr == pk
        elif isinstance(pk, tuple):
            return attr in set(pk)
        else:
            return False

    def clone(self):
        """
        get a clone of this object. useful when changing pkeys.
        """
        clone = self.__class__()
        clone._cloned = self
        for k, v in self.items():
            super(BaseNagObj, clone).__setitem__(k, v)
        return clone

    def replace_cloned(self):
        """
        If this object is clone, replace original with it in collection
        """
        if self._cloned:
            cloned = self._cloned
            self._cloned = None
            self.collection = cloned.collection
            self.update_pk()
            if self.collection:
                self.collection.remove(_cloned)
                self.collection.add(self)

    def unclone(self):
        """
        Make this object not to be a clone and add it to collection
        """
        if self._cloned:
            self.collection = self._cloned.collection
            self._cloned = None
            self.update_pk()
            if self.collection:
                self.collection.add(self)

    @classmethod
    def from_structure(cls, attrs, __id=None):
        """
        Create object from structure
        """
        self = cls()
        for a, v in attrs.items():
            self[a] = v
        if __id is None:
            self.update_pk()
        else:
            self.__id = __id
            super(BaseNagObj, self).__setitem__('__id', __id)
        self.fmt = None
        return self

    def to_structure(self):
        """
        Return object's representation as base structure
        """
        return {'obj_type': self.obj_type,
                '__id': self.__id,
                'fields': dict(self.fields()) }

    def _update_fmt(self):
        """
        Update object's format. It is called by __str__.
        """
        if not self.fmt is None:
            n = -1
            new_f = []
            line = []
            skip_line = False
            done = {}
            last_ln = 0
            for t, a, l in self.fmt:
                if n < 0:
                    n = l
                if n == l:
                    if not skip_line:
                        if t != 'FMT_VAL':
                            line.append((t, a, l))
                        elif a in self:
                            if hasattr(self[a], 'groups'):
                                i = done.setdefault(a, 0)
                                if i < len(self[a].groups):
                                    line.append((t, a, l))
                                done[a] += 1
                            else:
                                line.append((t, a, l))
                                done[a] = 1
                        else:
                            skip_line = True
                else:
                    if n >= 0 and not skip_line:
                        new_f.extend(line)
                    skip_line = False
                    line = [(t, a, l)]
                    n = -1
                last_ln = l
            last_l = line
            for a, v in self.fields():
                if hasattr(self[a], 'groups'):
                    left_len = len(self[a].groups[done[a]:])
                    for l in range(left_len):
                        new_f.extend(self._fmt_line(a, last_ln))
                        last_ln += 1
                elif not a in done:
                    new_f.extend(self._fmt_line(a, last_ln))
                    last_ln += 1
            new_f.extend(last_l)
            self.fmt = new_f

    def _fmt_line(self, attr, line_no):
        """
        Return list of format tuples representing line corresponding to
        attribute. This list extends slef._fmt.
        """
        ntabs = int((24 - len(a))/8) + 1
        return [('FMT_STR', '\t', last_ln),
                ('FMT_STR', a, last_ln),
                ('FMT_STR', '\t'*ntabs, last_ln),
                ('FMT_VAL', a, last_ln),
                ('FMT_STR', '\n', last_ln)]

    def __str__(self):
        if self.fmt is None:
            return dict.__str__(self)
        else:
            self._update_fmt()
            n = -1
            s = []
            line = []
            done = {}
            for t, a, l in self.fmt:
                if n < 0:
                    n = l
                if n == l:
                    if t != 'FMT_VAL':
                        line.append(a)
                    elif hasattr(self[a], 'groups'):
                        i = done.setdefault(a, 0)
                        if i < len(self[a].groups):
                            line.append(str(self[a].groups[i]))
                        done[a] += 1
                    else:
                        line.append(str(self[a]))
                        done[a] = 1
                else:
                    if n >= 0:
                        s.append(line)
                    if t == 'FMT_VAL':
                        line = [str(self[a])]
                    else:
                        line = [a]
                    n = -1
            s.append(line)
            return ''.join([ ''.join(l) for l in s ])

    def __hash__(self):
        """
        To be hashable as objects
        """
        return self.__id

    def __setitem__(self, attr, value):
        cv = attr in self and self[attr] or None
        sup = super(BaseNagObj, self)
        if hasattr(self.__class__, attr):
            attr_class = getattr(self.__class__, attr)
            if not isinstance(value, attr_class):
                value = attr_class(value)
        sup.__setitem__(attr, value)
        if self.is_pk(attr):
            pk = self['__id']
            self.update_pk()
        else:
            pk = None
        if self.collection and not self._cloned:
            if pk:
                if self.collection.check_pk(self):
                    self.collection.update_tag('__id', pk, self['__id'], self)
                    self.collection.update_tag(attr, cv, value, self)
                else:
                    if cv is None and attr in self:
                        del self[attr]
                    else:
                        sup.__setitem__(attr, cv)
                    sup.__setitem__('__id', pk)
                    raise NotUnique(
                    "Object '%s' with %s already exists in collection" % \
                            (self.obj_type, self.pkey_value()))
            else:
                self.collection.update_tag(attr, cv, value, self)


# Nagios objects
class NagObj(BaseNagObj):
    """
    Nagios object
    """
    def __str__(self):
        if self.fmt is None:
            return "define %s {\n\t%s\n\t}\n\n" % (self.obj_type, "\n\t".join([
                "%-40s%s" % (a, v) for a, v in self.fields() ]))
        else:
            return super(NagObj, self).__str__()

class NagObjGroup(NagObj):
    """
    Group of nagios objects (such as hostgroup, servicegroup, contactgroup)
    """
    members = fields.group_list(fields.value_list)

class NagHost(NagObj):
    obj_type = 'host'
    pkey = ('host_name', 'name')
    tags = set(['address', 'alias'])

class NagHostGroup(NagObjGroup):
    """
    Nagios host group
    """
    obj_type = 'hostgroup'
    pkey = 'hostgroup_name'
    tags = set(['use', 'name'])

class NagService(NagObj):
    obj_type = 'service'
    pkey = ('service_description', 'host_name', 'name', 'hostgroup_name')
    tags = set(['use'])

class NagServiceGroup(NagObjGroup):
    """
    Nagios service group
    """
    obj_type = 'servicegroup'
    pkey = 'servicegroup_name'
    tags = set(['alias'])
    members = fields.group_list(fields.tuple_list)

class NagContact(NagObj):
    obj_type = 'contact'
    pkey = ('contact_name', 'name')
    tags = set(['alias'])

class NagContactGroup(NagObjGroup):
    obj_type = 'contactgroup'
    pkey = 'contactgroup_name'
    tags = set(['alias'])

class NagServiceDependency(NagObj):
    obj_type = 'servicedependency'
    pkey = ('host_name', 'service_description', 'dependent_host_name',
    'dependent_description')

class NagServiceEscalation(NagObj):
    obj_type = 'serviceescalation'
    pkey = ('host_name', 'service_description')

class NagHostDependency(NagObj):
    obj_type = 'hostdependency'
    pkey = ('host_name', 'dependent_host_name')
    tags = set(['hostgroup_name'])

class NagHostEscalation(NagObj):
    obj_type = 'hostescalation'
    tags = set(['host_name', 'hostgroup_name'])

class NagHostExtInfo(NagObj):
    obj_type = 'hostextinfo'
    pkey = 'host_name'

class NagServiceExtInfo(NagObj):
    obj_type = 'serviceextinfo'
    pkey = 'service_description'

class NagTimePeriod(NagObj):
    obj_type = 'timeperiod'
    pkey = 'timeperiod_name'
    tags = set(['alias'])

class NagCommand(NagObj):
    obj_type = 'command'
    pkey = 'command_name'


# Nagios status objects
class NagStat(BaseNagObj):
    """
    Nagios status
    """
    def __str__(self):
        return "%s {\n\t%s\n\t}\n" % (self.obj_type, "\n\t".join([
            "%s = %s" % (a, v) for a, v in self.fields() ]))

class NagInfo(NagStat):
    obj_type = 'info'

class NagProgramStatus(NagStat):
    obj_type = 'programstatus'

class NagHostStatus(NagStat):
    obj_type = 'hoststatus'
    pkey = 'host_name'
    tags = set(['current_state', 'is_flapping', 'has_been_checked', 'state_type'])

class NagHostComment(NagStat):
    obj_type = 'hostcomment'
    pkey = 'comment_id'
    tags = set(['host_name', 'author'])

class NagServiceStatus(NagStat):
    obj_type = 'servicestatus'
    pkey = ('host_name', 'service_description')
    tags = set(['is_flapping', 'has_been_checked', 'state_type'])

class NagServiceComment(NagStat):
    obj_type = 'servicecomment'
    pkey = 'comment_id'
    tags = set(['host_name', 'service_description', 'author'])

class NagContactStatus(NagStat):
    obj_type = 'contactstatus'
    pkey = 'contact_name'


class NagConfig(NagStat):
    """
    Represents main Nagios configuration file. It contains field-value pairs,
    so obj_type is DEFAULT_ROOT (which is 'ROOT')
    """
    obj_type = 'ROOT'
    cfg_file = fields.group_list(fields.value_list)
    cfg_dir = fields.group_list(fields.value_list)

    def __str__(self):
        return BaseNagObj.__str__(self)

    def _fmt_line(self, attr, line_no):
        """
        Return list of format tuples representing line corresponding to
        attribute. This list extends slef._fmt.
        """
        return [('FMT_STR', '', last_ln),
                ('FMT_STR', a, last_ln),
                ('FMT_STR', '=', last_ln),
                ('FMT_VAL', a, last_ln),
                ('FMT_STR', '\n', last_ln)]

# Register object and status classes with Nagios factory
# should be called when starting to work with library

def register_object_classes(factory=NagiosFactory):
    """
    register object classes with factory
    """
    for c in [NagHost, NagHostGroup, NagService, NagServiceGroup, \
            NagContact, NagContactGroup, NagServiceDependency, \
            NagServiceEscalation, NagHostDependency, NagHostEscalation, \
            NagHostExtInfo, NagServiceExtInfo, NagTimePeriod, NagCommand]:
        factory.register_class(c)

def register_status_classes(factory=NagiosFactory):
    """
    register status classes with factory 
    """
    for c in [NagInfo, NagProgramStatus, NagHostStatus, NagHostComment,\
            NagServiceStatus, NagServiceComment, NagContactStatus]:
        factory.register_class(c)

def register_config_classes(factory=NagiosFactory):
    factory.register_class(NagConfig)

def register_all_classes(factory=NagiosFactory):
    """
    register all classes with factory
    """
    register_object_classes(factory)
    register_status_classes(factory)
    register_config_classes(factory)

