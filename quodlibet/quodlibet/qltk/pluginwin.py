# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gtk
import pango

from quodlibet import config
from quodlibet import const
from quodlibet import qltk
from quodlibet import util

from quodlibet.plugins import Manager
from quodlibet.qltk.views import HintedTreeView

class PluginWindow(qltk.UniqueWindow):
    def __init__(self, parent):
        if self.is_not_unique(): return
        super(PluginWindow, self).__init__()
        self.set_title(_("Quod Libet Plugins"))
        self.set_border_width(12)
        self.set_resizable(False)
        self.set_transient_for(parent)

        hbox = gtk.HBox(spacing=12)        
        vbox = gtk.VBox(spacing=6)

        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        tv = HintedTreeView()
        model = gtk.ListStore(object, object)
        tv.set_model(model)
        tv.set_rules_hint(True)

        render = gtk.CellRendererToggle()
        def cell_data(col, render, model, iter):
            row = model[iter]
            render.set_active(row[1].enabled(row[0]))
        render.connect('toggled', self.__toggled, model)
        column = gtk.TreeViewColumn("enabled", render)
        column.set_cell_data_func(render, cell_data)
        tv.append_column(column)

        render = gtk.CellRendererPixbuf()
        def cell_data(col, render, model, iter):
            icon = getattr(model[iter][0], 'PLUGIN_ICON', gtk.STOCK_EXECUTE)
            render.set_property('stock-id', icon)
        column = gtk.TreeViewColumn("image", render)
        column.set_cell_data_func(render, cell_data)
        tv.append_column(column)

        render = gtk.CellRendererText()
        render.set_property('ellipsize', pango.ELLIPSIZE_END)
        render.set_property('xalign', 0.0)
        column = gtk.TreeViewColumn("name", render)
        def cell_data(col, render, model, iter):
            render.set_property('text', model[iter][0].PLUGIN_NAME)
        column.set_cell_data_func(render, cell_data)
        column.set_expand(True)
        tv.append_column(column)

        sw.add(tv)
        sw.set_shadow_type(gtk.SHADOW_IN)

        tv.set_headers_visible(False)

        bbox = gtk.HBox(homogeneous=True, spacing=12)
        errors = qltk.Button(_("Show _Errors"), gtk.STOCK_DIALOG_WARNING)
        errors.set_focus_on_click(False)
        bbox.pack_start(errors)
        refresh = gtk.Button(stock=gtk.STOCK_REFRESH)
        refresh.set_focus_on_click(False)
        bbox.pack_start(refresh)
        vbox.pack_start(sw)
        vbox.pack_start(bbox, expand=False)
        vbox.set_size_request(250, -1)
        hbox.pack_start(vbox, expand=False)

        selection = tv.get_selection()
        desc = gtk.Label()
        desc.set_alignment(0, 0)
        desc.set_padding(6, 6)
        desc.set_line_wrap(True)
        desc.set_size_request(280, -1)
        selection.connect('changed', self.__description, desc)

        prefs = gtk.Frame()
        prefs.set_shadow_type(gtk.SHADOW_NONE)
        lab = gtk.Label()
        lab.set_markup("<b>%s</b>" % _("Preferences"))
        prefs.set_label_widget(lab)

        vb2 = gtk.VBox(spacing=12)
        vb2.pack_start(desc, expand=False)
        vb2.pack_start(prefs, expand=False)
        hbox.pack_start(vb2, expand=True)

        self.add(hbox)

        selection.connect('changed', self.__preferences, prefs)
        refresh.connect('clicked', self.__refresh, tv, desc, errors)
        errors.connect('clicked', self.__show_errors)
        tv.get_selection().emit('changed')
        refresh.clicked()
        hbox.set_size_request(550, 350)

        self.connect('destroy', self.__destroy)
        self.show_all()

    def __destroy(self, *args):
        config.write(const.CONFIG)

    def __description(self, selection, frame):
        model, iter = selection.get_selected()
        if not iter: return
        text = "<big>%s</big>\n" % util.escape(model[iter][0].PLUGIN_NAME)
        try: text += "<small>%s</small>\n" %(
            util.escape(model[iter][0].PLUGIN_VERSION))
        except (TypeError, AttributeError): pass
        try: text += "\n" + util.escape(model[iter][0].PLUGIN_DESC)
        except (TypeError, AttributeError): pass

        frame.set_markup(text)

    def __preferences(self, selection, frame):
        model, iter = selection.get_selected()
        if frame.child: frame.child.destroy()
        if iter and hasattr(model[iter][0], 'PluginPreferences'):
            try:
                prefs = model[iter][0].PluginPreferences(self)
            except:
                util.print_exc()
                frame.hide()
            else:
                if isinstance(prefs, gtk.Window):
                    b = gtk.Button(stock=gtk.STOCK_PREFERENCES)
                    b.connect_object('clicked', gtk.Window.show, prefs)
                    b.connect_object('destroy', gtk.Window.destroy, prefs)
                    frame.add(b)
                    frame.child.set_border_width(6)
                else:
                    frame.add(prefs)
                frame.show_all()
        else: frame.hide()

    def __toggled(self, render, path, model):
        render.set_active(not render.get_active())
        row = model[path]
        pm = row[1]
        pm.enable(row[0], render.get_active())
        pm.save()
        model.row_changed(row.path, row.iter)

    def __refresh(self, activator, view, desc, errors):
        model, sel = view.get_selection().get_selected()
        if sel: sel = model[sel][0]
        plugins = []
        failures = False
        model.clear()
        for pm in Manager.instances.values():
            pm.rescan()
            for plugin in pm.list():
                plugins.append((plugin.PLUGIN_NAME, plugin, pm))
            failures = failures or bool(pm.list_failures())

        plugins.sort()
        for plugin in plugins:
            it = model.append(row=plugin[1:])
            if plugin[1] is sel:
                view.get_selection().select_iter(it)
        if not plugins:
            desc.set_text(_("No plugins found."))
        errors.set_sensitive(failures)

    def __show_errors(self, activator):
        try: self.__win.present()
        except AttributeError:
            self.__win = qltk.Window()
            self.__win.set_title(_("Plugin Errors") + " - Quod Libet")
            self.__win.set_border_width(12)
            self.__win.set_transient_for(qltk.get_top_parent(self))
            self.__win.set_default_size(400, 250)

            scrolledwin = gtk.ScrolledWindow()
            self.__win.add(scrolledwin)
            vbox = gtk.VBox(spacing=6)
            scrolledwin.add_with_viewport(vbox)
            scrolledwin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
            scrolledwin.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse('#fff'))

            failures = {}
            for pm in Manager.instances.values():
                failures.update(pm.list_failures())
            keys = failures.keys()
            show_expanded = len(keys) <= 3
            for key in sorted(keys):
                expander = gtk.Expander("<b>%s</b>" % util.escape(key))
                expander.set_use_markup(True)
                if show_expanded: expander.set_expanded(True)

                # second line is always the __rescan line; don't show it
                message = failures[key][0:1] + failures[key][2:]
                failure = gtk.Label(''.join(message).strip())
                failure.set_alignment(0, 0)
                failure.set_padding(3, 3)
                failure.set_selectable(True)

                vbox.pack_start(expander, expand=False)
                expander.add(failure)

            scrolledwin.show_all()
            def delwin(*args): del self.__win
            self.__win.connect("destroy", delwin)
            self.__win.present()
