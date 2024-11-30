# Copyright 2012 Christoph Reiter
#           2020 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
from unittest.mock import Mock

import quodlibet.config
from quodlibet import app
from quodlibet.formats import AudioFile
from quodlibet.plugins.editing import EditTagsPlugin
from quodlibet.qltk.edittags import (SplitValues, SplitDisc, SplitTitle,
                                     SplitArranger, AddTagDialog,
                                     AudioFileGroup, EditTags, ListEntry,
                                     Comment, EditTagsPluginHandler)
from quodlibet.qltk.properties import SongProperties
from tests import TestCase, init_fake_app, destroy_fake_app


class DummyEditPlugin(EditTagsPlugin):
    activations = []

    def activated(self, tag, value):
        self.activations.append((tag, value))
        return super().activated(tag, value)


class TEditTags(TestCase):
    def setUp(self):
        init_fake_app()
        quodlibet.config.init()

    def tearDown(self):
        quodlibet.config.quit()
        destroy_fake_app()

    def test_items(self):
        SplitValues("foo", "bar").destroy()
        SplitDisc("foo", "bar").destroy()
        SplitTitle("foo", "bar").destroy()
        SplitArranger("foo", "bar").destroy()

    def test_addtag_dialog(self):
        AddTagDialog(None, ["artist"], app.library).destroy()

    def test_edit_tags_starts(self):
        props = SongProperties(app.library, [], quodlibet.app.window)
        EditTags(props, app.library)

    def test_edit_tags_popup_menu(self):
        song = AudioFile({"~filename": "/dev/null", "artist": "Person",
                          "album": "Dj Bars of FOO"})
        props = SongProperties(app.library, [song], app.window)
        box = EditTags(props, app.library)

        # Add a fake plugin
        plugin_cls = DummyEditPlugin
        box.handler = Mock(EditTagsPluginHandler)
        box.handler.plugins = [plugin_cls]
        model = box._view.get_model()

        # Make sure there's a row
        tag, value = "artist", song("artist")
        entry = ListEntry(tag, Comment(value))
        model.append(row=[entry])

        box._group_info = AudioFileGroup([song])
        box._view.select_by_func(lambda _: True)
        # Prevent weird mouse stuff failing in tests
        box._view.ensure_popup_selection = lambda: False
        box._popup_menu(box._view, props)
        box.show()
        assert plugin_cls.activations == [(tag, value)]


class GroupSong(AudioFile):

    def __init__(self, can_multiple: bool = True,
                 can_change: bool = True, cant_change: list[str] | None = None):
        self._can_multiple = can_multiple
        self._can_change = can_change
        self._cant_change = cant_change or []

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
        assert group.can_multiple_values() is True
        assert group.can_multiple_values("foo") is True

        group = AudioFileGroup([GroupSong(["ha"]), GroupSong(True)])
        self.assertEqual(group.can_multiple_values(), {"ha"})
        assert not group.can_multiple_values("foo")
        assert group.can_multiple_values("ha")

        group = AudioFileGroup([GroupSong(["foo", "ha"]), GroupSong(["ha"])])
        self.assertEqual(group.can_multiple_values(), {"ha"})
        assert not group.can_multiple_values("foo")
        assert group.can_multiple_values("ha")

    def test_can_change(self):
        group = AudioFileGroup(
            [GroupSong(can_change=True), GroupSong(can_change=True)])
        assert group.can_change() is True
        assert group.can_change("foo") is True

        group = AudioFileGroup(
            [GroupSong(can_change=["foo", "ha"]),
             GroupSong(can_change=["ha"])])
        self.assertEqual(group.can_change(), {"ha"})
        assert not group.can_change("foo")
        assert group.can_change("ha")

        group = AudioFileGroup([GroupSong(), GroupSong(cant_change=["baz"])])
        assert group.can_change()
        assert not group.can_change("baz")
