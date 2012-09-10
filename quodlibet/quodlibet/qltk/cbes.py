# Copyright 2005-2011 Joe Wreschnig, Michael Urman, Christoph Reiter,
#                     Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

import gtk
import pango

from quodlibet import qltk
from quodlibet.qltk.views import RCMHintedTreeView
from quodlibet.qltk import entry

class _KeyValueEditor(qltk.Window):
    """Base class for key-value edit widgets"""

    _WIDTH = 400
    _HEIGHT = 300

    def __init__(self, title, validator=None):
        super(_KeyValueEditor, self).__init__()
        self.set_border_width(12)
        self.set_title(title)
        self.set_default_size(self._WIDTH, self._HEIGHT)

        self.add(gtk.VBox(spacing=6))
        self.accels = gtk.AccelGroup()

        t = gtk.Table(2, 3)
        t.set_row_spacings(3)
        t.set_col_spacing(0, 3)
        t.set_col_spacing(1, 12)

        l = gtk.Label(_("_Name:"))
        name = entry.UndoEntry()
        l.set_mnemonic_widget(name)
        l.set_use_underline(True)
        l.set_alignment(0.0, 0.5)
        t.attach(l, 0, 1, 0, 1, xoptions=gtk.FILL)
        t.attach(name, 1, 2, 0, 1)

        l = gtk.Label(_("_Value:"))
        self.value = entry.ValidatingEntry(validator)
        l.set_mnemonic_widget(self.value)
        l.set_use_underline(True)
        l.set_alignment(0.0, 0.5)
        t.attach(l, 0, 1, 1, 2, xoptions=gtk.FILL)
        t.attach(self.value, 1, 2, 1, 2)
        add = gtk.Button(stock=gtk.STOCK_ADD)
        add.set_sensitive(False)
        t.attach(add, 2, 3, 1, 2, xoptions=gtk.FILL)

        self.child.pack_start(t, expand=False)

        # Set up the model for this widget
        self.model = gtk.ListStore(str, str)
        self.fill_values()

        view = RCMHintedTreeView(self.model)
        view.set_headers_visible(False)
        view.set_reorderable(True)
        view.set_rules_hint(True)
        render = gtk.CellRendererText()
        render.props.ellipsize = pango.ELLIPSIZE_END
        column = gtk.TreeViewColumn("", render)
        column.set_cell_data_func(render, self.__cdf)
        view.append_column(column)

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        sw.add(view)
        self.child.pack_start(sw)

        menu = gtk.Menu()
        remove = gtk.ImageMenuItem(gtk.STOCK_REMOVE)
        keyval, mod = gtk.accelerator_parse("Delete")
        remove.add_accelerator(
            'activate', self.accels, keyval, mod, gtk.ACCEL_VISIBLE)
        menu.append(remove)
        menu.show_all()

        bbox = gtk.HButtonBox()
        rem_b = gtk.Button(stock=gtk.STOCK_REMOVE)
        rem_b.set_sensitive(False)
        bbox.pack_start(rem_b)
        close = gtk.Button(stock=gtk.STOCK_CLOSE)
        bbox.pack_start(close)
        self.child.pack_start(bbox, expand=False)

        selection = view.get_selection()
        name.connect_object('activate', gtk.Entry.grab_focus, self.value)
        self.value.connect_object('activate', gtk.Button.clicked, add)
        self.value.connect('changed', self.__changed, [add])
        add.connect_object(
            'clicked', self.__add, selection, name, self.value, self.model)
        selection.connect('changed', self.__set_text, name, self.value, rem_b)
        view.connect('popup-menu', self.__popup, menu)
        remove.connect_object('activate', self.__remove, view)
        rem_b.connect_object('clicked', self.__remove, view)
        close.connect_object('clicked', qltk.Window.destroy, self)
        view.connect('key-press-event', self.__view_key_press)
        self.connect_object('destroy', gtk.Menu.destroy, menu)

        name.grab_focus()
        self.show_all()

    def fill_values(self):
        """Responsible for populating self.model (eg with values from disk)"""
        raise NotImplementedError

    def __view_key_press(self, view, event):
        if event.keyval == gtk.accelerator_parse("Delete")[0]:
            self.__remove(view)

    def __popup(self, view, menu):
        return view.popup_menu(menu, 0, gtk.get_current_event_time())

    def __remove(self, view):
        view.remove_selection()

    def __set_text(self, selection, name, value, remove):
        model, iter = selection.get_selected()
        remove.set_sensitive(bool(iter))
        if iter is not None:
            name.set_text(model[iter][1])
            value.set_text(model[iter][0])

    def __cdf(self, column, cell, model, iter):
        row = model[iter]
        content, name = row[0], row[1]
        cell.set_property('text', '%s\n\t%s' % (name, content))

    def __changed(self, entry, buttons):
        for b in buttons: b.set_sensitive(bool(entry.get_text()))

    def __add(self, selection, name, value, model):
        value = value.get_text()
        if value:
            name = name.get_text() or value
            iter = model.append(row=[value, name])
            selection.select_iter(iter)


