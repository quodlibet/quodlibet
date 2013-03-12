# Copyright 2012-2013 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk
import pango

from quodlibet import qltk, util
from quodlibet.util.dprint import print_d
from quodlibet.qltk.entry import UndoEntry, ValidatingEntry
from quodlibet.qltk.views import RCMHintedTreeView, HintedTreeView
from quodlibet.util.json_data import JSONObjectDict
from quodlibet.qltk.getstring import GetStringDialog


class JSONBasedEditor(qltk.UniqueWindow):
    """
    Flexible editor for objects extending `JSONObject`
    (held in a `JSONObjectDict`)
    TODO: validation, especially for name.
    """

    _WIDTH = 600
    _HEIGHT = 400

    def __init__(self, Prototype, values, filename, title):
        self.Prototype = Prototype
        self.current = None
        self.filename = filename
        self.input_entries = {}
        super(JSONBasedEditor, self).__init__()
        self.set_border_width(12)
        self.set_title(title)
        self.set_default_size(self._WIDTH, self._HEIGHT)

        self.add(gtk.HBox(spacing=6))
        self.get_child().set_homogeneous(True)
        self.accels = gtk.AccelGroup()

        # Set up the model for this widget
        self.model = gtk.ListStore(object)
        self._fill_values(values)

        # The browser for existing data
        self.view = view = RCMHintedTreeView(self.model)
        view.set_headers_visible(False)
        view.set_reorderable(True)
        view.set_rules_hint(True)
        render = gtk.CellRendererText()
        render.set_padding(3, 6)
        render.props.ellipsize = pango.ELLIPSIZE_END
        column = gtk.TreeViewColumn("", render)
        column.set_cell_data_func(render, self.__cdf)
        view.append_column(column)
        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        sw.add(view)
        self.get_child().pack_start(sw)

        vbox = gtk.VBox(spacing=6)
        # Input for new ones.
        frame = self.__build_input_frame()
        vbox.pack_start(frame, expand=False)

        # Add context menu
        menu = gtk.Menu()
        rem = gtk.ImageMenuItem(gtk.STOCK_REMOVE)
        keyval, mod = gtk.accelerator_parse("Delete")
        rem.add_accelerator(
            'activate', self.accels, keyval, mod, gtk.ACCEL_VISIBLE)
        rem.connect_object('activate', self.__remove, view)
        menu.append(rem)
        menu.show_all()
        view.connect('popup-menu', self.__popup, menu)
        view.connect('key-press-event', self.__view_key_press)
        self.connect_object('destroy', gtk.Menu.destroy, menu)

        # New and Close buttons
        bbox = gtk.HButtonBox()
        self.remove_but = gtk.Button(stock=gtk.STOCK_REMOVE)
        self.remove_but.set_sensitive(False)
        self.new_but = gtk.Button(stock=gtk.STOCK_NEW)
        self.new_but.connect('clicked', self._new_item)
        bbox.pack_start(self.new_but)
        close = gtk.Button(stock=gtk.STOCK_CLOSE)
        close.connect_object('clicked', qltk.Window.destroy, self)
        bbox.pack_start(close)
        align = gtk.Alignment(yalign=1.0, xscale=1.0)
        align.add(bbox)
        vbox.pack_end(align, expand=True)

        self.get_child().pack_start(vbox, expand=True)
        # Initialise
        self.selection = view.get_selection()
        model, iter = self.selection.get_selected()

        self.selection.connect('changed', self.__select)
        self.connect('destroy', self.__finish)
        self.show_all()

    def _find(self, name):
        for row in self.model:
            if row[0].name == name:
                return row[0]

    def _new_item(self, button):
        current_name = name = "New %s" % self.Prototype.__name__
        n = 2
        while True:
            if self._find(current_name):
                current_name = "%s (%d)" % (name, n)
                n += 1
                continue
            break
        self.model.append(row=(self.Prototype(name=current_name),))

    def _new_widget(self, key, val):
        """
        Creates a gtk.Entry subclass
        appropriate for a field named `key` with value `val`
        """
        callback = signal = None
        if isinstance(val, bool):
            entry = gtk.CheckButton()
            callback = self.__toggled_widget
            signal = "toggled"
        elif isinstance(val, int):
            adj = gtk.Adjustment(0, 0, 10000, 1, 10, 0)
            entry = gtk.SpinButton(adj)
            entry.set_numeric(True)
            callback = self.__changed_numeric_widget
        elif key.find("pattern") >= 0:
            print_d("Found Pattern type: %s" % key)
            entry = ValidatingEntry()
        else:
            entry = UndoEntry()
        entry.connect(signal or "changed",
                      callback or self.__changed_widget, key)
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
        for fn,val in obj.data:
            widget = self.input_entries[fn]
            widget.set_sensitive(True)
            # TODO: link this logic better with the creational stuff
            if isinstance(val, bool):
                widget.set_active(val)
            elif isinstance(val, int):
                widget.set_value(int(val))
            elif isinstance(val, basestring):
                widget.set_text(val)

    def __build_input_frame(self):
        t = gtk.Table(2, 3)
        t.set_row_spacings(6)
        t.set_col_spacing(0, 3)
        t.set_col_spacing(1, 12)

        empty = self.Prototype("empty")
        i = 0
        for i, (key, val) in enumerate(empty.data):
            field_name = key and key.replace("_", " ").title() or "(unknown)"
            l = gtk.Label(field_name + ":")
            entry = self._new_widget(key, val)
            entry.set_sensitive(False)
            # Store these away in a map for later access
            self.input_entries[key] = entry
            l.set_mnemonic_widget(entry)
            l.set_use_underline(True)
            l.set_alignment(0.0, 0.5)
            t.attach(l, 0, 1, i, i + 1, xoptions=gtk.FILL)
            t.attach(entry, 1, 2, i, i + 1)
        frame = qltk.Frame(label=self.Prototype.__name__, child=t)
        self.input_entries["name"].grab_focus()
        return frame

    def _fill_values(self, data):
        if not data: return
        for (name, obj) in data.items():
            self.model.prepend(row=[obj])

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
        return view.popup_menu(menu, 0, gtk.get_current_event_time())

    def __view_key_press(self, view, event):
        if event.keyval == gtk.accelerator_parse("Delete")[0]:
            self.__remove(view)

    def __cdf(self, column, cell, model, iter):
        row = model[iter]
        obj = row[0]
        obj_name = util.escape(obj.name)
        obj_description = util.escape(str(obj))
        markup = '<b>%s</b>\n%s' % (obj_name, obj_description)
        cell.markup = markup
        cell.set_property('markup', markup)

    def __finish(self, widget):
        # TODO: Warn about impending deletion of nameless items, or something
        all = JSONObjectDict.from_list(
                [row[0] for row in self.model if row[0].name])
        all.save(filename=self.filename)


