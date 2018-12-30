# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase

from quodlibet.qltk.edittags import SplitValues, SplitDisc, SplitTitle, \
    SplitArranger, AddTagDialog, AudioFileGroup
from quodlibet.formats import AudioFile
from quodlibet.library import SongLibrary
import quodlibet.config


class TEditTags(TestCase):
    def setUp(self):
        quodlibet.config.init()

    def tearDown(self):
        quodlibet.config.quit()

    def test_items(self):
        SplitValues("foo", "bar").destroy()
        SplitDisc("foo", "bar").destroy()
        SplitTitle("foo", "bar").destroy()
        SplitArranger("foo", "bar").destroy()

    def test_addtag_dialog(self):
        lib = SongLibrary()
        AddTagDialog(None, ["artist"], lib).destroy()


class GroupSong(AudioFile):

    def __init__(self, can_multiple=True, can_change=True, cant_change=[]):
        self._can_multiple = can_multiple
        self._can_change = can_change
        self._cant_change = cant_change

    def can_multiple_values(self, key=None):
        if key is None:
            return self._can_multiple
        if self._can_multiple is True:
            return True
        return key in self._can_multiple

    def can_change(self, key=None):
        if key is None:
            return self._can_change
        if self._can_change is True:
            return key not in self._cant_change
        return key in self._can_change


class TAudioFileGroup(TestCase):

    def test_multiple_values(self):
        group = AudioFileGroup([GroupSong(True), GroupSong(True)])
        self.assertTrue(group.can_multiple_values() is True)
        self.assertTrue(group.can_multiple_values("foo") is True)

        group = AudioFileGroup([GroupSong(["ha"]), GroupSong(True)])
        self.assertEqual(group.can_multiple_values(), {"ha"})
        self.assertFalse(group.can_multiple_values("foo"))
        self.assertTrue(group.can_multiple_values("ha"))

        group = AudioFileGroup([GroupSong(["foo", "ha"]), GroupSong(["ha"])])
        self.assertEqual(group.can_multiple_values(), {"ha"})
        self.assertFalse(group.can_multiple_values("foo"))
        self.assertTrue(group.can_multiple_values("ha"))

    def test_can_change(self):
        group = AudioFileGroup(
            [GroupSong(can_change=True), GroupSong(can_change=True)])
        self.assertTrue(group.can_change() is True)
        self.assertTrue(group.can_change("foo") is True)

        group = AudioFileGroup(
            [GroupSong(can_change=["foo", "ha"]),
             GroupSong(can_change=["ha"])])
        self.assertEqual(group.can_change(), {"ha"})
        self.assertFalse(group.can_change("foo"))
        self.assertTrue(group.can_change("ha"))

        group = AudioFileGroup([GroupSong(), GroupSong(cant_change=["baz"])])
        self.assertTrue(group.can_change())
        self.assertFalse(group.can_change("baz"))
