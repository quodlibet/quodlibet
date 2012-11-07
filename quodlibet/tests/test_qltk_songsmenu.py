from tests import TestCase, add

from quodlibet.formats._audio import AudioFile
from quodlibet.library import SongLibrary
from quodlibet.qltk.songsmenu import SongsMenu
import quodlibet.player

class TSongsMenu(TestCase):
    def setUp(self):
        self.library = SongLibrary()
        quodlibet.player.init("nullbe")
        self.device = quodlibet.player.init_device(self.library)
        
        self.songs = [AudioFile({"title": x}) for x in
                      ["song1", "song2", "song3"]]
        for song in self.songs: song.sanitize(song["title"])

    def test_empty(self):
        self.menu = SongsMenu(self.library, self.songs, plugins=False,
                              playlists=False, queue=False, devices=False,
                              remove=False, delete=False, edit=False)
        self.failUnlessEqual(0, len(self.menu))

    def test_simple(self):
        self.menu = SongsMenu(self.library, self.songs, plugins=False)

    def test_playlists(self):
        self.menu = SongsMenu(
            self.library, self.songs, plugins=False, playlists=True,
            queue=False, devices=False, remove=False, delete=False, edit=False)
        self.failUnlessEqual(1, len(self.menu))
        self.failUnless(self.menu.get_children()[0].props.sensitive)

        self.songs[0].can_add = False
        self.menu = SongsMenu(
            self.library, self.songs, plugins=False, playlists=True,
            queue=False, devices=False, remove=False, delete=False, edit=False)
        self.failUnlessEqual(1, len(self.menu))
        self.failIf(self.menu.get_children()[0].props.sensitive)

    def test_queue(self):
        self.menu = SongsMenu(
            self.library, self.songs, plugins=False, playlists=False,
            queue=True, devices=False, remove=False, delete=False, edit=False)
        self.failUnlessEqual(1, len(self.menu))
        self.failUnless(self.menu.get_children()[0].props.sensitive)

        self.songs[0].can_add = False
        self.menu = SongsMenu(
            self.library, self.songs, plugins=False, playlists=False,
            queue=True, devices=False, remove=False, delete=False, edit=False)
        self.failUnlessEqual(1, len(self.menu))
        self.failIf(self.menu.get_children()[0].props.sensitive)

    def test_devices(self):
        self.menu = SongsMenu(
            self.library, self.songs, plugins=False, playlists=False,
            queue=False, devices=True, remove=False, delete=False, edit=False)
        from quodlibet import browsers
        if browsers.media.MediaDevices in browsers.browsers:
            self.failUnlessEqual(1, len(self.menu))
        else:
            self.failUnlessEqual(0, len(self.menu))

    def test_remove(self):
        self.menu = SongsMenu(
            self.library, self.songs, plugins=False, playlists=False,
            queue=False, devices=False, remove=True, delete=False, edit=False)
        self.failUnlessEqual(1, len(self.menu))
        self.failIf(self.menu.get_children()[0].props.sensitive)

    def test_remove_sensitive(self):
        self.library.add(self.songs)
        self.menu = SongsMenu(
            self.library, self.songs, plugins=False, playlists=False,
            queue=False, devices=False, remove=True, delete=False, edit=False)
        self.failUnlessEqual(1, len(self.menu))
        self.failUnless(self.menu.get_children()[0].props.sensitive)

    def test_delete(self):
        self.menu = SongsMenu(
            self.library, self.songs, plugins=False, playlists=False,
            queue=False, devices=False, remove=False, delete=True, edit=False)
        self.failUnlessEqual(1, len(self.menu))
        self.failUnless(self.menu.get_children()[0].props.sensitive)

        self.songs[0].is_file = False
        self.menu = SongsMenu(
            self.library, self.songs, plugins=False, playlists=False,
            queue=False, devices=False, remove=False, delete=True, edit=False)
        self.failUnlessEqual(1, len(self.menu))
        self.failIf(self.menu.get_children()[0].props.sensitive)

    def tearDown(self):
        quodlibet.player.quit(self.device)
        self.library.destroy()
        try: self.menu.destroy()
        except AttributeError: pass
        else: del(self.menu)
add(TSongsMenu)
