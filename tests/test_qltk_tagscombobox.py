# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase, skipIf

from quodlibet.util.tags import USER_TAGS
from quodlibet.qltk import is_wayland


class TagsCombo(TestCase):
    def setUp(self):
        self.all = self.Kind()
        self.some = self.Kind(["artist", "album", "~people", "foobar"])

    def tearDown(self):
        self.all.destroy()
        self.some.destroy()


class TagsComboMixin:
    def test_none(self):
        self.assertRaises(ValueError, self.Kind, [])

    def test_some(self):
        self.some.set_active(2)
        self.assertEqual(self.some.tag, "foobar")

    def test_all(self):
        tags = list(USER_TAGS)
        tags.sort()
        for i, value in enumerate(tags):
            self.all.set_active(i)
            self.assertEqual(self.all.tag, value)


@skipIf(is_wayland(), "crashes..")
class TTagsComboBox(TagsCombo, TagsComboMixin):
    from quodlibet.qltk.tagscombobox import TagsComboBox as Kind

    Kind  # noqa


@skipIf(is_wayland(), "crashes..")
class TTagsComboBoxEntry(TagsCombo, TagsComboMixin):
    from quodlibet.qltk.tagscombobox import TagsComboBoxEntry as Kind

    Kind  # noqa

    def test_custom(self):
        self.all.get_child().set_text("a new tag")
        self.assertEqual(self.all.tag, "a new tag")
