"""
Python interface to Nagios objects and status
"""

import glob
import os
import time

from nagfile import NagObjectFile, NagStatusFile, NagConfigFile
from collection import NagCollection
from factory import NagiosFactory
from exceptions import NotFound, TooMany, NotInConfig
import model
import fmt

class NagData(object):
    """
    Provides interface to Nagios objects and status.
    """

    def __init__(self, config_file='/etc/nagios/nagios.cfg',
            status_file='/var/log/nagios/status.dat', factory=NagiosFactory,
            keep_backup=True):
        """
        config_file -- Nagios configuration file
        status_file -- Nagios status file
        """
        self.factory = factory
        model.register_all_classes(self.factory)
        fmt.register_fmt_classes(self.factory)
        self.nagios_cfg = config_file
        self.status_dat = status_file
        self.config = self.load_config(self.nagios_cfg)
        self.status = self.load_status(self.status_dat)
        self.keep_backup = keep_backup

    def load_config(self, filename):
        """
        Load configuration file and objects
        """
        nco = NagCollection()
        self.cfg = cfg = NagConfigFile(filename, self.factory).parse(add_file_info=True)
        nco.add(cfg)
        for f in cfg['cfg_file']:
            nco.extend(NagObjectFile(f, self.factory).parse(add_file_info=True))
        for d in cfg['cfg_dir']:
            for f in glob.glob("%s/*.cfg" % d):
                nco.extend(NagObjectFile(f, self.factory).parse(add_file_info=True))
        return nco

    def load_status(self, filename='/var/log/nagios/status.dat'):
        """
        Load status file and objects
        """
        nso = NagCollection()
        nso.extend(NagStatusFile(filename, self.factory).parse())
        return nso

    def update_config(self):
        """
        Update current configuration
        """
        cfg = self.load_config(self.nagios_cfg)
        self.config = cfg

    def update_status(self):
        """
        Update current status
        """
        stat = self.load_status(self.status_dat)
        self.status = stat

    def filter(self, **tags):
        """
        Return set of objects matching given tags
        """
        return self.config.filter(**tags).union(self.status.filter(**tags))

    def new(self, obj_type, **kw):
        """
        Create nagios object of obj_type, set its fields from kw
        """
        o = self.factory(obj_type)
        for k, v in kw.items():
            o[k] = v
        return o

    def add(self, nagobj):
        """
        Add object to corresponding collection
        """
        if nagobj.obj_type in self.config.tags['obj_type']:
            self.config.add(nagobj)
        elif nagobj.obj_type in self.status.tags['obj_type']:
            self.status.add(nagobj)

    def addnew(self, obj_type, **kw):
        """
        Create nagios object of obj_type, set its fields from kw, add it to
        corresponding collection, return it
        """
        o = self.new(obj_type, **kw)
        self.add(o)
        return o

    def remove(self, nagobj):
        """
        Remove object from collections
        """
        self.status.remove(nagobj)
        self.config.remove(nagobj)

    def get(self, obj_type, **kw):
        """
        Return object of given type matching given key-value, raise NotFound or
        TooMany exceptions when no objects found or found more than 1 object.
        """
        o = self.filter(obj_type=obj_type, **kw)
        l = len(o)
        if l <= 0:
            raise NotFound("'%s' (%s) not found" % \
                    (obj_type, ','.join([ "%s='%s'" % (str(n), str(v)) for n, v
                        in kw.items() ])))
        elif l > 1:
            raise TooMany("Too many objects '%s' (%s)" % \
                    (obj_type, ','.join([ "%s=%s" % (str(n), str(v)) for n, v
                        in kw.items() ])))
        else:
            return o.pop()

    def get_or_none(self, obj_type, **kw):
        """
        Return object of given type matching given key-value, returns None when
        cannot return single object (not found or found >1)
        """
        o = self.filter(obj_type=obj_type, **kw)
        if len(o) != 1:
            return None
        else:
            return o.pop()

    def save_object(self, nagobj, filename=None):
        """
        Save object to file and set __filename attribute
        If filename is not given, save it to self['__filename'], also saves all
        other objects belonging to that file.
        """
        if filename is None:
            filename = nagobj['__filename']
        filename = os.path.abspath(filename)
        nagobj['__filename'] = filename
        if not reduce(lambda s, d: s or filename.startswith(d), 
                self.cfg['cfg_dir'], False) \
                and not filename in self.cfg['cfg_file']:
                raise NotInConfig(("Fle '%s' is not in one of config " + \
                    "directories and not one of config files") % filename)
        objs = list(self.filter(__filename=filename))
        objs.sort(cmp=lambda a, b: cmp(a.get('__pos', 10000),
            b.get('__pos', 10000)))
        s = ''.join([ str(o) for o in objs ])
        #print s
        if self.keep_backup:
            if os.path.exists(filename):
                t = time.time()
                bkp = open(filename + \
                        time.strftime(".bkp.%Y%m%d%H%M%S.", time.localtime(t)) + \
                        (str(t - int(t))[2:]), 'w')
                org = open(filename, 'r')
                bkp.write(org.read())
                org.close()
                bkp.close()
        f = open(filename, 'w');
        f.write(s)
        f.close()



