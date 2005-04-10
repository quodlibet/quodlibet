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
import time     # ~#lastplayed display
import shutil   # renames (and Move to Trash)
import dircache # Ex Falso directory display

import gtk, pango, gobject
import qltk

import const
import config
import player
import parser
import formats
import util

from util import to
from library import library

if sys.version_info < (2, 4):
    from sets import Set as set

# Give us a namespace for now.. FIXME: We need to remove this later.
# Or, replace it with nicer wrappers!
class widgets(object): pass

class FSInterface(object):
    def __init__(self):
        widgets.watcher.connect('paused', self.__paused)
        widgets.watcher.connect('unpaused', self.__unpaused)
        widgets.watcher.connect('song-started', self.__started)
        widgets.watcher.connect('song-ended', self.__ended)

    def __paused(self, watcher):
        try: file(const.PAUSED, "w").close()
        except (OSError, IOError): pass

    def __unpaused(self, watcher):
        try: os.unlink(const.PAUSED)
        except OSError: pass

    def __started(self, watcher, song):
        if song:
            try: f = file(const.CURRENT, "w")
            except (OSError, IOError): pass
            else:
                f.write(song.to_dump())
                f.close()

    def __ended(self, watcher, song, stopped):
        try: os.unlink(const.CURRENT)
        except OSError: pass

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

class SongWatcher(gobject.GObject):
    SIG_PYOBJECT = (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object,))
    SIG_NONE = (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ())
    
    __gsignals__ = {
        # A song in the library has been changed; update it in all views.
        'changed': SIG_PYOBJECT,

        # A song was removed from the library; remove it from all views.
        'removed': SIG_PYOBJECT,

        # A group of changes has been finished; all library views should
        # do a global refresh if necessary
        'refresh': SIG_NONE,

        # A new song started playing (or the current one was restarted).
        'song-started': SIG_PYOBJECT,

        # A new song started playing (or the current one was restarted).
        # The boolean is True if the song was stopped rather than simply
        # ended.
        'song-ended': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                       (object, bool)),

        # Playback was paused.
        'paused': SIG_NONE,

        # Playback was unpaused.
        'unpaused': SIG_NONE,

        # A song was missing (i.e. disappeared from the filesystem).
        # This is emitted in parallel with remove.
        'missing': SIG_PYOBJECT
        }

    time = (0, 1)
    song = None

    def set_time(self, current, end):
        self.time = (current, end)

    def changed(self, song):
        gobject.idle_add(self.emit, 'changed', song)

    def removed(self, song):
        gobject.idle_add(self.emit, 'removed', song)

    def missing(self, song):
        self.removed(song)
        gobject.idle_add(self.emit, 'missing', song)

    def song_started(self, song):
        if song: self.set_time(0, song["~#length"] * 1000)
        else: self.set_time(0, 1)
        self.song = song
        gobject.idle_add(self.emit, 'song-started', song)

    def song_ended(self, song, stopped):
        self.changed(song)
        gobject.idle_add(self.emit, 'song-ended', song, stopped)

    def refresh(self):
        gobject.idle_add(self.emit, 'refresh')

    def set_paused(self, paused):
        if paused: gobject.idle_add(self.emit, 'paused')
        else: gobject.idle_add(self.emit, 'unpaused')

    def error(self, song):
        try: song.reload()
        except:
            library.remove(song)
            self.removed(song)
        else: self.changed(song)

gobject.type_register(SongWatcher)

# FIXME: replace with a standard About widget when using GTK 2.6.
class AboutWindow(gtk.Window):
    def __init__(self, parent=None):
        gtk.Window.__init__(self)
        self.set_title(_("About Quod Libet"))
        vbox = gtk.VBox(spacing=6)
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
        button = gtk.Button(stock=gtk.STOCK_CLOSE)
        button.connect_object('clicked', gtk.Window.destroy, self)
        vbox.pack_start(l2)
        hbox = gtk.HButtonBox()
        hbox.set_layout(gtk.BUTTONBOX_SPREAD)
        hbox.pack_start(button)
        vbox.pack_start(hbox)
        sig = gobject.timeout_add(
            4000, self.__pick_name, list(const.CREDITS), contrib)
        self.add(vbox)
        self.set_border_width(12)
        self.connect_object('destroy', AboutWindow.__destroy, self, sig)
        self.set_transient_for(parent)
        self.show_all()

    def __pick_name(self, credits, contrib):
        credits.append(credits.pop(0))
        contrib.set_text(credits[0])
        return hasattr(widgets, 'about')

    def __destroy(self, sig):
        gobject.source_remove(sig)
        try: del(widgets.about)
        except AttributeError: pass

