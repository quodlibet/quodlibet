# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, sys
import sre
import shutil # Move to Trash

import gtk, pango, gobject
import qltk

import const
import config
import player
import parser
import formats
import util

from util import to, tag
from gettext import ngettext
from library import library

if sys.version_info < (2, 4): from sets import Set as set
from properties import SongProperties

# Give us a namespace for now.. FIXME: We need to remove this later.
# Or, replace it with nicer wrappers!
class widgets(object): pass

# Provides some files in ~/.quodlibet to indicate what song is playing
# and whether the player is paused or not.
class FSInterface(object):
    def __init__(self, watcher):
        watcher.connect('paused', self.__paused)
        watcher.connect('unpaused', self.__unpaused)
        watcher.connect('song-started', self.__started)
        watcher.connect('song-ended', self.__ended)
        self.__paused(watcher)

    def __paused(self, watcher):
        try: file(const.PAUSED, "w").close()
        except EnvironmentError: pass

    def __unpaused(self, watcher):
        try: os.unlink(const.PAUSED)
        except EnvironmentError: pass

    def __started(self, watcher, song):
        if song:
            try: f = file(const.CURRENT, "w")
            except EnvironmentError: pass
            else:
                f.write(song.to_dump())
                f.close()

    def __ended(self, watcher, song, stopped):
        try: os.unlink(const.CURRENT)
        except EnvironmentError: pass

# Make a standard directory-chooser, and return the filenames and response.
class FileChooser(gtk.FileChooserDialog):
    def __init__(self, parent, title, initial_dir=None):
        super(FileChooser, self).__init__(
            title=title, parent=parent,
            action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                     gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        if initial_dir: self.set_current_folder(initial_dir)
        self.set_local_only(True)
        self.set_select_multiple(True)

    def run(self):
        resp = gtk.FileChooserDialog.run(self)
        fns = self.get_filenames()
        return resp, fns

class PluginWindow(gtk.Window):
    def __init__(self, parent):
        gtk.Window.__init__(self)
        self.set_title(_("Quod Libet Plugins"))
        self.set_border_width(12)
        self.set_resizable(False)
        self.set_transient_for(parent)
        icon_theme = gtk.icon_theme_get_default()
        self.set_icon(icon_theme.load_icon(
            const.ICON, 64, gtk.ICON_LOOKUP_USE_BUILTIN))

        hbox = gtk.HBox(spacing=12)        
        vbox = gtk.VBox(spacing=6)

        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        tv = qltk.HintedTreeView()
        model = gtk.ListStore(object)
        tv.set_model(model)
        tv.set_rules_hint(True)

        render = gtk.CellRendererToggle()
        def cell_data(col, render, model, iter):
            render.set_active(
                SongList.pm.enabled(model[iter][0]))
        render.connect('toggled', self.__toggled, model)
        column = gtk.TreeViewColumn("enabled", render)
        column.set_cell_data_func(render, cell_data)
        tv.append_column(column)

        render = gtk.CellRendererPixbuf()
        def cell_data(col, render, model, iter):
            render.set_property(
                'stock-id', getattr(model[iter][0], 'PLUGIN_ICON',
                                    gtk.STOCK_EXECUTE))
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

        refresh = gtk.Button(stock=gtk.STOCK_REFRESH)
        refresh.set_focus_on_click(False)
        vbox.pack_start(sw)
        vbox.pack_start(refresh, expand=False)
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
        refresh.connect('clicked', self.__refresh, tv, desc)
        tv.get_selection().emit('changed')
        refresh.clicked()
        hbox.set_size_request(550, 350)

        self.connect_object('destroy', self.__class__.__destroy, self)

        self.show_all()

    def __destroy(self):
        del(widgets.plugins)
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

    def __toggled(self, render, path, model):
        render.set_active(not render.get_active())
        SongList.pm.enable(model[path][0], render.get_active())
        SongList.pm.save()
        model[path][0] = model[path][0]

    def __refresh(self, activator, view, desc):
        model, sel = view.get_selection().get_selected()
        if sel: sel = model[sel][0]
        model.clear()
        SongList.pm.rescan()
        plugins = SongList.pm.list()
        plugins.sort(lambda a, b: cmp(a.PLUGIN_NAME, b.PLUGIN_NAME))
        for plugin in plugins:
            it = model.append(row=[plugin])
            if plugin is sel: view.get_selection().select_iter(it)
        if not plugins:
            desc.set_text(_("No plugins found."))

class AboutWindow(gtk.AboutDialog):
    def __init__(self, parent=None):
        gtk.AboutDialog.__init__(self)
        self.set_name("Quod Libet")
        self.set_version(const.VERSION)
        self.set_authors(const.AUTHORS)
        fmts = ", ".join([os.path.basename(name) for name, mod
                          in formats.modules if mod.extensions])
        text = "%s\n%s" % (_("Supported formats: %s"), _("Audio device: %s"))
        self.set_comments(text % (fmts, player.device.name))
        # Translators: Replace this with your name/email to have it appear
        # in the "About" dialog.
        self.set_translator_credits(_('translator-credits'))
        # The icon looks pretty ugly at this size.
        #self.set_logo_icon_name(const.ICON)
        self.set_website("http://www.sacredchao.net/quodlibet")
        self.set_copyright(
            "Copyright © 2004-2005 Joe Wreschnig, Michael Urman, & others\n"
            "<quodlibet@lists.sacredchao.net>")
        icon_theme = gtk.icon_theme_get_default()
        self.set_icon(icon_theme.load_icon(const.ICON, 64,
            gtk.ICON_LOOKUP_USE_BUILTIN))
        gtk.AboutDialog.run(self)
        self.destroy()

class PreferencesWindow(gtk.Window):
    class _Pane(object):
        def _toggle(self, c, name, section="settings"):
            config.set(section, name, str(bool(c.get_active())))

        def _changed(self, cb, name, section="settings"):
            config.set(section, name, str(cb.get_active()))

    class SongList(_Pane, gtk.VBox):
        def __init__(self):
            gtk.VBox.__init__(self, spacing=12)
            self.set_border_width(12)
            self.title = _("Song List")
            vbox = gtk.VBox(spacing=12)
            tips = gtk.Tooltips()

            c = qltk.ConfigCheckButton(
                _("_Jump to playing song automatically"), 'settings', 'jump')
            tips.set_tip(c, _("When the playing song changes, "
                              "scroll to it in the song list"))
            c.set_active(config.state("jump"))
            self.pack_start(c, expand=False)

            buttons = {}
            table = gtk.Table(3, 3)
            table.set_homogeneous(True)
            checks = config.get("settings", "headers").split()
            for j, l in enumerate(
                [[("~#disc", _("_Disc")),
                  ("album", _("Al_bum")),
                  ("~basename",_("_Filename"))],
                 [("~#track", _("_Track")),
                  ("artist", _("_Artist")),
                  ("~rating", _("_Rating"))],
                 [("title", tag("title")),
                  ("date", _("_Date")),
                  ("~length",_("_Length"))]]):
                for i, (k, t) in enumerate(l):
                    buttons[k] = gtk.CheckButton(t)
                    if k in checks:
                        buttons[k].set_active(True)
                        checks.remove(k)

                    table.attach(buttons[k], i, i + 1, j, j + 1)

            vbox.pack_start(table, expand=False)

            vbox2 = gtk.VBox()
            tiv = gtk.CheckButton(_("Title includes _version"))
            if "~title~version" in checks:
                buttons["title"].set_active(True)
                tiv.set_active(True)
                checks.remove("~title~version")
            aip = gtk.CheckButton(_("Album includes _part"))
            if "~album~part" in checks:
                buttons["album"].set_active(True)
                aip.set_active(True)
                checks.remove("~album~part")
            fip = gtk.CheckButton(_("Filename includes _folder"))
            if "~filename" in checks:
                buttons["~basename"].set_active(True)
                fip.set_active(True)
                checks.remove("~filename")

            t = gtk.Table(2, 2)
            t.set_homogeneous(True)
            t.attach(tiv, 0, 1, 0, 1)
            t.attach(aip, 0, 1, 1, 2)
            t.attach(fip, 1, 2, 0, 1)
            vbox.pack_start(t, expand=False)

            hbox = gtk.HBox(spacing=6)
            l = gtk.Label(_("_Others:"))
            hbox.pack_start(l, expand=False)
            others = gtk.Entry()
            if "~current" in checks: checks.remove("~current")
            others.set_text(" ".join(checks))
            tips.set_tip(
                others, _("Other headers to display, separated by spaces"))
            l.set_mnemonic_widget(others)
            l.set_use_underline(True)
            hbox.pack_start(others)
            vbox.pack_start(hbox, expand=False)

            apply = gtk.Button(stock=gtk.STOCK_APPLY)
            apply.connect(
                'clicked', self.__apply, buttons, tiv, aip, fip, others)
            b = gtk.HButtonBox()
            b.set_layout(gtk.BUTTONBOX_END)
            b.pack_start(apply)
            vbox.pack_start(b)

            frame = qltk.Frame(_("Visible Columns"), bold=True, child=vbox)
            tips.enable()
            self.connect_object('destroy', gtk.Tooltips.destroy, tips)
            self.pack_start(frame, expand=False)
            self.show_all()

        def __apply(self, button, buttons, tiv, aip, fip, others):
            headers = []
            for key in ["~#disc", "~#track", "title", "album", "artist",
                        "date", "~basename", "~rating", "~length"]:
                if buttons[key].get_active(): headers.append(key)
            if tiv.get_active():
                try: headers[headers.index("title")] = "~title~version"
                except ValueError: pass
            if aip.get_active():
                try: headers[headers.index("album")] = "~album~part"
                except ValueError: pass
            if fip.get_active():
                try: headers[headers.index("~basename")] = "~filename"
                except ValueError: pass

            headers.extend(others.get_text().split())
            if "~current" in headers: headers.remove("~current")
            headers.insert(0, "~current")
            config.set("settings", "headers", " ".join(headers))
            SongList.set_all_column_headers(headers)

    class Browsers(_Pane, gtk.VBox):
        def __init__(self):
            gtk.VBox.__init__(self, spacing=12)
            self.set_border_width(12)
            self.title = _("Browsers")
            tips = gtk.Tooltips()
            c = qltk.ConfigCheckButton(
                _("Color _search terms"), 'browsers', 'color')
            c.set_active(config.getboolean("browsers", "color"))
            tips.set_tip(
                c, _("Display simple searches in blue, "
                     "advanced ones in green, and invalid ones in red"))
            tips.enable()
            self.connect_object('destroy', gtk.Tooltips.destroy, tips)
            hb = gtk.HBox(spacing=6)
            l = gtk.Label(_("_Global filter:"))
            l.set_use_underline(True)
            e = qltk.ValidatingEntry(parser.is_valid_color)
            e.set_text(config.get("browsers", "background"))
            e.connect('changed', self._entry, 'background', 'browsers')
            l.set_mnemonic_widget(e)
            hb.pack_start(l, expand=False)
            hb.pack_start(e)
            self.pack_start(hb, expand=False)

            f = qltk.Frame(_("Search Bar"), bold=True, child=c)
            self.pack_start(f, expand=False)

            t = gtk.Table(2, 4)
            t.set_col_spacings(3)
            t.set_row_spacings(3)
            cbes = [gtk.combo_box_entry_new_text() for i in range(3)]
            values = ["", "genre", "artist", "album"]
            current = config.get("browsers", "panes").split()
            for i, c in enumerate(cbes):
                for v in values:
                    c.append_text(v)
                    try: c.child.set_text(current[i])
                    except IndexError: pass
                lbl = gtk.Label(_("_Pane %d:") % (i + 1))
                lbl.set_use_underline(True)
                lbl.set_mnemonic_widget(c)
                t.attach(lbl, 0, 1, i, i + 1, xoptions=0)
                t.attach(c, 1, 2, i, i + 1)
            b = gtk.Button(stock=gtk.STOCK_APPLY)
            b.connect('clicked', self.__update_panes, cbes)
            bbox = gtk.HButtonBox()
            bbox.set_layout(gtk.BUTTONBOX_END)
            bbox.pack_start(b)
            t.attach(bbox, 0, 2, 3, 4)
            self.pack_start(
                qltk.Frame(_("Paned Browser"), bold=True, child=t),
                expand=False)
            self.show_all()

        def _entry(self, entry, name, section="settings"):
            config.set(section, name, entry.get_text())

        def __update_panes(self, button, cbes):
            panes = " ".join([c.child.get_text() for c in cbes])
            config.set('browsers', 'panes', panes)
            if hasattr(widgets.main.browser, 'refresh_panes'):
                widgets.main.browser.refresh_panes(restore=True)

    class Player(_Pane, gtk.VBox):
        def __init__(self):
            gtk.VBox.__init__(self, spacing=12)
            self.set_border_width(12)
            self.title = _("Player")
            vbox = gtk.VBox()
            c = qltk.ConfigCheckButton(
                _("Show _album covers"), 'settings', 'cover')
            c.set_active(config.state("cover"))
            c.connect('toggled', self.__toggle_cover)
            vbox.pack_start(c)

            c = gtk.CheckButton(_("Closing _minimizes to system tray"))
            c.set_sensitive(widgets.main.icon.enabled)
            c.set_active(config.getboolean('plugins', 'icon_close') and
                         c.get_property('sensitive'))
            c.connect('toggled', self._toggle, 'icon_close', 'plugins')
            vbox.pack_start(c)
            self.pack_start(vbox, expand=False)

            f = qltk.Frame(_("_Volume Normalization"), bold=True)
            cb = gtk.combo_box_new_text()
            cb.append_text(_("No volume adjustment"))
            cb.append_text(_('Per-song ("Radio") volume adjustment'))
            cb.append_text(_('Per-album ("Audiophile") volume adjustment'))
            f.get_label_widget().set_mnemonic_widget(cb)
            f.child.add(cb)
            cb.set_active(config.getint("settings", "gain"))
            cb.connect('changed', self._changed, 'gain')
            self.pack_start(f, expand=False)

            self.show_all()

        def __toggle_cover(self, c):
            if config.state("cover"): widgets.main.image.show()
            else: widgets.main.image.hide()

    class Library(_Pane, gtk.VBox):
        def __init__(self):
            gtk.VBox.__init__(self, spacing=12)
            self.set_border_width(12)
            self.title = _("Library")
            f = qltk.Frame(_("Scan _Directories"), bold=True)
            hb = gtk.HBox(spacing=6)
            b = qltk.Button(_("_Select"), gtk.STOCK_OPEN)
            e = gtk.Entry()
            e.set_text(util.fsdecode(config.get("settings", "scan")))
            f.get_label_widget().set_mnemonic_widget(e)
            hb.pack_start(e)
            tips = gtk.Tooltips()
            tips.set_tip(e, _("Songs placed in these folders will "
                              "be added to your library"))
            hb.pack_start(b, expand=False)
            b.connect('clicked', self.__select, e, const.HOME)
            e.connect('changed', self._changed, 'scan')
            f.child.add(hb)
            self.pack_start(f, expand=False)

            f = qltk.Frame(_("Tag Editing"), bold=True)
            vbox = gtk.VBox(spacing=6)
            hb = gtk.HBox(spacing=6)
            e = gtk.Entry()
            e.set_text(config.get("editing", "split_on"))
            e.connect('changed', self._changed, 'split_on', 'editing')
            tips.set_tip(e, _('Separators for splitting tags'))
            l = gtk.Label(_("Split _on:"))
            l.set_use_underline(True)
            l.set_mnemonic_widget(e)
            hb.pack_start(l, expand=False)
            hb.pack_start(e)
            cb = qltk.ConfigCheckButton(
                _("Show _programmatic comments"), 'editing', 'allcomments')
            cb.set_active(config.getboolean("editing", "allcomments"))
            vbox.pack_start(hb, expand=False)
            vbox.pack_start(cb, expand=False)
            f.child.add(vbox)
            tips.enable()
            self.connect_object('destroy', gtk.Tooltips.destroy, tips)
            self.pack_start(f)
            self.show_all()

        def __select(self, button, entry, initial):
            chooser = FileChooser(self.parent.parent.parent,
                                  _("Select Directories"), initial)
            resp, fns = chooser.run()
            chooser.destroy()
            if resp == gtk.RESPONSE_OK:
                entry.set_text(":".join(map(util.fsdecode, fns)))

        def _changed(self, entry, name, section="settings"):
            config.set(section, name, entry.get_text())

    def __init__(self, parent):
        gtk.Window.__init__(self)
        self.set_title(_("Quod Libet Preferences"))
        self.set_border_width(12)
        self.set_resizable(False)
        self.set_transient_for(parent)
        icon_theme = gtk.icon_theme_get_default()
        self.set_icon(icon_theme.load_icon(
            const.ICON, 64, gtk.ICON_LOOKUP_USE_BUILTIN))

        self.add(qltk.Notebook())
        for Page in [self.SongList, self.Browsers, self.Player, self.Library]:
            self.child.append_page(Page())

        self.connect_object('destroy', PreferencesWindow.__destroy, self)
        self.show_all()

    def __destroy(self):
        del(widgets.preferences)
        config.write(const.CONFIG)

class BigCenteredImage(gtk.Window):
    def __init__(self, title, filename):
        gtk.Window.__init__(self)
        width = gtk.gdk.screen_width() / 2
        height = gtk.gdk.screen_height() / 2
        pixbuf = gtk.gdk.pixbuf_new_from_file(filename)

        x_rat = pixbuf.get_width() / float(width)
        y_rat = pixbuf.get_height() / float(height)
        if x_rat > 1 or y_rat > 1:
            if x_rat > y_rat: height = int(pixbuf.get_height() / x_rat)
            else: width = int(pixbuf.get_width() / y_rat)
            pixbuf = pixbuf.scale_simple(
                width, height, gtk.gdk.INTERP_BILINEAR)

        self.set_title(title)
        self.set_decorated(False)
        self.set_position(gtk.WIN_POS_CENTER)
        self.set_modal(False)
        self.set_icon(pixbuf)
        self.add(gtk.Frame())
        self.child.set_shadow_type(gtk.SHADOW_OUT)
        self.child.add(gtk.EventBox())
        self.child.child.add(gtk.Image())
        self.child.child.child.set_from_pixbuf(pixbuf)

        # The eventbox
        self.child.child.connect_object(
            'button-press-event', BigCenteredImage.__destroy, self)
        self.child.child.connect_object(
            'key-press-event', BigCenteredImage.__destroy, self)
        self.show_all()

    def __destroy(self, event):
        self.destroy()

class TrayIcon(object):
    def __init__(self, pixbuf, cbs):
        try:
            import trayicon
        except:
            self.__icon = None
        else:
            self.__icon = trayicon.TrayIcon('quodlibet')
            self.__tips = gtk.Tooltips()
            eb = gtk.EventBox()
            i = gtk.Image()
            i.set_from_pixbuf(pixbuf)
            eb.add(i)
            self.__mapped = False
            self.__icon.connect('map-event', self.__got_mapped, True)
            self.__icon.connect('unmap-event', self.__got_mapped, False)
            self.__icon.add(eb)
            self.__icon.child.connect("button-press-event", self.__event)
            self.__icon.child.connect("scroll-event", self.__scroll)
            self.__cbs = cbs
            self.__icon.show_all()

    def __got_mapped(self, s, event, value):
        self.__mapped = value

    def __enabled(self):
        return ((self.__icon is not None) and
                (self.__mapped) and
                (self.__icon.get_property('visible')))

    enabled = property(__enabled)

    def __event(self, widget, event, button=None):
        c = self.__cbs.get(button or event.button)
        if callable(c): c(event)

    def __scroll(self, widget, event):
        button = {gtk.gdk.SCROLL_DOWN: 4,
                  gtk.gdk.SCROLL_UP: 5,
                  gtk.gdk.SCROLL_RIGHT: 6,
                  gtk.gdk.SCROLL_LEFT: 7}.get(event.direction)
        self.__event(widget, event, button)


    def __set_tooltip(self, tooltip):
        if self.__icon: self.__tips.set_tip(self.__icon, tooltip)

    tooltip = property(None, __set_tooltip)

    def destroy(self):
        if self.__icon: self.__icon.destroy()

class PlaylistWindow(gtk.Window):

    # If we open a playlist whose window is already displayed, bring it
    # to the forefront rather than make a new one.
    __list_windows = {}
    def __new__(klass, name, *args, **kwargs):
        win = klass.__list_windows.get(name, None)
        if win is None:
            win = super(PlaylistWindow, klass).__new__(
                klass, name, *args, **kwargs)
            win.__initialize_window(name)
            klass.__list_windows[name] = win
            # insert sorted, unless present
            def insert_sorted(model, path, iter, last_try):
                if model[iter][1] == win.__plname:
                    return True # already present
                if model[iter][1] > win.__plname:
                    model.insert_before(iter, [win.__prettyname, win.__plname])
                    return True # inserted
                if path[0] == last_try:
                    model.insert_after(iter, [win.__prettyname, win.__plname])
                    return True # appended
            model = PlayList.lists_model()
            model.foreach(insert_sorted, len(model) - 1)
        return win

    def __init__(self, name):
        self.present()

    def set_name(self, name):
        self.__prettyname = name
        self.__plname = util.QuerySafe.encode(name)
        self.set_title('Quod Libet Playlist: %s' % name)

    def __destroy(self, view):
        del(self.__list_windows[self.__prettyname])
        if not len(view.get_model()):
            def remove_matching(model, path, iter, name):
                if model[iter][1] == name:
                    model.remove(iter)
                    return True
            PlayList.lists_model().foreach(remove_matching, self.__plname)

    def __initialize_window(self, name):
        gtk.Window.__init__(self)
        icon_theme = gtk.icon_theme_get_default()
        self.set_icon(icon_theme.load_icon(
            const.ICON, 64, gtk.ICON_LOOKUP_USE_BUILTIN))
        self.set_destroy_with_parent(True)
        self.set_default_size(400, 400)
        self.set_border_width(12)

        vbox = gtk.VBox(spacing=6)
        self.add(vbox)

        view = PlayList(name)
        bar = SearchBar(save=False)
        bar.connect('songs-selected', self.__add_query_results, view)
        vbox.pack_start(bar, expand=False, fill=False)

        swin = gtk.ScrolledWindow()
        swin.set_shadow_type(gtk.SHADOW_IN)
        swin.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        vbox.pack_start(swin)
        swin.add(view)
        swin.show_all()
        vbox.show()

        self.set_name(name)
        self.connect_object('destroy', self.__destroy, view)
        self.show()

    def __add_query_results(self, browser, songs, sort, view):
        songs.sort()
        view.append_songs(songs)

# A tray icon aware of UI policy -- left click shows/hides, right
# click makes a callback.
class HIGTrayIcon(TrayIcon):
    def __init__(self, pixbuf, window, cbs=None):
        self.__window = window
        cbs = cbs or {}
        cbs[1] = self.__showhide
        TrayIcon.__init__(self, pixbuf, cbs)

    def hide_window(self):
        if self.__window.get_property('visible'):
            self.__showhide(None)

    def __showhide(self, event):
        if self.__window.get_property('visible'):
            self.__pos = self.__window.get_position()
            self.__window.hide()
        else:
            self.__window.move(*self.__pos)
            self.__window.show()

class QLTrayIcon(HIGTrayIcon):
    def __init__(self, window, volume):
        menu = gtk.Menu()
        playpause = gtk.ImageMenuItem(_("_Play"))
        pp_img = gtk.Image()
        pp_img.set_from_stock(gtk.STOCK_MEDIA_PLAY, gtk.ICON_SIZE_MENU)
        playpause.set_image(pp_img)
        playpause.connect('activate', self.__playpause)

        previous = gtk.ImageMenuItem(const.SM_PREVIOUS)
        prev_img = gtk.Image()
        prev_img.set_from_stock(gtk.STOCK_MEDIA_PREVIOUS, gtk.ICON_SIZE_MENU)
        previous.set_image(prev_img)
        previous.connect('activate', lambda *args: player.playlist.previous())

        next = gtk.ImageMenuItem(const.SM_NEXT)
        next_img = gtk.Image()
        next_img.set_from_stock(gtk.STOCK_MEDIA_PLAY, gtk.ICON_SIZE_MENU)
        next.set_image(next_img)
        next.connect('activate', lambda *args: player.playlist.next())

        props = gtk.ImageMenuItem(gtk.STOCK_PROPERTIES)
        props.connect('activate', self.__properties)

        rating = gtk.Menu()
        def set_rating(value):
            if widgets.watcher.song is None: return
            else:
                widgets.watcher.song["~#rating"] = value
                widgets.watcher.changed([widgets.watcher.song])
        for i in range(5):
            item = gtk.MenuItem("%s %d" % (util.format_rating(i), i))
            item.connect_object('activate', set_rating, i)
            rating.append(item)
        ratings = gtk.MenuItem(_("Rating"))
        ratings.set_submenu(rating)

        quit = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        quit.connect('activate', gtk.main_quit)

        for item in [playpause, gtk.SeparatorMenuItem(), previous, next,
                     gtk.SeparatorMenuItem(), props, ratings,
                     gtk.SeparatorMenuItem(), quit]:
            menu.append(item)

        menu.show_all()

        widgets.watcher.connect('song-started', self.__set_song, next, props)
        widgets.watcher.connect('paused', self.__set_paused, menu, True)
        widgets.watcher.connect('unpaused', self.__set_paused, menu, False)

        cbs = {
            2: lambda *args: self.__playpause(args[0]),
            3: lambda ev, *args:
            menu.popup(None, None, None, ev.button, ev.time),
            4: lambda *args: volume.set_value(volume.get_value()-0.05),
            5: lambda *args: volume.set_value(volume.get_value()+0.05),
            6: lambda *args: player.playlist.next(),
            7: lambda *args: player.playlist.previous()
            }

        icon_theme = gtk.icon_theme_get_default()
        p = icon_theme.load_icon(
            const.ICON, 16, gtk.ICON_LOOKUP_USE_BUILTIN)

        HIGTrayIcon.__init__(self, p, window, cbs)

    def __set_paused(self, watcher, menu, paused):
        menu.get_children()[0].destroy()
        stock = [gtk.STOCK_MEDIA_PAUSE, gtk.STOCK_MEDIA_PLAY][paused]
        playpause = gtk.ImageMenuItem(stock)
        playpause.connect('activate', self.__playpause)
        playpause.show()
        menu.prepend(playpause)

    def __playpause(self, activator):
        if widgets.watcher.song: player.playlist.paused ^= True
        else: player.playlist.reset()

    def __properties(self, activator):
        if widgets.watcher.song:
            SongProperties([widgets.watcher.song], widgets.watcher)

    def __set_song(self, watcher, song, *items):
        for item in items: item.set_sensitive(bool(song))
        if song:
            try:
                pattern = util.FileFromPattern(
                    config.get("plugins", "icon_tooltip"), filename=False)
            except ValueError:
                pattern = util.FileFromPattern(
                    "<album|<album~discnumber~part~tracknumber~title~version>|"
                    "<artist~title~version>>", filename=False)
            self.tooltip = pattern.match(song)
        else: self.tooltip = _("Not playing")

class MmKeys(object):
    def __init__(self, cbs):
        try:
            import mmkeys
        except: pass
        else:
            self.__keys = mmkeys.MmKeys()
            map(self.__keys.connect, *zip(*cbs.items()))

# Browers are how the audio library is presented to the user; they
# create the list of songs that MainSongList is filled with, and pass
# them back via a callback function.
class Browser(object):
    # Unfortunately, GObjects do not play with Python multiple inheritance.
    # So, we need to reasssign this in every subclass.
    __gsignals__ = {
        'songs-selected':
        (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object, object))
        }

    # Packing options. False if the browser should be packed into the
    # window's VBox with expand=False. Otherwise, this should be
    # a function that returns an object like an RPaned; the browser
    # and MainSongList are both packed into it.
    expand = False # Packing options

    # If true, the global filter will be applied by MainSongList to
    # the songs returned.
    background = True

    # Returns true if the song should remain on the song list. Used to
    # implement dynamic playlist removal when a song ends.
    def dynamic(self, song): return True

    # Save/restore selected songlist. Browsers should save whatever
    # they need to recreate the criteria for the current song list (not
    # the list itself). restore is called at startup if the browser
    # is the first loaded.
    def save(self): raise NotImplementedError
    def restore(self): raise NotImplementedError

    # Decides whether "filter on foo" menu entries are available.
    def can_filter(self, key): return False

    # Actually do the filtering (with a union of values).
    def filter(self, key, values): raise NotImplementedError

    # Scroll to something related to the current song.
    def scroll(self): pass

