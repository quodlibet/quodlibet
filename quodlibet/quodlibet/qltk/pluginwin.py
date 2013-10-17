# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, Pango, GObject

from quodlibet import config
from quodlibet import const
from quodlibet import qltk
from quodlibet import util

from quodlibet.plugins import PluginManager
from quodlibet.qltk.views import HintedTreeView
from quodlibet.qltk.entry import ClearEntry
from quodlibet.qltk.models import ObjectStore, ObjectModelFilter


class PluginErrorWindow(qltk.UniqueWindow):
    def __init__(self, parent, failures):
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


class ComboType(object):
    TAG, ALL, NO, DIS, EN, SEP = range(6)


class PluginFilterCombo(Gtk.ComboBox):

    def __init__(self):
        combo_store = Gtk.ListStore(str, int)
        super(PluginFilterCombo, self).__init__(model=combo_store)

        cell = Gtk.CellRendererText()
        self.pack_start(cell, True)
        self.add_attribute(cell, "text", 0)

        def combo_sep(model, iter_, data):
            return model[iter_][1] == ComboType.SEP

        self.set_row_separator_func(combo_sep, None)

    def refill(self, tags, no_tags):
        """Fill with a sequence of tags.
        If no_tags is true display display the extra cetegory for it.
        """

        active = max(self.get_active(), 0)
        combo_store = self.get_model()
        combo_store.clear()
        combo_store.append([_("All"), ComboType.ALL])
        combo_store.append(["", ComboType.SEP])
        combo_store.append([_("Enabled"), ComboType.EN])
        combo_store.append([_("Disabled"), ComboType.DIS])
        if tags:
            combo_store.append(["", ComboType.SEP])
            for tag in sorted(tags):
                combo_store.append([tag, ComboType.TAG])
            if no_tags:
                combo_store.append([_("No category"), ComboType.NO])
        self.set_active(active)

    def get_active_tag(self):
        iter_ = self.get_active_iter()
        if iter_:
            model = self.get_model()
            return list(model[iter_])


class PluginListView(HintedTreeView):

    __gsignals__ = {
        # model, iter, enabled
        "plugin-toggled": (GObject.SignalFlags.RUN_LAST, None,
                           (object, object, bool))
    }

    def __init__(self):
        super(PluginListView, self).__init__()
        self.set_headers_visible(False)

        render = Gtk.CellRendererToggle()

        def cell_data(col, render, model, iter_, data):
            plugin = model.get_value(iter_)
            pm = PluginManager.instance
            render.set_active(pm.enabled(plugin))

        render.connect('toggled', self.__toggled)
        column = Gtk.TreeViewColumn("enabled", render)
        column.set_cell_data_func(render, cell_data)
        self.append_column(column)

        render = Gtk.CellRendererPixbuf()

        def cell_data2(col, render, model, iter_, data):
            plugin = model.get_value(iter_)
            icon = plugin.icon or Gtk.STOCK_EXECUTE
            if Gtk.stock_lookup(icon):
                render.set_property('stock-id', icon)
            else:
                render.set_property('icon-name', icon)

        column = Gtk.TreeViewColumn("image", render)
        column.set_cell_data_func(render, cell_data2)
        self.append_column(column)

        render = Gtk.CellRendererText()
        render.set_property('ellipsize', Pango.EllipsizeMode.END)
        render.set_property('xalign', 0.0)
        column = Gtk.TreeViewColumn("name", render)

        def cell_data3(col, render, model, iter_, data):
            plugin = model.get_value(iter_)
            render.set_property('text', plugin.name)

        column.set_cell_data_func(render, cell_data3)
        column.set_expand(True)
        self.append_column(column)

    def __toggled(self, render, path):
        render.set_active(not render.get_active())
        model = self.get_model()
        iter_ = model.get_iter(path)
        self.emit("plugin-toggled", model, iter_, render.get_active())

    def select_by_plugin_id(self, plugin_id):

        def restore_sel(row):
            return row[0].id == plugin_id

        if not self.select_by_func(restore_sel, one=True):
            self.set_cursor((0,))

    def refill(self, plugins):
        selection = self.get_selection()

        fmodel, fiter = selection.get_selected()
        model = fmodel.get_model()

        # get the ID of the selected plugin
        selected = None
        if fiter:
            plugin = fmodel.get_value(fiter)
            selected = plugin.id

        model.clear()

        for plugin in sorted(plugins, key=lambda x: x.name):
            it = model.append(row=[plugin])
            if plugin.id == selected:
                ok, fit = fmodel.convert_child_iter_to_iter(it)
                selection.select_iter(fit)


class PluginPreferencesContainer(Gtk.VBox):
    def __init__(self):
        super(PluginPreferencesContainer, self).__init__(spacing=12)

        self.desc = desc = Gtk.Label()
        desc.set_line_wrap(True)
        desc.set_alignment(0, 0.5)
        desc.set_selectable(True)
        desc.show()
        self.pack_start(desc, False, True, 0)

        self.prefs = prefs = Gtk.Frame()
        prefs.set_shadow_type(Gtk.ShadowType.NONE)
        prefs.show()
        self.pack_start(prefs, False, True, 0)

    def set_no_plugins(self):
        self.set_plugin(None)
        self.desc.set_text(_("No plugins found."))

    def set_plugin(self, plugin):
        label = self.desc

        if plugin is None:
            label.set_markup("")
        else:
            name = util.escape(plugin.name)
            text = "<big><b>%s</b></big>" % name
            if plugin.description:
                text += "<span font='4'>\n\n</span>"
                text += util.escape(plugin.description)
            label.set_markup(text)

        frame = self.prefs

        if frame.get_child():
            frame.get_child().destroy()

        if plugin is not None:
            instance_or_cls = plugin.get_instance() or plugin.cls

            if plugin and hasattr(instance_or_cls, 'PluginPreferences'):
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


