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
Python interface to Nagios objects and status
"""

import glob
import os
import time
import re

from nagfile import NagObjectFile, NagStatusFile, NagConfigFile, NagLogFile
from collection import NagCollection
from factory import NagiosFactory
from exceptions import NotFound, TooMany, NotInConfig, ConfigNotGiven
import model
import fmt
import log

class NagData(object):
    """
    Provides interface to Nagios objects and status.
    """
    starting_re = re.compile('^Nagios .+ starting\.\.\.')

    def __init__(self, config_file='/etc/nagios/nagios.cfg',
            factory=NagiosFactory,
            keep_backup=True):
        """
        config_file -- Nagios configuration file
        keep_backup -- keep backup copy of configuration file we're writing at
                       save_object
        """
        self.factory = factory
        model.register_all_classes(self.factory)
        fmt.register_fmt_classes(self.factory)
        log.register_log_classes(self.factory)
        self.nagios_cfg = config_file
        self.cfg, self.config = self.load_config()
        self.status, self.status_ctime = self.load_status()
        self.log, self.log_pos = self.load_log()
        # time of last check for nagios reload
        self.last_reload = time.strftime("%s")
        self.keep_backup = keep_backup

    def load_config_file(self, filename):
        """
        Loads configuration file and returns collection of objects containing
        in it, may be useful for incremental update of configuration
        Does not suit for loading main nagios.cfg
        """
        return NagObjectFile(filename, self.factory).parse(add_file_info=True)

    def load_config(self):
        """
        Load configuration file and objects, returns representation of main
        configuration file (nagios.cfg) and config collection
        """
        nco = NagCollection(obj_group='config')
        cfg = NagConfigFile(self.nagios_cfg, self.factory).parse(add_file_info=True)
        nco.add(cfg)
        for f in cfg['cfg_file']:
            nco.extend(self.load_config_file(f))
        for d in cfg['cfg_dir']:
            for f in glob.glob("%s/*.cfg" % d):
                nco.extend(self.load_config_file(f))
        return cfg, nco

    def load_status(self):
        """
        Load status file and objects, returns status collection and it's change
        time (ctime of file)
        """
        nso = NagCollection()
        try:
            nso.extend(NagStatusFile(self.cfg['status_file'], self.factory).parse())
        except:
            pass
        try:
            status_ctime = os.stat(self.cfg['status_file']).st_ctime
        except:
            status_ctime = 0
        return nso, status_ctime

    def load_log(self, filename=None, pos=None):
        """
        Load nagios.log file, or its archive copy, returns log file and position
        """
        if not filename:
            filename = self.cfg['log_file']
        log = NagLogFile(filename, self.factory).parse(add_file_info=True)
        pos = log['__byte_pos']
        return log, pos

    def update_config(self):
        """
        Update current configuration, changed and created objects remain in
        config collection
        """
        main_cfg, cfg_objs = self.load_config()
        # add changed and created config objects to new collection
        cfg_objs.update(self.config)
        self.config = cfg_objs
        self.cfg = main_cfg

    def update_config_file(self, filename):
        """
        Update config with objects from given file, can also update self.cfg
        from main nagios.cfg
        """
        if filename != self.nagios_cfg:
            objs = self.load_config_file(filename)
            self.config.update(objs)
        else:
            cfg = NagConfigFile(self.nagios_cfg, self.factory).parse(add_file_info=True)
            self.config.remove(self.cfg)
            self.cfg = cfg
            self.config.add(cfg)

    def update_status(self):
        """
        Update current status, status collection is fully updated, changes (if
        were, but shouldn't be) are discarded
        """
        stat, ctime = self.load_status()
        self.status_ctime = ctime
        self.status = stat

    def update_log(self):
        nlog, npos = self.load_log(filename=self.cfg['log_file'],
                pos=self.log_pos)
        self.log['records'].extend(nlog['records'])
        self.log_pos = npos

    def config_outdated(self):
        """
        Check if configuration files were updated since last load, returns set
        of updated files
        """
        outdated = set()
        for fn, fs in self.config.tags['__filename'].items():
            try:
                ctime = os.stat(fn).st_ctime
                if fs:
                    if ctime > list(fs)[0]['__ctime']:
                        outdated.add(fn)
                else:
                    outdated.add(fn)
            except:
                if fs:
                    outdated.add(fn)
        cfg = NagConfigFile(self.nagios_cfg,
                self.factory).parse()
        for f in cfg['cfg_file'] + reduce(lambda s, x: s + x,
                 [ glob.glob("%s/*.cfg" % d) for d in cfg['cfg_dir'] ], []):
                # appeared new file
                if not f in self.config.tags['__filename']:
                    outdated.add(f)
        return outdated

    def status_outdated(self):
        """
        Check if status file was updated since last use
        """
        try:
            ctime = os.stat(self.cfg['status_file']).st_ctime
            return ctime > self.status_ctime
        except:
            return False

    def nagios_reloaded(self, since=None):
        """
        Check if Nagios process was reloaded since last check
        """
        if not since:
            since = self.last_reload
        self.update_log()
        n = 0
        for ts, msg in self.log['records']:
            if ts >= since:
                break
            n += 1
        new_recs = self.log['records'][n:]
        reload_ts = None
        for ts, msg in new_recs:
            #print msg
            if msg == 'Caught SIGHUP, restarting...' \
                    or self.starting_re.match(msg):
                reload_ts = ts
        if reload_ts:
            self.last_reload = reload_ts
        return reload_ts

    def new(self, obj_type, **kw):
        """
        Create nagios object of obj_type, set its fields from kw, add it to
        config collection, return it. Can create only objects of 'config'
        group, otherwise exception raised when adding to config collection
        """
        o = self.factory(obj_type, **kw)
        self.config.add(o)
        return o

    def remove(self, nagobj):
        """
        Remove object from collections
        """
        self.status.remove(nagobj)
        self.config.remove(nagobj)

    def filter(self, **tags):
        """
        Return set of objects matching given tags
        """
        return self.config.filter(**tags).union(self.status.filter(**tags))

    def getall(self, obj_type, **tags):
        """
        Get set of all objects with givent type matching given key-value
        """
        # here we use fact that config and status objects are in different
        # collections
        if obj_type in self.config.tags['obj_type']:
            return self.config.filter(obj_type=obj_type, **tags)
        elif obj_type in self.status.tags['obj_type']:
            return self.status.filter(obj_type=obj_type, **tags)
        else:
            return set()

    def get(self, obj_type, **kw):
        """
        Return object of given type matching given key-value, raise NotFound or
        TooMany exceptions when no objects found or found more than 1 object.
        """
        o = self.getall(obj_type, **kw)
        l = len(o)
        if l <= 0:
            raise NotFound("'%s' (%s) not found" % \
                    (obj_type, ','.join([ "%s='%s'" % (str(n), str(v))
                        for n, v in kw.items() ])))
        elif l > 1:
            raise TooMany("Too many objects '%s' (%s)" % \
                    (obj_type, ','.join([ "%s='%s'" % (str(n), str(v))
                        for n, v in kw.items() ])))
        else:
            return o.pop()

    def get_or_none(self, obj_type, **kw):
        """
        Return object of given type matching given key-value, returns None when
        cannot return single object (not found or found >1)
        """
        o = self.getall(obj_type, **kw)
        if len(o) != 1:
            return None
        else:
            return o.pop()

    def save(self, nagobj, filename=None):
        """
        Save object to file and set __filename attribute
        If filename is not given, save it to self['__filename'], also saves all
        other objects belonging to that file.
        """
        if filename is None:
            filename = nagobj['__filename']
        filename = os.path.abspath(filename)
        nagobj['__filename'] = filename

        if not [ d for d in self.cfg['cfg_dir'] if filename.startswith(d) ] \
                and not filename in self.cfg['cfg_file']:
                    raise NotInConfig(filename)

        if not nagobj in self.config:
            self.config.add(nagobj)

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
        # update ctime of objects so that they will not appear in outdated
        ctime = os.stat(filename).st_ctime
        for o in objs:
            o['__ctime'] = ctime



class SimpleApi(object):
    """
    Mixin to add simple API for NagData to make access to common types of
    objects easier.
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
            return self.get('service', host_name=h['host_name'],
                    service_description=service_description)
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
        return list(self.getall('servicestatus', host_name=h.fields.host_name))

    def get_hostgroup_statuses(self, hostgroup_name):
        """
        list of hoststatus for hostgroup
        """
        hg = self.get_hostgroup(hostgroup_name)
        return [ s for s in
                [ self.get_hoststatus(host) for host in hg['members'] ] if s ]

    def get_servicegroup_statuses(self, servicegroup_name):
        """
        list of servicestatus for servicegroup
        """
        sg = self.get_servicegroup(servicegroup_name)
        return [ s for s in
                [ self.get_servicestatus(h, s) for h,s in sg['members'] ] if s ]

    def get_hostcomments(self, host):
        """
        list of hostcomment for host
        """
        h = self.get_host(host)
        return list(self.getall('hostcomment', host_name=h['host_name']))

    def get_servicecomments(self, host, srv):
        """
        list of servicecomment for host and service
        """
        h = self.get_host(host)
        return list(self.getall('servicecomment',
            host_name=h['host_name'], service_description=srv))

    def get_author_hostcomments(self, author):
        """
        all author hostcomments
        """
        return list(self.getall('hostcomment', author=author))

    def get_author_servicecomments(self, author):
        """
        all author servicecomments
        """
        return list(self.getall('servicecomment', author=author))

    def get_author_comments(self, author):
        """
        all author comments
        """
        return self.get_author_hostcomments(author) + self.get_author_servicecomments(author)

    def get_hosts(self):
        """
        all hosts
        """
        return list(self.getall('host'))

    def get_hostgroups(self):
        """
        all hostgroups
        """
        return list(self.getall('hostgroup'))

    def get_services(self):
        """
        all services
        """
        return list(self.getall('service'))

    def get_servicegroups(self):
        """
        all servicegroups
        """
        return list(self.getall('servicegroup'))

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

class OnUpdateCallbacks(object):
    """
    Mixin to add callbacks on update to NagData
    """

    def update_config(self):
        """
        Update current configuration, changed and created objects remain in
        config collection, call on_update_config(old, new) before any update
        """
        main_cfg, cfg_objs = self.load_config()
        self.before_update_config(self.config, cfg_objs)
        # add changed and created config objects to new collection
        cfg_objs.update(self.config)
        self.config = cfg_objs
        self.cfg = main_cfg
        self.after_update_config()

    def update_config_file(self, filename):
        """
        Update config with objects from given file, can also update self.cfg
        from main nagios.cfg
        """
        if filename != self.nagios_cfg:
            cfg_objs = self.load_config_file(filename)
            self.before_update_config(self.config, cfg_objs)
            self.config.update(cfg_objs)
            self.after_update_config()
        else:
            cfg = NagConfigFile(self.nagios_cfg, self.factory).parse(add_file_info=True)
            self.config.remove(self.cfg)
            self.cfg = cfg
            self.config.add(cfg)

    def update_status(self):
        """
        Update current status, status collection is fully updated, changes (if
        were, but shouldn't be) are discarded, call on_update_status(old, new)
        before any update
        """
        stat, ctime = self.load_status()
        self.before_update_status(self.config, stat)
        self.status_ctime = ctime
        self.status = stat
        self.after_update_status()

    def before_update_config(self, old_config, new_config):
        """
        Called after loading new configuration and before updating old
        """
        pass

    def after_update_config(self):
        """
        Called after updating configuration objects
        """
        pass

    def before_update_status(self, old_status, new_status):
        """
        Called after loading new status collection and before updating old
        """
        pass

    def after_update_status(self):
        """
        Called after updating status objects
        """
        pass

class NagDataSimpleApi(SimpleApi, OnUpdateCallbacks, NagData):
    """
    NagData with simple api and callbacks on update
    """
    pass