class CBESEditor(_KeyValueEditor):
    def __init__(self, cbes, title, validator=None):
        # Do this before calling parent constructor
        self.cbes = cbes
        super(CBESEditor, self).__init__(title, validator)
        self.set_transient_for(qltk.get_top_parent(cbes))
        self.connect_object('destroy', self.__finish, cbes)
        self.value.set_text(cbes.child.get_text())

    def fill_values(self):
        for row in self.cbes.get_model():
            if row[2] is not None:
                break
            else:
                self.model.append((row[0], row[1]))

    def __finish(self, cbes):
        cbes_model = cbes.get_model()
        iter = cbes_model.get_iter_first()
        while cbes_model[iter][2] is None:
            cbes_model.remove(iter)
            iter = cbes_model.get_iter_first()
        for row in self.model:
            cbes_model.insert_before(iter, row=[row[0], row[1], None])
        cbes.write()


class StandaloneEditor(_KeyValueEditor):
    """A key-value pair editor that can be used without CBES.
    Saves to disk in a single file of the same format with suffix '.saved'
    """

    # Make this editor a bit bigger
    _WIDTH = 500
    _HEIGHT = 350

    @classmethod
    def load_values(cls, filename):
        """Returns a list of tuples representing k,v pairs of the given file"""
        ret = []
        if os.path.exists(filename):
            fileobj = file(filename, "rU")
            lines = list(fileobj.readlines())
            for i in range(len(lines) / 2 ):
                ret.append( (lines[i*2+1].strip(), lines[i*2].strip()) )
        return ret

    def __init__(self, filename, title, initial=None, validator=None):
        self.filename = filename
        self.initial = initial or []
        super(StandaloneEditor, self).__init__(title, validator)
        self.connect_object('destroy', self.write, True)

    def fill_values(self):
        filename = self.filename + ".saved"
        if os.path.exists(filename):
            fileobj = file(filename, "rU")
            lines = list(fileobj.readlines())
            lines.reverse()
            while len(lines) > 1:
                self.model.prepend(
                    row=[lines.pop(1).strip(), lines.pop(0).strip()])
        if not len(self.model) and self.initial:
            #print_d("None found - using defaults.", context=self)
            for (k,v) in self.initial:
                self.model.append(row=[v.strip(), k.strip()] )

    def write(self, create=True):
        """Save to a filename. If create is True, any needed parent
        directories will be created."""
        try:
            if create:
                if not os.path.isdir(os.path.dirname(self.filename)):
                    os.makedirs(os.path.dirname(self.filename))

            saved = file(self.filename + ".saved", "w")
            for row in self.model:
                saved.write(row[0] + "\n")
                saved.write(row[1] + "\n")
            saved.close()
        except EnvironmentError:
            pass

ICONS = {gtk.STOCK_EDIT: CBESEditor}

