# Copyright 2012-2022 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
from collections.abc import Iterable

from gi.repository import Gtk
from gi.repository import Pango

from quodlibet import _
from quodlibet import qltk, util
from quodlibet.qltk.entry import UndoEntry, ValidatingEntry
from quodlibet.qltk.views import RCMHintedTreeView, HintedTreeView
from quodlibet.qltk.x import MenuItem, Button, Align
from quodlibet.qltk import Icons
from quodlibet.query import Query
from quodlibet.util.json_data import JSONObjectDict
from quodlibet.util import connect_obj
from quodlibet.qltk.getstring import GetStringDialog


class JSONBasedEditor(qltk.UniqueWindow):
    """
    Flexible editor for objects extending `JSONObject`
    (held in a `JSONObjectDict`)
    TODO: validation, especially for name.
    """

    _WIDTH = 800
    _HEIGHT = 400

    def __init__(self, proto_cls, values, filename, title):
        if self.is_not_unique():
            return
        super().__init__()
        self.proto_cls = proto_cls
        self.current = None
        self.filename = filename
        self.name = proto_cls.NAME or proto_cls.__name__
        self.input_entries = {}
        self.set_border_width(12)
        self.set_title(title)
        self.set_default_size(self._WIDTH, self._HEIGHT)

        self.add(Gtk.HBox(spacing=6))
        self.get_child().set_homogeneous(True)
        self.accels = Gtk.AccelGroup()

        # Set up the model for this widget
        self.model = Gtk.ListStore(object)
        self._fill_values(values)

        # The browser for existing data
        self.view = view = RCMHintedTreeView(model=self.model)
        view.set_headers_visible(False)
        view.set_reorderable(True)
        view.set_rules_hint(True)
        render = Gtk.CellRendererText()
        render.set_padding(3, 6)
        render.props.ellipsize = Pango.EllipsizeMode.END
        column = Gtk.TreeViewColumn("", render)
        column.set_cell_data_func(render, self.__cdf)
        view.append_column(column)
        sw = Gtk.ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.IN)
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.add(view)
        self.get_child().pack_start(sw, True, True, 0)

        vbox = Gtk.VBox(spacing=6)
        # Input for new ones.
        frame = self.__build_input_frame()
        vbox.pack_start(frame, False, True, 0)

        # Add context menu
        menu = Gtk.Menu()
        rem = MenuItem(_("_Remove"), Icons.LIST_REMOVE)
        keyval, mod = Gtk.accelerator_parse("Delete")
        rem.add_accelerator(
            "activate", self.accels, keyval, mod, Gtk.AccelFlags.VISIBLE
        )
        connect_obj(rem, "activate", self.__remove, view)
        menu.append(rem)
        menu.show_all()
        view.connect("popup-menu", self.__popup, menu)
        view.connect("key-press-event", self.__view_key_press)
        connect_obj(self, "destroy", Gtk.Menu.destroy, menu)

        # New and Close buttons
        bbox = Gtk.HButtonBox()
        self.remove_but = Button(_("_Remove"), Icons.LIST_REMOVE)
        self.remove_but.set_sensitive(False)
        self.new_but = Button(_("_New"), Icons.DOCUMENT_NEW)
        self.new_but.connect("clicked", self._new_item)
        bbox.pack_start(self.new_but, True, True, 0)
        close = Button(_("_Close"), Icons.WINDOW_CLOSE)
        connect_obj(close, "clicked", qltk.Window.destroy, self)
        bbox.pack_start(close, True, True, 0)
        vbox.pack_end(bbox, False, True, 0)

        self.get_child().pack_start(vbox, True, True, 0)
        # Initialise
        self.selection = view.get_selection()

        self.selection.connect("changed", self.__select)
        self.connect("destroy", self.__finish)
        self.get_child().show_all()

    def _find(self, name):
        for row in self.model:
            if row[0].name == name:
                return row[0]
        return None

    def _new_item(self, button):
        # Translators: New Command/Entry/Item/...
        current_name = name = _("New %s") % self.name
        n = 2
        while True:
            if self._find(current_name):
                current_name = "%s (%d)" % (name, n)
                n += 1
                continue
            break
        self.model.append(row=(self.proto_cls(name=current_name),))

    def _new_widget(self, key, val):
        """
        Creates a Gtk.Entry subclass
        appropriate for a field named `key` with value `val`
        """
        callback = signal = None
        if isinstance(val, bool):
            entry = Gtk.CheckButton()
            callback = self.__toggled_widget
            signal = "toggled"
        elif isinstance(val, int):
            adj = Gtk.Adjustment.new(0, 0, 9999, 1, 10, 0)
            entry = Gtk.SpinButton(adjustment=adj)
            entry.set_numeric(True)
            callback = self.__changed_numeric_widget
        elif "pattern" in key:
            entry = ValidatingEntry(validator=Query.validator)
        else:
            entry = UndoEntry()
        entry.connect(signal or "changed", callback or self.__changed_widget, key)
        return entry

    def __refresh_view(self):
        model, iter = self.selection.get_selected()
        self.model.emit("row-changed", model[iter].path, iter)

    def __changed_widget(self, entry, key):
        if self.current:
            setattr(self.current, key, str(entry.get_text()))
            self.__refresh_view()

    def __changed_numeric_widget(self, entry, key):
        if self.current:
            setattr(self.current, key, int(entry.get_text() or 0))
            self.__refresh_view()

    def __toggled_widget(self, entry, key):
        if self.current:
            setattr(self.current, key, bool(entry.get_active()))
            self.__refresh_view()

    def _populate_fields(self, obj):
        """Populates the input fields based on the `JSONData` object `obj`"""
        for fn, val in obj.data:
            widget = self.input_entries[fn]
            widget.set_sensitive(True)
            # TODO: link this logic better with the creational stuff
            if isinstance(val, bool):
                widget.set_active(val)
            elif isinstance(val, int):
                widget.set_value(int(val))
            elif isinstance(val, str):
                widget.set_text(val or "")

    def __build_input_frame(self):
        t = Gtk.Table(n_rows=2, n_columns=3)
        t.set_row_spacings(6)
        t.set_col_spacing(0, 3)
        t.set_col_spacing(1, 12)

        empty = self.proto_cls("empty")
        for i, (key, val) in enumerate(empty.data):
            field = empty.field(key)
            field_name = self.get_field_name(field, key)
            l = Gtk.Label(label=field_name + ":")
            entry = self._new_widget(key, val)
            entry.set_sensitive(False)
            if field.doc:
                entry.set_tooltip_text(field.doc)
            # Store these away in a map for later access
            self.input_entries[key] = entry
            l.set_mnemonic_widget(entry)
            l.set_use_underline(True)
            l.set_alignment(0.0, 0.5)
            if isinstance(val, int | bool):
                align = Align(entry, halign=Gtk.Align.START)
                t.attach(align, 1, 2, i, i + 1)
            else:
                t.attach(entry, 1, 2, i, i + 1)
            t.attach(l, 0, 1, i, i + 1, xoptions=Gtk.AttachOptions.FILL)
        frame = qltk.Frame(label=self.name, child=t)
        self.input_entries["name"].grab_focus()
        return frame

    @staticmethod
    def get_field_name(field, key):
        field_name = field.human_name or (key and key.replace("_", " "))
        return field_name and util.capitalize(field_name) or _("(unknown)")

    def _fill_values(self, data):
        if not data:
            return
        for _name, obj in data.items():
            self.model.append(row=[obj])

    def _update_current(self, new_selection=None):
        if new_selection:
            self.selection = new_selection
        model, iter = self.selection.get_selected()
        if iter:
            self.current = model[iter][0]

    def __select(self, selection):
        self._update_current(selection)
        self.remove_but.set_sensitive(bool(iter))
        if iter is not None:
            self._populate_fields(self.current)

    def __remove(self, view):
        view.remove_selection()

    def __popup(self, view, menu):
        return view.popup_menu(menu, 0, Gtk.get_current_event_time())

    def __view_key_press(self, view, event):
        if event.keyval == Gtk.accelerator_parse("Delete")[0]:
            self.__remove(view)

    def __cdf(self, column, cell, model, iter, data):
        row = model[iter]
        obj = row[0]
        obj_name = util.escape(obj.name)
        obj_description = util.escape(str(obj))
        markup = f"{util.bold(obj_name)}\n{obj_description}"
        cell.markup = markup
        cell.set_property("markup", markup)

    def __finish(self, widget):
        # TODO: Warn about impending deletion of nameless items, or something
        all = JSONObjectDict.from_list([row[0] for row in self.model if row[0].name])
        all.save(filename=self.filename)


