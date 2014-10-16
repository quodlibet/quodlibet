from tests import TestCase
from helper import capture_output

import os

from gi.repository import Gtk

from quodlibet import config
from quodlibet import Application

from quodlibet.library import SongFileLibrary, SongLibrarian
from quodlibet.player.nullbe import NullPlayer
from quodlibet.qltk.songlist import PlaylistModel
from quodlibet.browsers.empty import EmptyBar
from quodlibet.remote import Remote
from quodlibet.commands import registry


class TRemoteControl(TestCase):
    def setUp(self):
        config.init()

        class App(Application):
            browser = None

        app = App()
        app.player = NullPlayer()
        app.player.setup(PlaylistModel(), None, 0)
        app.library = SongFileLibrary()
        app.library.librarian = SongLibrarian()
        app.browser = EmptyBar(app.library, True)
        app.window = Gtk.OffscreenWindow()

        self.fifo = Remote(app, registry)
        self.fifo.start()

    def tearDown(self):
        self.fifo.stop()
        config.quit()

    def __send(self, command):
        self.assertTrue(Remote.send_message(command), msg=command)
        while Gtk.events_pending():
            Gtk.main_iteration()

    def test_player(self):
        self.__send("previous")
        self.__send("force-previous")
        self.__send("next")
        self.__send("pause")
        self.__send("play-pause")
        self.__send("play")
        self.__send("stop")
        self.__send("volume +1000")
        self.__send("volume 40")
        self.__send("volume -10")

        self.__send("seek -10")
        self.__send("seek +10")
        self.__send("seek 0")

    def test_misc(self):
        if os.name == "nt":
            return

        #self.__send("add-directory /dev/null")
        with capture_output():
            self.__send("add-file /dev/null")
        #self.__send("dump-playlist /dev/null")
        #self.__send("dump_queue /dev/null")
        #self.__send("enqueue /dev/null")
        self.__send("enqueue-files /dev/null")
        self.__send("filter album=test")
        self.__send("query '/foobar/'")
        self.__send("focus")
        self.__send("hide-window")
        self.__send("dump-browsers /dev/null")
        self.__send("open-browser SearchBar")
        from quodlibet.qltk.browser import LibraryBrowser
        for window in Gtk.Window.list_toplevels():
            if isinstance(window, LibraryBrowser):
                window.destroy()
        #self.__send("order shuffle")
        self.__send("properties")
        #self.__send("queue 1")
        self.__send("quit")
        #self.__send("random album")
        self.__send("refresh")
        #self.__send("repeat 0")
        #self.__send("set-browser 1")
        self.__send("set-rating 0.5")
        self.__send("show-window")
        #self.__send("song-list 1")
        #self.__send("status /dev/null")
        self.__send("toggle-window")
        #self.__send("unqueue /dev/null")