class ComboBoxEntrySave(gtk.ComboBoxEntry):
    """A ComboBoxEntry that remembers the past 'count' strings entered,
    and can save itself to (and load itself from) a filename or file-like."""

    __models = {}
    __last = ""

    def __init__(self, filename=None, initial=[], count=5, id=None,
        validator=None, title=_("Saved Values"),
        edit_title=_("Edit saved values...")):
        self.count = count
        self.filename = filename
        id = filename or id

        try: model = self.__models[id]
        except KeyError:
            model = type(self).__models[id] = gtk.ListStore(str, str, str)

        super(ComboBoxEntrySave, self).__init__(model, 0)
        self.clear()

        render = gtk.CellRendererPixbuf()
        self.pack_start(render, False)
        self.add_attribute(render, 'stock-id', 2)

        render = gtk.CellRendererText()
        self.pack_start(render, True)
        self.add_attribute(render, 'text', 1)

        self.set_row_separator_func(self.__separator_func)

        if not len(model):
            self.__fill(filename, initial, edit_title)

        self.remove(self.child)
        self.add(entry.ValidatingEntry(validator))

        self.connect_object('destroy', self.set_model, None)
        self.connect_object('changed', self.__changed, model,
            validator, title)

    def enable_clear_button(self):
        self.child.enable_clear_button()

    def __changed(self, model, validator, title):
        iter = self.get_active_iter()
        if iter:
            if model[iter][2] in ICONS:
                self.child.set_text(self.__last)
                Kind = ICONS[model[iter][2]]
                Kind(self, title, validator)
                self.set_active(-1)
            else:
                self.__focus_entry()
        self.__last = self.child.get_text()

    def __focus_entry(self):
        self.child.grab_focus()
        self.child.emit('move-cursor', gtk.MOVEMENT_BUFFER_ENDS, 0, False)

    def __fill(self, filename, initial, edit_title):
        model = self.get_model()
        model.append(row=["", edit_title, gtk.STOCK_EDIT])
        model.append(row=[None, None, None])

        if filename is None: return

        if os.path.exists(filename + ".saved"):
            fileobj = file(filename + ".saved", "rU")
            lines = list(fileobj.readlines())
            lines.reverse()
            while len(lines) > 1:
                model.prepend(
                    row=[lines.pop(1).strip(), lines.pop(0).strip(), None])

        if os.path.exists(filename):
            for line in file(filename, "rU").readlines():
                line = line.strip()
                model.append(row=[line, line, None])

        for c in initial:
            model.append(row=[c, c, None])

        self.__shorten()

    def __separator_func(self, model, iter):
        return model[iter][1] is None

    def __shorten(self):
        model = self.get_model()
        for row in model:
            if row[0] is None:
                offset = row.path[0] + 1
                break
        to_remove = (len(model) - offset) - self.count
        while to_remove > 0:
            model.remove(model.get_iter((len(model) - 1,)))
            to_remove -= 1

    def write(self, filename=None, create=True):
        """Save to a filename. If create is True, any needed parent
        directories will be created."""
        if filename is None: filename = self.filename
        try:
            if create:
                if not os.path.isdir(os.path.dirname(filename)):
                    os.makedirs(os.path.dirname(filename))

            saved = file(filename + ".saved", "w")
            memory = file(filename, "w")
            target = saved
            for row in self.get_model():
                if row[0] is None: target = memory
                elif row[2] is None:
                    target.write(row[0] + "\n")
                    if target is saved:
                        target.write(row[1] + "\n")
            saved.close()
            memory.close()
        except EnvironmentError: pass

    def __remove_if_present(self, text):
        # Removes an item from the list if it's present in the remembered
        # values, or returns true if it's in the saved values.
        removable = False
        model = self.get_model()
        for row in model:
            if row[0] is None:
                # Not found in the saved values, so if we find it from now
                # on, remove it and return false.
                removable = True
            elif row[2] is None and row[0] == text:
                # Found the value, and it's not the magic value -- remove
                # it if necessary, and return whether or not to continue.
                if removable: model.remove(row.iter)
                return not removable

    def prepend_text(self, text):
        # If we find the value in the saved values, don't prepend it.
        if self.__remove_if_present(text): return

        model = self.get_model()
        for row in model:
            if row[0] is None:
                model.insert_after(row.iter, row=[text, text, None])
                break
        self.__shorten()
