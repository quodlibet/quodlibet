#!/usr/bin/env python

# Copyright 2004 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

VERSION = "0.1"

# This object communicates with the playing thread. It's the only way
# the playing thread talks to the UI, so replacing this with something
# using e.g. Curses would change the UI. The converse is not true. Many
# parts of the UI talk to the player.
#
# The single instantiation of this is widgets.wrap, created at startup.
class GTKSongInfoWrapper(object):
    def __init__(self):
        self.image = widgets["albumcover"]
        self.vbar = widgets["vseparator2"]
        self.text = widgets["currentsong"]
        self.pos = widgets["song_pos"]
        self.timer = widgets["song_timer"]
        self.button = widgets["play_button"]
        self.playing = gtk.gdk.pixbuf_new_from_file("pause.png")
        self.paused = gtk.gdk.pixbuf_new_from_file("play.png")

        self._time = (0, 1)
        gtk.timeout_add(300, self._update_time)

    # The pattern of getting a call from the playing thread and then
    # queueing an idle function prevents thread-unsafety in GDK.

    # The pause toggle was clicked.
    def set_paused(self, paused):
        gtk.idle_add(self._update_paused, paused)

    def _update_paused(self, paused):
        img = self.button.get_icon_widget()
        if paused: img.set_from_pixbuf(self.paused)
        else: img.set_from_pixbuf(self.playing)

    # The player told us about a new time.
    def set_time(self, cur, end):
        self._time = (cur, end)

    def _update_time(self):
        cur, end = self._time
        self.pos.set_value(cur)
        self.timer.set_text("%d:%02d/%d:%02d" %
                            (cur / 60000, (cur % 60000) / 1000,
                             end / 60000, (end % 60000) / 1000))
        return True

    # A new song was selected, or the next song started playing.
    def set_song(self, song, player):
        gtk.idle_add(self._update_song, song, player)

    def missing_song(self, song):
        gtk.idle_add(self._missing_song, song)

    def _missing_song(self, song):
        path = (player.playlist.get_playlist().index(song),)
        iter = widgets.songs.get_iter(path)
        widgets.songs.remove(iter)
        statusbar = widgets["statusbar"]
        j = statusbar.get_context_id("warnings")
        statusbar.push(j, "Could not play %s." % song['filename'])
        library.remove(song)
        player.playlist.remove(song)

    # Called when no cover is available, or covers are off.
    def disable_cover(self):
        self.image.hide()
        self.vbar.hide()

    # Called when a covers are turned on; an image may not be available.
    def enable_cover(self):
        if self.image.get_pixbuf():
            self.image.show()
            self.vbar.show()

    def _update_song(self, song, player):
        if song:
            self.pos.set_range(0, player.length)
            self.pos.set_value(0)

            cover = song.find_cover()
            if cover:
                pixbuf = gtk.gdk.pixbuf_new_from_file(cover)
                pixbuf = pixbuf.scale_simple(100, 100, gtk.gdk.INTERP_BILINEAR)
                self.image.set_from_pixbuf(pixbuf)
                if config.state("cover"): self.enable_cover()
            else:
                self.image.set_from_pixbuf(None)
                self.disable_cover()
            self.text.set_markup(song.to_markup())
        else:
            self.image.set_from_pixbuf(None)
            self.pos.set_range(0, 1)
            self.pos.set_value(0)
            self._time = (0, 1)
            self.text.set_markup("<span size='xx-large'>Not playing</span>")

        # Update the currently-playing song in the list by bolding it.
        last_song = CURRENT_SONG[0]
        CURRENT_SONG[0] = song
        col = len(HEADERS)
        def update_if_last_or_current(model, path, iter):
            if model[iter][col] is song:
                model[iter][col + 1] = 700
                model.row_changed(path, iter)
                widgets["songlist"].scroll_to_cell(path)
            elif model[iter][col] is last_song:
                model[iter][col + 1] = 400
                model.row_changed(path, iter)
        widgets.songs.foreach(update_if_last_or_current)

        return False

# Make a standard directory-chooser, and return the filenames and response.
def make_chooser(title):
    chooser = gtk.FileChooserDialog(
        title = title,
        action = gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
        buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                   gtk.STOCK_OPEN, gtk.RESPONSE_OK))
    chooser.set_select_multiple(True)
    resp = chooser.run()
    fns = chooser.get_filenames()
    chooser.destroy()
    return resp, fns

