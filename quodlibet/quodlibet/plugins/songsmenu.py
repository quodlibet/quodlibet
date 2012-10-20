# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk

from quodlibet.util.songwrapper import check_wrapper_changed


class SongsMenuPlugin(gtk.ImageMenuItem):
    """Plugins of this type are subclasses of gtk.ImageMenuItem.
    They will be added, in alphabetical order, to the "Plugins" menu
    that appears when songs or lists of songs are right-clicked.
    They provide one or more of the following instance methods:
    
        self.plugin_single_song(song)
        self.plugin_song(song)
        self.plugin_songs(songs)
        self.plugin_single_album(album)
        self.plugin_album(album)
        self.plugin_albums(albums)

    All matching provided callables on a single object are called in the
    above order if they match until one returns a true value. They are
    not called with real AudioFile objects, but rather wrappers that
    automatically detect metadata or disk changes, and save or reload
    the files as appropriate. If the wrappers get changed after the above
    methods return, call self.plugin_finish() to check for changes.

    The single_ variant is only called if a single song/album is selected.

    The singular tense is called once for each selected song/album, but the
    plural tense is called with a list of songs/albums.

    An album is a list of songs all with the same album, labelid,
    and/or musicbrainz_albumid tags (like in the Album List).

    To make your plugin insensitive if unsupported songs are selected,
    a method that takes a list of songs and returns True or False to set
    the sensitivity of the menu entry:
        self.plugin_handles(songs)

    When these functions are called, the self.plugin_window will be
    available. This is the gtk.Window the plugin was invoked from. This
    provides access to two important widgets, self.plugin_window.browser
    and self.plugin_window.songlist.

    All of this is managed by the constructor for SongsMenuPlugin, so
    make sure it gets called if you override it (you shouldn't have to).
    """

    plugin_single_song = None
    plugin_song = None
    plugin_songs = None
    plugin_single_album = None
    plugin_album = None
    plugin_albums = None

    __initialized = False
    def __init__(self, songs, library, window):
        super(SongsMenuPlugin, self).__init__(self.PLUGIN_NAME)
        self.__library = library
        self.__songs = songs
        self.plugin_window = window
        self.__initialized = True
        try: i = gtk.image_new_from_stock(self.PLUGIN_ICON, gtk.ICON_SIZE_MENU)
        except AttributeError: pass
        else: self.set_image(i)
        self.set_sensitive(bool(self.plugin_handles(songs)))

    @property
    def initialized(self):
        # If the GObject __init__ method is bypassed, it can cause segfaults.
        # This explicitly prevents a bad plugin from taking down the app.
        return self.__initialized

    def plugin_handles(self, songs):
        return True

    def plugin_finish(self):
        check_wrapper_changed(self.__library, self.plugin_window, self.__songs)
