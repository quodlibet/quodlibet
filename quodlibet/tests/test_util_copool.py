from tests import TestCase, add

import gtk
from quodlibet.util import copool

class Tcopool(TestCase):
    def setUp(self):
        while gtk.events_pending(): gtk.main_iteration()
        self.buffer = None

    def tearDown(self):
        copool.remove_all()

    def __set_buffer(self):
        while True:
            self.buffer = True
            yield None

    def test_add_remove(self):
        copool.add(self.__set_buffer)
        gtk.main_iteration(block=False)
        gtk.main_iteration(block=False)
        self.assertEquals(self.buffer, True)
        copool.remove(self.__set_buffer)
        self.buffer = None
        gtk.main_iteration(block=False)
        gtk.main_iteration(block=False)
        self.assertEquals(self.buffer, None)

    def test_add_remove_with_funcid(self):
        copool.add(self.__set_buffer, funcid="test")
        gtk.main_iteration(block=False)
        gtk.main_iteration(block=False)
        self.assertEquals(self.buffer, True)
        copool.remove("test")
        self.buffer = None
        gtk.main_iteration(block=False)
        gtk.main_iteration(block=False)
        self.assertEquals(self.buffer, None)

    def test_pause_resume(self):
        copool.add(self.__set_buffer)
        gtk.main_iteration(block=False)
        gtk.main_iteration(block=False)
        copool.pause(self.__set_buffer)
        self.buffer = None
        gtk.main_iteration(block=False)
        gtk.main_iteration(block=False)
        self.assertEquals(self.buffer, None)
        copool.resume(self.__set_buffer)
        gtk.main_iteration(block=False)
        gtk.main_iteration(block=False)
        self.assertEquals(self.buffer, True)
        copool.remove(self.__set_buffer)
        self.buffer = None
        gtk.main_iteration(block=False)
        gtk.main_iteration(block=False)

    def test_pause_resume_with_funcid(self):
        copool.add(self.__set_buffer, funcid="test")
        gtk.main_iteration(block=False)
        gtk.main_iteration(block=False)
        copool.pause("test")
        self.buffer = None
        gtk.main_iteration(block=False)
        gtk.main_iteration(block=False)
        self.assertEquals(self.buffer, None)
        copool.resume("test")
        gtk.main_iteration(block=False)
        gtk.main_iteration(block=False)
        self.assertEquals(self.buffer, True)
        copool.remove("test")
        self.buffer = None
        gtk.main_iteration(block=False)
        gtk.main_iteration(block=False)

    def test_pause_restart_pause(self):
        copool.add(self.__set_buffer, funcid="test")
        gtk.main_iteration(block=False)
        gtk.main_iteration(block=False)
        self.failUnless(self.buffer)
        copool.pause("test")
        self.buffer = None
        gtk.main_iteration(block=False)
        gtk.main_iteration(block=False)
        self.failIf(self.buffer)
        copool.add(self.__set_buffer, funcid="test")
        gtk.main_iteration(block=False)
        gtk.main_iteration(block=False)
        self.failUnless(self.buffer)
        copool.pause("test")
        self.buffer = None
        gtk.main_iteration(block=False)
        gtk.main_iteration(block=False)
        self.failIf(self.buffer)

add(Tcopool)
