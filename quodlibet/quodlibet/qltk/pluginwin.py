# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2016-2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, Pango, GObject

from quodlibet import config
from quodlibet import const
from quodlibet import qltk
from quodlibet import util
from quodlibet import _

from quodlibet.plugins import PluginManager, plugin_enabled
from quodlibet.plugins.cover import CoverSourcePlugin
from quodlibet.plugins.editing import EditTagsPlugin
from quodlibet.plugins.events import EventPlugin
from quodlibet.plugins.gstelement import GStreamerPlugin
from quodlibet.plugins.playlist import PlaylistPlugin
from quodlibet.plugins.playorder import PlayOrderPlugin
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.qltk.views import HintedTreeView
from quodlibet.qltk.window import UniqueWindow, PersistentWindowMixin
from quodlibet.qltk.x import Align, Paned, Button, ScrolledWindow
from quodlibet.qltk.models import ObjectStore, ObjectModelFilter
from quodlibet.qltk.entry import UndoEntry
from quodlibet.qltk import Icons, is_accel, show_uri
from quodlibet.util import connect_obj


class UndoSearchEntry(Gtk.SearchEntry, UndoEntry):
    pass


class PluginErrorWindow(UniqueWindow):
    def __init__(self, parent, failures):
        if self.is_not_unique():
            return
        super(PluginErrorWindow, self).__init__()

        self.set_title(_("Plugin Errors"))
        self.set_border_width(12)
        self.set_transient_for(parent)
        self.set_default_size(520, 300)

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
            failure.set_line_wrap(True)

            vbox.pack_start(expander, False, True, 0)
            expander.add(failure)

        self.use_header_bar()

        if not self.has_close_button():
            vbox2 = Gtk.VBox(spacing=12)
            close = Button(_("_Close"), Icons.WINDOW_CLOSE)
            close.connect('clicked', lambda *x: self.destroy())
            b = Gtk.HButtonBox()
            b.set_layout(Gtk.ButtonBoxStyle.END)
            b.pack_start(close, True, True, 0)
            vbox2.pack_start(scrolledwin, True, True, 0)
            vbox2.pack_start(b, False, True, 0)
            self.add(vbox2)
            close.grab_focus()
        else:
            self.add(scrolledwin)

        self.get_child().show_all()


class EnabledType(object):
    TAG, ALL, NO, DIS, EN, SEP = range(6)


class PluginEnabledFilterCombo(Gtk.ComboBox):

    def __init__(self):
        combo_store = Gtk.ListStore(str, int)
        super(PluginEnabledFilterCombo, self).__init__(model=combo_store)

        cell = Gtk.CellRendererText()
        cell.props.ellipsize = Pango.EllipsizeMode.END
        self.pack_start(cell, True)
        self.add_attribute(cell, "text", 0)

        def combo_sep(model, iter_, data):
            return model[iter_][1] == EnabledType.SEP

        self.set_row_separator_func(combo_sep, None)

    def refill(self, tags, no_tags):
        """Fill with a sequence of tags.
        If no_tags is true display display the extra category for it.
        """

        active = max(self.get_active(), 0)
        combo_store = self.get_model()
        combo_store.clear()
        combo_store.append([_("All"), EnabledType.ALL])
        combo_store.append(["", EnabledType.SEP])
        combo_store.append([_("Enabled"), EnabledType.EN])
        combo_store.append([_("Disabled"), EnabledType.DIS])
        if tags:
            combo_store.append(["", EnabledType.SEP])
            for tag in sorted(tags):
                combo_store.append([tag, EnabledType.TAG])
            if no_tags:
                combo_store.append([_("No category"), EnabledType.NO])
        self.set_active(active)

    def get_active_row(self):
        iter_ = self.get_active_iter()
        if iter_:
            model = self.get_model()
            return list(model[iter_])