# A browser that the user only interacts with indirectly, via the
# Filter menu. The HBox remains empty.
class EmptyBar(gtk.HBox, Browser):
    __gsignals__ = Browser.__gsignals__

    def __init__(self):
        gtk.HBox.__init__(self)
        # When _text is None, calls to activate are ignored. This is to
        # avoid the song list changing when the user switches browses and
        # then refreshes.
        self._text = None

    def dynamic(self, song):
        if self._text is not None:
            try: return parser.parse(self._text).search(song)
            except parser.error: return True
        else: return True

    def set_text(self, text):
        if isinstance(text, str): text = text.decode('utf-8')
        self._text = text

    def save(self):
        config.set("browsers", "query_text", self._text.encode('utf-8'))

    def restore(self):
        try: self.set_text(config.get("browsers", "query_text"))
        except Exception: pass

    def activate(self):
        if self._text is not None:
            try: songs = library.query(self._text)
            except parser.error: pass
            else:
                self.emit('songs-selected', songs, None)
                self.save()

    def can_filter(self, key): return True

    def filter(self, key, values):
        if key.startswith("~#"):
            nheader = key[2:]
            queries = ["#(%s = %d)" % (nheader, i) for i in values]
            self.set_text("|(" + ", ".join(queries) + ")")
        else:
            text = ", ".join(
                ["'%s'c" % v.replace("\\", "\\\\").replace("'", "\\'")
                 for v in values])
            if key.startswith("~"): key = key[1:]
            self.set_text(u"%s = |(%s)" % (key, text))
        self.activate()

gobject.type_register(EmptyBar)

