# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2016-2020 Nick Boultbee
#                2022 Jej@github
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk, Pango, GObject, Gdk

from quodlibet import _
from quodlibet import config
from quodlibet import const
from quodlibet import qltk
from quodlibet import util
from quodlibet.plugins import PluginManager, plugin_enabled, Plugin
from quodlibet.plugins.cover import CoverSourcePlugin
from quodlibet.plugins.editing import EditTagsPlugin, RenameFilesPlugin
from quodlibet.plugins.events import EventPlugin
from quodlibet.plugins.gstelement import GStreamerPlugin
from quodlibet.plugins.playlist import PlaylistPlugin
from quodlibet.plugins.playorder import PlayOrderPlugin
from quodlibet.plugins.query import QueryPlugin
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.qltk import Icons, is_accel, show_uri
from quodlibet.qltk.entry import UndoEntry
from quodlibet.qltk.models import ObjectStore, ObjectModelFilter
from quodlibet.qltk.views import HintedTreeView
from quodlibet.qltk.window import UniqueWindow, PersistentWindowMixin
from quodlibet.qltk.x import Align, Paned, Button, ScrolledWindow
from quodlibet.util import connect_obj
from quodlibet.util.string.filter import remove_diacritics

PLUGIN_CATEGORIES = {
    _("Songs"): SongsMenuPlugin,
    _("Playlists"): PlaylistPlugin,
    _("Events"): EventPlugin,
    _("Play Order"): PlayOrderPlugin,
    _("Editing"): EditTagsPlugin,
    _("Renaming"): RenameFilesPlugin,
    _("Querying"): QueryPlugin,
    _("Effects"): GStreamerPlugin,
    _("Covers"): CoverSourcePlugin
}


def category_of(plugin: Plugin) -> str:
    try:
        return next(cat for cat, cls in PLUGIN_CATEGORIES.items()
                    if issubclass(plugin.cls, cls))
    except StopIteration:
        return _("Unknown")


class UndoSearchEntry(Gtk.SearchEntry, UndoEntry):
    pass


class PluginErrorWindow(UniqueWindow):
    def __init__(self, parent, failures):
        if self.is_not_unique():
            return
        super().__init__()

        self.set_title(_("Plugin Errors"))
        self.set_border_width(6)
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
            expander = Gtk.Expander(label=util.bold(key))
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


class EnabledType:
    TAG, ALL, NO, DIS, EN, SEP = range(6)


class PluginEnabledFilterCombo(Gtk.ComboBox):

    def __init__(self):
        combo_store = Gtk.ListStore(str, int)
        super().__init__(model=combo_store)

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
        combo_store.append([_("Any state"), EnabledType.ALL])
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
        super().__init__(model=combo_store)

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
        combo_store.append([_("Any category"), object])
        combo_store.append(["", None])
        for name, cls in PLUGIN_CATEGORIES.items():
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
        super().__init__()
        self.set_headers_visible(False)

        render = Gtk.CellRendererToggle()
        render.set_padding(6, 3)

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
        render.set_padding(6, 6)
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
        super().__init__(spacing=12)

        self.desc = desc = Gtk.Label()
        desc.set_line_wrap(True)
        # Ensure a reasonable minimum height request for long descriptions
        desc.set_width_chars(30)
        desc.set_alignment(0, 0.5)
        desc.set_selectable(True)
        self.pack_start(desc, False, True, 0)

        self.prefs = prefs = Gtk.Frame()
        prefs.set_shadow_type(Gtk.ShadowType.NONE)
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
            category = category_of(plugin).lower()
            text = (f"<big><b>{name}</b> "
                    f"<span alpha='40%'> – {category}</span>"
                    f"</big>")
            markup = plugin.description_markup
            if markup:
                text += f"<span font='4'>\n\n</span>{markup}"
            label.set_markup(text)
            label.connect("activate-link", show_uri)

        frame = self.prefs

        if frame.get_child():
            frame.get_child().destroy()

        if plugin is None:
            frame.hide()
        else:
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


