# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import pytest

from tests import TestCase

from gi.repository import Gtk

from quodlibet.util import copool


class Tcopool(TestCase):
    def setUp(self):
        self.buffer = None
        self.go = True

    def tearDown(self):
        copool.remove_all()

    def __set_buffer(self):
        while self.go:
            self.buffer = True
            yield None

    def _assert_eventually(self, value):
        for i in range(200):
            if self.buffer is value:
                return
            Gtk.main_iteration_do(False)
        assert self.buffer is value

    def _assert_never(self, value):
        for i in range(200):
            Gtk.main_iteration_do(False)
        assert self.buffer is not value

    def test_add_remove(self):
        copool.add(self.__set_buffer)
        self._assert_eventually(True)
        copool.remove(self.__set_buffer)
        self.buffer = None
        self._assert_eventually(None)

    def test_add_remove_with_funcid(self):
        copool.add(self.__set_buffer, funcid="test")
        self._assert_eventually(True)
        copool.remove("test")
        self.buffer = None
        self._assert_eventually(None)

    def test_pause_resume(self):
        copool.add(self.__set_buffer)
        self._assert_eventually(True)
        copool.pause(self.__set_buffer)
        self.buffer = None
        self._assert_never(True)
        copool.resume(self.__set_buffer)
        self._assert_eventually(True)
        copool.remove(self.__set_buffer)
        self.buffer = None
        self._assert_never(True)

    def test_pause_resume_with_funcid(self):
        self.buffer = None
        copool.add(self.__set_buffer, funcid="test")
        self._assert_eventually(True)
        copool.pause("test")
        self.buffer = None
        self._assert_never(True)
        copool.resume("test")
        copool.resume("test")
        self._assert_eventually(True)
        copool.remove("test")
        self.buffer = None
        self._assert_never(True)

    def test_pause_restart_pause(self):
        self.buffer = None
        copool.add(self.__set_buffer, funcid="test")
        self._assert_eventually(True)
        copool.pause("test")
        self.buffer = None
        self._assert_never(True)
        copool.add(self.__set_buffer, funcid="test")
        self._assert_eventually(True)
        copool.pause("test")
        self.buffer = None
        self._assert_never(True)

    def test_pause_all(self):
        self.buffer = None
        copool.add(self.__set_buffer, funcid="test")
        self._assert_eventually(True)
        copool.pause_all()
        self.buffer = None
        self._assert_never(True)

    def test_step(self):
        copool.add(self.__set_buffer, funcid="test")
        copool.pause("test")
        assert copool.step("test")
        self.go = False
        assert not copool.step("test")
        with pytest.raises(ValueError):
            copool.step("test")

    def test_timeout(self):
        copool.add(self.__set_buffer, funcid="test", timeout=100)
        copool.pause("test")
        copool.resume("test")
        copool.remove("test")
        with pytest.raises(ValueError):
            copool.step("test")
