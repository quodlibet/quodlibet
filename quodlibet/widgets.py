# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, sys
import gc, sre, time, shutil, signal
import gtk, pango
import qltk

import config, const, util, player, parser
from util import to
from library import library

if sys.version_info < (2, 4):
    from sets import Set as set

# Give us a namespace for now.. FIXME: We need to remove this later.
# Or, replace it with nicer wrappers!
class widgets(object): pass

# Make a standard directory-chooser, and return the filenames and response.
class FileChooser(object):
    def __init__(self, parent, title, initial_dir = None):
        self.dialog = gtk.FileChooserDialog(
            title = title,
            parent = parent,
            action = gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
            buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                       gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        if initial_dir:
            self.dialog.set_current_folder(initial_dir)
        self.dialog.set_local_only(True)
        self.dialog.set_select_multiple(True)

    def run(self):
        resp = self.dialog.run()
        fns = self.dialog.get_filenames()
        self.dialog.destroy()
        return resp, fns

# FIXME: replace with a standard About widget when using GTK 2.6.
class AboutWindow(gtk.Window):
    def __init__(self, parent):
        gtk.Window.__init__(self)
        self.set_title(_("About Quod Libet"))
        vbox = gtk.VBox(spacing = 6)
        l = gtk.Label(const.COPYRIGHT)
        s2 = _("Quod Libet is free software licensed under the GNU GPL v2.")
        l2 = gtk.Label("<small>%s</small>" % s2)
        l2.set_line_wrap(True)
        l.set_use_markup(True)
        l2.set_use_markup(True)
        l.set_justify(gtk.JUSTIFY_CENTER)
        l2.set_justify(gtk.JUSTIFY_CENTER)
        vbox.pack_start(l)

        contrib = gtk.Label(const.CREDITS[0])
        contrib.set_justify(gtk.JUSTIFY_CENTER)
        vbox.pack_start(contrib)
        button = qltk.Button(stock = gtk.STOCK_CLOSE, cb = self.destroy)
        vbox.pack_start(l2)
        hbox = gtk.HButtonBox()
        hbox.set_layout(gtk.BUTTONBOX_SPREAD)
        hbox.pack_start(button)
        vbox.pack_start(hbox)
        gtk.timeout_add(4000, self.pick_name, list(const.CREDITS), contrib)
        self.alive = True
        self.add(vbox)
        self.set_property('border-width', 12)
        self.connect('destroy', self.destroy)
        self.set_transient_for(parent)
        self.child.show_all()
        self.show()

    def pick_name(self, credits, contrib):
        credits.append(credits.pop(0))
        contrib.set_text(credits[0])
        return hasattr(widgets, 'about')

    def destroy(self, *args):
        gtk.Window.destroy(self)
        try: del(widgets.about)
        except AttributeError: pass

class PreferencesWindow(gtk.Window):
    class Browser(gtk.VBox):
        def __init__(self, tips):
            gtk.VBox.__init__(self)
            self.title = _("Browser")
            vbox = gtk.VBox(spacing = 12)
            buttons = {}
            table = gtk.Table(3, 3)
            table.set_homogeneous(True)
            checks = config.get("settings", "headers").split()
            for j, l in enumerate(
                [[("~#disc", _("_Disc")),
                  ("album", _("Al_bum")),
                  ("genre", _("_Genre"))],
                 [("~#track", _("_Track")),
                  ("artist", _("A_rtist")),
                  ("~basename",_("_Filename"))],
                 [("title",_("Title")),
                  ("date", _("Dat_e")),
                  ("~length",_("_Length"))]]):
                for i, (k, t) in enumerate(l):
                    buttons[k] = gtk.CheckButton(t)
                    if k in checks:
                        buttons[k].set_active(True)
                        checks.remove(k)
                    
                    table.attach(buttons[k], i, i + 1, j, j + 1)

            vbox.pack_start(table, expand = False)

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
            vbox2.pack_start(tiv)
            vbox2.pack_start(aip)
            vbox.pack_start(vbox2, expand = False)

            hbox = gtk.HBox(spacing = 3)
            l = gtk.Label(_("_Others:"))
            hbox.pack_start(l, expand = False)
            others = gtk.Entry()
            others.set_text(" ".join(checks))
            tips.set_tip(others, _("List other headers you want displayed, "
                                   "separated by spaces"))
            l.set_mnemonic_widget(others)
            l.set_use_underline(True)
            hbox.pack_start(others)
            apply = qltk.Button(stock = gtk.STOCK_APPLY, cb = self.apply,
                                user_data = [buttons, tiv, aip, others])
            hbox.pack_start(apply, expand = False)
            vbox.pack_start(hbox, expand = False)

            frame = qltk.Frame(_("Visible Columns"), border = 12, bold = True,
                               child = vbox)
            self.pack_start(frame, expand = False)

        def apply(self, button, buttons, tiv, aip, others):
            headers = []
            for key in ["~#disc", "~#track", "title", "album", "artist",
                        "date", "genre", "~basename", "~length"]:
                if buttons[key].get_active(): headers.append(key)
            if tiv.get_active():
                try: headers[headers.index("title")] = "~title~version"
                except ValueError: pass
            if aip.get_active():
                try: headers[headers.index("album")] = "~album~part"
                except ValueError: pass

            headers.extend(others.get_text().split())
            config.set("settings", "headers", " ".join(headers))
            widgets.main.set_column_headers(headers)

    class Player(gtk.VBox):
        def __init__(self, tips):
            gtk.VBox.__init__(self, spacing = 12)
            self.set_border_width(12)
            self.title = _("Player")
            vbox = gtk.VBox()
            c = gtk.CheckButton(_("Show _album cover images"))
            c.set_active(config.state("cover"))
            c.connect('toggled', self.toggle_cover)
            vbox.pack_start(c)
            c = gtk.CheckButton(_("Color _search terms"))
            tips.set_tip(
                c, _("Display simple searches in blue, "
                     "advanced ones in green, and invalid ones in red"))
                         
            c.set_active(config.state("color"))
            c.connect('toggled', self.toggle, "color")
            vbox.pack_start(c)
            c = gtk.CheckButton(_("_Jump to current song automatically"))
            tips.set_tip(c, _("When the playing song changes, "
                              "scroll to it in the song list"))
            c.set_active(config.state("jump"))
            c.connect('toggled', self.toggle, "jump")
            vbox.pack_start(c)
            self.pack_start(vbox, expand = False)

            f = qltk.Frame(_("_Volume Normalization"), bold = True)
            cb = gtk.combo_box_new_text()
            cb.append_text(_("No volume adjustment"))
            cb.append_text(_('Per-song ("Radio") volume adjustment'))
            cb.append_text(_('Per-album ("Audiophile") volume adjustment'))
            f.get_label_widget().set_mnemonic_widget(cb)
            f.child.add(cb)
            cb.set_active(config.getint("settings", "gain"))
            cb.connect('changed', self.changed, 'gain')
            self.pack_start(f, expand = False)

            f = qltk.Frame(_("_On-Screen Display"), bold = True)
            cb = gtk.combo_box_new_text()
            cb.append_text(_("No on-screen display"))
            cb.append_text(_('Display OSD on the top'))
            cb.append_text(_('Display OSD on the bottom'))
            cb.set_active(config.getint('settings', 'osd'))
            cb.connect('changed', self.changed, 'osd')
            f.get_label_widget().set_mnemonic_widget(cb)
            vbox = gtk.VBox(spacing = 6)
            f.child.add(vbox)
            f.child.child.pack_start(cb, expand = False)
            hb = gtk.HBox(spacing = 6)
            c1, c2 = config.get("settings", "osdcolors").split()
            color1 = gtk.ColorButton(gtk.gdk.color_parse(c1))
            color2 = gtk.ColorButton(gtk.gdk.color_parse(c2))
            tips.set_tip(color1, _("Select a color for the OSD"))
            tips.set_tip(color2, _("Select a second color for the OSD"))
            color1.connect('color-set', self.color_set, color1, color2)
            color2.connect('color-set', self.color_set, color1, color2)
            font = gtk.FontButton(config.get("settings", "osdfont"))
            font.connect('font-set', self.font_set)
            hb.pack_start(color1, expand = False)
            hb.pack_start(color2, expand = False)
            hb.pack_start(font)
            vbox.pack_start(hb, expand = False)
            self.pack_start(f, expand = False)

        def font_set(self, font):
            config.set("settings", "osdfont", font.get_font_name())

        def color_set(self, color, c1, c2):
            color = c1.get_color()
            ct1 = (color.red // 256, color.green // 256, color.blue // 256)
            color = c2.get_color()
            ct2 = (color.red // 256, color.green // 256, color.blue // 256)
            config.set("settings", "osdcolors",
                       "#%02x%02x%02x #%02x%02x%02x" % (ct1+ct2))

        def toggle(self, c, name):
            config.set("settings", name, str(bool(c.get_active())))

        def changed(self, cb, name):
            config.set("settings", name, str(cb.get_active()))

        def toggle_cover(self, c):
            config.set("settings", "cover", str(bool(c.get_active())))
            if config.state("cover"): widgets.main.enable_cover()
            else: widgets.main.disable_cover()        

    class Library(gtk.VBox):
        def __init__(self, tips):
            gtk.VBox.__init__(self, spacing = 12)
            self.set_border_width(12)
            self.title = _("Library")
            f = qltk.Frame(_("Scan _Directories"), bold = True)
            hb = gtk.HBox(spacing = 6)
            b = qltk.Button(_("_Select..."), gtk.STOCK_OPEN)
            e = gtk.Entry()
            e.set_text(util.fsdecode(config.get("settings", "scan")))
            f.get_label_widget().set_mnemonic_widget(e)
            hb.pack_start(e)
            tips.set_tip(e, _("On start up, any files found in these "
                              "directories will be added to your library"))
            hb.pack_start(b, expand = False)
            b.connect('clicked', self.select, e, const.HOME)
            e.connect('changed', self.changed, 'scan')
            f.child.add(hb)
            self.pack_start(f, expand = False)

            f = qltk.Frame(_("_Masked Directories"), bold = True)
            vb = gtk.VBox(spacing = 6)
            l = gtk.Label(_(
                "If you have songs in directories that will not always be "
                "mounted (for example, a removable device or an NFS shared "
                "drive), list those mount points here. Files in these "
                "directories will not be removed from the library if the "
                "device is not mounted."))
            l.set_line_wrap(True)
            l.set_justify(gtk.JUSTIFY_FILL)
            vb.pack_start(l, expand = False)
            hb = gtk.HBox(spacing = 6)
            b = qltk.Button(_("_Select..."), gtk.STOCK_OPEN)
            e = gtk.Entry()
            e.set_text(util.fsdecode(config.get("settings", "masked")))
            f.get_label_widget().set_mnemonic_widget(e)
            hb.pack_start(e)
            hb.pack_start(b, expand = False)
            vb.pack_start(hb, expand = False)
            if os.path.exists("/media"): dir = "/media"
            elif os.path.exists("/mnt"): dir = "/mnt"
            else: dir = "/"
            b.connect('clicked', self.select, e, dir)
            e.connect('changed', self.changed, 'mask')
            f.child.add(vb)
            self.pack_start(f, expand = False)

            f = qltk.Frame(_("Tag Editing"), bold = True)
            vbox = gtk.VBox(spacing = 6)
            hb = gtk.HBox(spacing = 6)
            e = gtk.Entry()
            # at least in English, this determines the size of the window
            #e.set_size_request(270, -1)
            e.set_text(config.get("settings", "splitters"))
            e.connect('changed', self.changed, 'splitters')
            tips.set_tip(
                e, _('These characters will be used as separators '
                     'when "Split values" is selected in the tag editor'))
            l = gtk.Label(_("Split _on:"))
            l.set_use_underline(True)
            l.set_mnemonic_widget(e)
            hb.pack_start(l, expand = False)
            hb.pack_start(e)
            cb = gtk.CheckButton(_("Show _programmatic comments"))
            cb.set_active(config.state("allcomments"))
            cb.connect('toggled', self.toggle, 'allcomments')
            vbox.pack_start(hb, expand = False)
            vbox.pack_start(cb, expand = False)
            f.child.add(vbox)
            self.pack_start(f)

        def toggle(self, c, name):
            config.set("settings", name, str(bool(c.get_active())))

        def select(self, button, entry, initial):
            chooser = FileChooser(widgets.preferences.window,
                                  _("Select Directories"), initial)
            resp, fns = chooser.run()
            if resp == gtk.RESPONSE_OK:
                entry.set_text(":".join(map(util.fsdecode, fns)))

        def changed(self, entry, name):
            config.set('settings', name,
                       util.fsencode(entry.get_text().decode('utf-8')))

    def __init__(self, parent):
        gtk.Window.__init__(self)
        self.set_title(_("Quod Libet Preferences"))
        self.set_border_width(12)
        self.set_resizable(False)
        self.set_transient_for(parent)
        self.add(gtk.VBox(spacing = 12))
        self.tips = gtk.Tooltips()
        n = qltk.Notebook()
        n.append_page(self.Browser(self.tips))
        n.append_page(self.Player(self.tips))
        n.append_page(self.Library(self.tips))

        self.child.pack_start(n)

        bbox = gtk.HButtonBox()
        bbox.set_layout(gtk.BUTTONBOX_END)
        button = qltk.Button(stock = gtk.STOCK_CLOSE, cb = self.destroy)
        bbox.pack_start(button)
        self.connect('delete-event', self.destroy)
        self.child.pack_start(bbox, expand = False)
        self.child.show_all()

    def destroy(self, activator, event = None):
        gtk.Window.destroy(self)
        del(widgets.preferences)
        self.tips.destroy()
        del(self.tips)
        config.write(const.CONFIG)

class DeleteDialog(gtk.Dialog):
    def __init__(self, parent, files):
        gtk.Dialog.__init__(self, _("Deleting files"), parent)
        self.set_border_width(6)
        self.vbox.set_spacing(6)
        self.action_area.set_border_width(0)
        self.set_resizable(False)
        # This is the GNOME trash can for at least some versions.
        # The FreeDesktop spec is complicated and I'm not sure it's
        # actually used by anything.
        if os.path.isdir(os.path.expanduser("~/.Trash")):
            b = qltk.Button(_("Move to Trash"), image = gtk.STOCK_DELETE)
            self.add_action_widget(b, 0)

        self.add_button(gtk.STOCK_CANCEL, 1)
        self.add_button(gtk.STOCK_DELETE, 2)

        hbox = gtk.HBox()
        hbox.set_border_width(6)
        i = gtk.Image()
        i.set_from_stock(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_DIALOG)
        i.set_padding(12, 0)
        i.set_alignment(0.5, 0.0)
        hbox.pack_start(i, expand = False)
        vbox = gtk.VBox(spacing = 6)
        base = os.path.basename(files[0])
        if len(files) == 1:
            l = _("Permanently delete this file?")
            exp = gtk.Expander("%s" % util.fsdecode(base))
        else:
            l = _("Permanently delete these files?")
            exp = gtk.Expander(_("%s and %d more...") %(
                util.fsdecode(base), len(files) - 1))

        lab = gtk.Label()
        lab.set_markup("<big><b>%s</b></big>" % l)
        lab.set_property('xalign', 0.0)
        vbox.pack_start(lab, expand = False)

        lab = gtk.Label("\n".join(
            map(util.fsdecode, map(util.unexpand, files))))
        lab.set_property('xalign', 0.1)
        lab.set_property('yalign', 0.0)
        exp.add(gtk.ScrolledWindow())
        exp.child.add_with_viewport(lab)
        exp.child.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        exp.child.child.set_shadow_type(gtk.SHADOW_NONE)
        vbox.pack_start(exp)
        hbox.pack_start(vbox)
        self.vbox.pack_start(hbox)
        self.vbox.show_all()

class WaitLoadWindow(gtk.Window):
    def __init__(self, parent, count, text, initial):
        gtk.Window.__init__(self)
        self.sig = parent.connect('configure-event', self.recenter)
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_decorated(False)
        self.set_resizable(False)
        self.add(gtk.Frame())
        self.child.set_shadow_type(gtk.SHADOW_OUT)
        vbox = gtk.VBox(spacing = 12)
        vbox.set_property('border-width', 12)
        self.label = gtk.Label()
        self.label.set_size_request(170, -1)
        self.label.set_use_markup(True)
        self.label.set_line_wrap(True)
        self.label.set_justify(gtk.JUSTIFY_CENTER)
        vbox.pack_start(self.label)
        self.progress = gtk.ProgressBar()
        self.progress.set_pulse_step(0.08)
        vbox.pack_start(self.progress)

        self.current = 0
        self.count = count
        if self.count > 5 or self.count == 0:
            # Display a stop/pause box. count = 0 means an indefinite
            # number of steps.
            hbox = gtk.HBox(spacing = 6, homogeneous = True)
            b1 = qltk.Button(stock = gtk.STOCK_STOP)
            b2 = gtk.ToggleButton()
            b2.add(gtk.HBox(spacing = 2))
            i = gtk.Image()
            i.set_from_stock(gtk.STOCK_NO, gtk.ICON_SIZE_BUTTON)
            b2.child.pack_start(i, expand = False)
            l = gtk.Label(_("_Pause"))
            l.set_use_underline(True)
            l.set_mnemonic_widget(b2)
            b2.child.pack_start(l)
            b1.connect('clicked', self.cancel_clicked)
            b2.connect('clicked', self.pause_clicked)
            hbox.pack_start(b1)
            hbox.pack_start(b2)
            vbox.pack_start(hbox)

        self.child.add(vbox)

        self.text = text
        self.paused = False
        self.quit = False

        self.label.set_markup(self.text % initial)
        self.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self.show_all()
        while gtk.events_pending(): gtk.main_iteration()

    def pause_clicked(self, button):
        self.paused = button.get_active()

    def cancel_clicked(self, button):
        self.quit = True

    def step(self, *values):
        self.label.set_markup(self.text % values)
        if self.count:
            self.current += 1
            self.progress.set_fraction(
                max(0, min(1, self.current / float(self.count))))
        else:
            self.progress.pulse()
            
        while not self.quit and (self.paused or gtk.events_pending()):
            gtk.main_iteration()
        return self.quit

    def recenter(self, parent, event):
        x, y = parent.get_position()
        dx, dy = parent.get_size()
        dx2, dy2 = self.get_size()
        self.move(x + dx/2 - dx2/2, y + dy/2 - dy2/2)

    def end(self):
        self.get_transient_for().disconnect(self.sig)
        self.destroy()

class BigCenteredImage(gtk.Window):
    def __init__(self, title, filename):
        gtk.Window.__init__(self)
        width = gtk.gdk.screen_width() / 2
        height = gtk.gdk.screen_height() / 2
        pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(filename, width, height)
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
        self.child.child.connect('button-press-event', self.destroy)
        self.child.child.connect('key-press-event', self.destroy)
        self.show_all()

    def destroy(self, *args): gtk.Window.destroy(self)

class TrayIcon(object):
    def __init__(self, pixbuf, cbs):
        try:
            import trayicon
        except:
            self.icon = None
        else:
            self.icon = trayicon.TrayIcon('quodlibet')
            self.tips = gtk.Tooltips()
            self.eb = gtk.EventBox()
            i = gtk.Image()
            i.set_from_pixbuf(pixbuf)
            self.eb.add(i)
            self.icon.add(self.eb)
            self.eb.connect("button-press-event", self._event)
            self.eb.connect("scroll-event", self._scroll)
            self.cbs = cbs
            self.icon.show_all()
            print to(_("Initialized status icon."))

    def _event(self, widget, event, button = None):
        c = self.cbs.get(button or event.button)
        if callable(c): c(event)

    def _scroll(self, widget, event):
        button = {gtk.gdk.SCROLL_DOWN: 4,
                  gtk.gdk.SCROLL_UP: 5,
                  gtk.gdk.SCROLL_RIGHT: 6,
                  gtk.gdk.SCROLL_LEFT: 7}.get(event.direction)
        self._event(widget, event, button)


    def set_tooltip(self, tooltip):
        if self.icon: self.tips.set_tip(self.eb, tooltip)

    tooltip = property(None, set_tooltip)

class PlaylistWindow(object):
    from weakref import WeakValueDictionary
    list_windows = WeakValueDictionary()
    def __new__(cls, name, *args, **kwargs):
        win = cls.list_windows.get(name, None)
        if win is None:
            win = super(PlaylistWindow, cls).__new__(cls, name,
                                                     *args, **kwargs)
            win.initialize_window(name)
            cls.list_windows[name] = win
            # insert sorted, unless present
            def insert_sorted(model, path, iter, last_try):
                if model[iter][1] == win.name:
                    return True # already present
                if model[iter][1] > win.name:
                    model.insert_before(iter, [win.prettyname, win.name])
                    return True # inserted
                if path[0] == last_try:
                    model.insert_after(iter, [win.prettyname, win.name])
                    return True # appended
            model = PlayList.lists_model()
            model.foreach(insert_sorted, len(model)-1)
        return win

    def __init__(self, name):
        self.win.present()

    def set_name(self, name):
        self.prettyname = name
        self.name = PlayList.normalize_name(name)
        self.win.set_title('Quod Libet Playlist: %s' % name)

    def destroy(self, *w):
        if not len(self.view.view.get_model()):
            def remove_matching(model, path, iter, name):
                if model[iter][1] == name:
                    model.remove(iter)
                    return True
            PlayList.lists_model().foreach(remove_matching, self.name)
        self.win.destroy()
        self.view.destroy()

    def initialize_window(self, name):
        win = self.win = gtk.Window()
        win.set_destroy_with_parent(True)
        win.set_default_size(400, 400)
        win.set_border_width(12)

        vbox = self.vbox = gtk.VBox(spacing = 6)
        win.add(vbox)

        hbox = gtk.HBox(spacing = 6)
        bar = SearchBar(hbox, _("Add Results"), self.add_query_results)
        vbox.pack_start(hbox, expand = False, fill = False)

        hbox = self.hbox = gtk.HButtonBox()
        hbox.set_layout(gtk.BUTTONBOX_END)
        vbox.pack_end(hbox, expand = False)
        vbox.pack_end(gtk.HSeparator(), expand = False)

        close = self.close = qltk.Button(stock = gtk.STOCK_CLOSE)
        hbox.pack_end(close, expand = False)

        swin = self.swin = gtk.ScrolledWindow()
        swin.set_shadow_type(gtk.SHADOW_IN)
        swin.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        vbox.pack_start(swin)

        view = gtk.TreeView()
        self.view = PlayList(view, name)
        swin.add(view)

        self.set_name(name)
        self.win.connect('delete-event', self.destroy)
        self.win.connect('destroy', self.destroy)
        self.close.connect('clicked', self.destroy)
        self.win.show_all()

    def add_query_results(self, text, sort):
        query = text.decode('utf-8').strip()
        try:
           songs = library.query(query)
           songs.sort()
           self.view.append_songs(songs)
        except ValueError: pass


# A tray icon aware of UI policy -- left click shows/hides, right
# click makes a callback.
class HIGTrayIcon(TrayIcon):
    def __init__(self, pixbuf, window, cbs = {}):
        self._window = window
        cbs[1] = self._showhide
        TrayIcon.__init__(self, pixbuf, cbs)

    def _showhide(self, event):
        if self._window.get_property('visible'):
            self._pos = self._window.get_position()
            self._window.hide()
        else:
            self._window.move(*self._pos)
            self._window.show()

class MmKeys(object):
    def __init__(self, cbs):
        try:
            import mmkeys
        except: pass
        else:
            self.keys = mmkeys.MmKeys()
            map(self.keys.connect, *zip(*cbs.items()))
            print to(_("Initialized multimedia key support."))

class Osd(object):
    def __init__(self):
        try:
            import gosd
        except:
            self.gosd = None
        else:
            self.gosd = gosd
            self.level = 0
            self.window = None

    def show_osd(self, song):
        if not self.gosd: return
        elif config.getint("settings", "osd") == 0: return
        color1, color2 = config.get("settings", "osdcolors").split()
        font = config.get("settings", "osdfont")

        if self.window: self.window.destroy()

        # \xe2\x99\xaa is a music note.
        msg = "\xe2\x99\xaa "

        msg += "<span foreground='%s' style='italic'>%s</span>" %(
            color2, util.escape(song("~title~version")))
        msg += " <span size='small'>(%s)</span> " % song("~length")
        msg += "\xe2\x99\xaa\n"

        msg += "<span size='x-small'>"
        for key in ["artist", "album", "tracknumber"]:
            if not song.unknown(key):
                msg += ("<span foreground='%s' size='xx-small' "
                        "style='italic'>%s</span> %s   "%(
                    (color2, tag(key), util.escape(song.comma(key)))))
        msg = msg.strip() + "</span>"
        if isinstance(msg, unicode):
            msg = msg.encode("utf-8")

        self.window = self.gosd.osd(msg, "black", color1, font)
        if config.getint("settings", "osd") == 1:
            self.window.move(gtk.gdk.screen_width()/2-self.window.width/2, 5)
        else:
            self.window.move(gtk.gdk.screen_width()/2 - self.window.width/2,
                             gtk.gdk.screen_height()-self.window.height-48)
        self.window.show()
        self.level += 1
        gtk.timeout_add(7500, self.unshow)

    def unshow(self):
        self.level -= 1
        if self.level == 0 and self.window:
            self.window.destroy()
            self.window = None

class BrowserBar(object):
    def __init__(self, hbox):
        for child in hbox.get_children():
            hbox.remove(child)

    def destroy(self): pass

    def can_filter(self, key):
        return False

class PlaylistBar(BrowserBar):
    def __init__(self, hbox, cb):
        super(self.__class__, self).__init__(hbox)
        self.combo = gtk.ComboBox(PlayList.lists_model())
        cell = gtk.CellRendererText()
        self.combo.pack_start(cell, True)
        self.combo.add_attribute(cell, 'text', 0)
        self.combo.set_active(0)
        hbox.pack_start(self.combo)

        self.button = gtk.Button()
        self.button2 = gtk.Button()
        # FIXME: Switch to STOCK_EDIT in 2.6.
        self.button.add(gtk.image_new_from_stock(gtk.STOCK_INDEX,
                                                  gtk.ICON_SIZE_MENU))
        self.button2.add(gtk.image_new_from_stock(gtk.STOCK_REFRESH,
                                                 gtk.ICON_SIZE_MENU))
        self.button.set_sensitive(False)
        self.button2.set_sensitive(False)
        hbox.pack_start(self.button2, expand = False)
        hbox.pack_start(self.button, expand = False)
        self.button.connect('clicked', self.edit_current)
        self.combo.connect('changed', self.list_selected)
        self.button2.connect('clicked', self.list_selected)

        self.cb = cb
        self.tips = gtk.Tooltips()
        self.tips.set_tip(self.button, _("Edit the current playlist"))
        self.tips.set_tip(self.button2, _("Refresh the current playlist"))
        self.tips.enable()
        hbox.show_all()

    def destroy(self):
        self.tips.disable()
        self.combo.set_model(None)
        self.button.destroy()
        self.button2.destroy()
        self.combo.destroy()
        self.tips.destroy()

    def list_selected(self, box):
        active = self.combo.get_active()
        self.button.set_sensitive(active != 0)
        self.button2.set_sensitive(active != 0)
        if active == 0:
            self.cb("", None)
        else:
            playlist = "playlist_" + self.combo.get_model()[active][1]
            self.cb("#(%s > 0)" % playlist, "~#"+playlist)

    def activate(self):
        self.list_selected(None)

    def edit_current(self, button):
        active = self.combo.get_active()
        if active: PlaylistWindow(self.combo.get_model()[active][0])

class EmptyBar(BrowserBar):
    def __init__(self, hbox, cb):
        BrowserBar.__init__(self, hbox)
        self.text = ""
        self.cb = cb

    def set_text(self, text):
        self.text = text

    def activate(self):
        self.cb(self.text, None)

    def can_filter(self, key):
        return True

    def filter(self, key, values):
        if key.startswith("~#"):
            nheader = key[2:]
            queries = ["#(%s = %d)" % (nheader, i) for i in values]
            self.set_text("|(" + ", ".join(queries) + ")")
        else:
            text = "|".join([sre.escape(s) for s in values])
            if key.startswith("~"): key = key[1:]
            self.set_text(u"%s = /^(%s)$/c" % (key, text))
        self.activate()

class SearchBar(EmptyBar):
    model = None
    
    def __init__(self, hbox, button, cb):
        EmptyBar.__init__(self, hbox, cb)

        if SearchBar.model is None:
            SearchBar.model = gtk.ListStore(str)

        self.combo = gtk.ComboBoxEntry(SearchBar.model, 0)
        self.button = qltk.Button(button, cb = self.text_parse)
        self.combo.child.connect('activate', self.text_parse)
        self.combo.child.connect('changed', self.test_filter)
        hbox.pack_start(self.combo)
        hbox.pack_start(self.button, expand = False)
        hbox.show_all()

    def destroy(self):
        self.combo.set_model(None)
        self.button.destroy()
        self.combo.destroy()

    def activate(self):
        self.button.clicked()

    def set_text(self, text):
        self.combo.child.set_text(text)

    def text_parse(self, *args):
        text = self.combo.child.get_text()
        if (parser.is_valid(text) or
            ("#" not in text and "=" not in text and "/" not in text)):
            SearchBar.model.prepend([text])
            try: SearchBar.model.remove(SearchBar.model.get_iter((10,)))
            except ValueError: pass
        self.cb(text, None)

    def test_filter(self, textbox):
        if not config.state('color'): return
        text = textbox.get_text()
        if "=" not in text and "#" not in text and "/" not in text:
            color = "blue"
        elif parser.is_valid(text): color = "dark green"
        else: color = "red"
        gtk.idle_add(self.set_entry_color, textbox, color)

    # Set the color of some text.
    def set_entry_color(self, entry, color):
        layout = entry.get_layout()
        text = layout.get_text()
        markup = '<span foreground="%s">%s</span>' %(
            color, util.escape(text))
        layout.set_markup(markup)

class MainWindow(object):
    def __init__(self):
        self.last_dir = os.path.expanduser("~")
        self.current_song = None
        self.albumfn = None
        self._time = (0, 1)

        self.tips = gtk.Tooltips()
        # create the main window, restore its size
        self.window = gtk.Window()
        self.window.set_title("Quod Libet")
        self.window.set_icon_from_file("quodlibet.png")
        self.window.set_default_size(
            *map(int, config.get('memory', 'size').split()))
        self.window.add(gtk.VBox())
        self.window.connect('configure-event', self.save_size)
        self.window.connect('destroy', gtk.main_quit)

        # create main menubar, load/restore accelerator groups
        self._create_menu()
        self.window.add_accel_group(self.ui.get_accel_group())
        gtk.accel_map_load(const.ACCELS)
        accelgroup = gtk.accel_groups_from_object(self.window)[0]
        accelgroup.connect('accel-changed',
                lambda *args: gtk.accel_map_save(const.ACCELS))
        self.window.child.pack_start(self.ui.get_widget("/Menu"), expand=False)

        # song info (top part of window)
        hbox = gtk.HBox()
        hbox.set_size_request(-1, 102)

        vbox = gtk.VBox()

        hb2 = gtk.HBox()

        # play controls
        t = gtk.Table(2, 3)
        t.set_homogeneous(True)
        t.set_row_spacings(3)
        t.set_col_spacings(3)
        t.set_border_width(3)

        prev = gtk.Button()
        prev.add(gtk.image_new_from_stock(
            gtk.STOCK_MEDIA_PREVIOUS, gtk.ICON_SIZE_LARGE_TOOLBAR))
        prev.connect('clicked', self.previous_song)
        t.attach(prev, 0, 1, 0, 1, xoptions = gtk.FILL, yoptions = gtk.FILL)

        play = gtk.Button()
        play.add(gtk.image_new_from_stock(
            gtk.STOCK_MEDIA_PLAY, gtk.ICON_SIZE_LARGE_TOOLBAR))
        play.connect('clicked', self.play_pause)
        t.attach(play, 1, 2, 0, 1, xoptions = gtk.FILL, yoptions = gtk.FILL)

        next = gtk.Button()
        next.add(gtk.image_new_from_stock(
            gtk.STOCK_MEDIA_NEXT, gtk.ICON_SIZE_LARGE_TOOLBAR))
        next.connect('clicked', self.next_song)
        t.attach(next, 2, 3, 0, 1, xoptions = False, yoptions = False)

        add = gtk.Button()
        add.add(gtk.image_new_from_stock(
            gtk.STOCK_ADD, gtk.ICON_SIZE_LARGE_TOOLBAR))
        add.connect('clicked', self.open_chooser)
        t.attach(add, 0, 1, 1, 2, xoptions = False, yoptions = False)
        self.tips.set_tip(add, _("Add songs to your library"))

        props = gtk.Button()
        props.add(gtk.image_new_from_stock(
            gtk.STOCK_PROPERTIES, gtk.ICON_SIZE_LARGE_TOOLBAR))
        props.connect('clicked', self.current_song_prop)
        t.attach(props, 1, 2, 1, 2, xoptions = False, yoptions = False)
        self.tips.set_tip(props, _("View and edit tags in the playing song"))

        info = gtk.Button()
        info.add(gtk.image_new_from_stock(
            gtk.STOCK_DIALOG_INFO, gtk.ICON_SIZE_LARGE_TOOLBAR))
        info.connect('clicked', self.open_website)
        t.attach(info, 2, 3, 1, 2, xoptions = False, yoptions = False)
        self.tips.set_tip(info, _("Visit the artist's website"))
                          

        self.song_buttons = [info, next, props]
        self.play_image = play.child

        hb2.pack_start(t, expand = False, fill = False)

        # song text
        self.text = gtk.Label()
        self.text.set_size_request(100, -1)
        self.text.set_alignment(0.0, 0.0)
        self.text.set_padding(6, 6)
        hb2.pack_start(self.text)

        vbox.pack_start(hb2, expand = True)

        hbox.pack_start(vbox, expand = True)

        # position slider
        hb2 = gtk.HBox()
        l = gtk.Label("0:00/0:00")
        l.set_padding(6, 0)
        hb2.pack_start(l, expand = False)
        scale = gtk.HScale(gtk.Adjustment(0, 0, 0, 3000, 15000, 0))
        scale.set_update_policy(gtk.UPDATE_DELAYED)
        scale.connect('adjust-bounds', self.seek_slider)
        scale.set_draw_value(False)
        self.song_pos = scale
        self.song_timer = l
        hb2.pack_start(scale)
        vbox.pack_start(hb2, expand = False)

        # cover image
        self.image = gtk.Image()
        self.image.set_size_request(-1, 100)
        self.iframe = gtk.Frame()
        self.iframe.add(gtk.EventBox())
        self.iframe.child.add(self.image)
        self.iframe.child.connect('button-press-event', self.show_big_cover)
        hbox.pack_start(self.iframe, expand = False)

        # volume control
        vbox = gtk.VBox()
        p = gtk.gdk.pixbuf_new_from_file("volume.png")
        i = gtk.Image()
        i.set_from_pixbuf(p)
        vbox.pack_start(i, expand = False)
        adj = gtk.Adjustment(1, 0, 1, 0.01, 0.1)
        self.volume = gtk.VScale(adj)
        self.volume.set_update_policy(gtk.UPDATE_CONTINUOUS)
        self.volume.connect('value-changed', self.update_volume)
        adj.set_value(config.getfloat('memory', 'volume'))
        self.volume.set_draw_value(False)
        self.volume.set_inverted(True)
        self.tips.set_tip(self.volume, _("Adjust audio volume"))
        vbox.pack_start(self.volume)
        hbox.pack_start(vbox, expand = False)

        self.window.child.pack_start(hbox, expand = False)

        # browser bar
        self.query_hbox = gtk.HBox()
        self.window.child.pack_start(self.query_hbox, expand = False)
        
        # song list
        self.song_scroller = sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        sw.set_shadow_type(gtk.SHADOW_IN)
        songlist = gtk.TreeView()
        songlist.set_rules_hint(True)
        songlist.set_size_request(200, 150)
        sw.add(songlist)
        self.songlist = MainSongList(songlist)
        widgets.songs = gtk.ListStore(object)
        self.set_column_headers(config.get("settings", "headers").split())
        self.window.child.pack_start(sw)
        songlist.connect('row-activated', self.select_song)
        songlist.connect('button-press-event', self.songs_button_press)
        songlist.connect('popup-menu', self.songs_popup_menu)
        songlist.connect('columns_changed', self.cols_changed)
        
        # status area
        hbox = gtk.HBox(spacing = 6)
        self.shuffle = shuffle = gtk.CheckButton(_("_Shuffle"))
        self.tips.set_tip(shuffle, _("Play songs in a random order"))
        shuffle.connect('toggled', self.toggle_shuffle)
        shuffle.set_active(config.getboolean('settings', 'shuffle'))
        hbox.pack_start(shuffle, expand = False)
        self.repeat = repeat = gtk.CheckButton(_("_Repeat"))
        repeat.connect('toggled', self.toggle_repeat)
        repeat.set_active(config.getboolean('settings', 'repeat'))
        self.tips.set_tip(
            repeat, _("Restart the playlist after all songs are played"))
        hbox.pack_start(repeat, expand = False)
        self.statusbar = gtk.Label()
        self.statusbar.set_text(_("No time information"))
        self.statusbar.set_alignment(1.0, 0.5)
        self.statusbar.set_justify(gtk.JUSTIFY_RIGHT)
        hbox.pack_start(self.statusbar)
        hbox.set_border_width(3)
        self.window.child.pack_start(hbox, expand = False)

        # Set up the tray icon. It gets created even if we don't
        # actually use it (e.g. missing trayicon.so).
        p = gtk.gdk.pixbuf_new_from_file_at_size("quodlibet.png", 16, 16)
        self.icon = HIGTrayIcon(p, self.window, cbs = {
            2: self.play_pause,
            3: self.tray_popup,
            4: lambda ev: self.volume.set_value(self.volume.get_value()-0.05),
            5: lambda ev: self.volume.set_value(self.volume.get_value()+0.05),
            6: self.next_song,
            7: self.previous_song
            })

        self.browser = SearchBar(self.query_hbox, _("Search"), self.text_parse)
        self.browser.set_text(config.get("memory", "query"))
        self.browser.activate()

        self.open_fifo()
        self.keys = MmKeys({"mm_prev": self.previous_song,
                            "mm_next": self.next_song,
                            "mm_playpause": self.play_pause})
        self.osd = Osd()

        gtk.timeout_add(100, self._update_time)
        self.window.child.show_all()
        self.window.realize()
        self.showhide_playlist(self.ui.get_widget("/Menu/View/Songlist"))
        self.tips.enable()

    def show(self):
        self.window.show()

    def _create_menu(self):
        ag = gtk.ActionGroup('MainWindowActions')
        ag.add_actions([
            ('Music', None, _("_Music")),
            ('AddMusic', gtk.STOCK_ADD, _('_Add Music...'), "<control>O", None,
             self.open_chooser),
            ('NewPlaylist', gtk.STOCK_NEW, _('_New Playlist...'), None, None,
             self.new_playlist),
            ("Preferences", gtk.STOCK_PREFERENCES, None, None, None,
             self.open_prefs),
            ("RefreshLibrary", gtk.STOCK_REFRESH, _("Re_fresh library"), None,
             None, self.rebuild),
            ("ReloadLibrary", gtk.STOCK_REFRESH, _("Re_load library"), None,
             None, self.rebuild_hard),
            ("Quit", gtk.STOCK_QUIT, None, None, None,
             lambda *args: self.window.destroy()),

            ('Filters', None, _("_Filters")),
            ("RandomGenre", gtk.STOCK_DIALOG_QUESTION, _("Random _genre"),
             "<control>G", None, self.random_genre),
            ("RandomArtist", gtk.STOCK_DIALOG_QUESTION, _("Random _artist"),
             "<control>T", None, self.random_artist),
            ("RandomAlbum", gtk.STOCK_DIALOG_QUESTION, _("Random al_bum"),
             "<control>M", None, self.random_album),
            ("NotPlayedDay", gtk.STOCK_FIND, _("Not played to_day"),
             "", None, self.lastplayed_day),
            ("NotPlayedWeek", gtk.STOCK_FIND, _("Not played in a _week"),
             "", None, self.lastplayed_week),
            ("NotPlayedMonth", gtk.STOCK_FIND, _("Not played in a _month"),
             "", None, self.lastplayed_month),
            ("NotPlayedEver", gtk.STOCK_FIND, _("_Never played"),
             "", None, self.lastplayed_never),
            ("Top", gtk.STOCK_GO_UP, _("_Top 40"), "", None, self.top40),
            ("Bottom", gtk.STOCK_GO_DOWN,_("B_ottom 40"), "",
             None, self.bottom40),
            ("Song", None, _("S_ong")),
            ("Previous", gtk.STOCK_MEDIA_PREVIOUS, None, "<control>Left",
             None, self.previous_song),
            ("PlayPause", gtk.STOCK_MEDIA_PLAY, None, "<control>space",
             None, self.play_pause),
            ("Next", gtk.STOCK_MEDIA_NEXT, None, "<control>Right",
             None, self.next_song),
            ("FilterGenre", gtk.STOCK_INDEX, _("Filter on _genre"), "",
             None, self.cur_genre_filter),
            ("FilterArtist", gtk.STOCK_INDEX, _("Filter on _artist"), "",
             None, self.cur_artist_filter),
            ("FilterAlbum", gtk.STOCK_INDEX, _("Filter on al_bum"), "",
             None, self.cur_album_filter),
            ("Properties", gtk.STOCK_PROPERTIES, None, "<Alt>Return", None,
             self.current_song_prop),
            ("Jump", gtk.STOCK_JUMP_TO, _("_Jump to playing song"),
             "<control>J", None, self.jump_to_current),

            ("View", None, _("_View")),
            ("Help", None, _("_Help")),
            ("About", gtk.STOCK_ABOUT, None, None, None, self.show_about),
            ])

        ag.add_toggle_actions([
            ("Songlist", None, _("Song _list"), None, None,
             self.showhide_playlist,
             config.getboolean("memory", "songlist"))])

        ag.add_radio_actions([
            ("BrowserDisable", None, _("_Disable browsing"), None, None, 0),
            ("BrowserSearch", None, _("_Search library"), None, None, 1),
            ("BrowserPlaylist", None, _("_Playlists"), None, None, 2)
            ], 1, self.select_browser)

        self.ui = gtk.UIManager()
        self.ui.insert_action_group(ag, 0)
        self.ui.add_ui_from_string(const.MENU)

        # Cute. So. UIManager lets you attach tooltips, but when they're
        # for menu items, they just get ignored. So here I get to actually
        # attach them.
        self.tips.set_tip(
            self.ui.get_widget("/Menu/Music/RefreshLibrary"),
            _("Check for changes in the library made since the program "
              "was started"))
        self.tips.set_tip(
            self.ui.get_widget("/Menu/Music/ReloadLibrary"),
            _("Reload all songs in your library (this can take a long time)"))
        self.tips.set_tip(
            self.ui.get_widget("/Menu/Filters/Top"),
             _("The 40 songs you've played most (more than 40 may "
               "be chosen if there are ties)"))
        self.tips.set_tip(
            self.ui.get_widget("/Menu/Filters/Bottom"),
            _("The 40 songs you've played least (more than 40 may "
              "be chosen if there are ties)"))
        self.tips.set_tip(
            self.ui.get_widget("/Menu/Song/Properties"),
            _("View and edit tags in the playing song"))


    def select_browser(self, activator, current):
        [self.hide_browser, self.show_search, self.show_listselect][
            current.get_current_value()](activator)

    def tray_popup(self, event, *args):
        tray_menu = gtk.Menu()
        if player.playlist.paused:
            b = gtk.ImageMenuItem(_("_Play"))
            tray_menu_play = b.get_image()
            tray_menu_play.set_from_stock(
                gtk.STOCK_MEDIA_PLAY, gtk.ICON_SIZE_MENU)
        else:
            b = gtk.ImageMenuItem(_("_Pause"))
            tray_menu_play = b.get_image()
            tray_menu_play.set_from_stock(
                gtk.STOCK_MEDIA_PAUSE, gtk.ICON_SIZE_MENU)
        b.connect('activate', self.play_pause)
        tray_menu.append(b)
        tray_menu.append(gtk.SeparatorMenuItem())
        b = gtk.ImageMenuItem(_("Pre_vious"))
        b.connect('activate', self.previous_song)
        b.get_image().set_from_stock('gtk-media-previous', gtk.ICON_SIZE_MENU)
        tray_menu.append(b)
        b = gtk.ImageMenuItem(_("_Next"))
        b.connect('activate', self.next_song)
        b.get_image().set_from_stock('gtk-media-next', gtk.ICON_SIZE_MENU)
        tray_menu.append(b)
        tray_menu.append(gtk.SeparatorMenuItem())
        b = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        b.connect('activate', gtk.main_quit)
        tray_menu.append(b)        
        tray_menu.show_all()
        tray_menu.connect('selection-done', lambda m: m.destroy())
        tray_menu.popup(None, None, None, event.button, event.time)

    def open_fifo(self):
        if not os.path.exists(const.CONTROL):
            util.mkdir(const.DIR)
            os.mkfifo(const.CONTROL, 0600)
        self.fifo = os.open(const.CONTROL, os.O_NONBLOCK)
        gtk.input_add(self.fifo, gtk.gdk.INPUT_READ, self._input_check)

    def _input_check(self, source, condition):
        c = os.read(source, 1)
        toggles = { "@": self.repeat, "&": self.shuffle }
        if c == "<": self.previous_song()
        elif c == ">": self.next_song()
        elif c == "-": self.play_pause()
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
        elif c in toggles:
            wid = toggles[c]
            c2 = os.read(source, 1)
            if c2 == "0": wid.set_active(False)
            elif c2 == "t": wid.set_active(not wid.get_active())
            else: wid.set_active(True)
        elif c == "!":
            if not self.window.get_property('visible'):
                self.window.move(*self.window_pos)
            self.window.present()
        elif c == "q": self.make_query(os.read(source, 4096))
        elif c == "s":
            player.playlist.seek(util.parse_time(os.read(source, 20)) * 1000)
        elif c == "p":
            filename = os.read(source, 4096)
            if library.add(filename):
                song = library[filename]
                if song not in player.playlist.get_playlist():
                    e_fn = sre.escape(filename)
                    self.make_query("filename = /^%s/c" % e_fn)
                player.playlist.go_to(library[filename])
                player.playlist.paused = False
            else:
                print to(_("W: Unable to load %s") % filename)
        elif c == "d":
            filename = os.read(source, 4096)
            for a, c in library.scan([filename]): pass
            self.make_query("filename = /^%s/c" % sre.escape(filename))

        os.close(self.fifo)
        self.open_fifo()

    def set_paused(self, paused):
        gtk.idle_add(self._update_paused, paused)

    def set_song(self, song, player):
        gtk.idle_add(self._update_song, song, player)

    def missing_song(self, song):
        gtk.idle_add(self._missing_song, song)

    # Called when no cover is available, or covers are off.
    def disable_cover(self):
        self.iframe.hide()

    # Called when covers are turned on; an image may not be available.
    def enable_cover(self):
        if self.image.get_pixbuf():
            self.iframe.show()

    def _update_paused(self, paused):
        menu = self.ui.get_widget("/Menu/Song/PlayPause")
        if paused:
            self.play_image.set_from_stock(
                gtk.STOCK_MEDIA_PLAY, gtk.ICON_SIZE_LARGE_TOOLBAR)
            menu.get_image().set_from_stock(
                gtk.STOCK_MEDIA_PLAY, gtk.ICON_SIZE_MENU)
            menu.child.set_text(_("_Play"))
        else:
            self.play_image.set_from_stock(
                gtk.STOCK_MEDIA_PAUSE, gtk.ICON_SIZE_LARGE_TOOLBAR)
            menu.get_image().set_from_stock(
                gtk.STOCK_MEDIA_PAUSE, gtk.ICON_SIZE_MENU)
            menu.child.set_text(_("_Pause"))
        menu.child.set_use_underline(True)

    def set_time(self, cur, end):
        self._time = (cur, end)

    def _update_time(self):
        cur, end = self._time
        self.song_pos.set_value(cur)
        self.song_timer.set_text("%d:%02d/%d:%02d" %
                            (cur // 60000, (cur % 60000) // 1000,
                             end // 60000, (end % 60000) // 1000))
        return True

    def _missing_song(self, song):
        path = (player.playlist.get_playlist().index(song),)
        iter = widgets.songs.get_iter(path)
        widgets.songs.remove(iter)
        self.statusbar.set_text(_("Could not play %s.") % song['~filename'])
        try: library.remove(song)
        except KeyError: pass
        player.playlist.remove(song)

    def update_markup(self, song):
        if song:
            self.text.set_markup(song.to_markup())
            self.icon.tooltip = song.to_short()
            self.osd.show_osd(song)
        else:
            s = _("Not playing")
            self.text.set_markup("<span size='xx-large'>%s</span>" % s)
            self.icon.tooltip = s
            self.albumfn = None
            self.disable_cover()

    def _update_song(self, song, player):
        self.window.show()
        for wid in self.song_buttons:
            wid.set_sensitive(bool(song))
        for wid in ["Jump", "Next", "Properties", "FilterGenre",
                    "FilterArtist", "FilterAlbum"]:
            self.ui.get_widget('/Menu/Song/' + wid).set_sensitive(bool(song))
        if song:
            self.song_pos.set_range(0, player.length)
            self.song_pos.set_value(0)
            cover = song.find_cover()
            if cover and cover.name != self.albumfn:
                try:
                    p = gtk.gdk.pixbuf_new_from_file_at_size(
                        cover.name, 100, 100)
                except:
                    self.image.set_from_pixbuf(None)
                    self.disable_cover()
                    self.albumfn = None
                else:
                    self.image.set_from_pixbuf(p)
                    if config.state("cover"): self.enable_cover()
                    self.albumfn = cover.name
            elif not cover:
                self.image.set_from_pixbuf(None)
                self.disable_cover()

            for h in ['genre', 'artist', 'album']:
                self.ui.get_widget(
                    "/Menu/Song/Filter%s" % h.capitalize()).set_sensitive(
                    not song.unknown(h))

            self.update_markup(song)
        else:
            self.image.set_from_pixbuf(None)
            self.song_pos.set_range(0, 1)
            self.song_pos.set_value(0)
            self._time = (0, 1)
            self.update_markup(None)

        # Update the currently-playing song in the list by bolding it.
        last_song = self.current_song
        self.current_song = song
        col = 0

        def update_if_last_or_current(model, path, iter):
            this_song = model[iter][col]
            if this_song is song or this_song is last_song:
                model.row_changed(path, iter)

        widgets.songs.foreach(update_if_last_or_current)
        gc.collect()
        if song and config.getboolean("settings", "jump"):
            self.jump_to_current()
        return False

    def gtk_main_quit(self, *args):
        gtk.main_quit()

    def save_size(self, widget, event):
        config.set("memory", "size", "%d %d" % (event.width, event.height))

    def new_playlist(self, activator):
        options = map(PlayList.prettify_name, library.playlists())
        name = GetStringDialog(self.window, _("New Playlist..."),
                               _("Enter a name for the new playlist. If it "
                                 "already exists it will be opened for "
                                 "editing."), options).run()
        if name:
            PlaylistWindow(name)

    def showhide_widget(self, box, on):
        if on and box.get_property('visible'): return
        width, height = self.window.get_size()
        if on:
            box.show()
            dy = box.get_allocation().height
            self.window.set_geometry_hints(None,
                max_height = -1, min_height = -1, max_width = -1)
            self.window.resize(width, height + dy)
            box.set_size_request(-1, -1)
        else:
            dy = box.get_allocation().height
            box.hide()
            self.window.resize(width, height - dy)
            box.set_size_request(-1, dy)
        if not box.get_property("visible"):
            self.window.set_geometry_hints(
                None, max_height = height - dy, max_width = 32000)
        self.window.realize()

    def showhide_playlist(self, toggle):
        self.showhide_widget(self.song_scroller, toggle.get_active())
        config.set("memory", "songlist", str(toggle.get_active()))

    def open_website(self, button):
        song = self.current_song
        site = song.website().replace("\\", "\\\\").replace("\"", "\\\"")
        for s in ["sensible-browser"]+os.environ.get("BROWSER","").split(":"):
            if util.iscommand(s):
                if "%s" in s:
                    s = s.replace("%s", '"' + site + '"')
                    s = s.replace("%%", "%")
                else: s += " \"%s\"" % site
                print to(_("Opening web browser: %s") % s)
                if os.system(s + " &") == 0: break
        else:
            qltk.ErrorMessage(self.window,
                              _("Unable to start a web browser"),
                              _("A web browser could not be found. Please set "
                                "your $BROWSER variable, or make sure "
                                "/usr/bin/sensible-browser exists.")).run()

    def play_pause(self, *args):
        if self.current_song is None: player.playlist.reset()
        else: player.playlist.paused ^= True

    def jump_to_current(self, *args):
        try: path = (player.playlist.get_playlist().index(self.current_song),)
        except ValueError: pass
        else: self.songlist.jump_to(path)

    def next_song(self, *args):
        player.playlist.next()

    def previous_song(self, *args):
        player.playlist.previous()

    def toggle_repeat(self, button):
        player.playlist.repeat = button.get_active()
        config.set("settings", "repeat", str(bool(button.get_active())))

    def show_about(self, menuitem):
        if not hasattr(widgets, 'about'):
            widgets.about = AboutWindow(self.window)
        widgets.about.present()

    def toggle_shuffle(self, button):
        player.playlist.shuffle = button.get_active()
        config.set("settings", "shuffle", str(bool(button.get_active())))

    def seek_slider(self, slider, v):
        gtk.idle_add(player.playlist.seek, v)

    def random_artist(self, menuitem):
        self.make_query("artist = /^%s$/c" %(
            sre.escape(library.random("artist"))))

    def random_album(self, menuitem):
        self.make_query("album = /^%s$/c" %(
            sre.escape(library.random("album"))))
        self.shuffle.set_active(False)

    def random_genre(self, menuitem):
        self.make_query("genre = /^%s$/c" %(
            sre.escape(library.random("genre"))))

    def lastplayed_day(self, menuitem):
        self.make_query("#(lastplayed > today)")
    def lastplayed_week(self, menuitem):
        self.make_query("#(lastplayed > 7 days ago)")
    def lastplayed_month(self, menuitem):
        self.make_query("#(lastplayed > 30 days ago)")
    def lastplayed_never(self, menuitem):
        self.make_query("#(playcount = 0)")

    def top40(self, menuitem):
        songs = [(song["~#playcount"], song) for song in library.values()]
        if len(songs) == 0: return
        songs.sort()
        if len(songs) < 40:
            self.make_query("#(playcount > %d)" % (songs[0][0] - 1))
        else:
            self.make_query("#(playcount > %d)" % (songs[-40][0] - 1))

    def bottom40(self, menuitem):
        songs = [(song["~#playcount"], song) for song in library.values()]
        if len(songs) == 0: return
        songs.sort()
        if len(songs) < 40:
            self.make_query("#(playcount < %d)" % (songs[0][0] + 1))
        else:
            self.make_query("#(playcount < %d)" % (songs[-40][0] + 1))

    def show_big_cover(self, image, event):
        if (self.current_song and event.button == 1 and
            event.type == gtk.gdk._2BUTTON_PRESS):
            cover = self.current_song.find_cover()
            BigCenteredImage(self.current_song.comma("album"), cover.name)

    def rebuild(self, activator, hard = False):
        window = WaitLoadWindow(self.window, len(library) // 7,
                                _("Quod Libet is scanning your library. "
                                  "This may take several minutes.\n\n"
                                  "%d songs reloaded\n%d songs removed"),
                                (0, 0))
        iter = 7
        c = r = 0
        for c, r in library.rebuild(hard):
            if iter == 7:
                if window.step(c, r):
                    window.end()
                    break
                iter = 0
            iter += 1
        else:
            window.end()
            if config.get("settings", "scan"):
                self.scan_dirs(config.get("settings", "scan").split(":"))
        if c + r != 0:
            library.save(const.LIBRARY)
            player.playlist.refilter()
            self.refresh_songlist()

    def rebuild_hard(self, activator):
        self.rebuild(activator, True)

    # Set up the preferences window.
    def open_prefs(self, activator):
        if not hasattr(widgets, 'preferences'):
            widgets.preferences = PreferencesWindow(self.window)
        widgets.preferences.present()

    def select_song(self, tree, indices, col):
        iter = widgets.songs.get_iter(indices)
        song = widgets.songs.get_value(iter, 0)
        player.playlist.go_to(song)
        player.playlist.paused = False

    def open_chooser(self, *args):
        chooser = FileChooser(self.window, _("Add Music"), self.last_dir)
        resp, fns = chooser.run()
        if resp == gtk.RESPONSE_OK: self.scan_dirs(fns)
        if fns: self.last_dir = fns[0]
        library.save(const.LIBRARY)

    def scan_dirs(self, fns):
        win = WaitLoadWindow(self.window, 0,
                             _("Quod Libet is scanning for new songs and "
                               "adding them to your library.\n\n"
                               "%d songs added"), 0)
        for added, changed in library.scan(fns):
            if win.step(added): break
        win.end()
        player.playlist.refilter()
        self.refresh_songlist()

    def update_volume(self, slider):
        val = (2 ** slider.get_value()) - 1
        player.device.volume = val
        config.set("memory", "volume", str(slider.get_value()))

    def songs_button_press(self, view, event):
        if event.button != 3:
            return False
        x, y = map(int, [event.x, event.y])
        try: path, col, cellx, celly = view.get_path_at_pos(x, y)
        except TypeError: return True
        view.grab_focus()
        selection = view.get_selection()
        if not selection.path_is_selected(path):
            view.set_cursor(path, col, 0)
        header = col.header_name
        self.prep_main_popup(header, event.button, event.time)
        return True

    def songs_popup_menu(self, view):
        path, col = view.get_cursor()
        header = col.header_name
        self.prep_main_popup(header, 1, 0)

    def song_col_filter(self, item):
        view = self.songlist.view
        path, col = view.get_cursor()
        header = col.header_name
        if "~" in header[1:]: header = filter(None, header.split("~"))[0]
        self.filter_on_header(header)

    def filter_proxy(self, item, header): self.filter_on_header(header)
    def artist_filter(self, item): self.filter_on_header('artist')
    def album_filter(self, item): self.filter_on_header('album')
    def genre_filter(self, item): self.filter_on_header('genre')

    def cur_artist_filter(self, item):
        self.filter_on_header('artist', [self.current_song])
    def cur_album_filter(self, item):
        self.filter_on_header('album', [self.current_song])
    def cur_genre_filter(self, item):
        self.filter_on_header('genre', [self.current_song])

    def remove_song(self, item):
        view = self.songlist.view
        selection = view.get_selection()
        model, rows = selection.get_selected_rows()
        rows.sort()
        rows.reverse()
        for row in rows:
            song = model[row][0]
            iter = widgets.songs.get_iter(row)
            widgets.songs.remove(iter)
            library.remove(song)
            player.playlist.remove(song)

    def delete_song(self, item):
        view = self.songlist.view
        selection = view.get_selection()
        model, rows = selection.get_selected_rows()
        songs = [model[r][0] for r in rows]
        filenames = [song["~filename"] for song in songs]
        filenames.sort()
        d = DeleteDialog(self.window, filenames)
        resp = d.run()
        d.destroy()
        if resp == 1 or resp == gtk.RESPONSE_DELETE_EVENT: return
        else:
            if resp == 0: s = _("Moving %d/%d.")
            elif resp == 2: s = _("Deleting %d/%d.")
            else: return
            w = WaitLoadWindow(self.window, len(songs), s, (0, len(songs)))
            trash = os.path.expanduser("~/.Trash")
            for song in songs:
                filename = str(song["~filename"])
                try:
                    if resp == 0:
                        basename = os.path.basename(filename)
                        shutil.move(filename, os.path.join(trash, basename))
                    else:
                        os.unlink(filename)
                    library.remove(song)
                except:
                    qltk.ErrorMessage(
                        self.window, _("Unable to remove file"),
                        _("Removing <b>%s</b> failed. "
                          "Possibly the target file does not exist, "
                          "or you do not have permission to "
                          "remove it.") % (filename)).run()
                    break
                else:
                    w.step(w.current + 1, w.count)
            w.end()
            player.playlist.refilter()
            self.refresh_songlist()

    def current_song_prop(self, *args):
        song = self.current_song
        if song: SongProperties([song])
            
    def song_properties(self, item):
        SongProperties(self.songlist.get_selected_songs())

    def prep_main_popup(self, header, button, time):
        if "~" in header[1:]: header = header.split("~")[0]
        menu = gtk.Menu()

        if self.browser.can_filter("genre"):
            b = gtk.ImageMenuItem(_("Filter on _genre"))
            b.connect('activate', self.filter_proxy, 'genre')
            b.get_image().set_from_stock(gtk.STOCK_INDEX, gtk.ICON_SIZE_MENU)
            menu.append(b)
        if self.browser.can_filter("artist"):
            b = gtk.ImageMenuItem(_("Filter on _artist"))
            b.connect('activate', self.filter_proxy, 'artist')
            b.get_image().set_from_stock(gtk.STOCK_INDEX, gtk.ICON_SIZE_MENU)
            menu.append(b)
        if self.browser.can_filter("album"):
            b = gtk.ImageMenuItem(_("Filter on al_bum"))
            b.connect('activate', self.filter_proxy, 'album')
            b.get_image().set_from_stock(gtk.STOCK_INDEX, gtk.ICON_SIZE_MENU)
            menu.append(b)
        if (header not in ["genre", "artist", "album"] and
            self.browser.can_filter(header)):
            b = gtk.ImageMenuItem(_("_Filter on %s") % _(tag(header)))
            b.connect('activate', self.filter_proxy, 'album')
            b.get_image().set_from_stock(gtk.STOCK_INDEX, gtk.ICON_SIZE_MENU)
        if menu.get_children(): menu.append(gtk.SeparatorMenuItem())

        b = gtk.ImageMenuItem(gtk.STOCK_REMOVE)
        b.connect('activate', self.remove_song)
        menu.append(b)
        b = gtk.ImageMenuItem(gtk.STOCK_DELETE)
        b.connect('activate', self.delete_song)
        menu.append(b)
        b = gtk.ImageMenuItem(gtk.STOCK_PROPERTIES)
        b.connect('activate', self.song_properties)
        menu.append(b)

        menu.show_all()
        menu.connect('selection-done', lambda m: m.destroy())
        menu.popup(None, None, None, button, time)

    def show_search(self, *args):
        if type(self.browser) != SearchBar:
            for w in ["Filters", "Song/FilterGenre", "Song/FilterArtist",
                      "Song/FilterAlbum"]:
                self.ui.get_widget("/Menu/" + w).show()
            self.browser.destroy()
            self.showhide_widget(self.query_hbox, True)
            self.browser = SearchBar(self.query_hbox,
                                     _("Search"), self.text_parse)
            self.browser.set_text(config.get("memory", "query"))

    def show_listselect(self, *args):
        if type(self.browser) != PlaylistBar:
            for w in ["Filters", "Song/FilterGenre", "Song/FilterArtist",
                      "Song/FilterAlbum"]:
                self.ui.get_widget("/Menu/" + w).hide()
            self.browser.destroy()
            self.showhide_widget(self.query_hbox, True)
            self.browser = PlaylistBar(self.query_hbox,
                                       self.playlist_selected)

    def playlist_selected(self, query, key):
        while gtk.events_pending(): gtk.main_iteration()
        player.playlist.playlist_from_filter(query)
        while gtk.events_pending(): gtk.main_iteration()
        self.songlist.set_sort_by(None, key, False)
        while gtk.events_pending(): gtk.main_iteration()
        self.refresh_songlist()

    def hide_browser(self, *args):
        if type(self.browser) != EmptyBar:
            for w in ["Filters", "Song/FilterGenre", "Song/FilterArtist",
                      "Song/FilterAlbum"]:
                self.ui.get_widget("/Menu/" + w).show()
            self.browser.destroy()
            self.showhide_widget(self.query_hbox, False)
            self.browser = EmptyBar(self.query_hbox,
                                    self.text_parse)

    # Grab the text from the query box, parse it, and make a new filter.
    # The sort argument is not used for this browser.
    def text_parse(self, text, dummy_sort):
        config.set("memory", "query", text)
        text = text.decode("utf-8").strip()
        if player.playlist.playlist_from_filter(text):
            self.refresh_songlist()
        return True

    def filter_on_header(self, header, songs = None):
        if not self.browser or not self.browser.can_filter(header):
            return
        if songs is None:
            songs = self.songlist.get_selected_songs()

        if header.startswith("~#"):
            values = [song(header, 0) for song in songs]
        else:
            values = {}
            for song in songs:
                for val in song.list(header):
                    values[val] = True
            values = values.keys()
        self.browser.filter(header, values)

    def cols_changed(self, view):        
        headers = [col.header_name for col in view.get_columns()]
        if len(headers) == len(config.get("settings", "headers").split()):
            # Not an addition or removal (handled separately)
            config.set("settings", "headers", " ".join(headers))

    def make_query(self, query):
        self.browser.set_text(query.encode('utf-8'))
        self.browser.activate()

    def set_column_headers(self, headers):
        SongList.set_all_column_headers(headers)

    def refresh_songlist(self):
        i, length = self.songlist.refresh(current=self.current_song)
        statusbar = self.statusbar
        if i != 1: statusbar.set_text(
            _("%d songs (%s)") % (i, util.format_time_long(length)))
        else: statusbar.set_text(
            _("%d song (%s)") % (i, util.format_time_long(length)))

class SongList(object):
    """Wrap a treeview that works like a songlist"""
    from weakref import WeakKeyDictionary
    songlistviews = WeakKeyDictionary()
    headers = []

    def __init__(self, view, recall = 0):
        self.view = view
        self.view.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.songlistviews[self] = None     # register self
        self.recall_size = recall
        self.set_column_headers(self.headers)

    def set_all_column_headers(cls, headers):
        cls.headers = headers
        for listview in cls.songlistviews:
            listview.set_column_headers(headers)
    set_all_column_headers = classmethod(set_all_column_headers)

    def get_selected_songs(self):
        model, rows = self.view.get_selection().get_selected_rows()
        return [model[row][0] for row in rows]

    def jump_to(self, path):
        self.view.scroll_to_cell(path)

    def save_widths(self, column, width):
        config.set("memory", "widths", " ".join(
            [str(x.get_width()) for x in self.view.get_columns()]))

    # Build a new filter around our list model, set the headers to their
    # new values.
    def set_column_headers(self, headers):
        if len(headers) == 0: return
        SHORT_COLS = ["tracknumber", "discnumber", "~length"]
        SLOW_COLS = ["~basename", "~dirname", "~filename"]
        if not self.recall_size:
            try: ws = map(int, config.get("memory", "widths").split())
            except: ws = []
        else: ws = []

        if len(ws) != len(headers):
            width = self.recall_size or self.view.get_allocation()[2]
            c = sum([(x.startswith("~#") and 0.2) or 1 for x in headers])
            width = int(width // c)
            ws = [width] * len(headers)
            
        for c in self.view.get_columns(): self.view.remove_column(c)

        def cell_data(column, cell, model, iter,
                attr = (pango.WEIGHT_NORMAL, pango.WEIGHT_BOLD)):
            try:
                song = model[iter][0]
                current_song = widgets.main.current_song
                cell.set_property('weight', attr[song is current_song])
                cell.set_property('text', song.comma(column.header_name))
            except AttributeError: pass

        def cell_data_fn(column, cell, model, iter, code,
                attr = (pango.WEIGHT_NORMAL, pango.WEIGHT_BOLD)):
            try:
                song = model[iter][0]
                current_song = widgets.main.current_song
                cell.set_property('weight', attr[song is current_song])
                cell.set_property('text', song.comma(column.header_name).decode(code, 'replace'))
            except AttributeError: pass

        for i, t in enumerate(headers):
            render = gtk.CellRendererText()
            title = tag(t)
            column = gtk.TreeViewColumn(title, render)
            column.header_name = t
            column.set_resizable(True)
            if t in SHORT_COLS or t.startswith("~#"):
                render.set_fixed_size(-1, -1)
            else:
                column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
                column.set_fixed_width(ws[i])
            if hasattr(self, 'set_sort_by'):
                column.connect('clicked', self.set_sort_by, t)
            self._set_column_settings(column)
            if t in ["~filename", "~basename", "~dirname"]:
                column.set_cell_data_func(render, cell_data_fn,
                                          util.fscoding())
            else:
                column.set_cell_data_func(render, cell_data)
            if t == "~length":
                column.set_property('alignment', 1.0)
                render.set_property('xalign', 1.0)
            self.view.append_column(column)

    def _set_column_settings(self, column):
        column.set_visible(True)

class PlayList(SongList):
    # ["%", " "] + parser.QueryLexeme.table.keys()
    BAD = ["%", " ", "!", "&", "|", "(", ")", "=", ",", "/", "#", ">", "<"]
    DAB = BAD[:]
    DAB.reverse()

    def normalize_name(name):
        for c in PlayList.BAD: name = name.replace(c, "%"+hex(ord(c))[2:])
        return name
    normalize_name = staticmethod(normalize_name)

    def prettify_name(name):
        for c in PlayList.DAB: name = name.replace("%"+hex(ord(c))[2:], c)
        return name
    prettify_name = staticmethod(prettify_name)

    def lists_model(cls):
        try: return cls._lists_model
        except AttributeError:
            model = cls._lists_model = gtk.ListStore(str, str)
            playlists = [[PlayList.prettify_name(p), p] for p in
                          library.playlists()]
            playlists.sort()
            model.append([("All songs"), ""])
            for p in playlists: model.append(p)
            return model
    lists_model = classmethod(lists_model)

    def __init__(self, view, name):
        self.name = 'playlist_' + PlayList.normalize_name(name)
        self.key = '~#' + self.name
        model = self.model = gtk.ListStore(object)
        super(PlayList, self).__init__(view, 400)

        for song in library.query('#(%s > 0)' % self.name, sort=self.key):
            model.append([song])

        view.set_model(model)
        view.connect('button-press-event', self.button_press)
        view.connect('drag-end', self.refresh_indices)
        view.set_reorderable(True)
        self.menu = gtk.Menu()
        rem = gtk.ImageMenuItem(gtk.STOCK_REMOVE, gtk.ICON_SIZE_MENU)
        rem.connect('activate', self.remove_selected_songs)
        self.menu.append(rem)
        prop = gtk.ImageMenuItem(gtk.STOCK_PROPERTIES, gtk.ICON_SIZE_MENU)
        prop.connect('activate', self.song_properties)
        self.menu.append(prop)
        self.menu.show_all()

    def append_songs(self, songs):
        model = self.model
        current_songs = dict.fromkeys([row[0]['~filename'] for row in model])
        for song in songs:
            if song['~filename'] not in current_songs:
                model.append([song])
                song[self.key] = len(model) # 1 based index; 0 means out

    def remove_selected_songs(self, *args):
        model, rows = self.view.get_selection().get_selected_rows()
        rows.sort()
        rows.reverse()
        for row in rows:
            del model[row][0][self.key]
            iter = model.get_iter(row)
            model.remove(iter)
        self.refresh_indices()

    def song_properties(self, *args):
        model, rows = self.view.get_selection().get_selected_rows()
        SongProperties([model[row][0] for row in rows])

    def refresh_indices(self, *args):
        for i, row in enumerate(iter(self.model)):
            row[0][self.key] = i + 1    # 1 indexed; 0 is not present

    def button_press(self, view, event):
        if event.button != 3:
            return False
        x, y = map(int, [event.x, event.y])
        try: path, col, cellx, celly = view.get_path_at_pos(x, y)
        except TypeError: return True
        view.grab_focus()
        selection = view.get_selection()
        if not selection.path_is_selected(path):
            view.set_cursor(path, col, 0)
        self.menu.popup(None, None, None, event.button, event.time)
        return True

    def destroy(self):
        self.menu.destroy()

class MainSongList(SongList):

    def _set_column_settings(self, column):
        column.set_clickable(True)
        column.set_reorderable(True)
        column.set_sort_indicator(False)
        column.connect('notify::width', self.save_widths)

    # Resort based on the header clicked.
    def set_sort_by(self, header, tag, refresh = True):
        s = gtk.SORT_ASCENDING
        if header:
            s = header.get_sort_order()
            if not header.get_sort_indicator() or s == gtk.SORT_DESCENDING:
                s = gtk.SORT_ASCENDING
            else: s = gtk.SORT_DESCENDING

        for h in self.view.get_columns():
            h.set_sort_indicator(False)
        if header:
            header.set_sort_indicator(True)
            header.set_sort_order(s)
        player.playlist.sort_by(tag, s == gtk.SORT_DESCENDING)
        if refresh: self.refresh()

    # Clear the songlist and readd the songs currently wanted.
    def refresh(self, current=None):
        if self.view.get_model() is None:
            self.view.set_model(widgets.songs)

        selected = self.get_selected_songs()
        selected = dict.fromkeys([song['~filename'] for song in selected])

        widgets.songs.clear()
        length = 0
        for song in player.playlist:
            widgets.songs.append([song])
            length += song["~#length"]

        # reselect what we can
        selection = self.view.get_selection()
        for i, row in enumerate(iter(widgets.songs)):
            if row[0]['~filename'] in selected:
                selection.select_path(i)
        i = len(list(player.playlist))
        return i, length

class GetStringDialog(gtk.Dialog):
    def __init__(self, parent, title, text, options = []):
        gtk.Dialog.__init__(self, title, parent)
        self.set_border_width(6)        
        self.set_resizable(False)
        self.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                gtk.STOCK_OPEN, gtk.RESPONSE_OK)
        self.vbox.set_spacing(6)
        self.set_default_response(gtk.RESPONSE_OK)

        box = gtk.VBox(spacing = 6)
        lab = gtk.Label(text)
        box.set_border_width(6)
        lab.set_line_wrap(True)
        lab.set_justify(gtk.JUSTIFY_CENTER)
        box.pack_start(lab)

        if options:
            self.entry = gtk.combo_box_entry_new_text()
            for o in options: self.entry.append_text(o)
            self.val = self.entry.child
            box.pack_start(self.entry)
        else:
            self.val = gtk.Entry()
            box.pack_start(self.val)
        self.vbox.pack_start(box)
        self.child.show_all()

    def run(self):
        self.show()
        self.val.set_text("")
        self.val.set_activates_default(True)
        self.val.grab_focus()
        resp = gtk.Dialog.run(self)
        if resp == gtk.RESPONSE_OK:
            value = self.val.get_text()
        else: value = None
        self.destroy()
        return value

class AddTagDialog(gtk.Dialog):
    def __init__(self, parent, can_change):
        if can_change == True:
            can = ["title", "version", "artist", "album",
                   "performer", "discnumber"]
        else: can = can_change
        can.sort()

        gtk.Dialog.__init__(self, _("Add a new tag"), parent)
        self.set_border_width(6)
        self.set_resizable(False)
        self.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                gtk.STOCK_ADD, gtk.RESPONSE_OK)
        self.vbox.set_spacing(6)
        self.set_default_response(gtk.RESPONSE_OK)
        table = gtk.Table(2, 2)
        table.set_row_spacings(12)
        table.set_col_spacings(6)
        table.set_border_width(6)

        if can_change == True:
            self.tag = gtk.combo_box_entry_new_text()
            for tag in can: self.tag.append_text(tag)
        else:
            self.tag = gtk.combo_box_new_text()
            for tag in can: self.tag.append_text(tag)
            self.tag.set_active(0)

        label = gtk.Label()
        label.set_property('xalign', 0.0)
        label.set_text(_("_Tag:"))
        label.set_use_underline(True)
        label.set_mnemonic_widget(self.tag)
        table.attach(label, 0, 1, 0, 1)
        table.attach(self.tag, 1, 2, 0, 1)

        self.val = gtk.Entry()
        label = gtk.Label()
        label.set_text(_("_Value:"))
        label.set_property('xalign', 0.0)
        label.set_use_underline(True)
        label.set_mnemonic_widget(self.val)
        table.attach(label, 0, 1, 1, 2)
        table.attach(self.val, 1, 2, 1, 2)

        self.vbox.pack_start(table)
        self.child.show_all()

    def get_tag(self):
        try: return self.tag.child.get_text().lower().strip()
        except AttributeError:
            return self.tag.get_model()[self.tag.get_active()][0]

    def get_value(self):
        return self.val.get_text().decode("utf-8")

    def run(self):
        self.show()
        try: self.tag.child.set_activates_default(True)
        except AttributeError: pass
        self.val.set_activates_default(True)
        self.tag.grab_focus()
        return gtk.Dialog.run(self)

class SongProperties(gtk.Window):

    class Information(gtk.ScrolledWindow):
        def __init__(self, parent):
            gtk.ScrolledWindow.__init__(self)
            self.title = _("Information")
            self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
            self.add(gtk.Viewport())
            self.child.set_shadow_type(gtk.SHADOW_NONE)
            self.box = gtk.VBox(spacing = 6)
            self.box.set_property('border-width', 12)
            self.child.add(self.box)
            self.prop = parent

        def _title(self, song):
            text = "<b><span size='x-large'>%s</span></b>" %(
                util.escape(song("title")))
            if "version" in song:
                text += "\n" + util.escape(song.comma("version"))
            w = self.Label(text)
            w.set_alignment(0, 0)
            return w

        def Frame(self, label, widget, big = True):
            f = gtk.Frame()
            g = gtk.Label()
            if big: g.set_markup("<big><u>%s</u></big>" % label)
            else: g.set_markup("<u>%s</u>" % label)
            f.set_label_widget(g)
            f.set_shadow_type(gtk.SHADOW_NONE)
            a = gtk.Alignment(xalign = 0.0, yalign = 0.0,
                              xscale = 1.0, yscale = 1.0)
            a.set_padding(0, 0, 12, 0)
            a.add(widget)
            f.add(a)
            return f

        def _people(self, song):
            vbox = gtk.VBox(spacing = 6)
            vbox.pack_start(self.Label(util.escape(song("artist"))),
                            expand = False)

            for names, tag in [
                (_("performers"), "performer"),
                (_("lyricists"),  "lyricist"),
                (_("arrangers"),  "arranger"),
                (_("composers"),  "composer"),
                (_("conductors"), "conductor"),
                (_("authors"),    "author")]:
                if tag in song:
                    if "\n" in song[tag]:
                        frame = self.Frame(names,
                                           self.Label(util.escape(song[tag])),
                                           False)
                    else:
                        ntag = util.title(_(tag))
                        frame = self.Frame(ntag,
                                           self.Label(util.escape(song[tag])),
                                           False)
                    vbox.pack_start(frame, expand = False)
            return self.Frame(util.title(_("artists")), vbox)

        def _album(self, song):
            title = _("Album")
            cover = song.find_cover()
            w = self.Label("")
            if cover:
                try:
                    hb = gtk.HBox(spacing = 12)
                    hb.pack_start(self._make_cover(cover, song),expand = False)
                    hb.pack_start(w)
                    f = self.Frame(title, hb)
                except:
                    f = self.Frame(title, w)
            else:
                f = self.Frame(title, w)

            text = []
            text.append("<b>%s</b>" % util.escape(song.comma("album")))
            if "date" in song: text[-1] += " - " + util.escape(song["date"])
            secondary = []
            if "discnumber" in song:
                secondary.append(_("Disc %s") % song("~#disc"))
            if "part" in song:
                secondary.append("<b>%s</b>" % util.escape(song.comma("part")))
            if "tracknumber" in song:
                secondary.append(_("Track %s") % song("~#track"))
            if secondary: text.append(" - ".join(secondary))

            if "organization" in song:
                t = util.escape(song.comma("~organization~labelid"))
                text.append(t)

            if "producer" in song:
                text.append("Produced by %s" %(
                    util.escape(song.comma("producer"))))

            w.set_selectable(True)
            w.set_markup("\n".join(text))
            
            f.show_all()
            return f

        def _listen(self, song):
            def counter(i):
                if i == 0: return _("Never")
                elif i == 1: return _("1 time")
                else: return _("%d times") % i

            def ftime(t):
                if t == 0: return _("Unknown")
                else: return time.strftime("%c", time.localtime(t))

            playcount = counter(song["~#playcount"])
            skipcount = counter(song.get("~#skipcount", 0))
            added = ftime(song.get("~#added", 0))
            changed = ftime(song["~#mtime"])
            size = util.format_size(os.path.getsize(song["~filename"]))
            tim = util.format_time_long(song["~#length"])
            fn = util.fsdecode(util.unexpand(song["~filename"]))
            tbl = [(_("play count"), playcount),
                   (_("skip count"), skipcount),
                   (_("length"), tim),
                   (_("added"), added),
                   (_("modified"), changed),
                   (_("file size"), size)
                   ]
            table = gtk.Table(len(tbl) + 1, 2)
            table.set_col_spacings(6)
            l = self.Label(util.escape(fn))
            table.attach(l, 0, 2, 0, 1, xoptions = gtk.FILL)
            table.set_homogeneous(False)
            for i, (l, r) in enumerate(tbl):
                l = util.escape(l) + ":"
                l = l[0].capitalize() + l[1:]
                l = "<b>%s</b>" % l
                table.attach(self.Label(l), 0, 1, i + 1, i + 2, xoptions = 0)
                table.attach(self.Label(util.escape(r)), 1, 2, i + 1, i + 2)

            return self.Frame(_("File"), table)

        def Label(self, str):
            l = gtk.Label()
            l.set_markup(str)
            l.set_alignment(0, 0)
            l.set_selectable(True)
            l.set_size_request(100, -1)
            return l

        def _update_one(self, song):
            self.box.pack_start(self._title(song), expand = False)
            if "album" in song:
                self.box.pack_start(self._album(song), expand = False)
            self.box.pack_start(self._people(song), expand = False)
            self.box.pack_start(self._listen(song), expand = False)

        def _update_album(self, songs):
            songs.sort()
            album = songs[0]("~album~date")
            self.box.pack_start(self.Label(
                "<b><span size='x-large'>%s</span></b>" % util.escape(album)),
                                expand = False)

            song = songs[0]

            text = []
            if "organization" in song:
                text.append(util.escape(song.comma("~organization~labelid")))

            if "producer" in song:
                text.append("Produced by %s" %(
                    util.escape(song.comma("producer"))))

            cover = songs[0].find_cover()
            if cover or text:
                w = self.Label("\n".join(text))
                if cover:
                    try:
                        hb = gtk.HBox(spacing = 12)
                        i = self._make_cover(cover, songs[0])
                        hb.pack_start(i, expand = False)
                        hb.pack_start(w)
                        self.box.pack_start(hb, expand = False)
                    except:
                        self.box.pack_start(w, expand = False)
                else:
                    self.box.pack_start(w, expand = False)

            artists = set()
            for song in songs: artists.update(song.list("artist"))
            artists = list(artists)
            artists.sort()
            l = gtk.Label(", ".join(artists))
            l.set_alignment(0, 0)
            l.set_selectable(True)
            l.set_line_wrap(True)
            self.box.pack_start(
                self.Frame(util.title(_("artists")), l), expand = False)

            text = []
            cur_disc = songs[0]("~#disc", 1) - 1
            cur_part = None
            cur_track = songs[0]("~#track", 1) - 1
            for song in songs:
                track = song("~#track", 0)
                disc = song("~#disc", 0)
                part = song.get("part")
                if disc != cur_disc:
                    if cur_disc: text.append("")
                    cur_track = song("~#track", 1) - 1
                    cur_part = None
                    cur_disc = disc
                    if disc:
                        text.append("<b>%s</b>" % (_("Disc %s") % disc))
                if part != cur_part:
                    tabs = "    " * bool(disc)
                    cur_part = part
                    if part:
                        text.append("%s<b>%s</b>" % (tabs, util.escape(part)))
                cur_track += 1
                tabs = "    " * (bool(disc) + bool(part))
                while cur_track < track:
                    text.append("%s<b>%d.</b> <i>%s</i>" %(
                        tabs, cur_track, _("No information available")))
                    cur_track += 1
                text.append("%s<b>%d.</b> %s" %(
                    tabs, track, util.escape(song.comma("~title~version"))))
            l = self.Label("\n".join(text))
            self.box.pack_start(self.Frame(_("Track List"), l), expand = False)

        def _update_artist(self, songs):
            artist = songs[0].comma("artist")
            self.box.pack_start(self.Label(
                "<b><span size='x-large'>%s</span></b>\n%s" %(
                util.escape(artist), _("%d songs") % len(songs))),
                                expand = False)

            noalbum = 0
            albums = {}
            for song in songs:
                if "album" in song:
                    albums[song.list("album")[0]] = song
                else:
                    noalbum += 1
            albums = [(song.get("date"), song, album) for album, song in
                        albums.items()]
            albums.sort()
            def format((date, song, album)):
                if date: return "%s (%s)" % (util.escape(album), date[:4])
                else: return util.escape(album)
            covers = [(a, s.find_cover(), s) for d, s, a in albums]
            albums = map(format, albums)
            if noalbum: albums.append(_("%d songs with no album") % noalbum)
            self.box.pack_start(
                self.Frame(_("Selected Discography"),
                           self.Label("\n".join(albums))),
                expand = False)
            added = set()
            covers = [ac for ac in covers if bool(ac[1])]
            t = gtk.Table(4, (len(covers) // 4) + 1)
            t.set_col_spacings(12)
            t.set_row_spacings(12)
            for i, (album, cover, song) in enumerate(covers):
                if cover.name in added: continue
                try:
                    cov = self._make_cover(cover, song)
                    self.prop.tips.set_tip(cov.child, album)
                    c = i % 4
                    r = i // 4
                    t.attach(cov, c, c + 1, r, r + 1,
                             xoptions = gtk.EXPAND, yoptions = 0)
                except: pass
                added.add(cover.name)
            self.box.pack_start(t)

        def _update_many(self, songs):
            text = "<b><span size='x-large'>%s</span></b>" %(
                _("%d songs") % len(songs))
            l = self.Label(text)
            self.box.pack_start(l, expand = False)

            tc = sum([complex(song["~#length"], song["~#playcount"])
                      for song in songs])
            time = tc.real
            count = int(tc.imag)
            table = gtk.Table(2, 2)
            table.set_col_spacings(6)
            table.attach(self.Label(_("Total length:")), 0, 1, 0, 1)
            table.attach(self.Label(util.format_time(time)), 1, 2, 0, 1)
            table.attach(self.Label(_("Songs heard:")), 0, 1, 1, 2)
            table.attach(self.Label(str(count)), 1, 2, 1, 2)

            self.box.pack_start(self.Frame(_("Listening"), table),
                                expand = False)

            artists = set()
            albums = set()
            noartist = noalbum = 0
            for song in songs:
                if "artist" in song: artists.update(song.list("artist"))
                else: noartist += 1
                if "album" in song: albums.update(song.list("album"))
                else: noalbum += 1
            artists = list(artists)
            artists.sort()
            arcount = len(artists)
            if noartist: artists.append(_("%d songs with no artist")%noartist)
            artists = util.escape("\n".join(artists))
            if artists:
                self.box.pack_start(
                    self.Frame("%s (%d)" % (util.title(_("artists")), arcount),
                               self.Label(artists)),
                               expand = False)

            albums = list(albums)
            albums.sort()
            alcount = len(albums)
            if noalbum: albums.append(_("%d songs with no album") % noalbum)
            albums = util.escape("\n".join(albums))
            if albums:
                self.box.pack_start(
                    self.Frame("%s (%d)" % (util.title(_("albums")), alcount),
                               self.Label(albums)),
                               expand = False)

        def update(self, songs):
            for c in self.box.get_children():
                self.box.remove(c)
                c.destroy()
            if len(songs) == 1: self._update_one(songs[0])
            else:
                albums =  [song.get("album") for song in songs]
                artists = [song.get("artist") for song in songs]
                if min(albums) == max(albums) and None not in albums:
                    self._update_album(songs[:])
                elif min(artists) == max(artists) and None not in albums:
                    self._update_artist(songs[:])
                else: self._update_many(songs)
            self.box.show_all()

        def _show_big_cover(self, image, event, song):
            if (event.button == 1 and event.type == gtk.gdk._2BUTTON_PRESS):
                cover = song.find_cover()
                if cover:
                    BigCenteredImage(song.comma("album"), cover.name)

        def _make_cover(self, cover, song):
            p = gtk.gdk.pixbuf_new_from_file_at_size(cover.name, 70, 70)
            i = gtk.Image()
            i.set_from_pixbuf(p)
            ev = gtk.EventBox()
            ev.add(i)
            ev.connect('button-press-event', self._show_big_cover, song)
            f = gtk.Frame()
            f.set_shadow_type(gtk.SHADOW_ETCHED_OUT)
            f.add(ev)
            return f

    class EditTags(gtk.VBox):
        def __init__(self, parent):
            gtk.VBox.__init__(self, spacing = 12)
            self.title = _("Edit Tags")
            self.set_border_width(12)
            self.prop = parent

            self.model = gtk.ListStore(str, str, bool, bool, bool, str)
            self.view = gtk.TreeView(self.model)
            selection = self.view.get_selection()
            selection.connect('changed', self.tag_select)
            render = gtk.CellRendererToggle()
            column = gtk.TreeViewColumn(_("Write"), render, active = 2,
                                        activatable = 3)
            render.connect('toggled', self.write_toggle, self.model)
            self.view.append_column(column)

            render = gtk.CellRendererText()
            render.connect('edited', self.edit_tag, self.model, 0)
            column = gtk.TreeViewColumn(_('Tag'), render, text=0)
            self.view.append_column(column)

            render = gtk.CellRendererText()
            render.set_property('editable', True)
            render.connect('edited', self.edit_tag, self.model, 1)
            column = gtk.TreeViewColumn(_('Value'), render, markup = 1,
                                        editable = 3, strikethrough = 4)
            self.view.append_column(column)

            self.view.connect('popup-menu', self.popup_menu)
            self.view.connect('button-press-event', self.button_press)

            sw = gtk.ScrolledWindow()
            sw.set_shadow_type(gtk.SHADOW_IN)
            sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
            sw.add(self.view)
            self.pack_start(sw)

            self.buttonbox = gtk.HBox(spacing = 18)
            bbox1 = gtk.HButtonBox()
            bbox1.set_spacing(6)
            bbox1.set_layout(gtk.BUTTONBOX_START)
            self.add = qltk.Button(stock = gtk.STOCK_ADD, cb = self.add_tag)
            self.remove = qltk.Button(stock = gtk.STOCK_REMOVE,
                                     cb = self.remove_tag)
            self.remove.set_sensitive(False)
            bbox1.pack_start(self.add)
            bbox1.pack_start(self.remove)

            bbox2 = gtk.HButtonBox()
            bbox2.set_spacing(6)
            bbox2.set_layout(gtk.BUTTONBOX_END)
            self.revert = qltk.Button(stock = gtk.STOCK_REVERT_TO_SAVED,
                                      cb = self.revert_files)
            self.save = qltk.Button(stock = gtk.STOCK_SAVE,
                                   cb = self.save_files)
            self.revert.set_sensitive(False)
            self.save.set_sensitive(False)
            bbox2.pack_start(self.revert)
            bbox2.pack_start(self.save)

            self.buttonbox.pack_start(bbox1)
            self.buttonbox.pack_start(bbox2)

            self.pack_start(self.buttonbox, expand = False)

            for widget, tip in [
                (self.view, _("Double-click a tag value to change it, "
                              "right-click for other options")),
                (self.add, _("Add a new tag to the file")),
                (self.remove, _("Remove a tag from the file"))]:
                self.prop.tips.set_tip(widget, tip)

        def popup_menu(self, view):
            path, col = view.get_cursor()
            row = view.get_model()[path]
            self.show_menu(row, 1, 0)

        def button_press(self, view, event):
            if event.button not in (2, 3): return False
            x, y = map(int, [event.x, event.y])
            try: path, col, cellx, celly = view.get_path_at_pos(x, y)
            except TypeError: return True
            view.grab_focus()
            selection = view.get_selection()
            if not selection.path_is_selected(path):
                view.set_cursor(path, col, 0)
            row = view.get_model()[path]

            if event.button == 2: # middle click paste
                if col != view.get_columns()[2]: return False
                display = gtk.gdk.display_manager_get().get_default_display()
                clipboard = gtk.Clipboard(display, "PRIMARY")
                for rend in col.get_cell_renderers():
                    if rend.get_property('editable'):
                        clipboard.request_text(self._paste, (rend, path[0]))
                        return True
                else: return False

            elif event.button == 3: # right click menu
                self.show_menu(row, event.button, event.time)
                return True

        def _paste(self, clip, text, (rend, path)):
            if text: rend.emit('edited', path, text.strip())

        def split_into_list(self, activator):
            model, iter = self.view.get_selection().get_selected()
            row = model[iter]
            spls = config.get("settings", "splitters")
            vals = util.split_value(util.unescape(row[1]), spls)
            if vals[0] != util.unescape(row[1]):
                row[1] = util.escape(vals[0])
                row[2] = True
                for val in vals[1:]: self.add_new_tag(row[0], val)

        def split_title(self, activator):
            model, iter = self.view.get_selection().get_selected()
            row = model[iter]
            spls = config.get("settings", "splitters")
            title, versions = util.split_title(util.unescape(row[1]), spls)
            if title != util.unescape(row[1]):
                row[1] = util.escape(title)
                row[2] = True
                for val in versions: self.add_new_tag("version", val)

        def split_album(self, activator):
            model, iter = self.view.get_selection().get_selected()
            row = model[iter]
            album, disc = util.split_album(util.unescape(row[1]))
            if album != util.unescape(row[1]):
                row[1] = util.escape(album)
                row[2] = True
                self.add_new_tag("discnumber", disc)

        def split_people(self, tag):
            model, iter = self.view.get_selection().get_selected()
            row = model[iter]
            spls = config.get("settings", "splitters")
            person, others = util.split_people(util.unescape(row[1]), spls)
            if person != util.unescape(row[1]):
                row[1] = util.escape(person)
                row[2] = True
                for val in others: self.add_new_tag(tag, val)

        def split_performer(self, activator): self.split_people("performer")
        def split_arranger(self, activator): self.split_people("arranger")

        def show_menu(self, row, button, time):
            menu = gtk.Menu()        
            spls = config.get("settings", "splitters")

            b = gtk.ImageMenuItem(_("_Split into multiple values"))
            b.get_image().set_from_stock(gtk.STOCK_FIND_AND_REPLACE,
                                         gtk.ICON_SIZE_MENU)
            b.set_sensitive(len(util.split_value(row[1], spls)) > 1)
            b.connect('activate', self.split_into_list)
            menu.append(b)
            menu.append(gtk.SeparatorMenuItem())

            if row[0] == "album":
                b = gtk.ImageMenuItem(_("Split disc out of _album"))
                b.get_image().set_from_stock(gtk.STOCK_FIND_AND_REPLACE,
                                             gtk.ICON_SIZE_MENU)
                b.connect('activate', self.split_album)
                b.set_sensitive(util.split_album(row[1])[1] is not None)
                menu.append(b)

            elif row[0] == "title":
                b = gtk.ImageMenuItem(_("Split version out of title"))
                b.get_image().set_from_stock(gtk.STOCK_FIND_AND_REPLACE,
                                             gtk.ICON_SIZE_MENU)
                b.connect('activate', self.split_title)
                b.set_sensitive(util.split_title(row[1], spls)[1] != [])
                menu.append(b)

            elif row[0] == "artist":
                ok = (util.split_people(row[1], spls)[1] != [])

                b = gtk.ImageMenuItem(_("Split arranger out of ar_tist"))
                b.get_image().set_from_stock(gtk.STOCK_FIND_AND_REPLACE,
                                             gtk.ICON_SIZE_MENU)
                b.connect('activate', self.split_arranger)
                b.set_sensitive(ok)
                menu.append(b)

                b = gtk.ImageMenuItem(_("Split _performer out of artist"))
                b.get_image().set_from_stock(gtk.STOCK_FIND_AND_REPLACE,
                                             gtk.ICON_SIZE_MENU)
                b.connect('activate', self.split_performer)
                b.set_sensitive(ok)
                menu.append(b)

            if len(menu.get_children()) > 2:
                menu.append(gtk.SeparatorMenuItem())

            b = gtk.ImageMenuItem(gtk.STOCK_REMOVE, gtk.ICON_SIZE_MENU)
            b.connect('activate', self.remove_tag)
            menu.append(b)

            menu.show_all()
            menu.connect('selection-done', lambda m: m.destroy())
            menu.popup(None, None, None, button, time)

        def tag_select(self, selection):
            model, iter = selection.get_selected()
            self.remove.set_sensitive(bool(selection.count_selected_rows())
                                      and model[iter][3])

        def add_new_tag(self, comment, value):
            edited = True
            edit = True
            orig = None
            deleted = False
            iters = []
            def find_same_comments(model, path, iter):
                if model[path][0] == comment: iters.append(iter)
            self.model.foreach(find_same_comments)
            row = [comment, util.escape(value), edited, edit,deleted,orig]
            if len(iters): self.model.insert_after(iters[-1], row=row)
            else: self.model.append(row=row)
            self.save.set_sensitive(True)
            self.revert.set_sensitive(True)

        def add_tag(self, *args):
            add = AddTagDialog(self.prop, self.songinfo.can_change())

            while True:
                resp = add.run()
                if resp != gtk.RESPONSE_OK: break
                comment = add.get_tag()
                value = add.get_value()
                date = sre.compile("^\d{4}(-\d{2}-\d{2})?$")
                if not self.songinfo.can_change(comment):
                    qltk.ErrorMessage(
                        self.prop, _("Invalid tag"),
                        _("Invalid tag <b>%s</b>\n\nThe files currently"
                          " selected do not support editing this tag.")%
                        util.escape(comment)).run()

                elif comment == "date" and not date.match(value):
                    qltk.ErrorMessage(self.prop, _("Invalid date"),
                                      _("Invalid date: <b>%s</b>.\n\n"
                                        "The date must be entered in YYYY or "
                                        "YYYY-MM-DD format.") % value).run()
                else:
                    self.add_new_tag(comment, value)
                    break

            add.destroy()

        def remove_tag(self, *args):
            model, iter = self.view.get_selection().get_selected()
            row = model[iter]
            if row[0] in self.songinfo:
                row[2] = True # Edited
                row[4] = True # Deleted
            else:
                model.remove(iter)
            self.save.set_sensitive(True)
            self.revert.set_sensitive(True)


        def save_files(self, *args):
            updated = {}
            deleted = {}
            added = {}
            def create_property_dict(model, path, iter):
                row = model[iter]
                # Edited, and or and not Deleted
                if row[2] and not row[4]:
                    if row[5] is not None:
                        updated.setdefault(row[0], [])
                        updated[row[0]].append((util.decode(row[1]),
                                                util.decode(row[5])))
                    else:
                        added.setdefault(row[0], [])
                        added[row[0]].append(util.decode(row[1]))
                if row[2] and row[4]:
                    if row[5] is not None:
                        deleted.setdefault(row[0], [])
                        deleted[row[0]].append(util.decode(row[5]))
            self.model.foreach(create_property_dict)

            win = WritingWindow(self.prop, len(self.songs))
            for song in self.songs:
                changed = False
                for key, values in updated.iteritems():
                    for (new_value, old_value) in values:
                        new_value = util.unescape(new_value)
                        if song.can_change(key):
                            if old_value is None: song.add(key, new_value)
                            else: song.change(key, old_value, new_value)
                            changed = True
                for key, values in added.iteritems():
                    for value in values:
                        value = util.unescape(value)
                        if song.can_change(key):
                            song.add(key, value)
                            changed = True
                for key, values in deleted.iteritems():
                    for value in values:
                        value = util.unescape(value)
                        if song.can_change(key) and key in song:
                            song.remove(key, value)
                            changed = True

                if changed:
                    try: song.write()
                    except:
                        qltk.ErrorMessage(
                            self.prop, _("Unable to edit song"),
                            _("Saving <b>%s</b> failed. The file "
                              "may be read-only, corrupted, or you "
                              "do not have permission to edit it.")%(
                            util.escape(song('~basename')))).run()
                        library.reload(song)
                        player.playlist.refilter()
                        widgets.main.refresh_songlist()
                        break
                    songref_update_view(song)

                if win.step(): break

            win.end()
            self.save.set_sensitive(False)
            self.revert.set_sensitive(False)
            self.prop.update()

        def revert_files(self, *args):
            self.update(self.songs)

        def edit_tag(self, renderer, path, new, model, colnum):
            new = ', '.join(new.splitlines())
            row = model[path]
            date = sre.compile("^\d{4}(-\d{2}-\d{2})?$")
            if row[0] == "date" and not date.match(new):
                qltk.WarningMessage(self.prop, _("Invalid date format"),
                                    _("Invalid date: <b>%s</b>.\n\n"
                                      "The date must be entered in YYYY or "
                                      "YYYY-MM-DD format.") % new).run()
            elif row[colnum].replace('<i>','').replace('</i>','') != new:
                row[colnum] = util.escape(new)
                row[2] = True # Edited
                row[4] = False # not Deleted
                self.save.set_sensitive(True)
                self.revert.set_sensitive(True)

        def write_toggle(self, renderer, path, model):
            row = model[path]
            row[2] = not row[2] # Edited
            self.save.set_sensitive(True)
            self.revert.set_sensitive(True)

        def update(self, songs):
            from library import AudioFileGroup
            self.songinfo = songinfo = AudioFileGroup(songs)
            self.songs = songs
            self.model.clear()

            keys = songinfo.realkeys()
            keys.sort()

            if not config.state("allcomments"):
                machine_comments = set(['replaygain_album_gain',
                                        'replaygain_album_peak',
                                        'replaygain_track_gain',
                                        'replaygain_track_peak'])
                keys = filter(lambda k: k not in machine_comments, keys)

            # reverse order here so insertion puts them in proper order.
            for comment in ['album', 'artist', 'title']:
                try: keys.remove(comment)
                except ValueError: pass
                else: keys.insert(0, comment)

            for comment in keys:
                orig_value = songinfo[comment].split("\n")
                value = songinfo[comment].safenicestr()
                edited = False
                edit = songinfo.can_change(comment)
                deleted = False
                for i, v in enumerate(value.split("\n")):
                    self.model.append(row=[comment, v, edited, edit, deleted,
                                           orig_value[i]])


            self.buttonbox.set_sensitive(bool(songinfo.can_change()))
            self.remove.set_sensitive(False)
            self.save.set_sensitive(False)
            self.revert.set_sensitive(False)

            self.songs = songs

        def destroy(self):
            self.model.clear()
            gtk.VBox.destroy(self)

    class TagByFilename(gtk.VBox):
        def __init__(self, prop):
            gtk.VBox.__init__(self, spacing = 6)
            self.title = _("Tag by Filename")
            self.prop = prop
            self.set_property('border-width', 12)
            hbox = gtk.HBox(spacing = 12)
            combo = gtk.combo_box_entry_new_text()
            for line in const.TBP_EXAMPLES.split("\n"):
                combo.append_text(line)
            hbox.pack_start(combo)
            self.entry = combo.child
            self.entry.connect('changed', self.changed)
            self.preview = qltk.Button(_("_Preview"), gtk.STOCK_CONVERT)
            self.preview.connect('clicked', self.preview_tags)
            hbox.pack_start(self.preview, expand = False)
            self.pack_start(hbox, expand = False)

            self.view = gtk.TreeView()
            sw = gtk.ScrolledWindow()
            sw.set_shadow_type(gtk.SHADOW_IN)
            sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
            sw.add(self.view)
            self.pack_start(sw)

            vbox = gtk.VBox()
            c1 = gtk.CheckButton(_("Replace _underscores with spaces"))
            c1.set_active(config.state("tbp_space"))
            c2 = gtk.CheckButton(_("_Title-case resulting values"))
            c2.set_active(config.state("titlecase"))
            c3 = gtk.CheckButton(_("Split into _multiple values"))
            c3.set_active(config.state("splitval"))
            c4 = gtk.combo_box_new_text()
            c4.append_text(_("Tags should replace existing ones"))
            c4.append_text(_("Tags should be added to existing ones"))
            c4.set_active(config.getint("settings", "addreplace"))
            self.space = c1
            self.titlecase = c2
            self.split = c3
            self.addreplace = c4
            for i in [c1, c2, c3]:
                i.connect('toggled', self.changed)
                vbox.pack_start(i)
            c4.connect('changed', self.changed)
            vbox.pack_start(c4)
            
            self.pack_start(vbox, expand = False)

            bbox = gtk.HButtonBox()
            bbox.set_layout(gtk.BUTTONBOX_END)
            self.save = qltk.Button(
                stock = gtk.STOCK_SAVE, cb = self.save_files)
            bbox.pack_start(self.save)
            self.pack_start(bbox, expand = False)

            for widget, tip in [
                (self.titlecase,
                 _("If appropriate to the language, the first letter of "
                   "each word will be capitalized"))]:
                self.prop.tips.set_tip(widget, tip)

        def update(self, songs):
            from library import AudioFileGroup
            self.songs = songs
            songinfo = AudioFileGroup(songs)
            pattern_text = self.entry.get_text().decode("utf-8")
            self.view.set_model(None)
            try: pattern = util.PatternFromFile(pattern_text)
            except sre.error:
                qltk.ErrorMessage(
                    self.prop, _("Invalid pattern"),
                    _("The pattern\n\t<b>%s</b>\nis invalid. "
                      "Possibly it contains the same tag twice or "
                      "it has unbalanced brackets (&lt; / &gt;).")%(
                    util.escape(pattern_text))).run()
                return

            invalid = []

            for header in pattern.headers:
                if not songinfo.can_change(header):
                    invalid.append(header)
            if len(invalid):
                if len(invalid) == 1:
                    title = _("Invalid tag")
                    msg = _("Invalid tag <b>%s</b>\n\nThe files currently"
                            " selected do not support editing this tag.")
                else:
                    title = _("Invalid tags")
                    msg = _("Invalid tags <b>%s</b>\n\nThe files currently"
                            " selected do not support editing these tags.")
                    
                qltk.ErrorMessage(self.prop, title,
                                  msg % ", ".join(invalid)).run()
                return

            rep = self.space.get_active()
            title = self.titlecase.get_active()
            split = self.split.get_active()
            self.model = gtk.ListStore(object, str,
                                       *([str] * len(pattern.headers)))
            for col in self.view.get_columns():
                self.view.remove_column(col)

            col = gtk.TreeViewColumn(_('File'), gtk.CellRendererText(),
                                     text=1)
            self.view.append_column(col)
            for i, header in enumerate(pattern.headers):
                render = gtk.CellRendererText()
                render.set_property('editable', True)
                render.connect('edited', self.changed, self.model,  i + 2)
                col = gtk.TreeViewColumn(header, render, text = i + 2)
                self.view.append_column(col)
            spls = config.get("settings", "splitters")

            for song in songs:
                basename = song("~basename")
                basename = basename.decode(util.fscoding(), "replace")
                row = [song, basename]
                match = pattern.match(song)
                for h in pattern.headers:
                    text = match.get(h, '')
                    if rep: text = text.replace("_", " ")
                    if title: text = util.title(text)
                    if split: text = "\n".join(util.split_value(text, spls))
                    row.append(text)
                self.model.append(row = row)

            # save for last to potentially save time
            self.view.set_model(self.model)
            self.preview.set_sensitive(False)
            self.save.set_sensitive(len(pattern.headers) > 0)

        def save_files(self, *args):
            pattern_text = self.entry.get_text().decode('utf-8')
            pattern = util.PatternFromFile(pattern_text)
            add = (self.addreplace.get_active() == 1)
            win = WritingWindow(self.prop, len(self.songs))

            def save_song(model, path, iter):
                song = model[path][0]
                row = model[path]
                changed = False
                for i, h in enumerate(pattern.headers):
                    if row[i + 2]:
                        if not add or h not in song:
                            song[h] = row[i + 2].decode("utf-8")
                            changed = True
                        else:
                            vals = row[i + 2].decode("utf-8")
                            for val in vals.split("\n"):
                                if val not in song[h]:
                                    song.add(h, val)
                                    changed = True

                if changed:
                    try:
                        song.sanitize()
                        song.write()
                    except:
                        qltk.ErrorMessage(
                            self.prop, _("Unable to edit song"),
                            _("Saving <b>%s</b> failed. The file "
                              "may be read-only, corrupted, or you "
                              "do not have permission to edit it.")%(
                            util.escape(song('~basename')))).run()
                        library.reload(song)
                        player.playlist.refilter()
                        widgets.main.refresh_songlist()
                        return True
                    songref_update_view(song)

                return win.step()
        
            self.model.foreach(save_song)
            win.end()
            self.save.set_sensitive(False)
            self.prop.update()

        def preview_tags(self, *args):
            self.update(self.songs)

        def changed(self, *args):
            config.set("settings", "addreplace",
                       str(self.addreplace.get_active()))
            config.set("settings", "splitval",
                       str(self.split.get_active()))
            config.set("settings", "titlecase",
                       str(self.titlecase.get_active()))
            config.set("settings", "tbp_space",
                       str(self.space.get_active()))
            self.preview.set_sensitive(True)
            self.save.set_sensitive(False)

        def destroy(self):
            self.view.set_model(None)
            try: self.model.clear()
            except AttributeError: pass
            gtk.VBox.destroy(self)

    class RenameFiles(gtk.VBox):
        def __init__(self, prop):
            gtk.VBox.__init__(self, spacing = 6)
            self.title = _("Rename Files")
            self.prop = prop
            self.set_border_width(12)
            hbox = gtk.HBox(spacing = 12)
            combo = gtk.combo_box_entry_new_text()
            for line in const.NBP_EXAMPLES.split("\n"):
                combo.append_text(line)
            hbox.pack_start(combo)
            self.entry = combo.child
            self.entry.connect('changed', self.changed)
            self.preview = qltk.Button(_("_Preview"), gtk.STOCK_CONVERT)
            self.preview.connect('clicked', self.preview_files)
            hbox.pack_start(self.preview, expand = False)
            self.pack_start(hbox, expand = False)

            self.model = gtk.ListStore(object, str, str)
            self.view = gtk.TreeView(self.model)
            column = gtk.TreeViewColumn(_('File'), gtk.CellRendererText(),
                                        text = 1)
            self.view.append_column(column)
            column = gtk.TreeViewColumn(_('New Name'), gtk.CellRendererText(),
                                        text = 2)
            self.view.append_column(column)
            sw = gtk.ScrolledWindow()
            sw.set_shadow_type(gtk.SHADOW_IN)
            sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
            sw.add(self.view)
            self.pack_start(sw)

            self.replace = gtk.CheckButton(
                _("Replace spaces with _underscores"))
            self.replace.set_active(config.state("nbp_space"))
            self.replace.connect('toggled', self.changed)
            self.windows = gtk.CheckButton(_(
                "Replace _Windows-incompatible characters"))
            self.windows.set_active(config.state("windows"))
            self.windows.connect('toggled', self.changed)
            self.ascii = gtk.CheckButton(_("Replace non-_ASCII characters"))
            self.ascii.set_active(config.state("ascii"))
            self.ascii.connect('toggled', self.changed)
            vbox = gtk.VBox()
            vbox.pack_start(self.replace)
            vbox.pack_start(self.windows)
            vbox.pack_start(self.ascii)
            self.pack_start(vbox, expand = False)

            self.save = qltk.Button(stock = gtk.STOCK_SAVE,
                                    cb = self.rename_files)
            bbox = gtk.HButtonBox()
            bbox.set_layout(gtk.BUTTONBOX_END)
            bbox.pack_start(self.save)
            self.pack_start(bbox, expand = False)

            for widget, tip in [
                (self.windows,
                 _("Characters not allowed in Windows filenames "
                   "(\:?;\"<>|) will be replaced by underscores")),
                (self.ascii,
                 _("Characters outside of the ASCII set (A-Z, a-z, 0-9, "
                   "and punctuation) will be replaced by underscores"))]:
                self.prop.tips.set_tip(widget, tip)

        def changed(self, *args):
            config.set("settings", "windows",
                       str(self.windows.get_active()))
            config.set("settings", "ascii",
                       str(self.ascii.get_active()))
            config.set("settings", "nbp_space",
                       str(self.replace.get_active()))
            self.save.set_sensitive(False)
            self.preview.set_sensitive(bool(self.entry.get_text()))

        def preview_files(self, *args):
            self.update(self.songs)
            self.save.set_sensitive(True)
            self.preview.set_sensitive(False)

        def rename_files(self, *args):
            win = WritingWindow(self.prop, len(self.songs))

            def rename(model, path, iter):
                song = model[path][0]
                oldname = model[path][1]
                newname = model[path][2]
                try:
                    newname = newname.encode(util.fscoding(), "replace")
                    library.rename(song, newname)
                    songref_update_view(song)
                except:
                    qltk.ErrorMessage(
                        self.prop, _("Unable to rename file"),
                        _("Renaming <b>%s</b> to <b>%s</b> failed. "
                          "Possibly the target file already exists, "
                          "or you do not have permission to make the "
                          "new file or remove the old one.") %(
                        util.escape(oldname), util.escape(newname))).run()
                    return True
                return win.step()
            self.model.foreach(rename)
            self.prop.refill()
            self.prop.update()
            self.save.set_sensitive(False)
            win.end()

        def update(self, songs):
            self.songs = songs
            self.model.clear()
            pattern = self.entry.get_text().decode("utf-8")

            underscore = self.replace.get_active()
            windows = self.windows.get_active()
            ascii = self.ascii.get_active()

            try:
                pattern = util.FileFromPattern(pattern)
            except ValueError: 
                qltk.ErrorMessage(
                    self.prop,
                    _("Pattern with subdirectories is not absolute"),
                    _("The pattern\n\t<b>%s</b>\ncontains / but "
                      "does not start from root. To avoid misnamed "
                      "directories, root your pattern by starting "
                      "it from the / directory.")%(
                    util.escape(pattern))).run()
                return
            
            for song in self.songs:
                newname = pattern.match(song)
                code = util.fscoding()
                newname = newname.encode(code, "replace").decode(code)
                basename = song("~basename").decode(code, "replace")
                if underscore: newname = newname.replace(" ", "_")
                if windows:
                    for c in '\\:*?;"<>|':
                        newname = newname.replace(c, "_")
                if ascii:
                    newname = "".join(
                        map(lambda c: ((ord(c) < 127 and c) or "_"),
                            newname))
                self.model.append(row=[song, basename, newname])
            self.preview.set_sensitive(False)
            self.save.set_sensitive(bool(self.entry.get_text()))

        def destroy(self):
            self.view.set_model(None)
            self.model.clear()
            gtk.VBox.destroy(self)

    class TrackNumbers(gtk.VBox):
        def __init__(self, prop):
            gtk.VBox.__init__(self, spacing = 6)
            self.title = _("Track Numbers")
            self.prop = prop
            self.set_property('border-width', 12)
            hbox = gtk.HBox(spacing = 18)
            hbox2 = gtk.HBox(spacing = 12)

            hbox_start = gtk.HBox(spacing = 3)
            label_start = gtk.Label("Start fro_m:")
            label_start.set_use_underline(True)
            spin_start = gtk.SpinButton()
            spin_start.set_range(1, 99)
            spin_start.set_increments(1, 10)
            spin_start.set_value(1)
            label_start.set_mnemonic_widget(spin_start)
            hbox_start.pack_start(label_start)
            hbox_start.pack_start(spin_start)

            hbox_total = gtk.HBox(spacing = 3)
            label_total = gtk.Label("_Total tracks:")
            label_total.set_use_underline(True)
            spin_total = gtk.SpinButton()
            spin_total.set_range(0, 99)
            spin_total.set_increments(1, 10)
            label_total.set_mnemonic_widget(spin_total)
            hbox_total.pack_start(label_total)
            hbox_total.pack_start(spin_total)

            self.total = spin_total
            self.start = spin_start
            self.total.connect('value-changed', self.changed)
            self.start.connect('value-changed', self.changed)

            hbox2.pack_start(hbox_start, expand = True, fill = False)
            hbox2.pack_start(hbox_total, expand = True, fill = False)

            self.preview = qltk.Button(_("_Preview"), gtk.STOCK_CONVERT)
            self.preview.connect('clicked', self.preview_tracks)
            hbox2.pack_start(self.preview, expand = False)

            self.pack_start(hbox2, expand = False)

            self.model = gtk.ListStore(object, str, str)
            self.view = gtk.TreeView(self.model)
            column = gtk.TreeViewColumn(_('File'), gtk.CellRendererText(),
                                        text = 1)
            self.view.append_column(column)
            column = gtk.TreeViewColumn(_('Track'), gtk.CellRendererText(),
                                        text = 2)
            self.view.append_column(column)
            self.view.set_reorderable(True)
            self.view.connect('drag-end', self.changed)
            w = gtk.ScrolledWindow()
            w.set_shadow_type(gtk.SHADOW_IN)
            w.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
            w.add(self.view)
            self.pack_start(w)

            bbox = gtk.HButtonBox()
            bbox.set_spacing(12)
            bbox.set_layout(gtk.BUTTONBOX_END)
            self.save = qltk.Button(
                stock = gtk.STOCK_SAVE, cb = self.save_files)
            self.revert = qltk.Button(
                stock = gtk.STOCK_REVERT_TO_SAVED, cb = self.revert_files)
            bbox.pack_start(self.revert)
            bbox.pack_start(self.save)
            self.pack_start(bbox, expand = False)

        def save_files(self, *args):
            win = WritingWindow(self.prop, len(self.songs))
            def settrack(model, path, iter):
                song = model[iter][0]
                track = model[iter][2]
                if song["tracknumber"] == track: return win.step()
                song["tracknumber"] = track
                try: song.write()
                except:
                    qltk.ErrorMessage(
                        self.prop, _("Unable to edit song"),
                        _("Saving <b>%s</b> failed. The file may be "
                          "read-only, corrupted, or you do not have "
                          "permission to edit it.")%(
                        util.escape(song('~basename')))).run()
                    library.reload(song)
                    player.playlist.refilter()
                    widgets.main.refresh_songlist()
                    return True
                songref_update_view(song)
                return win.step()
            self.model.foreach(settrack)
            self.prop.update()
            win.end()

        def changed(self, *args):
            self.preview.set_sensitive(True)
            self.save.set_sensitive(False)

        def revert_files(self, *args):
            self.update(self.songs)

        def preview_tracks(self, *args):
            start = self.start.get_value_as_int()
            total = self.total.get_value_as_int()
            def refill(model, path, iter):
                if total: s = "%d/%d" % (path[0] + start, total)
                else: s = str(path[0] + start)
                model[iter][2] = s
            self.model.foreach(refill)
            self.save.set_sensitive(True)
            self.revert.set_sensitive(True)
            self.preview.set_sensitive(False)

        def destroy(self):
            self.view.set_model(None)
            self.model.clear()
            gtk.VBox.destroy(self)

        def update(self, songs):
            self.songs = songs
            self.model.clear()
            self.total.set_value(len(songs))
            for song in songs:
                if not song.can_change("tracknumber"):
                    self.set_sensitive(False)
                    break
            else: self.set_sensitive(True)
            for song in songs:
                basename = util.fsdecode(song("~basename"))
                self.model.append(row = [song, basename, song("tracknumber")])
            self.save.set_sensitive(False)
            self.revert.set_sensitive(False)
            self.preview.set_sensitive(True)

    def __init__(self, songrefs):
        gtk.Window.__init__(self)
        self.set_default_size(300, 430)
        self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self.tips = gtk.Tooltips()
        self.pages = []
        self.notebook = qltk.Notebook()
        self.pages = [self.Information(self), self.EditTags(self),
                      self.TagByFilename(self), self.RenameFiles(self)]
        if len(songrefs) > 1:
            self.pages.append(self.TrackNumbers(self))
        for page in self.pages: self.notebook.append_page(page)
        self.set_property('border-width', 12)
        vbox = gtk.VBox(spacing = 12)
        vbox.pack_start(self.notebook)

        self.fbasemodel = gtk.ListStore(object, str, str, str)
        self.fmodel = gtk.TreeModelSort(self.fbasemodel)
        self.fview = gtk.TreeView(self.fmodel)
        selection = self.fview.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        selection.connect('changed', self.selection_changed)

        if len(songrefs) > 1:
            expander = gtk.Expander(_("Apply to these _files..."))
            c1 = gtk.TreeViewColumn(_('File'), gtk.CellRendererText(), text=1)
            c1.set_sort_column_id(1)
            c2 = gtk.TreeViewColumn(_('Path'), gtk.CellRendererText(), text=2)
            c2.set_sort_column_id(3)
            self.fview.append_column(c1)
            self.fview.append_column(c2)
            self.fview.set_size_request(-1, 130)
            sw = gtk.ScrolledWindow()
            sw.add(self.fview)
            sw.set_shadow_type(gtk.SHADOW_IN)
            sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
            expander.add(sw)
            expander.set_use_underline(True)
            vbox.pack_start(expander, expand = False)

        bbox = gtk.HButtonBox()
        bbox.set_layout(gtk.BUTTONBOX_END)
        button = qltk.Button(stock = gtk.STOCK_CLOSE, cb = self.close)
        bbox.pack_start(button)
        vbox.pack_start(bbox, expand = False)

        self.songrefs = songrefs

        for song in songrefs:
            self.fbasemodel.append(
                row = [song,
                       util.fsdecode(song("~basename")),
                       util.fsdecode(song("~dirname")),
                       song["~filename"]])

        if len(songrefs) > 1: selection.select_all()
        else: self.update(songrefs)
        self.add(vbox)
        self.connect('destroy', self.close)
        self.show_all()

    def close(self, *args):
        self.fview.set_model(None)
        self.tips.destroy()
        self.fbasemodel.clear()
        self.fmodel.clear_cache()
        for page in self.pages: page.destroy()
        self.destroy()

    def update(self, songs = None):
        if songs is not None: self.songrefs = songs
        elif widgets.main.current_song in self.songrefs:
            widgets.main.update_markup(widgets.main.current_song)
        for page in self.pages: page.update(self.songrefs)
        if len(self.songrefs) == 1:
            self.set_title(_("%s - Properties") %
                           self.songrefs[0].comma("title"))
        else:
            self.set_title(_("%s and %d more - Properties") %
                           (self.songrefs[0].comma("title"),
                            len(self.songrefs) - 1))

    def refill(self):
        def refresh(model, iter, path):
            song = model[iter][0]
            model[iter][1] = song("~basename")
            model[iter][2] = song("~dirname")
            model[iter][3] = song["~filename"]
        self.fbasemodel.foreach(refresh)

    def selection_changed(self, selection):
        songrefs = []
        def get_songrefs(model, path, iter, songrefs):
            songrefs.append(model[path][0])
        selection.selected_foreach(get_songrefs, songrefs)
        if len(songrefs): self.update(songrefs)

class WritingWindow(WaitLoadWindow):
    def __init__(self, parent, count):
        WaitLoadWindow.__init__(self, parent, count,
                                _("Saving the songs you changed.\n\n"
                                  "%d/%d songs saved"), (0, count))

    def step(self):
        return WaitLoadWindow.step(self, self.current + 1, self.count)

# Return a 'natural' version of the tag for human-readable bits.
# Strips ~ and ~# from the start and runs it through a map (which
# the user can configure).
def tag(name):
    try:
        if name[0] == "~":
            if name[1] == "#": name = name[2:]
            else: name = name[1:]
        return " / ".join([_(HEADERS_FILTER.get(n, n)) for n
                             in name.split("~")]).title()
    except IndexError:
        return _("Invalid tag name")

def songref_update_view(song):
    try: path = (player.playlist.get_playlist().index(song),)
    except ValueError: pass
    else:
        row = widgets.songs[path]
        row[0] = row[0]

HEADERS_FILTER = { "tracknumber": "track",
                   "discnumber": "disc",
                   "lastplayed": "last played",
                   "filename": "full name",
                   "playcount": "play count",
                   "skipcount": "skip count",
                   "mtime": "modified",
                   "basename": "filename",
                   "dirname": "directory"}

def init():
    if config.get("settings", "headers").split() == []:
       config.set("settings", "headers", "title")
    for opt in config.options("header_maps"):
        val = config.get("header_maps", opt)
        HEADERS_FILTER[opt] = val

    widgets.main = MainWindow()
    player.playlist.info = widgets.main
    gtk.threads_init()
    util.mkdir(const.DIR)
    signal.signal(signal.SIGINT, gtk.main_quit)
    signal.signal(signal.SIGTERM, gtk.main_quit)
    signal.signal(signal.SIGHUP, gtk.main_quit)
    return widgets.main

def error_and_quit():
    qltk.ErrorMessage(None,
                      _("No audio device found"),
                      _("Quod Libet was unable to open your audio device. "
                        "Often this means another program is using it, or "
                        "your audio drivers are not configured.\n\nQuod Libet "
                        "will now exit.")).run()
    gtk.main_quit()