class PreferencesWindow(gtk.Window):
    class _Pane(object):
        def _toggle(self, c, name, section="settings"):
            config.set(section, name, str(bool(c.get_active())))

        def _changed(self, cb, name):
            config.set("settings", name, str(cb.get_active()))

    class SongList(_Pane, gtk.VBox):
        def __init__(self):
            gtk.VBox.__init__(self, spacing=12)
            self.set_border_width(12)
            self.title = _("Song List")
            vbox = gtk.VBox(spacing=12)
            tips = gtk.Tooltips()

            c = gtk.CheckButton(_("_Jump to current song automatically"))
            tips.set_tip(c, _("When the playing song changes, "
                              "scroll to it in the song list"))
            c.set_active(config.state("jump"))
            c.connect('toggled', self._toggle, "jump")
            self.pack_start(c, expand=False)

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

            vbox.pack_start(table, expand=False)

            vbox2 = gtk.VBox()
            rat = gtk.CheckButton(_("Display song _rating"))
            if "~rating" in checks:
                rat.set_active(True)
                checks.remove("~rating")
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
            t.attach(rat, 1, 2, 1, 2)
            vbox.pack_start(t, expand=False)

            hbox = gtk.HBox(spacing=6)
            l = gtk.Label(_("_Others:"))
            hbox.pack_start(l, expand=False)
            others = gtk.Entry()
            others.set_text(" ".join(checks))
            tips.set_tip(others, _("List other headers you want displayed, "
                                   "separated by spaces"))
            l.set_mnemonic_widget(others)
            l.set_use_underline(True)
            hbox.pack_start(others)
            vbox.pack_start(hbox, expand=False)

            apply = qltk.Button(
                stock=gtk.STOCK_APPLY, cb=self.__apply,
                user_data=[buttons, rat, tiv, aip, fip, others])
            b = gtk.HButtonBox()
            b.set_layout(gtk.BUTTONBOX_END)
            b.pack_start(apply)
            vbox.pack_start(b)

            frame = qltk.Frame(_("Visible Columns"), bold=True, child=vbox)
            self.pack_start(frame, expand=False)

        def __apply(self, button, buttons, rat, tiv, aip, fip, others):
            headers = []
            for key in ["~#disc", "~#track", "title", "album", "artist",
                        "date", "genre", "~basename", "~length"]:
                if buttons[key].get_active(): headers.append(key)
            if rat.get_active():
                if headers and headers[-1] == "~length":
                    headers.insert(-1, "~rating")
                else: headers.append("~rating")
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
            config.set("settings", "headers", " ".join(headers))
            widgets.main.set_column_headers(headers)

    class Browsers(_Pane, gtk.VBox):
        def __init__(self):
            gtk.VBox.__init__(self, spacing=12)
            self.set_border_width(12)
            self.title = _("Browsers")
            tips = gtk.Tooltips()
            c = gtk.CheckButton(_("Color _search terms"))
            tips.set_tip(
                c, _("Display simple searches in blue, "
                     "advanced ones in green, and invalid ones in red"))
                         
            vb = gtk.VBox()
            c.set_active(config.getboolean("browsers", "color"))
            c.connect('toggled', self._toggle, "color", "browsers")
            vb.pack_start(c)

            hb = gtk.HBox(spacing=3)
            l = gtk.Label(_("_Global filter:"))
            l.set_use_underline(True)
            e = qltk.ValidatingEntry(parser.is_valid_color)
            e.set_text(config.get("browsers", "background"))
            e.connect('changed', self._entry, 'background', 'browsers')
            l.set_mnemonic_widget(e)
            hb.pack_start(l, expand=False)
            hb.pack_start(e)
            vb.pack_start(hb)

            f = qltk.Frame(_("Search Bar"), bold=True, child=vb)
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
            tips = gtk.Tooltips()
            vbox = gtk.VBox()
            c = gtk.CheckButton(_("Show _album cover images"))
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

            f = qltk.Frame(_("_On-Screen Display"), bold=True)
            cb = gtk.combo_box_new_text()
            cb.append_text(_("No on-screen display"))
            cb.append_text(_('Display OSD on the top'))
            cb.append_text(_('Display OSD on the bottom'))
            cb.set_active(config.getint('settings', 'osd'))
            cb.connect('changed', self._changed, 'osd')
            f.get_label_widget().set_mnemonic_widget(cb)
            vbox = gtk.VBox(spacing=6)
            f.child.add(vbox)
            f.child.child.pack_start(cb, expand=False)
            hb = gtk.HBox(spacing=6)
            c1, c2 = config.get("settings", "osdcolors").split()
            color1 = gtk.ColorButton(gtk.gdk.color_parse(c1))
            color2 = gtk.ColorButton(gtk.gdk.color_parse(c2))
            tips.set_tip(color1, _("Select a color for the OSD"))
            tips.set_tip(color2, _("Select a second color for the OSD"))
            color1.connect('color-set', self.__color_set, color1, color2)
            color2.connect('color-set', self.__color_set, color1, color2)
            font = gtk.FontButton(config.get("settings", "osdfont"))
            font.connect('font-set', self.__font_set)
            hb.pack_start(color1, expand=False)
            hb.pack_start(color2, expand=False)
            hb.pack_start(font)
            vbox.pack_start(hb, expand=False)
            self.pack_start(f, expand=False)

        def __font_set(self, font):
            config.set("settings", "osdfont", font.get_font_name())

        def __color_set(self, color, c1, c2):
            color = c1.get_color()
            ct1 = (color.red // 256, color.green // 256, color.blue // 256)
            color = c2.get_color()
            ct2 = (color.red // 256, color.green // 256, color.blue // 256)
            config.set("settings", "osdcolors",
                       "#%02x%02x%02x #%02x%02x%02x" % (ct1+ct2))

        def __toggle_cover(self, c):
            config.set("settings", "cover", str(bool(c.get_active())))
            if config.state("cover"): widgets.main.image.show()
            else: widgets.main.image.hide()

    class Library(_Pane, gtk.VBox):
        def __init__(self):
            gtk.VBox.__init__(self, spacing=12)
            self.set_border_width(12)
            self.title = _("Library")
            f = qltk.Frame(_("Scan _Directories"), bold=True)
            hb = gtk.HBox(spacing=6)
            b = qltk.Button(_("_Select..."), gtk.STOCK_OPEN)
            e = gtk.Entry()
            e.set_text(util.fsdecode(config.get("settings", "scan")))
            f.get_label_widget().set_mnemonic_widget(e)
            hb.pack_start(e)
            tips = gtk.Tooltips()
            tips.set_tip(e, _("On start up, any files found in these "
                              "directories will be added to your library"))
            hb.pack_start(b, expand=False)
            b.connect('clicked', self.__select, e, const.HOME)
            e.connect('changed', self._changed, 'scan')
            f.child.add(hb)
            self.pack_start(f, expand=False)

            f = qltk.Frame(_("_Masked Directories"), bold=True)
            vb = gtk.VBox(spacing=6)
            l = gtk.Label(_(
                "If you have songs in directories that will not always be "
                "mounted (for example, a removable device or an NFS shared "
                "drive), list those mount points here. Files in these "
                "directories will not be removed from the library if the "
                "device is not mounted."))
            l.set_line_wrap(True)
            l.set_justify(gtk.JUSTIFY_FILL)
            vb.pack_start(l, expand=False)
            hb = gtk.HBox(spacing=6)
            b = qltk.Button(_("_Select..."), gtk.STOCK_OPEN)
            e = gtk.Entry()
            e.set_text(util.fsdecode(config.get("settings", "masked")))
            f.get_label_widget().set_mnemonic_widget(e)
            hb.pack_start(e)
            hb.pack_start(b, expand=False)
            vb.pack_start(hb, expand=False)
            if os.path.exists("/media"): dir = "/media"
            elif os.path.exists("/mnt"): dir = "/mnt"
            else: dir = "/"
            b.connect('clicked', self.__select, e, dir)
            e.connect('changed', self._changed, 'masked')
            f.child.add(vb)
            self.pack_start(f, expand=False)

            f = qltk.Frame(_("Tag Editing"), bold=True)
            vbox = gtk.VBox(spacing=6)
            hb = gtk.HBox(spacing=6)
            e = gtk.Entry()
            e.set_text(config.get("settings", "splitters"))
            e.connect('changed', self._changed, 'splitters')
            tips.set_tip(
                e, _('These characters will be used as separators '
                     'when "Split values" is selected in the tag editor'))
            l = gtk.Label(_("Split _on:"))
            l.set_use_underline(True)
            l.set_mnemonic_widget(e)
            hb.pack_start(l, expand=False)
            hb.pack_start(e)
            cb = gtk.CheckButton(_("Show _programmatic comments"))
            cb.set_active(config.state("allcomments"))
            cb.connect('toggled', self._toggle, 'allcomments')
            vbox.pack_start(hb, expand=False)
            vbox.pack_start(cb, expand=False)
            f.child.add(vbox)
            self.pack_start(f)

        def __select(self, button, entry, initial):
            chooser = FileChooser(self.parent.parent.parent,
                                  _("Select Directories"), initial)
            resp, fns = chooser.run()
            chooser.destroy()
            if resp == gtk.RESPONSE_OK:
                entry.set_text(":".join(map(util.fsdecode, fns)))

        def _changed(self, entry, name):
            config.set('settings', name,
                       util.fsencode(entry.get_text().decode('utf-8')))

    def __init__(self, parent):
        gtk.Window.__init__(self)
        self.set_title(_("Quod Libet Preferences"))
        self.set_border_width(12)
        self.set_resizable(False)
        self.set_transient_for(parent)
        self.add(gtk.VBox(spacing=12))
        tips = gtk.Tooltips()
        n = qltk.Notebook()
        n.append_page(self.SongList())
        n.append_page(self.Browsers())
        n.append_page(self.Player())
        n.append_page(self.Library())

        self.child.pack_start(n)

        bbox = gtk.HButtonBox()
        bbox.set_layout(gtk.BUTTONBOX_END)
        button = gtk.Button(stock=gtk.STOCK_CLOSE)
        button.connect_object('clicked', gtk.Window.destroy, self)
        bbox.pack_start(button)
        self.connect_object('destroy', PreferencesWindow.__destroy, self)
        self.child.pack_start(bbox, expand=False)
        self.child.show_all()

    def __destroy(self):
        del(widgets.preferences)
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
            b = qltk.Button(_("_Move to Trash"), image = gtk.STOCK_DELETE)
            self.add_action_widget(b, 0)

        self.add_button(gtk.STOCK_CANCEL, 1)
        self.add_button(gtk.STOCK_DELETE, 2)

        hbox = gtk.HBox()
        hbox.set_border_width(6)
        i = gtk.Image()
        i.set_from_stock(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_DIALOG)
        i.set_padding(12, 0)
        i.set_alignment(0.5, 0.0)
        hbox.pack_start(i, expand=False)
        vbox = gtk.VBox(spacing=6)
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
        lab.set_alignment(0.0, 0.5)
        vbox.pack_start(lab, expand=False)

        lab = gtk.Label("\n".join(
            map(util.fsdecode, map(util.unexpand, files))))
        lab.set_alignment(0.1, 0.0)
        exp.add(gtk.ScrolledWindow())
        exp.child.add_with_viewport(lab)
        exp.child.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        exp.child.child.set_shadow_type(gtk.SHADOW_NONE)
        vbox.pack_start(exp)
        hbox.pack_start(vbox)
        self.vbox.pack_start(hbox)
        self.vbox.show_all()

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
            print to(_("Initialized status icon."))

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
        self.__plname = PlayList.normalize_name(name)
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
        self.set_destroy_with_parent(True)
        self.set_default_size(400, 400)
        self.set_border_width(12)

        vbox = gtk.VBox(spacing=6)
        self.add(vbox)

        self.__view = view = PlayList(name)
        bar = SearchBar(self.__add_query_results, gtk.STOCK_ADD, save=False)
        vbox.pack_start(bar, expand=False, fill=False)

        hbox = gtk.HButtonBox()
        hbox.set_layout(gtk.BUTTONBOX_END)
        vbox.pack_end(hbox, expand=False)
        vbox.pack_end(gtk.HSeparator(), expand=False)

        close = qltk.Button(stock=gtk.STOCK_CLOSE)
        hbox.pack_end(close, expand=False)

        swin = gtk.ScrolledWindow()
        swin.set_shadow_type(gtk.SHADOW_IN)
        swin.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        vbox.pack_start(swin)

        swin.add(view)

        self.set_name(name)
        self.connect_object('destroy', self.__destroy, view)
        close.connect_object('clicked', gtk.Window.destroy, self)
        self.show_all()

    def __add_query_results(self, text, sort):
        query = text.decode('utf-8').strip()
        try:
           songs = library.query(query)
           songs.sort()
           self.__view.append_songs(songs)
        except ValueError: pass

# A tray icon aware of UI policy -- left click shows/hides, right
# click makes a callback.
class HIGTrayIcon(TrayIcon):
    def __init__(self, pixbuf, window, cbs={}):
        self.__window = window
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
        playpause = gtk.ImageMenuItem(gtk.STOCK_MEDIA_PLAY)
        playpause.connect('activate', self.__playpause)

        previous = gtk.ImageMenuItem(gtk.STOCK_MEDIA_PREVIOUS)
        previous.connect('activate', lambda *args: player.playlist.previous())
        next = gtk.ImageMenuItem(gtk.STOCK_MEDIA_NEXT)
        next.connect('activate', lambda *args: player.playlist.next())

        props = gtk.ImageMenuItem(gtk.STOCK_PROPERTIES)
        props.connect('activate', self.__properties)

        quit = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        quit.connect('activate', gtk.main_quit)

        for item in [playpause, gtk.SeparatorMenuItem(), previous, next,
                     gtk.SeparatorMenuItem(), props, gtk.SeparatorMenuItem(),
                     quit]: menu.append(item)

        menu.show_all()

        widgets.watcher.connect('song-started', self.__set_song, next, props)
        widgets.watcher.connect('paused', self.__set_paused, menu, True)
        widgets.watcher.connect('unpaused', self.__set_paused, menu, False)

        cbs = {
            2: lambda *args: self.__playpause(args[0]),
            3: lambda ev, *args:
            tray_menu.popup(None, None, None, ev.button, ev.time),
            4: lambda *args: volume.set_value(volume.get_value()-0.05),
            5: lambda *args: volume.set_value(volume.get_value()+0.05),
            6: lambda *args: player.playlist.next(),
            7: lambda *args: player.playlist.previous()
            }

        p = gtk.gdk.pixbuf_new_from_file_at_size("quodlibet.png", 16, 16)

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
        if widgets.watcher.song: SongProperties([self.__song])

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
            print to(_("Initialized multimedia key support."))

class Osd(object):
    def __init__(self):
        try: import gosd
        except: pass
        else:
            self.__gosd = gosd
            self.__level = 0
            self.__window = None
            widgets.watcher.connect('song-started', self.__show_osd)

    def __show_osd(self, watcher, song):
        if song is None or config.getint("settings", "osd") == 0: return
        color1, color2 = config.get("settings", "osdcolors").split()
        font = config.get("settings", "osdfont")

        if self.__window: self.__window.destroy()

        # \xe2\x99\xaa is a music note.
        msg = "\xe2\x99\xaa "

        msg += "<span foreground='%s' style='italic'>%s</span>" %(
            color2, util.escape(song("~title~version")))
        msg += " <span size='small'>(%s)</span> " % song("~length")
        msg += "\xe2\x99\xaa\n"

        msg += "<span size='x-small'>"
        for key in ["artist", "album", "tracknumber"]:
            if key in song:
                msg += ("<span foreground='%s' size='xx-small' "
                        "style='italic'>%s</span> %s   "%(
                    (color2, tag(key), util.escape(song.comma(key)))))
        msg = msg.strip() + "</span>"
        if isinstance(msg, unicode):
            msg = msg.encode("utf-8")

        self.__window = self.__gosd.osd(msg, "black", color1, font)
        if config.getint("settings", "osd") == 1:
            self.__window.move(
                gtk.gdk.screen_width()/2 - self.__window.width/2, 5)
        else:
            self.__window.move(
                gtk.gdk.screen_width()/2 - self.__window.width/2,
                gtk.gdk.screen_height() - self.__window.height-48)
        self.__window.show()
        self.__level += 1
        gobject.timeout_add(7500, self.__unshow)

    def __unshow(self):
        self.__level -= 1
        if self.__level == 0 and self.__window:
            self.__window.destroy()
            self.__window = None

class Browser(object):
    expand = False # Packing options
    background = False # Use browsers/filter as a background filter

    # called when the library has been updated (new/removed/edited songs)
    def update(self): pass

    # read/write from config data
    def restore(self): pass
    def save(self): pass

    # decides whether "filter on foo" menu entries are available
    def can_filter(self, key):
        return False

class PanedBrowser(Browser, gtk.VBox):
    expand = True
    
    class Pane(gtk.ScrolledWindow):
        def __init__(self, mytag, next):
            gtk.ScrolledWindow.__init__(self)
            self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
            self.set_shadow_type(gtk.SHADOW_IN)
            self.add(gtk.TreeView(gtk.ListStore(str)))
            render = gtk.CellRendererText()
            column = gtk.TreeViewColumn(tag(mytag), render, markup = 0)
            column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
            column.set_fixed_width(50)
            self.child.append_column(column)
            self.tag = mytag
            self.__next = next
            self.__songs = []
            self.__selected_items = []
            self.child.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
            self.child.connect_object('destroy', self.child.set_model, None)
            self.__sig = self.child.get_selection().connect(
                'changed', self.__selection_changed)
            self.child.connect_object(
                'row-activated', PanedBrowser.Pane.__play_selection, self)

        def __play_selection(self, indices, col):
            player.playlist.next()
            player.playlist.reset()

        def __selection_changed(self, selection, check=True, jump=False):
            if check: # verify we've actually changed...
                model, rows = selection.get_selected_rows()
                selected_items = [model[row][0] for row in rows]
                if rows == []: rows = [(0,)]
                if self.__selected_items == selected_items: return
                else: self.__selected_items = selected_items
            else:
                model, rows = selection.get_selected_rows()
                self.__selected_items = [model[row][0] for row in rows]
            if jump:
                model, rows = selection.get_selected_rows()
                if rows: self.child.scroll_to_cell(rows[0])
            # pass on the remaining songs to the next pane
            self.__next.fill(
                filter(parser.parse(self.query()).search, self.__songs))

        def select(self, values, escape=True):
            selection = self.child.get_selection()
            selection.handler_block(self.__sig)
            selection.unselect_all()
            model = selection.get_tree_view().get_model()
            if values == []: selection.select_path((len(model) - 1,))
            elif values is None: selection.select_path((0,))
            else:
                if escape:
                    values = [util.escape(v.encode('utf-8')) for v in values]
                def select_values(model, path, iter):
                    if model[path][0] in values:
                        selection.select_path(path)
                model.foreach(select_values)
            selection.handler_unblock(self.__sig)
            self.__selection_changed(selection, check=False, jump=True)

        def fill(self, songs, handle_pending=True):
            self.__songs = songs
            # get values from song list
            complete = True
            values = set()
            for song in songs:
                l = song.list(self.tag)
                values.update(l)
                complete = complete and bool(l)
            values = list(values); values.sort()

            # record old selection data to preserve as much as possible
            selection = self.child.get_selection()
            selection.handler_block(self.__sig)
            model, rows = selection.get_selected_rows()
            selected_items = [model[row][0] for row in rows]
            # fill in the new model
            model = self.child.get_model()
            model.clear()
            to_select = []
            if len(values) + (not bool(complete)) > 1:
                model.append(["<b>%s</b>" % _("All")])
            for i, value in enumerate(map(util.escape, values)):
                model.append([value])
                if value in selected_items: to_select.append(i + 1)
            if not complete:
                model.append(["<b>%s</b>" % _("Unknown")])
            if to_select == []: to_select = [0]
            for i in to_select: selection.select_path((i,))
            selection.handler_unblock(self.__sig)
            self.__selection_changed(selection, check=False, jump=True)

        def query(self):
            selection = self.child.get_selection()
            model, rows = selection.get_selected_rows()
            if rows == [] or rows[0][0] == 0: # All
                return "%s = /.?/" % self.tag
            else:
                selected = ["/^%s$/c"%sre.escape(util.unescape(model[row][0]))
                            for row in rows]
                if model[rows[-1]][0].startswith("<b>"): # Not All, so Unknown
                    selected.pop()
                    selected.append("!/./")
                return ("%s = |(%s)" %(
                    self.tag, ", ".join(selected))).decode("utf-8")

    def __init__(self, cb):
        gtk.VBox.__init__(self, spacing=0)
        self.__cb = cb
        hbox = gtk.HBox(spacing=6)
        c = gtk.CheckButton(_("_Global filter:"))
        e = qltk.ValidatingEntry(parser.is_valid_color)
        e.set_text(config.get("browsers", "background"))
        e.set_sensitive(False)
        e.connect('changed', self.__filter_changed)
        c.connect('toggled', self.__filter_toggled, e)
        hbox.pack_start(c, expand=False)
        hbox.pack_start(e)
        a = gtk.Alignment(xalign=1.0, xscale=0.3)
        a.add(hbox)
        self.__refill_sig = 0

        self.pack_start(a, expand=False)
        self.refresh_panes(restore=False)

    def __filter_toggled(self, toggle, entry):
        self.background = toggle.get_active()
        entry.set_text(config.get("browsers", "background"))
        entry.set_sensitive(toggle.get_active())
        if entry.get_text():
            if not self.background: self.__panes[0].fill(library.values())
            else: self.__filter_changed(entry)

    def __filter_changed(self, entry):
        self.__refill_sig += 1
        gobject.timeout_add(
            500, self.__refill_panes_timeout, entry, self.__refill_sig)

    def __refill_panes_timeout(self, entry, id):
        if id == self.__refill_sig:
            filter = entry.get_text().strip()
            if parser.is_parsable(filter.decode('utf-8')):
                entry.set_position(10000) # at the end
                config.set("browsers", "background", filter)
                values = library.query(filter.decode('utf-8'))
                self.__panes[0].fill(values)

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
        map(hbox.pack_start, self.__panes)
        self.pack_start(hbox)
        self.__inhibit = True
        filter = config.get("browsers", "background")
        if not (self.background and filter and parser.is_parsable(filter)):
            values = library.values()
        else: values = library.query(filter)
        self.__panes[0].fill(values)
        if restore: self.restore()
        self.show_all()

    def can_filter(self, key):
        return key in [pane.tag for pane in self.__panes]

    def filter(self, key, values):
        for pane in self.__panes:
            self.__inhibit = True
            pane.select(None)

        pane = self.__panes[[pane.tag for pane in self.__panes].index(key)]
        pane.select(values)

    def save(self):
        selected = []
        for pane in self.__panes:
            selection = pane.child.get_selection()
            model, rows = selection.get_selected_rows()
            selected.append("\t".join([model[row][0] for row in rows]))
        config.set("browsers", "pane_selection", "\n".join(selected))

    def restore(self):
        try:
            selections = [y.split("\t") for y in
                          config.get("browsers", "pane_selection").split("\n")]
        except: pass
        else:
            if len(selections) == len(self.__panes):
                for sel, pane in zip(selections, self.__panes):
                    self.__inhibit = True
                    pane.select(sel, escape=False)

    def activate(self):
        self.fill(None)

    def update(self):
        self.__inhibit = True
        self.__panes[0].fill(library.values())
        for p in self.__panes:
            self.__inhibit = True
            p.select("<not in list>", False)

    def fill(self, songs):
        if self.__inhibit: self.__inhibit = False
        else:
            self.save()
            self.__cb(
                "&(%s)" % ", ".join(map(self.Pane.query, self.__panes)), None)

class PlaylistBar(Browser, gtk.HBox):
    def __init__(self, cb):
        gtk.HBox.__init__(self)
        combo = gtk.ComboBox(PlayList.lists_model())
        cell = gtk.CellRendererText()
        combo.pack_start(cell, True)
        combo.add_attribute(cell, 'text', 0)
        combo.set_active(0)
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
        edit.connect_object('clicked', self.__edit_current, combo)
        combo.connect('changed', self.__list_selected, edit, refresh)
        refresh.connect_object(
            'clicked', self.__list_selected, combo, edit, refresh)

        self.__cb = cb
        tips = gtk.Tooltips()
        tips.set_tip(edit, _("Edit the current playlist"))
        tips.set_tip(refresh, _("Refresh the current playlist"))
        self.show_all()
        self.connect_object(
            'destroy', gtk.ComboBoxEntry.set_model, combo, None)

    def save(self):
        combo = self.get_children()[0]
        active = combo.get_active()
        key = combo.get_model()[active][1]
        config.set("browsers", "playlist", key)

    def restore(self):
        try: key = config.get("browsers", "playlist")
        except Exception: pass
        else:
            combo = self.get_children()[0]
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
        edit.set_sensitive(active != 0)
        refresh.set_sensitive(active != 0)
        self.save()
        if active == 0:
            self.__cb("", None)
        else:
            playlist = "playlist_" + combo.get_model()[active][1]
            self.__cb("#(%s > 0)" % playlist, "~#"+playlist)

    def __edit_current(self, combo):
        active = combo.get_active()
        if active > 0: PlaylistWindow(combo.get_model()[active][0])

class CoverImage(gtk.Frame):
    def __init__(self, size=None):
        gtk.Frame.__init__(self)
        self.add(gtk.EventBox())
        self.child.add(gtk.Image())
        self.__size = size or [100, 100]
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

class EmptyBar(Browser, gtk.HBox):
    background = True
    
    def __init__(self, cb):
        gtk.HBox.__init__(self)
        self._text = ""
        self._cb = cb

    def set_text(self, text):
        self._text = text

    def save(self):
        config.set("browsers", "query_text", self._text)

    def restore(self):
        try: self.set_text(config.get("browsers", "query_text"))
        except Exception: pass

    def activate(self):
        self._cb(self._text, None)
        self.save()

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
    def __init__(self, cb, button=gtk.STOCK_FIND, save=True):
        EmptyBar.__init__(self, cb)
        self.__save = save

        tips = gtk.Tooltips()
        combo = qltk.ComboBoxEntrySave(
            const.QUERIES, model="searchbar", count=15)
        clear = gtk.Button()
        clear.add(gtk.image_new_from_stock(gtk.STOCK_CLEAR,gtk.ICON_SIZE_MENU))
        tips.set_tip(clear, _("Clear search text"))
        clear.connect('clicked', self.__clear, combo)
                  
        search = gtk.Button()
        b = gtk.HBox(spacing=2)
        b.pack_start(gtk.image_new_from_stock(button, gtk.ICON_SIZE_MENU))
        b.pack_start(gtk.Label(_("Search")))
        search.add(b)
        tips.set_tip(search, _("Search your audio library"))
        search.connect_object('clicked', self.__text_parse, combo.child)
        combo.child.connect('activate', self.__text_parse)
        combo.child.connect('changed', self.__test_filter)
        self.pack_start(combo)
        self.pack_start(clear, expand=False)
        self.pack_start(search, expand=False)
        self.show_all()

    def __clear(self, button, combo):
        combo.child.set_text("")

    def activate(self):
        self.get_children()[-1].clicked()

    def set_text(self, text):
        self.get_children()[0].child.set_text(text)
        self._text = text

    def __text_parse(self, entry):
        text = entry.get_text()
        if (parser.is_valid(text) or ("#" not in text and "=" not in text)):
            self._text = text
            self.get_children()[0].prepend_text(text)
        self._cb(text, None)
        if self.__save: self.save()
        self.get_children()[0].write(const.QUERIES)

    def __test_filter(self, textbox):
        if not config.getboolean('browsers', 'color'): return
        text = textbox.get_text()
        gobject.idle_add(
            self.__set_entry_color, textbox, parser.is_valid_color(text))

    # Set the color of some text.
    def __set_entry_color(self, entry, color):
        layout = entry.get_layout()
        text = layout.get_text()
        markup = '<span foreground="%s">%s</span>' %(
            color, util.escape(text))
        layout.set_markup(markup)

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
            self.set_size_request(100, -1)
            self.set_alignment(0.0, 0.0)
            self.set_padding(3, 3)
            widgets.watcher.connect('song-started', self.__song_started)
            widgets.watcher.connect('changed', self.__check_change)

        def __check_change(self, watcher, song):
            if song is watcher.song: self.__song_started(watcher, song)

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
            chooser = FileChooser(
                widgets.main, _("Add Music"), widgets.main.last_dir)
            resp, fns = chooser.run()
            chooser.destroy()
            if resp == gtk.RESPONSE_OK: widgets.main.scan_dirs(fns)
            if fns: widgets.main.last_dir = fns[0]
            library.save(const.LIBRARY)

        def __properties(self, button):
            if widgets.watcher.song:
                SongProperties([widgets.watcher.song])

        def __website(self, button):
            song = widgets.watcher.song
            if not song: return
            site = song.website().replace("\\", "\\\\").replace("\"", "\\\"")
            for s in (["sensible-browser"] +
                      os.environ.get("BROWSER","").split(":")):
                if util.iscommand(s):
                    if "%s" in s:
                        s = s.replace("%s", '"' + site + '"')
                        s = s.replace("%%", "%")
                    else: s += " \"%s\"" % site
                    print to(_("Opening web browser: %s") % s)
                    if os.system(s + " &") == 0: break
                else:
                    qltk.ErrorMessage(
                        widgets.main, _("Unable to start a web browser"),
                        _("A web browser could not be found. Please set "
                          "your $BROWSER variable, or make sure "
                          "/usr/bin/sensible-browser exists.")).run()

    class PositionSlider(gtk.HBox):
        __gsignals__ = {
            'seek': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (int,))
            }
                    
        def __init__(self):
            gtk.HBox.__init__(self)
            l = gtk.Label("0:00/0:00")
            l.set_padding(6, 0)
            self.pack_start(l, expand=False)
            scale = gtk.HScale(gtk.Adjustment(0, 0, 0, 3600, 15000, 0))
            scale.set_update_policy(gtk.UPDATE_DELAYED)
            scale.connect_object('adjust-bounds', self.emit, 'seek')
            scale.set_draw_value(False)
            self.pack_start(scale)

            widgets.watcher.connect(
                'song-started', self.__song_changed, scale, l)

            gobject.timeout_add(200, self.__update_time, scale, l)

        def __song_changed(self, watcher, song, position, label):
            if song:
                length = song["~#length"]
                position.set_range(0, length * 1000)
            else: position.set_range(0, 1)

        def __update_time(self, position, timer):
            cur, end = widgets.watcher.time
            position.set_value(cur)
            timer.set_text(
                "%d:%02d/%d:%02d" %
                (cur // 60000, (cur % 60000) // 1000,
                 end // 60000, (end % 60000) // 1000))
            return True

    gobject.type_register(PositionSlider)

    def __init__(self):
        gtk.Window.__init__(self)
        self.last_dir = os.path.expanduser("~")

        tips = gtk.Tooltips()
        self.set_title("Quod Libet")
        self.set_icon_from_file("quodlibet.png")
        self.set_default_size(
            *map(int, config.get('memory', 'size').split()))
        self.add(gtk.VBox())
        self.connect('configure-event', MainWindow.save_size)
        self.connect('destroy', gtk.main_quit)
        self.connect('delete-event', MainWindow.__delete_event)

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
        hb2.pack_start(text)

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
        vbox = gtk.VBox()
        p = gtk.gdk.pixbuf_new_from_file("volume.png")
        i = gtk.Image()
        i.set_from_pixbuf(p)
        vbox.pack_start(i, expand=False)
        adj = gtk.Adjustment(1, 0, 1, 0.01, 0.1)
        self.volume = gtk.VScale(adj)
        self.volume.set_update_policy(gtk.UPDATE_CONTINUOUS)
        self.volume.connect('value-changed', self.update_volume)
        adj.set_value(config.getfloat('memory', 'volume'))
        self.volume.set_draw_value(False)
        self.volume.set_inverted(True)
        tips.set_tip(self.volume, _("Adjust audio volume"))
        vbox.pack_start(self.volume)
        hbox.pack_start(vbox, expand=False)

        self.child.pack_start(hbox, expand=False)

        # status area
        hbox = gtk.HBox(spacing=6)
        self.shuffle = shuffle = gtk.CheckButton(_("_Shuffle"))
        tips.set_tip(shuffle, _("Play songs in a random order"))
        shuffle.connect('toggled', self.toggle_shuffle)
        shuffle.set_active(config.getboolean('settings', 'shuffle'))
        hbox.pack_start(shuffle, expand = False)
        self.repeat = repeat = gtk.CheckButton(_("_Repeat"))
        repeat.connect('toggled', self.toggle_repeat)
        repeat.set_active(config.getboolean('settings', 'repeat'))
        tips.set_tip(
            repeat, _("Restart the playlist after all songs are played"))
        hbox.pack_start(repeat, expand=False)
        self.__statusbar = gtk.Label()
        self.__statusbar.set_text(_("No time information"))
        self.__statusbar.set_alignment(1.0, 0.5)
        self.__statusbar.set_justify(gtk.JUSTIFY_RIGHT)
        hbox.pack_start(self.__statusbar)
        hbox.set_border_width(3)
        self.child.pack_end(hbox, expand=False)

        # Set up the tray icon. It gets created even if we don't
        # actually use it (e.g. missing trayicon.so).
        p = gtk.gdk.pixbuf_new_from_file_at_size("quodlibet.png", 16, 16)
        self.icon = QLTrayIcon(self, self.volume)

        # song list
        self.song_scroller = sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        sw.set_shadow_type(gtk.SHADOW_IN)
        self.songlist = MainSongList()
        self.songlist.set_rules_hint(True)
        self.songlist.set_size_request(200, 150)
        sw.add(self.songlist)
        self.songlist.set_model(gtk.ListStore(object))
        self.set_column_headers(config.get("settings", "headers").split())
        sort = config.get('memory', 'sortby')
        self.songlist.set_sort_by(
            None, sort[1:], refresh=True, order=int(sort[0]))
        self.child.pack_end(sw)
        self.songlist.connect('row-activated', self.select_song)
        self.songlist.connect('button-press-event', self.songs_button_press)
        self.songlist.connect('popup-menu', self.songs_popup_menu)
        self.songlist.connect('columns_changed', self.cols_changed)

        # plugin support
        from plugins import PluginManager
        self.__pm = PluginManager(widgets.watcher, [const.PLUGINS])
        self.__pm.rescan()
        
        self.browser = None
        self.select_browser(self, config.getint("memory", "browser"))
        self.browser.restore()
        self.browser.activate()

        self.open_fifo()
        self.keys = MmKeys({"mm_prev": self.previous_song,
                            "mm_next": self.next_song,
                            "mm_playpause": self.play_pause})

        self.child.show_all()
        self.showhide_playlist(self.ui.get_widget("/Menu/View/Songlist"))

        widgets.watcher.connect('removed', self.__song_removed)
        widgets.watcher.connect('changed', self.__update_title)
        widgets.watcher.connect('refresh', self.__update_browser)
        widgets.watcher.connect('song-started', self.__song_started)
        widgets.watcher.connect('song-ended', self.__song_ended)
        widgets.watcher.connect(
            'missing', self.__song_missing, self.__statusbar)
        widgets.watcher.connect('paused', self.__update_paused, True)
        widgets.watcher.connect('unpaused', self.__update_paused, False)

        self.show()

    def __delete_event(self, event):
        if self.icon.enabled and config.getboolean("plugins", "icon_close"):
            self.icon.hide_window()
            return True

    def _create_menu(self, tips):
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
             lambda *args: self.destroy()),

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
            ("BrowserPlaylist", None, _("_Playlists"), None, None, 2),
            ("BrowserPaned", None, _("_Paned browser"), None, None, 3)
            ], config.getint("memory", "browser"), self.select_browser)

        
        self.ui = gtk.UIManager()
        self.ui.insert_action_group(ag, 0)
        self.ui.add_ui_from_string(const.MENU)

        # Cute. So. UIManager lets you attach tooltips, but when they're
        # for menu items, they just get ignored. So here I get to actually
        # attach them.
        tips.set_tip(
            self.ui.get_widget("/Menu/Music/RefreshLibrary"),
            _("Check for changes in the library made since the program "
              "was started"))
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

    def select_browser(self, activator, current):
        if not isinstance(current, int): current = current.get_current_value()
        config.set("memory", "browser", str(current))
        Browser = [EmptyBar, SearchBar, PlaylistBar, PanedBrowser][current]
        if self.browser: self.browser.destroy()
        self.browser = Browser(self.__browser_cb)
        self.child.pack_start(self.browser, self.browser.expand)
        self.__hide_menus()

    def open_fifo(self):
        try:
            if not os.path.exists(const.CONTROL):
                util.mkdir(const.DIR)
                os.mkfifo(const.CONTROL, 0600)
            self.fifo = os.open(const.CONTROL, os.O_NONBLOCK)
            gobject.io_add_watch(
                self.fifo, gtk.gdk.INPUT_READ, self._input_check)
        except (IOError, OSError): pass

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
            if not self.get_property('visible'):
                self.move(*self.window_pos)
            self.present()
        elif c == "q": self.make_query(os.read(source, 4096))
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
        statusbar.set_text(_("Could not play %s.") % song['~filename'])
        try: library.remove(song)
        except KeyError: pass
        else: watcher.removed(song)

    def __song_ended(self, watcher, song, stopped):
        if player.playlist.filter and not player.playlist.filter(song):
            player.playlist.remove(song)
            iter = self.songlist.song_to_iter(song)
            if iter: self.songlist.get_model().remove(iter)

    def __update_title(self, watcher, song):
        if song is watcher.song:
            if song:
                self.set_title("Quod Libet - " + song.comma("~title~version"))
            else: self.set_title("Quod Libet")

    def __song_started(self, watcher, song):
        self.__update_title(watcher, song)

        for wid in ["Jump", "Next", "Properties", "FilterGenre",
                    "FilterArtist", "FilterAlbum"]:
            self.ui.get_widget('/Menu/Song/' + wid).set_sensitive(bool(song))
        if song:
            for h in ['genre', 'artist', 'album']:
                self.ui.get_widget(
                    "/Menu/Song/Filter%s" % h.capitalize()).set_sensitive(
                    h in song)
        col = 0
        def update_if_last_or_current(model, path, iter):
            this_song = model[iter][col]
            if this_song is song:
                model.row_changed(path, iter)

        self.songlist.get_model().foreach(update_if_last_or_current)
        if song and config.getboolean("settings", "jump"):
            self.jump_to_current()

    def save_size(self, event):
        config.set("memory", "size", "%d %d" % (event.width, event.height))

    def new_playlist(self, activator):
        options = map(PlayList.prettify_name, library.playlists())
        name = GetStringDialog(self, _("New Playlist..."),
                               _("Enter a name for the new playlist. If it "
                                 "already exists it will be opened for "
                                 "editing."), options).run()
        if name:
            PlaylistWindow(name)

    def showhide_widget(self, box, on):
        if on and box.get_property('visible'): return
        width, height = self.get_size()
        if on:
            box.show()
            dy = box.get_allocation().height
            self.set_geometry_hints(None,
                max_height = -1, min_height = -1, max_width = -1)
            self.resize(width, height + dy)
            box.set_size_request(-1, -1)
        else:
            dy = box.get_allocation().height
            box.hide()
            self.resize(width, height - dy)
            box.set_size_request(-1, dy)
        if not box.get_property("visible"):
            self.set_geometry_hints(
                None, max_height = height - dy, max_width = 32000)
        self.realize()

    def showhide_playlist(self, toggle):
        self.showhide_widget(self.song_scroller, toggle.get_active())
        config.set("memory", "songlist", str(toggle.get_active()))

    def play_pause(self, *args):
        if widgets.watcher.song is None: player.playlist.reset()
        else: player.playlist.paused ^= True

    def jump_to_current(self, *args):
        song = widgets.watcher.song
        try: path = (player.playlist.get_playlist().index(song),)
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
            widgets.about = AboutWindow(self)
        widgets.about.present()

    def toggle_shuffle(self, button):
        player.playlist.shuffle = button.get_active()
        config.set("settings", "shuffle", str(bool(button.get_active())))

    def __random(self, key):
        if self.browser.can_filter(key):
            value = library.random(key)
            if value is not None: self.browser.filter(key, [value])

    def random_artist(self, menuitem): self.__random('artist')
    def random_album(self, menuitem): self.__random('album')
    def random_genre(self, menuitem): self.__random('genre')

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

    def rebuild(self, activator, hard=False):
        window = qltk.WaitLoadWindow(self, len(library) // 7,
                                     _("Quod Libet is scanning your library. "
                                       "This may take several minutes.\n\n"
                                       "%d songs reloaded\n%d songs removed"),
                                     (0, 0))
        iter = 7
        c = r = 0
        for c, r in library.rebuild(hard):
            if iter == 7:
                if window.step(c, r):
                    window.destroy()
                    break
                iter = 0
            iter += 1
        else:
            window.destroy()
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
            widgets.preferences = PreferencesWindow(self)
        widgets.preferences.present()

    def select_song(self, tree, indices, col):
        model = self.songlist.get_model()
        iter = model.get_iter(indices)
        song = model.get_value(iter, 0)
        player.playlist.go_to(song)
        player.playlist.paused = False

    def open_chooser(self, *args):
        chooser = FileChooser(self, _("Add Music"), self.last_dir)
        resp, fns = chooser.run()
        chooser.destroy()
        if resp == gtk.RESPONSE_OK: self.scan_dirs(fns)
        if fns: self.last_dir = fns[0]
        library.save(const.LIBRARY)

    def scan_dirs(self, fns):
        win = qltk.WaitLoadWindow(self, 0,
                                  _("Quod Libet is scanning for new songs and "
                                    "adding them to your library.\n\n"
                                    "%d songs added"), 0)
        for added, changed in library.scan(fns):
            if win.step(added): break
        win.destroy()
        player.playlist.refilter()
        self.refresh_songlist()
        self.browser.update()

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
        view = self.songlist
        path, col = view.get_cursor()
        header = col.header_name
        if "~" in header[1:]: header = filter(None, header.split("~"))[0]
        self.__filter_on(header)

    def cur_artist_filter(self, item):
        self.__filter_on('artist', [widgets.watcher.song])
    def cur_album_filter(self, item):
        self.__filter_on('album', [widgets.watcher.song])
    def cur_genre_filter(self, item):
        self.__filter_on('genre', [widgets.watcher.song])

    def remove_song(self, item):
        view = self.songlist
        selection = view.get_selection()
        model, rows = selection.get_selected_rows()
        iters = [model.get_iter(row) for row in rows]
        for iter in iters:
            song = model[iter][0]
            library.remove(song)
            widgets.watcher.removed(song)
        widgets.watcher.refresh()

    def __update_browser(self, watcher):
        self.browser.update()

    def __song_removed(self, watcher, song):
        player.playlist.remove(song)

    def delete_song(self, item):
        view = self.songlist
        selection = view.get_selection()
        model, rows = selection.get_selected_rows()
        songs = [(model[r][0]["~filename"], model[r][0],
                  model.get_iter(r)) for r in rows]
        d = DeleteDialog(self, [song[0] for song in songs])
        resp = d.run()
        d.destroy()
        if resp == 1 or resp == gtk.RESPONSE_DELETE_EVENT: return
        else:
            if resp == 0: s = _("Moving %d/%d.")
            elif resp == 2: s = _("Deleting %d/%d.")
            else: return
            w = qltk.WaitLoadWindow(self, len(songs), s, (0, len(songs)))
            trash = os.path.expanduser("~/.Trash")
            for filename, song, iter in songs:
                try:
                    if resp == 0:
                        basename = os.path.basename(filename)
                        shutil.move(filename, os.path.join(trash, basename))
                    else:
                        os.unlink(filename)
                    library.remove(song)
                    widgets.watcher.removed(song)

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
            self.browser.update()

    def current_song_prop(self, *args):
        song = widgets.watcher.song
        if song: SongProperties([song])

    def song_properties(self, item):
        SongProperties(self.songlist.get_selected_songs())

    def set_selected_ratings(self, item, value):
        for song in self.songlist.get_selected_songs():
            song["~#rating"] = value
            widgets.watcher.changed(song)

    def prep_main_popup(self, header, button, time):
        if "~" in header[1:]: header = header.lstrip("~").split("~")[0]
        menu = gtk.Menu()

        if header == "~rating":
            item = gtk.MenuItem(_("Set rating..."))
            m2 = gtk.Menu()
            item.set_submenu(m2)
            for i in [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4]:
                itm = gtk.MenuItem("%0.1f\t%s" %(
                    i, util.format_rating(i)))
                m2.append(itm)
                itm.connect('activate', self.set_selected_ratings, i)
            menu.append(item)
            menu.append(gtk.SeparatorMenuItem())

        songs = self.songlist.get_selected_songs()

        if self.browser.can_filter("artist"):
            b = gtk.ImageMenuItem(_("Filter on _artist"))
            b.connect_object('activate', self.__filter_on, 'artist', songs)
            b.get_image().set_from_stock(gtk.STOCK_INDEX, gtk.ICON_SIZE_MENU)
            menu.append(b)
        if self.browser.can_filter("album"):
            b = gtk.ImageMenuItem(_("Filter on al_bum"))
            b.connect_object('activate', self.__filter_on, 'album', songs)
            b.get_image().set_from_stock(gtk.STOCK_INDEX, gtk.ICON_SIZE_MENU)
            menu.append(b)
        header = {"~rating":"~#rating", "~length":"~#length"}.get(
            header, header)
        if (header not in ["artist", "album"] and
            self.browser.can_filter(header) and
            (header[0] != "~" or header[1] == "#")):
            b = gtk.ImageMenuItem(_("_Filter on %s") % tag(header, False))
            b.connect_object('activate', self.__filter_on, 'header', songs)
            b.get_image().set_from_stock(gtk.STOCK_INDEX, gtk.ICON_SIZE_MENU)
            menu.append(b)
        if menu.get_children(): menu.append(gtk.SeparatorMenuItem())

        b = gtk.ImageMenuItem(_("Plugins"))
        b.get_image().set_from_stock(gtk.STOCK_EXECUTE, gtk.ICON_SIZE_MENU)
        menu.append(b)
        submenu = gtk.Menu()
        b.set_submenu(submenu)
        self.__create_plugins_menu(self.__pm, submenu)
        submenu.connect('expose-event', self.__refresh_plugins_menu,
                self.__pm, submenu)

        if menu.get_children(): menu.append(gtk.SeparatorMenuItem())

        b = gtk.ImageMenuItem(gtk.STOCK_REMOVE)
        b.connect('activate', self.remove_song)
        menu.append(b)
        b = gtk.ImageMenuItem(gtk.STOCK_DELETE)
        b.connect('activate', self.delete_song)
        menu.append(b)
        b = gtk.ImageMenuItem(gtk.STOCK_PROPERTIES)
        b.connect_object('activate', SongProperties, songs)
        menu.append(b)

        menu.show_all()
        menu.connect('selection-done', lambda m: m.destroy())
        menu.popup(None, None, None, button, time)

    def __refresh_plugins_menu(self, item, event, pm, menu):
        if pm.rescan(): self.__create_plugins_menu(pm, menu)

    def __create_plugins_menu(self, pm, menu):
        for child in menu.get_children(): menu.remove(child)
        songs = self.songlist.get_selected_songs()
        plugins = [(plugin.PLUGIN_NAME, plugin) for plugin in pm.list(songs)]
        plugins.sort()
        for name, plugin in plugins:
            if hasattr(plugin, 'PLUGIN_ICON'):
                b = gtk.ImageMenuItem(name)
                b.get_image().set_from_stock(plugin.PLUGIN_ICON,
                    gtk.ICON_SIZE_MENU)
            else:
                b = gtk.MenuItem(name)
            b.connect('activate', self.__invoke_plugin, pm, plugin, songs)
            menu.append(b)

        if not menu.get_children():
            b = gtk.MenuItem(_("No Matching Plugins"))
            b.set_sensitive(False)
            menu.append(b)
        menu.show_all()

    def __invoke_plugin(self, event, pm, plugin, songs):
        pm.invoke(plugin, songs)

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

    def __browser_cb(self, text, sort):
        if isinstance(text, str): text = text.decode("utf-8")
        text = text.strip()
        if self.browser.background:
            try: bg = config.get("browsers", "background").decode('utf-8')
            except UnicodeError: bg = ""
        else: bg = ""
        if player.playlist.playlist_from_filters(text, bg):
            if sort:
                self.songlist.set_sort_by(None, tag=sort, refresh=False)
            self.refresh_songlist()

    def __filter_on(self, header, songs=None):
        if not self.browser or not self.browser.can_filter(header):
            return
        if songs is None:
            songs = self.songlist.get_selected_songs()

        if header.startswith("~#"):
            values = set([song(header, 0) for song in songs])
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
        if self.browser.can_filter(None):
            self.browser.set_text(query.encode('utf-8'))
            self.browser.activate()

    def set_column_headers(self, headers):
        SongList.set_all_column_headers(headers)

    def refresh_songlist(self):
        i, length = self.songlist.refresh(current=widgets.watcher.song)
        statusbar = self.__statusbar
        if i != 1: statusbar.set_text(
            _("%d songs (%s)") % (i, util.format_time_long(length)))
        else: statusbar.set_text(
            _("%d song (%s)") % (i, util.format_time_long(length)))