class MultiStringEditor(qltk.UniqueWindow):
    """Dialog to edit a list of strings"""
    _WIDTH = 400
    _HEIGHT = 300

    def __init__(self, title, values=None):
        super(MultiStringEditor, self).__init__()
        self.data = values or []
        self.set_border_width(12)
        self.set_title(title)
        self.set_default_size(self._WIDTH, self._HEIGHT)

        vbox = gtk.VBox(spacing=12)
        hbox = gtk.HBox(spacing=12)

        # Set up the model for this widget
        self.model = gtk.ListStore(str)
        self.__fill_values()

        # Main view
        view = self.view = HintedTreeView(self.model)
        view.set_fixed_height_mode(True)
        view.set_headers_visible(False)

        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.add(view)
        sw.set_size_request(-1, max(sw.size_request()[1], 100))
        hbox.pack_start(sw)

        self.__setup_column(view)

        # Context menu
        menu = gtk.Menu()
        remove_item = gtk.ImageMenuItem(gtk.STOCK_REMOVE)
        menu.append(remove_item)
        menu.show_all()
        view.connect('popup-menu', self.__popup, menu)
        remove_item.connect_object('activate', self.__remove, view)

        # Add and Remove buttons
        vbbox = gtk.VButtonBox()
        vbbox.set_layout(gtk.BUTTONBOX_START)
        vbbox.set_spacing(6)
        add = gtk.Button(stock=gtk.STOCK_ADD)
        add.connect("clicked", self.__add)
        vbbox.pack_start(add, expand=False)
        remove = gtk.Button(stock=gtk.STOCK_REMOVE)
        remove.connect("clicked", self.__remove)
        vbbox.pack_start(remove, expand=False)
        hbox.pack_start(vbbox, expand=False)
        vbox.pack_start(hbox)

        # Close buttons
        bbox = gtk.HButtonBox()
        self.remove_but = gtk.Button(stock=gtk.STOCK_REMOVE)
        self.remove_but.set_sensitive(False)
        close = gtk.Button(stock=gtk.STOCK_CLOSE)
        close.connect_object('clicked', qltk.Window.destroy, self)
        bbox.set_layout(gtk.BUTTONBOX_END)
        bbox.pack_start(close)
        vbox.pack_start(bbox, expand=False)

        # Finish up
        self.add(vbox)
        self.show_all()

    def __setup_column(self, view):
        def cdf(column, cell, model, iter):
            row = model[iter]
            if row:
                cell.set_property('text', row[0])

        render = gtk.CellRendererText()
        render.set_property('ellipsize', pango.ELLIPSIZE_END)
        column = gtk.TreeViewColumn(None, render)
        column.set_cell_data_func(render, cdf)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        view.append_column(column)

    def __fill_values(self):
        for s in self.data:
            self.model.append(row=[s])

    def get_strings(self):
        strings = [row[0] for row in self.model if row]
        return strings

    def __remove(self, *args):
        self.view.remove_selection()

    def __add(self, *args):
        dialog = GetStringDialog(self, _("Enter new value"), "",
                                 okbutton=gtk.STOCK_ADD)
        new = dialog.run()
        if new:
            self.model.append(row=[new])

    def __popup(self, view, menu):
        return view.popup_menu(menu, 0, gtk.get_current_event_time()).show()
