# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, Pango

from quodlibet import config
from quodlibet import const
from quodlibet import qltk
from quodlibet import util

from quodlibet.plugins import PluginManager
from quodlibet.qltk.views import HintedTreeView
from quodlibet.qltk.entry import ClearEntry
from quodlibet.qltk.models import ObjectStore, ObjectModelFilter


TAG, ALL, NO, DIS, EN, SEP = range(6)


class PluginErrorWindow(qltk.UniqueWindow):
    def __init__(self, parent):
        if self.is_not_unique():
            return
        super(PluginErrorWindow, self).__init__()

        self.set_title(_("Plugin Errors") + " - Quod Libet")
        self.set_border_width(12)
        self.set_transient_for(parent)
        self.set_default_size(420, 250)

        scrolledwin = Gtk.ScrolledWindow()
        vbox = Gtk.VBox(spacing=6)
        vbox.set_border_width(6)
        scrolledwin.set_policy(Gtk.PolicyType.AUTOMATIC,
                               Gtk.PolicyType.AUTOMATIC)
        scrolledwin.add_with_viewport(vbox)

        failures = {}
        failures.update(PluginManager.instance.failures)
        keys = failures.keys()
        show_expanded = len(keys) <= 3
        for key in sorted(keys):
            expander = Gtk.Expander(label="<b>%s</b>" % util.escape(key))
            expander.set_use_markup(True)
            if show_expanded:
                expander.set_expanded(True)

            # second line is always the __rescan line; don't show it
            message = failures[key][0:1] + failures[key][3:]
            failure = Gtk.Label(label=''.join(message).strip())
            failure.set_alignment(0, 0)
            failure.set_padding(12, 6)
            failure.set_selectable(True)

            vbox.pack_start(expander, False, True, 0)
            expander.add(failure)

        vbox2 = Gtk.VBox(spacing=12)
        close = Gtk.Button(stock=Gtk.STOCK_CLOSE)
        close.connect('clicked', lambda *x: self.destroy())
        b = Gtk.HButtonBox()
        b.set_layout(Gtk.ButtonBoxStyle.END)
        b.pack_start(close, True, True, 0)

        vbox2.pack_start(scrolledwin, True, True, 0)
        vbox2.pack_start(b, False, True, 0)
        self.add(vbox2)

        close.grab_focus()
        self.get_child().show_all()