# Like EmptyBar, but the user can also enter a query manually. This
# is QL's default browser. EmptyBar handles all the GObject stuff.
class SearchBar(EmptyBar):
    # Most browsers implement something like save/play. If save is
    # false, Browser#save should do nothing. Likewise, if play is false,
    # the browser should never start songs playing. These are used
    # when making browsers for the Library Browser windows.
    def __init__(self, save=True, play=True):
        EmptyBar.__init__(self)
        self.__save = save

        hb = gtk.HBox()
        lab = gtk.Label("_Limit:")
        lab.set_padding(3, 0)
        limit = gtk.SpinButton()
        limit.set_numeric(True)
        limit.set_range(0, 1000000)
        limit.set_increments(5, 50)
        lab.set_mnemonic_widget(limit)
        lab.set_use_underline(True)
        hb.pack_start(lab)
        hb.pack_start(limit)
        self.pack_start(hb, expand=False)

        tips = gtk.Tooltips()
        combo = qltk.ComboBoxEntrySave(
            const.QUERIES, model="searchbar", count=15)
        clear = gtk.Button()
        clear.add(gtk.image_new_from_stock(gtk.STOCK_CLEAR,gtk.ICON_SIZE_MENU))
        tips.set_tip(clear, _("Clear search"))
        clear.connect_object('clicked', self.set_text, "")
                  
        search = gtk.Button()
        b = gtk.HBox(spacing=2)
        b.pack_start(gtk.image_new_from_stock(
            gtk.STOCK_FIND, gtk.ICON_SIZE_MENU))
        b.pack_start(gtk.Label(_("Search")))
        search.add(b)
        tips.set_tip(search, _("Search your audio library"))
        search.connect_object('clicked', self.__text_parse, combo.child)
        combo.child.connect('activate', self.__text_parse)
        limit.connect_object_after('activate', self.__text_parse, combo.child)
        combo.child.connect('changed', self.__test_filter)
        tips.enable()
        combo.child.connect('realize', lambda w: w.grab_focus())
        combo.child.connect('populate-popup', self.__menu, hb)
        self.connect_object('destroy', gtk.Tooltips.destroy, tips)
        self.pack_start(combo)
        self.pack_start(clear, expand=False)
        self.pack_start(search, expand=False)
        self.show_all()
        self.__limit = limit
        hb.hide_all()

    def __menu(self, entry, menu, hb):
        sep = gtk.SeparatorMenuItem()
        menu.prepend(sep)
        item = gtk.CheckMenuItem(_("_Limit Results"))
        menu.prepend(item)
        item.set_active(hb.get_property('visible'))
        item.connect('toggled', self.__showhide_limit, hb)
        item.show(); sep.show()

    def __showhide_limit(self, button, hb):
        if button.get_active(): hb.show_all()
        else: hb.hide_all()

    def activate(self):
        if self._text is not None:
            try: songs = library.query(self._text)
            except parser.error: pass
            else:
                self.get_children()[1].prepend_text(self._text)
                val = self.__limit.get_value_as_int()
                if (self.__limit.get_property('visible') and
                    val and len(songs) > val):
                    import random
                    random.shuffle(songs)
                    songs = songs[:val]
                self.emit('songs-selected', songs, None)
                if self.__save: self.save()
                self.get_children()[1].write(const.QUERIES)

    def set_text(self, text):
        self.get_children()[1].child.set_text(text)
        if isinstance(text, str): text = text.decode('utf-8')
        self._text = text

    def __text_parse(self, entry):
        text = entry.get_text()
        if parser.is_parsable(text):
            self._text = text.decode('utf-8')
            self.activate()

    def __test_filter(self, textbox):
        if not config.getboolean('browsers', 'color'): return
        text = textbox.get_text().decode('utf-8')
        gobject.idle_add(
            self.__set_entry_color, textbox, parser.is_valid_color(text))

    def __set_entry_color(self, entry, color):
        layout = entry.get_layout()
        text = layout.get_text()
        markup = '<span foreground="%s">%s</span>' %(
            color, util.escape(text))
        layout.set_markup(markup)

class AlbumList(Browser, gtk.VBox):
    expand = qltk.RHPaned
    __gsignals__ = Browser.__gsignals__

    # Something like an AudioFile, but for a whole album.
    class _Album(object):
        __covers = {}
        __pending_covers = []

        def clear_cache(klass): klass.__covers.clear()
        clear_cache = classmethod(clear_cache)

        def __init__(self, title):
            self.length = 0
            self.discs = 1
            self.tracks = 0
            self.date = ""
            self.people = set()
            self.title = title
            self.songs = set()
            self.cover = self.__covers.get(self.title, False)
            self.genre = set()

        def get(self, key, default=None):
            if key == "~#length": return self.length
            elif key == "~#tracks": return self.tracks
            elif key == "~#discs": return self.discs
            elif key == "~length": return self.__length
            elif key in ["title", "album"]: return self.title
            elif key == "date": return self.date
            elif key in ["people", "artist", "artists"]:
                return "\n".join(self.people)
            elif key in "genre":
                return "\n".join(self.genre)
            else: return default

        __call__ = get

        # All songs added, cache info.
        def finalize(self):
            self.tracks = len(self.songs)
            self.length = sum([song["~#length"] for song in self.songs])
            self.__long_length = util.format_time_long(self.length)
            self.__length = util.format_time(self.length)
            people = {}
            self.genre = set()
            for song in self.songs:
                for w, key in enumerate(["performer", "composer", "artist"]):
                    for person in song.list(key):
                        if person not in people:
                            people[person] = 0
                        people[person] -= 1000 ** w
                self.genre.update(song.list("genre"))
            self.people = [(num, person) for (person, num) in people.items()]
            self.people.sort()
            self.people = [person for (num, person) in self.people]

            if self.title:
                for song in self.songs:
                    if "date" in song:
                        self.date = song.list("date")[0]
                    self.discs = max(self.discs, song("~#disc", 0))

            text = "<i><b>%s</b></i>" % util.escape(
                self.title or _("Songs not in an album"))
            if self.date: text += " (%s)" % self.date
            text += "\n<small>"
            if self.discs > 1:
                text += ngettext(
                    "%d disc", "%d discs", self.discs) % self.discs + " - "
            text += ngettext(
                "%d track", "%d tracks", self.tracks) % self.tracks
            text += " - " + self.__long_length
            text += "</small>\n" + ", ".join(map(util.escape, self.people))
            self.markup = text

        def add(self, song):
            self.songs.add(song)
            if self.title:
                if self.cover is False:
                    self.cover = None
                    if not self.__pending_covers: gobject.idle_add(
                        self.__get_covers, priority=gobject.PRIORITY_LOW)
                    self.__pending_covers.append([self.__get_cover, song])

        def remove(self, song):
            try: self.songs.remove(song)
            except KeyError: return False
            else: return True

        def __nonzero__(self): return bool(self.songs)

        def __get_covers(self):
            try: get, song = self.__pending_covers.pop()
            except IndexError: return
            get(song)
            gobject.idle_add(self.__get_covers, priority=gobject.PRIORITY_LOW)

        def __get_cover(self, song):
            if self._iter is None: return
            cover = song.find_cover()
            if cover is not None:
                try:
                    cover = gtk.gdk.pixbuf_new_from_file_at_size(
                        cover.name, 48, 48)
                except: pass
                else:
                    # add a black outline
                    w, h = cover.get_width(), cover.get_height()
                    newcover = gtk.gdk.Pixbuf(
                        gtk.gdk.COLORSPACE_RGB, True, 8, w + 2, h + 2)
                    newcover.fill(0x000000ff)
                    cover.copy_area(0, 0, w, h, newcover, 1, 1)
                    self.cover = newcover
                    self.__covers[self.title] = newcover
                    self._model.row_changed(
                        self._model.get_path(self._iter), self._iter)

    # An auto-searching entry; it wraps is a TreeModelFilter whose parent
    # is the album list.
    class FilterEntry(qltk.ValidatingEntry):
        def __init__(self, model):
            qltk.ValidatingEntry.__init__(self, parser.is_valid_color)
            self.connect_object('changed', self.__filter_changed, model)
            self.__refill_id = None
            self.__filter = None
            self.inhibit = False
            model.set_visible_func(self.__parse)

        def __parse(self, model, iter):
            if self.__filter is None: return True
            elif model[iter][0] is None: return False
            else: return self.__filter(model[iter][0])

        def __filter_changed(self, model):
            if self.__refill_id is not None:
                gobject.source_remove(self.__refill_id)
                self.__refill_id = None
            text = self.get_text().decode('utf-8')
            if parser.is_parsable(text):
                if not text: self.__filter = None
                else: self.__filter = parser.parse(text).search
                self.__refill_id = gobject.timeout_add(
                    500, self.__refilter, model)

        def __refilter(self, model):
            self.inhibit = True
            model.refilter()
            self.inhibit = False

    # Sorting, either by people or album title. It wraps a TreeModelSort
    # whose parent is the album list.
    class SortCombo(gtk.ComboBox):
        def __init__(self, model):
            # Contains string to display, function to do sorting
            cbmodel = gtk.ListStore(str, object)
            gtk.ComboBox.__init__(self, cbmodel)
            cell = gtk.CellRendererText()
            self.pack_start(cell, True)
            self.add_attribute(cell, 'text', 0)

            for text, func in [
                (_("Sort by title"), self.__compare_title),
                (_("Sort by artist"), self.__compare_artist)
                ]: cbmodel.append(row=[text, func])

            self.connect_object('changed', self.__set_cmp_func, model)
            try: active = config.getint('browsers', 'album_sort')
            except: active = 0
            self.set_active(active)

        def __set_cmp_func(self, model):
            active = self.get_active()
            config.set("browsers", "album_sort", str(active))
            model.set_default_sort_func(self.get_model()[(active,)][1])

        def __compare_title(self, model, i1, i2):
            a1, a2 = model[i1][0], model[i2][0]
            if (a1 and a2) is None: return cmp(a1, a2)
            elif not a1.title: return 1
            elif not a2.title: return -1
            else: return cmp(a1.title, a2.title)

        def __compare_artist(self, model, i1, i2):
            a1, a2 = model[i1][0], model[i2][0]
            if (a1 and a2) is None: return cmp(a1, a2)
            elif a1.title == "": return 1
            elif a2.title == "": return -1
            else: return (cmp(a1.people, a2.people) or
                          cmp(a1.date, a2.date) or
                          cmp(a1.title, a2.title))

    class _AlbumStore(gtk.ListStore):
        def get_albums(self):
            albums = [row[0] for row in self]
            try: albums.remove(None)
            except ValueError: pass
            return dict([(a.title, a) for a in albums])

    def __init__(self, save=True, play=True):
        gtk.VBox.__init__(self)

        self.__save = save

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        view = qltk.HintedTreeView()
        view.set_headers_visible(False)
        model = self._AlbumStore(object)
        model_sort = gtk.TreeModelSort(model)
        model_filter = model_sort.filter_new()
        view.set_model(model_filter)

        render = gtk.CellRendererPixbuf()
        column = gtk.TreeViewColumn("covers", render)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
        render.set_property('xpad', 2)
        render.set_property('ypad', 2)
        render.set_property('width', 56)
        render.set_property('height', 56)

        def cell_data_pb(column, cell, model, iter):
            album = model[iter][0]
            if album is None: cell.set_property('pixbuf', None)
            elif album.cover: cell.set_property('pixbuf', album.cover)
            else: cell.set_property('pixbuf', None)
        column.set_cell_data_func(render, cell_data_pb)
        view.append_column(column)

        render = gtk.CellRendererText()
        column = gtk.TreeViewColumn("albums", render)
        render.set_property('ellipsize', pango.ELLIPSIZE_END)
        def cell_data(column, cell, model, iter):
            album = model[iter][0]
            if album is None:
                text = "<b>%s</b>" % _("All Albums")
                text += "\n" + ngettext("%d album", "%d albums",
                        len(model) - 1) % (len(model) - 1)
                cell.markup = text
            else: cell.markup = model[iter][0].markup
            cell.set_property('markup', cell.markup)
        column.set_cell_data_func(render, cell_data)
        view.append_column(column)

        view.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        view.set_rules_hint(True)
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        sw.add(view)
        e = self.FilterEntry(model_filter)

        if play: view.connect('row-activated', self.__play_selection)
        view.get_selection().connect('changed', self.__selection_changed, e)
        for s in [
            widgets.watcher.connect('removed', self.__remove_songs, model),
            widgets.watcher.connect('changed', self.__changed_songs, model),
            widgets.watcher.connect('added', self.__add_songs, model),
            ]:
            self.connect_object('destroy', widgets.watcher.disconnect, s)

        menu = gtk.Menu()
        button = gtk.ImageMenuItem(gtk.STOCK_REFRESH)
        props = gtk.ImageMenuItem(gtk.STOCK_PROPERTIES)
        menu.append(button)
        menu.append(props)
        menu.show_all()
        button.connect('activate', self.__refresh, view, model, True)
        props.connect('activate', self.__properties, view)

        view.connect_object('popup-menu', gtk.Menu.popup, menu,
                            None, None, None, 2, 0)
        view.connect('button-press-event', self.__button_press, menu)

        hb = gtk.HBox(spacing=6)
        hb.pack_start(self.SortCombo(model_sort), expand=False)
        hb.pack_start(e)
        self.pack_start(hb, expand=False)
        self.pack_start(sw, expand=True)
        self.__refresh(None, view, model)
        self.show_all()

    def __get_selected_albums(self, selection):
        model, rows = selection.get_selected_rows()
        if not model or not rows: return set([])
        albums = [model[row][0] for row in rows]
        if None in albums: return None
        else: return albums

    def __update(self, changed, model):
        to_change = []
        to_remove = []        
        def update(model, path, iter):
            album = model[iter][0]
            if album is not None and album.title in changed:
                if album: to_change.append((path, iter))
                else: to_remove.append(iter)
                album.finalize()
        model.foreach(update)
        if to_change: map(model.row_changed, *zip(*to_change))
        if to_remove: map(model.remove, to_remove)

    def __remove_songs(self, watcher, removed, model):
        albums = model.get_albums()
        changed = set()
        for title, album in albums.iteritems():
            if True in map(album.remove, removed): changed.add(title)
        self.__update(changed, model)

    def __changed_songs(self, watcher, changed, model):
        self.__remove_songs(watcher, changed, model)
        self.__add_songs(watcher, changed, model)

    def __add_songs(self, watcher, added, model):
        albums = model.get_albums()
        changed = set()
        new = []
        for song in added:
            if "album" in song:
                for alb in song.list("album"):
                    if alb in albums:
                        changed.add(alb)
                        albums[alb].add(song)
                    else:
                        albums[alb] = self._Album(alb)
                        new.append(albums[alb])
                        albums[alb].add(song)
            else:
                if "" not in albums:
                    albums[""] = self._Album("")
                    new.append(albums[""])
                changed.add("")
                albums[""].add(song)
        for album in new:
            album.finalize()
            album._model = model
            album._iter = model.append(row=[album])
        self.__update(changed, model)

    def __get_selected_songs(self, selection):
        model, rows = selection.get_selected_rows()
        if not model or not rows: return set([])
        albums = [model[row][0] for row in rows]
        if None in albums: return library.values()
        else: return list(
            reduce(set.union, [album.songs for album in albums], set()))

    def __properties(self, activator, view):
        songs = self.__get_selected_songs(view.get_selection())
        if songs:
            songs.sort()
            SongProperties(songs, widgets.watcher, initial=0)

    def __button_press(self, view, event, menu):
        x, y = map(int, [event.x, event.y])
        try: path, col, cellx, celly = view.get_path_at_pos(x, y)
        except TypeError: return True
        if event.button == 3:
            sens = bool(view.get_model()[path][0])
            for c in menu.get_children(): c.set_sensitive(sens)
            view.grab_focus()
            selection = view.get_selection()
            if not selection.path_is_selected(path):
                view.set_cursor(path, col, 0)
            menu.popup(None, None, None, event.button, event.time)
            return True

    def __play_selection(self, view, indices, col):
        player.playlist.next()
        player.playlist.reset()

    def filter(self, key, values):
        assert(key == "album")
        if not values: values = [""]
        view = self.get_children()[1].child
        selection = view.get_selection()
        selection.unselect_all()
        model = view.get_model()
        first = None
        for i, row in enumerate(iter(model)):
            if row[0] and row[0].title in values:
                selection.select_path(i)
                first = first or i
        if first:
            view.scroll_to_cell(first, use_align=True, row_align=0.5)

    def activate(self):
        self.get_children()[1].child.get_selection().emit('changed')

    def can_filter(self, key):
        return (key == "album")

    def restore(self):
        albums = config.get("browsers", "albums").split("\n")
        selection = self.get_children()[1].child.get_selection()
        # FIXME: If albums is "" then it could be either all albums or
        # no albums. If it's "" and some other stuff, assume no albums,
        # otherwise all albums.
        selection.unselect_all()
        if albums == [""]:  selection.select_path((0,))
        else:
            model = selection.get_tree_view().get_model()
            first = None
            for i, row in enumerate(iter(model)):
                if row[0] and row[0].title in albums:
                    selection.select_path(i)
                    first = first or i

            if first: selection.get_tree_view().scroll_to_cell(
                first, use_align=True, row_align=0.5)

    def scroll(self):
        view = self.get_children()[1].child
        model = view.get_model()
        values = widgets.watcher.song.list("album")
        for i, row in enumerate(iter(model)):
            if row[0] and row[0].title in values:
                view.scroll_to_cell(i, use_align=True, row_align=0.5)
                break

    def __selection_changed(self, selection, sort):
        if sort.inhibit: return
        songs = self.__get_selected_songs(selection)
        albums = self.__get_selected_albums(selection)
        if not songs: return
        self.emit('songs-selected', songs, None)
        if self.__save:
            if albums is None: config.set("browsers", "albums", "")
            else:
                confval = "\n".join([a.title for a in albums])
                # Since ConfigParser strips a trailing \n...
                if confval and confval[-1] == "\n":
                    confval = "\n" + confval[:-1]
                config.set("browsers", "albums", confval)

    def __refresh(self, watcher, view, model, clear_cache=False):
        # Prevent refiltering while the view is being refreshed.
        view.freeze_child_notify()
        selected = self.__get_selected_albums(view.get_selection())
        if selected is not None: selected = [a.title for a in selected]

        if clear_cache: self._Album.clear_cache()
        for row in iter(model):
            if row[0]: row[0]._iter = row[0]._model = None
        model.clear()
        albums = {}
        songs = library.itervalues()
        for song in songs:
            if "album" not in song:
                if "" not in albums: albums[""] = self._Album("")
                albums[""].add(song)
            else:
                for album in song.list('album'):
                    if album not in albums:
                        albums[album] = self._Album(album)
                    albums[album].add(song)

        model.append(row=[None])
        for album in albums.values():
            album.finalize()
            album._iter = model.append(row=[album])
            album._model = model

        view.thaw_child_notify()
        if selected: self.filter("album", selected)