class PluginTypeFilterCombo(Gtk.ComboBox):

    def __init__(self):
        combo_store = Gtk.ListStore(str, object)
        super(PluginTypeFilterCombo, self).__init__(model=combo_store)

        cell = Gtk.CellRendererText()
        cell.props.ellipsize = Pango.EllipsizeMode.END
        self.pack_start(cell, True)
        self.add_attribute(cell, "text", 0)

        def combo_sep(model, iter_, data):
            return model[iter_][1] is None

        self.set_row_separator_func(combo_sep, None)
        self.__refill()

    def __refill(self):
        """Fill with plugin types"""

        active = max(self.get_active(), 0)
        combo_store = self.get_model()
        combo_store.clear()
        combo_store.append([_("All"), object])
        combo_store.append(["", None])
        for name, cls in sorted([
                [_("Songs"), SongsMenuPlugin],
                [_("Playlists"), PlaylistPlugin],
                [_("Events"), EventPlugin],
                [_("Play Order"), PlayOrderPlugin],
                [_("Editing"), EditTagsPlugin],
                [_("Effects"), GStreamerPlugin],
                [_("Covers"), CoverSourcePlugin]]):
            combo_store.append([name, cls])

        self.set_active(active)

    def get_active_type(self):
        iter_ = self.get_active_iter()
        if iter_:
            model = self.get_model()
            return model[iter_][1]


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
        render.set_padding(1, 1)

        def cell_data(col, render, model, iter_, data):
            plugin = model.get_value(iter_)
            pm = PluginManager.instance
            render.set_activatable(plugin.can_enable)
            # If it can't be enabled because it's an always-on kinda thing,
            # show it as enabled so it doesn't look broken.
            render.set_active(pm.enabled(plugin) or not plugin.can_enable)

        render.connect('toggled', self.__toggled)
        column = Gtk.TreeViewColumn("enabled", render)
        column.set_cell_data_func(render, cell_data)
        self.append_column(column)

        render = Gtk.CellRendererPixbuf()
        render.set_padding(1, 1)

        def cell_data2(col, render, model, iter_, data):
            plugin = model.get_value(iter_)
            icon = plugin.icon or Icons.SYSTEM_RUN
            render.set_property('icon-name', icon)
            render.set_property('stock-size', Gtk.IconSize.LARGE_TOOLBAR)

        column = Gtk.TreeViewColumn("image", render)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_cell_data_func(render, cell_data2)
        self.append_column(column)

        render = Gtk.CellRendererText()
        render.set_property('ellipsize', Pango.EllipsizeMode.END)
        render.set_property('xalign', 0.0)
        render.set_padding(2, 2)
        column = Gtk.TreeViewColumn("name", render)

        def cell_data3(col, render, model, iter_, data):
            plugin = model.get_value(iter_)
            render.set_property('text', plugin.name)

        column.set_cell_data_func(render, cell_data3)
        column.set_expand(True)
        self.append_column(column)

    def do_key_press_event(self, event):
        if is_accel(event, "space", "KP_Space"):
            selection = self.get_selection()
            fmodel, fiter = selection.get_selected()
            plugin = fmodel.get_value(fiter)
            if plugin.can_enable:
                self._emit_toggled(fmodel.get_path(fiter),
                                   not plugin_enabled(plugin))
            self.get_model().iter_changed(fiter)
        else:
            Gtk.TreeView.do_key_press_event(self, event)

    def __toggled(self, render, path):
        render.set_active(not render.get_active())
        self._emit_toggled(path, render.get_active())

    def _emit_toggled(self, path, value):
        model = self.get_model()
        iter_ = model.get_iter(path)
        self.emit("plugin-toggled", model, iter_, value)

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
                text += plugin.description
            label.set_markup(text)
            label.connect("activate-link", show_uri)

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
                        b = Button(_("_Preferences"), Icons.PREFERENCES_SYSTEM)
                        connect_obj(b, 'clicked', Gtk.Window.show, prefs)
                        connect_obj(b, 'destroy', Gtk.Window.destroy, prefs)
                        frame.add(b)
                        frame.get_child().set_border_width(6)
                    else:
                        frame.add(prefs)
                    frame.show_all()
        else:
            frame.hide()