# Display the error dialog.
def make_error(title, description, buttons):
    text = "<span size='xx-large'>%s</span>\n\n%s" % (escape(title),
                                                      escape(description))
    dialog = gtk.MessageDialog(widgets["main_window"],
                               gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                               gtk.MESSAGE_ERROR,
                               buttons)
    dialog.set_markup(text)
    dialog.show_all()
    return dialog

# Standard Glade widgets wrapper.
class Widgets(object):
    def __init__(self, file):
        self.widgets = gtk.glade.XML("quodlibet.glade")
        self.widgets.signal_autoconnect(GladeHandlers.__dict__)

    def __getitem__(self, key):
        return self.widgets.get_widget(key)

# Glade-connected handler functions.
class GladeHandlers(object):
    def gtk_main_quit(*args): gtk.main_quit()

    def play_pause(button):
        player.playlist.paused ^= True

    def next_song(*args):
        player.playlist.next()

    def previous_song(*args):
        player.playlist.previous()

    def toggle_repeat(button):
        player.playlist.repeat = button.get_active()

    def show_about(menuitem):
        widgets["about_window"].set_transient_for(widgets["main_window"])
        widgets["about_window"].show()

    def close_about(*args):
        widgets["about_window"].hide()
        return True

    def toggle_shuffle(button):
        player.playlist.shuffle = button.get_active()

    def seek_slider(slider, v):
        gtk.idle_add(player.playlist.seek, v)

    # Set up the preferences window.
    def open_prefs(*args):
        widgets["prefs_window"].set_transient_for(widgets["main_window"])
        # Fill in the general checkboxes.
        widgets["cover_t"].set_active(config.state("cover"))
        widgets["color_t"].set_active(config.state("color"))
        old_h = HEADERS[:]

        # Fill in the header checkboxes.
        widgets["track_t"].set_active("=#" in old_h)
        widgets["album_t"].set_active("album" in old_h)
        widgets["artist_t"].set_active("artist" in old_h)
        widgets["genre_t"].set_active("genre" in old_h)
        widgets["year_t"].set_active("year" in old_h)
        widgets["version_t"].set_active("version" in old_h)
        widgets["performer_t"].set_active("performer" in old_h)

        # Remove the standard headers, and put the rest in the list.
        for t in ["=#", "album", "artist", "genre", "year", "version",
                  "performer", "title"]:
            try: old_h.remove(t)
            except ValueError: pass
        widgets["extra_headers"].set_text(" ".join(old_h))

        # Fill in the scanned directories.
        widgets["scan_opt"].set_text(config.get("settings", "scan"))
        widgets["prefs_window"].show()

    def set_headers(*args):
        # Based on the state of the checkboxes, set up new column headers.
        new_h = []
        if widgets["track_t"].get_active(): new_h.append("=#")
        new_h.append("title")
        if widgets["album_t"].get_active(): new_h.append("album")
        if widgets["artist_t"].get_active(): new_h.append("artist")
        if widgets["genre_t"].get_active(): new_h.append("genre")
        if widgets["year_t"].get_active(): new_h.append("year")
        if widgets["version_t"].get_active(): new_h.append("version")
        if widgets["performer_t"].get_active(): new_h.append("performer")
        new_h.extend(widgets["extra_headers"].get_text().split())
        HEADERS[:] = new_h
        config.set("settings", "headers", " ".join(HEADERS))
        set_column_headers(widgets["songlist"])

    def change_scan(*args):
        config.set("settings", "scan", widgets["scan_opt"].get_text())

    def toggle_color(toggle):
        config.set("settings", "color", str(bool(toggle.get_active())))

    def toggle_cover(toggle):
        config.set("settings", "cover", str(bool(toggle.get_active())))
        if config.state("cover"): widgets.wrap.enable_cover()
        else: widgets.wrap.disable_cover()

    def select_scan(*args):
        resp, fns = make_chooser("Select Directories")
        if resp == gtk.RESPONSE_OK:
            widgets["scan_opt"].set_text(":".join(fns))

    def prefs_closed(*args):
        widgets["prefs_window"].hide()
        config_fn = os.path.join(os.environ["HOME"], ".quodlibet", "config")
        util.mkdir(os.path.dirname(config_fn))
        f = file(config_fn, "w")
        config.write(f)
        f.close()
        return True

    def select_song(tree, indices, col):
        iter = widgets.songs.get_iter(indices)
        song = widgets.songs.get_value(iter, len(HEADERS))
        player.playlist.go_to(song)
        player.playlist.paused = False

    def open_chooser(*args):
        resp, fns = make_chooser("Add Music")
        if resp == gtk.RESPONSE_OK:
            progress = widgets["throbber"]
            label = widgets["found_count"]
            wind = widgets["scan_window"]
            wind.set_transient_for(widgets["main_window"])
            wind.show()
            for added, changed in library.scan(fns):
                progress.pulse()
                label.set_text("%d new songs found" % added)
                while gtk.events_pending(): gtk.main_iteration()
            wind.hide()
            player.playlist.refilter()
            refresh_songlist()
            gc.collect()

    def update_volume(slider):
        player.device.volume = int(slider.get_value())

    def songs_button_press(view, event):
        if event.button != 3:
            return False
        x, y = map(int, [event.x, event.y])
        path, col, cellx, celly = view.get_path_at_pos(x, y)
        view.grab_focus()
        selection = view.get_selection()
        if not selection.path_is_selected(path):
            view.set_cursor(path, col, 0)
        widgets["songs_popup"].popup(None,None,None, event.button, event.time)
        return True

    def song_col_filter(item):
        view = widgets["songlist"]
        path, col = view.get_cursor()
        coln = view.get_columns().index(col)
        header = HEADERS[coln]
        filter_on_header(header)

    def artist_filter(item): filter_on_header('artist')
    def album_filter(item):filter_on_header('album')

    def remove_song(item):
        view = widgets["songlist"]
        path, col = view.get_cursor()
        iter = widgets.songs.get_iter(path)
        song = widgets.songs.get_value(iter, len(HEADERS))
        widgets.songs.remove(iter)
        library.remove(song)
        player.playlist.remove(song)

    def song_properties(item):
        view = widgets["songlist"]
        path, col = view.get_cursor()
        selection = widgets["songlist"].get_selection()
        model, rows = selection.get_selected_rows()
        songrefs = [ [model[row][len(HEADERS)],
                      gtk.TreeRowReference(model, row)] for row in rows]
        make_song_properties(songrefs)

