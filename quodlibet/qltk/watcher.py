# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gobject, gtk

# Everything connects to this to get updates about the library and player.
# FIXME: This should be split up. The player should manage its signals
# itself. The library should manage its signals itself.
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

        # A new song started playing (or the current one was restarted).
        'song-started': SIG_PYOBJECT,

        # The song was seeked within.
        'seek': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                 (object, int)),

        # A new song started playing (or the current one was restarted).
        # The boolean is True if the song was stopped rather than simply
        # ended.
        'song-ended': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                       (object, bool)),

        # Playback was paused.
        'paused': SIG_NONE,

        # Playback was unpaused.
        'unpaused': SIG_NONE,

        }

    # (current_in_msec, total_in_msec)
    # (0, 1) when no song is playing.
    time = (0, 1)

    # the currently playing song.
    song = None

    def changed(self, songs):
        if songs: gobject.idle_add(self.emit, 'changed', songs)

    def added(self, songs):
        if songs: gobject.idle_add(self.emit, 'added', songs)

    def removed(self, songs):
        if songs: gobject.idle_add(self.emit, 'removed', songs)

    def song_started(self, song):
        try: self.time = (0, song["~#length"] * 1000)
        except (AttributeError, TypeError): self.time = (0, 1)
        self.song = song
        gobject.idle_add(self.emit, 'song-started', song)

    def song_ended(self, song, stopped):
        gobject.idle_add(self.emit, 'song-ended', song, stopped)

    def set_paused(self, paused):
        if paused: gobject.idle_add(self.emit, 'paused')
        else: gobject.idle_add(self.emit, 'unpaused')

    def seek(self, song, position_in_msec):
        gobject.idle_add(self.emit, 'seek', song, position_in_msec)

    def error(self, code, lock=False):
        from widgets import main
        from qltk.msg import ErrorMessage
        if lock: gtk.threads_enter()
        ErrorMessage(
            main, _("Unable to play song"),
            _("GStreamer was unable to load the selected song.")
            + "\n\n" + code).run()
        if lock: gtk.threads_leave()

    def reload(self, song):
        try: song.reload()
        except Exception, err:
            import traceback; traceback.print_exc()
            from library import library
            if library: library.remove(song)
            self.removed([song])
        else: self.changed([song])
