# -*- coding: utf-8 -*-
# Copyright 2010, 2012-2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from quodlibet import config
from quodlibet import util
from quodlibet import qltk
from quodlibet import _
from quodlibet.qltk.tagscombobox import TagsComboBoxEntry
from quodlibet.qltk.views import BaseView
from quodlibet.qltk import Button, Icons
from quodlibet.util import connect_obj
from quodlibet.compat import iteritems, iterkeys


def get_headers():
    result = []
    headers = config.get("browsers", "collection_headers")
    for h in headers.splitlines():
        values = h.split()
        if len(values) != 2:
            continue
        tag, merge = values
        try:
            result.append((tag, bool(int(merge))))
        except ValueError:
            continue
    return result


def save_headers(headers):
    headers = "\n".join(["%s %d" % (t, m) for (t, m) in headers])
    config.set("browsers", "collection_headers", headers)


class PatternEditor(Gtk.HBox):

    PRESETS = [
        [("~people", False)],
        [("~year", False)],
        [("genre", False)],
        [("genre", False), ("artist", False)],
    ]

    COMPLETION = ["genre", "grouping", "~people", "artist", "album", "~year"]

    def __init__(self):
        super(PatternEditor, self).__init__(spacing=12)

        self.__headers = headers = {}
        buttons = []

        group = None
        for tags in self.PRESETS:
            tied = "~" + "~".join([t[0] for t in tags])
            group = Gtk.RadioButton(group=group, label="_" + util.tag(tied),
                                    use_underline=True)
            headers[group] = tags
            buttons.append(group)

        group = Gtk.RadioButton(group=group, label=_("_Custom"),
                                use_underline=True)
        self.__custom = group
        headers[group] = []
        buttons.append(group)

        button_box = Gtk.HBox(spacing=6)
        self.__model = model = Gtk.ListStore(str, bool)

        radio_box = Gtk.VBox(spacing=6)
        for button in buttons:
            radio_box.pack_start(button, False, True, 0)
            button.connect('toggled', self.__toggled, button_box, model)

        self.pack_start(radio_box, False, True, 0)

        cb = TagsComboBoxEntry(self.COMPLETION)

        view = BaseView(model=model)
        view.set_reorderable(True)
        view.set_headers_visible(True)

        ctrl_box = Gtk.VBox(spacing=6)

        add = Button(_("_Add"), Icons.LIST_ADD)
        ctrl_box.pack_start(add, False, True, 0)
        add.connect('clicked', self.__add, model, cb)

        remove = Button(_("_Remove"), Icons.LIST_REMOVE)
        ctrl_box.pack_start(remove, False, True, 0)
        remove.connect('clicked', self.__remove, view)

        selection = view.get_selection()
        selection.connect('changed', self.__selection_changed, remove)
        selection.emit('changed')

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.set_shadow_type(Gtk.ShadowType.IN)
        sw.add(view)

        edit_box = Gtk.VBox(spacing=6)
        edit_box.pack_start(cb, False, True, 0)
        edit_box.pack_start(sw, True, True, 0)

        button_box.pack_start(edit_box, True, True, 0)
        button_box.pack_start(ctrl_box, False, True, 0)
        self.pack_start(button_box, True, True, 0)

        render = Gtk.CellRendererText()
        render.set_property("editable", True)

        def edited_cb(render, path, text, model):
            model[path][0] = text
        render.connect("edited", edited_cb, model)

        column = Gtk.TreeViewColumn(_("Tag"), render, text=0)
        column.set_expand(True)
        view.append_column(column)

        toggle = Gtk.CellRendererToggle()
        toggle.connect("toggled", self.__toggeled, model)
        toggle_column = Gtk.TreeViewColumn(_("Merge"), toggle, active=1)
        view.append_column(toggle_column)

    def __toggeled(self, render, path, model):
        model[path][1] = not model[path][1]

    @property
    def headers(self):
        for button in iterkeys(self.__headers):
            if button.get_active():
                if button == self.__custom:
                    model_headers = [(row[0], row[1]) for row in self.__model]
                    self.__headers[self.__custom] = model_headers
                return self.__headers[button]

    @headers.setter
    def headers(self, new_headers):
        for button, headers in iteritems(self.__headers):
            if headers == new_headers:
                button.set_active(True)
                button.emit("toggled")
                break
        else:
            self.__headers[self.__custom] = new_headers
            self.__custom.set_active(True)

    def __selection_changed(self, selection, remove):
        remove.set_sensitive(bool(selection.get_selected()[1]))

    def __add(self, button, model, cb):
        if cb.tag:
            model.append(row=[cb.tag, False])

    def __remove(self, button, view):
        view.remove_selection()

    def __toggled(self, button, edit_widget, model):
        tags = self.__headers[button]

        if tags:
            model.clear()
            for tag, merge in tags:
                model.append(row=[tag, merge])

        edit_widget.set_sensitive(
            button.get_active() and button is self.__custom)


class Preferences(qltk.UniqueWindow):
    def __init__(self, browser):
        if self.is_not_unique():
            return
        super(Preferences, self).__init__()

        self._browser = browser

        self.set_transient_for(qltk.get_top_parent(browser))
        self.set_default_size(350, 225)
        self.set_border_width(12)

        self.set_title(_("Album Collection Preferences"))

        vbox = Gtk.VBox(spacing=12)

        editor = PatternEditor()
        editor.headers = get_headers()

        apply = Button(_("_Apply"))
        connect_obj(apply, "clicked", self.__apply, editor, False)

        cancel = Button(_("_Cancel"))
        cancel.connect("clicked", lambda x: self.destroy())

        box = Gtk.HButtonBox()
        box.set_spacing(6)
        box.set_layout(Gtk.ButtonBoxStyle.END)
        box.pack_start(apply, True, True, 0)
        self.use_header_bar()
        if not self.has_close_button():
            box.pack_start(cancel, True, True, 0)

        vbox.pack_start(editor, True, True, 0)
        vbox.pack_start(box, False, True, 0)

        self.add(vbox)

        apply.grab_focus()
        self.show_all()

    def __apply(self, editor, close):
        if editor.headers != get_headers():
            save_headers(editor.headers)
            self._browser.set_hierarchy()

        if close:
            self.destroy()
