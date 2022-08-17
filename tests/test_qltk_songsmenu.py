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
from senf import fsnative
from tests import TestCase, mkdtemp


def an_af(i: int) -> AudioFile:
    return AudioFile({"~filename": "/dev/null",
                      "title": "http://example.com/%0d" % i})


def an_rf(i: int) -> AudioFile:
    return RemoteFile(f"https://example.com/{i}.mp3")


class TSongsMenu(TestCase):

    def _confirmer(self, *args):
        self.confirmed = True
        return False

    def setUp(self):
        config.init()
        self.library = SongFileLibrary()
        backend = quodlibet.player.init_backend("nullbe")
        self.device = backend.init(self.library)

        self.songs = [AudioFile({"title": x}) for x in
                      ["song1", "song2", "song3"]]
        for song in self.songs:
            song.sanitize(fsnative(str(song["title"])))
        self.confirmed = False

    def test_empty(self):
        self.menu = self.empty_menu_with()
        self.failIf(len(self.menu))

    def test_simple(self):
        self.menu = SongsMenu(self.library, self.songs, plugins=False)

    def test_playlists(self):
        self.menu = self.empty_menu_with(playlists=True)
        self.failUnlessEqual(len(self.menu), 1)
        self.failUnless(self.menu.get_children()[0].props.sensitive)

        self.songs[0].can_add = False
        self.menu = self.empty_menu_with(playlists=True)
        self.failUnlessEqual(len(self.menu), 1)
        self.failIf(self.menu.get_children()[0].props.sensitive)

    def test_queue(self):
        self.menu = self.empty_menu_with(queue=True)
        self.failUnlessEqual(len(self.menu), 1)
        self.failUnless(self.menu.get_children()[0].props.sensitive)

        self.songs[0].can_add = False
        self.menu = self.empty_menu_with(queue=True)
        self.failUnlessEqual(len(self.menu), 1)
        self.failIf(self.menu.get_children()[0].props.sensitive)

    def test_remove(self):
        self.menu = self.empty_menu_with(remove=True,
                                         removal_confirmer=self._confirmer)
        self.failUnlessEqual(len(self.menu), 1)
        item = self.menu.get_children()[0]
        self.failIf(item.props.sensitive)
        item.activate()
        self.failUnless(self.confirmed, "Should have confirmed song removal")

    def test_remove_sensitive(self):
        self.library.add(self.songs)
        self.menu = self.empty_menu_with(remove=True)
        self.failUnlessEqual(len(self.menu), 1)
        self.failUnless(self.menu.get_children()[0].props.sensitive)

    def test_delete(self):
        self.menu = self.empty_menu_with(delete=True)
        self.failUnlessEqual(len(self.menu), 1)
        self.failUnless(self.menu.get_children()[0].props.sensitive)

        self.songs[0].is_file = False
        self.menu = self.empty_menu_with(delete=True)
        self.failIf(self.menu.get_children()[0].props.sensitive)

    def test_show_files(self):
        self.menu = self.empty_menu_with(show_files=True)
        self.failUnlessEqual(len(self.menu), 1)
        self.failUnless(self.menu.get_children()[0].props.sensitive)
        item = self.menu.get_children()[0]
        self.failUnless(item.props.sensitive)

    def test_show_files_remote_songs(self):
        self.songs = self.library.songs = [an_rf(1)]
        self.menu = self.empty_menu_with(show_files=True)
        self.failIf(len(self.menu))

    def test_show_files_too_many_songs(self):
        self.songs = self.library.songs = [an_af(i) for i in range(50)]
        self.menu = self.empty_menu_with(show_files=True)
        item = self.menu.get_children()[0]
        self.failIf(item.props.sensitive,
                    msg="Should have disabled show files for 50 files")

    def test_download(self):
        def choose(*args, **kwargs):
            return [mkdtemp()]
        self.songs = self.library.songs = [an_rf(i) for i in range(3)]
        self.menu = self.empty_menu_with(download=True, folder_chooser=choose)
        last = self.menu.get_children()[-1]
        assert last.props.sensitive, "should have enabled download for remotes"
        # TODO: some useful assertions, without needing a UI

    def empty_menu_with(self, plugins=False, playlists=False, queue=False,
                        remove=False, delete=False, edit=False, info=False,
                        ratings=False, show_files=False, download=False,
                        removal_confirmer=None, folder_chooser=None):
        return SongsMenu(self.library, self.songs, plugins=plugins, playlists=playlists,
                         queue=queue, remove=remove, delete=delete, edit=edit,
                         info=info, ratings=ratings, show_files=show_files,
                         removal_confirmer=removal_confirmer,
                         download=download, folder_chooser=folder_chooser)

    def tearDown(self):
        self.device.destroy()
        self.library.destroy()
        try:
            self.menu.destroy()
        except AttributeError:
            pass
        else:
            del(self.menu)
        config.quit()