class SongList(gtk.TreeView):
    """Wrap a treeview that works like a songlist"""
    songlistviews = {}
    headers = []

    def __init__(self, recall=0):
        gtk.TreeView.__init__(self)
        self.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.songlistviews[self] = None     # register self
        self.recall_size = recall
        self.set_column_headers(self.headers)
        self.connect_object('destroy', SongList._destroy, self)
        sigc = widgets.watcher.connect_object(
            'changed', SongList.__song_updated, self)
        sigr = widgets.watcher.connect_object(
            'removed', SongList.__song_removed, self)
        self.connect_object('destroy', widgets.watcher.disconnect, sigc)
        self.connect_object('destroy', widgets.watcher.disconnect, sigr)

    def set_all_column_headers(cls, headers):
        cls.headers = headers
        for listview in cls.songlistviews:
            listview.set_column_headers(headers)
    set_all_column_headers = classmethod(set_all_column_headers)

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

    def __song_updated(self, song):
        iter = self.song_to_iter(song)
        if iter:
            model = self.get_model()
            model[iter][0] = model[iter][0]

    def __song_removed(self, song):
        iter = self.song_to_iter(song)
        if iter:
            model = self.get_model()
            model.remove(iter)

    def jump_to(self, path):
        self.scroll_to_cell(path)

    def save_widths(self, column, width):
        config.set("memory", "widths", " ".join(
            [str(x.get_width()) for x in self.get_columns()]))

    # Build a new filter around our list model, set the headers to their
    # new values.
    def set_column_headers(self, headers):
        if len(headers) == 0: return
        SHORT_COLS = ["tracknumber", "discnumber", "~length", "~rating"]
        SLOW_COLS = ["~basename", "~dirname", "~filename"]
        if not self.recall_size:
            try: ws = map(int, config.get("memory", "widths").split())
            except: ws = []
        else: ws = []

        if len(ws) != len(headers): ws = [40] * len(headers)

        for c in self.get_columns(): self.remove_column(c)

        def cell_data(column, cell, model, iter,
                attr = (pango.WEIGHT_NORMAL, pango.WEIGHT_BOLD)):
            try:
                song = model[iter][0]
                current_song = widgets.watcher.song
                cell.set_property('weight', attr[song is current_song])
                cell.set_property('text', song.comma(column.header_name))
            except AttributeError: pass

        def cell_data_fn(column, cell, model, iter, code,
                attr = (pango.WEIGHT_NORMAL, pango.WEIGHT_BOLD)):
            try:
                song = model[iter][0]
                current_song = widgets.watcher.song
                cell.set_property('weight', attr[song is current_song])
                cell.set_property('text', util.unexpand(
                    song.comma(column.header_name).decode(code, 'replace')))
            except AttributeError: pass

        for i, t in enumerate(headers):
            render = gtk.CellRendererText()
            title = tag(t)
            column = gtk.TreeViewColumn(title, render)
            column.header_name = t
            if t in SHORT_COLS or t.startswith("~#"):
                column.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
            else:
                column.set_expand(True)
                column.set_resizable(True)
                column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
                column.set_fixed_width(ws[i])
            if hasattr(self, 'set_sort_by'):
                column.connect('clicked', self.set_sort_by)
            self._set_column_settings(column)
            if t in ["~filename", "~basename", "~dirname"]:
                column.set_cell_data_func(render, cell_data_fn,
                                          util.fscoding())
            else:
                column.set_cell_data_func(render, cell_data)
            if t == "~length":
                column.set_alignment(1.0)
                render.set_property('xalign', 1.0)
            self.append_column(column)

    def _destroy(self):
        del(self.songlistviews[self])
        self.set_model(None)

    def _set_column_settings(self, column):
        column.set_visible(True)

