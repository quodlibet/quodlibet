# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gobject

# Browers are how the audio library is presented to the user; they
# create the list of songs that MainSongList is filled with, and pass
# them back via a callback function.
class Browser(object):
    # Unfortunately, GObjects do not play with Python multiple inheritance.
    # So, we need to reasssign this in every subclass.
    __gsignals__ = {
        'songs-selected':
        (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object, object))
        }

    # Packing options. False if the browser should be packed into the
    # window's VBox with expand=False. Otherwise, this should be
    # a function that returns an object like an RPaned; the browser
    # and MainSongList are both packed into it.
    expand = False # Packing options

    # If true, the global filter will be applied by MainSongList to
    # the songs returned.
    background = True

    # A list of column headers to display; None means all are okay.
    headers = None

    # Per-browser remote commands.
    commands = {}

    # Called after library and MainWindow initialization, before the
    # GTK main loop starts.
    def init(klass, watcher): pass
    init = classmethod(init)

    # Returns true if the song should remain on the song list. Used to
    # implement dynamic playlist removal when a song ends.
    def dynamic(self, song): return True

    # Save/restore selected songlist. Browsers should save whatever
    # they need to recreate the criteria for the current song list (not
    # the list itself). restore is called at startup if the browser
    # is the first loaded.
    def save(self): raise NotImplementedError
    def restore(self): raise NotImplementedError

    # Decides whether "filter on foo" menu entries are available.
    def can_filter(self, key): return False

    # Actually do the filtering (with a union of values).
    def filter(self, key, values): raise NotImplementedError

    # Scroll to something related to the given song.
    def scroll(self, song): pass

    # Do whatever is needed to emit songs-selected again.
    def activate(self): raise NotImplementedError

    # Called when the song list is reordered. If it's not callable
    # but true, no call is made but the song list is still reorderable.
    # def reordered(self, songlist): ...
    reordered = None

    # Called with the SongList and a list of songs when songs are dropped
    # but the song list does not support reordering. Adding the songs to
    # the list is the browser's responsibility. This function should
    # return True if the drop was successful.
    # def dropped(self, songlist, songs): ... return True
    dropped = None

    # An AccelGroup that is added to / removed from the window where
    # the browser is.
    accelerators = None

    # Returns a list of items to be inserted into the SongList context
    # menu when this browser is active. songs is the list of selected
    # songs; songlist is the SongList instance.
    def Menu(self, songs, songlist): return []

    def statusbar(self, i):
        return ngettext(
            "%(count)d song (%(time)s)", "%(count)d songs (%(time)s)", i)

    def list(self, tag):
        from library import library
        return library.tag_values(tag)
