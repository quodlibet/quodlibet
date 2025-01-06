# Copyright 2006 Joe Wreschnig
#      2013-2014 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet.plugins.gui import MenuItemPlugin

from quodlibet.util.songwrapper import check_wrapper_changed


class SongsMenuPlugin(MenuItemPlugin):
    """Plugins of this type are subclasses of Gtk.ImageMenuItem.
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

    The singular version is called once for each selected song/album,
    whereas the plural version is called with a list of songs/albums.

    An album is a list of songs all with the same album, labelid,
    and/or musicbrainz_albumid tags (like in the Album List).

    To make your plugin insensitive if unsupported songs are selected,
    a method that takes a list of songs and returns True or False to set
    the sensitivity of the menu entry:
        self.plugin_handles(songs)

    All of this is managed by the constructor for SongsMenuPlugin, so
    make sure it gets called if you override it (you shouldn't have to).
    """

    plugin_single_song = None
    plugin_song = None
    plugin_songs = None
    plugin_single_album = None
    plugin_album = None
    plugin_albums = None

    def __init__(self, songs=None, library=None):
        super().__init__()
        self.__library = library
        self.__songs = songs or []

        self.set_sensitive(bool(self.plugin_handles(songs)))

    def plugin_handles(self, songs):
        return True

    @property
    def handles_albums(self):
        return any(
            map(
                callable,
                [self.plugin_single_album, self.plugin_album, self.plugin_albums],
            )
        )

    def plugin_finish(self):
        check_wrapper_changed(self.__library, self.__songs)