class TagListEditor(qltk.Window):
    """Dialog to edit a list of tag names."""

    _WIDTH = 600
    _HEIGHT = 300

    def __init__(self, title, values=None):
        super().__init__()
        self.use_header_bar()
        self.set_border_width(12)
        self.set_title(title)
        self.set_default_size(self._WIDTH, self._HEIGHT)

        vbox = Gtk.VBox(spacing=12)
        hbox = Gtk.HBox(spacing=12)

        # Set up the model for this widget
        self.model = Gtk.ListStore(str)
        self.__fill_values(values or [])

        def on_row_activated(view, path, column):
            self._renderer.set_property("editable", True)
            view.set_cursor(path, view.get_columns()[0], start_editing=True)

        # Main view
        view = self.view = HintedTreeView(model=self.model)
        view.set_fixed_height_mode(True)
        view.set_headers_visible(False)
        view.connect("row-activated", on_row_activated)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_shadow_type(Gtk.ShadowType.IN)
        sw.add(view)
        sw.set_size_request(-1, max(sw.size_request().height, 100))
        hbox.pack_start(sw, True, True, 0)

        self.__setup_column(view)

        # Context menu
        menu = Gtk.Menu()
        remove_item = MenuItem(_("_Remove"), Icons.LIST_REMOVE)
        menu.append(remove_item)
        menu.show_all()
        view.connect("popup-menu", self.__popup, menu)
        connect_obj(remove_item, "activate", self.__remove, view)

        # Add and Remove buttons
        vbbox = Gtk.VButtonBox()
        vbbox.set_layout(Gtk.ButtonBoxStyle.START)
        vbbox.set_spacing(6)
        add = Button(_("_Add…"), Icons.LIST_ADD)
        add.connect("clicked", self.__add)
        vbbox.pack_start(add, False, True, 0)
        remove = Button(_("_Remove"), Icons.LIST_REMOVE)
        remove.connect("clicked", self.__remove)
        vbbox.pack_start(remove, False, True, 0)
        edit = Button(_("_Edit"), Icons.LIST_EDIT)
        edit.connect("clicked", self.__edit)
        vbbox.pack_start(edit, False, True, 0)
        hbox.pack_start(vbbox, False, True, 0)
        vbox.pack_start(hbox, True, True, 0)

        # Close buttons
        bbox = Gtk.HButtonBox()
        self.remove_but = Button(_("_Remove"), Icons.LIST_REMOVE)
        self.remove_but.set_sensitive(False)
        close = Button(_("_Close"), Icons.WINDOW_CLOSE)
        connect_obj(close, "clicked", qltk.Window.destroy, self)
        bbox.set_layout(Gtk.ButtonBoxStyle.END)
        if not self.has_close_button():
            bbox.pack_start(close, True, True, 0)
            vbox.pack_start(bbox, False, True, 0)

        # Finish up
        self.add(vbox)
        self.get_child().show_all()

    def __start_editing(self, _render, editable, path):
        editable.set_text(self.model[path][0])

    def __edited(self, _render, path, new_name):
        self.model[path][0] = new_name
        self.model.row_changed(path, self.model.get_iter(path))

    def __setup_column(self, view):
        def tag_cdf(column, cell, model, iter, data):
            row = model[iter]
            if row:
                cell.set_property("text", row[0])

        def desc_cdf(column, cell, model, iter, data):
            row = model[iter]
            if row:
                cell.set_property("markup", util.italic(util.tag(row[0])))

        def __create_cell_renderer():
            r = Gtk.CellRendererText()
            r.connect("editing-started", self.__start_editing)
            r.connect("edited", self.__edited)
            return r

        self._renderer = renderer = __create_cell_renderer()
        column = Gtk.TreeViewColumn(_("Tag expression"), renderer)
        column.set_cell_data_func(renderer, tag_cdf)
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column.set_expand(True)
        view.append_column(column)

        renderer = Gtk.CellRendererText()
        renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
        renderer.set_property("sensitive", False)
        column = Gtk.TreeViewColumn(_("Description"), renderer)
        column.set_cell_data_func(renderer, desc_cdf)
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column.set_expand(True)

        view.append_column(column)
        view.set_headers_visible(True)

    def __fill_values(self, data: Iterable[str]):
        for s in data:
            self.model.append(row=[s])

    @property
    def tags(self):
        """Returns the tag names as edited"""
        return [row[0] for row in self.model if row]

    def __remove(self, *args):
        self.view.remove_selection()

    def __add(self, *args):
        tooltip = _("Tag expression e.g. people:real or ~album~year")
        dialog = GetStringDialog(
            self, _("Enter new tag"), "", button_icon=None, tooltip=tooltip
        )
        new = dialog.run()
        if new:
            self.model.append(row=[new])

    def __edit(self, *args):
        path, col = self.view.get_cursor()
        tooltip = _("Tag expression e.g. people:real or ~album~year")
        dialog = GetStringDialog(
            self, _("Edit tag expression"), "", button_icon=None, tooltip=tooltip
        )
        edited = dialog.run(text=self.model[path][0])
        if edited:
            self.model[path][0] = edited

    def __popup(self, view, menu):
        return view.popup_menu(menu, 0, Gtk.get_current_event_time()).show()
