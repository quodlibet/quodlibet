# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, sys

import gtk, pango, gobject, gst
import stock
import qltk

import browsers
import const
import config
import player
import parser
import formats
import util
import locale

from util import to
from library import library

if sys.version_info < (2, 4): from sets import Set as set
from properties import SongProperties
from qltk.songlist import SongList
from qltk.wlw import WaitLoadWindow
from qltk.getstring import GetStringDialog
from qltk.browser import LibraryBrowser

# Give us a namespace for now.. FIXME: We need to remove this later.
# Or, replace it with nicer wrappers!
class __widgets(object):
    __slots__ = ["watcher", "main"]
widgets = __widgets()

class MainSongList(SongList):
    # The SongList that represents the current playlist.

    class CurrentColumn(gtk.TreeViewColumn):
        # Displays the current song indicator, either a play or pause icon.
    
        _render = gtk.CellRendererPixbuf()
        _render.set_property('xalign', 0.5)
        header_name = "~current"

        def _cdf(self, column, cell, model, iter,
                 pixbuf=(gtk.STOCK_MEDIA_PLAY, gtk.STOCK_MEDIA_PAUSE)):
            try:
                if model.get_path(iter) != model.current_path: stock = ''
                else: stock = pixbuf[player.playlist.paused]
                cell.set_property('stock-id', stock)
            except AttributeError: pass

        def __init__(self):
            gtk.TreeViewColumn.__init__(self, "", self._render)
            self.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
            self.set_fixed_width(24)
            self.set_cell_data_func(self._render, self._cdf)
            self.header_name = "~current"

    def __init__(self, watcher, player):
        SongList.__init__(self, watcher)
        self.set_rules_hint(True)
        self.model = self.get_model()
        s = watcher.connect_object('removed', map, player.remove)
        self.connect_object('destroy', watcher.disconnect, s)
        self.connect_object('row-activated', self.__select_song, player)

    def __select_song(self, player, indices, col):
        iter = self.model.get_iter(indices)
        player.go_to(iter)
        if player.song: player.paused = False

    def set_sort_by(self, *args, **kwargs):
        SongList.set_sort_by(self, *args, **kwargs)
        tag, reverse = self.get_sort_by()
        config.set('memory', 'sortby', "%d%s" % (int(not reverse), tag))