class NagDataSimpleApi(NagData):
    """
    Simple API for NagData to make access to common types of objects easier.
    """

    def get_host(self, host=None):
        """
        host by host_name or address
        """
        try:
            return self.get('host', host_name=host)
        except NotFound:
            return self.get('host', address=host)

    def get_service(self, service_description, host=None):
        """
        service by description
        """
        if host:
            h = self.get_host(host)
            return self.get('service', host_name=h['host_name'], service_description=service_description)
        else:
            return self.get('service', service_description=service_description)

    def get_servicegroup(self, name):
        """
        servicegroup by name
        """
        return self.get('servicegroup', servicegroup_name=name)

    def get_hostgroup(self, name):
        """
        hostgroup by name
        """
        return self.get('hostgroup', hostgroup_name=name)

    def get_hoststatus(self, host=None):
        """
        hoststatus for host
        """
        h = self.get_host(host)
        return self.get_or_none('hoststatus', host_name=h['host_name'])

    def get_servicestatus(self, host, service_description):
        """
        servicestatus for host and description
        """
        h = self.get_host(host)
        return self.get_or_none('servicestatus', host_name=h['host_name'],
                service_description=service_description)

    def get_host_servicestatuses(self, host):
        """
        list of servicestatus for host
        """
        h = self.get_host(host)
        return list(self.filter(obj_type='servicestatus',
            host_name=h.fields.host_name))

    def get_hostgroup_statuses(self, hostgroup_name):
        """
        list of hoststatus for hostgroup
        """
        hg = self.get_hostgroup(hostgroup_name)
        return filter(lambda x: not x is None,
                [ self.get_hoststatus(host) for host in hg['members'] ])

    def get_servicegroup_statuses(self, servicegroup_name):
        """
        list of servicestatus for servicegroup
        """
        sg = self.get_servicegroup(servicegroup_name)
        return filter(lambda x: not x is None,
                [ self.get_servicestatus(h, s) for h, s in sg['members'] ])

    def get_hostcomments(self, host):
        """
        list of hostcomment for host
        """
        h = self.get_host(host)
        return list(self.filter(obj_type='hostcomment',
            host_name=h['host_name']))

    def get_servicecomments(self, host, srv):
        """
        list of servicecomment for host and service
        """
        h = self.get_host(host)
        return list(self.filter(obj_type='servicecomment',
            host_name=h['host_name'], service_description=srv))

    def get_author_hostcomments(self, author):
        """
        all author hostcomments
        """
        return list(self.filter(obj_type='hostcomment', author=author))

    def get_author_servicecomments(self, author):
        """
        all author servicecomments
        """
        return list(self.filter(obj_type='servicecomment', author=author))

    def get_author_comments(self, author):
        """
        all author comments
        """
        return self.get_author_hostcomments(author) + self.get_author_servicecomments(author)

    def get_hosts(self):
        """
        all hosts
        """
        return list(self.filter(obj_type='host'))

    def get_hostgroups(self):
        """
        all hostgroups
        """
        return list(self.filter(obj_type='hostgroup'))

    def get_services(self):
        """
        all services
        """
        return list(self.filter(obj_type='service'))

    def get_servicegroups(self):
        """
        all servicegroups
        """
        return list(self.filter(obj_type='servicegroup'))

    def get_info(self):
        """
        Nagios info
        """
        return self.get('info')

    def get_programstatus(self):
        """
        programstatus
        """
        return self.get('programstatus')

