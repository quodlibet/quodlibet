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
import formats
import util
import locale
import widgets

from library import library

if sys.version_info < (2, 4): from sets import Set as set
from qltk.properties import SongProperties
from qltk.songlist import SongList
from qltk.wlw import WaitLoadWindow
from qltk.getstring import GetStringDialog
from qltk.browser import LibraryBrowser
from qltk.msg import ErrorMessage
from qltk.information import Information
from util.uri import URI
from parse import Query

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

    def __init__(self, watcher, player, visible):
        super(MainSongList, self).__init__(watcher)
        self.set_rules_hint(True)
        s = watcher.connect_object('removed', map, player.remove)
        self.connect_object('destroy', watcher.disconnect, s)
        self.connect_object('row-activated', self.__select_song, player)
        self.connect_object('notify::visible', self.__visibility, visible)

    def __visibility(self, visible, event):
        visible.set_active(self.get_property('visible'))

    def __select_song(self, player, indices, col):
        iter = self.model.get_iter(indices)
        player.go_to(iter)
        if player.song: player.paused = False

    def set_sort_by(self, *args, **kwargs):
        SongList.set_sort_by(self, *args, **kwargs)
        tag, reverse = self.get_sort_by()
        config.set('memory', 'sortby', "%d%s" % (int(reverse), tag))

