#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2004 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# $Id$

VERSION = "0.8"

import os, sys

# Give us a namespace for now.. FIXME: We need to remove this later.
class widgets(object): pass

# Standard Glade widgets wrapper.
class Widgets(object):
    def __init__(self, file = None, handlers = None, widget = None):
        file = file or "quodlibet.glade"
        domain = gettext.textdomain()
        if widget: self.widgets = gtk.glade.XML(file, widget, domain = domain)
        else: self.widgets = gtk.glade.XML(file, domain = domain)
        if handlers is not None:
            self.widgets.signal_autoconnect(handlers)
        self.get_widget = self.widgets.get_widget
        self.signal_autoconnect = self.widgets.signal_autoconnect

    def __getitem__(self, key):
        w = self.widgets.get_widget(key)
        if w: return w
        else: raise KeyError("no such widget %s" % key)

class MultiInstanceWidget(object):
    def __init__(self, file = None, widget = None):
        self.widgets = Widgets(handlers = self, widget = widget)

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

class Message(object):
    def __init__(self, kind, parent, title, description, buttons = None):
        buttons = buttons or gtk.BUTTONS_OK
        text = "<span size='xx-large'>%s</span>\n\n%s" % (title, description)
        self.dialog = gtk.MessageDialog(
            parent, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
            kind, buttons)
        self.dialog.set_markup(text)

    def run(self):
        self.dialog.run()
        self.dialog.destroy()

class ErrorMessage(Message):
    def __init__(self, *args):
        Message.__init__(self, gtk.MESSAGE_ERROR, *args)

class WarningMessage(Message):
    def __init__(self, *args):
        Message.__init__(self, gtk.MESSAGE_WARNING, *args)

# FIXME: replace with a standard About widget when using GTK 2.6.
class AboutWindow(MultiInstanceWidget):
    def __init__(self, parent):
        MultiInstanceWidget.__init__(self, widget = "about_window")
        self.window = self.widgets["about_window"]
        self.window.set_transient_for(parent)

    def close_about(self, *args):
        self.window.hide()

    def show(self):
        self.window.present()

