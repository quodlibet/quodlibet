from tests import add, TestCase

import os
import gtk

from quodlibet import const
from quodlibet import config

from quodlibet.formats._audio import AudioFile
from quodlibet.library import SongFileLibrary
from quodlibet.player.nullbe import NullPlayer
from quodlibet.qltk.remote import FSInterface, FIFOControl


class TFSInterface(TestCase):
    def setUp(self):
        self.p = NullPlayer()
        self.fs = FSInterface(self.p)

    def do(self):
        while gtk.events_pending(): gtk.main_iteration()

    def test_init(self):
        self.do()
        self.failIf(os.path.exists(const.CURRENT))

    def test_start(self):
        self.p.emit('song_started', AudioFile({"woo": "bar", "~#length": 10}))
        self.do()
        self.failUnless("woo=bar\n" in file(const.CURRENT).read())

    def test_song_ended(self):
        self.p.emit('song-started', AudioFile({"woo": "bar", "~#length": 10}))
        self.do()
        self.p.emit('song-ended', {}, False)
        self.do()
        self.failIf(os.path.exists(const.CURRENT))

    def tearDown(self):
        self.p.destroy()
        try: os.unlink(const.CURRENT)
        except EnvironmentError: pass
add(TFSInterface)


class TFIFOControl(TestCase):
    def setUp(self):
        config.init()
        self.p = NullPlayer()
        self.l = SongFileLibrary()
        self.w = gtk.Window()
        self.fifo = FIFOControl(self.l, self.w, self.p)

    def tearDown(self):
        self.p.destroy()
        self.l.destroy()
        self.w.destroy()
        config.quit()

    def __send(self, command):
        f = open(const.CONTROL, "wb")
        f.write(command)
        f.close()
        while gtk.events_pending():
            gtk.main_iteration()

    def test_player(self):
        self.__send("previous")
        self.__send("force_previous")
        self.__send("next")
        self.__send("pause")
        self.__send("play-pause")
        self.__send("stop")
        self.__send("volume +1000")
        self.__send("volume 40")
        self.__send("volume -10")

        #self.__send("seek -10")
        #self.__send("seek +10")
        #self.__send("seek 0")

    def test_misc(self):
        #self.__send("add-directory /dev/null")
        self.__send("add-file /dev/null")
        #self.__send("dump-playlist /dev/null")
        #self.__send("dump_queue /dev/null")
        #self.__send("enqueue /dev/null")
        self.__send("enqueue-files /dev/null")
        #self.__send("filter album=test")
        #self.__send("focus")
        #self.__send("hide-window")
        #self.__send("open-browser 1")
        #self.__send("order shuffle")
        self.__send("properties")
        #self.__send("queue 1")
        self.__send("quit")
        #self.__send("random album")
        #self.__send("refresh")
        #self.__send("repeat 0")
        #self.__send("set-browser 1")
        self.__send("set-rating 0.5")
        #self.__send("show-window")
        #self.__send("song-list 1")
        #self.__send("status /dev/null")
        #self.__send("toggle-window")
        #self.__send("unqueue /dev/null")

add(TFIFOControl)