class PluginWindow(UniqueWindow, PersistentWindowMixin):
    def __init__(self, parent=None):
        if self.is_not_unique():
            return
        on_top = config.getboolean("settings", "plugins_window_on_top", False)
        super().__init__(dialog=on_top)
        self.set_title(_("Plugins"))
        self.set_default_size(750, 500)
        if parent and on_top:
            self.set_transient_for(parent)
        self.set_type_hint(Gdk.WindowTypeHint.NORMAL)
        self.enable_window_tracking("plugin_prefs")

        model = ObjectStore()
        filter_model = ObjectModelFilter(child_model=model)

        self._list_view = plv = PluginListView()
        plv.set_model(filter_model)
        plv.set_rules_hint(True)

        plv.connect("plugin-toggled", self.__plugin_toggled)
        sw = ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)
        sw.add(plv)
        sw.set_shadow_type(Gtk.ShadowType.IN)

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

        self._filter_entry = fe = UndoSearchEntry()
        fe.set_tooltip_text(_("Filter by plugin name or description"))
        fe.connect("changed", lambda s: filter_model.refilter())

        errors = qltk.Button(_("Show _Errors"), Icons.DIALOG_WARNING)
        errors.set_focus_on_click(False)
        errors.connect('clicked', self.__show_errors)
        errors.show()
        errors = Align(errors, top=6, bottom=6)
        errors.set_no_show_all(True)
        bbox = Gtk.VBox()
        bbox.pack_start(errors, True, True, 0)

        pref_box = PluginPreferencesContainer()

        if const.DEBUG:
            refresh = qltk.Button(_("_Refresh"), Icons.VIEW_REFRESH)
            refresh.set_focus_on_click(False)
            refresh.connect('clicked', self.__refresh, plv, pref_box, errors,
                            enabled_combo)
            bbox.pack_start(refresh, True, True, 0)

        filter_box = Gtk.VBox(spacing=6)
        filter_box.pack_start(fb, False, True, 0)
        filter_box.pack_start(fe, False, True, 0)

        vbox = Gtk.VBox()
        vbox.pack_start(Align(filter_box, border=6, right=-6), False, False, 0)
        vbox.pack_start(sw, True, True, 0)
        vbox.pack_start(Align(bbox, left=3, right=3, top=0), False, False, 3)
        paned = Paned()
        paned.pack1(vbox, False, False)

        close = qltk.Button(_("_Close"), Icons.WINDOW_CLOSE)
        close.connect('clicked', lambda *x: self.destroy())
        bb_align = Align(halign=Gtk.Align.END, valign=Gtk.Align.END)
        bb = Gtk.HButtonBox()
        bb.set_layout(Gtk.ButtonBoxStyle.END)
        bb.pack_start(close, True, True, 0)
        bb_align.add(bb)

        selection = plv.get_selection()
        selection.connect('changed', self.__selection_changed, pref_box)
        selection.emit('changed')

        right_box = Gtk.VBox()
        right_box.pack_start(pref_box, True, True, 0)
        if not self.has_close_button():
            right_box.pack_start(bb_align, True, True, 0)

        align = Align(right_box, left=6, right=15, top=12, bottom=3)
        paned.pack2(align, True, False)
        paned.set_position(290)

        self.add(paned)

        self.__refill(plv, pref_box, errors, enabled_combo)

        self.connect('destroy', self.__destroy)
        filter_model.set_visible_func(
            self.__filter, (fe, enabled_combo, type_combo))

        self.get_child().show_all()
        fe.grab_focus()

        restore_id = config.get("memory", "plugin_selection")
        plv.select_by_plugin_id(restore_id)

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

        def matches(text, filter_):
            return all(p in remove_diacritics(text.lower())
                       for p in filter_.lower().split())

        filter_ = remove_diacritics(entry.get_text())
        return (matches(plugin.name, filter_) or
                matches(plugin.id, filter_) or
                matches((plugin.description or ""), filter_))

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