class MultiInstanceWidget(object):

    def __init__(self, file=None, widget=None):
        self.widgets = gtk.glade.XML(file or "quodlibet.glade", widget)
        self.widgets.signal_autoconnect(self)

    def songprop_close(self, *args):
        for song, ref in self.songrefs: ref.free()
        self.window.destroy()

    def songprop_save_click(self, button):

        updated = {}
        deleted = {}
        def create_property_dict(model, path, iter):
            row = model[iter]
            # Edited, and or and not Deleted
            if row[2] and not row[4]: updated[row[0]] = row[1]
            if row[2] and row[4]: deleted[row[0]] = 1
        self.model.foreach(create_property_dict)

        progress = widgets["writing_progress"]
        label = widgets["saved_count"]
        widgets["write_window"].set_transient_for(self.window)
        widgets["write_window"].show()
        saved = 0
        progress.set_fraction(0.0)
        for song, ref in self.songrefs:
            changed = False
            for key, value in updated.iteritems():
                if song.can_change(key):
                    if song.get(key) != value:
                        song[key] = value
                        changed = True
            for key in deleted:
                if song.can_change(key) and key in song:
                    changed = True
                    del song[key]

            if changed:
                path = ref.get_path()
                song.write()
                if path is not None:
                    widgets.songs[path] = ([song.get(h, "") for h in HEADERS] +
                                           [song, 400])
            saved += 1
            progress.set_fraction(saved / float(len(self.songrefs)))
            label.set_text("%d/%d songs saved" % (saved, len(self.songrefs)))
            while gtk.events_pending(): gtk.main_iteration()

        widgets["write_window"].hide()
        self.save.set_sensitive(False)
        self.revert.set_sensitive(False)
        self.fill_property_info()

    def songprop_revert_click(self, button):
        self.save.set_sensitive(False)
        self.revert.set_sensitive(False)
        self.fill_property_info()

    def songprop_toggle(self, renderer, path, model):
        row = model[path]
        row[2] = not row[2] # Edited
        self.save.set_sensitive(True)
        self.revert.set_sensitive(True)

    def songprop_edit(self, renderer, path, new, model, colnum):
        row = model[path]
        if row[colnum] != new:
            row[colnum] = new
            row[2] = True # Edited
            row[4] = False # not Deleted
            self.save.set_sensitive(True)
            self.revert.set_sensitive(True)

    def songprop_selection_changed(self, selection):
        model, iter = selection.get_selected()
        may_remove = bool(selection.count_selected_rows()) and model[iter][3]
        self.remove.set_sensitive(may_remove)

    def songprop_add(self, button):
        print 'FIXME: code songprop_add'
        self.save.set_sensitive(True)
        self.revert.set_sensitive(True)

    def songprop_remove(self, button):
        model, iter = self.view.get_selection().get_selected()
        row = model[iter]
        if row[0] in self.existing_comments:
            row[1] = 'Deleted'
            row[2] = True # Edited
            row[4] = True # Deleted
        else:
            model.remove(iter)
        self.save.set_sensitive(True)
        self.revert.set_sensitive(True)

    def fill_property_info(self):
        if len(self.songrefs) == 1:
            self.window.set_title("%s - Properties" %
                    self.songrefs[0][0]["title"])
        elif len(self.songrefs) > 1:
            self.window.set_title("%s and %d more - Properties" %
                    (self.songrefs[0][0]["title"], len(self.songrefs)-1))
        else:
            raise ValueError("Properties of no songs?")
        artist = {}
        title = {}
        album = {}
        filename = {}
        for song, iter in self.songrefs:
            artist.setdefault(song["artist"], 0)
            title.setdefault(song["title"], 0)
            album.setdefault(song["album"], 0)
            filename.setdefault(song["filename"], 0)
        for w, v, m in [ (self.artist, artist, 'Artists'),
                         (self.title, title, 'Titles'),
                         (self.album, album, 'Albums'),
                         (self.filename, filename, 'Files') ]:
            if len(v) > 1:
                w.set_markup("<i>%d %s</i>" % (len(v), m))
            else:
                w.set_text(v.keys()[0])

        self.model.clear()
        comments = {} # dict of dicts to see if comments all share value
        for song, iter in self.songrefs:
            for k, v in song.iteritems():
                if k.startswith('=') or k == 'filename': continue
                comval = comments.setdefault(k, {})
                comval.setdefault(v, True)
                comval[v] = comval[v] and song.can_change(k)

        keys = comments.keys()
        keys.sort()
        # reverse order here so insertion puts them in proper order.
        for comment in ['album', 'artist', 'title']:
            try: keys.remove(comment)
            except ValueError: pass
            else: keys.insert(0, comment)

        for comment in keys:
            valdict = comments[comment]
            if len(valdict) == 1:
                value, mayedit = valdict.items()[0]
            else:
                value = '(%s variants of %s)' % (len(valdict), comment)
                mayedit = min(valdict.values())
            edited = False
            deleted = False
            self.model.append(row=[comment, value, edited, mayedit, deleted])

        self.existing_comments = comments.keys()[:]

