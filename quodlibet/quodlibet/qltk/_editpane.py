# -*- coding: utf-8 -*-
# Copyright 2004-2006 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, GObject

from quodlibet import config
from quodlibet import util
from quodlibet import qltk

from quodlibet.plugins import PluginManager
from quodlibet.qltk.cbes import ComboBoxEntrySave
from quodlibet.qltk.ccb import ConfigCheckButton


class EditingPluginHandler(GObject.GObject):
    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_LAST, None, ())
    }

    Kind = None

    def __init__(self):
        super(EditingPluginHandler, self).__init__()
        self.__plugins = []

    @property
    def plugins(self):
        return list(self.__plugins)

    def plugin_handle(self, plugin):
        return issubclass(plugin.cls, self.Kind)

    def plugin_enable(self, plugin):
        self.__plugins.append(plugin.cls)
        self.emit("changed")

    def plugin_disable(self, plugin):
        self.__plugins.remove(plugin.cls)
        self.emit("changed")


class FilterCheckButton(ConfigCheckButton):
    __gsignals__ = {
        "preview": (GObject.SignalFlags.RUN_LAST, None, ())
        }

    def __init__(self):
        super(FilterCheckButton, self).__init__(
            self._label, self._section, self._key)
        try:
            self.set_active(config.getboolean(self._section, self._key))
        except:
            pass
        self.connect_object('toggled', self.emit, 'preview')
    active = property(lambda s: s.get_active())

    def filter(self, original, filename):
        raise NotImplementedError

    def filter_list(self, origs, names):
        return map(self.filter, origs, names)

    def __lt__(self, other):
        return (self._order, type(self).__name__) < \
            (other._order, type(other).__name__)


class EditPane(Gtk.VBox):
    @classmethod
    def init_plugins(cls):
        PluginManager.instance.register_handler(cls.handler)

    def __init__(self, cbes_filename, cbes_defaults):
        super(EditPane, self).__init__(spacing=6)
        self.set_border_width(12)
        hbox = Gtk.HBox(spacing=12)
        self.combo = ComboBoxEntrySave(cbes_filename, cbes_defaults,
            title=_("Path Patterns"),
            edit_title=_("Edit saved patterns..."))
        hbox.pack_start(self.combo, True, True, 0)
        self.preview = qltk.Button(_("_Preview"), Gtk.STOCK_CONVERT)
        hbox.pack_start(self.preview, False, True, 0)
        self.pack_start(hbox, False, True, 0)
        self.combo.get_child().connect('changed', self._changed)

        model = Gtk.ListStore(object, str, str)
        self.view = Gtk.TreeView(model)

        sw = Gtk.ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.IN)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.add(self.view)
        self.pack_start(sw, True, True, 0)

        filters = [Kind() for Kind in self.FILTERS]
        filters.sort()
        vbox = Gtk.VBox()
        for f in filters:
            vbox.pack_start(f, True, True, 0)
        self.pack_start(vbox, False, True, 0)

        hb = Gtk.HBox()
        expander = Gtk.Expander(label=_("_More options..."))
        expander.set_use_underline(True)
        adj = Gtk.Alignment(yalign=1.0, xscale=1.0)
        adj.add(expander)
        hb.pack_start(adj, True, True, 0)

        # Save button
        self.save = Gtk.Button(stock=Gtk.STOCK_SAVE)
        bbox = Gtk.HButtonBox()
        bbox.set_layout(Gtk.ButtonBoxStyle.END)
        bbox.pack_start(self.save, True, True, 0)
        hb.pack_start(bbox, False, True, 0)
        self.pack_start(hb, False, True, 0)

        for filt in filters:
            filt.connect_object('preview', Gtk.Button.clicked, self.preview)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        vbox = Gtk.VBox()

        self.__filters = filters
        self.__plugins = []

        self.handler.connect("changed", self.__refresh_plugins, vbox, expander)

        sw.add_with_viewport(vbox)
        self.pack_start(sw, False, True, 0)

        expander.connect("notify::expanded", self.__notify_expanded, sw)
        expander.set_expanded(False)

        self.show_all()
        self.handler.emit("changed")
        sw.hide()

    @property
    def filters(self):
        return self.__filters + self.__plugins

    def __refresh_plugins(self, handler, vbox, expander):
        instances = []
        for Kind in handler.plugins:
            try:
                f = Kind()
            except:
                util.print_exc()
                continue
            else:
                instances.append(f)
        instances.sort()

        for child in vbox.get_children():
            child.destroy()
        del self.__plugins[:]

        for f in instances:
            try:
                vbox.pack_start(f, True, True, 0)
            except:
                util.print_exc()
                f.destroy()
            else:
                try:
                    f.connect_object(
                        'preview', Gtk.Button.clicked, self.preview)
                except:
                    try:
                        f.connect_object(
                            'changed', self._changed, self.combo.get_child())
                    except:
                        util.print_exc()
                    else:
                        self.__plugins.append(f)
                else:
                    self.__plugins.append(f)
        vbox.show_all()

        # Don't display the expander if there aren't any plugins.
        if not vbox.get_children():
            expander.set_expanded(False)
            expander.hide()
        else:
            expander.show()

    def __notify_expanded(self, expander, event, vbox):
        vbox.set_property('visible', expander.get_property('expanded'))

    def _changed(self, entry):
        self.save.set_sensitive(False)
        self.preview.set_sensitive(bool(entry.get_text()))