class PluginWindow(qltk.UniqueWindow):
    def __init__(self, parent):
        if self.is_not_unique():
            return
        super(PluginWindow, self).__init__()
        self.set_title(_("Plugins") + " - Quod Libet")
        self.set_border_width(12)
        self.set_default_size(655, 404)
        self.set_transient_for(parent)

        hbox = Gtk.HBox(spacing=12)
        vbox = Gtk.VBox(spacing=6)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)
        tv = HintedTreeView()
        model = ObjectStore()
        filter = ObjectModelFilter(child_model=model)

        tv.set_model(filter)
        tv.set_rules_hint(True)

        filter_entry = ClearEntry()
        filter_entry.connect("changed", lambda s: filter.refilter())

        combo_store = Gtk.ListStore(str, int)
        filter_combo = Gtk.ComboBox(model=combo_store)
        cell = Gtk.CellRendererText()
        filter_combo.pack_start(cell, True)
        filter_combo.add_attribute(cell, "text", 0)
        filter_combo.connect("changed", lambda s: filter.refilter())

        combo_sep = lambda model, iter, data: model[iter][1] == SEP
        filter_combo.set_row_separator_func(combo_sep, None)

        fb = Gtk.HBox(spacing=6)
        fb.pack_start(filter_combo, False, True, 0)

        filter_entry.enable_clear_button()
        fb.pack_start(filter_entry, True, True, 0)

        render = Gtk.CellRendererToggle()

        def cell_data(col, render, model, iter, data):
            plugin = model[iter][0]
            pm = PluginManager.instance
            render.set_active(pm.enabled(plugin))

        render.connect('toggled', self.__toggled, filter)
        column = Gtk.TreeViewColumn("enabled", render)
        column.set_cell_data_func(render, cell_data)
        tv.append_column(column)

        render = Gtk.CellRendererPixbuf()

        def cell_data2(col, render, model, iter, data):
            plugin = model[iter][0]
            icon = plugin.icon or Gtk.STOCK_EXECUTE
            if Gtk.stock_lookup(icon):
                render.set_property('stock-id', icon)
            else:
                render.set_property('icon-name', icon)

        column = Gtk.TreeViewColumn("image", render)
        column.set_cell_data_func(render, cell_data2)
        tv.append_column(column)

        render = Gtk.CellRendererText()
        render.set_property('ellipsize', Pango.EllipsizeMode.END)
        render.set_property('xalign', 0.0)
        column = Gtk.TreeViewColumn("name", render)

        def cell_data3(col, render, model, iter, data):
            render.set_property('text', model[iter][0].name)

        column.set_cell_data_func(render, cell_data3)
        column.set_expand(True)
        tv.append_column(column)

        sw.add(tv)
        sw.set_shadow_type(Gtk.ShadowType.IN)
        sw.set_size_request(250, -1)

        tv.set_headers_visible(False)

        bbox = Gtk.HBox(homogeneous=True, spacing=12)
        errors = qltk.Button(_("Show _Errors"), Gtk.STOCK_DIALOG_WARNING)
        errors.set_focus_on_click(False)
        bbox.pack_start(errors, True, True, 0)
        refresh = Gtk.Button(stock=Gtk.STOCK_REFRESH)
        refresh.set_focus_on_click(False)
        bbox.pack_start(refresh, True, True, 0)
        vbox.pack_start(fb, False, True, 0)
        vbox.pack_start(sw, True, True, 0)
        vbox.pack_start(bbox, False, True, 0)
        hbox.pack_start(vbox, False, True, 0)

        selection = tv.get_selection()
        desc = Gtk.Label()
        desc.set_line_wrap(True)
        desc.set_alignment(0, 0.5)
        desc.set_selectable(True)
        selection.connect('changed', self.__description, desc)

        prefs = Gtk.Frame()
        prefs.set_shadow_type(Gtk.ShadowType.NONE)

        close = Gtk.Button(stock=Gtk.STOCK_CLOSE)
        close.connect('clicked', lambda *x: self.destroy())

        bb_align = Gtk.Alignment.new(0, 1, 1, 0)

        bb = Gtk.HButtonBox()
        bb.set_layout(Gtk.ButtonBoxStyle.END)
        bb.pack_start(close, True, True, 0)
        bb_align.add(bb)

        vb2 = Gtk.VBox(spacing=12)
        vb2.pack_start(desc, False, True, 0)
        vb2.pack_start(prefs, False, True, 0)
        vb2.pack_start(bb_align, True, True, 0)
        hbox.pack_start(vb2, True, True, 0)

        self.add(hbox)
        selection.connect('changed', self.__preferences, prefs)
        refresh.connect('clicked', self.__refresh, tv, desc, errors,
            filter_combo, combo_store)
        errors.connect('clicked', self.__show_errors)
        tv.get_selection().emit('changed')
        refresh.clicked()

        self.connect('destroy', self.__destroy)
        filter.set_visible_func(
            self.__filter, (filter_entry, filter_combo, combo_store))

        self.get_child().show_all()
        filter_entry.grab_focus()

        restore_id = config.get("memory", "plugin_selection")

        def restore_sel(row):
            return row[0].id == restore_id

        if not tv.select_by_func(restore_sel, one=True) and tv.get_model():
            tv.set_cursor((0,))

    def __filter(self, model, iter, widgets):
        plugin = model.get_value(iter)
        pm = PluginManager.instance

        if not plugin:
            return False

        entry, combo, model = widgets

        plugin_tags = plugin.tags

        iter = combo.get_active_iter()
        if iter:
            enabled = pm.enabled(plugin)
            tag = model[iter][0]
            flag = model[iter][1]
            if flag == NO and plugin_tags or \
                flag == TAG and not tag in plugin_tags or \
                flag == EN and not enabled or \
                flag == DIS and enabled:
                return False

        filter = entry.get_text().lower()
        if not filter or filter in plugin.name.lower() or \
                filter in (plugin.description or "").lower():
            return True
        return False

    def __destroy(self, *args):
        config.write(const.CONFIG)

    def __description(self, selection, label):
        model, iter = selection.get_selected()
        if not iter:
            label.set_markup("")
            return

        plugin = model.get_value(iter)

        config.set("memory", "plugin_selection", plugin.id)

        name = util.escape(plugin.name)
        text = "<big><b>%s</b></big>" % name
        if plugin.description:
            text += "<span font='4'>\n\n</span>"
            text += util.escape(plugin.description)
        label.set_markup(text)

    def __preferences(self, selection, frame):
        if frame.get_child():
            frame.get_child().destroy()

        model, iter = selection.get_selected()
        if not iter:
            return

        plugin = model.get_value(iter)
        instance_or_cls = plugin.get_instance() or plugin.cls

        if iter and hasattr(instance_or_cls, 'PluginPreferences'):
            try:
                prefs = instance_or_cls.PluginPreferences(self)
            except:
                util.print_exc()
                frame.hide()
            else:
                if isinstance(prefs, Gtk.Window):
                    b = Gtk.Button(stock=Gtk.STOCK_PREFERENCES)
                    b.connect_object('clicked', Gtk.Window.show, prefs)
                    b.connect_object('destroy', Gtk.Window.destroy, prefs)
                    frame.add(b)
                    frame.get_child().set_border_width(6)
                else:
                    frame.add(prefs)
                frame.show_all()
        else:
            frame.hide()

    def __toggled(self, render, fpath, fmodel):
        render.set_active(not render.get_active())

        path = fmodel.convert_path_to_child_path(Gtk.TreePath(fpath))
        model = fmodel.get_model()

        pm = PluginManager.instance
        row = model[path]
        plugin = row[0]

        pm.enable(plugin, render.get_active())
        pm.save()

        model.row_changed(row.path, row.iter)

    def __refresh(self, activator, view, desc, errors, combo, combo_store):
        fmodel, fiter = view.get_selection().get_selected()
        model = fmodel.get_model()

        # get the ID of the selected plugin
        selected = None
        if fiter:
            iter = fmodel.convert_iter_to_child_iter(fiter)
            plugin = model.get_value(iter)
            selected = plugin.id

        model.clear()

        pm = PluginManager.instance
        pm.rescan()

        tags = []
        no_tags = False

        for plugin in sorted(pm.plugins, key=lambda x: x.name):
            it = model.append(row=[plugin])
            if plugin.id is selected:
                ok, fit = fmodel.convert_child_iter_to_iter(it)
                view.get_selection().select_iter(fit)
            if not plugin.tags:
                no_tags = True
            tags.extend(plugin.tags)
        tags = list(set(tags))

        active = max(combo.get_active(), 0)
        combo_store.clear()
        combo_store.append([_("All"), ALL])
        combo_store.append(["", SEP])
        combo_store.append([_("Enabled"), EN])
        combo_store.append([_("Disabled"), DIS])
        if tags:
            combo_store.append(["", SEP])
            for tag in sorted(tags):
                combo_store.append([tag, TAG])
            if no_tags:
                combo_store.append([_("No category"), NO])
        combo.set_active(active)

        if not len(model):
            desc.set_text(_("No plugins found."))
        errors.set_sensitive(bool(pm.failures))

    def __show_errors(self, activator):
        window = PluginErrorWindow(self)
        window.show()
