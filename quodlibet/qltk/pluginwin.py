# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gtk, pango
import const
import config
import qltk
import util

from qltk.views import HintedTreeView

class PluginWindow(qltk.Window):
    __window = None

    def __new__(klass, parent, pm):
        if klass.__window is None:
            return super(PluginWindow, klass).__new__(klass)
        else: return klass.__window

    def __init__(self, parent, pm):
        if type(self).__window: return
        else: type(self).__window = self
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
        model = gtk.ListStore(object)
        tv.set_model(model)
        tv.set_rules_hint(True)

        render = gtk.CellRendererToggle()
        def cell_data(col, render, model, iter, pm):
            render.set_active(pm.enabled(model[iter][0]))
        render.connect('toggled', self.__toggled, model, pm)
        column = gtk.TreeViewColumn("enabled", render)
        column.set_cell_data_func(render, cell_data, pm)
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
        refresh.connect('clicked', self.__refresh, tv, desc, pm, errors)
        errors.connect('clicked', self.__show_errors, pm)
        tv.get_selection().emit('changed')
        refresh.clicked()
        hbox.set_size_request(550, 350)

        self.connect('destroy', self.__destroy)
        self.show_all()

    def __destroy(self, *args):
        type(self).__window = None
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
                import traceback; traceback.print_exc()
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

    def __toggled(self, render, path, model, pm):
        render.set_active(not render.get_active())
        pm.enable(model[path][0], render.get_active())
        pm.save()
        model[path][0] = model[path][0]

    def __refresh(self, activator, view, desc, pm, errors):
        model, sel = view.get_selection().get_selected()
        if sel: sel = model[sel][0]
        model.clear()
        pm.rescan()
        plugins = pm.list()
        plugins.sort(lambda a, b: cmp(a.PLUGIN_NAME, b.PLUGIN_NAME))
        for plugin in plugins:
            it = model.append(row=[plugin])
            if plugin is sel: view.get_selection().select_iter(it)
        if not plugins:
            desc.set_text(_("No plugins found."))
        errors.set_sensitive(bool(len(pm.list_failures())))

    def __show_errors(self, activator, pm):
        try: self.__win.present()
        except AttributeError:
            self.__win = qltk.Window()
            self.__win.set_title(_("Quod Libet Plugin Load Errors"))
            self.__win.set_border_width(12)
            self.__win.set_resizable(False)
            self.__win.set_transient_for(qltk.get_top_parent(self))

            vbox = gtk.VBox(spacing=6)
            self.__win.add(vbox)
            
            failures = pm.list_failures()
            keys = failures.keys();
            keys.sort()
            show_expanded = len(keys) <= 3
            for key in keys:
                expander = gtk.Expander("<b>%s</b>" % key)
                expander.set_use_markup(True)
                if show_expanded: expander.set_expanded(True)

                frame = gtk.Frame()
                frame.set_shadow_type(gtk.SHADOW_IN)

                # second line is always the __rescan line; don't show it
                message = failures[key][0:1] + failures[key][2:]
                failure = gtk.Label(''.join(message).strip())
                failure.set_padding(3, 3)
                failure.set_selectable(True)

                vbox.pack_start(expander, expand=False)
                expander.add(frame)
                frame.add(failure)

            vbox.show_all()
            def delwin(*args): del self.__win
            self.__win.connect("destroy", delwin)
            self.__win.present()
