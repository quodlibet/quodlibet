# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import traceback

import gobject
import gtk

from qltk.msg import ErrorMessage

# Everything connects to this to get updates about the library and player.
# FIXME: The library should manage its signals itself.
class SongWatcher(gtk.Object):
    SIG_PYOBJECT = (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object,))
    SIG_NONE = (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ())
    
    __gsignals__ = {
        # Songs have changed.
        'changed': SIG_PYOBJECT,

        # Songs were removed.
        'removed': SIG_PYOBJECT,

        # Songs were added.
        'added': SIG_PYOBJECT,

        }

    def changed(self, songs):
        if songs: gobject.idle_add(self.emit, 'changed', songs)

    def added(self, songs):
        if songs: gobject.idle_add(self.emit, 'added', songs)

    def removed(self, songs):
        if songs: gobject.idle_add(self.emit, 'removed', songs)

    def reload(self, song):
        try: song.reload()
        except Exception, err:
            traceback.print_exc()
            from library import library
            if library: library.remove(song)
            self.removed([song])
        else: self.changed([song])