class PlayList(SongList):
    # ["%", " "] + parser.QueryLexeme.table.keys()
    BAD = ["%", " ", "!", "&", "|", "(", ")", "=", ",", "/", "#", ">", "<"]
    DAB = BAD[::-1]

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
            model.append([(_("All songs")), ""])
            for p in playlists: model.append(p)
            return model
    lists_model = classmethod(lists_model)

    def __init__(self, name):
        plname = 'playlist_' + PlayList.normalize_name(name)
        self.__key = key = '~#' + plname
        model = gtk.ListStore(object)
        super(PlayList, self).__init__(400)

        for song in library.query('#(%s > 0)' % plname, sort=key):
            model.append([song])

        self.set_model(model)
        self.connect_object('drag-end', self.__refresh_indices, key)
        self.set_reorderable(True)

        menu = gtk.Menu()
        rem = gtk.ImageMenuItem(gtk.STOCK_REMOVE, gtk.ICON_SIZE_MENU)
        rem.connect('activate', self.__remove_selected_songs, key)
        menu.append(rem)
        prop = gtk.ImageMenuItem(gtk.STOCK_PROPERTIES, gtk.ICON_SIZE_MENU)
        prop.connect('activate', self.__song_properties)
        menu.append(prop)
        menu.show_all()
        self.connect_object('destroy', gtk.Menu.destroy, menu)
        self.connect('button-press-event', self.__button_press, menu)
        self.connect_object('popup-menu', gtk.Menu.popup, menu,
                            None, None, None, 2, 0)

        sig = widgets.watcher.connect('refresh', self.__refresh_indices, key)
        self.connect_object('destroy', widgets.watcher.disconnect, sig)

    def append_songs(self, songs):
        model = self.get_model()
        current_songs = set([row[0]['~filename'] for row in model])
        for song in songs:
            if song['~filename'] not in current_songs:
                model.append([song])
                song[self.__key] = len(model) # 1 based index; 0 means out

    def __remove_selected_songs(self, activator, key):
        model, rows = self.get_selection().get_selected_rows()
        rows.sort()
        rows.reverse()
        for row in rows:
            del(model[row][0][key])
            iter = model.get_iter(row)
            model.remove(iter)
        self.__refresh_indices(activator, key)

    def __song_properties(self, activator):
        model, rows = self.get_selection().get_selected_rows()
        SongProperties([model[row][0] for row in rows])

    def __refresh_indices(self, context, key):
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

    def _set_column_settings(self, column):
        column.set_clickable(True)
        column.set_reorderable(True)
        column.set_sort_indicator(False)
        column.connect('notify::width', self.save_widths)

    # Resort based on the header clicked.
    def set_sort_by(self, header, tag=None, refresh=True, order=None):
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
                    if order: s == gtk.SORT_ASCENDING
                    else: s = gtk.SORT_DESCENDING
                h.set_sort_indicator(True)
                h.set_sort_order(s)
            else: h.set_sort_indicator(False)
        player.playlist.sort_by(tag, s == gtk.SORT_DESCENDING)
        config.set('memory', 'sortby', "%d%s" % (s == gtk.SORT_ASCENDING,
                                                 tag))
        if refresh: self.refresh()

    # Clear the songlist and readd the songs currently wanted.
    def refresh(self, current=None):
        model = self.get_model()

        selected = self.get_selected_songs()
        selected = dict.fromkeys([song['~filename'] for song in selected])

        model.clear()
        length = 0
        for song in player.playlist:
            model.append([song])
            length += song["~#length"]

        # reselect what we can
        selection = self.get_selection()
        for i, row in enumerate(iter(model)):
            if row[0]['~filename'] in selected:
                selection.select_path(i)
        i = len(list(player.playlist))
        return i, length