class MainWindow(gtk.Window):
    def __init__(self, watcher):
        gtk.Window.__init__(self)
        self.last_dir = os.path.expanduser("~")

        tips = gtk.Tooltips()
        self.set_title("Quod Libet")

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

        # play controls
        from qltk.controls import PlayControls
        t = PlayControls(watcher, player.playlist)
        self.volume = t.volume
        hbox.pack_start(t, expand=False, fill=False)

        # song text
        from qltk.info import SongInfo
        text = SongInfo(watcher, player.playlist)
        # Packing the text directly into the hbox causes clipping problems
        # with Hebrew, so use an Alignment instead.
        alignment = gtk.Alignment(xalign=0, yalign=0, xscale=1, yscale=1)
        alignment.set_padding(3, 3, 3, 3)
        alignment.add(text)
        hbox.pack_start(alignment)

        # cover image
        from qltk.cover import CoverImage
        self.image = CoverImage()
        watcher.connect('song-started', self.image.set_song)
        hbox.pack_start(self.image, expand=False)

        self.child.pack_start(hbox, expand=False)

        # status area
        hbox = gtk.HBox(spacing=6)
        self.order = order = gtk.combo_box_new_text()
        self.order.append_text(_("In Order"))
        self.order.append_text(_("Shuffle"))
        self.order.append_text(_("Weighted"))
        self.order.append_text(_("One Song"))
        tips.set_tip(order, _("Set play order"))
        order.connect('changed', self.__order)
        hbox.pack_start(order, expand=False)
        self.repeat = repeat = gtk.CheckButton(_("_Repeat"))
        tips.set_tip(repeat, _("Restart the playlist when finished"))
        hbox.pack_start(repeat, expand=False)
        self.__statusbar = gtk.Label()
        self.__statusbar.set_text(_("No time information"))
        self.__statusbar.set_alignment(1.0, 0.5)
        self.__statusbar.set_ellipsize(pango.ELLIPSIZE_START)
        hbox.pack_start(self.__statusbar)
        hbox.set_border_width(3)
        self.child.pack_end(hbox, expand=False)

        # song list
        self.song_scroller = sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        sw.set_shadow_type(gtk.SHADOW_IN)
        self.songlist = MainSongList(watcher, player.playlist)
        self.songlist.connect_after(
            'drag-data-received', self.__songlist_drag_data_recv)
        sw.add(self.songlist)

        from qltk.queue import QueueExpander
        self.qexpander = QueueExpander(
            self.ui.get_widget("/Menu/View/Queue"), watcher)

        from qltk.songlist import PlaylistMux
        self.playlist = PlaylistMux(
            watcher, self.qexpander.model, self.songlist.model)

        self.songpane = gtk.VBox(spacing=6)
        self.songpane.pack_start(self.song_scroller)
        self.songpane.pack_start(self.qexpander, expand=False, fill=True)
        self.songpane.show_all()
        self.song_scroller.connect('notify::visible', self.__show_or)
        self.qexpander.connect('notify::visible', self.__show_or)

        sort = config.get('memory', 'sortby')
        self.songlist.set_sort_by(None, sort[1:], order=int(sort[0]))

        self.inter = gtk.VBox()

        self.browser = None

        from qltk.mmkeys import MmKeys
        self.__keys = MmKeys(player.playlist)

        self.child.show_all()
        sw.show_all()
        self.select_browser(self, config.get("memory", "browser"))
        self.browser.restore()
        self.browser.activate()
        self.showhide_playlist(self.ui.get_widget("/Menu/View/SongList"))
        self.showhide_playqueue(self.ui.get_widget("/Menu/View/Queue"))

        try: shf = config.getint('memory', 'order')
        except: shf = int(config.getboolean('memory', 'order'))
        order.set_active(shf)
        repeat.connect('toggled', self.toggle_repeat)
        repeat.set_active(config.getboolean('settings', 'repeat'))

        self.connect('configure-event', MainWindow.__save_size)
        self.connect('destroy', gtk.main_quit)
        self.connect('window-state-event', self.__window_state_changed)
        self.__hidden_state = 0

        self.songlist.connect('button-press-event', self.__songs_button_press)
        self.songlist.connect('popup-menu', self.__songs_popup_menu)
        self.songlist.connect('columns-changed', self.__cols_changed)
        self.songlist.connect('columns-changed', self.__hide_headers)
        self.songlist.get_selection().connect('changed', self.__set_time)

        watcher.connect('removed', self.__set_time)
        watcher.connect('refresh', self.__refresh)
        watcher.connect('changed', self.__update_title)
        watcher.connect('song-started', self.__song_started)
        watcher.connect_after('song-ended', self.__song_ended)
        watcher.connect('paused', self.__update_paused, True)
        watcher.connect('unpaused', self.__update_paused, False)

        
        targets = [("text/uri-list", 0, 1)]
        self.drag_dest_set(
            gtk.DEST_DEFAULT_ALL, targets, gtk.gdk.ACTION_DEFAULT)
        self.connect_object('drag-motion', MainWindow.__drag_motion, self)
        self.connect_object('drag-leave', MainWindow.__drag_leave, self)
        self.connect_object(
            'drag-data-received', MainWindow.__drag_data_received, self)

        self.resize(*map(int, config.get("memory", "size").split()))
        self.child.show()

    def __drag_motion(self, ctx, x, y, time):
        # Don't accept drops from QL itself, since it offers text/uri-list.
        if ctx.get_source_widget() is None:
            self.drag_highlight()
            return True
        else: return False

    def __drag_leave(self, ctx, time):
        self.drag_unhighlight()

    def __drag_data_received(self, ctx, x, y, sel, tid, etime):
        if tid == 1: uris = sel.get_uris()
        if tid == 2:
            uri = sel.data.decode('ucs-2', 'replace').split('\n')[0]
            uris = [uri.encode('ascii', 'replace')]

        dirs = []
        files = []
        error = False
        from formats.remote import RemoteFile
        for uri in uris:
            from urllib import splittype as split, url2pathname as topath
            type, loc = split(uri)
            if type == "file":
                loc = os.path.normpath(topath(loc))
                if os.path.isdir(loc): dirs.append(loc)
                else:
                    loc = os.path.realpath(loc)
                    if loc not in library:
                        song = library.add(loc)
                        if song: files.append(song)
            elif gst.element_make_from_uri(gst.URI_SRC, uri, ''):
                if uri not in library:
                    files.append(RemoteFile(uri))
                    library.add_song(files[-1])
            else:
                error = True
                break
        ctx.finish(not error, False, etime)
        if error:
            qltk.ErrorWindow(
                self, _("Unable to add songs"),
                _("<b>%s</b> uses an unsupported protocol.") % uri).run()
        else:
            if dirs: self.scan_dirs(dirs)
            if files: widgets.watcher.added(files)

    def __songlist_drag_data_recv(self, view, *args):
        if callable(self.browser.reordered): self.browser.reordered(view)
        self.songlist.set_sort_by(None, refresh=False)

    def __window_state_changed(self, window, event):
        assert window is self
        self.__window_state = event.new_window_state

    def hide(self):
        self.__hidden_state = self.__window_state
        if self.__hidden_state & gtk.gdk.WINDOW_STATE_MAXIMIZED:
            self.unmaximize()
        super(MainWindow, self).hide()

    def show(self):
        super(MainWindow, self).show()
        if self.__hidden_state & gtk.gdk.WINDOW_STATE_MAXIMIZED:
            self.maximize()

    def __show_or(self, widget, prop):
        ssv = self.song_scroller.get_property('visible')
        qxv = self.qexpander.get_property('visible')
        self.songpane.set_property('visible', ssv or qxv)
        self.songpane.set_child_packing(
            self.qexpander, expand=not ssv, fill=True, padding=0,
            pack_type=gtk.PACK_START)
        if not ssv:
            self.qexpander.set_expanded(True)

    def _create_menu(self, tips):
        ag = gtk.ActionGroup('MainWindowActions')

        actions = [
            ('Music', None, _("_Music")),
            ('AddFolders', gtk.STOCK_ADD, _('_Add a Folder...'),
             "<control>O", None, self.open_chooser),
            ('AddFiles', gtk.STOCK_ADD, _('_Add a File...'),
             None, None, self.open_chooser),
            ('AddLocation', gtk.STOCK_ADD, _('_Add a Location...'),
             None, None, self.open_location),
            ('BrowseLibrary', gtk.STOCK_FIND, _('_Browse Library'), ""),
            ("Preferences", gtk.STOCK_PREFERENCES, None, None, None,
             self.__preferences),
            ("Plugins", gtk.STOCK_EXECUTE, _("_Plugins"), None, None,
             self.__plugins),
            ("Quit", gtk.STOCK_QUIT, None, None, None, gtk.main_quit),
            ('Filters', None, _("_Filters")),

            ("NotPlayedDay", gtk.STOCK_FIND, _("Not Played To_day"),
             "", None, self.lastplayed_day),
            ("NotPlayedWeek", gtk.STOCK_FIND, _("Not Played in a _Week"),
             "", None, self.lastplayed_week),
            ("NotPlayedMonth", gtk.STOCK_FIND, _("Not Played in a _Month"),
             "", None, self.lastplayed_month),
            ("NotPlayedEver", gtk.STOCK_FIND, _("_Never Played"),
             "", None, self.lastplayed_never),
            ("Top", gtk.STOCK_GO_UP, _("_Top 40"), "", None, self.__top40),
            ("Bottom", gtk.STOCK_GO_DOWN,_("B_ottom 40"), "",
             None, self.__bottom40),
            ("Control", None, _("_Control")),
            ("Properties", gtk.STOCK_PROPERTIES, None, "<Alt>Return", None,
             self.__current_song_prop),
            ("Rating", None, _("_Rating")),

            ("Jump", gtk.STOCK_JUMP_TO, _("_Jump to Playing Song"),
             "<control>J", None, self.__jump_to_current),

            ("View", None, _("_View")),
            ("Help", None, _("_Help")),
            ]

        if const.SM_PREVIOUS.startswith("gtk-"): label = None
        else: label = const.SM_PREVIOUS
        actions.append(("Previous", gtk.STOCK_MEDIA_PREVIOUS, label,
                        "<control>comma", None, self.__previous_song))

        if const.SM_PLAY.startswith('gtk-'): label = None
        else: label = const.SM_PLAY
        actions.append(("PlayPause", gtk.STOCK_MEDIA_PLAY, label,
                        "<control>space", None, self.__play_pause))

        if const.SM_NEXT.startswith("gtk-"): label = None
        else: label = const.SM_NEXT
        actions.append(("Next", gtk.STOCK_MEDIA_NEXT, label,
                        "<control>period", None, self.__next_song))

        ag.add_actions(actions)

        from qltk.about import AboutWindow
        act = gtk.Action("About", None, None, gtk.STOCK_ABOUT)
        act.connect_object('activate', AboutWindow, self, player.playlist)
        ag.add_action(act)

        act = gtk.Action(
            "RefreshLibrary", _("Re_fresh Library"), None, gtk.STOCK_REFRESH)
        act.connect('activate', self.__rebuild)
        ag.add_action(act)
        act = gtk.Action(
            "ReloadLibrary", _("Re_load Library"), None, gtk.STOCK_REFRESH)
        act.connect('activate', self.__rebuild, True)
        ag.add_action(act)

        for tag_, lab in [
            ("genre", _("Filter on _Genre")),
            ("artist", _("Filter on _Artist")),
            ("album", _("Filter on Al_bum"))]:
            act = gtk.Action(
                "Filter%s" % util.capitalize(tag_), lab, None, gtk.STOCK_INDEX)
            act.connect_object('activate', self.__filter_on, tag_)
            ag.add_action(act)

        for (tag_, accel, label) in [
            ("genre", "G", _("Random _Genre")),
            ("artist", "T", _("Random _Artist")),
            ("album", "M", _("Random Al_bum"))]:
            act = gtk.Action("Random%s" % util.capitalize(tag_), label,
                             None, gtk.STOCK_DIALOG_QUESTION)
            act.connect('activate', self.__random, tag_)
            ag.add_action_with_accel(act, "<control>" + accel)

        ag.add_toggle_actions([
            ("SongList", None, _("Song _List"), None, None,
             self.showhide_playlist,
             config.getboolean("memory", "songlist"))])

        ag.add_toggle_actions([
            ("Queue", None, _("_Queue"), None, None,
             self.showhide_playqueue,
             config.getboolean("memory", "queue"))])

        ag.add_radio_actions([
            (a, None, l, None, None, i) for (i, (a, l, K)) in
            enumerate(browsers.get_view_browsers())
            ], browsers.index(config.get("memory", "browser")),
                             self.select_browser)

        for id, label, Kind in browsers.get_browsers():
            act = gtk.Action(id, label, None, None)
            act.connect_object(
                'activate', LibraryBrowser, Kind, widgets.watcher)
            ag.add_action(act)

        self.ui = gtk.UIManager()
        self.ui.insert_action_group(ag, -1)
        menustr = const.MENU%(browsers.BrowseLibrary(), browsers.ViewBrowser())
        self.ui.add_ui_from_string(menustr)

        # Cute. So. UIManager lets you attach tooltips, but when they're
        # for menu items, they just get ignored. So here I get to actually
        # attach them.
        tips.set_tip(
            self.ui.get_widget("/Menu/Music/RefreshLibrary"),
            _("Check for changes in your library"))
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
            self.ui.get_widget("/Menu/Control/Properties"),
            _("View and edit tags in the playing song"))
        self.connect_object('destroy', gtk.Tooltips.destroy, tips)
        tips.enable()

    def __browser_configure(self, paned, event, browser):
        if paned.get_property('position-set'):
            key = "%s_pos" % browser.__class__.__name__
            config.set("browsers", key, str(paned.get_relative()))

    def select_browser(self, activator, current):
        if isinstance(current, gtk.RadioAction):
            current = current.get_current_value()
        Browser = browsers.get(current)
        config.set("memory", "browser", Browser.__name__)
        if self.browser:
            c = self.child.get_children()[-2]
            c.remove(self.songpane)
            c.remove(self.browser)
            c.destroy()
            self.browser.destroy()
        self.browser = Browser(widgets.watcher, player.playlist)
        self.browser.connect('songs-selected', self.__browser_cb)
        if self.browser.reordered: self.songlist.enable_drop()
        else: self.songlist.disable_drop()

        if self.browser.expand:
            c = self.browser.expand()
            c.pack1(self.browser, resize=True)
            c.pack2(self.songpane, resize=True)
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
            c.pack_start(self.songpane)
        self.child.pack_end(c)
        c.show()
        self.__hide_menus()
        self.__hide_headers()
        self.__refresh_size()

    def __update_paused(self, watcher, paused):
        menu = self.ui.get_widget("/Menu/Control/PlayPause")
        if paused:
            menu.get_image().set_from_stock(
                gtk.STOCK_MEDIA_PLAY, gtk.ICON_SIZE_MENU)
            label = const.SM_PLAY
        else:
            menu.get_image().set_from_stock(
                gtk.STOCK_MEDIA_PAUSE, gtk.ICON_SIZE_MENU)
            label = const.SM_PAUSE
        text = gtk.stock_lookup(label)
        text = (text and text[1]) or label
        menu.child.set_text(text)
        menu.child.set_use_underline(True)

    def __song_ended(self, watcher, song, stopped):
        if song is None: return
        if not self.browser.dynamic(song):
            player.playlist.remove(song)
            iter = self.songlist.song_to_iter(song)
            if iter: self.songlist.get_model().remove(iter)
            self.__set_time()

    def __update_title(self, watcher, songs):
        if player.playlist.song in songs:
            song = player.playlist.song
            if song:
                self.set_title("Quod Libet - " + song.comma("~title~version"))
            else: self.set_title("Quod Libet")

    def __song_started(self, watcher, song):
        self.__update_title(watcher, [song])

        for wid in ["Jump", "Next", "Properties", "FilterGenre",
                    "FilterArtist", "FilterAlbum"]:
            self.ui.get_widget('/Menu/Control/'+wid).set_sensitive(bool(song))
        if song:
            for h in ['genre', 'artist', 'album']:
                self.ui.get_widget(
                    "/Menu/Control/Filter%s" % h.capitalize()).set_sensitive(
                    h in song)
        if song and config.getboolean("settings", "jump"):
            self.__jump_to_current(False)

    def __save_size(self, event):
        config.set("memory", "size", "%d %d" % (event.width, event.height))

    def __refresh_size(self):
        if (not self.browser.expand and
            not self.songpane.get_property('visible')):
            width, height = self.get_size()
            self.resize(width, 1)
            self.set_geometry_hints(None, max_height=1, max_width=32000)
        else:
            self.set_geometry_hints(None, max_height=-1, max_width=-1)

    def showhide_playlist(self, toggle):
        self.song_scroller.set_property('visible', toggle.get_active())
        config.set("memory", "songlist", str(toggle.get_active()))
        self.__refresh_size()

    def showhide_playqueue(self, toggle):
        self.qexpander.set_property('visible', toggle.get_active())
        self.__refresh_size()

    def __play_pause(self, *args):
        if player.playlist.song is None:
            player.playlist.reset()
            player.playlist.next()
        else: player.playlist.paused ^= True

    def __jump_to_current(self, explicit):
        watcher, songlist = widgets.watcher, self.songlist
        iter = songlist.song_to_iter(player.playlist.song)
        if iter:
            path = songlist.get_model().get_path(iter)
            if path:
                songlist.scroll_to_cell(path[0], use_align=True, row_align=0.5)
        if explicit: self.browser.scroll()

    def __next_song(self, *args): player.playlist.next()
    def __previous_song(self, *args): player.playlist.previous()

    def toggle_repeat(self, button):
        self.songlist.model.repeat = button.get_active()
        config.set("settings", "repeat", str(bool(button.get_active())))

    def __order(self, button):
        self.songlist.model.order = button.get_active()
        config.set("memory", "order", str(button.get_active()))

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
        self.__keys.block()
        window = WaitLoadWindow(self, len(library) // 7,
                                _("Scanning your library. "
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
        self.__keys.unblock()

    # Set up the preferences window.
    def __preferences(self, activator):
        from qltk.prefs import PreferencesWindow
        PreferencesWindow(self)

    def __plugins(self, activator):
        from qltk.pluginwin import PluginWindow
        PluginWindow(self, SongList.pm)

    def open_location(self, action):
        name = GetStringDialog(self, _("Add a Location"),
            _("Enter the location of an audio file:"),
            okbutton=gtk.STOCK_ADD).run()
        if name:
            if not gst.uri_is_valid(name):
                qltk.ErrorMessage(
                    self, _("Unable to add location"),
                    _("<b>%s</b> is not a valid location.") %(
                    util.escape(name))).run()
            elif not gst.element_make_from_uri(gst.URI_SRC, name, ""):
                qltk.ErrorMessage(
                    self, _("Unable to add location"),
                    _("<b>%s</b> uses an unsupported protocol.") %(
                    util.escape(name))).run()
            else:
                from formats.remote import RemoteFile
                if name not in library:
                    song = library.add_song(RemoteFile(name))
                    if song: widgets.watcher.added([song])

    def open_chooser(self, action):
        if not os.path.exists(self.last_dir):
            self.last_dir = os.environ["HOME"]

        if action.get_name() == "AddFolders":
            from qltk.chooser import FolderChooser
            chooser = FolderChooser(self, _("Add Music"), self.last_dir)
        else:
            from qltk.chooser import FileChooser
            chooser = FileChooser(
                self, _("Add Music"), formats.filter, self.last_dir)
        
        fns = chooser.run()
        chooser.destroy()
        if fns:
            if action.get_name() == "AddFolders":
                self.last_dir = fns[0]
                if self.scan_dirs(fns):
                    widgets.watcher.refresh()
                    library.save(const.LIBRARY)
            else:
                added = []
                self.last_dir = os.path.basename(fns[0])
                for filename in map(os.path.realpath, fns):
                    if filename in library: continue
                    song = library.add(filename)
                    if song: added.append(song)
                    else:
                        from traceback import format_exception_only as feo
                        tb = feo(sys.last_type, sys.last_value)
                        msg = _("%s could not be added to your library.\n\n")
                        msg %= util.escape(util.fsdecode(
                            os.path.basename(filename)))
                        msg += util.escape(util.fsdecode(
                            "".join(tb).decode(locale.getpreferredencoding())))
                        d = qltk.ErrorMessage(
                            self, _("Unable to add song"), msg)
                        d.label.set_selectable(True)
                        d.run()
                        continue
                if added:
                    widgets.watcher.added(added)

    def scan_dirs(self, fns):
        win = WaitLoadWindow(self, 0,
                             _("Scanning for new songs and "
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

    def __songs_popup_menu(self, songlist):
        path, col = songlist.get_cursor()
        header = col.header_name
        self.prep_main_popup(header, 1, 0)
        return True

    def __current_song_prop(self, *args):
        song = player.playlist.song
        if song: SongProperties([song], widgets.watcher)

    def prep_main_popup(self, header, button, time):
        menu = self.songlist.Menu(header, self.browser, widgets.watcher)
        menu.popup(None, None, None, button, time)
        return True

    def __hide_menus(self):
        menus = {'genre': ["/Menu/Control/FilterGenre",
                           "/Menu/Filters/RandomGenre"],
                 'artist': ["/Menu/Control/FilterArtist",
                           "/Menu/Filters/RandomArtist"],
                 'album':  ["/Menu/Control/FilterAlbum",
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

    def __browser_cb(self, browser, songs, sorted):
        if browser.background:
            try: bg = config.get("browsers", "background").decode('utf-8')
            except UnicodeError: bg = ""
            if bg:
                try: search = parser.parse(bg, SongList.star).search
                except parser.error: pass
                else: songs = filter(search, songs)

        self.__set_time(songs=songs)
        self.songlist.set_songs(songs, sorted)

    def __filter_on(self, header, songs=None):
        if not self.browser or not self.browser.can_filter(header):
            return
        if songs is None:
            if player.playlist.song: songs = [player.playlist.song]
            else: return

        values = set()
        if header.startswith("~#"):
            values.update([song(header, 0) for song in songs])
        else:
            for song in songs: values.update(song.list(header))
        self.browser.filter(header, list(values))

    def __hide_headers(self, activator=None):
        for column in self.songlist.get_columns():
            if self.browser.headers is None:
                column.set_visible(True)
            else:
                tag = column.header_name
                if "~" in tag[1:]: tag = filter(None, tag.split("~"))[0]
                column.set_visible(tag in self.browser.headers)

    def __cols_changed(self, songlist):
        headers = [col.header_name for col in songlist.get_columns()]
        try: headers.remove('~current')
        except ValueError: pass
        if len(headers) == len(config.get("settings", "headers").split()):
            # Not an addition or removal (handled separately)
            config.set("settings", "headers", " ".join(headers))
            SongList.headers = headers

    def __make_query(self, query):
        if self.browser.can_filter(None):
            self.browser.set_text(query.encode('utf-8'))
            self.browser.activate()

    def __refresh(self, watcher):
        self.__set_time()

    def __set_time(self, *args, **kwargs):
        statusbar = self.__statusbar
        songs = kwargs.get("songs") or self.songlist.get_selected_songs()
        if "songs" not in kwargs and len(songs) <= 1:
            songs = self.songlist.get_songs()

        i = len(songs)
        length = sum([song["~#length"] for song in songs])
        t = ngettext("%(count)d song (%(time)s)", "%(count)d songs (%(time)s)",
                i) % {'count': i, 'time': util.format_time_long(length)}
        statusbar.set_property('label', t)
        gobject.idle_add(statusbar.queue_resize)

def website_wrap(activator, link):
    if not util.website(link):
        qltk.ErrorMessage(
            widgets.main, _("Unable to start web browser"),
            _("A web browser could not be found. Please set "
              "your $BROWSER variable, or make sure "
              "/usr/bin/sensible-browser exists.")).run()

def init():
    stock.init()
    # Translators: Only translate this if GTK's stock item is incorrect
    # or missing. Don't literally translate media/next/previous/play/pause.
    const.SM_NEXT = _('gtk-media-next')
    # Translators: Only translate this if GTK does so incorrectly.
    # or missing. Don't literally translate media/next/previous/play/pause.
    const.SM_PREVIOUS = _('gtk-media-previous')

    # Translators: Only translate this if GTK does so incorrectly.
    # or missing. Don't literally translate media/next/previous/play/pause.
    const.SM_PLAY = _('gtk-media-play')
    # Translators: Only translate this if GTK does so incorrectly.
    # or missing. Don't literally translate media/next/previous/play/pause.
    const.SM_PAUSE = _('gtk-media-pause')

    gtk.window_set_default_icon_from_file("quodlibet.png")

    if config.get("settings", "headers").split() == []:
       config.set("settings", "headers", "title")
    headers = config.get("settings", "headers").split()
    SongList.set_all_column_headers(headers)
            
    for opt in config.options("header_maps"):
        val = config.get("header_maps", opt)
        util.HEADERS_FILTER[opt] = val

    from qltk.watcher import SongWatcher
    widgets.watcher = watcher = SongWatcher()

    # plugin support
    from plugins import PluginManager
    SongList.pm = PluginManager(watcher, ["./plugins", const.PLUGINS])
    SongList.pm.rescan()

    in_all =("~filename ~uri ~#lastplayed ~#rating ~#playcount ~#skipcount "
             "~#added ~#bitrate ~current").split()
    for Kind in zip(*browsers.browsers)[2]:
        if Kind.headers is not None: Kind.headers.extend(in_all)
        Kind.init(watcher)

    widgets.main = MainWindow(watcher)
    gtk.about_dialog_set_url_hook(website_wrap)

    # These stay alive in the watcher/other callbacks.
    from qltk.remote import FSInterface, FIFOControl
    FSInterface(watcher)
    FIFOControl(watcher, widgets.main, player.playlist)

    from qltk.count import CountManager
    CountManager(watcher, widgets.main.playlist)

    from qltk.trayicon import TrayIcon
    TrayIcon(watcher, widgets.main, player.playlist)

    flag = widgets.main.songlist.get_columns()[-1].get_clickable
    while not flag(): gtk.main_iteration()
    song = library.get(config.get("memory", "song"))
    player.playlist.setup(watcher, widgets.main.playlist, song)
    widgets.main.show()
    return widgets.main

def save_library(window, player):
    player.quit()

    # If something goes wrong here, it'll probably be caught
    # saving the library anyway.
    try: config.write(const.CONFIG)
    except EnvironmentError, err: pass

    for fn in [const.CONTROL, const.PAUSED, const.CURRENT]:
        # FIXME: PAUSED and CURRENT should be handled by
        # FSInterface.
        try: os.unlink(fn)
        except EnvironmentError: pass

    window.destroy()

    print to(_("Saving library."))
    try: library.save(const.LIBRARY)
    except EnvironmentError, err:
        err = str(err).decode('utf-8', 'replace')
        qltk.ErrorMessage(None, _("Unable to save library"), err).run()

def no_sink_quit(sink):
    header = _("Unable to open audio device")
    body = _("Quod Libet tried to access the 'alsasink', 'osssink', and "
             "'%(sink)s' drivers but could not open any of them. Set your "
             "GStreamer pipeline by changing the\n"
             "    <b>pipeline = %(sink)s</b>\n"
             "line in ~/.quodlibet/config.") % {"sink": sink}
    qltk.ErrorMessage(None, header, body).run()
    gtk.main_quit()

def no_source_quit():
    header = _("Unable to open files")
    body = _("Quod Libet could not find the 'filesrc' GStreamer element. "
             "Check your GStreamer installation.")
    qltk.ErrorMessage(None, header, body).run()
    gtk.main_quit()