gobject.type_register(AlbumList)

class PanedBrowser(gtk.VBox, Browser):
    __gsignals__ = Browser.__gsignals__
    expand = qltk.RVPaned

    class Pane(qltk.HintedTreeView):
        __render = gtk.CellRendererText()
        __render.set_property('ellipsize', pango.ELLIPSIZE_END)

        def __init__(self, mytag, next):
            qltk.HintedTreeView.__init__(self)
            if "~" in mytag[1:]: self.tags = filter(None, mytag.split("~"))
            else: self.tags = [mytag]
            self.__next = next
            model = gtk.ListStore(str, object)

            column = gtk.TreeViewColumn(tag(mytag), self.__render, markup=0)
            column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
            column.set_fixed_width(50)
            self.append_column(column)
            self.set_model(model)

            selection = self.get_selection()
            selection.set_mode(gtk.SELECTION_MULTIPLE)
            self.__sig = selection.connect('changed', self.__changed)

            s = widgets.watcher.connect('removed', self.__removed)
            self.connect_object('destroy', widgets.watcher.disconnect, s)

            self.connect_object('destroy', self.__destroy, model)

        def __destroy(self, model):
            self.set_model(None)
            model.clear()

        def __changed(self, selection, jump=False):
            model, rows = selection.get_selected_rows()
            if jump and rows:
                self.scroll_to_cell(rows[0][0], use_align=True, row_align=0.5)
            self.__next.fill(self.get_songs())

        def __removed(self, watcher, songs):
            model = self.get_model()
            to_remove = []
            def update(model, path, iter):
                data = model[iter][1]
                for song in songs:
                    if song in data: data.remove(song)
                if not model[iter][1]: to_remove.append(iter)
            model.foreach(update)
            map(model.remove, to_remove)

        def inhibit(self): self.get_selection().handler_block(self.__sig)
        def uninhibit(self): self.get_selection().handler_unblock(self.__sig)

        def fill(self, songs, inhibit=False):
            selected = self.get_selected()
            self.inhibit()
            values = {}
            unknown = set()
            for song in songs:
                songvals = song.listall(self.tags)
                if songvals:
                    for val in songvals:
                        values.setdefault(val, set()).add(song)
                else: unknown.add(song)
            keys = values.keys()
            keys.sort()

            model = self.get_model()
            model.clear()
            if len(keys) + bool(unknown) > 1:
                model.append(row=["<b>%s</b>" % _("All"), songs])
            for k in keys: model.append(row=[util.escape(k), values[k]])
            if unknown:
                model.append(row=["<b>%s</b>" % _("Unknown"), unknown])

            self.uninhibit()
            if selected: self.set_selected(selected, jump=True)
            else: self.set_selected(None, jump=True)

        def scroll(self, song):
            values = map(util.escape, song.listall(self.tags))
            for i, row in enumerate(iter(self.get_model())):
                if row[0] in values:
                    self.scroll_to_cell(i, use_align=True, row_align=0.5)
                    break

        def get_selected(self):
            model, rows = self.get_selection().get_selected_rows()
            return [model[row][0] for row in rows]

        def set_selected(self, values, jump=False):
            model = self.get_model()
            selection = self.get_selection()
            if values == self.get_selected(): return
            elif values is None and selection.path_is_selected((0,)): return

            self.inhibit()
            selection.unselect_all()
            first = 0
            if values is None: selection.select_path((0,))
            else:
                for i, row in enumerate(iter(model)):
                    if row[0] in values:
                        selection.select_path((i,))
                        first = first or i
            if first == 0: selection.select_path((0,))
            if jump and len(model): self.scroll_to_cell(first)
            self.uninhibit()
            self.get_selection().emit('changed')

        def get_songs(self):
            model, rows = self.get_selection().get_selected_rows()
            # No reason to look further if "All" is selected.
            if rows and rows[0][0] == 0: return model[(0,)][1]
            else:
                songs = [model[row][1] for row in rows]
                return list(reduce(set.union, songs, set()))

    __save = False
    __play = False
    def __init__(self, save=True, play=True):
        gtk.VBox.__init__(self, spacing=0)
        self.__play = play

        hb = gtk.HBox(spacing=3)
        label = gtk.Label(_("_Search:"))
        label.set_padding(3, 0)
        search = qltk.ValidatingEntry(parser.is_valid_color)
        label.set_mnemonic_widget(search)
        label.set_use_underline(True)
        hb.pack_start(label, expand=False)
        hb.pack_start(search)
        self.pack_start(hb, expand=False)
        self.__refill_id = None
        self.__filter = None
        search.connect('changed', self.__filter_changed)

        self.refresh_panes(restore=False)
        self.__save = save
        self.show_all()

    def __filter_changed(self, entry):
        if self.__refill_id is not None:
            gobject.source_remove(self.__refill_id)
            self.__refill_id = None
        text = entry.get_text().decode('utf-8')
        if parser.is_parsable(text):
            if text: self.__filter = parser.parse(text).search
            else: self.__filter = None
            self.__refill_id = gobject.timeout_add(500, self.activate)

    def activate(self):
        self.__panes[0].fill(filter(self.__filter, library.values()))

    def scroll(self):
        for pane in self.__panes:
            pane.scroll(widgets.watcher.song)

    def refresh_panes(self, restore=True):
        try: hbox = self.get_children()[1]
        except IndexError: pass # first call
        else: hbox.destroy()

        hbox = gtk.HBox(spacing=3)
        hbox.set_homogeneous(True)
        hbox.set_size_request(100, 100)
        # fill in the pane list. the last pane reports back to us.
        self.__panes = [self]
        panes = config.get("browsers", "panes").split(); panes.reverse()
        for pane in panes:
            self.__panes.insert(0, self.Pane(pane, self.__panes[0]))
        self.__panes.pop() # remove self

        for pane in self.__panes:
            if self.__play: pane.connect('row-activated', self.__start)
            sw = gtk.ScrolledWindow()
            sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
            sw.set_shadow_type(gtk.SHADOW_IN)
            sw.add(pane)
            hbox.pack_start(sw)

        self.pack_start(hbox)
        if restore: self.restore()
        else:
            self.__panes[-1].inhibit()
            self.activate()
            self.__panes[-1].uninhibit()
        self.show_all()

    def __start(self, view, indices, col):
        player.playlist.next()
        player.playlist.reset()

    def can_filter(self, key):
        for pane in self.__panes:
            if key in pane.tags: return True
        else: return False

    def filter(self, key, values):
        thepane = None
        self.__panes[-1].inhibit()
        for pane in self.__panes:
            if key in pane.tags:
                pane.set_selected(map(util.escape, values), True)
            else: pane.set_selected(None, True)
        self.__panes[-1].uninhibit()
        self.__panes[-1].get_selection().emit('changed')

    def save(self):
        selected = []
        for pane in self.__panes:
            selected.append("\t".join(pane.get_selected()))
        config.set("browsers", "pane_selection", "\n".join(selected))

    def restore(self):
        selected = config.get("browsers", "pane_selection").split("\n")
        if len(selected) == len(self.__panes):
            self.__panes[-1].inhibit()
            for values, pane in zip(selected, self.__panes[:-1]):
                pane.set_selected(values.split("\t"), True)
            self.__panes[-1].uninhibit()
            self.__panes[-1].set_selected(selected[-1].split("\t"), True)

    def __refresh(self, watcher):
        self.activate()

    def fill(self, songs):
        if self.__save: self.save()
        self.emit('songs-selected', list(songs), None)

gobject.type_register(PanedBrowser)

class PlaylistBar(Browser, gtk.HBox):
    __gsignals__ = Browser.__gsignals__
    background = False

    def __init__(self):
        gtk.HBox.__init__(self)
        Browser.__init__(self)
        combo = gtk.ComboBox(PlayList.lists_model())
        cell = gtk.CellRendererText()
        combo.pack_start(cell, True)
        combo.add_attribute(cell, 'text', 0)
        self.pack_start(combo)

        edit = gtk.Button()
        refresh = gtk.Button()
        edit.add(gtk.image_new_from_stock(gtk.STOCK_EDIT, gtk.ICON_SIZE_MENU))
        refresh.add(gtk.image_new_from_stock(gtk.STOCK_REFRESH,
                                             gtk.ICON_SIZE_MENU))
        edit.set_sensitive(False)
        refresh.set_sensitive(False)
        self.pack_start(edit, expand=False)
        self.pack_start(refresh, expand=False)
        edit.connect('clicked', self.__edit_current, combo)
        combo.connect('changed', self.__list_selected, edit, refresh)
        refresh.connect_object(
            'clicked', self.__list_selected, combo, edit, refresh)

        tips = gtk.Tooltips()
        tips.set_tip(edit, _("Edit the current playlist"))
        tips.set_tip(refresh, _("Refresh the current playlist"))
        self.connect_object('destroy', combo.set_model, None)
        self.connect_object('destroy', gtk.Tooltips.destroy, tips)
        tips.enable()
        self.show_all()

    def save(self):
        combo = self.get_children()[1]
        active = combo.get_active()
        key = combo.get_model()[active][1]
        config.set("browsers", "playlist", key)

    def restore(self):
        try: key = config.get("browsers", "playlist")
        except Exception: self.get_children()[1].set_active(0)
        else:
            combo = self.get_children()[1]
            model = combo.get_model()
            def find_key(model, path, iter, key):
                if model[iter][1] == key:
                    combo.set_active(path[0])
                    return True
            model.foreach(find_key, key)

    def activate(self):
        self.__list_selected(*self.get_children())

    def __list_selected(self, combo, edit, refresh):
        active = combo.get_active()
        edit.set_sensitive(active > 0)
        refresh.set_sensitive(active > 0)
        if active == -1: return # Unset
        self.save()
        if active == 0:
            self.emit('songs-selected', library.values(), None)
        else:
            key = "~#playlist_" + combo.get_model()[active][1]
            songs = filter(lambda s: key in s, library.itervalues())
            self.emit('songs-selected', songs, key)

    def __edit_current(self, edit, combo):
        active = combo.get_active()
        if active > 0: PlaylistWindow(combo.get_model()[active][0])

gobject.type_register(PlaylistBar)

class CoverImage(gtk.Frame):
    def __init__(self, size=None):
        gtk.Frame.__init__(self)
        self.add(gtk.EventBox())
        self.child.add(gtk.Image())
        self.__size = size or [120, 100]
        self.child.child.set_size_request(-1, self.__size[1])
        self.child.connect_object(
            'button-press-event', CoverImage.__show_cover, self)
        self.child.show_all()
        self.__albumfn = None

    def set_song(self, activator, song):
        self.__song = song
        if song is None:
            self.child.child.set_from_pixbuf(None)
            self.__albumfn = None
            self.hide()
        else:
            cover = song.find_cover()
            if cover is None:
                self.__albumfn = None
                self.child.child.set_from_pixbuf(None)
                self.hide()
            elif cover.name != self.__albumfn:
                try:
                    pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(
                        cover.name, *self.__size)
                except gobject.GError:
                    self.hide()
                else:
                    self.child.child.set_from_pixbuf(pixbuf)
                    self.__albumfn = cover.name
                    self.show()

    def show(self):
        if config.state("cover") and self.__albumfn:
            gtk.Frame.show(self)

    def __show_cover(self, event):
        if (self.__song and event.button == 1 and
            event.type == gtk.gdk._2BUTTON_PRESS):
            cover = self.__song.find_cover()
            BigCenteredImage(self.__song.comma("album"), cover.name)

