# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gobject
import gtk
import pango

from quodlibet import qltk
from quodlibet import util

from quodlibet.formats._audio import AudioFile
from quodlibet.parse import XMLFromPattern

try:
    import gtksourceview2
except ImportError:
    from gtk import TextView
    from gtk import TextBuffer
else:
    TextView = gtksourceview2.View
    class TextBuffer(gtksourceview2.Buffer):
        def __init__(self, *args):
            super(TextBuffer, self).__init__(*args)
            self.set_highlight_matching_brackets(False)
            self.set_highlight_syntax(False)

        def set_text(self, *args):
            self.begin_not_undoable_action()
            super(TextBuffer, self).set_text(*args)
            self.end_not_undoable_action()

class TextEditBox(gtk.HBox):
    """A simple text editing area with a default value, a revert button,
    and an apply button. The 'buffer' attribute is the text buffer, the
    'apply' attribute is the apply button.

    FIXME: Button text should changable (without poking the buttons directly).
    """

    def __init__(self, default=""):
        super(TextEditBox, self).__init__(spacing=6)

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add(TextView(TextBuffer()))
        self.pack_start(sw)
        self.buffer = sw.child.get_buffer()

        box = gtk.VBox(spacing=6)
        rev = gtk.Button(stock=gtk.STOCK_REVERT_TO_SAVED)
        app = gtk.Button(stock=gtk.STOCK_APPLY)
        box.pack_start(rev, expand=False)
        box.pack_start(app, expand=False)
        self.pack_start(box, expand=False)
        rev.connect_object('clicked', self.buffer.set_text, default)
        self.revert = rev
        self.apply = app

    def __get_text(self):
        return self.buffer.get_text(*self.buffer.get_bounds()).decode('utf-8')
    text = property(__get_text,
                    lambda s, v: s.buffer.set_text(v))

class PatternEditBox(TextEditBox):
    """A TextEditBox that stops the apply button's clicked signal if
    the pattern is invalid. You need to use connect_after to connect to
    it, to get this feature."""

    def __init__(self, default=""):
        super(PatternEditBox, self).__init__(default)
        self.apply.connect('clicked', self.__check_markup)

    def __check_markup(self, apply):
        try:
            f = AudioFile({"~filename":"dummy"})
            pango.parse_markup(XMLFromPattern(self.text) % f, u"\u0000")
        except (ValueError, gobject.GError), e:
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
        if self.is_not_unique(): return
        super(TextEdit, self).__init__()
        self.set_title(_("Edit Display"))
        self.set_transient_for(qltk.get_top_parent(parent))
        self.set_border_width(12)
        self.set_default_size(420, 190)

        vbox = gtk.VBox(spacing=12)
        close = gtk.Button(stock=gtk.STOCK_CLOSE)
        close.connect('clicked', lambda *x: self.destroy())
        b = gtk.HButtonBox()
        b.set_layout(gtk.BUTTONBOX_END)
        b.pack_start(close)

        self.box = box = self.Box(default)
        vbox.pack_start(box)
        vbox.pack_start(b, expand=False)

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