class GetStringDialog(gtk.Dialog):
    def __init__(self, parent, title, text, options=[]):
        gtk.Dialog.__init__(self, title, parent)
        self.set_border_width(6)        
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

class AddTagDialog(gtk.Dialog):
    def __init__(self, parent, can_change, validators):
        if can_change == True:
            can = ["title", "version", "artist", "album",
                   "performer", "discnumber", "tracknumber"]
        else: can = can_change
        can.sort()

        gtk.Dialog.__init__(self, _("Add a new tag"), parent)
        self.set_border_width(6)
        self.set_resizable(False)
        self.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        add = self.add_button(gtk.STOCK_ADD, gtk.RESPONSE_OK)
        self.vbox.set_spacing(6)
        self.set_default_response(gtk.RESPONSE_OK)
        table = gtk.Table(2, 2)
        table.set_row_spacings(12)
        table.set_col_spacings(6)
        table.set_border_width(6)

        if can_change == True:
            self.__tag = gtk.combo_box_entry_new_text()
            for tag in can: self.__tag.append_text(tag)
        else:
            self.__tag = gtk.combo_box_new_text()
            for tag in can: self.__tag.append_text(tag)
            self.__tag.set_active(0)

        label = gtk.Label()
        label.set_alignment(0.0, 0.5)
        label.set_text(_("_Tag:"))
        label.set_use_underline(True)
        label.set_mnemonic_widget(self.__tag)
        table.attach(label, 0, 1, 0, 1)
        table.attach(self.__tag, 1, 2, 0, 1)

        self.__val = gtk.Entry()
        label = gtk.Label()
        label.set_text(_("_Value:"))
        label.set_alignment(0.0, 0.5)
        label.set_use_underline(True)
        label.set_mnemonic_widget(self.__val)
        valuebox = gtk.EventBox()
        table.attach(label, 0, 1, 1, 2)
        table.attach(valuebox, 1, 2, 1, 2)
        hbox = gtk.HBox()
        valuebox.add(hbox)
        hbox.pack_start(self.__val)
        hbox.set_spacing(6)
        invalid = gtk.image_new_from_stock(
            gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_SMALL_TOOLBAR)
        hbox.pack_start(invalid)

        self.vbox.pack_start(table)
        self.child.show_all()
        invalid.hide()

        tips = gtk.Tooltips()
        for entry in [self.__tag, self.__val]:
            entry.connect(
                'changed', self.__validate, validators, add, invalid, tips,
                valuebox)

    def get_tag(self):
        try: return self.__tag.child.get_text().lower().strip()
        except AttributeError:
            return self.__tag.get_model()[self.__tag.get_active()][0]

    def get_value(self):
        return self.__val.get_text().decode("utf-8")

    def __validate(self, editable, validators, add, invalid, tips, box):
        tag = self.get_tag()
        try: validator, message = validators.get(tag)
        except TypeError: valid = True
        else: valid = bool(validator(self.get_value()))

        add.set_sensitive(valid)
        if valid:
            invalid.hide()
            tips.disable()
        else:
            invalid.show()
            tips.set_tip(box, message)
            tips.enable()

    def run(self):
        self.show()
        try: self.__tag.child.set_activates_default(True)
        except AttributeError: pass
        self.__val.set_activates_default(True)
        self.__tag.grab_focus()
        return gtk.Dialog.run(self)