class QuodLibetWindow(gtk.Window):
    def __init__(self, watcher, player):
        gtk.Window.__init__(self)
        self.last_dir = os.path.expanduser("~")

        tips = qltk.Tooltips(self)
        self.set_title("Quod Libet")

        self.set_default_size(
            *map(int, config.get('memory', 'size').split()))
        self.add(gtk.VBox())

        # create main menubar, load/restore accelerator groups
        self.__create_menu(tips, player)
        self.add_accel_group(self.ui.get_accel_group())

        accel_fn = os.path.join(const.DIR, "accels")
        gtk.accel_map_load(accel_fn)
        accelgroup = gtk.accel_groups_from_object(self)[0]
        accelgroup.connect('accel-changed',
                lambda *args: gtk.accel_map_save(accel_fn))
        self.child.pack_start(self.ui.get_widget("/Menu"), expand=False)

        self.__vbox = realvbox = gtk.VBox(spacing=6)
        realvbox.set_border_width(6)
        self.child.pack_start(realvbox)

        # get the playlist up before other stuff
        from qltk.queue import QueueExpander
        self.songlist = MainSongList(
            watcher, player, self.ui.get_widget("/Menu/View/SongList"))
        self.add_accel_group(self.songlist.accelerators)
        self.songlist.connect_after(
            'drag-data-received', self.__songlist_drag_data_recv)
        self.qexpander = QueueExpander(
            self.ui.get_widget("/Menu/View/Queue"), watcher)
        from qltk.songlist import PlaylistMux
        self.playlist = PlaylistMux(
            watcher, self.qexpander.model, self.songlist.model)

        # song info (top part of window)
        hbox = gtk.HBox(spacing=6)

        # play controls
        from qltk.controls import PlayControls
        t = PlayControls(watcher, player)
        self.volume = t.volume
        hbox.pack_start(t, expand=False, fill=False)

        # song text
        from qltk.info import SongInfo
        text = SongInfo(watcher, player)
        hbox.pack_start(text)

        # cover image
        from qltk.cover import CoverImage
        self.image = CoverImage()
        watcher.connect('song-started', self.image.set_song)
        hbox.pack_start(self.image, expand=False)

        realvbox.pack_start(hbox, expand=False)

        # status area
        align = gtk.Alignment(xscale=1, yscale=1)
        align.set_padding(0, 6, 6, 6)
        hbox = gtk.HBox(spacing=12)
        hb = gtk.HBox(spacing=3)
        from qltk.playorder import PlayOrder
        label = gtk.Label(_("_Order:"))
        self.order = order = PlayOrder(self.songlist.model)
        label.set_mnemonic_widget(order)
        label.set_use_underline(True)
        hb.pack_start(label)
        hb.pack_start(order)
        hbox.pack_start(hb, expand=False)
        self.repeat = repeat = qltk.ccb.ConfigCheckButton(
            _("_Repeat"), "settings", "repeat")
        tips.set_tip(repeat, _("Restart the playlist when finished"))
        hbox.pack_start(repeat, expand=False)
        self.__statusbar = gtk.Label()
        self.__statusbar.set_text(_("No time information"))
        # GTK (2.8?) rounding error, 1.0 clips the rightmost pixel.
        self.__statusbar.set_alignment(0.999999, 0.5)
        self.__statusbar.set_ellipsize(pango.ELLIPSIZE_START)
        hbox.pack_start(self.__statusbar)
        align.add(hbox)
        self.child.pack_end(align, expand=False)

        # song list
        self.song_scroller = sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.add(self.songlist)

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
        self.__keys = MmKeys(player)

        self.child.show_all()
        sw.show_all()
        self.select_browser(self, config.get("memory", "browser"), player)
        self.browser.restore()
        self.browser.activate()
        self.showhide_playlist(self.ui.get_widget("/Menu/View/SongList"))
        self.showhide_playqueue(self.ui.get_widget("/Menu/View/Queue"))

        repeat.connect('toggled', self.__repeat, self.songlist.model)
        repeat.set_active(config.getboolean('settings', 'repeat'))

        self.connect('configure-event', QuodLibetWindow.__save_size)
        self.connect('window-state-event', self.__window_state_changed)
        self.__hidden_state = 0

        self.songlist.connect('popup-menu', self.__songs_popup_menu)
        self.songlist.connect('columns-changed', self.__cols_changed)
        self.songlist.connect('columns-changed', self.__hide_headers)
        self.songlist.get_selection().connect('changed', self.__set_time)

        watcher.connect('removed', self.__set_time)
        watcher.connect('added', self.__set_time)
        watcher.connect('changed', self.__update_title, player)
        watcher.connect('song-started', self.__song_started, player)
        watcher.connect_after('song-ended', self.__song_ended, player)
        watcher.connect('paused', self.__update_paused, True)
        watcher.connect('unpaused', self.__update_paused, False)

        targets = [("text/uri-list", 0, 1)]
        self.drag_dest_set(
            gtk.DEST_DEFAULT_ALL, targets, gtk.gdk.ACTION_DEFAULT)
        self.connect_object('drag-motion', QuodLibetWindow.__drag_motion, self)
        self.connect_object('drag-leave', QuodLibetWindow.__drag_leave, self)
        self.connect_object(
            'drag-data-received', QuodLibetWindow.__drag_data_received, self)

        self.resize(*map(int, config.get("memory", "size").split()))

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
            uri = sel.data.decode('utf16', 'replace').split('\n')[0]
            uris = [uri.encode('ascii', 'replace')]

        dirs = []
        files = []
        error = False
        from formats.remote import RemoteFile
        for uri in uris:
            try: uri = URI(uri)
            except ValueError: continue

            if uri.is_filename:
                loc = os.path.normpath(uri.filename)
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
            ErrorMessage(
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
        super(QuodLibetWindow, self).hide()

    def present(self):
        super(QuodLibetWindow, self).present()
        if self.__hidden_state & gtk.gdk.WINDOW_STATE_MAXIMIZED:
            self.maximize()

    def show(self):
        super(QuodLibetWindow, self).show()
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

    def __create_menu(self, tips, player):
        ag = gtk.ActionGroup('QuodLibetWindowActions')

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
            ("Plugins", stock.PLUGINS, None, None, None,
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
            ("EditTags", stock.EDIT_TAGS, None, "", None,
             self.__current_song_prop),
            ("Information", gtk.STOCK_INFO, None, None, None,
             self.__current_song_info),
            ("Rating", None, _("_Rating")),

            ("Jump", gtk.STOCK_JUMP_TO, _("_Jump to Playing Song"),
             "<control>J", None, self.__jump_to_current),

            ("View", None, _("_View")),
            ("Help", None, _("_Help")),
            ]

        actions.append(("Previous", gtk.STOCK_MEDIA_PREVIOUS, None,
                        "<control>comma", None, self.__previous_song))

        actions.append(("PlayPause", gtk.STOCK_MEDIA_PLAY, None,
                        "<control>space", None, self.__play_pause))

        actions.append(("Next", gtk.STOCK_MEDIA_NEXT, None,
                        "<control>period", None, self.__next_song))

        ag.add_actions(actions)

        from qltk.about import AboutWindow
        act = gtk.Action("About", None, None, gtk.STOCK_ABOUT)
        act.connect_object('activate', AboutWindow, self, player)
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
            act.connect_object('activate', self.__filter_on, tag_, None, player)
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
                             self.select_browser, player)

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

    def __browser_configure(self, paned, event, browser):
        if paned.get_property('position-set'):
            key = "%s_pos" % browser.__class__.__name__
            config.set("browsers", key, str(paned.get_relative()))

    def select_browser(self, activator, current, player):
        if isinstance(current, gtk.RadioAction):
            current = current.get_current_value()
        Browser = browsers.get(current)
        config.set("memory", "browser", Browser.__name__)
        if self.browser:
            c = self.__vbox.get_children()[-1]
            c.remove(self.songpane)
            c.remove(self.browser)
            c.destroy()
            if self.browser.accelerators:
                self.remove_accel_group(self.browser.accelerators)
            self.browser.destroy()
        self.browser = Browser(widgets.watcher, player)
        self.browser.connect('songs-selected', self.__browser_cb)
        if self.browser.reordered: self.songlist.enable_drop()
        else: self.songlist.disable_drop()
        if self.browser.accelerators:
            self.add_accel_group(self.browser.accelerators)

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
            c = gtk.VBox(spacing=6)
            c.pack_start(self.browser, expand=False)
            c.pack_start(self.songpane)
        self.__vbox.pack_end(c)
        c.show()
        self.__hide_menus()
        self.__hide_headers()
        self.__refresh_size()

    def __update_paused(self, watcher, paused):
        menu = self.ui.get_widget("/Menu/Control/PlayPause")
        if paused: key = gtk.STOCK_MEDIA_PLAY
        else: key = gtk.STOCK_MEDIA_PAUSE
        text = gtk.stock_lookup(key)[1]
        menu.get_image().set_from_stock(key, gtk.ICON_SIZE_MENU)
        menu.child.set_text(text)
        menu.child.set_use_underline(True)

    def __song_ended(self, watcher, song, stopped, player):
        if song is None: return
        if not self.browser.dynamic(song):
            player.remove(song)
            iter = self.songlist.model.find(song)
            if iter:
                self.songlist.model.remove(iter)
                self.__set_time()

    def __update_title(self, watcher, songs, player):
        if player.song in songs:
            song = player.song
            if song:
                self.set_title("Quod Libet - " + song.comma("~title~version"))
            else: self.set_title("Quod Libet")

    def __song_started(self, watcher, song, player):
        self.__update_title(watcher, [song], player)

        for wid in ["Jump", "Next", "EditTags", "Information"]:
            self.ui.get_widget('/Menu/Control/'+wid).set_sensitive(bool(song))
        for wid in ["FilterAlbum", "FilterArtist", "FilterGenre"]:
            self.ui.get_widget('/Menu/Filters/'+wid).set_sensitive(bool(song))
        if song:
            for h in ['genre', 'artist', 'album']:
                self.ui.get_widget(
                    "/Menu/Filters/Filter%s" % h.capitalize()).set_sensitive(
                    h in song)
        if song and config.getboolean("settings", "jump"):
            self.__jump_to_current(False)

    def __save_size(self, event):
        config.set("memory", "size", "%d %d" % (event.width, event.height))

    def __refresh_size(self):
        if (not self.browser.expand and
            not self.songpane.get_property('visible')):
            width, height = self.get_size()
            height = self.size_request()[1]
            self.resize(width, height)
            self.set_geometry_hints(None, max_height=height, max_width=32000)
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
        if player.playlist.song is None: return
        elif player.playlist.song == self.songlist.model.current:
            path = self.songlist.model.current_path
            self.songlist.scroll_to_cell(
                path[0], use_align=True, row_align=0.5)
        if explicit: self.browser.scroll(player.playlist.song)

    def __next_song(self, *args): player.playlist.next()
    def __previous_song(self, *args): player.playlist.previous()

    def __repeat(self, button, model):
        model.repeat = button.get_active()

    def __random(self, item, key):
        if self.browser.can_filter(key):
            values = self.browser.list(key)
            if values:
                import random
                value = random.choice(values)
                self.browser.filter(key, [value])

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
        self.__keys.unblock()

    # Set up the preferences window.
    def __preferences(self, activator):
        from qltk.prefs import PreferencesWindow
        PreferencesWindow(self)

    def __plugins(self, activator):
        from qltk.pluginwin import PluginWindow
        PluginWindow(self)

    def open_location(self, action):
        name = GetStringDialog(self, _("Add a Location"),
            _("Enter the location of an audio file:"),
            okbutton=gtk.STOCK_ADD).run()
        if name:
            if not gst.uri_is_valid(name):
                ErrorMessage(
                    self, _("Unable to add location"),
                    _("<b>%s</b> is not a valid location.") %(
                    util.escape(name))).run()
            elif not gst.element_make_from_uri(gst.URI_SRC, name, ""):
                ErrorMessage(
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
                    self.browser.activate()
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
                        d = ErrorMessage(self, _("Unable to add song"), msg)
                        d.label.set_selectable(True)
                        d.run()
                        continue
                if added:
                    widgets.watcher.added(added)
                    self.browser.activate()

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

    def __songs_popup_menu(self, songlist):
        path, col = songlist.get_cursor()
        header = col.header_name
        menu = self.songlist.Menu(header, self.browser, widgets.watcher)
        menu.popup(None, None, None, 0, gtk.get_current_event_time())
        return True

    def __current_song_prop(self, *args):
        song = player.playlist.song
        if song: SongProperties(widgets.watcher, [song])

    def __current_song_info(self, *args):
        song = player.playlist.song
        if song: Information(widgets.watcher, [song])

    def __hide_menus(self):
        menus = {'genre': ["/Menu/Filters/FilterGenre",
                           "/Menu/Filters/RandomGenre"],
                 'artist': ["/Menu/Filters/FilterArtist",
                           "/Menu/Filters/RandomArtist"],
                 'album':  ["/Menu/Filters/FilterAlbum",
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
                try: search = Query(bg, SongList.star).search
                except Query.error: pass
                else: songs = filter(search, songs)

        self.__set_time(songs=songs)
        self.songlist.set_songs(songs, sorted)

    def __filter_on(self, header, songs, player):
        if not self.browser or not self.browser.can_filter(header):
            return
        if songs is None:
            if player.song: songs = [player.song]
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
                for tag in util.tagsplit(column.header_name):
                    if tag in self.browser.headers:
                        column.set_visible(True)
                        break
                else: column.set_visible(False)

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

    def __set_time(self, *args, **kwargs):
        statusbar = self.__statusbar
        songs = kwargs.get("songs") or self.songlist.get_selected_songs()
        if "songs" not in kwargs and len(songs) <= 1:
            songs = self.songlist.get_songs()

        i = len(songs)
        length = sum([song["~#length"] for song in songs])
        t = self.browser.statusbar(i) % {
            'count': i, 'time': util.format_time_long(length)}
        statusbar.set_text(t)
        gobject.idle_add(statusbar.queue_resize)
