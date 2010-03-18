#!/usr/bin/python

import gamin
from nagdata import nagdata
import time
import os

class GaminWatcher(object):
    def __init__(self, nd):
        """
        nd -- nagdata object to watch for
        """
        self.watch_monitor = gamin.WatchMonitor()
        self.nd = nd

    def update_config_file(self, path, evt, base_dir=None):
        """
        Called when one of configuration files changes
        """
        if path.endswith('.cfg') and evt == gamin.GAMCreated:
            if base_dir:
                path = base_dir + os.sep + path
            if path in self.nd.config_outdated():
                self.nd.update_config_file(path)

    def update_status(self, path, evt):
        if evt == gamin.GAMCreated:
            self.nd.update_status()

    def watch_config(self, watch=True):
        """
        Watch for config files and directories
        """
        if watch:
            for f in self.nd.cfg['cfg_file']:
                self.watch_monitor.watch_file(f, self.update_config_file)
            for d in self.nd.cfg['cfg_dir']:
                self.watch_monitor.watch_directory(d, self.update_config_file, d)
        else:
            for f in self.nd.cfg['cfg_file']:
                self.watch_monitor.stop_watch(f)
            for d in self.nd.cfg['cfg_dir']:
                self.watch_monitor.stop_watch(d)

    def watch_status(self, watch=True):
        """
        Watch for status file
        """
        if watch:
            self.watch_monitor.watch_file(
                    self.nd.cfg['status_file'], self.update_status)
        else:
            self.watch_monitor.stop_watch(self.nd.cfg['status_file'])

    def run(self):
        """
        Run an infinite loop handling events
        """
        while True:
            self.watch_monitor.handle_one_event()
            self.watch_monitor.handle_events()
            time.sleep(0.1)

class N(nagdata.NagDataSimpleApi):
    def before_update_status(self, old, new):
        print 'upd st'
    def before_update_config(self, old, new):
        print 'upd cfg'
    def after_update_config(self):
        print 'updated configuration'
    def after_update_status(self):
        print 'updated status'

if __name__ == '__main__':
    # create nagdata object
    n = N()
    # tie it with watcher
    g = GaminWatcher(n)
    # make in watch config
    g.watch_config()
    # make in watch status
    g.watch_status()
    # start main loop
    g.run()