class SongProperties(gtk.Window):
    __gsignals__ = { 'changed': (gobject.SIGNAL_RUN_LAST,
                                 gobject.TYPE_NONE, (object,))
                     }

    class Information(gtk.ScrolledWindow):
        def __init__(self, parent):
            gtk.ScrolledWindow.__init__(self)
            self.title = _("Information")
            self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
            self.add(gtk.Viewport())
            self.child.set_shadow_type(gtk.SHADOW_NONE)
            self.box = gtk.VBox(spacing=6)
            self.box.set_border_width(12)
            self.child.add(self.box)
            self.tips = gtk.Tooltips()
            parent.connect_object('changed', self.__class__.__update, self)

        def _title(self, song):
            text = "<b><span size='x-large'>%s</span></b>" %(
                util.escape(song("title")))
            if "version" in song:
                text += "\n" + util.escape(song.comma("version"))
            w = self.Label(text)
            w.set_alignment(0, 0)
            return w

        def Frame(self, label, widget, big=True):
            f = gtk.Frame()
            g = gtk.Label()
            if big: g.set_markup("<big><u>%s</u></big>" % label)
            else: g.set_markup("<u>%s</u>" % label)
            f.set_label_widget(g)
            f.set_shadow_type(gtk.SHADOW_NONE)
            a = gtk.Alignment(xalign=0.0, yalign=0.0, xscale=1.0, yscale=1.0)
            a.set_padding(0, 0, 12, 0)
            a.add(widget)
            f.add(a)
            return f

        def _people(self, song):
            vbox = gtk.VBox(spacing=6)
            vbox.pack_start(
                self.Label(util.escape(song("artist"))), expand=False)

            for names, tag_ in [
                (_("performers"), "performer"),
                (_("lyricists"),  "lyricist"),
                (_("arrangers"),  "arranger"),
                (_("composers"),  "composer"),
                (_("conductors"), "conductor"),
                (_("authors"),    "author")]:
                if tag_ in song:
                    if "\n" in song[tag_]:
                        frame = self.Frame(util.capitalize(names),
                                           self.Label(util.escape(song[tag_])),
                                           False)
                    else:
                        ntag = util.capitalize(tag(tag_))
                        frame = self.Frame(util.capitalize(ntag),
                                           self.Label(util.escape(song[tag_])),
                                           False)
                    vbox.pack_start(frame, expand=False)
            return self.Frame(util.capitalize(_("artists")), vbox)

        def _album(self, song):
            title = tag("album")
            cover = song.find_cover()
            w = self.Label("")
            if cover:
                try:
                    hb = gtk.HBox(spacing=12)
                    hb.pack_start(self._make_cover(cover, song),expand=False)
                    hb.pack_start(w)
                    f = self.Frame(title, hb)
                except:
                    f = self.Frame(title, w)
            else:
                f = self.Frame(title, w)

            text = []
            text.append("<b>%s</b>" % util.escape(song.comma("album")))
            if "date" in song: text[-1] += " (%s)" % util.escape(song["date"])
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
            rating = song("~rating")
            tbl = [(_("play count"), playcount),
                   (_("skip count"), skipcount),
                   (_("rating"), rating),
                   (_("length"), tim),
                   (_("added"), added),
                   (_("modified"), changed),
                   (_("file size"), size)
                   ]

            if song.get("~#bitrate"):
                tbl.insert(-1,
                           (_("bitrate"),
                            _("%d kbps") % int(song["~#bitrate"]/1000)))
            table = gtk.Table(len(tbl) + 1, 2)
            table.set_col_spacings(6)
            l = self.Label(util.escape(fn))
            table.attach(l, 0, 2, 0, 1, xoptions=gtk.FILL)
            table.set_homogeneous(False)
            for i, (l, r) in enumerate(tbl):
                l = "<b>%s</b>" % util.capitalize(util.escape(l) + ":")
                table.attach(self.Label(l), 0, 1, i + 1, i + 2, xoptions=0)
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
            self.box.pack_start(self._title(song), expand=False)
            if "album" in song:
                self.box.pack_start(self._album(song), expand=False)
            self.box.pack_start(self._people(song), expand=False)
            self.box.pack_start(self._listen(song), expand=False)

        def _update_album(self, songs):
            songs.sort()
            album = songs[0]("~album~date")
            self.box.pack_start(self.Label(
                "<b><span size='x-large'>%s</span></b>" % util.escape(album)),
                                expand=False)

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
                        hb = gtk.HBox(spacing=12)
                        i = self._make_cover(cover, songs[0])
                        hb.pack_start(i, expand=False)
                        hb.pack_start(w)
                        self.box.pack_start(hb, expand=False)
                    except:
                        self.box.pack_start(w, expand=False)
                else:
                    self.box.pack_start(w, expand=False)

            artists = set()
            for song in songs: artists.update(song.list("artist"))
            artists = list(artists)
            artists.sort()
            l = gtk.Label(", ".join(artists))
            l.set_alignment(0, 0)
            l.set_selectable(True)
            l.set_line_wrap(True)
            self.box.pack_start(
                self.Frame(util.capitalize(_("artists")), l), expand=False)

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
            self.box.pack_start(self.Frame(_("Track List"), l), expand=False)

        def _update_artist(self, songs):
            artist = songs[0].comma("artist")
            self.box.pack_start(self.Label(
                "<b><span size='x-large'>%s</span></b>\n%s" %(
                util.escape(artist), _("%d songs") % len(songs))),
                                expand=False)

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
                expand=False)
            added = set()
            covers = [ac for ac in covers if bool(ac[1])]
            t = gtk.Table(4, (len(covers) // 4) + 1)
            t.set_col_spacings(12)
            t.set_row_spacings(12)
            for i, (album, cover, song) in enumerate(covers):
                if cover.name in added: continue
                try:
                    cov = self._make_cover(cover, song)
                    self.tips.set_tip(cov.child, album)
                    c = i % 4
                    r = i // 4
                    t.attach(cov, c, c + 1, r, r + 1,
                             xoptions=gtk.EXPAND, yoptions=0)
                except: pass
                added.add(cover.name)
            self.box.pack_start(t)

        def _update_many(self, songs):
            text = "<b><span size='x-large'>%s</span></b>" %(
                _("%d songs") % len(songs))
            l = self.Label(text)
            self.box.pack_start(l, expand=False)

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
                                expand=False)

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
                    self.Frame("%s (%d)" % (util.capitalize(_("artists")),
                                            arcount),
                               self.Label(artists)),
                               expand=False)

            albums = list(albums)
            albums.sort()
            alcount = len(albums)
            if noalbum: albums.append(_("%d songs with no album") % noalbum)
            albums = util.escape("\n".join(albums))
            if albums:
                self.box.pack_start(
                    self.Frame("%s (%d)" % (util.capitalize(_("albums")),
                                            alcount),
                               self.Label(albums)),
                               expand=False)

        def __update(self, songs):
            for c in self.box.get_children():
                self.box.remove(c)
                c.destroy()
            if len(songs) == 0:
                self.box.pack_start(gtk.Label(_("No songs are selected.")))
            elif len(songs) == 1: self._update_one(songs[0])
            else:
                albums = [song.get("album") for song in songs]
                artists = [song.get("artist") for song in songs]
                if min(albums) == max(albums) and None not in albums:
                    self._update_album(songs[:])
                elif min(artists) == max(artists) and None not in artists:
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
            gtk.VBox.__init__(self, spacing=12)
            self.title = _("Edit Tags")
            self.set_border_width(12)
            self.prop = parent

            self.model = gtk.ListStore(str, str, bool, bool, bool, str)
            self.view = gtk.TreeView(self.model)
            selection = self.view.get_selection()
            selection.connect('changed', self.tag_select)
            render = gtk.CellRendererPixbuf()
            column = gtk.TreeViewColumn(_("Write"), render)

            style = self.view.get_style()
            pixbufs = [ style.lookup_icon_set(stock)
                        .render_icon(style, gtk.TEXT_DIR_NONE, state,
                            gtk.ICON_SIZE_MENU, self.view, None)
                        for state in (gtk.STATE_INSENSITIVE, gtk.STATE_NORMAL)
                            for stock in (gtk.STOCK_EDIT, gtk.STOCK_DELETE) ]
            def cdf_write(col, rend, model, iter, (write, delete)):
                row = model[iter]
                rend.set_property('pixbuf', pixbufs[2*row[write]+row[delete]])
            column.set_cell_data_func(render, cdf_write, (2, 4))
            self.view.connect('button-press-event',
                              self.write_toggle, (column, 2))
            self.view.append_column(column)

            render = gtk.CellRendererText()
            render.connect('edited', self.edit_tag, self.model, 0)
            column = gtk.TreeViewColumn(_('Tag'), render, text=0,
                                        strikethrough=4)
            column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            self.view.append_column(column)

            render = gtk.CellRendererText()
            render.set_property('editable', True)
            render.connect('edited', self.edit_tag, self.model, 1)
            column = gtk.TreeViewColumn(_('Value'), render, markup=1,
                                        editable=3, strikethrough=4)
            column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            self.view.append_column(column)

            self.view.connect('popup-menu', self.popup_menu)
            self.view.connect('button-press-event', self.button_press)

            sw = gtk.ScrolledWindow()
            sw.set_shadow_type(gtk.SHADOW_IN)
            sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
            sw.add(self.view)
            self.pack_start(sw)

            self.buttonbox = gtk.HBox(spacing=18)
            bbox1 = gtk.HButtonBox()
            bbox1.set_spacing(6)
            bbox1.set_layout(gtk.BUTTONBOX_START)
            self.add = qltk.Button(stock=gtk.STOCK_ADD, cb=self.add_tag)
            self.remove = qltk.Button(stock=gtk.STOCK_REMOVE,
                                      cb=self.remove_tag)
            self.remove.set_sensitive(False)
            bbox1.pack_start(self.add)
            bbox1.pack_start(self.remove)

            bbox2 = gtk.HButtonBox()
            bbox2.set_spacing(6)
            bbox2.set_layout(gtk.BUTTONBOX_END)
            self.revert = qltk.Button(stock=gtk.STOCK_REVERT_TO_SAVED,
                                      cb=self.revert_files)
            self.save = qltk.Button(stock=gtk.STOCK_SAVE,
                                   cb=self.save_files)
            self.revert.set_sensitive(False)
            self.save.set_sensitive(False)
            bbox2.pack_start(self.revert)
            bbox2.pack_start(self.save)

            self.buttonbox.pack_start(bbox1)
            self.buttonbox.pack_start(bbox2)

            self.pack_start(self.buttonbox, expand=False)

            tips = gtk.Tooltips()
            for widget, tip in [
                (self.view, _("Double-click a tag value to change it, "
                              "right-click for other options")),
                (self.add, _("Add a new tag to the file")),
                (self.remove, _("Remove a tag from the file"))]:
                tips.set_tip(widget, tip)
            parent.connect_object('changed', self.__class__.__update, self)

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
            add = AddTagDialog(self.prop, self.songinfo.can_change(),
                {'date': [sre.compile(r"^\d{4}(-\d{2}-\d{2})?$").match,
                _("The date must be entered in YYYY or YYYY-MM-DD format.")]})

            while True:
                resp = add.run()
                if resp != gtk.RESPONSE_OK: break
                comment = add.get_tag()
                value = add.get_value()
                if not self.songinfo.can_change(comment):
                    qltk.ErrorMessage(
                        self.prop, _("Invalid tag"),
                        _("Invalid tag <b>%s</b>\n\nThe files currently"
                          " selected do not support editing this tag.")%
                        util.escape(comment)).run()
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
                if not song.valid() and not qltk.ConfirmAction(
                    self.prop, _("Tag may not be accurate"),
                    _("<b>%s</b> looks like it was changed while the "
                      "program was running. Saving now without "
                      "refreshing your library might overwrite other "
                      "changes to tag.\n\n"
                      "Save this tag anyway?") % song("~basename")
                    ).run():
                    break

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
                        widgets.watcher.error(song)
                        break
                    widgets.watcher.changed(song)

                if win.step(): break

            win.destroy()
            widgets.watcher.refresh()
            self.save.set_sensitive(False)
            self.revert.set_sensitive(False)

        def revert_files(self, *args):
            self.__update(self.songs)

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

        def write_toggle(self, view, event, (writecol, edited)):
            if event.button != 1: return False
            x, y = map(int, [event.x, event.y])
            try: path, col, cellx, celly = view.get_path_at_pos(x, y)
            except TypeError: return False

            if col is writecol:
                row = view.get_model()[path]
                row[edited] = not row[edited]
                self.save.set_sensitive(True)
                self.revert.set_sensitive(True)
                return True

        def __update(self, songs):
            from library import AudioFileGroup
            self.songinfo = songinfo = AudioFileGroup(songs)
            self.songs = songs
            self.view.set_model(None)
            self.model.clear()
            self.view.set_model(self.model)

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
            self.add.set_sensitive(bool(songs))
            self.songs = songs

    class TagByFilename(gtk.VBox):
        def __init__(self, prop):
            gtk.VBox.__init__(self, spacing=6)
            self.title = _("Tag by Filename")
            self.prop = prop
            self.set_border_width(12)
            hbox = gtk.HBox(spacing=12)
            self.combo = combo = qltk.ComboBoxEntrySave(
                const.TBP, const.TBP_EXAMPLES.split("\n"))
            hbox.pack_start(combo)
            self.entry = combo.child
            self.entry.connect('changed', self.changed)
            self.preview = qltk.Button(_("_Preview"), gtk.STOCK_CONVERT)
            self.preview.connect('clicked', self.preview_tags)
            hbox.pack_start(self.preview, expand=False)
            self.pack_start(hbox, expand=False)

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
            
            self.pack_start(vbox, expand=False)

            bbox = gtk.HButtonBox()
            bbox.set_layout(gtk.BUTTONBOX_END)
            self.save = qltk.Button(
                stock=gtk.STOCK_SAVE, cb=self.save_files)
            bbox.pack_start(self.save)
            self.pack_start(bbox, expand=False)

            tips = gtk.Tooltips()
            for widget, tip in [
                (self.titlecase,
                 _("If appropriate to the language, the first letter of "
                   "each word will be capitalized"))]:
                tips.set_tip(widget, tip)
            prop.connect_object('changed', self.__class__.__update, self)

        def __update(self, songs):
            from library import AudioFileGroup
            self.songs = songs

            songinfo = AudioFileGroup(songs)
            if songs: pattern_text = self.entry.get_text().decode("utf-8")
            else: pattern_text = ""
            try: pattern = util.PatternFromFile(pattern_text)
            except sre.error:
                qltk.ErrorMessage(
                    self.prop, _("Invalid pattern"),
                    _("The pattern\n\t<b>%s</b>\nis invalid. "
                      "Possibly it contains the same tag twice or "
                      "it has unbalanced brackets (&lt; / &gt;).")%(
                    util.escape(pattern_text))).run()
                return
            else:
                if pattern_text:
                    self.combo.prepend_text(pattern_text)
                    self.combo.write(const.TBP)

            invalid = []

            for header in pattern.headers:
                if not songinfo.can_change(header):
                    invalid.append(header)
            if len(invalid) and songs:
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
                pattern = util.PatternFromFile("")

            self.view.set_model(None)
            rep = self.space.get_active()
            title = self.titlecase.get_active()
            split = self.split.get_active()
            self.model = gtk.ListStore(object, str,
                                       *([str] * len(pattern.headers)))
            for col in self.view.get_columns():
                self.view.remove_column(col)

            col = gtk.TreeViewColumn(_('File'), gtk.CellRendererText(),
                                     text=1)
            col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            self.view.append_column(col)
            for i, header in enumerate(pattern.headers):
                render = gtk.CellRendererText()
                render.set_property('editable', True)
                render.connect('edited', self.row_edited, self.model, i + 2)
                col = gtk.TreeViewColumn(header, render, text=i + 2)
                col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
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
                self.model.append(row=row)

            # save for last to potentially save time
            if songs: self.view.set_model(self.model)
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
                if not song.valid() and not qltk.ConfirmAction(
                    self.prop, _("Tag may not be accurate"),
                    _("<b>%s</b> looks like it was changed while the "
                      "program was running. Saving now without "
                      "refreshing your library might overwrite other "
                      "changes to tag.\n\n"
                      "Save this tag anyway?") % song("~basename")
                    ).run():
                    return True

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
                    try: song.write()
                    except:
                        qltk.ErrorMessage(
                            self.prop, _("Unable to edit song"),
                            _("Saving <b>%s</b> failed. The file "
                              "may be read-only, corrupted, or you "
                              "do not have permission to edit it.")%(
                            util.escape(song('~basename')))).run()
                        widgets.watcher.error(song)
                        return True
                    widgets.watcher.changed(song)

                return win.step()
        
            self.model.foreach(save_song)
            win.destroy()
            widgets.watcher.refresh()
            self.save.set_sensitive(False)

        def row_edited(self, renderer, path, new, model, colnum):
            row = model[path]
            if row[colnum] != new:
                row[colnum] = new
                self.preview.set_sensitive(True)

        def preview_tags(self, *args):
            self.__update(self.songs)

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

    class RenameFiles(gtk.VBox):
        def __init__(self, prop):
            gtk.VBox.__init__(self, spacing=6)
            self.title = _("Rename Files")
            self.set_border_width(12)

            # ComboEntry and Preview button
            hbox = gtk.HBox(spacing=12)
            combo = qltk.ComboBoxEntrySave(
                const.NBP, const.NBP_EXAMPLES.split("\n"))
            hbox.pack_start(combo)
            preview = qltk.Button(_("_Preview"), gtk.STOCK_CONVERT)
            hbox.pack_start(preview, expand=False)
            self.pack_start(hbox, expand=False)

            # Tree view in a scrolling window
            model = gtk.ListStore(object, str, str)
            view = gtk.TreeView(model)
            column = gtk.TreeViewColumn(
                _('File'), gtk.CellRendererText(), text=1)
            column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            view.append_column(column)
            render = gtk.CellRendererText()
            render.set_property('editable', True)
            render.connect('edited', self.__row_edited, model, preview)
            column = gtk.TreeViewColumn(_('New Name'), render, text=2)
            column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            view.append_column(column)
            sw = gtk.ScrolledWindow()
            sw.set_shadow_type(gtk.SHADOW_IN)
            sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
            sw.add(view)
            self.pack_start(sw)

            # Checkboxes
            replace = gtk.CheckButton(_("Replace spaces with _underscores"))
            replace.set_active(config.state("nbp_space"))
            windows = gtk.CheckButton(_(
                "Replace _Windows-incompatible characters"))
            windows.set_active(config.state("windows"))
            ascii = gtk.CheckButton(_("Replace non-_ASCII characters"))
            ascii.set_active(config.state("ascii"))

            vbox = gtk.VBox()
            vbox.pack_start(replace)
            vbox.pack_start(windows)
            vbox.pack_start(ascii)
            self.pack_start(vbox, expand=False)

            # Save button
            save = gtk.Button(stock=gtk.STOCK_SAVE)
            bbox = gtk.HButtonBox()
            bbox.set_layout(gtk.BUTTONBOX_END)
            bbox.pack_start(save)
            self.pack_start(bbox, expand=False)

            # Set tooltips
            tips = gtk.Tooltips()
            for widget, tip in [
                (windows,
                 _("Characters not allowed in Windows filenames "
                   "(\:?;\"<>|) will be replaced by underscores")),
                (ascii,
                 _("Characters outside of the ASCII set (A-Z, a-z, 0-9, "
                   "and punctuation) will be replaced by underscores"))]:
                tips.set_tip(widget, tip)

            # Connect callbacks
            preview_args = [combo, prop, model, save, preview,
                            replace, windows, ascii]
            preview.connect(
                'clicked', self.__preview_files, *preview_args)
            prop.connect_object(
                'changed', self.__class__.__update, self, *preview_args)

            changed_args = [replace, windows, ascii, save, preview,
                            combo.child]
            for w in [replace, windows, ascii]:
                w.connect_object('toggled', self.__changed, *changed_args)
            combo.child.connect_object(
                'changed', self.__changed, *changed_args)

            save.connect_object(
                'clicked', self.__rename_files, prop, save, model)

        def __changed(self, replace, windows, ascii, save, preview, entry):
            config.set("settings", "windows", str(windows.get_active()))
            config.set("settings", "ascii", str(ascii.get_active()))
            config.set("settings", "nbp_space", str(replace.get_active()))
            save.set_sensitive(False)
            preview.set_sensitive(bool(entry.get_text()))

        def __row_edited(self, renderer, path, new, model, preview):
            row = model[path]
            if row[2] != new:
                row[2] = new
                preview.set_sensitive(True)

        def __preview_files(self, button, *args):
            self.__update(self.__songs, *args)
            save = args[3]
            save.set_sensitive(True)
            preview = args[4]
            preview.set_sensitive(False)

        def __rename_files(self, parent, save, model):
            win = WritingWindow(parent, len(self.__songs))

            def rename(model, path, iter):
                song = model[path][0]
                oldname = model[path][1]
                newname = model[path][2]
                try:
                    newname = newname.encode(util.fscoding(), "replace")
                    if library: library.rename(song, newname)
                    else: song.rename(newname)
                    widgets.watcher.changed(song)
                except:
                    qltk.ErrorMessage(
                        win, _("Unable to rename file"),
                        _("Renaming <b>%s</b> to <b>%s</b> failed. "
                          "Possibly the target file already exists, "
                          "or you do not have permission to make the "
                          "new file or remove the old one.") %(
                        util.escape(oldname), util.escape(newname))).run()
                    widgets.watcher.error(song)
                    return True
                return win.step()
            model.foreach(rename)
            widgets.watcher.refresh()
            save.set_sensitive(False)
            widgets.watcher.refresh()
            win.destroy()

        def __update(self, songs, combo, parent, model, save, preview,
                     replace, windows, ascii):
            self.__songs = songs
            model.clear()
            pattern = combo.child.get_text().decode("utf-8")

            underscore = replace.get_active()
            windows = windows.get_active()
            ascii = ascii.get_active()

            try:
                pattern = util.FileFromPattern(pattern)
            except ValueError: 
                qltk.ErrorMessage(
                    parent,
                    _("Pattern with subdirectories is not absolute"),
                    _("The pattern\n\t<b>%s</b>\ncontains / but "
                      "does not start from root. To avoid misnamed "
                      "directories, root your pattern by starting "
                      "it from the / directory.")%(
                    util.escape(pattern))).run()
                return
            else:
                if combo.child.get_text():
                    combo.prepend_text(combo.child.get_text())
                    combo.write(const.NBP)

            for song in self.__songs:
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
                model.append(row=[song, basename, newname])
            preview.set_sensitive(False)
            save.set_sensitive(bool(combo.child.get_text()))

    class TrackNumbers(gtk.VBox):
        def __init__(self, prop):
            gtk.VBox.__init__(self, spacing=6)
            self.title = _("Track Numbers")
            self.set_border_width(12)
            hbox = gtk.HBox(spacing=18)
            hbox2 = gtk.HBox(spacing=12)

            hbox_start = gtk.HBox(spacing=3)
            label_start = gtk.Label("Start fro_m:")
            label_start.set_use_underline(True)
            spin_start = gtk.SpinButton()
            spin_start.set_range(1, 99)
            spin_start.set_increments(1, 10)
            spin_start.set_value(1)
            label_start.set_mnemonic_widget(spin_start)
            hbox_start.pack_start(label_start)
            hbox_start.pack_start(spin_start)

            hbox_total = gtk.HBox(spacing=3)
            label_total = gtk.Label("_Total tracks:")
            label_total.set_use_underline(True)
            spin_total = gtk.SpinButton()
            spin_total.set_range(0, 99)
            spin_total.set_increments(1, 10)
            label_total.set_mnemonic_widget(spin_total)
            hbox_total.pack_start(label_total)
            hbox_total.pack_start(spin_total)

            hbox2.pack_start(hbox_start, expand=True, fill=False)
            hbox2.pack_start(hbox_total, expand=True, fill=False)

            model = gtk.ListStore(object, str, str)
            view = gtk.TreeView(model)

            self.pack_start(hbox2, expand=False)

            column = gtk.TreeViewColumn(
                _('File'), gtk.CellRendererText(), text=1)
            column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            view.append_column(column)
            column = gtk.TreeViewColumn(
                _('Track'), gtk.CellRendererText(), text=2)
            column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            view.append_column(column)
            view.set_reorderable(True)
            w = gtk.ScrolledWindow()
            w.set_shadow_type(gtk.SHADOW_IN)
            w.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
            w.add(view)
            self.pack_start(w)

            bbox = gtk.HButtonBox()
            bbox.set_spacing(12)
            bbox.set_layout(gtk.BUTTONBOX_END)
            save = gtk.Button(stock=gtk.STOCK_SAVE)
            save.connect_object(
                'clicked', self.__save_files, prop, model)
            revert = gtk.Button(stock=gtk.STOCK_REVERT_TO_SAVED)
            revert.connect_object(
                'clicked', self.__revert_files, spin_total, model,
                save, revert)
            bbox.pack_start(revert)
            bbox.pack_start(save)
            self.pack_start(bbox, expand=False)

            preview_args = [spin_start, spin_total, model, save, revert]
            spin_total.connect(
                'value-changed', self.__preview_tracks, *preview_args)
            spin_start.connect(
                'value-changed', self.__preview_tracks, *preview_args)
            view.connect_object(
                'drag-end', self.__class__.__preview_tracks, self,
                *preview_args)

            prop.connect_object(
                'changed', self.__class__.__update, self,
                spin_total, model, save, revert)

        def __save_files(self, parent, model):
            win = WritingWindow(parent, len(self.__songs))
            def settrack(model, path, iter):
                song = model[iter][0]
                track = model[iter][2]
                if song.get("tracknumber") == track: return win.step()
                if not song.valid() and not qltk.ConfirmAction(
                    win, _("Tag may not be accurate"),
                    _("<b>%s</b> looks like it was changed while the "
                      "program was running. Saving now without "
                      "refreshing your library might overwrite other "
                      "changes to tag.\n\n"
                      "Save this tag anyway?") % song("~basename")
                    ).run():
                    return True
                song["tracknumber"] = track
                try: song.write()
                except:
                    qltk.ErrorMessage(
                        win, _("Unable to edit song"),
                        _("Saving <b>%s</b> failed. The file may be "
                          "read-only, corrupted, or you do not have "
                          "permission to edit it.")%(
                        util.escape(song('~basename')))).run()
                    widgets.watcher.error(song)
                    return True
                widgets.watcher.changed(song)
                return win.step()
            model.foreach(settrack)
            widgets.watcher.refresh()
            win.destroy()

        def __revert_files(self, *args):
            self.__update(self.__songs, *args)

        def __preview_tracks(self, ctx, start, total, model, save, revert):
            start = start.get_value_as_int()
            total = total.get_value_as_int()
            def refill(model, path, iter):
                if total: s = "%d/%d" % (path[0] + start, total)
                else: s = str(path[0] + start)
                model[iter][2] = s
            model.foreach(refill)
            save.set_sensitive(True)
            revert.set_sensitive(True)

        def __update(self, songs, total, model, save, revert):
            songs = songs[:]; songs.sort()
            self.__songs = songs
            model.clear()
            total.set_value(len(songs))
            for song in songs:
                if not song.can_change("tracknumber"):
                    self.set_sensitive(False)
                    break
            else: self.set_sensitive(True)
            for song in songs:
                basename = util.fsdecode(song("~basename"))
                model.append(row=[song, basename, song("tracknumber")])
            save.set_sensitive(False)
            revert.set_sensitive(False)

    def __init__(self, songs):
        gtk.Window.__init__(self)
        self.set_default_size(300, 430)
        self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        notebook = qltk.Notebook()
        pages = [Ctr(self) for Ctr in
                 [self.Information, self.EditTags, self.TagByFilename,
                  self.RenameFiles]]
        if len(songs) > 1:
            pages.append(self.TrackNumbers(self))
        for page in pages: notebook.append_page(page)
        self.set_border_width(12)
        vbox = gtk.VBox(spacing=12)
        vbox.pack_start(notebook)

        fbasemodel = gtk.ListStore(object, str, str, str)
        fmodel = gtk.TreeModelSort(fbasemodel)
        fview = gtk.TreeView(fmodel)
        selection = fview.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        selection.connect('changed', self.__selection_changed)

        if len(songs) > 1:
            expander = gtk.Expander(_("Apply to these _files..."))
            c1 = gtk.TreeViewColumn(_('File'), gtk.CellRendererText(), text=1)
            c1.set_sort_column_id(1)
            c1.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            c2 = gtk.TreeViewColumn(_('Path'), gtk.CellRendererText(), text=2)
            c2.set_sort_column_id(3)
            c2.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            fview.append_column(c1)
            fview.append_column(c2)
            fview.set_size_request(-1, 130)
            sw = gtk.ScrolledWindow()
            sw.add(fview)
            sw.set_shadow_type(gtk.SHADOW_IN)
            sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
            expander.add(sw)
            expander.set_use_underline(True)
            vbox.pack_start(expander, expand=False)

        bbox = gtk.HButtonBox()
        bbox.set_layout(gtk.BUTTONBOX_END)
        button = gtk.Button(stock=gtk.STOCK_CLOSE)
        button.connect_object('clicked', gtk.Window.destroy, self)
        bbox.pack_start(button)
        vbox.pack_start(bbox, expand=False)

        for song in songs:
            fbasemodel.append(
                row = [song,
                       util.fsdecode(song("~basename")),
                       util.fsdecode(song("~dirname")),
                       song["~filename"]])

        self.connect_object('changed', SongProperties.__set_title, self)

        selection.select_all()
        self.add(vbox)
        self.connect_object('destroy', fview.set_model, None)
        self.connect_object('destroy', gtk.ListStore.clear, fbasemodel)
        self.connect_object(
            'destroy', gtk.TreeModelSort.clear_cache, fmodel)

        s1 = widgets.watcher.connect_object(
            'refresh', SongProperties.__refill, self, fbasemodel)
        s2 = widgets.watcher.connect_object(
            'removed', SongProperties.__remove, self, fbasemodel, selection)
        s3 = widgets.watcher.connect_object(
            'refresh', selection.emit, 'changed')
        self.connect_object('destroy', widgets.watcher.disconnect, s1)
        self.connect_object('destroy', widgets.watcher.disconnect, s2)
        self.connect_object('destroy', widgets.watcher.disconnect, s3)

        self.emit('changed', songs)
        self.show_all()

    def __remove(self, song, model, selection):
        to_remove = [None]
        def remove(model, path, iter):
            if model[iter][0] == song: to_remove.append(iter)
            return bool(to_remove[-1])
        model.foreach(remove)
        if to_remove[-1]:
            model.remove(to_remove[-1])
            self.__refill(model)
            selection.emit('changed')

    def __set_title(self, songs):
        if songs:
            if len(songs) == 1: title = songs[0].comma("title")
            else: title = _("%s and %d more") % (
                songs[0].comma("title"), len(songs) - 1)
            self.set_title("%s - %s" % (title, _("Properties")))
        else: self.set_title(_("Properties"))

    def __refill(self, model):
        def refresh(model, iter, path):
            song = model[iter][0]
            model[iter][1] = song("~basename")
            model[iter][2] = song("~dirname")
            model[iter][3] = song["~filename"]
        model.foreach(refresh)

    def __selection_changed(self, selection):
        model = selection.get_tree_view().get_model()
        if model and len(model) == 1: self.emit('changed', [model[(0,)][0]])
        else:
            songs = []
            def get_songs(model, path, iter, songs):
                songs.append(model[iter][0])
            selection.selected_foreach(get_songs, songs)
            self.emit('changed', songs)

