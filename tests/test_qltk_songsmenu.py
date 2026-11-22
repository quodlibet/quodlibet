# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import quodlibet.player
from quodlibet import config
from quodlibet.formats import AudioFile
from quodlibet.formats.remote import RemoteFile
from quodlibet.library import SongFileLibrary
from quodlibet.qltk.songsmenu import SongsMenu
from quodlibet.fsn import fsnative
from tests import TestCase, mkdtemp


def an_af(i: int) -> AudioFile:
    return AudioFile({"~filename": "/dev/null", "title": "http://example.com/%0d" % i})


def an_rf(i: int) -> AudioFile:
    return RemoteFile(f"https://example.com/{i}.mp3")


def action(menu: SongsMenu, name: str):
    return menu._actions.lookup_action(name)


class TSongsMenu(TestCase):
    def _confirmer(self, *args):
        self.confirmed = True
        return False

    def setUp(self):
        config.init()
        self.library = SongFileLibrary()
        backend = quodlibet.player.init_backend("nullbe")
        self.device = backend.init(self.library)

        self.songs = [AudioFile({"title": x}) for x in ["song1", "song2", "song3"]]
        for song in self.songs:
            song.sanitize(fsnative(str(song["title"])))
        self.confirmed = False

    def test_empty(self):
        menu = self.empty_menu_with()
        assert menu.get_menu_model().get_n_items() == 0

    def test_simple(self):
        SongsMenu(self.library, self.songs, plugins=False)

    def test_playlists(self):
        menu = self.empty_menu_with(playlists=True)
        assert action(menu, "playlist-new").get_enabled()

        self.songs[0].can_add = False
        menu = self.empty_menu_with(playlists=True)
        assert not action(menu, "playlist-new").get_enabled()

    def test_queue(self):
        menu = self.empty_menu_with(queue=True)
        assert action(menu, "queue").get_enabled()

        self.songs[0].can_add = False
        menu = self.empty_menu_with(queue=True)
        assert not action(menu, "queue").get_enabled()

    def test_remove(self):
        menu = self.empty_menu_with(remove=True, removal_confirmer=self._confirmer)
        remove = action(menu, "remove")
        assert not remove.get_enabled(), "songs are not in the library"
        remove.set_enabled(True)
        remove.activate(None)
        assert self.confirmed, "Should have confirmed song removal"

    def test_remove_sensitive(self):
        self.library.add(self.songs)
        menu = self.empty_menu_with(remove=True)
        assert action(menu, "remove").get_enabled()

    def test_delete(self):
        menu = self.empty_menu_with(delete=True)
        assert action(menu, "delete").get_enabled()

        self.songs[0].is_file = False
        menu = self.empty_menu_with(delete=True)
        assert not action(menu, "delete").get_enabled()

    def test_show_files(self):
        menu = self.empty_menu_with(show_files=True)
        assert action(menu, "show-files").get_enabled()

    def test_show_files_remote_songs(self):
        self.songs = self.library.songs = [an_rf(1)]
        menu = self.empty_menu_with(show_files=True)
        assert action(menu, "show-files") is None
        assert menu.get_menu_model().get_n_items() == 0

    def test_show_files_too_many_songs(self):
        self.songs = self.library.songs = [an_af(i) for i in range(50)]
        menu = self.empty_menu_with(show_files=True)
        self.assertFalse(
            action(menu, "show-files").get_enabled(),
            msg="Should have disabled show files for 50 files",
        )

    def test_download(self):
        def choose(*args, **kwargs):
            return [mkdtemp()]

        self.songs = self.library.songs = [an_rf(i) for i in range(3)]
        menu = self.empty_menu_with(download=True, folder_chooser=choose)
        assert action(menu, "download").get_enabled(), "download disabled for remotes"

    def empty_menu_with(
        self,
        plugins=False,
        playlists=False,
        queue=False,
        remove=False,
        delete=False,
        edit=False,
        info=False,
        ratings=False,
        show_files=False,
        download=False,
        removal_confirmer=None,
        folder_chooser=None,
    ):
        return SongsMenu(
            self.library,
            self.songs,
            plugins=plugins,
            playlists=playlists,
            queue=queue,
            remove=remove,
            delete=delete,
            edit=edit,
            info=info,
            ratings=ratings,
            show_files=show_files,
            removal_confirmer=removal_confirmer,
            download=download,
            folder_chooser=folder_chooser,
        )

    def tearDown(self):
        self.device.destroy()
        self.library.destroy()
        config.quit()
