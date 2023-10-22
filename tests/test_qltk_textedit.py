# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase

from quodlibet.qltk.textedit import TextEditBox, TextEdit, \
    validate_markup_pattern


class TTextEditBox(TestCase):
    def setUp(self):
        self.box = TextEditBox()

    def test_empty(self):
        self.assertEqual(self.box.text, "")

    def test_set(self):
        self.box.text = "bazquux"
        self.assertEqual(self.box.text, "bazquux")

    def test_clicked(self):
        self.box.apply.clicked()

    def tearDown(self):
        self.box.destroy()


class TTextEdit(TTextEditBox):
    def setUp(self):
        self.box = TextEdit(None)


class TTextEditBox2(TestCase):
    def setUp(self):
        self.foobar = TextEditBox("foobar")

    def test_revert(self):
        self.foobar.revert.clicked()
        self.assertTrue(self.foobar.text, "foobar")

    def tearDown(self):
        self.foobar.destroy()


class TTextEdit2(TTextEditBox2):
    def setUp(self):
        self.foobar = TextEdit(None, "foobar")


class Tvalidate_markup_pattern(TestCase):

    def test_valid(self):
        for t in ["", "<foo>", "\\<b\\><foo>bar\\</b\\>", "[b]"]:
            validate_markup_pattern(t, False, False)

        for t in ["[b][/b]"]:
            validate_markup_pattern(t, True, False)

        for t in ["[a href=''][/a]", "\\<a href=''\\>\\</a\\>"]:
            validate_markup_pattern(t, True, True)

    def test_invalid(self):
        for t in ["\\<", "\\<a href=''\\>\\</a\\>"]:
            self.assertRaises(
                ValueError, validate_markup_pattern, t, False, False)

        for t in ["[b]"]:
            self.assertRaises(
                ValueError, validate_markup_pattern, t, True, False)