def make_song_properties(songrefs):
    dlg = MultiInstanceWidget(widget="properties_window")
    dlg.window = dlg.widgets.get_widget('properties_window')
    dlg.save = dlg.widgets.get_widget('songprop_save')
    dlg.revert = dlg.widgets.get_widget('songprop_revert')
    dlg.artist = dlg.widgets.get_widget('songprop_artist')
    dlg.title = dlg.widgets.get_widget('songprop_title')
    dlg.album = dlg.widgets.get_widget('songprop_album')
    dlg.filename = dlg.widgets.get_widget('songprop_file')
    dlg.view = dlg.widgets.get_widget('songprop_view')
    dlg.add = dlg.widgets.get_widget('songprop_add')
    dlg.remove = dlg.widgets.get_widget('songprop_remove')
    # comment, value, use-changes, edit, deleted
    dlg.model = gtk.ListStore(str, str, bool, bool, bool)
    dlg.view.set_model(dlg.model)
    dlg.songrefs = songrefs
    selection = dlg.view.get_selection()
    selection.connect('changed', dlg.songprop_selection_changed)

    render = gtk.CellRendererToggle()
    column = gtk.TreeViewColumn('Write', render, active=2, activatable=3)
    render.connect('toggled', dlg.songprop_toggle, dlg.model)
    dlg.view.append_column(column)
    render = gtk.CellRendererText()
    render.connect('edited', dlg.songprop_edit, dlg.model, 0)
    column = gtk.TreeViewColumn('Property', render, text=0)
    dlg.view.append_column(column)
    render = gtk.CellRendererText()
    render.connect('edited', dlg.songprop_edit, dlg.model, 1)
    column = gtk.TreeViewColumn('Value', render, text=1, editable=3)
    dlg.view.append_column(column)

    dlg.fill_property_info()

    dlg.window.show()

# Non-Glade handlers:

