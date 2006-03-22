# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import gtk
import pango
import qltk

class CBESEditor(qltk.Window):
    def __init__(self, cbes, initial=""):
        super(CBESEditor, self).__init__()
        self.set_border_width(12)
        self.set_title(_("Saved Values"))
        self.set_transient_for(qltk.get_top_parent(cbes))
        self.set_default_size(400, 300)

        self.add(gtk.VBox(spacing=6))

        t = gtk.Table(2, 3)
        t.set_row_spacings(3)
        t.set_col_spacing(0, 3)
        t.set_col_spacing(1, 12)

        l = gtk.Label(_("_Name:"))
        name = gtk.Entry()
        l.set_mnemonic_widget(name)
        l.set_use_underline(True)
        l.set_alignment(0.0, 0.5)
        t.attach(l, 0, 1, 0, 1, xoptions=gtk.FILL)
        t.attach(name, 1, 2, 0, 1)
        add = gtk.Button(stock=gtk.STOCK_ADD)
        t.attach(add, 2, 3, 0, 1, xoptions=gtk.FILL)

        l = gtk.Label(_("_Value:"))
        value = gtk.Entry()
        l.set_mnemonic_widget(value)
        l.set_use_underline(True)
        l.set_alignment(0.0, 0.5)
        t.attach(l, 0, 1, 1, 2, xoptions=gtk.FILL)
        t.attach(value, 1, 2, 1, 2)
        update = qltk.Button(_("_Replace"), gtk.STOCK_FIND_AND_REPLACE)
        t.attach(update, 2, 3, 1, 2, xoptions=gtk.FILL)

        self.child.pack_start(t, expand=False)

        model = gtk.ListStore(str, str)
        for row in cbes.get_model():
            if row[0] is None: break
            else: model.append((row[0], row[1]))

        view = gtk.TreeView(model)
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

        bbox = gtk.HButtonBox()
        remove = gtk.Button(stock=gtk.STOCK_REMOVE)
        remove.set_sensitive(False)
        bbox.pack_start(remove)
        close = gtk.Button(stock=gtk.STOCK_CLOSE)
        bbox.pack_start(close)
        self.child.pack_start(bbox, expand=False)

        selection = view.get_selection()
        name.connect_object('activate', gtk.Entry.grab_focus, value)
        value.connect_object(
            'activate', self.__dtrt, selection, name, value, model)
        value.connect('changed', self.__changed, [add, update])
        add.connect_object(
            'clicked', self.__add, selection, name, value, model)
        update.connect_object(
            'clicked', self.__update, selection, name, value, model)
        selection.connect(
            'changed', self.__set_text, name, value, [update, remove])
        close.connect_object('clicked', qltk.Window.destroy, self)
        remove.connect_object('clicked', self.__remove, selection)
        self.connect_object('destroy', self.__finish, model, cbes)

        name.grab_focus()
        value.set_text(initial)
        self.show_all()

    def __dtrt(self, selection, name, value, model):
        if value.get_text():
            if selection.get_selected()[1] is None:
                self.__add(selection, name, value, model)
            else: self.__update(selection, name, value, model)

    def __remove(self, selection):
        model, iter = selection.get_selected()
        if iter is not None: model.remove(iter)

    def __set_text(self, selection, name, value, buttons):
        model, iter = selection.get_selected()
        for button in buttons:
            button.set_sensitive(bool(iter))
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
        name = name.get_text() or value
        iter = model.append(row=[value, name])
        selection.select_iter(iter)

    def __update(self, selection, name, value, model):
        model, iter = selection.get_selected()
        value = value.get_text()
        name = name.get_text() or value
        model.set(iter, 0, value, 1, name)

    def __finish(self, model, cbes):
        cbes_model = cbes.get_model()
        iter = cbes_model.get_iter_first()
        while cbes_model.get_value(iter, 0) is not None:
            cbes_model.remove(iter)
            iter = cbes_model.get_iter_first()
        for row in model:
            cbes_model.insert_before(iter, row=[row[0], row[1]])
        cbes.write()

class ComboBoxEntrySave(gtk.ComboBoxEntry):
    """A ComboBoxEntry that remembers the past 'count' strings entered,
    and can save itself to (and load itself from) a filename or file-like."""

    models = {}

    def __init__(self, filename=None, initial=[], count=5, model=None):
        self.count = count
        self.filename = filename
        try: model = self.models[model]
        except KeyError:
            model = self.models[model] = gtk.ListStore(str, str)
        else: model = gtk.ListStore(str, str)

        super(ComboBoxEntrySave, self).__init__(model, 0)
        self.clear()
        render = gtk.CellRendererText()
        self.pack_start(render, True)
        self.add_attribute(render, 'text', 1)

        self.set_row_separator_func(self.__separator_func)

        if len(model) == 0:
            self.__fill(filename, initial)
        self.connect_object('destroy', self.set_model, None)
        self.child.connect('populate-popup', self.__popup)

    def __popup(self, entry, menu):
        item = gtk.ImageMenuItem(stock_id=gtk.STOCK_EDIT)
        item.child.set_text(_("_Edit Saved Values..."))
        item.child.set_use_underline(True)
        item.connect_object(
            'activate', CBESEditor, self, self.child.get_text())
        item.show_all()
        menu.prepend(item)

    def __fill(self, filename, initial):
        model = self.get_model()
        model.append(row=[None, None])

        if filename is None: return

        if os.path.exists(filename + ".saved"):
            fileobj = file(filename + ".saved", "rU")
            lines = list(fileobj.readlines())
            lines.reverse()
            while len(lines) > 1:
                model.prepend(row=[lines.pop(1).strip(), lines.pop(0).strip()])

        if os.path.exists(filename):
            for line in file(filename, "rU").readlines():
                line = line.strip()
                model.append(row=[line, line])

        for c in initial:
            model.append(row=[c, c])

        self.__shorten()

    def __separator_func(self, model, iter):
        return model[iter][0] is None

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

            saved = file(filename + ".saved", "wU")
            memory = file(filename, "wU")
            target = saved
            for row in self.get_model():
                if row[0] is None: target = memory
                else:
                    target.write(row[0] + "\n")
                    if target is saved:
                        target.write(row[1] + "\n")
            saved.close()
            memory.close()
        except EnvironmentError: pass

    def __remove_if_present(self, text):
        removable = False
        model = self.get_model()
        for row in model:
            if row[0] is None: removable = True
            elif removable and row[0] == text:
                model.remove(row.iter)
                return

    def prepend_text(self, text):
        model = self.get_model()

        self.__remove_if_present(text)

        for row in model:
            if row[0] is None:
                model.insert_after(row.iter, row=[text, text])
                break
        self.__shorten()
