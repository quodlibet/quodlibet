# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase

from gi.repository import Gtk

from quodlibet.util import copool


class Tcopool(TestCase):
    def setUp(self):
        while Gtk.events_pending():
            Gtk.main_iteration()
        self.buffer = None
        self.go = True

    def tearDown(self):
        copool.remove_all()

    def __set_buffer(self):
        while self.go:
            self.buffer = True
            yield None

    def test_add_remove(self):
        copool.add(self.__set_buffer)
        Gtk.main_iteration_do(False)
        Gtk.main_iteration_do(False)
        self.assertEquals(self.buffer, True)
        copool.remove(self.__set_buffer)
        self.buffer = None
        Gtk.main_iteration_do(False)
        Gtk.main_iteration_do(False)
        self.assertEquals(self.buffer, None)

    def test_add_remove_with_funcid(self):
        copool.add(self.__set_buffer, funcid="test")
        Gtk.main_iteration_do(False)
        Gtk.main_iteration_do(False)
        self.assertEquals(self.buffer, True)
        copool.remove("test")
        self.buffer = None
        Gtk.main_iteration_do(False)
        Gtk.main_iteration_do(False)
        self.assertEquals(self.buffer, None)

    def test_pause_resume(self):
        copool.add(self.__set_buffer)
        Gtk.main_iteration_do(False)
        Gtk.main_iteration_do(False)
        copool.pause(self.__set_buffer)
        self.buffer = None
        Gtk.main_iteration_do(False)
        Gtk.main_iteration_do(False)
        self.assertEquals(self.buffer, None)
        copool.resume(self.__set_buffer)
        Gtk.main_iteration_do(False)
        Gtk.main_iteration_do(False)
        self.assertEquals(self.buffer, True)
        copool.remove(self.__set_buffer)
        self.buffer = None
        Gtk.main_iteration_do(False)
        Gtk.main_iteration_do(False)

    def test_pause_resume_with_funcid(self):
        copool.add(self.__set_buffer, funcid="test")
        Gtk.main_iteration_do(False)
        Gtk.main_iteration_do(False)
        copool.pause("test")
        self.buffer = None
        Gtk.main_iteration_do(False)
        Gtk.main_iteration_do(False)
        self.assertEquals(self.buffer, None)
        copool.resume("test")
        copool.resume("test")
        Gtk.main_iteration_do(False)
        Gtk.main_iteration_do(False)
        self.assertEquals(self.buffer, True)
        copool.remove("test")
        self.buffer = None
        Gtk.main_iteration_do(False)
        Gtk.main_iteration_do(False)

    def test_pause_restart_pause(self):
        copool.add(self.__set_buffer, funcid="test")
        Gtk.main_iteration_do(False)
        Gtk.main_iteration_do(False)
        self.failUnless(self.buffer)
        copool.pause("test")
        self.buffer = None
        Gtk.main_iteration_do(False)
        Gtk.main_iteration_do(False)
        self.failIf(self.buffer)
        copool.add(self.__set_buffer, funcid="test")
        Gtk.main_iteration_do(False)
        Gtk.main_iteration_do(False)
        self.failUnless(self.buffer)
        copool.pause("test")
        self.buffer = None
        Gtk.main_iteration_do(False)
        Gtk.main_iteration_do(False)
        self.failIf(self.buffer)

    def test_pause_all(self):
        copool.add(self.__set_buffer, funcid="test")
        Gtk.main_iteration_do(False)
        Gtk.main_iteration_do(False)
        self.failUnless(self.buffer)
        copool.pause_all()
        self.buffer = None
        Gtk.main_iteration_do(False)
        Gtk.main_iteration_do(False)
        self.failIf(self.buffer)

    def test_step(self):
        copool.add(self.__set_buffer, funcid="test")
        copool.pause("test")
        self.assertTrue(copool.step("test"))
        self.go = False
        self.assertFalse(copool.step("test"))
        self.assertRaises(ValueError, copool.step, "test")

    def test_timeout(self):
        copool.add(self.__set_buffer, funcid="test", timeout=100)
        copool.pause("test")
        copool.resume("test")
        copool.remove("test")
        self.assertRaises(ValueError, copool.step, "test")