# Grab the text from the query box, parse it, and make a new filter.
def text_parse(*args):
    text = widgets["query"].child.get_text().decode("utf-8").strip()
    orig_text = text
    if text and "=" not in text and "/" not in text:
        # A simple search, not regexp-based.
        parts = ["* = /" + sre.escape(p) + "/" for p in text.split()]
        text = "&(" + ",".join(parts) + ")"
        # The result must be well-formed, since no /s were
        # in the original string and we escaped it.

    if player.playlist.playlist_from_filter(text):
        m = widgets["query"].get_model()
        for i, row in enumerate(iter(m)):
             if row[0] == orig_text:
                 m.remove(m.get_iter((i,)))
                 break
        else:
            if len(m) > 10: m.remove(m.get_iter((10,)))
        m.prepend([orig_text])
        set_entry_color(widgets["query"].child, "black")
        refresh_songlist()

def filter_on_header(header):
    view = widgets["songlist"]
    path, col = view.get_cursor()
    iter = widgets.songs.get_iter(path)
    song = widgets.songs.get_value(iter, len(HEADERS))
    if header == "=#": header = "tracknumber"
    text = song.get(header, "")
    text = "|".join([sre.escape(s) for s in text.split("\n")])
    query = u"%s = /%s/c" % (header, text)
    widgets["query"].child.set_text(query.encode('utf-8'))
    widgets["search_button"].clicked()

# Try and construct a query, but don't actually run it; change the color
# of the textbox to indicate its validity (if the option to do so is on).
def test_filter(*args):
    if not config.state("color"): return
    textbox = widgets["query"].child
    text = textbox.get_text()
    if "=" not in text and "/" not in text:
        gtk.idle_add(set_entry_color, textbox, "blue")
    elif parser.is_valid(text):
        gtk.idle_add(set_entry_color, textbox, "dark green")
    else:
        gtk.idle_add(set_entry_color, textbox, "red")

# Resort based on the header clicked.
def set_sort_by(header, i, sortdir=None):
    s = header.get_sort_order()
    if sortdir is not None: s = sortdir
    elif not header.get_sort_indicator() or s == gtk.SORT_DESCENDING:
        s = gtk.SORT_ASCENDING
    else: s = gtk.SORT_DESCENDING
    for h in widgets["songlist"].get_columns():
        h.set_sort_indicator(False)
    header.set_sort_indicator(True)
    header.set_sort_order(s)
    player.playlist.sort_by(HEADERS[i[0]], s == gtk.SORT_DESCENDING)
    refresh_songlist()

# Clear the songlist and readd the songs currently wanted.
def refresh_songlist():
    sl = widgets["songlist"]
    sl.set_model(None)
    widgets.songs.clear()
    statusbar = widgets["statusbar"]
    for song in player.playlist:
        wgt = ((song is CURRENT_SONG[0] and 700) or 400)
        widgets.songs.append([song.get(h, "") for h in HEADERS] + [song, wgt])

    j = statusbar.get_context_id("playlist")
    i = len(list(player.playlist))
    statusbar.push(j, "%d song%s found." % (i, (i != 1 and "s" or "")))
    sl.set_model(widgets.songs)

HEADERS = ["=#", "title", "album", "artist"]
HEADERS_FILTER = { "=#": "Track", "tracknumber": "Track" }

CURRENT_SONG = [ None ]

# Set the color of some text.
def set_entry_color(entry, color):
    layout = entry.get_layout()
    text = layout.get_text()
    markup = '<span foreground="%s">%s</span>' % (color, escape(text))
    layout.set_markup(markup)

# Build a new filter around our list model, set the headers to their
# new values.
def set_column_headers(sl):
    sl.set_model(None)
    widgets.songs = gtk.ListStore(*([str] * len(HEADERS) + [object, int]))
    for c in sl.get_columns(): sl.remove_column(c)
    for i, t in enumerate(HEADERS):
        render = gtk.CellRendererText()
        column = gtk.TreeViewColumn(HEADERS_FILTER.get(t, t).title(),
                                    render, text = i, weight = len(HEADERS)+1)
        column.set_resizable(True)
        column.set_clickable(True)
        column.set_sort_indicator(False)
        column.connect('clicked', set_sort_by, (i,))
        sl.append_column(column)
    refresh_songlist()
    sl.set_model(widgets.songs)