class PluginWindow(UniqueWindow, PersistentWindowMixin):
    def __init__(self, parent=None):
        if self.is_not_unique():
            return
        super(PluginWindow, self).__init__()
        self.set_title(_("Plugins"))
        self.set_default_size(700, 500)
        self.set_transient_for(parent)
        self.enable_window_tracking("plugin_prefs")

        paned = Paned()
        vbox = Gtk.VBox()

        sw = ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)

        model = ObjectStore()
        filter_model = ObjectModelFilter(child_model=model)

        self._list_view = tv = PluginListView()
        tv.set_model(filter_model)
        tv.set_rules_hint(True)

        tv.connect("plugin-toggled", self.__plugin_toggled)

        fb = Gtk.HBox(spacing=6)

        enabled_combo = PluginEnabledFilterCombo()
        enabled_combo.connect("changed", lambda s: filter_model.refilter())
        enabled_combo.set_tooltip_text(_("Filter by plugin state / tag"))
        fb.pack_start(enabled_combo, True, True, 0)
        self._enabled_combo = enabled_combo

        type_combo = PluginTypeFilterCombo()
        type_combo.connect("changed", lambda s: filter_model.refilter())
        type_combo.set_tooltip_text(_("Filter by plugin type"))
        fb.pack_start(type_combo, True, True, 0)
        self._type_combo = type_combo

        filter_entry = UndoSearchEntry()
        filter_entry.set_tooltip_text(
            _("Filter by plugin name or description"))
        filter_entry.connect("changed", lambda s: filter_model.refilter())
        self._filter_entry = filter_entry

        sw.add(tv)
        sw.set_shadow_type(Gtk.ShadowType.IN)

        bbox = Gtk.VBox()

        errors = qltk.Button(_("Show _Errors"), Icons.DIALOG_WARNING)
        errors.set_focus_on_click(False)
        errors.connect('clicked', self.__show_errors)
        errors.show()
        errors = Align(errors, top=6, bottom=6)
        errors.set_no_show_all(True)
        bbox.pack_start(errors, True, True, 0)

        pref_box = PluginPreferencesContainer()

        if const.DEBUG:
            refresh = qltk.Button(_("_Refresh"), Icons.VIEW_REFRESH)
            refresh.set_focus_on_click(False)
            refresh.connect('clicked', self.__refresh, tv, pref_box, errors,
                            enabled_combo)
            bbox.pack_start(refresh, True, True, 0)

        filter_box = Gtk.VBox(spacing=6)
        filter_box.pack_start(fb, False, True, 0)
        filter_box.pack_start(filter_entry, False, True, 0)
        vbox.pack_start(Align(filter_box, border=6, right=-6), False, False, 0)
        vbox.pack_start(sw, True, True, 0)
        vbox.pack_start(Align(bbox, left=6), False, True, 0)
        paned.pack1(vbox, False, False)

        close = qltk.Button(_("_Close"), Icons.WINDOW_CLOSE)
        close.connect('clicked', lambda *x: self.destroy())
        bb_align = Align(halign=Gtk.Align.END, valign=Gtk.Align.END)
        bb = Gtk.HButtonBox()
        bb.set_layout(Gtk.ButtonBoxStyle.END)
        bb.pack_start(close, True, True, 0)
        bb_align.add(bb)

        selection = tv.get_selection()
        selection.connect('changed', self.__selection_changed, pref_box)
        selection.emit('changed')

        right_box = Gtk.VBox(spacing=12)
        right_box.pack_start(pref_box, True, True, 0)
        self.use_header_bar()
        if not self.has_close_button():
            right_box.pack_start(bb_align, True, True, 0)

        paned.pack2(Align(right_box, border=12), True, False)
        paned.set_position(275)

        self.add(paned)

        self.__refill(tv, pref_box, errors, enabled_combo)

        self.connect('destroy', self.__destroy)
        filter_model.set_visible_func(
            self.__filter, (filter_entry, enabled_combo, type_combo))

        self.get_child().show_all()
        filter_entry.grab_focus()

        restore_id = config.get("memory", "plugin_selection")
        tv.select_by_plugin_id(restore_id)

    def __filter(self, model, iter_, data):
        """Filter a single row"""
        plugin = model.get_value(iter_)
        if not plugin:
            return False

        entry, state_combo, type_combo = data

        plugin_type = type_combo.get_active_type()
        if not issubclass(plugin.cls, plugin_type):
            return False

        tag_row = state_combo.get_active_row()
        if tag_row:
            plugin_tags = plugin.tags
            tag, flag = tag_row
            enabled = plugin_enabled(plugin)
            if (flag == EnabledType.NO and plugin_tags or
                    flag == EnabledType.TAG and tag not in plugin_tags or
                    flag == EnabledType.EN and not enabled or
                    flag == EnabledType.DIS and enabled):
                return False

        filter_ = util.gdecode(entry.get_text()).lower()
        return (not filter_ or filter_ in plugin.name.lower()
                or filter_ in (plugin.description or "").lower())

    def __destroy(self, *args):
        config.save()

    def __selection_changed(self, selection, container):
        model, iter_ = selection.get_selected()
        if not iter_:
            container.set_plugin(None)
            return

        plugin = model.get_value(iter_)
        config.set("memory", "plugin_selection", plugin.id)
        container.set_plugin(plugin)

    def unfilter(self):
        """Clears all filters applied to the list"""

        self._enabled_combo.set_active(0)
        self._type_combo.set_active(0)
        self._filter_entry.set_text(u"")

    def move_to(self, plugin_id):
        def selector(r):
            return r[0].id == plugin_id

        if self._list_view.select_by_func(selector):
            return True
        else:
            self.unfilter()
            return self._list_view.select_by_func(selector)

    def __plugin_toggled(self, tv, model, iter_, enabled):
        plugin = model.get_value(iter_)
        pm = PluginManager.instance
        pm.enable(plugin, enabled)
        pm.save()

        rmodel = model.get_model()
        riter = model.convert_iter_to_child_iter(iter_)
        rmodel.row_changed(rmodel.get_path(riter), riter)

    def __refill(self, view, prefs, errors, state_combo):
        pm = PluginManager.instance

        # refill plugin list
        view.refill(pm.plugins)

        # get all tags and refill tag-based (state) combobox
        tags = set()
        no_tags = False
        for plugin in pm.plugins:
            if not plugin.tags:
                no_tags = True
            tags.update(plugin.tags)

        state_combo.refill(tags, no_tags)

        if not len(pm.plugins):
            prefs.set_no_plugins()

        errors.set_visible(bool(pm.failures))

    def __refresh(self, activator, view, prefs, errors, state_combo):
        pm = PluginManager.instance
        pm.rescan()
        self.__refill(view, prefs, errors, state_combo)

    def __show_errors(self, activator):
        pm = PluginManager.instance
        window = PluginErrorWindow(self, pm.failures)
        window.show()
