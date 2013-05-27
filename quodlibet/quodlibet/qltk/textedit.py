# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, GLib, Pango

from quodlibet import qltk
from quodlibet import util

from quodlibet.formats._audio import AudioFile
from quodlibet.parse import XMLFromPattern

try:
    import gi
    gi.require_version("GtkSource", "3.0")
    from gi.repository import GtkSource
except (ValueError, ImportError):
    TextView = Gtk.TextView
    TextBuffer = Gtk.TextBuffer
else:
    TextView = GtkSource.View

    class TextBuffer(GtkSource.Buffer):
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

    FIXME: Button text should changable (without poking the buttons directly).
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
        rev = Gtk.Button(stock=Gtk.STOCK_REVERT_TO_SAVED)
        app = Gtk.Button(stock=Gtk.STOCK_APPLY)
        box.pack_start(rev, False, True, 0)
        box.pack_start(app, False, True, 0)
        self.pack_start(box, False, True, 0)
        rev.connect_object('clicked', self.buffer.set_text, default)
        self.revert = rev
        self.apply = app

    def __get_text(self):
        start, end = self.buffer.get_bounds()
        return self.buffer.get_text(start, end, True).decode('utf-8')
    text = property(__get_text,
                    lambda s, v: s.buffer.set_text(v, -1))


class PatternEditBox(TextEditBox):
    """A TextEditBox that stops the apply button's clicked signal if
    the pattern is invalid. You need to use connect_after to connect to
    it, to get this feature."""

    def __init__(self, default=""):
        super(PatternEditBox, self).__init__(default)
        self.apply.connect('clicked', self.__check_markup)

    def __check_markup(self, apply):
        try:
            f = AudioFile({"~filename": "dummy"})
            Pango.parse_markup(XMLFromPattern(self.text) % f, -1, u"\u0000")
        except (ValueError, GLib.GError), e:
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

    def __init__(self, parent, default=""):
        if self.is_not_unique():
            return
        super(TextEdit, self).__init__()
        self.set_title(_("Edit Display"))
        self.set_transient_for(qltk.get_top_parent(parent))
        self.set_border_width(12)
        self.set_default_size(420, 190)

        vbox = Gtk.VBox(spacing=12)
        close = Gtk.Button(stock=Gtk.STOCK_CLOSE)
        close.connect('clicked', lambda *x: self.destroy())
        b = Gtk.HButtonBox()
        b.set_layout(Gtk.ButtonBoxStyle.END)
        b.pack_start(close, True, True, 0)

        self.box = box = self.Box(default)
        vbox.pack_start(box, True, True, 0)
        vbox.pack_start(b, False, True, 0)

        self.add(vbox)
        self.apply = box.apply
        self.revert = box.revert

        close.grab_focus()
        self.show_all()

    text = property(lambda s: s.box.text,
                    lambda s, v: setattr(s.box, 'text', v))


class PatternEdit(TextEdit):
    """A window with a pattern editing box in it."""
    Box = PatternEditBox
