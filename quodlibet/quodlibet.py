#!/usr/bin/env python

# Copyright 2004 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# $Id$

VERSION = "0.7"

import os, sys

# Give us a namespace for now.. FIXME: We need to remove this later.
class widgets(object): pass

# Make a standard directory-chooser, and return the filenames and response.
class FileChooser(object):
    def __init__(self, title, initial_dir = None):
        self.dialog = gtk.FileChooserDialog(
            title = title,
            parent = widgets["main_window"],
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

class MultiInstanceWidget(object):
    def __init__(self, file = None, widget = None):
        self.widgets = Widgets(file or "quodlibet.glade", self, widget)

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
        headers = config.get("settings", "headers").split()

        self.widgets["prefs_addreplace"].set_active(
            config.getint("settings", "addreplace"))

        # Fill in the header checkboxes.
        self.widgets["disc_t"].set_active("~#disc" in headers)
        self.widgets["track_t"].set_active("~#track" in headers)
        for h in ["album", "part", "artist", "genre", "date", "version",
                  "performer"]:
            self.widgets[h + "_t"].set_active(h in headers)
        self.widgets["filename_t"].set_active("~basename" in headers)
        self.widgets["length_t"].set_active("~length" in headers)

        # Remove the standard headers, and put the rest in the list.
        for t in ["~#disc", "~#track", "album", "artist", "genre", "date",
                  "version", "performer", "title", "~basename", "part",
                  "~length"]:
            try: headers.remove(t)
            except ValueError: pass
        self.widgets["extra_headers"].set_text(" ".join(headers))

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

    def pmp_changed(self, combobox):
        driver = self.widgets["pmp_combo"].get_active()
        config.set('pmp', 'driver', str(driver))
        self.widgets["pmp_entry"].set_sensitive(driver == 1)
        self.widgets["run_entry"].set_sensitive(driver == 2)

    def pmp_location_changed(self, entry):
        config.set('pmp', 'location', entry.get_text())

    def pmp_command_changed(self, entry):
        config.set('pmp', 'command', entry.get_text())

    def set_headers(self, *args):
        new_h = []
        if self.widgets["disc_t"].get_active(): new_h.append("~#disc")
        if self.widgets["track_t"].get_active(): new_h.append("~#track")
        new_h.append("title")
        for h in ["version", "album", "part", "artist", "performer",
                  "date", "genre"]:
            if self.widgets[h + "_t"].get_active(): new_h.append(h)
        if self.widgets["filename_t"].get_active(): new_h.append("~basename")
        if self.widgets["length_t"].get_active(): new_h.append("~length")
        new_h.extend(self.widgets["extra_headers"].get_text().split())
        HEADERS[:] = new_h
        config.set("settings", "headers", " ".join(new_h))
        set_column_headers(self.widgets["songlist"], new_h)

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
        chooser = FileChooser(_("Select Directories"), const.HOME)
        resp, fns = chooser.run()
        if resp == gtk.RESPONSE_OK:
            self.widgets["scan_opt"].set_text(":".join(fns))

    def select_masked(self, *args):
        if os.path.exists("/media"): path = "/media"
        elif os.path.exists("/mnt"): path = "/mnt"
        else: path = "/"
        chooser = FileChooser(_("Select Mount Points"), path)
        resp, fns = chooser.run()
        if resp == gtk.RESPONSE_OK:
            self.widgets["mask_opt"].set_text(":".join(fns))

    def prefs_closed(self, *args):
        self.window.hide()
        save_config()
        return True

    def show(self):
        self.window.present()

class WaitLoadWindow(MultiInstanceWidget):
    def __init__(self, parent, count, text, initial):
        MultiInstanceWidget.__init__(self, widget = "load_window")
        self.widgets["load_window"].set_transient_for(parent)
        self.current = 0
        self.count = count
        if self.count < 6: self.widgets["pause_cancel_box"].hide()
        self.text = text
        self.paused = False
        self.quit = False
        self.label = self.widgets["load_label"]
        self.progress = self.widgets["load_progress"]
        self.progress.set_fraction(0)
        self.label.set_markup(self.text % initial)
        self.widgets["load_window"].show()
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

    def end(self):
        self.widgets["load_window"].destroy()

# Standard Glade widgets wrapper.
class Widgets(object):
    def __init__(self, file, handlers, widget = None):
        if widget:
            self.widgets = gtk.glade.XML(file or "quodlibet.glade", widget,
                                         domain = gettext.textdomain())
        else:
            self.widgets = gtk.glade.XML(file or "quodlibet.glade",
                                         domain = gettext.textdomain())
        self.widgets.signal_autoconnect(handlers)
        self.get_widget = self.widgets.get_widget
        self.signal_autoconnect = self.widgets.signal_autoconnect

    def __getitem__(self, key):
        return self.widgets.get_widget(key)

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

class MainWindow(MultiInstanceWidget):
    def __init__(self):
        MultiInstanceWidget.__init__(self, widget = "main_window")
        self.last_dir = os.path.expanduser("~")
        self.window = self.widgets["main_window"]
        self.current_song = None

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
        self.icon = TrayIcon(p, self.tray_toggle_window, self.tray_popup)
        self.restore_size()

        # Set up the main song list store.
        sl = self.widgets["songlist"]
        sl.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        widgets.songs = gtk.ListStore(object)

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

        # Show main window.
        self.window.show()
        # Wait to fill in the column headers because otherwise the
        # spacing is off, since the window hasn't been sized until now.
        self.set_column_headers(sl, config.get("settings", "headers").split())
        self.widgets["query"].child.set_text(config.get("memory", "query"))

        self.widgets["shuffle_t"].set_active(config.state("shuffle"))
        self.widgets["repeat_t"].set_active(config.state("repeat"))

        if config.get("memory", "song"):
            self.widgets["query"].child.set_text(config.get("memory","query"))
            self.text_parse()
        else:
            player.playlist.set_playlist(library.values())
            self.refresh_songlist()

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

    def restore_size(self):
       w, h = map(int, config.get("memory", "size").split())
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
        if c == "<": self.previous_song(c)
        elif c == ">": self.next_song(c)
        elif c == "-": self.play_pause(c)
        elif c == ")": player.playlist.paused = False
        elif c == "|": player.playlist.paused = True
        elif c == "0": player.playlist.seek(0)
        elif c == "^": self.volume.set_value(self.volume.get_value() + 0.05)
        elif c == "v": self.volume.set_value(self.volume.get_value() - 0.05)
        elif c == "_": self.volume.set_value(0)
        elif c == "!":
            if not self.window.get_property('visible'):
                self.window.move(*self.window_pos)
            self.widgets.main.present()
        elif c == "q": make_query(os.read(source, 4096))
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
                            (cur / 60000, (cur % 60000) / 1000,
                             end / 60000, (end % 60000) / 1000))
        return True

    def _missing_song(self, song):
        path = (player.playlist.get_playlist().index(song),)
        iter = widgets.songs.get_iter(path)
        widgets.songs.remove(iter)
        statusbar = widgets["statusbar"]
        statusbar.set_text(_("Could not play %s.") % song['~filename'])
        library.remove(song)
        player.playlist.remove(song)

    def update_markup(self, song):
        if song:
            self.text.set_markup(song.to_markup())
            self.icon.tooltip = song.to_short()
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
        col = len(HEADERS)

        def update_if_last_or_current(model, path, iter):
            if model[iter][col] is song:
                model[iter][col + 1] = 700
                model.row_changed(path, iter)
            elif model[iter][col] is last_song:
                model[iter][col + 1] = 400
                model.row_changed(path, iter)

        widgets.songs.foreach(update_if_last_or_current)
        gc.collect()
        return False

    def tray_toggle_window(self, icon):
        window = self.window
        if window.get_property('visible'):
            self.window_pos = window.get_position()
            window.hide()
        else:
            window.move(*self.window_pos)
            window.show()

    def tray_popup(self, *args):
        self.tray_menu["tray_popup"].popup(None, None, None, 3, 0)

    def gtk_main_quit(self, *args):
        gtk.main_quit()

    def save_size(self, widget, event):
        config.set("memory", "size", "%d %d" % (event.width, event.height))

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
        else: self.widgets["songlist"].scroll_to_cell(path)

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
        self.make_query("artist = /^%s$/c"%sre.escape(library.random("artist")))

    def random_album(self, menuitem):
        self.make_query("album = /^%s$/c"%sre.escape(library.random("album")))
        self.widgets["shuffle_t"].set_active(False)

    def random_genre(self, menuitem):
        self.make_query("genre = /^%s$/c"%sre.escape(library.random("genre")))

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

    def rebuild(self, activator):
        window = WaitLoadWindow(self.window, len(library) / 5,
                                _("Quod Libet is scanning your library. "
                                  "This may take several minutes.\n\n"
                                  "%d songs reloaded\n%d songs removed"),
                                (0, 0))
        iter = 5
        for c, r in library.rebuild():
            if iter == 5:
                if window.step(c, r): break
                iter = 0
            iter += 1
        window.end()
        player.playlist.refilter()
        self.refresh_songlist()

    def rebuild_hard(self, activator):
        window = WaitLoadWindow(self.window, len(library) / 5,
                                _("Quod Libet is reloading your library. "
                                  "This may take several minutes.\n\n"
                                  "%d songs reloaded\n%d songs removed"),
                                (0, 0))
        iter = 5
        for c, r in library.rebuild(True):
            if iter == 5:
                if window.step(c, r): break
                iter = 0
            iter += 1
        window.end()
        player.playlist.refilter()
        self.refresh_songlist()

    def pmp_upload(self, *args):
        view = self.widgets["songlist"]
        selection = view.get_selection()
        model, rows = selection.get_selected_rows()
        songs = [model[row][len(HEADERS)] for row in rows]
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
        song = widgets.songs.get_value(iter, len(HEADERS))
        player.playlist.go_to(song)
        player.playlist.paused = False

    def open_chooser(self, *args):
        chooser = FileChooser(_("Add Music"), GladeHandlers.last_dir)
        resp, fns = chooser.run()
        if resp == gtk.RESPONSE_OK:
            win = WaitLoadWindow(self.window, 0,
                                 _("Quod Libet is scanning for new songs and "
                                   "adding them to your library.\n\n"
                                   "%d songs added"), 0)
            for added, changed in library.scan(fns):
                if win.step(added): break
            win.end()
            player.playlist.refilter()
            self.refresh_songlist()
        if fns: self.last_dir = fns[0]

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
        coln = view.get_columns().index(col)
        header = HEADERS[coln]
        self.prep_main_popup(header)
        self.cmenu.popup(None,None,None, event.button, event.time)
        return True

    def songs_popup_menu(self, view):
        path, col = view.get_cursor()
        coln = view.get_columns().index(col)
        header = HEADERS[coln]
        self.prep_main_popup(header)
        self.cmenu.popup(None, None, None, 1, 0)

    def song_col_filter(self, item):
        view = self.widgets["songlist"]
        path, col = view.get_cursor()
        coln = view.get_columns().index(col)
        header = HEADERS[coln]
        self.filter_on_header(header)

    def artist_filter(self, item): self.filter_on_header('artist')
    def album_filter(self, item): self,filter_on_header('album')
    def genre_filter(self, item): self.filter_on_header('genre')

    def cur_artist_filter(self, item):
        self.filter_on_header('artist', CURRENT_SONG)
    def cur_album_filter(self, item):
        self.filter_on_header('album', CURRENT_SONG)
    def cur_genre_filter(self, item):
        self.filter_on_header('genre', CURRENT_SONG)

    def remove_song(self, item):
        view = self.widgets["songlist"]
        selection = self.widgets["songlist"].get_selection()
        model, rows = selection.get_selected_rows()
        rows.sort()
        rows.reverse()
        for row in rows:
            song = model[row][len(HEADERS)]
            iter = widgets.songs.get_iter(row)
            widgets.songs.remove(iter)
            library.remove(song)
            player.playlist.remove(song)

    def current_song_prop(self, *args):
        song = self.current_song
        if song:
            l = self.widgets["songlist"]
            try: path = (player.playlist.get_playlist().index(song),)
            except ValueError: ref = None
            else: ref = gtk.TreeRowReference(l.get_model(), path)
            SongProperties([(song, ref)])
            
    def song_properties(self, item):
        view = self.widgets["songlist"]
        selection = view.get_selection()
        model, rows = selection.get_selected_rows()
        songrefs = [ (model[row][len(HEADERS)],
                      gtk.TreeRowReference(model, row)) for row in rows]
        SongProperties(songrefs)

    def prep_main_popup(self, header):
        if not config.getint("pmp", "driver"):
            self.cmenu_w["pmp_sep"].hide()
            self.cmenu_w["pmp_upload"].hide()
        else:
            self.cmenu_w["pmp_sep"].show()
            self.cmenu_w["pmp_upload"].show()
        if header not in ["genre", "artist", "album"]:
            self.cmenu_w["filter_column"].show()
            if header.startswith("~#"): header = header[2:]
            elif header.startswith("~"): header = header[1:]
            header = HEADERS_FILTER.get(header, header)
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
            selection = self.widgets["songlist"].get_selection()
            model, rows = selection.get_selected_rows()
            songs = [model[row][len(HEADERS)] for row in rows]

        if header.startswith("~#"):
            nheader = header[2:]
            values = [song.get(header, 0) for song in songs]
            queries = ["#(%s = %d)" % (nheader, i) for i in values]
            self.make_query("|(" + ", ".join(queries) + ")")
        else:
            if header.startswith("~"): header = header[1:]
            values = {}
            for song in songs:
                if header in song:
                    for val in song[header].split("\n"):
                        values[val] = True

            text = "|".join([sre.escape(s) for s in values.keys()])
            self.make_query(u"%s = /^(%s)$/c" % (header, text))

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
        for h in self.widgets["songlist"].get_columns():
            h.set_sort_indicator(False)
        header.set_sort_indicator(True)
        header.set_sort_order(s)
        player.playlist.sort_by(tag, s == gtk.SORT_DESCENDING)
        self.refresh_songlist()

    # Clear the songlist and readd the songs currently wanted.
    def refresh_songlist(self):
        sl = self.widgets["songlist"]
        sl.set_model(None)
        widgets.songs.clear()
        statusbar = self.widgets["statusbar"]
        length = 0
        for song in player.playlist:
            wgt = ((song is self.current_song and 700) or 400)
            widgets.songs.append([song.get(h, "") for h in HEADERS] + [song, wgt])
            length += song["~#length"]
        i = len(list(player.playlist))
        if i != 1: statusbar.set_text(
            _("%d songs (%s)") % (i, util.format_time_long(length)))
        else: statusbar.set_text(
            _("%d song (%s)") % (i, util.format_time_long(length)))
        sl.set_model(widgets.songs)
        gc.collect()

    # Build a new filter around our list model, set the headers to their
    # new values.
    def set_column_headers(self, sl, headers):
        SHORT_COLS = ["tracknumber", "discnumber"]
        sl.set_model(None)
        widgets.songs = gtk.ListStore(*([str] * len(headers) + [object, int]))
        for c in sl.get_columns(): sl.remove_column(c)
        self.widgets["songlist"].realize()
        width = self.widgets["songlist"].get_allocation()[2]
        c = 0
        for t in headers:
            if t in SHORT_COLS or t.startswith("~#"): c += 0.1
            else: c += 1
        width = int(width / c)
        for i, t in enumerate(headers):
            render = gtk.CellRendererText()
            if t in SHORT_COLS or t.startswith("~#"):
                render.set_fixed_size(-1, -1)
            else: render.set_fixed_size(width, -1)
            t2 = t.lstrip("~#")
            title = util.title(_(HEADERS_FILTER.get(t2, t2)))
            column = gtk.TreeViewColumn(title, render, text = i,
                                        weight = len(headers)+1)
            column.set_resizable(True)
            column.set_clickable(True)
            column.set_sort_indicator(False)
            column.connect('clicked', self.set_sort_by, t)
            sl.append_column(column)
        self.refresh_songlist()
        sl.set_model(widgets.songs)

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
        for song, ref in songrefs:
            self.fbasemodel.append(
                row=[song, ref, song.get('~basename', ''),
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
        del(self.songrefs)

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
        for song, ref in self.songrefs:
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

            if changed and ref:
                try: song.write()
                except:
                    ErrorMessage(self.window,
                                 _("Unable to edit song"),
                                 _("Saving <b>%s</b> failed. The file may be "
                                   "read-only, corrupted, or you do not have "
                                   "permission to edit it.")%(
                        util.escape(song['~basename']))).run()
                    library.reload(song)
                    player.playlist.refilter()
                    refresh_songlist()
                    break
                songref_update_view(song, ref)

            if win.step(): break

        win.end()
        self.save_edit.set_sensitive(False)
        self.revert.set_sensitive(False)
        self.fill_property_info()
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
            path = model.convert_path_to_child_path(path)
            model = model.get_model()
            songrefs.append([model[path][0], model[path][1]])
        selection.selected_foreach(get_songrefs, songrefs)
        if len(songrefs): self.songrefs = songrefs
        self.fill_property_info()

    def prep_prop_menu(self, row):
        self.menu_w.get_widget("split_album").hide()
        self.menu_w.get_widget("split_title").hide()
        self.menu_w.get_widget("split_performer").hide()
        self.menu_w.get_widget("split_arranger").hide()
        self.menu_w.get_widget("special_sep").hide()
        spls = config.get("settings", "splitters")

        self.menu_w["split_into_list"].set_sensitive(
            len(util.split_value(row[1], spls)) > 1)

        if row[0] == "album":
            self.menu_w["split_album"].show()
            self.menu_w["special_sep"].show()
            self.menu_w["split_album"].set_sensitive(
                util.split_album(row[1])[1] is not None)

        if row[0] == "title":
            self.menu_w.get_widget("split_title").show()
            self.menu_w.get_widget("special_sep").show()
            self.menu_w["split_title"].set_sensitive(
                util.split_title(row[1], spls)[1] != [])

        if row[0] == "artist":
            self.menu_w.get_widget("split_performer").show()
            self.menu_w.get_widget("split_arranger").show()
            self.menu_w.get_widget("special_sep").show()
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
        add = widgets["add_tag_dialog"]
        tag = widgets["add_tag_tag"]
        val = widgets["add_tag_value"]
        tag.child.set_text("")
        val.set_text("")
        tag.child.set_activates_default(gtk.TRUE)
        val.set_activates_default(gtk.TRUE)
        tag.child.grab_focus()

        while True:
            resp = add.run()
            if resp != gtk.RESPONSE_OK: break

            comment = tag.child.get_text().decode("utf-8").lower().strip()
            value = val.get_text().decode("utf-8")
            date = sre.compile("^\d{4}(-\d{2}-\d{2})?$")
            if not self.songinfo.can_change(comment):
                WarningMessage(
                    self.window, _("Invalid tag"),
                    _("Invalid tag <b>%s</b>\n\nThe files currently"
                      " selected do not support editing this tag")%
                    util.escape(comment)).run()

            elif comment == "date" and not date.match(value):
                WarningMessage(self.window, _("Invalid date"),
                               _("Invalid date: <b>%s</b>.\n\n"
                                 "The date must be entered in YYYY or "
                                 "YYYY-MM-DD format.") % value).run()
            else:
                self.add_new_tag(comment, value)
                tag.child.set_text("")
                val.set_text("")
                break

        add.hide()

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
        songinfo = AudioFileGroup([song for (song,ref) in self.songrefs])
        self.songinfo = songinfo
        if len(self.songrefs) == 1:
            self.window.set_title(_("%s - Properties") %
                    self.songrefs[0][0]["title"])
        elif len(self.songrefs) > 1:
            self.window.set_title(_("%s and %d more - Properties") %
                    (self.songrefs[0][0]["title"], len(self.songrefs)-1))
        else:
            raise ValueError("Properties of no songs?")

        self.artist.set_markup(songinfo['artist'].safenicestr())
        self.title.set_markup(songinfo['title'].safenicestr())
        self.album.set_markup(songinfo['album'].safenicestr())
        filename = util.unexpand(songinfo['~filename'].safenicestr())
        self.filename.set_markup(filename)

        if len(self.songrefs) > 1:
            listens = sum([song["~#playcount"] for song, i in self.songrefs])
            if listens == 1: s = _("1 song heard")
            else: s = _("%d songs heard") % listens
            self.played.set_markup("<i>%s</i>" % s)
        else:
            self.played.set_text(self.songrefs[0][0].get_played())

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
        for song, ref in self.songrefs:
            self.tn_model.append(row = [song, ref, song['~basename'],
                                        song.get("tracknumber", "")])

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
            ref = model[iter][1]
            track = model[iter][3]
            song["tracknumber"] = track
            try: song["~#track"] = int(track.split("/")[0])
            except ValueError:
                try: del(song["~#track"])
                except KeyError: pass
            try: song.write()
            except:
                ErrorMessage(self.window,
                             _("Unable to edit song"),
                             _("Saving <b>%s</b> failed. The file may be "
                               "read-only, corrupted, or you do not have "
                               "permission to edit it.")%(
                    util.escape(song['~basename']))).run()
                library.reload(song)
                player.playlist.refilter()
                refresh_songlist()
                return True
            if ref: songref_update_view(song, ref)
            return win.step()
        self.tn_model.foreach(settrack)
        self.fill_property_info()
        self.save_tn.set_sensitive(False)
        win.end()

    def songprop_nbp_preview(self, *args):
        self.nbp_model.clear()
        pattern = self.nbp_entry.get_text().decode('utf-8')

        underscore = self.widgets.get_widget("prop_nbp_space_t").get_active()
        windows = self.widgets.get_widget("prop_windows_t").get_active()
        ascii = self.widgets.get_widget("prop_ascii_t").get_active()

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
            
        for song, ref in self.songrefs:
            newname = pattern.match(song)
            if underscore: newname = newname.replace(" ", "_")
            if windows:
                for c in '\\:*?;"<>|':
                    newname = newname.replace(c, "_")
            if ascii:
                newname = "".join(map(lambda c: ((ord(c) < 127 and c) or "_"),
                                      newname))
            self.nbp_model.append(row=[song, ref, song['~basename'], newname])
        self.nbp_preview.set_sensitive(False)
        self.save_nbp.set_sensitive(True)

    def nbp_save(self, *args):
        pattern = self.nbp_entry.get_text().decode('utf-8')
        win = WritingWindow(self.window, len(self.songrefs))

        def rename(model, path, iter):
            song = model[path][0]
            ref = model[path][1]
            oldname = model[path][2]
            newname = model[path][3]
            try:
                library.rename(song, newname)
                if ref: songref_update_view(song, ref)
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
            model[path][2] = song['~basename']
            model[path][3] = song['~dirname']
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
        self.tbp_view.set_model(None)
        self.tbp_model.clear()

        # build the pattern
        pattern_text = self.tbp_entry.get_text().decode('utf-8')

        try: pattern = util.PatternFromFile(pattern_text)
        except sre.error:
            ErrorMessage(self.window,
                         _("Invalid pattern"),
                         _("The pattern\n\t<b>%s</b>\nis invalid. "
                           "Possibly it contains the same tag twice or "
                           "it has unbalanced brackets (&lt; and &gt;).")%(
                util.escape(pattern_text))).run()
            return

        rep = self.widgets.get_widget("prop_tbp_space_t").get_active()
        title = self.widgets.get_widget("prop_titlecase_t").get_active()
        split = self.widgets.get_widget("prop_splitval_t").get_active()

        # create model to store the matches, and view to match
        self.tbp_model = gtk.ListStore(object, object, str,
                *([str] * len(pattern.headers)))

        for col in self.tbp_view.get_columns():
            self.tbp_view.remove_column(col)
        col = gtk.TreeViewColumn(_('File'), gtk.CellRendererText(), text=2)
        self.tbp_view.append_column(col)
        for i, header in enumerate(pattern.headers):
            render = gtk.CellRendererText()
            render.set_property('editable', True)
            render.connect('edited', self.tbp_edited, self.tbp_model,  i + 3)
            col = gtk.TreeViewColumn(header, render, text=i+3)
            self.tbp_view.append_column(col)

        spls = config.get("settings", "splitters")
        # get info for all matches
        for song, ref in self.songrefs:
            row = [song, ref, song['~basename']]
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
        spls = config.get("settings", "splitters")

        def save_song(model, path, iter):
            song = model[path][0]
            ref = model[path][1]
            row = model[path]
            changed = False
            for i, h in enumerate(pattern.headers):
                if row[i]:
                    if not add or h not in song:
                        song[h] = row[i + 3].decode("utf-8")
                        changed = True
                    else:
                        for val in row[i + 3].decode("utf-8").split("\n"):
                            if val not in song[h]:
                                song.add(h, val)
                                changed = True

            if changed and ref:
                try:
                    song.sanitize()
                    song.write()
                except:
                    ErrorMessage(self.window,
                                 _("Unable to edit song"),
                                 _("Saving <b>%s</b> failed. The file may be "
                                   "read-only, corrupted, or you do not have "
                                   "permission to edit it.")%(
                        util.escape(song['~basename']))).run()
                    library.reload(song)
                    player.playlist.refilter()
                    refresh_songlist()
                    return True
                songref_update_view(song, ref)

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

def songref_update_view(song, ref):
    path = ref.get_path()
    if path is not None:
        row = widgets.songs[path]
        for i, h in enumerate(HEADERS): row[i] = song.get(h, "")

HEADERS = ["~#track", "title", "album", "artist"]
HEADERS_FILTER = { "tracknumber": "track",
                   "discnumber": "disc",
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
    HEADERS[:] = config.get("settings", "headers").split()
    if "title" not in HEADERS: HEADERS.append("title")
    setup_ui()
    player.playlist.sort_by(HEADERS[0])

    for opt in config.options("header_maps"):
        val = config.get("header_maps", opt)
        HEADERS_FILTER[opt] = val

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

  --next, --previous, --play-pause, --volume-up, -volume-down,
  --play, --pause
    Control a currently running instance of Quod Libet.
  --query search-string
    Search in a running instance of Quod Libet.
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
    library.library.rebuild()
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
            signal.alarm(2)
            f = file(const.CONTROL, "w")
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
    import os, sys

    basedir = os.path.split(os.path.realpath(__file__))[0]
    i18ndir = "/usr/share/locale"

    import locale, gettext
    try: locale.setlocale(locale.LC_ALL, '')
    except: pass
    gettext.bindtextdomain("quodlibet", i18ndir)
    gettext.textdomain("quodlibet")
    gettext.install("quodlibet", i18ndir, unicode = 1)
    _ = gettext.gettext

    if os.path.exists(os.path.join(basedir, "quodlibet.zip")):
        sys.path.insert(0, os.path.join(basedir, "quodlibet.zip"))

    import const

    # Check command-line parameters before doing "real" work, so they
    # respond quickly.
    opts = sys.argv[1:]
    controls = {"--next": ">", "--previous": "<", "--play": ")",
                "--pause": "|", "--play-pause": "-", "--volume-up": "^",
                "--volume-down": "v"}
    try:
        for i, command in enumerate(opts):
            if command in ["--help", "-h"]: print_help()
            elif command in ["--version", "-v"]: print_version()
            elif command in ["--refresh-library"]: refresh_cache()
            elif command in controls: control(controls[command])
            elif command in ["--query"]:
                control("q" + opts[i+1])
            elif command in ["--play-file"]:
                filename = os.path.abspath(os.path.expanduser(opts[i+1]))
                if os.path.isdir(filename): control("d" + filename)
                else: control("p" + filename)
            elif command in ["--seek-to"]:
                control("s" + opts[i+1])
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
    import gtk
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
