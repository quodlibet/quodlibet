from tests import TestCase, add

from formats._audio import AudioFile
from qltk.songsmenu import SongsMenu
from qltk.watcher import SongWatcher

class TSongsMenu(TestCase):
    def setUp(self):
        self.watcher = SongWatcher()
        self.songs = [AudioFile({"title": x}) for x in
                      ["song1", "song2", "song3"]]
        for song in self.songs: song.sanitize(song["title"])

    def test_empty(self):
        self.menu = SongsMenu(self.watcher, self.songs, plugins=False,
                              playlists=False, queue=False, remove=False,
                              delete=False, edit=False)
        self.failUnlessEqual(0, len(self.menu))

    def test_simple(self):
        self.menu = SongsMenu(self.watcher, self.songs, plugins=False)

    def test_playlists(self):
        self.menu = SongsMenu(
            self.watcher, self.songs, plugins=False, playlists=True,
            queue=False, remove=False, delete=False, edit=False)
        self.failUnlessEqual(1, len(self.menu))
        self.failUnless(self.menu.get_children()[0].props.sensitive)

        self.songs[0].can_add = False
        self.menu = SongsMenu(
            self.watcher, self.songs, plugins=False, playlists=True,
            queue=False, remove=False, delete=False, edit=False)
        self.failUnlessEqual(1, len(self.menu))
        self.failIf(self.menu.get_children()[0].props.sensitive)

    def test_queue(self):
        self.menu = SongsMenu(
            self.watcher, self.songs, plugins=False, playlists=False,
            queue=True, remove=False, delete=False, edit=False)
        self.failUnlessEqual(1, len(self.menu))
        self.failUnless(self.menu.get_children()[0].props.sensitive)

        self.songs[0].can_add = False
        self.menu = SongsMenu(
            self.watcher, self.songs, plugins=False, playlists=False,
            queue=True, remove=False, delete=False, edit=False)
        self.failUnlessEqual(1, len(self.menu))
        self.failIf(self.menu.get_children()[0].props.sensitive)

    def test_remove(self):
        # FIXME: Mock a fake library to test should-be-sensitive case.
        self.menu = SongsMenu(
            self.watcher, self.songs, plugins=False, playlists=False,
            queue=False, remove=True, delete=False, edit=False)
        self.failUnlessEqual(1, len(self.menu))
        self.failIf(self.menu.get_children()[0].props.sensitive)

    def test_delete(self):
        self.menu = SongsMenu(
            self.watcher, self.songs, plugins=False, playlists=False,
            queue=False, remove=False, delete=True, edit=False)
        self.failUnlessEqual(1, len(self.menu))
        self.failUnless(self.menu.get_children()[0].props.sensitive)

        self.songs[0].is_file = False
        self.menu = SongsMenu(
            self.watcher, self.songs, plugins=False, playlists=False,
            queue=False, remove=False, delete=True, edit=False)
        self.failUnlessEqual(1, len(self.menu))
        self.failIf(self.menu.get_children()[0].props.sensitive)

    def tearDown(self):
        self.watcher.destroy()
        try: self.menu.destroy()
        except AttributeError: pass
        else: del(self.menu)
add(TSongsMenu)