class MainWindow(gtk.Window):
    class StopAfterMenu(gtk.Menu):
        def __init__(self):
            gtk.Menu.__init__(self)
            self.__item = gtk.CheckMenuItem(_("Stop after this song"))
            self.__item.set_active(False)
            self.append(self.__item)
            self.__item.show()

        def __get_active(self): return self.__item.get_active()
        def __set_active(self, v): return self.__item.set_active(v)
        active = property(__get_active, __set_active)

    class SongInfo(gtk.Label):
        def __init__(self):
            gtk.Label.__init__(self)
            self.set_ellipsize(pango.ELLIPSIZE_END)
            self.set_alignment(0.0, 0.0)
            self.set_direction(gtk.TEXT_DIR_LTR)
            widgets.watcher.connect('song-started', self.__song_started)
            widgets.watcher.connect('changed', self.__check_change)

        def __check_change(self, watcher, songs):
            if watcher.song in songs:
                self.__song_started(watcher, watcher.song)

        def __song_started(self, watcher, song):
            if song:
                t = self.__title(song)+self.__people(song)+self.__album(song)
            else: t = "<span size='xx-large'>%s</span>" % _("Not playing")
            self.set_markup(t)

        def __title(self, song):
            t = "<span weight='bold' size='large'>%s</span>" %(
                util.escape(song.comma("title")))
            if "version" in song:
                t += "\n<small><b>%s</b></small>" %(
                    util.escape(song.comma("version")))
            return t

        def __people(self, song):
            t = ""
            if "artist" in song:
                t += "\n" + _("by %s") % util.escape(song.comma("artist"))
            if "performer" in song:
                t += "\n<small>%s</small>" % util.escape(
                    _("Performed by %s") % song.comma("performer"))

            others = []
            for key, name in [
                ("arranger", _("arranged by %s")),
                ("lyricist", _("lyrics by %s")),
                ("conductor", _("conducted by %s")),
                ("composer", _("composed by %s")),
                ("author", _("written by %s"))]:
                if key in song: others.append(name % song.comma(key))
            if others:
                others = util.capitalize("; ".join(others))
                t += "\n<small>%s</small>" % util.escape(others)
            return t

        def __album(self, song):
            t = []
            if "album" in song:
                t.append("\n<b>%s</b>" % util.escape(song.comma("album")))
                if "discnumber" in song:
                    t.append(_("Disc %s") % util.escape(
                        song.comma("discnumber")))
                if "part" in song:
                    t.append("<b>%s</b>" % util.escape(song.comma("part")))
                if "tracknumber" in song:
                    t.append(_("Track %s") % util.escape(
                        song.comma("tracknumber")))
            return " - ".join(t)

    class PlayControls(gtk.Table):
        def __init__(self):
            gtk.Table.__init__(self, 2, 3)
            self.set_homogeneous(True)
            self.set_row_spacings(3)
            self.set_col_spacings(3)
            self.set_border_width(3)

            prev = gtk.Button()
            prev.add(gtk.image_new_from_stock(
                gtk.STOCK_MEDIA_PREVIOUS, gtk.ICON_SIZE_LARGE_TOOLBAR))
            prev.connect('clicked', self.__previous)
            self.attach(prev, 0, 1, 0, 1, xoptions=gtk.FILL, yoptions=gtk.FILL)

            play = gtk.Button()
            play.add(gtk.image_new_from_stock(
                gtk.STOCK_MEDIA_PLAY, gtk.ICON_SIZE_LARGE_TOOLBAR))
            play.connect('clicked', self.__playpause)
            self.attach(play, 1, 2, 0, 1, xoptions=gtk.FILL, yoptions=gtk.FILL)

            next = gtk.Button()
            next.add(gtk.image_new_from_stock(
                gtk.STOCK_MEDIA_NEXT, gtk.ICON_SIZE_LARGE_TOOLBAR))
            next.connect('clicked', self.__next)
            self.attach(next, 2, 3, 0, 1, xoptions=gtk.FILL, yoptions=gtk.FILL)

            tips = gtk.Tooltips()

            add = gtk.Button()
            add.add(gtk.image_new_from_stock(
                gtk.STOCK_ADD, gtk.ICON_SIZE_LARGE_TOOLBAR))
            add.connect('clicked', self.__add_music)
            self.attach(add, 0, 1, 1, 2, xoptions=gtk.FILL, yoptions=gtk.FILL)
            tips.set_tip(add, _("Add songs to your library"))

            prop = gtk.Button()
            prop.add(gtk.image_new_from_stock(
                gtk.STOCK_PROPERTIES, gtk.ICON_SIZE_LARGE_TOOLBAR))
            prop.connect('clicked', self.__properties)
            self.attach(prop, 1, 2, 1, 2, xoptions=gtk.FILL, yoptions=gtk.FILL)
            tips.set_tip(prop, _("View and edit tags in the playing song"))

            info = gtk.Button()
            info.add(gtk.image_new_from_stock(
                gtk.STOCK_DIALOG_INFO, gtk.ICON_SIZE_LARGE_TOOLBAR))
            info.connect('clicked', self.__website)
            self.attach(info, 2, 3, 1, 2, xoptions=gtk.FILL, yoptions=gtk.FILL)
            tips.set_tip(info, _("Visit the artist's website"))

            stopafter = MainWindow.StopAfterMenu()

            widgets.watcher.connect(
                'song-started', self.__song_started, stopafter,
                next, prop, info)
            widgets.watcher.connect(
                'song-ended', self.__song_ended, stopafter)
            widgets.watcher.connect(
                'paused', self.__paused, stopafter, play.child,
                gtk.STOCK_MEDIA_PLAY),
            widgets.watcher.connect(
                'unpaused', self.__paused, stopafter, play.child,
                gtk.STOCK_MEDIA_PAUSE),

            play.connect(
                'button-press-event', self.__popup_stopafter, stopafter)
            tips.enable()
            self.connect_object('destroy', gtk.Tooltips.destroy, tips)
            self.show_all()

        def __popup_stopafter(self, activator, event, stopafter):
            if event.button == 3:
                stopafter.popup(None, None, None, event.button, event.time)

        def __song_started(self, watcher, song, stopafter, *buttons):
            if song and stopafter.active:
                player.playlist.paused = True
            for b in buttons: b.set_sensitive(bool(song))

        def __paused(self, watcher, stopafter, image, stock):
            stopafter.active = False
            image.set_from_stock(stock, gtk.ICON_SIZE_LARGE_TOOLBAR)

        def __song_ended(self, watcher, song, stopped, stopafter):
            if stopped: stopafter.active = False

        def __playpause(self, button):
            if widgets.watcher.song is None: player.playlist.reset()
            else: player.playlist.paused ^= True

        def __previous(self, button): player.playlist.previous()
        def __next(self, button): player.playlist.next()

        def __add_music(self, button):
            widgets.main.open_chooser(button)

        def __properties(self, button):
            if widgets.watcher.song:
                SongProperties([widgets.watcher.song], widgets.watcher)

        def __website(self, button):
            song = widgets.watcher.song
            if not song: return
            website_wrap(button, song.website())

    class PositionSlider(gtk.HBox):
        __gsignals__ = {
            'seek': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (int,))
            }
                    
        def __init__(self):
            gtk.HBox.__init__(self)
            l = gtk.Label("0:00/0:00")
            l.set_padding(3, 0)
            # Without this, the text is clipped off the side. Since the
            # format string is reversible, this is not a problem.
            l.set_direction(gtk.TEXT_DIR_LTR)
            self.pack_start(l, expand=False)
            scale = gtk.HScale(gtk.Adjustment(0, 0, 0, 3600, 15000, 0))
            scale.set_update_policy(gtk.UPDATE_DELAYED)
            scale.connect_object('adjust-bounds', self.emit, 'seek')
            scale.set_draw_value(False)
            self.pack_start(scale)

            widgets.watcher.connect(
                'song-started', self.__song_changed, scale, l)

            gobject.timeout_add(
                500, self.__update_time, widgets.watcher, scale, l)

        def __song_changed(self, watcher, song, position, label):
            if song:
                length = song["~#length"]
                position.set_range(0, length * 1000)
            else: position.set_range(0, 1)

        def __update_time(self, watcher, position, timer):
            cur, end = watcher.time
            position.set_value(cur)
            cur = "%d:%02d" % (cur // 60000, (cur % 60000) // 1000)
            end = "%d:%02d" % (end // 60000, (end % 60000) // 1000)
            timer.set_text(
                _("%(current)s/%(total)s") % dict(current=cur, total=end))
            return True

    gobject.type_register(PositionSlider)

    class VolumeSlider(gtk.VBox):
        def __init__(self, device):
            gtk.VBox.__init__(self)
            i = gtk.Image()
            i.set_from_pixbuf(gtk.gdk.pixbuf_new_from_file("volume.png"))
            self.pack_start(i, expand=False)
            slider = gtk.VScale(gtk.Adjustment(1, 0, 1, 0.01, 0.1))
            slider.set_update_policy(gtk.UPDATE_CONTINUOUS)
            slider.connect('value-changed', self.__volume_changed, device)
            self.pack_start(slider)
            tips = gtk.Tooltips()
            tips.set_tip(slider, _("Change volume"))
            tips.enable()
            self.connect_object('destroy', gtk.Tooltips.destroy, tips)
            self.get_value = slider.get_value
            self.set_value = slider.set_value
            slider.set_inverted(True)
            slider.set_draw_value(False)
            self.set_value(config.getfloat("memory", "volume"))
            self.show_all()

        def __volume_changed(self, slider, device):
            val = (2 ** slider.get_value()) - 1
            device.volume = val
            config.set("memory", "volume", str(slider.get_value()))

    def __init__(self):
        gtk.Window.__init__(self)
        self.last_dir = os.path.expanduser("~")

        tips = gtk.Tooltips()
        self.set_title("Quod Libet")

        icon_theme = gtk.icon_theme_get_default()
        p = gtk.gdk.pixbuf_new_from_file("quodlibet.png")
        gtk.icon_theme_add_builtin_icon(const.ICON, 64, p)
        self.set_icon(icon_theme.load_icon(
            const.ICON, 64, gtk.ICON_LOOKUP_USE_BUILTIN))

        self.set_default_size(
            *map(int, config.get('memory', 'size').split()))
        self.add(gtk.VBox())

        # create main menubar, load/restore accelerator groups
        self._create_menu(tips)
        self.add_accel_group(self.ui.get_accel_group())
        gtk.accel_map_load(const.ACCELS)
        accelgroup = gtk.accel_groups_from_object(self)[0]
        accelgroup.connect('accel-changed',
                lambda *args: gtk.accel_map_save(const.ACCELS))
        self.child.pack_start(self.ui.get_widget("/Menu"), expand=False)

        # song info (top part of window)
        hbox = gtk.HBox()
        hbox.set_size_request(-1, 102)

        vbox = gtk.VBox()

        hb2 = gtk.HBox()

        # play controls
        t = self.PlayControls()
        hb2.pack_start(t, expand=False, fill=False)

        # song text
        text = self.SongInfo()
        # Packing the text directly into the hbox causes clipping problems
        # with Hebrew, so use an Alignment instead.
        alignment = gtk.Alignment(xalign=0, yalign=0, xscale=1, yscale=1)
        alignment.set_padding(3, 3, 3, 3)
        alignment.add(text)
        hb2.pack_start(alignment)

        vbox.pack_start(hb2, expand=True)
        hbox.pack_start(vbox, expand=True)

        # position slider
        scale = self.PositionSlider()
        scale.connect('seek', lambda s, pos: player.playlist.seek(pos))
        vbox.pack_start(scale, expand=False)

        # cover image
        self.image = CoverImage()
        widgets.watcher.connect('song-started', self.image.set_song)
        hbox.pack_start(self.image, expand=False)

        # volume control
        self.volume = self.VolumeSlider(player.device)
        hbox.pack_start(self.volume, expand=False)

        self.child.pack_start(hbox, expand=False)

        # status area
        hbox = gtk.HBox(spacing=6)
        self.shuffle = shuffle = gtk.combo_box_new_text()
        self.shuffle.append_text(_("In Order"))
        self.shuffle.append_text(_("Shuffle"))
        self.shuffle.append_text(_("Weighted"))
        tips.set_tip(shuffle, _("Play songs in random order"))
        shuffle.connect('changed', self.__shuffle)
        try: shf = config.getint('memory', 'shuffle')
        except: shf = int(config.getboolean('memory', 'shuffle'))
        shuffle.set_active(shf)
        hbox.pack_start(shuffle, expand=False)
        self.repeat = repeat = gtk.CheckButton(_("_Repeat"))
        repeat.connect('toggled', self.toggle_repeat)
        repeat.set_active(config.getboolean('settings', 'repeat'))
        tips.set_tip(
            repeat, _("Restart the playlist when finished"))
        hbox.pack_start(repeat, expand=False)
        self.__statusbar = gtk.Label()
        self.__statusbar.set_text(_("No time information"))
        self.__statusbar.set_alignment(1.0, 0.5)
        self.__statusbar.set_ellipsize(pango.ELLIPSIZE_START)
        hbox.pack_start(self.__statusbar)
        hbox.set_border_width(3)
        self.child.pack_end(hbox, expand=False)

        # Set up the tray icon. It gets created even if we don't
        # actually use it (e.g. missing trayicon.so).
        self.icon = QLTrayIcon(self, self.volume)

        # song list
        self.song_scroller = sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        sw.set_shadow_type(gtk.SHADOW_IN)
        self.songlist = MainSongList()
        self.songlist.set_rules_hint(True)
        sw.add(self.songlist)
        self.songlist.set_model(gtk.ListStore(object))
        SongList.set_all_column_headers(
            config.get("settings", "headers").split())
        sort = config.get('memory', 'sortby')
        self.songlist.set_sort_by(None, sort[1:], order=int(sort[0]))

        self.inter = gtk.VBox()

        self.browser = None

        self.open_fifo()
        self.__keys = MmKeys({"mm_prev": self.__previous_song,
                              "mm_next": self.__next_song,
                              "mm_playpause": self.__play_pause})

        self.child.show_all()
        sw.show_all()
        self.__select_browser(self, config.getint("memory", "browser"))
        self.browser.restore()
        self.browser.activate()
        self.showhide_playlist(self.ui.get_widget("/Menu/View/Songlist"))

        self.connect('configure-event', MainWindow.__save_size)
        self.connect('delete-event', MainWindow.__delete_event)
        self.connect_object('destroy', TrayIcon.destroy, self.icon)
        self.connect('destroy', gtk.main_quit)

        self.songlist.connect('row-activated', self.__select_song)
        self.songlist.connect('button-press-event', self.__songs_button_press)
        self.songlist.connect('popup-menu', self.__songs_popup_menu)
        self.songlist.connect('columns-changed', self.__cols_changed)
        self.songlist.get_selection().connect('changed', self.__set_time)

        widgets.watcher.connect('removed', self.__set_time)
        widgets.watcher.connect('refresh', self.__refresh)
        widgets.watcher.connect('changed', self.__update_title)
        widgets.watcher.connect('song-started', self.__song_started)
        widgets.watcher.connect('song-ended', self.__song_ended)
        widgets.watcher.connect(
            'missing', self.__song_missing, self.__statusbar)
        widgets.watcher.connect('paused', self.__update_paused, True)
        widgets.watcher.connect('unpaused', self.__update_paused, False)

        self.resize(*map(int, config.get("memory", "size").split()))
        self.show()

    def __delete_event(self, event):
        if self.icon.enabled and config.getboolean("plugins", "icon_close"):
            self.icon.hide_window()
            return True

    def _create_menu(self, tips):
        ag = gtk.ActionGroup('MainWindowActions')

        actions = [
            ('Music', None, _("_Music")),
            ('AddMusic', gtk.STOCK_ADD, _('_Add Music...'), "<control>O", None,
             self.open_chooser),
            ('NewPlaylist', gtk.STOCK_EDIT, _('_New/Edit Playlist...'),
             None, None, self.__new_playlist),
            ('BrowseLibrary', gtk.STOCK_FIND, _('_Browse Library')),
            ("Preferences", gtk.STOCK_PREFERENCES, None, None, None,
             self.__preferences),
            ("Plugins", gtk.STOCK_EXECUTE, _("_Plugins"), None, None,
             self.__plugins),
            ("Quit", gtk.STOCK_QUIT, None, None, None, gtk.main_quit),
            ('Filters', None, _("_Filters")),

            ("NotPlayedDay", gtk.STOCK_FIND, _("Not played to_day"),
             "", None, self.lastplayed_day),
            ("NotPlayedWeek", gtk.STOCK_FIND, _("Not played in a _week"),
             "", None, self.lastplayed_week),
            ("NotPlayedMonth", gtk.STOCK_FIND, _("Not played in a _month"),
             "", None, self.lastplayed_month),
            ("NotPlayedEver", gtk.STOCK_FIND, _("_Never played"),
             "", None, self.lastplayed_never),
            ("Top", gtk.STOCK_GO_UP, _("_Top 40"), "", None, self.__top40),
            ("Bottom", gtk.STOCK_GO_DOWN,_("B_ottom 40"), "",
             None, self.__bottom40),
            ("Song", None, _("S_ong")),
            ("Properties", gtk.STOCK_PROPERTIES, None, "<Alt>Return", None,
             self.__current_song_prop),
            ("Rating", None, _("Rating")),

            ("Jump", gtk.STOCK_JUMP_TO, _("_Jump to playing song"),
             "<control>J", None, self.__jump_to_current),

            ("View", None, _("_View")),
            ("Help", None, _("_Help")),
            ("About", gtk.STOCK_ABOUT, None, None, None, AboutWindow),
            ]

        if const.SM_PREVIOUS.startswith("gtk-"): label = None
        else: label = const.SM_PREVIOUS
        actions.append(("Previous", gtk.STOCK_MEDIA_PREVIOUS, label,
                        "<control>Left", None, self.__previous_song))

        actions.append(("PlayPause", gtk.STOCK_MEDIA_PLAY, _("_Play"),
                        "<control>space", None, self.__play_pause))

        if const.SM_NEXT.startswith("gtk-"): label = None
        else: label = const.SM_NEXT
        actions.append(("Next", gtk.STOCK_MEDIA_NEXT, label,
                        "<control>Right", None, self.__next_song))

        ag.add_actions(actions)

        act = gtk.Action(
            "RefreshLibrary", _("Re_fresh Library"), None, gtk.STOCK_REFRESH)
        act.connect('activate', self.__rebuild)
        ag.add_action(act)
        act = gtk.Action(
            "ReloadLibrary", _("Re_load Library"), None, gtk.STOCK_REFRESH)
        act.connect('activate', self.__rebuild, True)
        ag.add_action(act)

        for tag_, lab in [
            ("genre", _("Filter on _genre")),
            ("artist", _("Filter on _artist")),
            ("album", _("Filter on al_bum"))]:
            act = gtk.Action(
                "Filter%s" % util.capitalize(tag_), lab, None, gtk.STOCK_INDEX)
            act.connect_object('activate', self.__filter_on, tag_)
            ag.add_action(act)

        for (tag_, accel, label) in [
            ("genre", "G", _("Random _genre")),
            ("artist", "T", _("Random _artist")),
            ("album", "M", _("Random al_bum"))]:
            act = gtk.Action("Random%s" % util.capitalize(tag_), label,
                             None, gtk.STOCK_DIALOG_QUESTION)
            act.connect('activate', self.__random, tag_)
            ag.add_action_with_accel(act, "<control>" + accel)

        ag.add_toggle_actions([
            ("Songlist", None, _("Song _List"), None, None,
             self.showhide_playlist,
             config.getboolean("memory", "songlist"))])

        ag.add_radio_actions([
            ("BrowserDisable", None, _("_Disable Browser"), None, None, 0),
            ("BrowserSearch", None, _("_Search Library"), None, None, 1),
            ("BrowserPlaylist", None, _("_Playlists"), None, None, 2),
            ("BrowserPaned", None, _("_Paned Browser"), None, None, 3),
            ("BrowserAlbum", None, _("_Album List"), None, None, 4),
            ], config.getint("memory", "browser"), self.__select_browser)

        for id, label, Kind in [
            ("BrowseSearch", _("_Search Library"), SearchBar),
            ("BrowsePaned", _("_Paned Browser"), PanedBrowser),
            ("BrowseAlbumList", _("_Album List"), AlbumList)]:
            act = gtk.Action(id, label, None, None)
            act.connect('activate', LibraryBrowser, Kind)
            ag.add_action(act)

        for i in range(5):
            act = gtk.Action(
                "Rate%d" % i, "%d %s" % (i, util.format_rating(i)), None, None)
            act.connect('activate', self.__set_rating, i)
            ag.add_action(act)
        
        self.ui = gtk.UIManager()
        self.ui.insert_action_group(ag, -1)
        self.ui.add_ui_from_string(const.MENU)

        # Cute. So. UIManager lets you attach tooltips, but when they're
        # for menu items, they just get ignored. So here I get to actually
        # attach them.
        tips.set_tip(
            self.ui.get_widget("/Menu/Music/RefreshLibrary"),
            _("Check for changes made to the library"))
        tips.set_tip(
            self.ui.get_widget("/Menu/Music/ReloadLibrary"),
            _("Reload all songs in your library (this can take a long time)"))
        tips.set_tip(
            self.ui.get_widget("/Menu/Filters/Top"),
             _("The 40 songs you've played most (more than 40 may "
               "be chosen if there are ties)"))
        tips.set_tip(
            self.ui.get_widget("/Menu/Filters/Bottom"),
            _("The 40 songs you've played least (more than 40 may "
              "be chosen if there are ties)"))
        tips.set_tip(
            self.ui.get_widget("/Menu/Song/Properties"),
            _("View and edit tags in the playing song"))
        self.connect_object('destroy', gtk.Tooltips.destroy, tips)
        tips.enable()

    def __browser_configure(self, paned, event, browser):
        if paned.get_property('position-set'):
            key = "%s_pos" % browser.__class__.__name__
            config.set("browsers", key, str(paned.get_relative()))

    def __select_browser(self, activator, current):
        if not isinstance(current, int): current = current.get_current_value()
        config.set("memory", "browser", str(current))
        Browser = [EmptyBar, SearchBar, PlaylistBar, PanedBrowser,
                   AlbumList][current]
        if self.browser:
            c = self.child.get_children()[-2]
            c.remove(self.song_scroller)
            c.remove(self.browser)
            c.destroy()
            self.browser.destroy()
        self.browser = Browser()
        self.browser.connect('songs-selected', self.__browser_cb)
        if self.browser.expand:
            c = self.browser.expand()
            c.pack1(self.browser, resize=True)
            c.pack2(self.song_scroller, resize=True)
            try:
                key = "%s_pos" % self.browser.__class__.__name__
                val = config.getfloat("browsers", key)
            except: val = 0.4
            c.connect(
                'notify::position', self.__browser_configure, self.browser)
            def set_size(paned, alloc, pos):
                paned.set_relative(pos)
                paned.disconnect(paned._size_sig)
                # The signal disconnects itself! I hate GTK sizing.
                del(paned._size_sig)
            sig = c.connect('size-allocate', set_size, val)
            c._size_sig = sig
        else:
            c = gtk.VBox()
            c.pack_start(self.browser, expand=False)
            c.pack_start(self.song_scroller)
        self.child.pack_end(c)
        c.show()
        self.__hide_menus()
        self.__refresh_size()

    def open_fifo(self):
        try:
            if not os.path.exists(const.CONTROL):
                util.mkdir(const.DIR)
                os.mkfifo(const.CONTROL, 0600)
            self.fifo = os.open(const.CONTROL, os.O_NONBLOCK)
            gobject.io_add_watch(
                self.fifo, gtk.gdk.INPUT_READ, self.__input_check)
        except EnvironmentError: pass

    def __input_check(self, source, condition):
        c = os.read(source, 1)
        if c == "<": self.__previous_song()
        elif c == ">": self.__next_song()
        elif c == "-": self.__play_pause()
        elif c == ")": player.playlist.paused = False
        elif c == "|": player.playlist.paused = True
        elif c == "0": player.playlist.seek(0)
        elif c == "v":
            c2 = os.read(source, 3)
            if c2 == "+":
                self.volume.set_value(self.volume.get_value() + 0.05)
            elif c2 == "-":
                self.volume.set_value(self.volume.get_value() - 0.05)
            else:
                try: self.volume.set_value(int(c2) / 100.0)
                except ValueError: pass
        elif c == "&":
            c2 = os.read(source, 1)
            if c2 in "012": self.shuffle.set_active(int(c2))
            elif c2 == "t":
                self.shuffle.set_active(
                    int(not bool(self.shuffle.get_active())))
        elif c == "@":
            c2 = os.read(source, 1)
            if c2 == "0": self.repeat.set_active(False)
            elif c2 == "t":
                self.repeat.set_active(not self.repeat.get_active())
            else: self.repeat.set_active(True)
        elif c == "!": self.present()
        elif c == "q": self.__make_query(os.read(source, 4096))
        elif c == "s":
            time = os.read(source, 20)
            seek_to = widgets.watcher.time[0]
            if time[0] == "+": seek_to += util.parse_time(time[1:]) * 1000
            elif time[0] == "-": seek_to -= util.parse_time(time[1:]) * 1000
            else: seek_to = util.parse_time(time) * 1000
            seek_to = min(widgets.watcher.time[1] - 1, max(0, seek_to))
            player.playlist.seek(seek_to)
        elif c == "p":
            filename = os.read(source, 4096)
            if library.add(filename):
                song = library[filename]
                if song not in player.playlist.get_playlist():
                    e_fn = sre.escape(filename)
                    self.__make_query("filename = /^%s/c" % e_fn)
                player.playlist.go_to(library[filename])
                player.playlist.paused = False
            else:
                print to(_("W: Unable to load %s") % filename)
        elif c == "d":
            filename = os.read(source, 4096)
            for added, changed, removed in library.scan([filename]): pass
            widgets.watcher.added(added)
            widgets.watcher.changed(changed)
            widgets.watcher.removed(removed)
            self.__make_query("filename = /^%s/c" % sre.escape(filename))

        os.close(self.fifo)
        self.open_fifo()

    def __update_paused(self, watcher, paused):
        menu = self.ui.get_widget("/Menu/Song/PlayPause")
        if paused:
            menu.get_image().set_from_stock(
                gtk.STOCK_MEDIA_PLAY, gtk.ICON_SIZE_MENU)
            menu.child.set_text(_("_Play"))
        else:
            menu.get_image().set_from_stock(
                gtk.STOCK_MEDIA_PAUSE, gtk.ICON_SIZE_MENU)
            menu.child.set_text(_("_Pause"))
        menu.child.set_use_underline(True)

    def __song_missing(self, watcher, song, statusbar):
        try: library.remove(song)
        except KeyError: pass
        else: watcher.removed([song])
        gobject.idle_add(
            statusbar.set_text, _("Could not play %s.") % song['~filename'])

    def __song_ended(self, watcher, song, stopped):
        if not self.browser.dynamic(song):
            player.playlist.remove(song)
            iter = self.songlist.song_to_iter(song)
            if iter: self.songlist.get_model().remove(iter)
            self.__set_time()

    def __update_title(self, watcher, songs):
        if watcher.song in songs:
            song = watcher.song
            if song:
                self.set_title("Quod Libet - " + song.comma("~title~version"))
            else: self.set_title("Quod Libet")

    def __song_started(self, watcher, song):
        self.__update_title(watcher, [song])

        for wid in ["Jump", "Next", "Properties", "FilterGenre",
                    "FilterArtist", "FilterAlbum", "Rating"]:
            self.ui.get_widget('/Menu/Song/' + wid).set_sensitive(bool(song))
        if song:
            for h in ['genre', 'artist', 'album']:
                self.ui.get_widget(
                    "/Menu/Song/Filter%s" % h.capitalize()).set_sensitive(
                    h in song)
        if song and config.getboolean("settings", "jump"):
            self.__jump_to_current(False)

    def __save_size(self, event):
        config.set("memory", "size", "%d %d" % (event.width, event.height))

    def __new_playlist(self, activator):
        options = map(util.QuerySafe.decode, library.playlists())
        name = GetStringDialog(self, _("New/Edit Playlist"),
                               _("Enter a name for the new playlist. If it "
                                 "already exists it will be opened for "
                                 "editing."), options).run()
        if name:
            PlaylistWindow(name)

    def __refresh_size(self):
        if (not self.browser.expand and
            not self.song_scroller.get_property('visible')):
            width, height = self.get_size()
            self.resize(width, 1)
            self.set_geometry_hints(None, max_height=1, max_width=32000)
        else:
            self.set_geometry_hints(None, max_height=-1, max_width=-1)
        self.realize()

    def showhide_playlist(self, toggle):
        self.song_scroller.set_property('visible', toggle.get_active())
        config.set("memory", "songlist", str(toggle.get_active()))
        self.__refresh_size()

    def __play_pause(self, *args):
        if widgets.watcher.song is None: player.playlist.reset()
        else: player.playlist.paused ^= True

    def __jump_to_current(self, explicit):
        watcher, songlist = widgets.watcher, self.songlist
        iter = songlist.song_to_iter(watcher.song)
        if iter:
            path = songlist.get_model().get_path(iter)
            songlist.scroll_to_cell(path, use_align=True, row_align=0.5)
            if explicit: self.browser.scroll()

    def __next_song(self, *args):
        player.playlist.next()

    def __previous_song(self, *args):
        player.playlist.previous()

    def toggle_repeat(self, button):
        player.playlist.repeat = button.get_active()
        config.set("settings", "repeat", str(bool(button.get_active())))

    def __shuffle(self, button):
        player.playlist.shuffle = button.get_active()
        config.set("memory", "shuffle", str(button.get_active()))

    def __random(self, item, key):
        if self.browser.can_filter(key):
            value = library.random(key)
            if value is not None: self.browser.filter(key, [value])

    def lastplayed_day(self, menuitem):
        self.__make_query("#(lastplayed > today)")
    def lastplayed_week(self, menuitem):
        self.__make_query("#(lastplayed > 7 days ago)")
    def lastplayed_month(self, menuitem):
        self.__make_query("#(lastplayed > 30 days ago)")
    def lastplayed_never(self, menuitem):
        self.__make_query("#(playcount = 0)")

    def __top40(self, menuitem):
        songs = [song["~#playcount"] for song in library.itervalues()]
        if len(songs) == 0: return
        songs.sort()
        if len(songs) < 40:
            self.__make_query("#(playcount > %d)" % (songs[0] - 1))
        else:
            self.__make_query("#(playcount > %d)" % (songs[-40] - 1))

    def __bottom40(self, menuitem):
        songs = [song["~#playcount"] for song in library.itervalues()]
        if len(songs) == 0: return
        songs.sort()
        if len(songs) < 40:
            self.__make_query("#(playcount < %d)" % (songs[0] + 1))
        else:
            self.__make_query("#(playcount < %d)" % (songs[-40] + 1))

    def __rebuild(self, activator, hard=False):
        window = qltk.WaitLoadWindow(self, len(library) // 7,
                                     _("Quod Libet is scanning your library. "
                                       "This may take several minutes.\n\n"
                                       "%d songs reloaded\n%d songs removed"),
                                     (0, 0))
        iter = 7
        c = []
        r = []
        s = False
        for c, r in library.rebuild(hard):
            if iter == 7:
                if window.step(len(c), len(r)):
                    window.destroy()
                    break
                iter = 0
            iter += 1
        else:
            window.destroy()
            if config.get("settings", "scan"):
                s = self.scan_dirs(config.get("settings", "scan").split(":"))
        widgets.watcher.changed(c)
        widgets.watcher.removed(r)
        if c or r or s:
            library.save(const.LIBRARY)
            widgets.watcher.refresh()

    # Set up the preferences window.
    def __preferences(self, activator):
        if not hasattr(widgets, 'preferences'):
            widgets.preferences = PreferencesWindow(self)
        widgets.preferences.present()

    def __plugins(self, activator):
        if not hasattr(widgets, 'plugins'):
            widgets.plugins = PluginWindow(self)
        widgets.plugins.present()

    def __select_song(self, songlist, indices, col):
        model = songlist.get_model()
        iter = model.get_iter(indices)
        song = model.get_value(iter, 0)
        player.playlist.go_to(song)
        player.playlist.paused = False

    def open_chooser(self, *args):
        if not os.path.exists(self.last_dir):
            self.last_dir = os.environ["HOME"]
        chooser = FileChooser(self, _("Add Music"), self.last_dir)
        resp, fns = chooser.run()
        chooser.destroy()
        if resp == gtk.RESPONSE_OK:
            if self.scan_dirs(fns):
                widgets.watcher.refresh()
                library.save(const.LIBRARY)
        if fns:
            self.last_dir = fns[0]

    def scan_dirs(self, fns):
        win = qltk.WaitLoadWindow(self, 0,
                                  _("Quod Libet is scanning for new songs and "
                                    "adding them to your library.\n\n"
                                    "%d songs added"), 0)
        added, changed, removed = [], [], []
        for added, changed, removed in library.scan(fns):
            if win.step(len(added)): break
        widgets.watcher.changed(changed)
        widgets.watcher.added(added)
        widgets.watcher.removed(removed)
        win.destroy()
        return (added or changed or removed)

    def __songs_button_press(self, view, event):
        x, y = map(int, [event.x, event.y])
        try: path, col, cellx, celly = view.get_path_at_pos(x, y)
        except TypeError: return True
        view.grab_focus()
        selection = view.get_selection()
        header = col.header_name
        if event.button == 3:
            if not selection.path_is_selected(path):
                view.set_cursor(path, col, 0)
            self.prep_main_popup(header, event.button, event.time)
            return True

    def __set_rating(self, item, value):
        song = widgets.watcher.song
        if song is not None:
            song["~#rating"] = value
            widgets.watcher.changed([song])

    def __songs_popup_menu(self, songlist):
        path, col = songlist.get_cursor()
        header = col.header_name
        self.prep_main_popup(header, 1, 0)

    def __current_song_prop(self, *args):
        song = widgets.watcher.song
        if song: SongProperties([song], widgets.watcher)

    def prep_main_popup(self, header, button, time):
        menu = self.songlist.Menu(
            header, self.browser.can_filter, self.__filter_on, True)
        menu.show_all()
        menu.connect('selection-done', lambda m: m.destroy())
        menu.popup(None, None, None, button, time)

    def __hide_menus(self):
        menus = {'genre': ["/Menu/Song/FilterGenre",
                           "/Menu/Filters/RandomGenre"],
                 'artist': ["/Menu/Song/FilterArtist",
                           "/Menu/Filters/RandomArtist"],
                 'album':  ["/Menu/Song/FilterAlbum",
                           "/Menu/Filters/RandomAlbum"],
                 None: ["/Menu/Filters/NotPlayedDay",
                        "/Menu/Filters/NotPlayedWeek",
                        "/Menu/Filters/NotPlayedMonth",
                        "/Menu/Filters/NotPlayedEver",
                        "/Menu/Filters/Top",
                        "/Menu/Filters/Bottom"]}
        for key, widgets in menus.items():
            c = self.browser.can_filter(key)
            for widget in widgets:
                self.ui.get_widget(widget).set_property('visible', c)

    def __browser_cb(self, browser, songs, sort):
        if browser.background:
            try: bg = config.get("browsers", "background").decode('utf-8')
            except UnicodeError: bg = ""
            try: songs = filter(parser.parse(bg).search, songs)
            except parser.error: pass

        self.songlist.set_songs(songs, tag=sort)
        self.__set_time()

    def __filter_on(self, header, songs=None):
        if not self.browser or not self.browser.can_filter(header):
            return
        if songs is None:
            if widgets.watcher.song: songs = [widgets.watcher.song]
            else: return

        values = set()
        if header.startswith("~#"):
            values.update([song(header, 0) for song in songs])
        else:
            for song in songs: values.update(song.list(header))
        self.browser.filter(header, list(values))

    def __cols_changed(self, songlist):
        headers = [col.header_name for col in songlist.get_columns()]
        if len(headers) == len(config.get("settings", "headers").split()):
            # Not an addition or removal (handled separately)
            config.set("settings", "headers", " ".join(headers))
            SongList.headers = headers

    def __make_query(self, query):
        if self.browser.can_filter(None):
            self.browser.set_text(query.encode('utf-8'))
            self.browser.activate()

    def __refresh(self, watcher):
        self.browser.activate()
        self.__set_time()

    def __set_time(self, *args):
        statusbar = self.__statusbar
        songs = self.songlist.get_selected_songs()
        if len(songs) <= 1: songs = self.songlist.get_songs()

        i = len(songs)
        length = sum([song["~#length"] for song in songs])
        t = ngettext("%(count)d song (%(time)s)", "%(count)d songs (%(time)s)",
                i) % {'count': i, 'time': util.format_time_long(length)}
        statusbar.set_property('label', t)
        gobject.idle_add(statusbar.queue_resize)

class SongList(qltk.HintedTreeView):
    """Wrap a treeview that works like a songlist"""
    songlistviews = {}
    headers = []

    # Displays the current song indicator
    class CurrentColumn(gtk.TreeViewColumn):
        _render = gtk.CellRendererPixbuf()
        _render.set_property('xalign', 0.5)
        header_name = "~current"

        def _cdf(self, column, cell, model, iter,
                 pixbuf=(gtk.STOCK_MEDIA_PLAY, gtk.STOCK_MEDIA_PAUSE)):
            try:
                if model[iter][0] is not widgets.watcher.song: stock = ''
                else: stock = pixbuf[player.playlist.paused]
                cell.set_property('stock-id', stock)
            except AttributeError: pass

        def __init__(self):
            gtk.TreeViewColumn.__init__(self, "", self._render)
            self.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
            self.set_fixed_width(24)
            self.set_cell_data_func(self._render, self._cdf)
            self.header_name = "~current"

    class TextColumn(gtk.TreeViewColumn):
        _render = gtk.CellRendererText()

        def _cdf(self, column, cell, model, iter, tag):
            try:
                song = model[iter][0]
                cell.set_property('text', song.comma(tag))
            except AttributeError: pass

        def __init__(self, t):
            gtk.TreeViewColumn.__init__(self, tag(t), self._render)
            self.header_name = t
            self.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
            self.set_visible(True)
            self.set_clickable(True)
            self.set_reorderable(True)
            self.set_sort_indicator(False)
            self.set_cell_data_func(self._render, self._cdf, t)

    class WideTextColumn(TextColumn):
        _render = gtk.CellRendererText()
        _render.set_property('ellipsize', pango.ELLIPSIZE_END)

        def __init__(self, tag):
            SongList.TextColumn.__init__(self, tag)
            self.set_expand(True)
            self.set_resizable(True)
            self.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
            self.set_fixed_width(1)

    class NonSynthTextColumn(WideTextColumn):
        def _cdf(self, column, cell, model, iter, tag):
            try:
                song = model[iter][0]
                cell.set_property(
                    'text', song.get(tag, "").replace("\n", ", "))
            except AttributeError: pass

    class FSColumn(WideTextColumn):
        def _cdf(self, column, cell, model, iter, tag, code=util.fscoding()):
            try:
                song = model[iter][0]
                cell.set_property('text', util.unexpand(
                    song.comma(tag).decode(code, 'replace')))
            except AttributeError: pass

    class LengthColumn(TextColumn):
        _render = gtk.CellRendererText()
        _render.set_property('xalign', 1.0)

        def __init__(self, tag="~length"):
            SongList.TextColumn.__init__(self, tag)
            self.set_alignment(1.0)

    class NumericColumn(TextColumn):
        _render = gtk.CellRendererText()
        _render.set_property('xpad', 12)
        _render.set_property('xalign', 1.0)

    def Menu(self, header, can_filter, filter, remove):
        if "~" in header[1:]: header = header.lstrip("~").split("~")[0]
        menu = gtk.Menu()

        if header == "~rating":
            item = gtk.MenuItem(_("Rating"))
            m2 = gtk.Menu()
            item.set_submenu(m2)
            for i in range(5):
                itm = gtk.MenuItem("%d\t%s" %(i, util.format_rating(i)))
                m2.append(itm)
                itm.connect('activate', self.set_selected_ratings, i)
            menu.append(item)
            menu.append(gtk.SeparatorMenuItem())

        songs = self.get_selected_songs()
        if can_filter("artist"):
            b = gtk.ImageMenuItem(_("Filter on _artist"))
            b.connect_object('activate', filter, 'artist', songs)
            b.get_image().set_from_stock(gtk.STOCK_INDEX, gtk.ICON_SIZE_MENU)
            menu.append(b)
        if can_filter("album"):
            b = gtk.ImageMenuItem(_("Filter on al_bum"))
            b.connect_object('activate', filter, 'album', songs)
            b.get_image().set_from_stock(gtk.STOCK_INDEX, gtk.ICON_SIZE_MENU)
            menu.append(b)
        header = {"~rating":"~#rating", "~length":"~#length"}.get(
            header, header)
        if (header not in ["artist", "album"] and can_filter(header) and
            (header[0] != "~" or header[1] == "#")):
            # Translators: The substituted string is the name of the
            # selected column (a translated tag name).
            b = gtk.ImageMenuItem(_("_Filter on %s") % tag(header, False))
            b.connect_object('activate', filter, header, songs)
            b.get_image().set_from_stock(gtk.STOCK_INDEX, gtk.ICON_SIZE_MENU)
            menu.append(b)
        if menu.get_children(): menu.append(gtk.SeparatorMenuItem())

        submenu = self.pm.create_plugins_menu(songs)
        if submenu is not None:
            b = gtk.ImageMenuItem(_("_Plugins"))
            b.get_image().set_from_stock(gtk.STOCK_EXECUTE, gtk.ICON_SIZE_MENU)
            menu.append(b)
            b.set_submenu(submenu)
            if menu.get_children(): menu.append(gtk.SeparatorMenuItem())

        if remove:
            b = gtk.ImageMenuItem(_('Remove from Library'))
            b_img = gtk.Image()
            b_img.set_from_stock(gtk.STOCK_REMOVE, gtk.ICON_SIZE_MENU)
            b.set_image(b_img)
            b.connect_object('activate', self.remove_songs, songs)

        menu.append(b)
        b = gtk.ImageMenuItem(gtk.STOCK_DELETE)
        b.connect_object('activate', self.delete_songs, songs)
        menu.append(b)
        b = gtk.ImageMenuItem(gtk.STOCK_PROPERTIES)
        b.connect_object('activate', SongProperties, songs, widgets.watcher)
        menu.append(b)

        menu.show_all()
        menu.connect('selection-done', lambda m: m.destroy())
        return menu

    def __init__(self):
        qltk.HintedTreeView.__init__(self)
        self.set_size_request(200, 150)
        self.set_rules_hint(True)
        self.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.songlistviews[self] = None     # register self
        self.set_column_headers(self.headers)
        self.connect_object('destroy', SongList._destroy, self)
        sigs = [widgets.watcher.connect('changed', self.__song_updated),
                widgets.watcher.connect('song-started', self.__redraw_current),
                widgets.watcher.connect('removed', self.__song_removed),
                widgets.watcher.connect('paused', self.__redraw_current),
                widgets.watcher.connect('unpaused', self.__redraw_current)
                ]
        for sig in sigs:
            self.connect_object('destroy', widgets.watcher.disconnect, sig)

        targets = [("text/uri-list", 0, 1)]
        self.drag_source_set(
            gtk.gdk.BUTTON1_MASK|gtk.gdk.CONTROL_MASK, targets,
            gtk.gdk.ACTION_DEFAULT|gtk.gdk.ACTION_COPY)
        self.connect('drag-data-get', self.__drag_data_get)
        self.connect('button-press-event', self.__button_press)
        self.connect('key-press-event', self.__key_press)

    def __button_press(self, view, event):
        if event.button != 1: return
        x, y = map(int, [event.x, event.y])
        try: path, col, cellx, celly = view.get_path_at_pos(x, y)
        except TypeError: return True
        header = col.header_name
        if header == "~rating":
            width = col.get_property('width')
            song = view.get_model()[path][0]
            parts = (width / 4.0)
            if cellx < parts + 1:
                rating = (song["~#rating"] & 1) ^ 1
            elif cellx < 2*parts: rating = 2
            elif cellx < 3*parts: rating = 3
            else: rating = 4
            self.__set_rating(rating, [song])

    def remove_songs(self, songs):
        map(library.remove, songs)
        widgets.watcher.removed(songs)

    def delete_songs(self, songs):
        songs = [(song["~filename"], song) for song in songs]
        removed = []
        d = qltk.DeleteDialog([song[0] for song in songs])
        resp = d.run()
        d.destroy()
        if resp == 1 or resp == gtk.RESPONSE_DELETE_EVENT: return
        else:
            if resp == 0: s = _("Moving %d/%d.")
            elif resp == 2: s = _("Deleting %d/%d.")
            else: return
            w = qltk.WaitLoadWindow(None, len(songs), s, (0, len(songs)))
            trash = os.path.expanduser("~/.Trash")
            for filename, song in songs:
                try:
                    if resp == 0:
                        basename = os.path.basename(filename)
                        shutil.move(filename, os.path.join(trash, basename))
                    else:
                        os.unlink(filename)
                    library.remove(song)
                    removed.append(song)

                except:
                    qltk.ErrorMessage(
                        self, _("Unable to delete file"),
                        _("Deleting <b>%s</b> failed. "
                          "Possibly the target file does not exist, "
                          "or you do not have permission to "
                          "delete it.") % (filename)).run()
                    break
                else:
                    w.step(w.current + 1, w.count)
            w.destroy()
            widgets.watcher.removed(removed)

    def __set_rating(self, value, songs):
        for song in songs: song["~#rating"] = value
        widgets.watcher.changed(songs)

    def set_selected_ratings(self, item, value):
        self.__set_rating(value, self.get_selected_songs())

    def song_properties(self, item):
        SongProperties(self.get_selected_songs(), widgets.watcher)

    def __key_press(self, songlist, event):
        if event.string in ['0', '1', '2', '3', '4']:
            self.__set_rating(int(event.string), self.get_selected_songs())

    def __drag_data_get(self, view, ctx, sel, tid, etime):
        model, paths = self.get_selection().get_selected_rows()
        paths.sort()
        from urllib import pathname2url as tourl
        filenames = ["file:" + tourl(model[path][0].get("~filename", ""))
                     for path in paths]
        sel.set_uris(filenames)

    def __redraw_current(self, watcher, song=None):
        model = self.get_model()
        iter = self.song_to_iter(watcher.song)
        if iter: model[iter][0] = model[iter][0]

    def set_all_column_headers(cls, headers):
        cls.headers = headers
        for listview in cls.songlistviews:
            listview.set_column_headers(headers)
    set_all_column_headers = classmethod(set_all_column_headers)

    def get_sort_by(self):
        for header in self.get_columns():
            if header.get_sort_indicator():
                return (header.header_name,
                        header.get_sort_order() == gtk.SORT_DESCENDING)
        else: return "artist", False

    # Resort based on the header clicked.
    def set_sort_by(self, header, tag=None, order=None, refresh=True):
        s = gtk.SORT_ASCENDING

        if header and tag is None: tag = header.header_name

        for h in self.get_columns():
            if h.header_name == tag:
                if order is None:
                    s = header.get_sort_order()
                    if (not header.get_sort_indicator() or
                        s == gtk.SORT_DESCENDING):
                        s = gtk.SORT_ASCENDING
                    else: s = gtk.SORT_DESCENDING
                else:
                    if order: s = gtk.SORT_ASCENDING
                    else: s = gtk.SORT_DESCENDING
                h.set_sort_indicator(True)
                h.set_sort_order(s)
            else: h.set_sort_indicator(False)
        if refresh: self.set_songs(self.get_songs())

    def get_songs(self):
        return [row[0] for row in self.get_model()]

    def set_songs(self, songs, tag=None):
        model = self.get_model()

        if tag is None: tag, reverse = self.get_sort_by()
        else:
            self.set_sort_by(None, refresh=False)
            reverse = False

        if tag == "~#track": tag = "album"
        elif tag == "~#disc": tag = "album"
        elif tag == "~length": tag = "~#length"
        elif tag == "~album~part": tag = "album"
        if tag != "album":
            if reverse:
                songs.sort(lambda b, a: (cmp(a(tag), b(tag)) or cmp(a, b)))
            else:
                songs.sort(lambda a, b: (cmp(a(tag), b(tag)) or cmp(a, b)))
        else:
            songs.sort()
            if reverse: songs.reverse()

        selected = self.get_selected_songs()
        selected = dict.fromkeys([song['~filename'] for song in selected])

        model.clear()
        for song in songs: model.append([song])

        # reselect what we can
        selection = self.get_selection()
        for i, row in enumerate(iter(model)):
            if row[0]['~filename'] in selected:
                selection.select_path(i)

    def get_selected_songs(self):
        model, rows = self.get_selection().get_selected_rows()
        return [model[row][0] for row in rows]

    def song_to_iter(self, song):
        model = self.get_model()
        it = [None]
        def find(model, path, iter, it):
            if model[iter][0] == song: it.append(iter)
            return bool(it[-1])
        model.foreach(find, it)
        return it[-1]

    def songs_to_iters(self, songs):
        model = self.get_model()
        it = []
        def find(model, path, iter, it):
            if model[iter][0] in songs: it.append(iter)
            return len(it) == len(songs)
        model.foreach(find, it)
        return it

    def __song_updated(self, watcher, songs):
        pi = []
        model = self.get_model()
        def find(model, path, iter):
            if model[iter][0] in songs: pi.append((path, iter))
        # Optimize the common case
        def find_one(model, path, iter):
            if model[iter][0] in songs:
                pi.append((path, iter))
                return True
        if len(songs) == 1: model.foreach(find_one)
        else: model.foreach(find)
        for p, i in pi:
            model.row_changed(p, i)

    def __song_removed(self, watcher, songs):
        map(self.get_model().remove, self.songs_to_iters(songs))

    # Build a new filter around our list model, set the headers to their
    # new values.
    def set_column_headers(self, headers):
        if len(headers) == 0: return
        for c in self.get_columns(): self.remove_column(c)

        self.append_column(self.CurrentColumn())
        if "~current" in headers: headers.remove("~current")

        for i, t in enumerate(headers):
            if t in ["tracknumber", "discnumber", "~rating"]:
                column = self.TextColumn(t)
            elif t.startswith("~#"): column = self.NumericColumn(t)
            elif t in ["~filename", "~basename", "~dirname"]:
                column = self.FSColumn(t)
            elif t == "~length": column = self.LengthColumn()
            elif "~" not in t and t != "title":
                column = self.NonSynthTextColumn(t)
            else: column = self.WideTextColumn(t)
            column.connect('clicked', self.set_sort_by)
            self.append_column(column)

    def _destroy(self):
        del(self.songlistviews[self])
        self.set_model(None)

    def _set_column_settings(self, column):
        column.set_visible(True)
        column.set_clickable(True)
        column.set_reorderable(True)
        column.set_sort_indicator(False)

class LibraryBrowser(gtk.Window):
    def __init__(self, activator, Kind=SearchBar):
        gtk.Window.__init__(self)
        self.set_border_width(12)
        self.set_title(_("Library Browser"))
        icon_theme = gtk.icon_theme_get_default()
        self.set_icon(icon_theme.load_icon(
            const.ICON, 64, gtk.ICON_LOOKUP_USE_BUILTIN))

        view = SongList()
        view.set_model(gtk.ListStore(object))

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.add(view)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        browser = Kind(save=False, play=False)
        browser.connect_object('songs-selected', SongList.set_songs, view)
        if Kind.expand:
            container = Kind.expand()
            container.pack1(browser, resize=True)
            container.pack2(sw, resize=True)
            self.add(container)
        else:
            vbox = gtk.VBox(spacing=6)
            vbox.pack_start(browser, expand=False)
            vbox.pack_start(sw)
            self.add(vbox)
        self.browser = browser

        view.connect('button-press-event', self.__button_press)
        view.connect('popup-menu', self.__menu, 3, 0)
        sid = widgets.watcher.connect_object('refresh', Kind.activate, browser)
        self.connect_object('destroy', widgets.watcher.disconnect, sid)
        self.set_default_size(500, 300)
        sw.show_all()
        self.child.show()
        self.show()

    def __button_press(self, view, event):
        if event.button != 3: return False
        x, y = map(int, [event.x, event.y])
        try: path, col, cellx, celly = view.get_path_at_pos(x, y)
        except TypeError: return True
        view.grab_focus()
        selection = view.get_selection()
        if not selection.path_is_selected(path):
            view.set_cursor(path, col, 0)
        self.__menu(view, event.button, event.time)
        return True

    def __menu(self, view, button, time):
        path, col = view.get_cursor()
        header = col.header_name
        menu = view.Menu(
            header, self.browser.can_filter, self.__filter_on, True)
        menu.show_all()
        menu.connect('selection-done', lambda m: m.destroy())
        menu.popup(None, None, None, button, time)

    def __filter_on(self, header, songs=None):
        if not self.browser or not self.browser.can_filter(header):
            return
        if songs is None:
            if widgets.watcher.song: songs = [widgets.watcher.song]
            else: return

        values = set()
        if header.startswith("~#"):
            values.update([song(header, 0) for song in songs])
        else:
            for song in songs: values.update(song.list(header))
        self.browser.filter(header, list(values))

class PlayList(SongList):
    def lists_model(cls):
        try: return cls._lists_model
        except AttributeError:
            model = cls._lists_model = gtk.ListStore(str, str)
            playlists = [[util.QuerySafe.decode(p), p] for p in
                          library.playlists()]
            playlists.sort()
            model.append([(_("All songs")), ""])
            for p in playlists: model.append(p)
            return model
    lists_model = classmethod(lists_model)

    def __init__(self, name):
        plname = 'playlist_' + util.QuerySafe.encode(name)
        self.__key = key = '~#' + plname
        model = gtk.ListStore(object)
        super(PlayList, self).__init__()

        for song in library.query('#(%s > 0)' % plname, sort=key):
            model.append([song])

        menu = gtk.Menu()
        rem = gtk.ImageMenuItem(gtk.STOCK_REMOVE, gtk.ICON_SIZE_MENU)
        rem.connect('activate', self.__remove_selected_songs, key)
        menu.append(rem)
        prop = gtk.ImageMenuItem(gtk.STOCK_PROPERTIES, gtk.ICON_SIZE_MENU)
        prop.connect('activate', self.song_properties)
        menu.append(prop)
        menu.show_all()
        self.connect_object('destroy', gtk.Menu.destroy, menu)
        self.connect('button-press-event', self.__button_press, menu)
        self.connect_object(
            'popup-menu', gtk.Menu.popup, menu, None, None, None, 2, 0)

        self.set_model(model)
        self.connect('drag-end', self.__refresh_indices)

        targets = [("text/uri-list", 0, 1)]
        self.enable_model_drag_dest(targets, gtk.gdk.ACTION_DEFAULT)
        self.connect('drag-data-received', self.__drag_data_received)

    def __drag_data_received(self, view, ctx, x, y, sel, info, etime):
        model = view.get_model()
        from urllib import splittype as split, url2pathname as topath
        filenames = [topath(split(s)[1]) for s in sel.get_uris()
                     if split(s)[0] == "file"]
        songs = filter(None, [library.get(f) for f in filenames])
        if not songs: return True

        try: path, position = view.get_dest_row_at_pos(x, y)
        except TypeError:
            for song in songs:
                it = self.song_to_iter(song)
                if it: model.remove(it)
                model.append([song])
        else:
            iter = model.get_iter(path)
            song = songs.pop(0)
            it = self.song_to_iter(song)
            if it: model.remove(it)
            if position in (gtk.TREE_VIEW_DROP_BEFORE,
                            gtk.TREE_VIEW_DROP_INTO_OR_BEFORE):
                iter = model.insert_before(iter, [song])
            else:
                iter = model.insert_after(iter, [song])
            for song in songs:
                it = self.song_to_iter(song)
                if it: model.remove(it)
                iter = model.insert_after(iter, [song])
        ctx.finish(True, True, etime)
        self.__refresh_indices()

    def append_songs(self, songs):
        model = self.get_model()
        current_songs = set([row[0]['~filename'] for row in model])
        for song in songs:
            if song['~filename'] not in current_songs:
                model.append([song])
                song[self.__key] = len(model) # 1 based index; 0 means out

    def set_sort_by(*args): pass
    def get_sort_by(self, *args): return self__key, False

    def __remove_selected_songs(self, activator, key):
        model, rows = self.get_selection().get_selected_rows()
        rows.sort()
        rows.reverse()
        for row in rows:
            del(model[row][0][key])
            iter = model.get_iter(row)
            model.remove(iter)
        self.__refresh_indices()

    def __refresh_indices(self, *args):
        for i, row in enumerate(iter(self.get_model())):
            row[0][self.__key] = i + 1    # 1 indexed; 0 is not present

    def __button_press(self, view, event, menu):
        if event.button != 3:
            return False
        x, y = map(int, [event.x, event.y])
        try: path, col, cellx, celly = view.get_path_at_pos(x, y)
        except TypeError: return True
        view.grab_focus()
        selection = view.get_selection()
        if not selection.path_is_selected(path):
            view.set_cursor(path, col, 0)
        menu.popup(None, None, None, event.button, event.time)
        return True

class MainSongList(SongList):

    def __init__(self, *args, **kwargs):
        SongList.__init__(self, *args, **kwargs)
        s = widgets.watcher.connect_object(
            'removed', map, player.playlist.remove)
        self.connect_object('destroy', widgets.watcher.disconnect, s)

    def set_sort_by(self, *args, **kwargs):
        SongList.set_sort_by(self, *args, **kwargs)
        tag, reverse = self.get_sort_by()
        config.set('memory', 'sortby', "%d%s" % (int(not reverse), tag))

    def set_songs(self, *args, **kwargs):
        SongList.set_songs(self, *args, **kwargs)
        player.playlist.set_playlist(self.get_songs())

class GetStringDialog(gtk.Dialog):
    def __init__(self, parent, title, text, options=[]):
        gtk.Dialog.__init__(self, title, parent)
        self.set_border_width(6)
        self.set_has_separator(False)
        self.set_resizable(False)
        self.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                         gtk.STOCK_OPEN, gtk.RESPONSE_OK)
        self.vbox.set_spacing(6)
        self.set_default_response(gtk.RESPONSE_OK)

        box = gtk.VBox(spacing=6)
        lab = gtk.Label(text)
        box.set_border_width(6)
        lab.set_line_wrap(True)
        lab.set_justify(gtk.JUSTIFY_CENTER)
        box.pack_start(lab)

        if options:
            self.__entry = gtk.combo_box_entry_new_text()
            for o in options: self.__entry.append_text(o)
            self.__val = self.__entry.child
            box.pack_start(self.__entry)
        else:
            self.__val = gtk.Entry()
            box.pack_start(self.__val)
        self.vbox.pack_start(box)
        self.child.show_all()

    def run(self):
        self.show()
        self.__val.set_text("")
        self.__val.set_activates_default(True)
        self.__val.grab_focus()
        resp = gtk.Dialog.run(self)
        if resp == gtk.RESPONSE_OK:
            value = self.__val.get_text()
        else: value = None
        self.destroy()
        return value

def website_wrap(activator, link):
    if not util.website(link):
        qltk.ErrorMessage(
            widgets.main, _("Unable to start a web browser"),
            _("A web browser could not be found. Please set "
              "your $BROWSER variable, or make sure "
              "/usr/bin/sensible-browser exists.")).run()

def init():
    # Translators: Only translate this if GTK does so incorrectly.
    # See http://www.sacredchao.net/quodlibet/ticket/85 for more details
    const.SM_NEXT = _('gtk-media-next')
    # Translators: Only translate this if GTK does so incorrectly.
    # See http://www.sacredchao.net/quodlibet/ticket/85 for more details
    const.SM_PREVIOUS = _('gtk-media-previous')

    if config.get("settings", "headers").split() == []:
       config.set("settings", "headers", "title")
    for opt in config.options("header_maps"):
        val = config.get("header_maps", opt)
        util.HEADERS_FILTER[opt] = val

    watcher = widgets.watcher = qltk.SongWatcher()

    # plugin support
    from plugins import PluginManager
    SongList.pm = PluginManager(widgets.watcher, ["./plugins", const.PLUGINS])
    SongList.pm.rescan()

    gtk.about_dialog_set_url_hook(website_wrap)
    widgets.main = MainWindow()
    FSInterface(watcher) # Keeps itself alive in the watcher.
    player.playlist.info = widgets.watcher

    util.mkdir(const.DIR)

    return widgets.main

def save_library(thread):
    player.playlist.quitting()
    thread.join()
    print to(_("Saving song library."))
    try: library.save(const.LIBRARY)
    except EnvironmentError, err:
        err = str(err).decode('utf-8', 'replace')
        qltk.ErrorMessage(None, _("Unable to save library"), err).run()

    try: config.write(const.CONFIG)
    except EnvironmentError, err:
        err = str(err).decode('utf-8', 'replace')
        qltk.ErrorMessage(None, _("Unable to save library"), err).run()

    for fn in [const.PAUSED, const.CURRENT, const.CONTROL]:
        # No big deal if these fail, we'll just get a few inconsistent
        # --status reports. Not worth a dialog.
        try: os.unlink(fn)
        except EnvironmentError: pass

def error_and_quit():
    qltk.ErrorMessage(
        None, _("No audio device found"),
        _("Quod Libet was unable to open your audio device. "
          "Often this means another program is using it, or "
          "your audio drivers are not configured.\n\nQuod Libet "
          "will now exit.")).run()
    gtk.main_quit()
