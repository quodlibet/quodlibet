# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import random
import sys

import gst
import gtk
import pango

import browsers
import config
import const
import formats
import player
import qltk
import qltk.about
import stock
import util

from formats.remote import RemoteFile
from library import library, librarian
from parse import Query
from qltk.browser import LibraryBrowser
from qltk.chooser import FolderChooser, FileChooser
from qltk.controls import PlayControls
from qltk.cover import CoverImage
from qltk.getstring import GetStringDialog
from qltk.info import SongInfo
from qltk.information import Information
from qltk.mmkeys import MmKeys
from qltk.msg import ErrorMessage
from qltk.playorder import PlayOrder
from qltk.pluginwin import PluginWindow
from qltk.properties import SongProperties
from qltk.prefs import PreferencesWindow
from qltk.queue import QueueExpander
from qltk.songlist import SongList, PlaylistMux
from qltk.x import RPaned
from util import copool
from util.uri import URI

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
                if model[iter][0].get("~error"):
                    stock = gtk.STOCK_DIALOG_ERROR
                elif model.get_path(iter) != model.current_path:
                    stock = ''
                elif model.sourced:
                    stock = pixbuf[player.playlist.paused]
                else: stock = gtk.STOCK_MEDIA_STOP
                cell.set_property('stock-id', stock)
            except AttributeError: pass

        def __init__(self):
            super(MainSongList.CurrentColumn, self).__init__("", self._render)
            self.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
            self.set_fixed_width(24)
            self.set_cell_data_func(self._render, self._cdf)
            self.header_name = "~current"

    def __init__(self, library, player, visible):
        super(MainSongList, self).__init__(library, player)
        self.set_rules_hint(True)
        s = library.librarian.connect_object('removed', map, player.remove)
        self.connect_object('destroy', library.librarian.disconnect, s)
        self.connect_object('row-activated', self.__select_song, player)
        self.connect_object('notify::visible', self.__visibility, visible)

    def __visibility(self, visible, event):
        visible.set_active(self.get_property('visible'))

    def __select_song(self, player, indices, col):
        iter = self.model.get_iter(indices)
        player.go_to(iter)
        if player.song: player.paused = False

    def set_sort_by(self, *args, **kwargs):
        super(MainSongList, self).set_sort_by(*args, **kwargs)
        tag, reverse = self.get_sort_by()
        config.set('memory', 'sortby', "%d%s" % (int(reverse), tag))

class StatusBar(gtk.HBox):
    def __init__(self):
        super(StatusBar, self).__init__()
        self.progress = gtk.ProgressBar()
        self.count = gtk.Label(_("No time information"))
        self.count.set_justify(gtk.JUSTIFY_RIGHT)
        self.count.set_ellipsize(pango.ELLIPSIZE_START)
        self.pack_start(self.count)
        progress_label = gtk.Label()
        progress_label.set_justify(gtk.JUSTIFY_RIGHT)
        progress_label.set_ellipsize(pango.ELLIPSIZE_START)
        # GtkProgressBar can't show text when pulsing. Proxy its set_text
        # method to a label that can.
        self.progress.set_text = progress_label.set_text
        hb = gtk.HBox(spacing=12)
        hb.pack_start(progress_label)
        hb.pack_start(self.progress, expand=False)
        pause = gtk.ToggleButton()
        pause.add(gtk.image_new_from_stock(
            gtk.STOCK_MEDIA_PAUSE, gtk.ICON_SIZE_MENU))
        pause.connect('toggled', self.__pause)
        hb.pack_start(pause, expand=False)
        self.pack_start(hb)
        self.progress.connect('notify::visible', self.__toggle, pause, hb)
        self.progress.connect_object(
            'notify::fraction', lambda *args: args[0].set_active(False), pause)
        self.count.show()

    def __pause(self, pause):
        if pause.get_active():
            copool.pause("library")
        else:
            copool.resume("library")

    def __toggle(self, bar, property, pause, hb):
        if self.progress.props.visible:
            self.count.hide()
            pause.set_active(False)
            hb.show_all()
        else:
            self.count.show()
            hb.hide()