class PluginWindow(qltk.UniqueWindow):
    def __init__(self, parent=None):
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

        model = ObjectStore()
        filter_model = ObjectModelFilter(child_model=model)

        tv = PluginListView()
        tv.set_model(filter_model)
        tv.set_rules_hint(True)

        tv.connect("plugin-toggled", self.__plugin_toggled)

        fb = Gtk.HBox(spacing=6)

        filter_combo = PluginFilterCombo()
        filter_combo.connect("changed", lambda s: filter_model.refilter())
        fb.pack_start(filter_combo, False, True, 0)

        filter_entry = ClearEntry()
        filter_entry.connect("changed", lambda s: filter_model.refilter())
        filter_entry.enable_clear_button()
        fb.pack_start(filter_entry, True, True, 0)

        sw.add(tv)
        sw.set_shadow_type(Gtk.ShadowType.IN)
        sw.set_size_request(250, -1)

        bbox = Gtk.HBox(homogeneous=True, spacing=12)

        errors = qltk.Button(_("Show _Errors"), Gtk.STOCK_DIALOG_WARNING)
        errors.set_focus_on_click(False)
        errors.connect('clicked', self.__show_errors)
        bbox.pack_start(errors, True, True, 0)

        pref_box = PluginPreferencesContainer()

        if const.DEBUG:
            refresh = Gtk.Button(stock=Gtk.STOCK_REFRESH)
            refresh.set_focus_on_click(False)
            refresh.connect('clicked', self.__refresh, tv, pref_box, errors,
                            filter_combo)
            bbox.pack_start(refresh, True, True, 0)

        vbox.pack_start(fb, False, True, 0)
        vbox.pack_start(sw, True, True, 0)
        vbox.pack_start(bbox, False, True, 0)
        hbox.pack_start(vbox, False, True, 0)

        close = Gtk.Button(stock=Gtk.STOCK_CLOSE)
        close.connect('clicked', lambda *x: self.destroy())
        bb_align = Gtk.Alignment.new(0, 1, 1, 0)
        bb = Gtk.HButtonBox()
        bb.set_layout(Gtk.ButtonBoxStyle.END)
        bb.pack_start(close, True, True, 0)
        bb_align.add(bb)

        selection = tv.get_selection()
        selection.connect('changed', self.__selection_changed, pref_box)
        selection.emit('changed')

        right_box = Gtk.VBox(spacing=12)
        right_box.pack_start(pref_box, True, True, 0)
        right_box.pack_start(bb_align, True, True, 0)

        hbox.pack_start(right_box, True, True, 0)

        self.add(hbox)

        self.__refill(tv, pref_box, errors, filter_combo)

        self.connect('destroy', self.__destroy)
        filter_model.set_visible_func(
            self.__filter, (filter_entry, filter_combo))

        self.get_child().show_all()
        filter_entry.grab_focus()

        restore_id = config.get("memory", "plugin_selection")
        tv.select_by_plugin_id(restore_id)

    def __filter(self, model, iter_, data):
        plugin = model.get_value(iter_)
        if not plugin:
            return False

        entry, combo = data

        tag = combo.get_active_tag()
        if tag:
            plugin_tags = plugin.tags
            tag, flag = tag
            pm = PluginManager.instance
            enabled = pm.enabled(plugin)
            if flag == ComboType.NO and plugin_tags or \
                flag == ComboType.TAG and not tag in plugin_tags or \
                flag == ComboType.EN and not enabled or \
                flag == ComboType.DIS and enabled:
                return False

        filter_ = entry.get_text().lower()
        if not filter_ or filter_ in plugin.name.lower() or \
                filter_ in (plugin.description or "").lower():
            return True
        return False

    def __destroy(self, *args):
        config.write(const.CONFIG)

    def __selection_changed(self, selection, container):
        model, iter_ = selection.get_selected()
        if not iter_:
            container.set_plugin(None)
            return

        plugin = model.get_value(iter_)
        config.set("memory", "plugin_selection", plugin.id)
        container.set_plugin(plugin)

    def __plugin_toggled(self, tv, model, iter_, enabled):
        plugin = model.get_value(iter_)
        pm = PluginManager.instance
        pm.enable(plugin, enabled)
        pm.save()

        rmodel = model.get_model()
        riter = model.convert_iter_to_child_iter(iter_)
        rmodel.row_changed(rmodel.get_path(riter), riter)

    def __refill(self, view, prefs, errors, combo):
        pm = PluginManager.instance

        # refill plugin list
        view.refill(pm.plugins)

        # get all tags and refill combobox
        tags = set()
        no_tags = False
        for plugin in pm.plugins:
            if not plugin.tags:
                no_tags = True
            tags.update(plugin.tags)

        combo.refill(tags, no_tags)

        if not len(pm.plugins):
            prefs.set_no_plugins()

        errors.set_sensitive(bool(pm.failures))

    def __refresh(self, activator, view, prefs, errors, combo):
        pm = PluginManager.instance
        pm.rescan()

        self.__refill(view, prefs, errors, combo)

    def __show_errors(self, activator):
        pm = PluginManager.instance
        window = PluginErrorWindow(self, pm.failures)
        window.show()
