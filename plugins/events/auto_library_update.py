# Automatic library update plugin
#
# (c) 2009 Joe Higton
#     2011 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from pyinotify import WatchManager, EventsCodes, ProcessEvent, Notifier,\
    ThreadedNotifier
from quodlibet import config, print_d
from quodlibet.plugins.events import EventPlugin
import gobject
import os

class LibraryEvent(ProcessEvent):
    """pynotify event handler for library changes"""

    # Slightly dodgy state mechanism for updates
    _being_created = set()

    def __init__(self, library):
        self._library = library

    def process_default(self, event):
        print_d('Uncaught event for %s' % self.pevent, self)

    def process_IN_CLOSE_WRITE(self, event):
        path = os.path.join(event.path, event.name)
        # No need to add files for modifications only
        if path in self._being_created:
            gobject.idle_add(self.add, event)
            self._being_created.remove(path)
        elif event.path in self._being_created:
            # The first file per new-directory gets missed for me (bug?)
            # TODO: so work out how/when to remove parent path properly
            gobject.idle_add(self.add, event)
            self._being_created.remove(event.path)
        else:
            print_d("Ignoring modification on %s" % path, self)

    def process_IN_MOVED_TO(self, event):
        print_d('Triggered for "%s"' % event.name, self)
        gobject.idle_add(self.add, event)

    def process_IN_CREATE(self, event):
        #print_d('Triggered for "%s"' % event.name, self)
        # Just remember that they've been created, process in further updates
        path = os.path.join(event.path, event.name)
        self._being_created.add(path)

    def process_IN_DELETE(self, event):
        print_d('Triggered for "%s"' % event.name, self)
        gobject.idle_add(self.update, event)

    def process_IN_MOVED_FROM(self, event):
        print_d('Triggered for "%s"' % event.name, self)
        gobject.idle_add(self.update, event)

    def add(self, event):
        """Add a library file / folder based on an incoming event"""
        lib = self._library
        path = os.path.join(event.path, event.name)
        if event.dir:
            print_d('Scanning directories...', self)
            for path, dnames, fnames in os.walk(path):
                print_d('Found %d file(s) in "%s"' % (len(fnames), path), self)
                lib.add_filename([os.path.join(path, fn) for fn in fnames])
        else:
            item = lib.add_filename(path)
        return False

    def update(self, event):
        """Update a library / file. Typically this means deleting it"""
        lib = self._library
        path = os.path.join(event.path, event.name)
        if event.dir:
            print_d('Checking directory %s...' % path, self)
            to_reload = []
            for filename in lib._contents:
                if filename.startswith(path):
                    item = lib.get(filename, None)
                    if item:
                        # Don't modify whilst iterating...
                        to_reload.append(item)
            print_d('Reloading %d matching songs(s)' % len(to_reload), self)
            for item in to_reload:
                lib.reload(item)
        else:
            item = lib.get(path, None)
            if item:
                lib.reload(item)
        return False


class AutoLibraryUpdate(EventPlugin):
    PLUGIN_ID = "Automatic library update"
    PLUGIN_DESC = _("Keep your library up to date with inotify. "
                    "Requires %s.") % "pyinotify"
    PLUGIN_VERSION = "0.2"

    # TODO: make a config option
    USE_THREADS = True

    library = None
    event_handler = None
    running = False

    def __init__(self):
        from quodlibet.library import library as library
        self.library = library

    def enabled(self):
        if not self.running :
            wm = WatchManager()
            self.event_handler = LibraryEvent(self.library)

            # Choose event types to watch for
            # FIXME: watch for IN_CREATE or for some reason folder copies
            # are missed,  --nickb
            FLAGS = ['IN_DELETE', 'IN_CLOSE_WRITE', 'IN_MODIFY',
                     'IN_MOVED_FROM', 'IN_MOVED_TO', 'IN_CREATE']
            mask = reduce(lambda x, s: x | EventsCodes.ALL_FLAGS[s], FLAGS , 0)

            if self.USE_THREADS:
                print_d("Using threaded notifier", self)
                self.notifier = ThreadedNotifier(wm, self.event_handler)
                # Daemonize to ensure thread dies on exit
                self.notifier.daemon = True
                self.notifier.start()
            else:
                self.notifier = Notifier(wm, self.event_handler, timeout=100)
                gobject.timeout_add(1000, self.unthreaded_callback)

            for path in self.get_library_dirs():
                print_d('Watching directory %s for %s' % (path, FLAGS), self)
                # See https://github.com/seb-m/pyinotify/wiki/Frequently-Asked-Questions
                wm.add_watch(path, mask, rec=True, auto_add=True)

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
            print_d("Stopping inotify watch...", self)
            self.notifier.stop()

    # find list of directories to scan
    def get_library_dirs(self):
        return config.get("settings", "scan").split(":")
