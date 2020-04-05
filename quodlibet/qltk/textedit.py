# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk, GLib, Pango

from senf import fsnative

from quodlibet import _
from quodlibet import qltk
from quodlibet import util

from quodlibet.qltk import Button, Icons
from quodlibet.formats import AudioFile
from quodlibet.pattern import XMLFromPattern, XMLFromMarkupPattern, \
    error as PatternError
from quodlibet.util import connect_obj

try:
    import gi
    gi.require_version("GtkSource", "3.0")
    from gi.repository import GtkSource
except (ValueError, ImportError):
    TextView = Gtk.TextView
    TextBuffer = Gtk.TextBuffer
else:
    TextView = GtkSource.View

    class TextBuffer(GtkSource.Buffer):  # type: ignore
        def __init__(self, *args):
            super(TextBuffer, self).__init__(*args)
            self.set_highlight_matching_brackets(False)
            self.set_highlight_syntax(False)

        def set_text(self, *args):
            self.begin_not_undoable_action()
            super(TextBuffer, self).set_text(*args)
            self.end_not_undoable_action()


class TextEditBox(Gtk.HBox):
    """A simple text editing area with a default value, a revert button,
    and an apply button. The 'buffer' attribute is the text buffer, the
    'apply' attribute is the apply button.

    FIXME: Button text should changeable (without poking the buttons directly).
    """

    def __init__(self, default=""):
        super(TextEditBox, self).__init__(spacing=6)

        sw = Gtk.ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.IN)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.add(TextView(buffer=TextBuffer()))
        self.pack_start(sw, True, True, 0)
        self.buffer = sw.get_child().get_buffer()

        box = Gtk.VBox(spacing=6)
        rev = Button(_("_Revert"), Icons.DOCUMENT_REVERT)
        app = Button(_("_Apply"))
        box.pack_start(rev, False, True, 0)
        box.pack_start(app, False, True, 0)
        self.pack_start(box, False, True, 0)
        connect_obj(rev, 'clicked', self.buffer.set_text, default)
        self.revert = rev
        self.apply = app

    @property
    def text(self):
        start, end = self.buffer.get_bounds()
        return self.buffer.get_text(start, end, True)

    @text.setter
    def text(self, value):
        self.buffer.set_text(value, -1)


def validate_markup_pattern(text, alternative_markup=True, links=False):
    """Check whether a passed pattern results in a valid pango markup.

    Args:
        text (unicode): the pattern
        alternative_markup (bool): if "[b]" gets mapped to "\\<b\\>"
        links (bool): if link tags are allowed (for Gtk.Label only)

    Raises:
        ValueError: In case the pattern isn't valid
    """

    assert isinstance(text, str)

    f = AudioFile({"~filename": fsnative(u"dummy")})

    try:
        if alternative_markup:
            pattern = XMLFromMarkupPattern(text)
        else:
            pattern = XMLFromPattern(text)
        text = pattern % f
    except PatternError as e:
        return ValueError(e)

    try:
        Pango.parse_markup(text, -1, u"\u0000")
    except GLib.GError as e:
        if not links:
            raise ValueError(e)
        # Gtk.Label supports links on top of pango markup but doesn't
        # provide a way to verify them. We can check if the markup
        # was accepted by seeing if get_text() returns something.
        l = Gtk.Label()
        # add a character in case text is empty.
        # this might print a warning to stderr.. no idea how to prevent that..
        l.set_markup(text + " ")
        if not l.get_text():
            raise ValueError(e)


class PatternEditBox(TextEditBox):
    """A TextEditBox that stops the apply button's clicked signal if
    the pattern is invalid. You need to use connect_after to connect to
    it, to get this feature."""

    def __init__(self, default="", alternative_markup=True, links=False):
        super(PatternEditBox, self).__init__(default)
        self._alternative_markup = alternative_markup
        self._links = links
        self.apply.connect('clicked', self.__check_markup)

    def __check_markup(self, apply):
        try:
            validate_markup_pattern(
                self.text, self._alternative_markup, self._links)
        except ValueError as e:
            qltk.ErrorMessage(
                self, _("Invalid pattern"),
                _("The pattern you entered was invalid. Make sure you enter "
                  "&lt; and &gt; as \\&lt; and \\&gt; and that your tags are "
                  "balanced.\n\n%s") % util.escape(str(e))).run()
            apply.stop_emission('clicked')
        return False


class TextEdit(qltk.UniqueWindow):
    """A window with a text editing box in it."""

    Box = TextEditBox

    def __init__(self, parent, default="", **kwargs):
        if self.is_not_unique():
            return
        super(TextEdit, self).__init__()
        self.set_title(_("Edit Display"))
        self.set_transient_for(qltk.get_top_parent(parent))
        self.set_border_width(12)
        self.set_default_size(420, 190)

        vbox = Gtk.VBox(spacing=12)
        close = Button(_("_Close"), Icons.WINDOW_CLOSE)
        close.connect('clicked', lambda *x: self.destroy())
        b = Gtk.HButtonBox()
        b.set_layout(Gtk.ButtonBoxStyle.END)
        b.pack_start(close, True, True, 0)

        self.box = box = self.Box(default, **kwargs)
        vbox.pack_start(box, True, True, 0)
        self.use_header_bar()
        if not self.has_close_button():
            vbox.pack_start(b, False, True, 0)

        self.add(vbox)
        self.apply = box.apply
        self.revert = box.revert

        close.grab_focus()
        self.get_child().show_all()

    @property
    def text(self):
        return self.box.text

    @text.setter
    def text(self, value):
        self.box.text = value


class PatternEdit(TextEdit):
    """A window with a pattern editing box in it."""
    Box = PatternEditBox