gobject.type_register(SongProperties)

class DirectoryTree(gtk.TreeView):
    def cell_data(column, cell, model, iter):
        cell.set_property('text', util.fsdecode(
            os.path.basename(model[iter][0])) or "/")
    cell_data = staticmethod(cell_data)

    def __init__(self, initial=None):
        gtk.TreeView.__init__(self, gtk.TreeStore(str))
        column = gtk.TreeViewColumn(_("Folders"))
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        render = gtk.CellRendererPixbuf()
        render.set_property('stock_id', gtk.STOCK_DIRECTORY)
        column.pack_start(render, expand=False)
        render = gtk.CellRendererText()
        column.pack_start(render)
        column.set_cell_data_func(render, self.cell_data)

        column.set_attributes(render, text=0)
        self.append_column(column)
        folders = [os.environ["HOME"], "/"]
        # Read in the GTK bookmarks list; gjc says this is the right way
        try: f = file(os.path.join(os.environ["HOME"], ".gtk-bookmarks"))
        except: pass
        else:
            import urlparse
            for line in f.readlines():
                folders.append(urlparse.urlsplit(line.rstrip())[2])
            folders = filter(os.path.isdir, folders)

        for path in folders:
            niter = self.get_model().append(None, [path])
            self.get_model().append(niter, ["dummy"])
        self.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.connect('test-expand-row', DirectoryTree.__expanded,
                     self.get_model())

        if initial:
            path = []
            head, tail = os.path.split(initial)
            while head != os.path.dirname(os.environ["HOME"]) and tail != '':
                if tail:
                    dirs = [d for d in dircache.listdir(head) if
                            (d[0] != "." and
                             os.path.isdir(os.path.join(head,d)))]
                    try: path.insert(0, dirs.index(tail))
                    except ValueError: break
                head, tail = os.path.split(head)

            if initial.startswith(os.environ["HOME"]): path.insert(0, 0)
            else: path.insert(0, 1)
            for i in range(len(path)):
                self.expand_row(tuple(path[:i+1]), False)
            self.get_selection().select_path(tuple(path))
            self.scroll_to_cell(tuple(path))

        else: pass

    def __expanded(self, iter, path, model):
        if model is None: return
        while model.iter_has_child(iter):
            model.remove(model.iter_children(iter))
        dir = model[iter][0]
        for base in dircache.listdir(dir):
            path = os.path.join(dir, base)
            if (base[0] != "." and os.access(path, os.R_OK) and
                os.path.isdir(path)):
                niter = model.append(iter, [path])
                if filter(os.path.isdir,
                          [os.path.join(path, d) for d in
                           dircache.listdir(path) if d[0] != "."]):
                    model.append(niter, ["dummy"])
        if not model.iter_has_child(iter): return True