class PreferencesWindow(MultiInstanceWidget):
    def __init__(self, parent):
        MultiInstanceWidget.__init__(self, widget = "prefs_window")
        self.window = self.widgets["prefs_window"]
        self.window.set_transient_for(parent)
        # Fill in the general checkboxes.
        for w in ["jump", "cover", "color", "tbp_space", "titlecase",
                  "splitval", "nbp_space", "windows", "ascii", "allcomments"]:
             self.widgets["prefs_%s_t" % w].set_active(config.state(w))
        self.widgets["prefs_addreplace"].set_active(
            config.getint("settings", "addreplace"))

        # Fill in the scanned directories.
        self.widgets["scan_opt"].set_text(config.get("settings", "scan"))
        self.widgets["mask_opt"].set_text(config.get("settings", "masked"))

        self.widgets["split_entry"].set_text(
            config.get("settings", "splitters"))
        self.widgets["gain_opt"].set_active(config.getint("settings", "gain"))

        driver = config.getint("pmp", "driver")
        self.widgets["pmp_combo"].set_active(driver)
        self.widgets["pmp_entry"].set_text(config.get("pmp", "location"))
        self.widgets["run_entry"].set_text(config.get("pmp", "command"))

        try: import gosd
        except ImportError:
            self.widgets["osd_combo"].set_sensitive(False)
            self.widgets["osd_color"].set_sensitive(False)
        self.widgets["osd_combo"].set_active(config.getint("settings", "osd"))
        color1, color2 = config.get("settings", "osdcolors").split()
        self.widgets["osd_color"].set_color(gtk.gdk.color_parse(color1))
        self.widgets["osd_color2"].set_color(gtk.gdk.color_parse(color2))

        self.widgets["osd_font"].set_font_name(
            config.get("settings", "osdfont"))

    def pmp_changed(self, combobox):
        driver = self.widgets["pmp_combo"].get_active()
        config.set('pmp', 'driver', str(driver))
        self.widgets["pmp_entry"].set_sensitive(driver == 1)
        self.widgets["run_entry"].set_sensitive(driver == 2)

    def pmp_location_changed(self, entry):
        config.set('pmp', 'location', entry.get_text())

    def pmp_command_changed(self, entry):
        config.set('pmp', 'command', entry.get_text())

    def set_color(self, button):
        color = self.widgets["osd_color"].get_color()
        ct1 = (color.red // 256, color.green // 256, color.blue // 256)
        color = self.widgets["osd_color2"].get_color()
        ct2 = (color.red // 256, color.green // 256, color.blue // 256)
        config.set("settings", "osdcolors",
                   "#%02x%02x%02x #%02x%02x%02x" % (ct1+ct2))

    def set_font(self, button):
        config.set("settings", "osdfont", button.get_font_name())

    def set_headers(self, *args):
        new_h = []
        if self.widgets["disc_t"].get_active(): new_h.append("~#disc")
        if self.widgets["track_t"].get_active(): new_h.append("~#track")
        for h in ["title", "version", "album", "part", "artist", "performer",
                  "date", "genre"]:
            if self.widgets[h + "_t"].get_active(): new_h.append(h)
        if self.widgets["filename_t"].get_active(): new_h.append("~basename")
        if self.widgets["length_t"].get_active(): new_h.append("~length")

        if self.widgets["titleversion_t"].get_active():
            try: new_h[new_h.index("title")] = "~title~version"
            except ValueError: pass

        if self.widgets["albumpart_t"].get_active():
            try: new_h[new_h.index("album")] = "~album~part"
            except ValueError: pass

        new_h.extend(self.widgets["extra_headers"].get_text().split())
        config.set("settings", "headers", " ".join(new_h))
        widgets.main.set_column_headers(new_h)

    def toggle_cover(self, toggle):
        config.set("settings", "cover", str(bool(toggle.get_active())))
        if config.state("cover"): widgets.main.enable_cover()
        else: widgets.main.disable_cover()

    def __getattr__(self, name):
        # A checkbox was changed.
        if name.startswith("toggle_"):
            name = name[7:]
            def toggle(toggle):
                config.set("settings", name, str(bool(toggle.get_active())))
            return toggle

        # A text entry was changed.
        elif name.startswith("text_change_"):
            name = name[12:]
            def set_text(entry):
                config.set("settings", name, entry.get_text())
            return set_text

        # A combobox was changed.
        elif name.startswith("combo_"):
            name = name[6:]
            def set_combo(combo):
                config.set("settings", name, str(combo.get_active()))
            return set_combo

        else: return object.__getattr__(self, name)

    def select_scan(self, *args):
        chooser = FileChooser(self.window,
                              _("Select Directories"), const.HOME)
        resp, fns = chooser.run()
        if resp == gtk.RESPONSE_OK:
            self.widgets["scan_opt"].set_text(":".join(fns))

    def select_masked(self, *args):
        if os.path.exists("/media"): path = "/media"
        elif os.path.exists("/mnt"): path = "/mnt"
        else: path = "/"
        chooser = FileChooser(self.window, _("Select Mount Points"), path)
        resp, fns = chooser.run()
        if resp == gtk.RESPONSE_OK:
            self.widgets["mask_opt"].set_text(":".join(fns))

    def prefs_closed(self, *args):
        self.window.hide()
        save_config()
        return True

    def show(self):
        headers = config.get("settings", "headers").split()

        # Fill in the header checkboxes.
        self.widgets["disc_t"].set_active("~#disc" in headers)
        self.widgets["track_t"].set_active("~#track" in headers)
        for h in ["title", "album", "part", "artist", "genre",
                  "date", "version", "performer"]:
            self.widgets[h + "_t"].set_active(h in headers)
        self.widgets["filename_t"].set_active("~basename" in headers)
        self.widgets["length_t"].set_active("~length" in headers)

        if "~title~version" in headers:
            self.widgets["title_t"].set_active(True)
            self.widgets["titleversion_t"].set_active(True)
            headers.remove("~title~version")
        else:
            self.widgets["titleversion_t"].set_active(False)

        if "~album~part" in headers:
            self.widgets["album_t"].set_active(True)
            self.widgets["albumpart_t"].set_active(True)
            headers.remove("~album~part")
        else:
            self.widgets["albumpart_t"].set_active(False)

        # Remove the standard headers, and put the rest in the list.
        for t in ["~#disc", "~#track", "album", "artist", "genre", "date",
                  "version", "performer", "title", "~basename", "part",
                  "~length"]:
            try: headers.remove(t)
            except ValueError: pass
        self.widgets["extra_headers"].set_text(" ".join(headers))

        self.window.present()

class DeleteDialog(object):
    def __init__(self, parent, files):
        self.dialog = gtk.Dialog(title = _("Deleting files"), parent = parent)
        self.dialog.set_property('border-width', 6)
        self.dialog.set_resizable(False)
        if os.path.isdir(os.path.expanduser("~/.Trash")):
            b = gtk.Button()
            b.add(gtk.HBox(spacing = 2))
            i = gtk.Image()
            i.set_from_stock(gtk.STOCK_DELETE, gtk.ICON_SIZE_BUTTON)
            b.child.pack_start(i)
            l = gtk.Label(_("_Move to Trash"))
            l.set_use_underline(True)
            l.set_mnemonic_widget(b)
            b.child.pack_start(l)
            self.dialog.add_action_widget(b, 0)

        self.dialog.add_button('gtk-cancel', 1)
        self.dialog.add_button('gtk-delete', 2)

        hbox = gtk.HBox()
        i = gtk.Image()
        i.set_from_stock(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_DIALOG)
        i.set_padding(12, 12)
        i.set_alignment(0.5, 0.0)
        hbox.pack_start(i, expand = False)
        vbox = gtk.VBox(spacing = 6)
        if len(files) == 1:
            l = _("Permanently delete this file?")
            exp = gtk.Expander("%s" % os.path.basename(files[0]))
        else:
            l = _("Permanently delete these files?")
            exp = gtk.Expander(_("%s and %d more...") %(
                os.path.basename(files[0]), len(files) - 1))

        lab = gtk.Label()
        lab.set_markup("<big><b>%s</b></big>" % l)
        lab.set_property('xalign', 0.0)
        vbox.pack_start(lab, expand = False)

        lab = gtk.Label("\n".join(map(util.unexpand, files)))
        lab.set_property('xalign', 0.1)
        lab.set_property('yalign', 0.0)
        exp.add(gtk.ScrolledWindow())
        exp.child.add_with_viewport(lab)
        exp.child.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        exp.child.child.set_shadow_type(gtk.SHADOW_NONE)
        vbox.pack_start(exp)
        hbox.pack_start(vbox)
        self.dialog.vbox.pack_start(hbox)

    def run(self):
        self.dialog.show_all()
        return self.dialog.run()

    def destroy(self, *args):
        self.dialog.destroy()

class WaitLoadWindow(object):
    def __init__(self, parent, count, text, initial):
        self.window = gtk.Window()
        self.sig = parent.connect('configure-event', self.recenter)
        self.parent = parent
        self.window.set_transient_for(parent)
        self.window.set_modal(True)
        self.window.set_decorated(False)
        self.window.set_resizable(False)
        self.window.add(gtk.Frame())
        self.window.child.set_shadow_type(gtk.SHADOW_OUT)
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
            b1 = gtk.Button(stock = 'gtk-stop')
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

        self.window.child.add(vbox)

        self.text = text
        self.paused = False
        self.quit = False

        self.label.set_markup(self.text % initial)
        self.window.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self.window.show_all()
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

    def recenter(self, *args):
        x, y = self.parent.get_position()
        dx, dy = self.parent.get_size()
        dx2, dy2 = self.window.get_size()
        self.window.move(x + dx/2 - dx2/2, y + dy/2 - dy2/2)

    def end(self):
        self.parent.disconnect(self.sig)
        self.window.destroy()

class BigCenteredImage(object):
    def __init__(self, title, filename):
        width = gtk.gdk.screen_width() / 2
        height = gtk.gdk.screen_height() / 2
        pixbuf = gtk.gdk.pixbuf_new_from_file(filename)

        x_rat = pixbuf.get_width() / float(width)
        y_rat = pixbuf.get_height() / float(height)

        if x_rat > 1 or y_rat > 1:
            if x_rat > y_rat:
                pixbuf = pixbuf.scale_simple(width,
                                             int(pixbuf.get_height()/y_rat),
                                             gtk.gdk.INTERP_BILINEAR)
            else:
                pixbuf = pixbuf.scale_simple(int(pixbuf.get_width()/x_rat),
                                             height, gtk.gdk.INTERP_BILINEAR)

        self.window = gtk.Window()
        self.window.set_title(title)
        self.window.set_decorated(False)
        self.window.set_position(gtk.WIN_POS_CENTER)
        self.window.set_modal(True)
        self.window.set_icon(pixbuf)
        self.window.add(gtk.Frame())
        self.window.child.set_shadow_type(gtk.SHADOW_OUT)
        self.window.child.add(gtk.EventBox())
        self.window.child.child.add(gtk.Image())
        self.window.child.child.child.set_from_pixbuf(pixbuf)

        # The eventbox
        self.window.child.child.connect('button-press-event', self.close)
        self.window.child.child.connect('key-press-event', self.close)
        self.window.show_all()

    def close(self, *args):
        self.window.destroy()

class TrayIcon(object):
    def __init__(self, pixbuf, activate_cb, popup_cb):
        try:
            import statusicon
        except:
            self.icon = None
            print _("W: Failed to initialize status icon.")
        else:
            self.icon = statusicon.StatusIcon(pixbuf)
            self.icon.connect("activate", activate_cb)
            self.icon.connect("popup-menu", popup_cb)
            print _("Initialized status icon.")

    def set_tooltip(self, tooltip):
        if self.icon:
            self.icon.set_tooltip(tooltip, "magic")

    tooltip = property(None, set_tooltip)

# A tray icon aware of UI policy -- left click shows/hides, right
# click brings up a popup menu
class HIGTrayIcon(TrayIcon):
    def __init__(self, pixbuf, window, menu):
        self._menu = menu
        self._window = window
        TrayIcon.__init__(self, pixbuf, self._showhide, self._popup)

    def _showhide(self, icon):
        if self._window.get_property('visible'):
            self._pos = self._window.get_position()
            self._window.hide()
        else:
            self._window.move(*self._pos)
            self._window.show()

    def _popup(self, *args):
        self._menu.popup(None, None, None, 2, 0)

class MmKeys(object):
    def __init__(self, cbs):
        try:
            import mmkeys
        except:
            print _("W: Failed to initialize multimedia key support.")
        else:
            self.keys = mmkeys.MmKeys()
            map(self.keys.connect, *zip(*cbs.items()))
            print _("Initialized multimedia key support.")

class Osd(object):
    def __init__(self):
        try:
            import gosd
        except:
            self.gosd = None
            print _("W: Failed to initialize OSD.")
        else:
            self.gosd = gosd
            self.level = 0
            self.window = None
            print _("Initialized OSD.")

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

class MainWindow(MultiInstanceWidget):
    def __init__(self):
        MultiInstanceWidget.__init__(self, widget = "main_window")
        self.last_dir = os.path.expanduser("~")
        self.window = self.widgets["main_window"]
        self.current_song = None

        settings = gtk.settings_get_default()
        accelgroup = gtk.accel_groups_from_object(self.window)[0]
        menubar = self.widgets["menubar1"]
        for menuitem in menubar.get_children():
            menu = menuitem.get_submenu()
            menu.set_accel_group(accelgroup)
            menu.set_accel_path('<quodlibet>/%s' %
                    menu.get_name().replace('_menu',''))

        if not os.path.exists(const.ACCELS):
            util.mkdir(const.DIR)
            accels = open(const.ACCELS, 'w')
            accels.write(
"""\
(gtk_accel_path "<quodlibet>/FiltersMenu/Random album" "<Control>m")
(gtk_accel_path "<quodlibet>/FiltersMenu/Random genre" "<Control>g")
(gtk_accel_path "<quodlibet>/SongMenu/Previous song" "<Control>Left")
(gtk_accel_path "<quodlibet>/SongMenu/Next song" "<Control>Right")
(gtk_accel_path "<quodlibet>/MusicMenu/Add Music..." "<Control>o")
(gtk_accel_path "<quodlibet>/SongMenu/Properties" "<Alt>Return")
(gtk_accel_path "<quodlibet>/SongMenu/Play song" "<Control>space")
(gtk_accel_path "<quodlibet>/MusicMenu/Quit" "<Control>q")
(gtk_accel_path "<quodlibet>/FiltersMenu/Random artist" "<Control>t")
(gtk_accel_path "<quodlibet>/SongMenu/Jump to playing song" "<Control>j")\
""")
            accels.close()

        gtk.accel_map_load(const.ACCELS)
        accelgroup.connect('accel-changed',
                lambda *args: gtk.accel_map_save(const.ACCELS))

        menu = Widgets(None, self, "songs_popup")
        self.cmenu = menu["songs_popup"]
        self.cmenu_w = menu

        # Oft-used pixmaps -- play/pause and small versions of the same.
        # FIXME: Switching to GTK 2.6 we can use the stock icons.
        self.playing = gtk.gdk.pixbuf_new_from_file("pause.png")
        self.paused = gtk.gdk.pixbuf_new_from_file("play.png")
        self.play_s = gtk.gdk.pixbuf_new_from_file_at_size("pause.png", 16,16)
        self.pause_s = gtk.gdk.pixbuf_new_from_file_at_size("play.png", 16,16)

        pp = gtk.gdk.pixbuf_new_from_file_at_size("previous.png", 16, 16)
        self.widgets["prev_menu"].get_image().set_from_pixbuf(pp)

        pn = gtk.gdk.pixbuf_new_from_file_at_size("next.png", 16, 16)
        self.widgets["next_menu"].get_image().set_from_pixbuf(pn)
        self.widgets["play_menu"].get_image().set_from_pixbuf(self.pause_s)

        # Set up the tray icon; initialize the menu widget even if we
        # don't end up using it for simplicity.
        self.tray_menu = Widgets(None, self, "tray_popup")
        self.tray_menu_play = self.tray_menu["play_popup_menu"].get_image()
        self.tray_menu_play.set_from_pixbuf(self.pause_s)
        self.tray_menu["prev_popup_menu"].get_image().set_from_pixbuf(pp)
        self.tray_menu["next_popup_menu"].get_image().set_from_pixbuf(pn)

        p = gtk.gdk.pixbuf_new_from_file_at_size("quodlibet.png", 16, 16)
        self.icon = HIGTrayIcon(p, self.window, self.tray_menu["tray_popup"])

        # Set up the main song list store.
        self.songlist = self.widgets["songlist"]
        self.songlist.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        widgets.songs = gtk.ListStore(object, int)

        # Build a model and view for our ComboBoxEntry.
        liststore = gtk.ListStore(str)
        self.widgets["query"].set_model(liststore)
        self.widgets["query"].set_text_column(0)
        cell = gtk.CellRendererText()
        self.widgets["query"].pack_start(cell, True)
        self.widgets["query"].child.connect('activate', self.text_parse)
        self.widgets["query"].child.connect('changed', self.test_filter)
        self.widgets["search_button"].connect('clicked', self.text_parse)

        # Initialize volume controls.
        self.widgets["volume"].set_value(config.getfloat("memory", "volume"))

        self.widgets["shuffle_t"].set_active(config.state("shuffle"))
        self.widgets["repeat_t"].set_active(config.state("repeat"))

        self.widgets["query"].child.set_text(config.get("memory", "query"))
        self.set_column_headers(config.get("settings", "headers").split())
        self.text_parse()

        self.albumfn = None
        self._time = (0, 1)
        gtk.timeout_add(300, self._update_time)
        self.text = self.widgets["currentsong"]
        self.image = self.widgets["albumcover"]
        self.iframe = self.widgets["iframe"]
        self.volume = self.widgets["volume"]

        self.open_fifo()
        self.keys = MmKeys({"mm_prev": self.previous_song,
                            "mm_next": self.next_song,
                            "mm_playpause": self.play_pause})
        self.osd = Osd()

        # Show main window.
        self.restore_size()
        self.window.show()

    def restore_size(self):
        try: w, h = map(int, config.get("memory", "size").split())
        except ValueError: pass
        else:
            self.window.set_property("default-width", w)
            self.window.set_property("default-height", h)

    def open_fifo(self):
        if not os.path.exists(const.CONTROL):
            util.mkdir(const.DIR)
            os.mkfifo(const.CONTROL, 0600)
        self.fifo = os.open(const.CONTROL, os.O_NONBLOCK)
        gtk.input_add(self.fifo, gtk.gdk.INPUT_READ, self._input_check)

    def _input_check(self, source, condition):
        c = os.read(source, 1)
        toggles = { "@": "repeat_t", "&": "shuffle_t" }
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
            wid = self.widgets[toggles[c]]
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
                print "W: Unable to load %s" % filename
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
        if paused:
            self.widgets["play_image"].set_from_pixbuf(self.paused)
            self.widgets["play_menu"].get_image().set_from_pixbuf(
                self.pause_s)
            self.tray_menu_play.set_from_pixbuf(self.pause_s)
            self.widgets["play_menu"].child.set_text(_("Play _song"))
            self.tray_menu["play_popup_menu"].child.set_text(_("_Play"))
        else:
            self.widgets["play_image"].set_from_pixbuf(self.playing)
            self.widgets["play_menu"].get_image().set_from_pixbuf(
                self.play_s)
            self.widgets["play_menu"].get_image().set_from_pixbuf(self.play_s)
            self.tray_menu_play.set_from_pixbuf(self.play_s)
            self.widgets["play_menu"].child.set_text(_("Pause _song"))
            self.tray_menu["play_popup_menu"].child.set_text(_("_Pause"))
        self.widgets["play_menu"].child.set_use_underline(True)
        self.tray_menu["play_popup_menu"].child.set_use_underline(True)

    def set_time(self, cur, end):
        self._time = (cur, end)

    def _update_time(self):
        cur, end = self._time
        self.widgets["song_pos"].set_value(cur)
        self.widgets["song_timer"].set_text("%d:%02d/%d:%02d" %
                            (cur // 60000, (cur % 60000) // 1000,
                             end // 60000, (end % 60000) // 1000))
        return True

    def _missing_song(self, song):
        path = (player.playlist.get_playlist().index(song),)
        iter = widgets.songs.get_iter(path)
        widgets.songs.remove(iter)
        statusbar = self.widgets["statusbar"]
        statusbar.set_text(_("Could not play %s.") % song['~filename'])
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
        for wid in ["web_button", "next_button", "prop_menu",
                    "play_menu", "jump_menu", "next_menu", "prop_button",
                    "filter_genre_menu", "filter_album_menu",
                    "filter_artist_menu"]:
            self.widgets[wid].set_sensitive(bool(song))
        if song:
            self.widgets["song_pos"].set_range(0, player.length)
            self.widgets["song_pos"].set_value(0)
            cover_f = None
            cover = song.find_cover()
            if hasattr(cover, "write"):
                cover_f = cover
                cover = cover.name
            if cover != self.albumfn:
                try:
                    p = gtk.gdk.pixbuf_new_from_file_at_size(cover, 100, 100)
                except:
                    self.image.set_from_pixbuf(None)
                    self.disable_cover()
                    self.albumfn = None
                else:
                    self.image.set_from_pixbuf(p)
                    if config.state("cover"): self.enable_cover()
                    self.albumfn = cover
            for h in ['genre', 'artist', 'album']:
                self.widgets["filter_%s_menu"%h].set_sensitive(
                    not song.unknown(h))
            if cover_f: cover_f.close()

            self.update_markup(song)
        else:
            self.image.set_from_pixbuf(None)
            self.widgets["song_pos"].set_range(0, 1)
            self.widgets["song_pos"].set_value(0)
            self._time = (0, 1)
            self.update_markup(None)

        # Update the currently-playing song in the list by bolding it.
        last_song = self.current_song
        self.current_song = song
        col = 0

        def update_if_last_or_current(model, path, iter):
            if model[iter][col] is song:
                model[iter][col + 1] = 700
                model.row_changed(path, iter)
            elif model[iter][col] is last_song:
                model[iter][col + 1] = 400
                model.row_changed(path, iter)

        widgets.songs.foreach(update_if_last_or_current)
        gc.collect()
        if song and config.getboolean("settings", "jump"):
            self.jump_to_current()
        return False

    def gtk_main_quit(self, *args):
        gtk.main_quit()

    def save_widths(self, column, width):
        config.set("memory", "widths", " ".join(
            [str(x.get_width()) for x in self.songlist.get_columns()]))

    def save_size(self, widget, event):
        config.set("memory", "size", "%d %d" % (event.width, event.height))

    def showhide_widget(self, box, on):
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
        if not self.widgets["song_scroller"].get_property("visible"):
            self.window.set_geometry_hints(
                None, max_height = height - dy, max_width = 32000)

    def showhide_searchbox(self, toggle):
        self.showhide_widget(self.widgets["query_hbox"], toggle.get_active())
        config.set("memory", "show_search", str(toggle.get_active()))

    def showhide_playlist(self, toggle):
        self.showhide_widget(self.widgets["song_scroller"],
                             toggle.get_active())
        config.set("memory", "show_playlist", str(toggle.get_active()))

    def open_website(self, button):
        song = self.current_song
        site = song.website().replace("\\", "\\\\").replace("\"", "\\\"")
        for s in ["sensible-browser"]+os.environ.get("BROWSER","").split(":"):
            if util.iscommand(s):
                if "%s" in s:
                    s = s.replace("%s", '"' + site + '"')
                    s = s.replace("%%", "%")
                else: s += " \"%s\"" % site
                print _("Opening web browser: %s") % s
                if os.system(s + " &") == 0: break
        else:
            ErrorMessage(self.window,
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
        else: self.songlist.scroll_to_cell(path)

    def next_song(self, *args):
        player.playlist.next()

    def previous_song(self, *args):
        player.playlist.previous()

    def toggle_repeat(self, button):
        player.playlist.repeat = button.get_active()
        config.set("settings", "repeat", str(bool(button.get_active())))

    def show_about(self, menuitem):
        widgets.about.show()

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
        self.widgets["shuffle_t"].set_active(False)

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
            if hasattr(cover, "write"):
                cover_f = cover
                cover = cover.name
            BigCenteredImage(self.current_song.comma("album"), cover)

    def rebuild(self, activator, hard = False):
        window = WaitLoadWindow(self.window, len(library) // 7,
                                _("Quod Libet is scanning your library. "
                                  "This may take several minutes.\n\n"
                                  "%d songs reloaded\n%d songs removed"),
                                (0, 0))
        iter = 7
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

    def pmp_upload(self, *args):
        selection = self.songlist.get_selection()
        model, rows = selection.get_selected_rows()
        songs = [model[row][0] for row in rows]
        try:
            window = WaitLoadWindow(self.window, len(songs),
                                    _("Uploading song %d/%d"),
                                    (0, len(songs)))
            d = pmp.drivers[config.getint("pmp", "driver")](songs, window)
            d.run()
            window.end()
        except pmp.error, s:
            window.end()
            e = ErrorMessage(self.window, _("Unable to upload files"), s)
            e.run()

    # Set up the preferences window.
    def open_prefs(self, activator):
        widgets.preferences.show()

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
        self.prep_main_popup(header)
        self.cmenu.popup(None,None,None, event.button, event.time)
        return True

    def songs_popup_menu(self, view):
        path, col = view.get_cursor()
        header = col.header_name
        self.prep_main_popup(header)
        self.cmenu.popup(None, None, None, 1, 0)

    def song_col_filter(self, item):
        view = self.songlist
        path, col = view.get_cursor()
        header = col.header_name
        self.filter_on_header(header)

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
        view = self.songlist
        selection = self.songlist.get_selection()
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
        view = self.songlist
        selection = self.songlist.get_selection()
        model, rows = selection.get_selected_rows()
        songs = [model[r][0] for r in rows]
        filenames = [song["~filename"] for song in songs]
        filenames.sort()
        d = DeleteDialog(self.window, filenames)
        resp = d.run()
        d.destroy()
        if resp == 1: return
        else:
            if resp == 0: s = _("Moving %d/%d.")
            else: s = _("Deleting %d/%d.")
            w = WaitLoadWindow(self.window, len(songs), s, (0, len(songs)))
            trash = os.path.expanduser("~/.Trash")
            for song in songs:
                filename = song["~filename"]
                try:
                    if resp == 0:
                        basename = os.path.basename(filename)
                        shutil.move(filename, os.path.join(trash, basename))
                    else:
                        os.unlink(filename)
                    library.remove(song)
                except:
                    ErrorMessage(self.window,
                                 _("Unable to remove file"),
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
        if song:
            SongProperties([song])
            
    def song_properties(self, item):
        selection = self.songlist.get_selection()
        model, rows = selection.get_selected_rows()
        songrefs = [model[row][0] for row in rows]
        SongProperties(songrefs)

    def prep_main_popup(self, header):
        if not config.getint("pmp", "driver"):
            self.cmenu_w["pmp_sep"].hide()
            self.cmenu_w["pmp_upload"].hide()
        else:
            self.cmenu_w["pmp_sep"].show()
            self.cmenu_w["pmp_upload"].show()
        if header not in ["genre", "artist", "album", "~album~part"]:
            self.cmenu_w["filter_column"].show()
            if header.startswith("~#"): header = header[2:]
            elif header.startswith("~"): header = header[1:]
            header = tag(header)
            self.cmenu_w["filter_column"].child.set_text(
                _("_Filter on this column (%s)") % _(header))
            self.cmenu_w["filter_column"].child.set_use_underline(True)
        else:
            self.cmenu_w["filter_column"].hide()

    # Grab the text from the query box, parse it, and make a new filter.
    def text_parse(self, *args):
        text = self.widgets["query"].child.get_text()
        config.set("memory", "query", text)
        text = text.decode("utf-8").strip()
        orig_text = text
        if text and "#" not in text and "=" not in text and "/" not in text:
            # A simple search, not regexp-based.
            parts = ["* = /" + sre.escape(p) + "/" for p in text.split()]
            text = "&(" + ",".join(parts) + ")"
            # The result must be well-formed, since no /s were
            # in the original string and we escaped it.

        if player.playlist.playlist_from_filter(text):
            m = self.widgets["query"].get_model()
            for i, row in enumerate(iter(m)):
                 if row[0] == orig_text:
                     m.remove(m.get_iter((i,)))
                     break
            else:
                if len(m) > 10: m.remove(m.get_iter((10,)))
            m.prepend([orig_text])
            self.set_entry_color(self.widgets["query"].child, "black")
            self.refresh_songlist()
            self.widgets["query"].child.set_text(orig_text)
        return True

    def filter_on_header(self, header, songs = None):
        if songs is None:
            selection = self.songlist.get_selection()
            model, rows = selection.get_selected_rows()
            songs = [model[row][0] for row in rows]

        if header.startswith("~#"):
            nheader = header[2:]
            values = [song.get(header, 0) for song in songs]
            queries = ["#(%s = %d)" % (nheader, i) for i in values]
            self.make_query("|(" + ", ".join(queries) + ")")
        else:
            values = {}
            for song in songs:
                if header in song:
                    for val in song.list(header):
                        values[val] = True

            text = "|".join([sre.escape(s) for s in values.keys()])
            if header.startswith("~"): header = header[1:]
            self.make_query(u"%s = /^(%s)$/c" % (header, text))

    def cols_changed(self, view):        
        headers = [col.header_name for col in view.get_columns()]
        if len(headers) == len(config.get("settings", "headers").split()):
            # Not an addition or removal (handled separately)
            config.set("settings", "headers", " ".join(headers))

    def make_query(self, query):
        self.widgets["query"].child.set_text(query.encode('utf-8'))
        self.widgets["search_button"].clicked()

    # Try and construct a query, but don't actually run it; change the color
    # of the textbox to indicate its validity (if the option to do so is on).
    def test_filter(self, textbox):
        if not config.state("color"): return
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
        markup = '<span foreground="%s">%s</span>'%(
            color, util.escape(text))
        layout.set_markup(markup)

    # Resort based on the header clicked.
    def set_sort_by(self, header, tag):
        s = header.get_sort_order()
        if not header.get_sort_indicator() or s == gtk.SORT_DESCENDING:
            s = gtk.SORT_ASCENDING
        else: s = gtk.SORT_DESCENDING
        for h in self.songlist.get_columns():
            h.set_sort_indicator(False)
        header.set_sort_indicator(True)
        header.set_sort_order(s)
        player.playlist.sort_by(tag, s == gtk.SORT_DESCENDING)
        self.refresh_songlist()

    # Clear the songlist and readd the songs currently wanted.
    def refresh_songlist(self):

        selection = self.songlist.get_selection()
        model, rows = selection.get_selected_rows()
        selected = dict.fromkeys([model[row][0]['~filename'] for row in rows])

        self.songlist.set_model(None)
        widgets.songs.clear()
        statusbar = self.widgets["statusbar"]
        length = 0
        for song in player.playlist:
            wgt = ((song is self.current_song and 700) or 400)
            widgets.songs.append([song, wgt])
            length += song["~#length"]
        i = len(list(player.playlist))
        if i != 1: statusbar.set_text(
            _("%d songs (%s)") % (i, util.format_time_long(length)))
        else: statusbar.set_text(
            _("%d song (%s)") % (i, util.format_time_long(length)))
        self.songlist.set_model(widgets.songs)

        selection = self.songlist.get_selection()
        for i, row in enumerate(iter(widgets.songs)):
            if row[0]['~filename'] in selected:
                selection.select_path(i)
        del selected

        gc.collect()

    # Build a new filter around our list model, set the headers to their
    # new values.
    def set_column_headers(self, headers):
        if len(headers) == 0: return
        SHORT_COLS = ["tracknumber", "discnumber", "~length"]
        try: ws = map(int, config.get("memory", "widths").split())
        except: ws = []

        if len(ws) != len(headers):
            width = self.songlist.get_allocation()[2]
            c = sum([(x.startswith("~#") and 0.2) or 1 for x in headers])
            width = int(width // c)
            ws = [width] * len(headers)
            
        for c in self.songlist.get_columns(): self.songlist.remove_column(c)

        def cell_data(column, cell, model, iter):
            cell.set_property('text',
                              model[iter][0].get(column.header_name, ""))
        
        for i, t in enumerate(headers):
            render = gtk.CellRendererText()
            title = tag(t)
            column = gtk.TreeViewColumn(title, render,
                                        weight = 1)
            column.header_name = t
            column.set_resizable(True)
            if t in SHORT_COLS or t.startswith("~#"):
                render.set_fixed_size(-1, -1)
            else:
                column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
                column.set_fixed_width(ws[i])
            column.set_clickable(True)
            column.set_reorderable(True)
            column.set_sort_indicator(False)
            column.connect('clicked', self.set_sort_by, t)
            column.connect('notify::width', self.save_widths)
            column.set_cell_data_func(render, cell_data)
            self.songlist.append_column(column)

class AddTagDialog(object):
    def __init__(self, parent, can_change):
        if can_change == True:
            self.limit = False
            can = ["title", "version", "artist", "album",
                        "performer", "discnumber"]
        else:
            self.limit = True
            can = can_change
        can.sort()

        self.dialog = gtk.Dialog(parent = parent, title = _("Add a new tag"))
        self.dialog.connect('close', self.destroy)
        self.dialog.set_property('border-width', 12)
        self.dialog.set_resizable(False)
        self.dialog.add_buttons('gtk-cancel', gtk.RESPONSE_CANCEL,
                                'gtk-add', gtk.RESPONSE_OK)
        self.dialog.vbox.set_property('spacing', 9)
        self.dialog.set_default_response(gtk.RESPONSE_OK)
        table = gtk.Table(2, 2)
        table.set_row_spacings(6)
        table.set_col_spacings(9)
        
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

        self.dialog.vbox.pack_start(table)

    def get_tag(self):
        try: return self.tag.child.get_text().lower().strip()
        except AttributeError:
            return self.tag.get_model()[self.tag.get_active()][0]

    def get_value(self):
        return self.val.get_text().decode("utf-8")

    def run(self):
        self.dialog.show_all()
        try: self.tag.child.set_text("")
        except AttributeError: pass
        self.val.set_text("")
        try: self.tag.child.set_activates_default(True)
        except AttributeError: pass
        self.val.set_activates_default(True)
        self.tag.grab_focus()
        return self.dialog.run()

    def destroy(self, *args):
        self.dialog.destroy()

class SongProperties(MultiInstanceWidget):
    def __init__(self, songrefs):
        MultiInstanceWidget.__init__(self, widget = "properties_window")
        menu = Widgets("quodlibet.glade", self, "props_popup")
        self.menu = menu["props_popup"]
        self.menu_w = menu

        self.window = self.widgets['properties_window']
        self.save_edit = self.widgets['songprop_save']
        self.revert = self.widgets['songprop_revert']
        self.artist = self.widgets['songprop_artist']
        self.played = self.widgets['songprop_played']
        self.title = self.widgets['songprop_title']
        self.album = self.widgets['songprop_album']
        self.filename = self.widgets['songprop_file']
        self.view = self.widgets['songprop_view']
        self.add = self.widgets['songprop_add']
        self.remove = self.widgets['songprop_remove']

        # comment, value, use-changes, edit, deleted
        self.model = gtk.ListStore(str, str, bool, bool, bool, str)
        self.view.set_model(self.model)
        selection = self.view.get_selection()
        selection.connect('changed', self.songprop_selection_changed)
        
        render = gtk.CellRendererToggle()
        column = gtk.TreeViewColumn(_('Write'), render, active = 2,
                                    activatable = 3)
        render.connect('toggled', self.songprop_toggle, self.model)
        self.view.append_column(column)
        render = gtk.CellRendererText()
        render.connect('edited', self.songprop_edit, self.model, 0)
        column = gtk.TreeViewColumn(_('Tag'), render, text=0)
        self.view.append_column(column)
        render = gtk.CellRendererText()
        render.connect('edited', self.songprop_edit, self.model, 1)
        column = gtk.TreeViewColumn(_('Value'), render, markup = 1,
                                    editable = 3, strikethrough=4)
        self.view.append_column(column)

        # select active files
        self.fview = self.widgets['songprop_files']
        self.fview_scroll = self.widgets['songprop_files_scroll']
        self.fbasemodel = gtk.ListStore(object, object, str, str, str)
        self.fmodel = gtk.TreeModelSort(self.fbasemodel)
        self.fview.set_model(self.fmodel)
        selection = self.fview.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        selection.connect('changed', self.songprop_files_changed)
        column = gtk.TreeViewColumn(_('File'), gtk.CellRendererText(), text=2)
        column.set_sort_column_id(2)
        self.fview.append_column(column)
        column = gtk.TreeViewColumn(_('Path'), gtk.CellRendererText(), text=3)
        column.set_sort_column_id(4)
        self.fview.append_column(column)
        for song in songrefs:
            self.fbasemodel.append(
                row=[song, None, song.get('~basename', ''),
                     song.get('~dirname', ''), song['~filename']])

        # tag by pattern
        self.tbp_entry = self.widgets["songprop_tbp_combo"].child
        self.tbp_view = self.widgets["songprop_tbp_view"]
        self.tbp_model = gtk.ListStore(int) # fake first one
        self.save_tbp = self.widgets['prop_tbp_save']
        self.tbp_preview = self.widgets['tbp_preview']
        self.tbp_entry.connect('changed', self.tbp_changed)
        self.tbp_headers = []
        self.widgets["prop_tbp_addreplace"].set_active(
            config.getint("settings", "addreplace"))

        # rename by pattern
        self.nbp_preview = self.widgets['nbp_preview']
        self.nbp_entry = self.widgets["songprop_nbp_combo"].child
        self.nbp_view = self.widgets["songprop_nbp_view"]
        self.nbp_model = gtk.ListStore(object, object, str, str)
        self.nbp_view.set_model(self.nbp_model)
        self.save_nbp = self.widgets['prop_nbp_save']
        self.nbp_entry.connect('changed', self.nbp_changed)
        column = gtk.TreeViewColumn(_('File'), gtk.CellRendererText(),
                                    text = 2)
        self.nbp_view.append_column(column)
        column = gtk.TreeViewColumn(_('New Name'), gtk.CellRendererText(),
                                    text = 3)
        self.nbp_view.append_column(column)

        for w in ["tbp_space", "titlecase", "splitval", "nbp_space",
                  "windows", "ascii"]:
            self.widgets["prop_%s_t" % w].set_active(config.state(w))

        # track numbering
        self.tn_preview = self.widgets['prop_tn_preview']
        self.tn_view = self.widgets["prop_tn_view"]
        self.tn_model = gtk.ListStore(object, object, str, str)
        self.tn_view.set_model(self.tn_model)
        self.save_tn = self.widgets['prop_tn_save']
        column = gtk.TreeViewColumn(_('File'), gtk.CellRendererText(),
                                    text = 2)
        self.tn_view.append_column(column)
        column = gtk.TreeViewColumn(_('Track'), gtk.CellRendererText(),
                                    text = 3)
        self.tn_view.append_column(column)

        # select all files, causing selection update to fill the info
        selection.select_all()
        self.window.show()

    def songprop_close(self, *args):
        self.fview.set_model(None)
        self.fbasemodel.clear()
        self.fmodel.clear_cache()
        self.model.clear()
        self.window.destroy()
        self.menu.destroy()

    def songprop_save_click(self, button):
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

        win = WritingWindow(self.window, len(self.songrefs))
        for song in self.songrefs:
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
                except None:
                    ErrorMessage(self.window,
                                 _("Unable to edit song"),
                                 _("Saving <b>%s</b> failed. The file may be "
                                   "read-only, corrupted, or you do not have "
                                   "permission to edit it.")%(
                        util.escape(song('~basename')))).run()
                    library.reload(song)
                    player.playlist.refilter()
                    widgets.main.refresh_songlist()
                    break
                songref_update_view(song)

            if win.step(): break

        win.end()
        self.save_edit.set_sensitive(False)
        self.revert.set_sensitive(False)
        self.fill_property_info()
        if widgets.main.current_song in self.songrefs:
            widgets.main.update_markup(widgets.main.current_song)

    def songprop_revert_click(self, button):
        self.save_edit.set_sensitive(False)
        self.revert.set_sensitive(False)
        self.fill_property_info()

    def songprop_toggle(self, renderer, path, model):
        row = model[path]
        row[2] = not row[2] # Edited
        self.save_edit.set_sensitive(True)
        self.revert.set_sensitive(True)

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

    def songprop_edit(self, renderer, path, new, model, colnum):
        row = model[path]
        date = sre.compile("^\d{4}(-\d{2}-\d{2})?$")
        if row[0] == "date" and not date.match(new):
            WarningMessage(self.window, _("Invalid date format"),
                           _("Invalid date: <b>%s</b>.\n\n"
                             "The date must be entered in YYYY or "
                             "YYYY-MM-DD format.") % new).run()
        elif row[colnum].replace('<i>','').replace('</i>','') != new:
            row[colnum] = util.escape(new)
            row[2] = True # Edited
            row[4] = False # not Deleted
            self.enable_save()

    def songprop_selection_changed(self, selection):
        model, iter = selection.get_selected()
        may_remove = bool(selection.count_selected_rows()) and model[iter][3]
        self.remove.set_sensitive(may_remove)

    def songprop_files_toggled(self, toggle):
        if toggle.get_active(): self.fview_scroll.show()
        else: self.fview_scroll.hide()

    def songprop_files_changed(self, selection):
        songrefs = []
        def get_songrefs(model, path, iter, songrefs):
            songrefs.append(model[path][0])
        selection.selected_foreach(get_songrefs, songrefs)
        if len(songrefs): self.songrefs = songrefs
        self.fill_property_info()

    def prep_prop_menu(self, row):
        self.menu_w["split_album"].hide()
        self.menu_w["split_title"].hide()
        self.menu_w["split_performer"].hide()
        self.menu_w["split_arranger"].hide()
        self.menu_w["special_sep"].hide()
        spls = config.get("settings", "splitters")

        self.menu_w["split_into_list"].set_sensitive(
            len(util.split_value(row[1], spls)) > 1)

        if row[0] == "album":
            self.menu_w["split_album"].show()
            self.menu_w["special_sep"].show()
            self.menu_w["split_album"].set_sensitive(
                util.split_album(row[1])[1] is not None)

        if row[0] == "title":
            self.menu_w["split_title"].show()
            self.menu_w["special_sep"].show()
            self.menu_w["split_title"].set_sensitive(
                util.split_title(row[1], spls)[1] != [])

        if row[0] == "artist":
            self.menu_w["split_performer"].show()
            self.menu_w["split_arranger"].show()
            self.menu_w["special_sep"].show()
            ok = (util.split_people(row[1], spls)[1] != [])
            self.menu_w["split_performer"].set_sensitive(ok)
            self.menu_w["split_arranger"].set_sensitive(ok)

    def prop_popup_menu(self, view):
        path, col = view.get_cursor()
        row = view.get_model()[path]
        self.prep_prop_menu(row)
        self.menu.popup(None, None, None, 1, 0)

    def prop_button_press(self, view, event):
        if event.button != 3:
            return False
        x, y = map(int, [event.x, event.y])
        try: path, col, cellx, celly = view.get_path_at_pos(x, y)
        except TypeError: return True
        view.grab_focus()
        selection = view.get_selection()
        if not selection.path_is_selected(path):
            view.set_cursor(path, col, 0)
        row = view.get_model()[path]
        self.prep_prop_menu(row)
        self.menu.popup(None, None, None, event.button, event.time)
        return True

    def songprop_add(self, button):
        add = AddTagDialog(self.window, self.songinfo.can_change(None))

        while True:
            resp = add.run()
            if resp != gtk.RESPONSE_OK: break
            comment = add.get_tag()
            value = add.get_value()
            date = sre.compile("^\d{4}(-\d{2}-\d{2})?$")
            if not self.songinfo.can_change(comment):
                ErrorMessage(
                    self.window, _("Invalid tag"),
                    _("Invalid tag <b>%s</b>\n\nThe files currently"
                      " selected do not support editing this tag.")%
                    util.escape(comment)).run()

            elif comment == "date" and not date.match(value):
                ErrorMessage(self.window, _("Invalid date"),
                               _("Invalid date: <b>%s</b>.\n\n"
                                 "The date must be entered in YYYY or "
                                 "YYYY-MM-DD format.") % value).run()
            else:
                self.add_new_tag(comment, value)
                break

        add.destroy()

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
        self.enable_save()

    def enable_save(self):
        self.save_edit.set_sensitive(True)
        self.revert.set_sensitive(True)
        if self.window.get_title()[0] != "*":
            self.window.set_title("* " + self.window.get_title())

    def songprop_remove(self, *args):
        model, iter = self.view.get_selection().get_selected()
        row = model[iter]
        if row[0] in self.songinfo:
            row[2] = True # Edited
            row[4] = True # Deleted
        else:
            model.remove(iter)
        self.enable_save()

    def fill_property_info(self):
        from library import AudioFileGroup
        songinfo = AudioFileGroup(self.songrefs)
        self.songinfo = songinfo
        editable = bool(songinfo.can_change(None))
        self.widgets["songprop_add"].set_sensitive(editable)
        self.widgets["songprop_remove"].set_sensitive(editable)
        self.widgets["songprop_tbp_combo"].set_sensitive(editable)
        
        if len(self.songrefs) == 1:
            self.window.set_title(_("%s - Properties") %
                    self.songrefs[0]["title"])
        elif len(self.songrefs) > 1:
            self.window.set_title(_("%s and %d more - Properties") %
                    (self.songrefs[0]["title"], len(self.songrefs)-1))
        else:
            raise ValueError("Properties of no songs?")

        self.artist.set_markup(songinfo['artist'].safenicestr())
        self.title.set_markup(songinfo['title'].safenicestr())
        self.album.set_markup(songinfo['album'].safenicestr())
        filename = util.unexpand(songinfo['~filename'].safenicestr())
        self.filename.set_markup(filename)

        if len(self.songrefs) > 1:
            listens = sum([song["~#playcount"] for song in self.songrefs])
            if listens == 1: s = _("1 song heard")
            else: s = _("%d songs heard") % listens
            self.played.set_markup("<i>%s</i>" % s)
        else:
            self.played.set_text(self.songrefs[0].get_played())

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

        self.add.set_sensitive(bool(songinfo.can_change()))
        self.save_edit.set_sensitive(False)
        self.revert.set_sensitive(False)

        self.songprop_tbp_preview()
        self.songprop_nbp_preview()
        self.songprop_tn_fill()

    def songprop_tn_fill(self, *args):
        self.tn_model.clear()
        self.widgets["prop_tn_total"].set_value(len(self.songrefs))
        for song in self.songrefs:
            self.tn_model.append(row = [song, None, song('~basename'),
                                        song.get("tracknumber", "")])
        tn_change = self.songinfo.can_change("tracknumber")
        self.widgets["prop_tn_start"].set_sensitive(tn_change)
        self.widgets["prop_tn_total"].set_sensitive(tn_change)
        self.tn_preview.set_sensitive(tn_change)
        self.tn_view.set_reorderable(tn_change)
            

    def songprop_tn_preview(self, *args):
        start = self.widgets["prop_tn_start"].get_value_as_int()
        total = self.widgets["prop_tn_total"].get_value_as_int()
        def refill(model, path, iter):
            if total: s = "%d/%d" % (path[0] + start, total)
            else: s = str(path[0] + start)
            model[iter][3] = s
        self.tn_model.foreach(refill)
        self.tn_preview.set_sensitive(False)
        self.save_tn.set_sensitive(True)

    def prop_tn_changed(self, *args):
        self.tn_preview.set_sensitive(True)
        self.save_tn.set_sensitive(False)

    def tn_save(self, *args):
        win = WritingWindow(self.window, len(self.songrefs))
        def settrack(model, path, iter):
            song = model[iter][0]
            track = model[iter][3]
            song["tracknumber"] = track
            try: song.write()
            except:
                ErrorMessage(self.window,
                             _("Unable to edit song"),
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
        self.tn_model.foreach(settrack)
        self.fill_property_info()
        self.save_tn.set_sensitive(False)
        win.end()

    def songprop_nbp_preview(self, *args):
        self.nbp_model.clear()
        pattern = self.nbp_entry.get_text().decode('utf-8')

        underscore = self.widgets["prop_nbp_space_t"].get_active()
        windows = self.widgets["prop_windows_t"].get_active()
        ascii = self.widgets["prop_ascii_t"].get_active()

        try:
            pattern = util.FileFromPattern(pattern)
        except ValueError: 
            d = ErrorMessage(self.window,
                             _("Pattern with subdirectories is not absolute"),
                             _("The pattern\n\t<b>%s</b>\ncontains / but "
                               "does not start from root. To avoid misnamed "
                               "directories, root your pattern by starting "
                               "it from the / directory.")%(
                util.escape(pattern)))
            d.run()
            return
            
        for song in self.songrefs:
            newname = pattern.match(song)
            if underscore: newname = newname.replace(" ", "_")
            if windows:
                for c in '\\:*?;"<>|':
                    newname = newname.replace(c, "_")
            if ascii:
                newname = "".join(map(lambda c: ((ord(c) < 127 and c) or "_"),
                                      newname))
            self.nbp_model.append(row=[song, None, song('~basename'), newname])
        self.nbp_preview.set_sensitive(False)
        self.save_nbp.set_sensitive(True)

    def nbp_save(self, *args):
        pattern = self.nbp_entry.get_text().decode('utf-8')
        win = WritingWindow(self.window, len(self.songrefs))

        def rename(model, path, iter):
            song = model[path][0]
            oldname = model[path][2]
            newname = model[path][3]
            try:
                library.rename(song, newname)
                songref_update_view(song)
            except:
                ErrorMessage(self.window,
                             _("Unable to rename file"),
                             _("Renaming <b>%s</b> to <b>%s</b> failed. "
                               "Possibly the target file already exists, "
                               "or you do not have permission to make the "
                               "new file or remove the old one.") %(
                    util.escape(oldname), util.escape(newname))).run()
                return True
            return win.step()
        self.nbp_model.foreach(rename)

        def update_filename(model, path, iter):
            song = model[path][0]
            model[path][2] = song('~basename')
            model[path][3] = song('~dirname')
            model[path][3] = song['~filename']
        self.fbasemodel.foreach(update_filename)

        self.fill_property_info()
        self.save_nbp.set_sensitive(False)
        win.end()

    def tbp_changed(self, *args):
        self.tbp_preview.set_sensitive(True)
        self.save_tbp.set_sensitive(False)

    def nbp_changed(self, *args):
        self.nbp_preview.set_sensitive(True)
        self.save_nbp.set_sensitive(False)

    def tbp_edited(self, cell, path, text, model, col):
        model[path][col] = text
        self.tbp_preview.set_sensitive(True)

    def songprop_tbp_preview(self, *args):
        # build the pattern
        pattern_text = self.tbp_entry.get_text().decode('utf-8')
        self.tbp_view.set_model(None)
        self.tbp_model.clear()

        try: pattern = util.PatternFromFile(pattern_text)
        except sre.error:
            ErrorMessage(self.window,
                         _("Invalid pattern"),
                         _("The pattern\n\t<b>%s</b>\nis invalid. "
                           "Possibly it contains the same tag twice or "
                           "it has unbalanced brackets (&lt; and &gt;).")%(
                util.escape(pattern_text))).run()
            return

        invalid = []
        for header in pattern.headers:
            if not self.songinfo.can_change(header):
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
                    
            ErrorMessage(self.window, title, msg % ", ".join(invalid)).run()
            return

        rep = self.widgets["prop_tbp_space_t"].get_active()
        title = self.widgets["prop_titlecase_t"].get_active()
        split = self.widgets["prop_splitval_t"].get_active()

        # create model to store the matches, and view to match
        self.tbp_model = gtk.ListStore(object, str,
                *([str] * len(pattern.headers)))

        for col in self.tbp_view.get_columns():
            self.tbp_view.remove_column(col)
        col = gtk.TreeViewColumn(_('File'), gtk.CellRendererText(), text=1)
        self.tbp_view.append_column(col)
        for i, header in enumerate(pattern.headers):
            render = gtk.CellRendererText()
            render.set_property('editable', True)
            render.connect('edited', self.tbp_edited, self.tbp_model,  i + 2)
            col = gtk.TreeViewColumn(header, render, text = i + 2)
            self.tbp_view.append_column(col)

        spls = config.get("settings", "splitters")
        # get info for all matches
        for song in self.songrefs:
            row = [song, song('~basename')]
            match = pattern.match(song)
            for h in pattern.headers:
                text = match.get(h, '')
                if rep: text = text.replace("_", " ")
                if title: text = util.title(text)
                if split: text = "\n".join(util.split_value(text, spls))
                row.append(text)
            self.tbp_model.append(row = row)

        # save for last to potentially save time
        self.tbp_view.set_model(self.tbp_model)
        self.tbp_preview.set_sensitive(False)
        if len(pattern.headers) > 0: self.save_tbp.set_sensitive(True)

    def tbp_save(self, *args):
        pattern_text = self.tbp_entry.get_text().decode('utf-8')
        pattern = util.PatternFromFile(pattern_text)
        add = (self.widgets["prop_tbp_addreplace"].get_active() == 1)
        win = WritingWindow(self.window, len(self.songrefs))

        def save_song(model, path, iter):
            song = model[path][0]
            row = model[path]
            changed = False
            for i, h in enumerate(pattern.headers):
                if row[i + 2]:
                    if not add or h not in song:
                        try:
                            song[h] = row[i + 2].decode("utf-8")
                        except UnicodeDecodeError:
                            song[h] = row[i + 2].decode("iso8859-1")
                        changed = True
                    else:
                        try:
                            vals = row[i + 2].decode("utf-8")
                        except UnicodeDecodeError:
                            vals = row[i + 2].decode("iso8859-1")
                        for val in vals.split("\n"):
                            if val not in song[h]:
                                song.add(h, val)
                                changed = True

            if changed:
                try:
                    song.sanitize()
                    song.write()
                except:
                    ErrorMessage(self.window,
                                 _("Unable to edit song"),
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

        self.tbp_model.foreach(save_song)
        win.end()
        self.save_tbp.set_sensitive(False)
        self.fill_property_info()

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
        return " / ".join([HEADERS_FILTER.get(n, n) for n
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
                   "album~part": "album",
                   "title~version": "title",
                   "lastplayed": "last played", "filename": "full name",
                   "playcount": "play count", "basename": "filename",
                   "dirname": "directory"}

def setup_ui():
    widgets.main = MainWindow()
    player.playlist.info = widgets.main
    gtk.threads_init()

    widgets.preferences = PreferencesWindow(widgets.main.window)
    widgets.about = AboutWindow(widgets.main.window)

def save_config():
    util.mkdir(const.DIR)
    f = file(const.CONFIG, "w")  
    config.write(f)
    f.close()

def main():
    if config.get("settings", "headers").split() == []:
       config.set("settings", "headers", "title")
    for opt in config.options("header_maps"):
        val = config.get("header_maps", opt)
        print opt, val
        HEADERS_FILTER[opt] = val

    setup_ui()

    from threading import Thread
    t = Thread(target = player.playlist.play, args = (widgets.main,))
    util.mkdir(const.DIR)
    signal.signal(signal.SIGINT, gtk.main_quit)
    signal.signal(signal.SIGKILL, gtk.main_quit)
    signal.signal(signal.SIGTERM, gtk.main_quit)
    signal.signal(signal.SIGHUP, gtk.main_quit)
    t.start()
    gtk.main()
    signal.signal(signal.SIGINT, cleanup)
    player.playlist.quitting()
    t.join()

    print _("Saving song library.")
    library.save(const.LIBRARY)
    cleanup()
    save_config()

def print_help():
    print _("""\
Quod Libet - a music library and player
Options:
  --help, -h        Display this help message
  --version         Display version and copyright information
  --refresh-library Rescan your song cache and then exit.
  --print-playing   Print the currently playing song.

 Player controls:
  --next, --previous, --play-pause, --play, --pause
    Change songs or pause/resume playing.
  --volume +|-|0..100
    Increase, decrease, or set the volume.
  --shuffle 0|1|t, --repeat 0|1|t
    Enable, disable, or toggle shuffle and repeat.  
  --query search-string
    Make a new playlist from the given search.
  --seek-to [HH:MM:]SS
    Seek to a position in the current song.
  --play-file filename
    Play this file, adding it to the library if necessary.

For more information, see the manual page (`man 1 quodlibet').
""")

    raise SystemExit

def print_version():
    print _("""\
Quod Libet %s
Copyright 2004 Joe Wreschnig, Michael Urman - quodlibet@lists.sacredchao.net

This is free software; see the source for copying conditions.  There is NO
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.\
""") % VERSION
    raise SystemExit

def refresh_cache():
    if isrunning():
        raise SystemExit(_(
            "The library cannot be refreshed while Quod Libet is running."))
    import library, config, const
    config.init(const.CONFIG)
    library.init()
    print _("Loading, scanning, and saving your library.")
    library.library.load(const.LIBRARY)
    for x, y in library.library.rebuild(): pass
    library.library.save(const.LIBRARY)
    raise SystemExit

DEF_PP = ("%(artist)?(album) - %(album)??(tracknumber) - "
          "%(tracknumber)? - %(title)")
def print_playing(fstring = DEF_PP):
    import util
    try:
        fn = file(const.CURRENT)
        data = {}
        for line in fn:
            line = line.strip()
            parts = line.split("=")
            key = parts[0]
            val = "=".join(parts[1:])
            if key in data: data[key] += "\n" + val
            else: data[key] = val
        try: print util.format_string(fstring, data)
        except (IndexError, ValueError):
            print util.format_string(DEF_PP, data)
        raise SystemExit
    except (OSError, IOError):
        print _("No song is currently playing.")
        raise SystemExit(True)

def error_and_quit():
    ErrorMessage(None,
                 _("No audio device found"),
                 _("Quod Libet was unable to open your audio device. "
                   "Often this means another program is using it, or "
                   "your audio drivers are not configured.\n\nQuod Libet "
                   "will now exit.")).run()
    gtk.main_quit()
    return True

def isrunning():
    return os.path.exists(const.CONTROL)

def control(c):
    if not isrunning():
        raise SystemExit(_("Quod Libet is not running."))
    else:
        try:
            import signal
            # This is a total abuse of Python! Hooray!
            signal.signal(signal.SIGALRM, lambda: "" + 2)
            signal.alarm(1)
            f = file(const.CONTROL, "w")
            signal.signal(signal.SIGALRM, signal.SIG_IGN)
            f.write(c)
            f.close()
        except (OSError, IOError, TypeError):
            os.unlink(const.CONTROL)
            print _("Unable to write to %s. Removing it.") % const.CONTROL
            if c != '!': raise SystemExit(True)
        else:
            raise SystemExit

def cleanup(*args):
    for filename in [const.CURRENT, const.CONTROL]:
        try: os.unlink(filename)
        except OSError: pass

if __name__ == "__main__":
    basedir = os.path.split(os.path.realpath(__file__))[0]
    i18ndir = "/usr/share/locale"

    import locale, gettext
    try: locale.setlocale(locale.LC_ALL, '')
    except: pass
    gettext.bindtextdomain("quodlibet", i18ndir)
    gettext.textdomain("quodlibet")
    gettext.install("quodlibet", i18ndir, unicode = 1)
    _ = gettext.gettext

    sys.path.insert(0, os.path.join(basedir, "quodlibet.zip"))

    import const

    # Check command-line parameters before doing "real" work, so they
    # respond quickly.
    opts = sys.argv[1:]
    controls = {"--next": ">", "--previous": "<", "--play": ")",
                "--pause": "|", "--play-pause": "-", "--volume-up": "v+",
                "--volume-down": "v-", }
    controls_opt = { "--seek-to": "s", "--shuffle": "&", "--repeat": "@",
                     "--query": "q", "--volume": "v" }
    try:
        for i, command in enumerate(opts):
            if command in ["--help", "-h"]: print_help()
            elif command in ["--version", "-v"]: print_version()
            elif command in ["--refresh-library"]: refresh_cache()
            elif command in controls: control(controls[command])
            elif command in controls_opt:
                control(controls_opt[command] + opts[i+1])
            elif command in ["--play-file"]:
                filename = os.path.abspath(os.path.expanduser(opts[i+1]))
                if os.path.isdir(filename): control("d" + filename)
                else: control("p" + filename)
            elif command in ["--print-playing"]:
                try: print_playing(opts[i+1])
                except IndexError: print_playing()
            else:
                print _("E: Unknown command line option: %s") % command
                raise SystemExit(_("E: Try %s --help") % sys.argv[0])
    except IndexError:
        print _("E: Option `%s' requires an argument.") % command
        raise SystemExit(_("E: Try %s --help") % sys.argv[0])

    if os.path.exists(const.CONTROL):
        print _("Quod Libet is already running.")
        control('!')

    # Get to the right directory for our data.
    os.chdir(basedir)
    # Initialize GTK/Glade.
    import pygtk
    pygtk.require('2.0')
    import gtk, pango
    if gtk.pygtk_version < (2, 4) or gtk.gtk_version < (2, 4):
        print _("E: You need GTK+ and PyGTK 2.4 or greater to run Quod Libet.")
        print _("E: You have GTK+ %s and PyGTK %s.") % (
            ".".join(map(str, gtk.gtk_version)),
            ".".join(map(str, gtk.pygtk_version)))
        raise SystemExit(_("E: Please upgrade GTK+/PyGTK."))
    import gtk.glade
    gtk.glade.bindtextdomain("quodlibet", i18ndir)
    gtk.glade.textdomain("quodlibet")

    import gc
    import shutil
    import util

    # Load configuration data and scan the library for new/changed songs.
    import config
    config.init(const.CONFIG)

    # Load the library.
    import library
    library.init(const.LIBRARY)
    print _("Loaded song library.")
    from library import library

    if config.get("settings", "scan"):
        for a, c in library.scan(config.get("settings", "scan").split(":")):
            pass

    # Try to initialize the playlist and audio output.
    print _("Opening audio device.")
    import player
    try: player.init(config.get("settings", "backend"))
    except IOError:
        # The audio device was busy; we can't do anything useful yet.
        # FIXME: Allow editing but not playing in this case.
        gtk.idle_add(error_and_quit)
        gtk.main()
        save_config()
        raise SystemExit(True)

    import pmp
    import parser
    import signal
    import sre
    if sys.version_info < (2, 4):
        from sets import Set as set
    try: main()
    finally: cleanup()
