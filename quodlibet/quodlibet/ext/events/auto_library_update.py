# -*- coding: utf-8 -*-
# Automatic library update plugin
#
# (c) 2009 Joe Higton
#     2011 - 2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import operator
import os
import sys

from quodlibet.qltk import Icons

if os.name == "nt" or sys.platform == "darwin":
    from quodlibet.plugins import PluginNotSupportedError
    raise PluginNotSupportedError

try:
    from pyinotify import WatchManager, EventsCodes, ProcessEvent
    from pyinotify import Notifier, ThreadedNotifier
except ImportError as e:
    from quodlibet import plugins
    raise plugins.MissingModulePluginException("pyinotify")

from quodlibet import _
from quodlibet.util.dprint import print_d, print_w
from quodlibet.plugins.events import EventPlugin
from quodlibet.util.library import get_scan_dirs
from quodlibet.compat import reduce
from quodlibet import app
from gi.repository import GLib


class LibraryEvent(ProcessEvent):
    """pynotify event handler for library changes"""

    # Slightly dodgy state mechanism for updates
    _being_created = set()

    def my_init(self, library=None):
        self._library = library

    def process_default(self, event):
        print_d('Uncaught event for %s' % (event.maskname if event else "??"))

    def process_IN_CLOSE_WRITE(self, event):
        path = os.path.join(event.path, event.name)
        # No need to add files for modifications only
        if path in self._being_created:
            GLib.idle_add(self.add, event)
            self._being_created.remove(path)
        elif event.path in self._being_created:
            # The first file per new-directory gets missed for me (bug?)
            # TODO: so work out how/when to remove parent path properly
            GLib.idle_add(self.add, event)
            self._being_created.remove(event.path)
        else:
            print_d("Ignoring modification on %s" % path)

    def process_IN_MOVED_TO(self, event):
        self._log(event)
        GLib.idle_add(self.add, event)

    def process_IN_CREATE(self, event):
        if not event.dir:
            self._log(event)
            # Just remember that they've been created, will process later
            path = os.path.join(event.path, event.name)
            if os.path.exists(path):
                self._being_created.add(path)
            else:
                print_w("Couldn't find %s" % path)

    def process_IN_DELETE(self, event):
        self._log(event)
        if event.dir:
            try:
                del self._moved[event.pathname]
            except KeyError:
                pass
        GLib.idle_add(self.update, event)

    def process_IN_MOVED_FROM(self, event):
        self._log(event)
        GLib.idle_add(self.update, event)

    def _log(self, event):
        print_d('%s for "%s" on %s' % (event.maskname, event.name, event.path))

    def add(self, event):
        """Add a library file / folder based on an incoming event"""
        lib = self._library
        path = os.path.join(event.path, event.name)
        if event.dir:
            print_d('Scanning directories...')
            songs = []
            for path, dnames, fnames in os.walk(path):
                print_d('Found %d file(s) in "%s"' % (len(fnames), path))
                for filename in (os.path.join(path, fn) for fn in fnames):
                    song = lib.add_filename(filename, add=False)
                    if song:
                        songs.append(song)
            lib.add(songs)
        else:
            lib.add_filename(path)
        return False

    def update(self, event):
        """Update a library / file. Typically this means deleting it"""
        lib = self._library
        path = os.path.join(event.path, event.name)
        if event.dir:
            print_d('Checking directory %s...' % path)
            to_reload = []
            for filename in lib._contents:
                if filename.startswith(path):
                    item = lib.get(filename, None)
                    if item:
                        # Don't modify whilst iterating...
                        to_reload.append(item)
            print_d('Reloading %d matching songs(s)' % len(to_reload))
            for item in to_reload:
                lib.reload(item)
        else:
            item = lib.get(path, None)
            if item:
                lib.reload(item)
        return False


class AutoLibraryUpdate(EventPlugin):
    PLUGIN_ID = "Automatic library update"
    PLUGIN_NAME = _("Automatic Library Update")
    PLUGIN_DESC = _("Keeps your library up to date with inotify. "
                    "Requires %s.") % "pyinotify"
    PLUGIN_ICON = Icons.VIEW_REFRESH

    # TODO: make a config option
    USE_THREADS = True

    event_handler = None
    running = False

    def enabled(self):
        if not self.running:
            wm = WatchManager()
            self.event_handler = LibraryEvent(library=app.library)

            FLAGS = ['IN_DELETE', 'IN_CLOSE_WRITE', # 'IN_MODIFY',
                     'IN_MOVED_FROM', 'IN_MOVED_TO', 'IN_CREATE']

            masks = [EventsCodes.FLAG_COLLECTIONS['OP_FLAGS'][s]
                     for s in FLAGS]
            mask = reduce(operator.or_, masks, 0)

            if self.USE_THREADS:
                print_d("Using threaded notifier")
                self.notifier = ThreadedNotifier(wm, self.event_handler)
                # Daemonize to ensure thread dies on exit
                self.notifier.daemon = True
                self.notifier.start()
            else:
                self.notifier = Notifier(wm, self.event_handler, timeout=100)
                GLib.timeout_add(1000, self.unthreaded_callback)

            for path in get_scan_dirs():
                real_path = os.path.realpath(path)
                print_d('Watching directory %s for %s (mask: %x)'
                        % (real_path, FLAGS, mask))
                # See https://github.com/seb-m/pyinotify/wiki/
                # Frequently-Asked-Questions
                wm.add_watch(real_path, mask, rec=True, auto_add=True)

            self.running = True

    def unthreaded_callback(self):
        """Processes as much of the inotify events as allowed"""
        assert self.notifier._timeout is not None, \
                'Notifier must be constructed with a [short] timeout'
        self.notifier.process_events()
        # loop in case more events appear while we are processing
        while self.notifier.check_events():
            self.notifier.read_events()
        self.notifier.process_events()
        return True

    # disable hook, stop the notifier:
    def disabled(self):
        if self.running:
            self.running = False
        if self.notifier:
            print_d("Stopping inotify watch...")
            self.notifier.stop()