class FileSelector(gtk.VPaned):
    def cell_data(column, cell, model, iter):
        cell.set_property(
            'text', util.fsdecode(os.path.basename(model[iter][0])))
    cell_data = staticmethod(cell_data)

    __gsignals__ = { 'changed': (gobject.SIGNAL_RUN_LAST,
                                 gobject.TYPE_NONE, (gtk.TreeSelection,))
                     }

    def __init__(self, initial=None, filter=formats.filter):
        gtk.VPaned.__init__(self)
        self.__filter = filter

        dirlist = DirectoryTree(initial)
        filelist = gtk.TreeView(gtk.ListStore(str))
        column = gtk.TreeViewColumn(_("Audio files"))
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        render = gtk.CellRendererPixbuf()
        render.set_property('stock_id', gtk.STOCK_FILE)
        column.pack_start(render, expand=False)
        render = gtk.CellRendererText()
        column.pack_start(render)
        column.set_cell_data_func(render, self.cell_data)
        column.set_attributes(render, text=0)
        filelist.append_column(column)
        filelist.set_rules_hint(True)
        filelist.get_selection().set_mode(gtk.SELECTION_MULTIPLE)

        self.__sig = filelist.get_selection().connect(
            'changed', self.__changed)

        dirlist.get_selection().connect(
            'changed', self.__fill, filelist)
        dirlist.get_selection().emit('changed')
        def select_all_files(view, path, col, fileselection):
            fileselection.select_all()
        dirlist.connect('row-activated', select_all_files,
            filelist.get_selection())

        sw = gtk.ScrolledWindow()
        sw.add(dirlist)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_IN)
        self.pack1(sw, resize=True)

        sw = gtk.ScrolledWindow()
        sw.add(filelist)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_IN)
        self.pack2(sw, resize=True)

    def rescan(self):
        self.get_child1().child.get_selection().emit('changed')

    def __changed(self, selection):
        self.emit('changed', selection)

    def __fill(self, selection, filelist):
        fselect = filelist.get_selection()
        fselect.handler_block(self.__sig)
        fmodel, frows = fselect.get_selected_rows()
        selected = [fmodel[row][0] for row in frows]
        fmodel = filelist.get_model()
        fmodel.clear()
        dmodel, rows = selection.get_selected_rows()
        dirs = [dmodel[row][0] for row in rows]
        files = []
        for dir in dirs:
            for file in filter(self.__filter, dircache.listdir(dir)):
                fmodel.append([os.path.join(dir, file)])
        def select_paths(model, path, iter, selection):
            if model[path][0] in selected:
                selection.select_path(path)
        if fmodel: fmodel.foreach(select_paths, fselect)
        fselect.handler_unblock(self.__sig)
        fselect.emit('changed')

gobject.type_register(FileSelector)

class ExFalsoWindow(gtk.Window):
    __gsignals__ = { 'changed': (gobject.SIGNAL_RUN_LAST,
                                 gobject.TYPE_NONE, (object,))
                     }

    def __init__(self, dir=None):
        gtk.Window.__init__(self)
        self.set_title("Ex Falso")
        self.set_icon_from_file("exfalso.png")
        self.set_border_width(12)
        self.set_default_size(700, 500)
        self.add(gtk.HPaned())
        fs = FileSelector(dir)
        self.child.pack1(fs, resize=True)
        nb = qltk.Notebook()
        for Page in [SongProperties.EditTags,
                     SongProperties.TagByFilename,
                     SongProperties.RenameFiles,
                     SongProperties.TrackNumbers]:
            nb.append_page(Page(self))
        self.child.pack2(nb, resize=False, shrink=False)
        fs.connect('changed', self.__changed, nb)
        self.__cache = {}
        s = widgets.watcher.connect_object('refresh', FileSelector.rescan, fs)
        self.connect_object('destroy', widgets.watcher.disconnect, s)
        self.connect('destroy', gtk.main_quit)
        self.emit('changed', [])

    def __changed(self, selector, selection, notebook):
        model, rows = selection.get_selected_rows()
        files = []
        for row in rows:
            filename = model[row][0]
            if not os.path.exists(filename): pass
            elif filename in self.__cache: files.append(self.__cache[filename])
            else: files.append(formats.MusicFile(model[row][0]))
        try:
            while True: files.remove(None)
        except ValueError: pass
        self.emit('changed', files)
        self.__cache.clear()
        if len(files) == 0: self.set_title("Ex Falso")
        elif len(files) == 1:
            self.set_title("%s - Ex Falso" % files[0]("title"))
        else:
            self.set_title(
                "%s - Ex Falso" %
                (_("%s and %d more") % (files[0]("title"), len(files) - 1)))
        self.__cache = dict([(song["~filename"], song) for song in files])

gobject.type_register(ExFalsoWindow)

class WritingWindow(qltk.WaitLoadWindow):
    def __init__(self, parent, count):
        qltk.WaitLoadWindow.__init__(self, parent, count,
                                _("Saving the songs you changed.\n\n"
                                  "%d/%d songs saved"), (0, count))

    def step(self):
        return qltk.WaitLoadWindow.step(self, self.current + 1, self.count)

# Return a 'natural' version of the tag for human-readable bits.
# Strips ~ and ~# from the start and runs it through a map (which
# the user can configure).
def tag(name, cap=True):
    try:
        if name[0] == "~":
            if name[1] == "#": name = name[2:]
            else: name = name[1:]
        parts = [_(HEADERS_FILTER.get(n, n)) for n in name.split("~")]
        if cap: parts = map(util.capitalize, parts)
        return " / ".join(parts)
    except IndexError:
        return _("Invalid tag name")

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

    widgets.watcher = SongWatcher()
    FSInterface()
    widgets.main = MainWindow()
    player.playlist.info = widgets.watcher

    # If the OSD module is not available, no signal is registered and
    # the reference is dropped. If it is available, a reference to it is
    # stored in its signal registered with SongWatcher.
    Osd()

    util.mkdir(const.DIR)
    import signal
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