def setup_nonglade():
    # Set up the main song list store.
    sl = widgets["songlist"]
    sl.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
    widgets.songs = gtk.ListStore(object)
    set_column_headers(sl)
    refresh_songlist()

    # Build a model and view for our ComboBoxEntry.
    liststore = gtk.ListStore(str)
    widgets["query"].set_model(liststore)
    widgets["query"].set_text_column(0)
    cell = gtk.CellRendererText()
    widgets["query"].pack_start(cell, True)
    widgets["query"].child.connect('activate', text_parse)
    widgets["query"].child.connect('changed', test_filter)
    widgets["search_button"].connect('clicked', text_parse)

    # Initialize volume controls.
    widgets["volume"].set_value(player.device.volume)

    widgets.wrap = GTKSongInfoWrapper()

    widgets["main_window"].show()

    gtk.threads_init()

def main():
    load_cache()
    HEADERS[:] = config.get("settings", "headers").split()
    if "title" not in HEADERS: HEADERS.append("title")
    player.playlist.set_playlist(library.values())
    player.playlist.sort_by(HEADERS[0])
    setup_nonglade()
    print "Done loading songs."
    t = threading.Thread(target = player.playlist.play,
                         args = (widgets.wrap,))
    gc.collect()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    t.start()
    gtk.main()
    player.playlist.quitting()
    t.join()
    save_cache()

def print_help():
    print """\
Quod Libet - a music library and player
Options:
  --help, -h        Display this help message
  --version         Display version and copyright information
  --refresh-library Rescan your song cache; remove dead files; add new ones;
                    and then exit."""

    raise SystemExit

def print_version():
    print """\
Quod Libet %s
Copyright 2004 Joe Wreschnig <piman@sacredchao.net>
               Michael Urman

This is free software; see the source for copying conditions.  There is NO
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.\
""" % VERSION
    raise SystemExit

def load_cache():
    from library import library
    import config
    config_fn = os.path.join(os.environ["HOME"], ".quodlibet", "config")
    print "Loading config"
    config.init(config_fn)
    print "Loading library"
    cache_fn = os.path.join(os.environ["HOME"], ".quodlibet", "songs")
    c, d = library.load(cache_fn)
    print "Changed %d songs, deleted %d songs" % (c, d)
    if config.get("settings", "scan"):
        for a, c in library.scan(config.get("settings", "scan").split(":")):
            pass

def save_cache():
    from library import library
    print "Saving library"
    cache_fn = os.path.join(os.environ["HOME"], ".quodlibet", "songs")
    library.save(cache_fn)

def refresh_cache():
    load_cache()
    save_cache()
    raise SystemExit

def print_playing(fstring):
    try:
        fn = file(os.path.join(os.environ["HOME"], ".quodlibet", "current"))
        data = {}
        for line in fn:
            line = line.strip()
            parts = line.split("=")
            key = parts[0]
            val = "=".join(parts[1:])
            if key in data: data[key] += "\n" + val
            else: data[key] = val
        print fstring % data
        raise SystemExit
    except (OSError, IOError):
        print "No song is currently playing."
        raise SystemExit(True)

def error_and_quit():
    d = make_error("No audio device found",
                   "Quod Libet was unable to open your audio device. "
                   "Often this means another program is using it, or "
                   "your audio drivers are not configured.\n\nQuod Libet "
                   "will now exit.",
                   gtk.BUTTONS_OK)
    d.show()
    d.run()
    gtk.main_quit()
    return True

if __name__ == "__main__":
    import os, sys
    for command in sys.argv[1:]:
        if command in ["--help", "-h"]: print_help()
        elif command in ["--version", "-v"]: print_version()
        elif command in ["--refresh-library"]: refresh_cache()
        elif command in ["--print-playing"]: print_playing(sys.argv[2])
        else:
            print "E: Unknown command line option: %s" % command
            raise SystemExit("E: Try %s --help" % sys.argv[0])

    import pygtk
    pygtk.require('2.0')
    import gtk
    if gtk.pygtk_version < (2, 4) or gtk.gtk_version < (2, 4):
        print "E: You need GTK+ and PyGTK 2.4 or greater to run Quod Libet."
        print "E: You have GTK+ %s and PyGTK %s." % (
            ".".join(map(str, gtk.gtk_version)),
            ".".join(map(str, gtk.pygtk_version)))
        raise SystemExit("E: Please upgrade GTK+/PyGTK.")

    import gtk.glade
    widgets = Widgets("quodlibet.glade")

    import util; from util import escape
    import threading
    import gc
    import os
    import ao
    from library import library
    try: import player
    except ao.aoError:
        gtk.idle_add(error_and_quit)
        gtk.main()
        raise SystemExit(True)

    import parser
    import signal
    import config
    import sre
    main()
