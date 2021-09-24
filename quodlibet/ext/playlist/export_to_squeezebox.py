# Copyright 2014-2021 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import _
from quodlibet import app
from quodlibet import qltk
from quodlibet.qltk.notif import Task
from quodlibet.qltk import Icons
from quodlibet.qltk.getstring import GetStringDialog
from quodlibet.util import copool
from quodlibet.util.dprint import print_d
from quodlibet.plugins.playlist import PlaylistPlugin
from quodlibet.ext._shared.squeezebox.base import SqueezeboxPluginMixin


class SqueezeboxPlaylistPlugin(PlaylistPlugin, SqueezeboxPluginMixin):
    PLUGIN_ID = "Export to Squeezebox Playlist"
    PLUGIN_NAME = _(u"Export to Squeezebox")
    PLUGIN_DESC_MARKUP = (
        _("Dynamically exports a playlist to Logitech Squeezebox "
          "playlist, provided both share a directory structure.") + "\n" +
        _("Shares configuration with <a href=\"%(plugin_link)s\">Squeezebox "
          "Sync plugin</a>.")
        % {"plugin_link": "quodlibet:///prefs/plugins/Squeezebox Output"}
    )
    PLUGIN_ICON = Icons.NETWORK_WORKGROUP
    ELLIPSIZE_NAME = True
    _PERSIST_FUDGE = 100

    TEMP_PLAYLIST = "_quodlibet"

    def __add_songs(self, task, songs, name):
        """Generator for copool to add songs to the temp playlist"""
        print_d("Backing up current Squeezebox playlist."
                "This can take a while if your current playlist is big...")
        self.__cancel = False
        # Arbitrarily assign playlist operations a value of 2 * addition
        task_total = float(len(songs) + 2 * self._PERSIST_FUDGE + 3 * 2)
        self.server.playlist_save(self.TEMP_PLAYLIST)
        task.update(self._PERSIST_FUDGE / task_total)
        yield True
        self.server.playlist_clear()
        task.update((self._PERSIST_FUDGE + 2.0) // task_total)
        yield True
        # Check if we're currently playing.
        stopped = self.server.is_stopped()
        total = len(songs)
        print_d("Adding %d song(s) to Squeezebox playlist. "
                "This might take a while..." % total)
        for i, song in enumerate(songs):
            if self.__cancel:
                print_d("Cancelled squeezebox export")
                self.__cancel = False
                break
            # Actually do the (slow) call
            self.server.playlist_add(self.get_sb_path(song))
            task.update(float(i) / task_total)
            yield True
        print_d("Saving Squeezebox playlist \"%s\"" % name)
        self.server.playlist_save(name)
        task.update((task_total - 2) / task_total)
        yield True
        # Resume if we actually stopped
        self.server.playlist_resume(self.TEMP_PLAYLIST, not stopped, True)
        task.finish()

    def __cancel_add(self):
        """Tell the copool to stop (adding songs)"""
        self.__cancel = True

    @staticmethod
    def __get_playlist_name(name="Quod Libet playlist"):
        dialog = GetStringDialog(None,
                                 _("Export playlist to Squeezebox"),
                                 _("Playlist name (will overwrite existing)"),
                                 button_label=_("_Save"),
                                 button_icon=Icons.DOCUMENT_SAVE)
        name = dialog.run(text=name)
        return name

    def plugin_playlist(self, playlist):
        self.init_server()
        if not self.server.is_connected:
            qltk.ErrorMessage(
                app.window,
                _("Error finding Squeezebox server"),
                _("Error finding %s. Please check settings") %
                self.server.config
            ).run()
        else:
            name = self.__get_playlist_name(name=playlist.name)
            if name:
                task = Task("Squeezebox", _("Export to Squeezebox playlist"),
                            stop=self.__cancel_add)
                copool.add(self.__add_songs, task, playlist.songs, name,
                           funcid="squeezebox-playlist-save")