class QuodLibetWindow(gtk.Window):
    def __init__(self, library, player):
        super(QuodLibetWindow, self).__init__()
        self.last_dir = os.path.expanduser("~")

        tips = qltk.Tooltips(self)
        self.set_title("Quod Libet")

        self.set_default_size(
            *map(int, config.get('memory', 'size').split()))
        self.add(gtk.VBox())

        # create main menubar, load/restore accelerator groups
        self.__create_menu(tips, player)
        self.add_accel_group(self.ui.get_accel_group())

        accel_fn = os.path.join(const.USERDIR, "accels")
        gtk.accel_map_load(accel_fn)
        accelgroup = gtk.accel_groups_from_object(self)[0]
        accelgroup.connect('accel-changed',
                lambda *args: gtk.accel_map_save(accel_fn))
        self.child.pack_start(self.ui.get_widget("/Menu"), expand=False)

        self.__vbox = realvbox = gtk.VBox(spacing=6)
        realvbox.set_border_width(6)
        self.child.pack_start(realvbox)

        # get the playlist up before other stuff
        self.songlist = MainSongList(
            library, player, self.ui.get_widget("/Menu/View/SongList"))
        self.add_accel_group(self.songlist.accelerators)
        self.songlist.connect_after(
            'drag-data-received', self.__songlist_drag_data_recv)
        self.qexpander = QueueExpander(
            self.ui.get_widget("/Menu/View/Queue"), library, player)
        self.playlist = PlaylistMux(
            player, self.qexpander.model, self.songlist.model)

        # song info (top part of window)
        hbox = gtk.HBox(spacing=6)

        # play controls
        t = PlayControls(player, library.librarian)
        self.volume = t.volume
        hbox.pack_start(t, expand=False, fill=False)

        # song text
        text = SongInfo(library.librarian, player)
        hbox.pack_start(text)

        # cover image
        self.image = CoverImage()
        player.connect('song-started', self.image.set_song)
        hbox.pack_start(self.image, expand=False)

        realvbox.pack_start(hbox, expand=False)

        # status area
        align = gtk.Alignment(xscale=1, yscale=1)
        align.set_padding(0, 6, 6, 6)
        hbox = gtk.HBox(spacing=12)
        hb = gtk.HBox(spacing=3)
        label = gtk.Label(_("_Order:"))
        label.set_size_request(-1, 28)
        self.order = order = PlayOrder(self.songlist.model, player)
        label.set_mnemonic_widget(order)
        label.set_use_underline(True)
        hb.pack_start(label)
        hb.pack_start(order)
        hbox.pack_start(hb, expand=False)
        self.repeat = repeat = qltk.ccb.ConfigCheckButton(
            _("_Repeat"), "settings", "repeat")
        tips.set_tip(repeat, _("Restart the playlist when finished"))
        hbox.pack_start(repeat, expand=False)
        self.statusbar = StatusBar()
        hbox.pack_start(self.statusbar)
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

        self.__keys = MmKeys(player)

        self.child.show_all()
        sw.show_all()
        self.select_browser(
            self, config.get("memory", "browser"), library, player)
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

        library.librarian.connect('removed', self.__set_time)
        library.librarian.connect('added', self.__set_time)
        library.librarian.connect_object('changed', self.__update_title, player)
        player.connect('song-ended', self.__song_ended)
        player.connect('song-started', self.__song_started)
        player.connect('paused', self.__update_paused, True)
        player.connect('unpaused', self.__update_paused, False)

        targets = [("text/uri-list", 0, 1)]
        self.drag_dest_set(
            gtk.DEST_DEFAULT_ALL, targets, gtk.gdk.ACTION_DEFAULT)
        self.connect_object('drag-motion', QuodLibetWindow.__drag_motion, self)
        self.connect_object('drag-leave', QuodLibetWindow.__drag_leave, self)
        self.connect_object(
            'drag-data-received', QuodLibetWindow.__drag_data_received, self)

        self.resize(*map(int, config.get("memory", "size").split()))
        self.__rebuild(None, False)

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
        for uri in uris:
            try: uri = URI(uri)
            except ValueError: continue

            if uri.is_filename:
                loc = os.path.normpath(uri.filename)
                if os.path.isdir(loc): dirs.append(loc)
                else:
                    loc = os.path.realpath(loc)
                    if loc not in library:
                        song = library.add_filename(loc)
                        if song: files.append(song)
            elif gst.element_make_from_uri(gst.URI_SRC, uri, ''):
                if uri not in library:
                    files.append(RemoteFile(uri))
                    library.add([files[-1]])
            else:
                error = True
                break
        ctx.finish(not error, False, etime)
        if error:
            ErrorMessage(
                self, _("Unable to add songs"),
                _("<b>%s</b> uses an unsupported protocol.") % uri).run()
        else:
            if dirs:
                copool.add(library.scan, dirs, self.__status.bar.progress,
                           funcid="library")

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

        act = gtk.Action("About", None, None, gtk.STOCK_ABOUT)
        act.connect_object('activate', qltk.about.show, self, player)
        ag.add_action_with_accel(act, None)

        act = gtk.Action(
            "RefreshLibrary", _("Re_fresh Library"), None, gtk.STOCK_REFRESH)
        act.connect('activate', self.__rebuild, False)
        ag.add_action_with_accel(act, None)
        act = gtk.Action(
            "ReloadLibrary", _("Re_load Library"), None, gtk.STOCK_REFRESH)
        act.connect('activate', self.__rebuild, True)
        ag.add_action_with_accel(act, None)

        for tag_, lab in [
            ("genre", _("Filter on _Genre")),
            ("artist", _("Filter on _Artist")),
            ("album", _("Filter on Al_bum"))]:
            act = gtk.Action(
                "Filter%s" % util.capitalize(tag_), lab, None, gtk.STOCK_INDEX)
            act.connect_object('activate', self.__filter_on, tag_, None, player)
            ag.add_action_with_accel(act, None)

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

        view_actions = []
        for i, Kind in enumerate(browsers.browsers):
            action = "View" + Kind.__name__
            label = Kind.accelerated_name
            view_actions.append((action, None, label, None, None, i))
        current = browsers.index(config.get("memory", "browser"))
        ag.add_radio_actions(
            view_actions, current, self.select_browser, (library, player))

        for Kind in browsers.browsers:
            if not Kind.in_menu: continue
            action = "Browser" + Kind.__name__
            label = Kind.accelerated_name
            act = gtk.Action(action, label, None, None)
            act.connect_object('activate', LibraryBrowser, Kind, library)
            ag.add_action_with_accel(act, None)

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

    def select_browser(self, activator, current, library, player):
        if isinstance(current, gtk.RadioAction):
            current = current.get_current_value()
        Browser = browsers.get(current)
        config.set("memory", "browser", Browser.__name__)
        if self.browser:
            container = self.browser.__container
            self.browser.unpack(container, self.songpane)
            if self.browser.accelerators:
                self.remove_accel_group(self.browser.accelerators)
            container.destroy()
            self.browser.destroy()
        self.browser = Browser(library, player)
        self.browser.connect('songs-selected', self.__browser_cb)
        if self.browser.reordered:
            self.songlist.enable_drop()
        elif self.browser.dropped:
            self.songlist.enable_drop(False)
        else: self.songlist.disable_drop()
        if self.browser.accelerators:
            self.add_accel_group(self.browser.accelerators)

        container = self.browser.__container = self.browser.pack(self.songpane)
        # Save position if container is a RPaned
        if isinstance(container, RPaned):
            try:
                key = "%s_pos" % self.browser.__class__.__name__
                val = config.getfloat("browsers", key)
            except: val = 0.4
            container.connect(
                'notify::position', self.__browser_configure, self.browser)
            def set_size(paned, alloc, pos):
                paned.set_relative(pos)
                paned.disconnect(paned._size_sig)
                # The signal disconnects itself! I hate GTK sizing.
                del(paned._size_sig)
            sig = container.connect('size-allocate', set_size, val)
            container._size_sig = sig

        player.replaygain_profiles[0] = self.browser.replaygain_profiles
        player.volume = player.volume
        self.__vbox.pack_end(container)
        container.show()
        self.__hide_menus()
        self.__hide_headers()
        self.__refresh_size()

    def __update_paused(self, player, paused):
        menu = self.ui.get_widget("/Menu/Control/PlayPause")
        if paused: key = gtk.STOCK_MEDIA_PLAY
        else: key = gtk.STOCK_MEDIA_PAUSE
        text = gtk.stock_lookup(key)[1]
        menu.get_image().set_from_stock(key, gtk.ICON_SIZE_MENU)
        menu.child.set_text(text)
        menu.child.set_use_underline(True)

    def __song_ended(self, player, song, stopped):
        if song is None: return
        if not self.browser.dynamic(song):
            player.remove(song)
            iter = self.songlist.model.find(song)
            if iter:
                self.songlist.model.remove(iter)
                self.__set_time()

    def __update_title(self, player, songs):
        song = player.info
        if song:
            self.set_title("Quod Libet - " + song.comma("~title~version"))
        else: self.set_title("Quod Libet")

    def __song_started(self, player, song):
        if song is None:
            self.__update_title(player, [song])

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
        else: player.playlist.paused ^= True

    def __jump_to_current(self, explicit):
        if player.playlist.song is None: return
        elif player.playlist.song == self.songlist.model.current:
            path = self.songlist.model.current_path
            self.songlist.scroll_to_cell(
                path[0], use_align=True, row_align=0.5)
            if explicit:
                iter = self.songlist.model.current_iter
                selection = self.songlist.get_selection()
                selection.unselect_all()
                selection.select_path(path)
        if explicit: self.browser.scroll(player.playlist.song)

    def __next_song(self, *args): player.playlist.next()
    def __previous_song(self, *args): player.playlist.previous()

    def __repeat(self, button, model):
        model.repeat = button.get_active()

    def __random(self, item, key):
        if self.browser.can_filter(key):
            values = self.browser.list(key)
            if values:
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
        songs = [song["~#playcount"] for song in library]
        if len(songs) == 0: return
        songs.sort()
        if len(songs) < 40:
            self.__make_query("#(playcount > %d)" % (songs[0] - 1))
        else:
            self.__make_query("#(playcount > %d)" % (songs[-40] - 1))

    def __bottom40(self, menuitem):
        songs = [song["~#playcount"] for song in library]
        if len(songs) == 0: return
        songs.sort()
        if len(songs) < 40:
            self.__make_query("#(playcount < %d)" % (songs[0] + 1))
        else:
            self.__make_query("#(playcount < %d)" % (songs[-40] + 1))

    def __rebuild(self, activator, force):
        paths = config.get("settings", "scan").split(":")
        copool.add(library.rebuild, paths, self.statusbar.progress, force,
                   funcid="library")

    # Set up the preferences window.
    def __preferences(self, activator):
        PreferencesWindow(self)

    def __plugins(self, activator):
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
                if name not in library:
                    song = library.add([RemoteFile(name)])

    def open_chooser(self, action):
        if not os.path.exists(self.last_dir):
            self.last_dir = const.HOME

        if action.get_name() == "AddFolders":
            chooser = FolderChooser(self, _("Add Music"), self.last_dir)
            cb = gtk.CheckButton(_("Watch this folder for new songs"))
            cb.set_active(not config.get("settings", "scan"))
            cb.show()
            chooser.set_extra_widget(cb)
        else:
            chooser = FileChooser(
                self, _("Add Music"), formats.filter, self.last_dir)
            cb = None
        
        fns = chooser.run()
        chooser.destroy()
        if fns:
            if action.get_name() == "AddFolders":
                self.last_dir = fns[0]
                copool.add(library.scan, fns, self.statusbar.progress,
                           funcid="library")
            else:
                added = []
                self.last_dir = os.path.basename(fns[0])
                for filename in map(os.path.realpath, fns):
                    if filename in library: continue
                    song = library.add_filename(filename)
                    if song: added.append(song)
                    else:
                        from traceback import format_exception_only as feo
                        tb = feo(sys.last_type, sys.last_value)
                        msg = _("%s could not be added to your library.\n\n")
                        msg %= util.escape(util.fsdecode(
                            os.path.basename(filename)))
                        msg += util.escape("".join(tb).decode(
                            const.ENCODING, "replace"))
                        d = ErrorMessage(self, _("Unable to add song"), msg)
                        d.label.set_selectable(True)
                        d.run()
                        continue
                if added:
                    self.browser.activate()

        if cb and cb.get_active():
            dirs = config.get("settings", "scan").split(":")
            for fn in fns:
                if fn not in dirs: dirs.append(fn)
            dirs = ":".join(dirs)
            config.set("settings", "scan", dirs)

    def __songs_popup_menu(self, songlist):
        path, col = songlist.get_cursor()
        header = col.header_name
        menu = self.songlist.Menu(header, self.browser, library)
        if menu is not None:
            return self.songlist.popup_menu(menu, 0,
                    gtk.get_current_event_time())

    def __current_song_prop(self, *args):
        song = player.playlist.song
        if song: SongProperties(librarian, [song])

    def __current_song_info(self, *args):
        song = player.playlist.song
        if song: Information(librarian, [song])

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
        songs = kwargs.get("songs") or self.songlist.get_selected_songs()
        if "songs" not in kwargs and len(songs) <= 1:
            songs = self.songlist.get_songs()
        i = len(songs)
        length = sum([song["~#length"] for song in songs])
        t = self.browser.statusbar(i) % {
            'count': i, 'time': util.format_time_long(length)}
        self.statusbar.count.set_text(t)
