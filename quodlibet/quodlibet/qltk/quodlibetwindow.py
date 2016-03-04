# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

from gi.repository import Gtk, Gdk, GLib, Gio, GObject

import quodlibet

from quodlibet import browsers
from quodlibet import config
from quodlibet import const
from quodlibet import formats
from quodlibet import qltk
from quodlibet import util
from quodlibet import app

from quodlibet.formats.remote import RemoteFile
from quodlibet.qltk.browser import LibraryBrowser, FilterMenu
from quodlibet.qltk.chooser import FolderChooser, FileChooser
from quodlibet.qltk.controls import PlayControls
from quodlibet.qltk.cover import CoverImage
from quodlibet.qltk.getstring import GetStringDialog
from quodlibet.qltk.bookmarks import EditBookmarks
from quodlibet.qltk.shortcuts import show_shortcuts
from quodlibet.qltk.info import SongInfo
from quodlibet.qltk.information import Information
from quodlibet.qltk.msg import ErrorMessage, WarningMessage
from quodlibet.qltk.notif import StatusBar, TaskController
from quodlibet.qltk.playorder import PlayOrder
from quodlibet.qltk.pluginwin import PluginWindow
from quodlibet.qltk.properties import SongProperties
from quodlibet.qltk.prefs import PreferencesWindow
from quodlibet.qltk.queue import QueueExpander
from quodlibet.qltk.songlist import SongList, get_columns, set_columns
from quodlibet.qltk.songmodel import PlaylistMux
from quodlibet.qltk.x import ConfigRVPaned, Align, ScrolledWindow, Action
from quodlibet.qltk.x import SymbolicIconImage, ToggleAction, RadioAction
from quodlibet.qltk.x import SeparatorMenuItem, MenuItem, CellRendererPixbuf
from quodlibet.qltk import Icons
from quodlibet.qltk.about import AboutDialog
from quodlibet.util import copool, connect_destroy, connect_after_destroy
from quodlibet.util.library import get_scan_dirs, set_scan_dirs
from quodlibet.util.uri import URI
from quodlibet.util import connect_obj
from quodlibet.util.path import glib2fsnative, get_home_dir
from quodlibet.util.library import background_filter, scan_library
from quodlibet.qltk.window import PersistentWindowMixin, Window, on_first_map
from quodlibet.qltk.songlistcolumns import SongListColumn


class PlayerOptions(GObject.Object):
    """Provides a simplified interface for playback options.

    This currently provides a limited view on the play order state which is
    useful for external interfaces (mpd, mpris, etc.) and for reducing
    the dependency on the state holding widgets in the main window.

    Usable as long as the main window is not destroyedor until destroy()
    is called.
    """

    __gproperties__ = {
        'random': (bool, '', '', False,
                   GObject.ParamFlags.READABLE | GObject.ParamFlags.WRITABLE),
        'repeat': (bool, '', '', False,
                   GObject.ParamFlags.READABLE | GObject.ParamFlags.WRITABLE),
        'single': (bool, '', '', False,
                   GObject.ParamFlags.READABLE | GObject.ParamFlags.WRITABLE),
        'stop-after': (
            bool, '', '', False,
            GObject.ParamFlags.READABLE | GObject.ParamFlags.WRITABLE),
    }

    def __init__(self, window):
        """windows is a QuodLibetWindow"""

        super(PlayerOptions, self).__init__()

        self._repeat = window.repeat
        self._rid = self._repeat.connect(
            "toggled", lambda *x: self.notify("repeat"))

        self._stop_after = window.stop_after
        self._said = self._stop_after.connect(
            "toggled", lambda *x: self.notify("stop-after"))

        def order_changed(*args):
            self.notify("random")
            self.notify("single")

        self._order = window.order
        self._oid = self._order.connect("changed", order_changed)

        window.connect("destroy", self._window_destroy)

    def _window_destroy(self, window):
        self.destroy()

    def destroy(self):
        if self._repeat:
            self._repeat.disconnect(self._rid)
            self._repeat = None
        if self._order:
            self._order.disconnect(self._oid)
            self._order = None
        if self._stop_after:
            self._stop_after.disconnect(self._said)
            self._stop_after = None

    def do_get_property(self, param):
        return getattr(self, param.name.replace("-", "_"))

    def do_set_property(self, param, value):
        setattr(self, param.name.replace("-", "_"), value)

    @property
    def single(self):
        """If only the current song is considered as next track

        This means in case repeat() is False the playlist will end after
        this song finishes. In cas.e repeat() is True the current song will
        be replayed.
        """

        return self._order.get_active_name() == "onesong"

    @single.setter
    def single(self, value):
        if value and not self.single:
            self._order.set_active_by_name("onesong")
        elif not value and self.single:
            self._order.set_active_by_name("inorder")

    @property
    def random(self):
        """If a random based play order is active"""

        return self._order.get_shuffle()

    @random.setter
    def random(self, value):
        self._order.set_shuffle(value)

    @property
    def repeat(self):
        """If the playlist will be restarted if it ended"""

        return self._repeat.get_active()

    @repeat.setter
    def repeat(self, value):
        self._repeat.set_active(value)

    @property
    def stop_after(self):
        """If the player will pause after the current song ends"""

        return self._stop_after.get_active()

    @stop_after.setter
    def stop_after(self, value):
        self._stop_after.set_active(value)


class DockMenu(Gtk.Menu):
    """Menu used for the OSX dock and the tray icon"""

    def __init__(self, app):
        super(DockMenu, self).__init__()

        player = app.player

        play_item = MenuItem(_("_Play"), Icons.MEDIA_PLAYBACK_START)
        play_item.connect("activate", self._on_play, player)
        pause_item = MenuItem(_("P_ause"), Icons.MEDIA_PLAYBACK_PAUSE)
        pause_item.connect("activate", self._on_pause, player)
        self.append(play_item)
        self.append(pause_item)

        previous = MenuItem(_("Pre_vious"), Icons.MEDIA_SKIP_BACKWARD)
        previous.connect('activate', lambda *args: player.previous())
        self.append(previous)

        next_ = MenuItem(_("_Next"), Icons.MEDIA_SKIP_FORWARD)
        next_.connect('activate', lambda *args: player.next())
        self.append(next_)

        browse = qltk.MenuItem(_("_Browse Library"), Icons.EDIT_FIND)
        browse_sub = Gtk.Menu()
        for Kind in browsers.browsers:
            if Kind.is_empty:
                continue
            i = Gtk.MenuItem(label=Kind.accelerated_name, use_underline=True)
            connect_obj(i,
                'activate', LibraryBrowser.open, Kind, app.library, app.player)
            browse_sub.append(i)

        browse.set_submenu(browse_sub)
        self.append(SeparatorMenuItem())
        self.append(browse)

        self.show_all()
        self.hide()

    def _on_play(self, item, player):
        player.paused = False

    def _on_pause(self, item, player):
        player.paused = True


class CurrentColumn(SongListColumn):
    """Displays the current song indicator, either a play or pause icon."""

    def __init__(self):
        super(CurrentColumn, self).__init__("~current")
        self._render = CellRendererPixbuf()
        self.pack_start(self._render, True)
        self._render.set_property('xalign', 0.5)

        self.set_fixed_width(24)
        self.set_expand(False)
        self.set_cell_data_func(self._render, self._cdf)

    def _format_title(self, tag):
        return u""

    def _cdf(self, column, cell, model, iter_, user_data):
        PLAY = "media-playback-start"
        PAUSE = "media-playback-pause"
        STOP = "media-playback-stop"
        ERROR = "dialog-error"

        row = model[iter_]

        if row.path == model.current_path:
            player = app.player
            if player.error:
                name = ERROR
            elif model.sourced:
                name = [PLAY, PAUSE][player.paused]
            else:
                name = STOP
        else:
            name = None

        if not self._needs_update(name):
            return

        if name is not None:
            gicon = Gio.ThemedIcon.new_from_names(
                [name + "-symbolic", name])
        else:
            gicon = None

        cell.set_property('gicon', gicon)


class MainSongList(SongList):
    # The SongList that represents the current playlist.

    _activated = False

    def __init__(self, library, player):
        super(MainSongList, self).__init__(library, player, update=True)
        self.set_first_column_type(CurrentColumn)

        self.connect('row-activated', self.__select_song, player)

        # ugly.. so the main window knows if the next song-started
        # comes from an row-activated or anything else.
        def reset_activated(*args):
            self._activated = False
        connect_after_destroy(player, 'song-started', reset_activated)

        self.connect("orders-changed", self.__orders_changed)

    def __orders_changed(self, *args):
        l = []
        for tag, reverse in self.get_sort_orders():
            l.append("%d%s" % (int(reverse), tag))
        config.setstringlist('memory', 'sortby', l)

    def __select_song(self, widget, indices, col, player):
        self._activated = True
        iter = self.model.get_iter(indices)
        if player.go_to(iter, explicit=True, source=self.model):
            player.paused = False


class SongListScroller(ScrolledWindow):
    def __init__(self, menu):
        super(SongListScroller, self).__init__()
        self.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.set_shadow_type(Gtk.ShadowType.IN)
        self.connect('notify::visible', self.__visibility, menu)

    def __visibility(self, widget, event, menu):
        value = self.get_property('visible')
        menu.set_active(value)
        config.set("memory", "songlist", str(value))


class TopBar(Gtk.Toolbar):
    def __init__(self, parent, player, library):
        super(TopBar, self).__init__()

        # play controls
        control_item = Gtk.ToolItem()
        self.insert(control_item, 0)
        t = PlayControls(player, library.librarian)
        self.volume = t.volume

        # only restore the volume in case it is managed locally, otherwise
        # this could affect the system volume
        if not player.has_external_volume:
            player.volume = config.getfloat("memory", "volume")

        connect_destroy(player, "notify::volume", self._on_volume_changed)
        control_item.add(t)

        self.insert(Gtk.SeparatorToolItem(), 1)

        info_item = Gtk.ToolItem()
        self.insert(info_item, 2)
        info_item.set_expand(True)

        box = Gtk.Box(spacing=6)
        info_item.add(box)
        qltk.add_css(self, "GtkToolbar {padding: 3px;}")

        # song text
        info_pattern_path = os.path.join(quodlibet.get_user_dir(), "songinfo")
        text = SongInfo(library.librarian, player, info_pattern_path)
        box.pack_start(Align(text, border=3), True, True, 0)

        # cover image
        self.image = CoverImage(resize=True)
        connect_destroy(player, 'song-started', self.__new_song)

        # FIXME: makes testing easier
        if app.cover_manager:
            connect_destroy(
                app.cover_manager, 'cover-changed',
                self.__song_art_changed, library)

        box.pack_start(Align(self.image, border=2), False, True, 0)

        # On older Gtk+ (3.4, at least)
        # setting a margin on CoverImage leads to errors and result in the
        # QL window not beeing visible for some reason.
        assert self.image.props.margin == 0

        for child in self.get_children():
            child.show_all()

        context = self.get_style_context()
        context.add_class("primary-toolbar")

    def _on_volume_changed(self, player, *args):
        config.set("memory", "volume", str(player.volume))

    def __new_song(self, player, song):
        self.image.set_song(song)

    def __song_art_changed(self, player, songs, library):
        self.image.refresh()
        refresh_albums = []
        for song in songs:
            # Album browser only (currently):
            album = library.albums.get(song.album_key, None)
            if album:
                album.scan_cover(force=True)
                refresh_albums.append(album)
        if refresh_albums:
            library.albums.refresh(refresh_albums)


class ReapeatButton(Gtk.ToggleButton):

    def __init__(self):
        super(ReapeatButton, self).__init__(
            image=SymbolicIconImage(
                "media-playlist-repeat", Gtk.IconSize.SMALL_TOOLBAR))

        self.set_name("ql-repeat-button")
        qltk.add_css(self, """
            #ql-repeat-button {
                padding: 0px;
            }
        """)
        self.set_size_request(26, 26)

        self.set_tooltip_text(_("Restart the playlist when finished"))

        self.bind_config("settings", "repeat")

    def bind_config(self, section, option):
        self.set_active(config.getboolean(section, option))

        def toggled_cb(*args):
            config.set(section, option, self.get_active())

        self.connect('toggled', toggled_cb)


class StatusBarBox(Gtk.HBox):

    def __init__(self, model, player):
        super(StatusBarBox, self).__init__(spacing=6)

        self.order = order = PlayOrder(model, player)
        self.pack_start(order, False, True, 0)

        self.repeat = repeat = ReapeatButton()
        self.pack_start(repeat, False, True, 0)
        repeat.connect('toggled', self.__repeat, model)
        model.repeat = repeat.get_active()

        self.statusbar = StatusBar(TaskController.default_instance)
        self.pack_start(self.statusbar, True, True, 0)

    def __repeat(self, button, model):
        model.repeat = button.get_active()


class AppMenu(object):
    """Implements a app menu proxy mirroring some main menu items
    to a new menu and exporting it on the session bus.

    Activation gets proxied back to the main menu actions.
    """

    def __init__(self, window, action_group):
        window.realize()

        self._bus = None
        self._ag_id = None
        self._am_id = None
        window.connect("destroy", self._unexport)

        if window.get_realized():
            self._export(window, action_group)
        else:
            self._id = window.connect("realize", self._realized, action_group)

    def _realized(self, window, ag):
        window.disconnect(self._id)
        self._export(window, ag)

    def _export(self, window, gtk_group):
        actions = [
            ["Preferences", "Plugins"],
            ["RefreshLibrary"],
            ["OnlineHelp", "About", "Quit"],
        ]

        # build the new menu
        menu = Gio.Menu()
        action_names = []
        for group in actions:
            section = Gio.Menu()
            for name in group:
                action = gtk_group.get_action(name)
                assert action
                label = action.get_label()
                section.append(label, "app." + name)
                action_names.append(name)
            menu.append_section(None, section)
        menu.freeze()

        # proxy activate to the old group
        def callback(action, data):
            name = action.get_name()
            gtk_action = gtk_group.get_action(name)
            gtk_action.activate()

        action_group = Gio.SimpleActionGroup()
        for name in action_names:
            action = Gio.SimpleAction.new(name, None)
            action_group.insert(action)
            action.connect("activate", callback)

        # export on the bus
        ag_object_path = "/net/sacredchao/QuodLibet"
        am_object_path = "/net/sacredchao/QuodLibet/menus/appmenu"
        app_id = "net.sacredchao.QuodLibet"

        win = window.get_window()
        if not hasattr(win, "set_utf8_property"):
            # not a GdkX11.X11Window
            print_d("Registering appmenu failed: X11 only")
            return

        # FIXME: this doesn't fail on Windows but takes for ages.
        # Maybe remove some deps to make it fail fast?
        # We don't need dbus anyway there.
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            self._ag_id = bus.export_action_group(ag_object_path, action_group)
            self._am_id = bus.export_menu_model(am_object_path, menu)
        except GLib.GError as e:
            print_d("Registering appmenu failed: %r" % e)
            return

        self._bus = bus

        win.set_utf8_property("_GTK_UNIQUE_BUS_NAME", bus.get_unique_name())
        win.set_utf8_property("_GTK_APPLICATION_ID", app_id)
        win.set_utf8_property("_GTK_APPLICATION_OBJECT_PATH", ag_object_path)
        win.set_utf8_property("_GTK_APP_MENU_OBJECT_PATH", am_object_path)

    def _unexport(self, window):
        if self._bus:
            self._bus.unexport_action_group(self._ag_id)
            self._bus.unexport_menu_model(self._am_id)
            self._bus = None


class PlaybackErrorDialog(ErrorMessage):

    def __init__(self, parent, player_error):
        add_full_stop = lambda s: s and (s.rstrip(".") + ".")
        description = add_full_stop(util.escape(player_error.short_desc))
        details = add_full_stop(util.escape(player_error.long_desc or ""))
        if details:
            description += " " + details

        super(PlaybackErrorDialog, self).__init__(
            parent, _("Playback Error"), description)


class ConfirmLibDirSetup(WarningMessage):

    RESPONSE_SETUP = 1

    def __init__(self, parent):
        title = _("Set up library directories?")
        description = _("You don't have any music library set up. "
                        "Would you like to do that now?")

        super(ConfirmLibDirSetup, self).__init__(
            parent, title, description, buttons=Gtk.ButtonsType.NONE)

        self.add_button(_("_Not Now"), Gtk.ResponseType.CANCEL)
        self.add_button(_("_Set Up"), self.RESPONSE_SETUP)
        self.set_default_response(Gtk.ResponseType.CANCEL)


MAIN_MENU = """
<ui>
  <menubar name='Menu'>
    <menu action='Music'>
      <menuitem action='AddFolders' always-show-image='true'/>
      <menuitem action='AddFiles' always-show-image='true'/>
      <menuitem action='AddLocation' always-show-image='true'/>
      <separator/>
      <menu action='BrowseLibrary' always-show-image='true'>
      %(browsers)s
      </menu>
      <separator/>
      <menuitem action='Preferences' always-show-image='true'/>
      <menuitem action='Plugins' always-show-image='true'/>
      <separator/>
      <menuitem action='RefreshLibrary' always-show-image='true'/>
      <separator/>
      <menuitem action='Quit' always-show-image='true'/>
    </menu>
  </menubar>
</ui>
"""


MENU = """
<ui>
  <menubar name='Menu'>
    <menu action='Control'>
      <menuitem action='Previous' always-show-image='true'/>
      <menuitem action='PlayPause' always-show-image='true'/>
      <menuitem action='Next' always-show-image='true'/>
      <menuitem action='StopAfter' always-show-image='true'/>
      <separator/>
      <menuitem action='AddBookmark' always-show-image='true'/>
      <menuitem action='EditBookmarks' always-show-image='true'/>
      <separator/>
      <menuitem action='EditTags' always-show-image='true'/>
      <menuitem action='Information' always-show-image='true'/>
      <separator/>
      <menuitem action='Jump' always-show-image='true'/>
    </menu>
    <menu action='View'>
      <menuitem action='SongList' always-show-image='true'/>
      <menuitem action='Queue' always-show-image='true'/>
      <separator/>
      %(views)s
    </menu>
    <menu action='Help'>
      <menuitem action='OnlineHelp' always-show-image='true'/>
      <menuitem action='Shortcuts' always-show-image='true'/>
      <menuitem action='SearchHelp' always-show-image='true'/>
      <menuitem action='About' always-show-image='true'/>
    </menu>
  </menubar>
</ui>
"""


def BrowseLibrary():
    items = []
    for Kind in browsers.browsers:
        if not Kind.is_empty:
            item = "Browser" + Kind.__name__
            items.append("<menuitem action='%s'/>" % item)
    return "\n".join(items)


def ViewBrowser():
    items = []
    for Kind in browsers.browsers:
        item = "View" + Kind.__name__
        items.append("<menuitem action='%s'/>" % item)
    return "\n".join(items)


DND_URI_LIST, = range(1)


class QuodLibetWindow(Window, PersistentWindowMixin):

    def __init__(self, library, player, headless=False, restore_cb=None):
        super(QuodLibetWindow, self).__init__(dialog=False)
        self.last_dir = get_home_dir()

        self.__destroyed = False
        self.__update_title(player)
        self.set_default_size(550, 450)

        main_box = Gtk.VBox()
        self.add(main_box)

        # create main menubar, load/restore accelerator groups
        self.__library = library
        ui = self.__create_menu(player, library)
        accel_group = ui.get_accel_group()
        self.add_accel_group(accel_group)

        def scroll_and_jump(*args):
            self.__jump_to_current(True, True)

        keyval, mod = Gtk.accelerator_parse("<Primary><shift>J")
        accel_group.connect(keyval, mod, 0, scroll_and_jump)

        # dbus app menu
        # Unity puts the app menu next to our menu bar. Since it only contains
        # menu items also available in the menu bar itself, don't add it.
        if not util.is_unity():
            AppMenu(self, ui.get_action_groups()[0])

        # custom accel map
        accel_fn = os.path.join(quodlibet.get_user_dir(), "accels")
        Gtk.AccelMap.load(accel_fn)
        # save right away so we fill the file with example comments of all
        # accels
        Gtk.AccelMap.save(accel_fn)

        menubar = ui.get_widget("/Menu")

        # Since https://git.gnome.org/browse/gtk+/commit/?id=b44df22895c79
        # toplevel menu items show an empty 16x16 image. While we don't
        # need image items there UIManager creates them by default.
        # Work around by removing the empty GtkImages
        for child in menubar.get_children():
            if isinstance(child, Gtk.ImageMenuItem):
                child.set_image(None)

        main_box.pack_start(menubar, False, True, 0)

        # get the playlist up before other stuff
        self.songlist = MainSongList(library, player)
        self.songlist.show_all()
        self.songlist.connect("key-press-event", self.__songlist_key_press)
        self.songlist.connect_after(
            'drag-data-received', self.__songlist_drag_data_recv)
        self.song_scroller = SongListScroller(
            ui.get_widget("/Menu/View/SongList"))
        self.song_scroller.add(self.songlist)
        self.qexpander = QueueExpander(
            ui.get_widget("/Menu/View/Queue"), library, player)
        self.playlist = PlaylistMux(
            player, self.qexpander.model, self.songlist.model)

        top_bar = TopBar(self, player, library)
        main_box.pack_start(top_bar, False, True, 0)
        self.top_bar = top_bar

        self.__browserbox = Align(bottom=3)
        main_box.pack_start(self.__browserbox, True, True, 0)

        statusbox = StatusBarBox(self.songlist.model, player)
        self.order = statusbox.order
        self.repeat = statusbox.repeat
        self.statusbar = statusbox.statusbar

        main_box.pack_start(
            Align(statusbox, border=3, top=-3, right=3),
            False, True, 0)

        self.songpane = ConfigRVPaned("memory", "queue_position", 0.75)
        self.songpane.pack1(self.song_scroller, resize=True, shrink=False)
        self.songpane.pack2(self.qexpander, resize=True, shrink=False)
        self.__handle_position = self.songpane.get_property("position")

        def songpane_button_press_cb(pane, event):
            """If we start to drag the pane handle while the
            queue expander is unexpanded, expand it and move the handle
            to the bottom, so we can 'drag' the queue out
            """

            if event.window != pane.get_handle_window():
                return False

            if not self.qexpander.get_expanded():
                self.qexpander.set_expanded(True)
                pane.set_relative(1.0)
            return False

        self.songpane.connect("button-press-event", songpane_button_press_cb)

        self.song_scroller.connect('notify::visible', self.__show_or)
        self.qexpander.connect('notify::visible', self.__show_or)
        self.qexpander.connect('notify::expanded', self.__expand_or)
        self.qexpander.connect('draw', self.__qex_size_allocate)
        self.songpane.connect('notify', self.__moved_pane_handle)

        try:
            orders = []
            for e in config.getstringlist('memory', 'sortby', []):
                orders.append((e[1:], int(e[0])))
        except ValueError:
            pass
        else:
            self.songlist.set_sort_orders(orders)

        self.browser = None
        self.ui = ui

        main_box.show_all()

        self._playback_error_dialog = None
        connect_destroy(player, 'song-started', self.__song_started)
        connect_destroy(player, 'paused', self.__update_paused, True)
        connect_destroy(player, 'unpaused', self.__update_paused, False)
        # make sure we redraw all error indicators before opening
        # a dialog (blocking the main loop), so connect after default handlers
        connect_after_destroy(player, 'error', self.__player_error)
        # connect after to let SongTracker update stats
        connect_after_destroy(player, "song-ended", self.__song_ended)

        # set at least the playlist. the song should be restored
        # after the browser emits the song list
        player.setup(self.playlist, None, 0)
        self.__restore_cb = restore_cb
        self.__first_browser_set = True

        restore_browser = not headless
        try:
            self._select_browser(
                self, config.get("memory", "browser"), library, player,
                restore_browser)
        except:
            config.set("memory", "browser", browsers.name(browsers.default))
            config.save()
            raise

        self.showhide_playlist(ui.get_widget("/Menu/View/SongList"))
        self.showhide_playqueue(ui.get_widget("/Menu/View/Queue"))

        self.songlist.connect('popup-menu', self.__songs_popup_menu)
        self.songlist.connect('columns-changed', self.__cols_changed)
        self.songlist.connect('columns-changed', self.__hide_headers)
        self.songlist.info.connect("changed", self.__set_time)

        lib = library.librarian
        connect_destroy(lib, 'changed', self.__song_changed, player)

        targets = [("text/uri-list", Gtk.TargetFlags.OTHER_APP, DND_URI_LIST)]
        targets = [Gtk.TargetEntry.new(*t) for t in targets]

        self.drag_dest_set(
            Gtk.DestDefaults.ALL, targets, Gdk.DragAction.COPY)
        self.connect('drag-data-received', self.__drag_data_received)

        if not headless:
            on_first_map(self, self.__configure_scan_dirs, library)

        if config.getboolean('library', 'refresh_on_start'):
            self.__rebuild(None, False)

        self.connect("key-press-event", self.__key_pressed, player)

        self.connect("destroy", self.__destroy)

        self.enable_window_tracking("quodlibet")

    def set_as_osx_window(self, osx_app):
        assert osx_app

        self._dock_menu = DockMenu(app)
        osx_app.set_dock_menu(self._dock_menu)

        menu = self.ui.get_widget("/Menu")
        menu.hide()
        osx_app.set_menu_bar(menu)
        # Reparent some items to the "Application" menu
        item = self.ui.get_widget('/Menu/Help/About')
        osx_app.insert_app_menu_item(item, 0)
        osx_app.insert_app_menu_item(Gtk.SeparatorMenuItem(), 1)
        item = self.ui.get_widget('/Menu/Music/Preferences')
        osx_app.insert_app_menu_item(item, 2)
        quit_item = self.ui.get_widget('/Menu/Music/Quit')
        quit_item.hide()

    def get_osx_is_persistent(self):
        return True

    def __player_error(self, player, song, player_error):
        # it's modal, but mmkeys etc. can still trigger new ones
        if self._playback_error_dialog:
            self._playback_error_dialog.destroy()
        dialog = PlaybackErrorDialog(self, player_error)
        self._playback_error_dialog = dialog
        dialog.run()
        self._playback_error_dialog = None

    def __configure_scan_dirs(self, library):
        """Get user to configure scan dirs, if none is set up"""
        if not get_scan_dirs() and not len(library) and \
                quodlibet.is_first_session("quodlibet"):
            print_d("Couldn't find any scan dirs")

            resp = ConfirmLibDirSetup(self).run()
            if resp == ConfirmLibDirSetup.RESPONSE_SETUP:
                prefs = PreferencesWindow(self)
                prefs.set_page("library")
                prefs.show()

    def __add_bookmark(self, librarian, player):
        if player.song:
            position = player.get_position() // 1000
            bookmarks = player.song.bookmarks
            new_mark = (position, _("Bookmark Name"))
            if new_mark not in bookmarks:
                bookmarks.append(new_mark)
                player.song.bookmarks = bookmarks

    def __keyboard_shortcuts(self, action):
        show_shortcuts(self)

    def __edit_bookmarks(self, librarian, player):
        if player.song:
            window = EditBookmarks(self, librarian, player)
            window.show()

    def __key_pressed(self, widget, event, player):
        if not player.song:
            return

        def seek_relative(seconds):
            current = player.get_position()
            current += seconds * 1000
            current = min(player.song("~#length") * 1000 - 1, current)
            current = max(0, current)
            player.seek(current)

        if qltk.is_accel(event, "<alt>Right"):
            seek_relative(10)
            return True
        elif qltk.is_accel(event, "<alt>Left"):
            seek_relative(-10)
            return True

    def __destroy(self, *args):
        self.playlist.destroy()

        # The tray icon plugin tries to unhide QL because it gets disabled
        # on Ql exit. The window should stay hidden after destroy.
        self.show = lambda: None
        self.present = self.show

    def __drag_data_received(self, widget, ctx, x, y, sel, tid, etime):
        assert tid == DND_URI_LIST

        uris = sel.get_uris()

        dirs = []
        error = False
        for uri in uris:
            try:
                uri = URI(uri)
            except ValueError:
                continue

            if uri.is_filename:
                loc = os.path.normpath(uri.filename)
                if os.path.isdir(loc):
                    dirs.append(loc)
                else:
                    loc = os.path.realpath(loc)
                    if loc not in self.__library:
                        self.__library.add_filename(loc)
            elif app.player.can_play_uri(uri):
                if uri not in self.__library:
                    self.__library.add([RemoteFile(uri)])
            else:
                error = True
                break
        Gtk.drag_finish(ctx, not error, False, etime)
        if error:
            ErrorMessage(
                self, _("Unable to add songs"),
                _("%s uses an unsupported protocol.") % util.bold(uri)).run()
        else:
            if dirs:
                copool.add(
                    self.__library.scan, dirs,
                    cofuncid="library", funcid="library")

    def __songlist_key_press(self, songlist, event):
        return self.browser.key_pressed(event)

    def __songlist_drag_data_recv(self, view, *args):
        if self.browser.can_reorder:
            songs = view.get_songs()
            self.browser.reordered(songs)
        self.songlist.clear_sort()

    def __show_or(self, widget, prop):
        ssv = self.song_scroller.get_property('visible')
        qxv = self.qexpander.get_property('visible')
        self.songpane.set_property('visible', ssv or qxv)
        if not ssv:
            self.qexpander.set_expanded(True)
        self.__expand_or(widget, prop)

    def __expand_or(self, widget, prop):
        if self.qexpander.get_property('expanded'):
            self.songpane.set_property("position", self.__handle_position)

    def __moved_pane_handle(self, widget, prop):
        if self.qexpander.get_property('expanded'):
            self.__handle_position = self.songpane.get_property("position")

    def __qex_size_allocate(self, event, param=None):
        if not self.qexpander.get_property('expanded'):
            p_max = self.songpane.get_property("max-position")
            p_cur = self.songpane.get_property("position")
            if p_max != p_cur:
                self.songpane.set_property("position", p_max)

    def __create_menu(self, player, library):
        ag = Gtk.ActionGroup.new('QuodLibetWindowActions')

        act = Action(name="Music", label=_("_Music"))
        ag.add_action(act)

        act = Action(name="AddFolders", label=_(u'_Add a Folder…'),
                     icon_name=Icons.LIST_ADD)
        act.connect('activate', self.open_chooser)
        ag.add_action_with_accel(act, "<Primary>O")

        act = Action(name="AddFiles", label=_(u'_Add a File…'),
                     icon_name=Icons.LIST_ADD)
        act.connect('activate', self.open_chooser)
        ag.add_action(act)

        act = Action(name="AddLocation", label=_(u'_Add a Location…'),
                     icon_name=Icons.LIST_ADD)
        act.connect('activate', self.open_location)
        ag.add_action(act)

        act = Action(name="BrowseLibrary", label=_('Open _Browser'),
                     icon_name=Icons.EDIT_FIND)
        ag.add_action(act)

        act = Action(name="Preferences", label=_('_Preferences'),
                     icon_name=Icons.PREFERENCES_SYSTEM)
        act.connect('activate', self.__preferences)
        ag.add_action(act)

        act = Action(name="Plugins", label=_('_Plugins'),
                     icon_name=Icons.SYSTEM_RUN)
        act.connect('activate', self.__plugins)
        ag.add_action(act)

        act = Action(name="Quit", label=_('_Quit'),
                     icon_name=Icons.APPLICATION_EXIT)
        act.connect('activate', lambda *x: self.destroy())
        ag.add_action_with_accel(act, "<Primary>Q")

        act = Action(name="Control", label=_('_Control'))
        ag.add_action(act)

        act = Action(name="EditTags", label=_('Edit _Tags'),
                     icon_name=Icons.DOCUMENT_PROPERTIES)
        act.connect('activate', self.__current_song_prop)
        ag.add_action(act)

        act = Action(name="Information", label=_('_Information'),
                     icon_name=Icons.DIALOG_INFORMATION)
        act.connect('activate', self.__current_song_info)
        ag.add_action(act)

        act = Action(name="Jump", label=_('_Jump to Playing Song'),
                     icon_name=Icons.GO_JUMP)
        act.connect('activate', self.__jump_to_current)
        ag.add_action_with_accel(act, "<Primary>J")

        act = Action(name="View", label=_('_View'))
        ag.add_action(act)

        act = Action(name="Help", label=_('_Help'))
        ag.add_action(act)

        act = Action(name="Previous", label=_('Pre_vious'),
                     icon_name=Icons.MEDIA_SKIP_BACKWARD)
        act.connect('activate', self.__previous_song)
        ag.add_action_with_accel(act, "<Primary>comma")

        act = Action(name="PlayPause", label=_('_Play'),
                     icon_name=Icons.MEDIA_PLAYBACK_START)
        act.connect('activate', self.__play_pause)
        ag.add_action_with_accel(act, "<Primary>space")

        act = Action(name="Next", label=_('_Next'),
                     icon_name=Icons.MEDIA_SKIP_FORWARD)
        act.connect('activate', self.__next_song)
        ag.add_action_with_accel(act, "<Primary>period")

        act = ToggleAction(name="StopAfter", label=_("Stop After This Song"))
        ag.add_action_with_accel(act, "<shift>space")

        # access point for the tray icon
        self.stop_after = act

        act = Action(name="AddBookmark", label=_("Add Bookmark"),
                     icon_name=Icons.LIST_ADD)
        connect_obj(act, 'activate', self.__add_bookmark,
                           library.librarian, player)
        ag.add_action_with_accel(act, "<Primary>D")

        act = Action(name="EditBookmarks", label=_(u"Edit Bookmarks…"))
        connect_obj(act, 'activate', self.__edit_bookmarks,
                           library.librarian, player)
        ag.add_action_with_accel(act, "<Primary>B")

        act = Action(name="Shortcuts", label=_("_Keyboard Shortcuts"))
        act.connect('activate', self.__keyboard_shortcuts)
        ag.add_action_with_accel(act, "<Primary>F1")

        act = Action(name="About", label=_("_About"),
                     icon_name=Icons.HELP_ABOUT)
        act.connect('activate', self.__show_about)
        ag.add_action_with_accel(act, None)

        act = Action(name="OnlineHelp", label=_("Online Help"),
                     icon_name=Icons.HELP_BROWSER)

        def website_handler(*args):
            util.website(const.ONLINE_HELP)

        act.connect('activate', website_handler)
        ag.add_action_with_accel(act, "F1")

        act = Action(name="SearchHelp", label=_("Search Help"))

        def search_help_handler(*args):
            util.website(const.SEARCH_HELP)

        act.connect('activate', search_help_handler)
        ag.add_action_with_accel(act, None)

        act = Action(
            name="RefreshLibrary", label=_("_Scan Library"),
            icon_name=Icons.VIEW_REFRESH)
        act.connect('activate', self.__rebuild, False)
        ag.add_action(act)

        act = ToggleAction(name="SongList", label=_("Song _List"))
        act.set_active(config.getboolean("memory", "songlist"))
        act.connect('activate', self.showhide_playlist)
        ag.add_action(act)

        act = ToggleAction(name="Queue", label=_("_Queue"))
        act.set_active(config.getboolean("memory", "queue"))
        act.connect('activate', self.showhide_playqueue)
        ag.add_action(act)

        current = config.get("memory", "browser")
        try:
            browsers.get(current)
        except ValueError:
            current = browsers.name(browsers.default)

        first_action = None
        for Kind in browsers.browsers:
            name = browsers.name(Kind)
            index = browsers.index(name)
            action_name = "View" + Kind.__name__
            label = Kind.accelerated_name
            act = RadioAction(name=action_name, label=Kind.accelerated_name,
                              value=index)
            act.join_group(first_action)
            first_action = first_action or act
            if name == current:
                act.set_active(True)
            ag.add_action_with_accel(act, None)
        assert first_action
        self._browser_action = first_action

        def action_callback(view_action, current_action):
            current = browsers.name(
                browsers.get(current_action.get_current_value()))
            self._select_browser(view_action, current, library, player)

        first_action.connect("changed", action_callback)

        for Kind in browsers.browsers:
            if Kind.is_empty:
                continue
            action = "Browser" + Kind.__name__
            label = Kind.accelerated_name
            act = Action(name=action, label=label)

            def browser_activate(action, Kind):
                LibraryBrowser.open(Kind, library, player)

            act.connect('activate', browser_activate, Kind)
            ag.add_action_with_accel(act, None)

        ui = Gtk.UIManager()
        ui.insert_action_group(ag, -1)

        ui.add_ui_from_string(
            MAIN_MENU % {"browsers": BrowseLibrary()})
        self._filter_menu = FilterMenu(library, player, ui)

        menustr = MENU % {
            "views": ViewBrowser(),
        }
        ui.add_ui_from_string(menustr)

        # Cute. So. UIManager lets you attach tooltips, but when they're
        # for menu items, they just get ignored. So here I get to actually
        # attach them.
        ui.get_widget("/Menu/Music/RefreshLibrary").set_tooltip_text(
                _("Check for changes in your library"))

        return ui

    def __show_about(self, *args):
        about = AboutDialog(self, app)
        about.run()
        about.destroy()

    def select_browser(self, browser_key, library, player):
        """Given a browser name (see browsers.get()) changes the current
        browser.

        Returns True if the passed browser ID is known and the change
        was initiated.
        """

        try:
            Browser = browsers.get(browser_key)
        except ValueError:
            return False

        action_name = "View%s" % Browser.__name__
        for i, action in enumerate(self._browser_action.get_group()):
            if action.get_name() == action_name:
                action.set_active(True)
                return True
        return False

    def _select_browser(self, activator, current, library, player,
                       restore=False):

        Browser = browsers.get(current)

        config.set("memory", "browser", current)
        if self.browser:
            if not (self.browser.uses_main_library and
                    Browser.uses_main_library):
                self.songlist.clear()
            container = self.browser.__container
            self.browser.unpack(container, self.songpane)
            if self.browser.accelerators:
                self.remove_accel_group(self.browser.accelerators)
            container.destroy()
            self.browser.destroy()
        self.browser = Browser(library)
        self.browser.connect('songs-selected',
            self.__browser_cb, library, player)
        self.browser.connect('songs-activated', self.__browser_activate)
        if restore:
            self.browser.restore()
            self.browser.activate()
        self.browser.finalize(restore)
        if self.browser.can_reorder:
            self.songlist.enable_drop()
        elif self.browser.dropped:
            self.songlist.enable_drop(False)
        else:
            self.songlist.disable_drop()
        if self.browser.accelerators:
            self.add_accel_group(self.browser.accelerators)

        container = self.browser.__container = self.browser.pack(self.songpane)

        player.replaygain_profiles[1] = self.browser.replaygain_profiles
        player.reset_replaygain()
        self.__browserbox.add(container)
        container.show()
        self._filter_menu.set_browser(self.browser)
        self.__hide_headers()
        self.__refresh_size()

    def __update_paused(self, player, paused):
        menu = self.ui.get_widget("/Menu/Control/PlayPause")
        image = menu.get_image()

        if paused:
            label, icon = _("_Play"), Icons.MEDIA_PLAYBACK_START
        else:
            label, icon = _("P_ause"), Icons.MEDIA_PLAYBACK_PAUSE

        menu.set_label(label)
        image.set_from_icon_name(icon, Gtk.IconSize.MENU)

    def __song_ended(self, player, song, stopped):
        # Check if the song should be removed, based on the
        # active filter of the current browser.
        active_filter = self.browser.active_filter
        if song and active_filter and not active_filter(song):
            iter_ = self.songlist.model.find(song)
            if iter_:
                self.songlist.remove_iters([iter_])

        if self.stop_after.get_active():
            player.paused = True
            self.stop_after.set_active(False)

    def __song_changed(self, library, songs, player):
        if player.info in songs:
            self.__update_title(player)

    def __update_title(self, player):
        song = player.info
        title = "Quod Libet"
        if song:
            title = song.comma("~title~version~~people") + " - " + title
        self.set_title(title)

    def __song_started(self, player, song):
        self.__update_title(player)

        for wid in ["Jump", "Next", "EditTags", "Information",
                    "EditBookmarks", "AddBookmark", "StopAfter"]:
            self.ui.get_widget(
                '/Menu/Control/' + wid).set_sensitive(bool(song))

        # don't jump on stream changes (player.info != player.song)
        if song and player.song is song and not self.songlist._activated and \
            config.getboolean("settings", "jump") and self.songlist.sourced:
            self.__jump_to_current(False)

    def __refresh_size(self):
        ssv = self.song_scroller.get_property('visible')
        qex = self.qexpander.get_property('visible')

        if ssv or qex:
            return

        # Handle more later if needed..
        if not isinstance(self.browser, Gtk.Box):
            return

        # If a child expands the browser will take the new space
        for child in self.browser.get_children():
            if self.browser.query_child_packing(child)[0]:
                break
        else:
            # no expanding child, make the window smaller instead
            width, height = self.get_size()
            height = self.size_request().height
            self.resize(width, height)

    def showhide_playlist(self, toggle):
        self.song_scroller.set_property('visible', toggle.get_active())
        self.__refresh_size()

    def showhide_playqueue(self, toggle):
        self.qexpander.set_property('visible', toggle.get_active())
        self.__refresh_size()

    def __play_pause(self, *args):
        if app.player.song is None:
            app.player.reset()
        else:
            app.player.paused ^= True

    def __jump_to_current(self, explicit, force_scroll=False):
        """Select/scroll to the current playing song in the playlist.
        If it can't be found tell the browser to properly fill the playlist
        with an appropriate selection containing the song.

        explicit means that the jump request comes from the user and not
        from an event like song-started.

        force_scroll will ask the browser to refill the playlist in any case.
        """

        def idle_jump_to(song, select):
            ok = self.songlist.jump_to_song(song, select=select)
            if ok:
                self.songlist.grab_focus()
            return False

        song = app.player.song

        # We are not playing a song
        if song is None:
            return

        if not force_scroll:
            ok = self.songlist.jump_to_song(song, select=explicit)
        else:
            assert explicit
            ok = False

        if ok:
            self.songlist.grab_focus()
        elif explicit:
            # if we can't find it and the user requested it, try harder
            self.browser.scroll(song)
            # We need to wait until the browser has finished
            # scrolling/filling and the songlist is ready.
            # Not perfect, but works for now.
            GLib.idle_add(
                idle_jump_to, song, explicit, priority=GLib.PRIORITY_LOW)

    def __next_song(self, *args):
        app.player.next()

    def __previous_song(self, *args):
        app.player.previous()

    def __rebuild(self, activator, force):
        scan_library(self.__library, force)

    # Set up the preferences window.
    def __preferences(self, activator):
        window = PreferencesWindow(self)
        window.show()

    def __plugins(self, activator):
        window = PluginWindow(self)
        window.show()

    def open_location(self, action):
        name = GetStringDialog(self, _("Add a Location"),
            _("Enter the location of an audio file:"),
            button_label=_("_Add"), button_icon=Icons.LIST_ADD).run()
        if name:
            if not util.uri_is_valid(name):
                ErrorMessage(
                    self, _("Unable to add location"),
                    _("%s is not a valid location.") % (
                    util.bold(util.escape(name)))).run()
            elif not app.player.can_play_uri(name):
                ErrorMessage(
                    self, _("Unable to add location"),
                    _("%s uses an unsupported protocol.") % (
                    util.bold(util.escape(name)))).run()
            else:
                if name not in self.__library:
                    self.__library.add([RemoteFile(name)])

    def open_chooser(self, action):
        last_dir = self.last_dir
        if not os.path.exists(last_dir):
            last_dir = get_home_dir()

        class MusicFolderChooser(FolderChooser):
            def __init__(self, parent, init_dir):
                super(MusicFolderChooser, self).__init__(
                    parent, _("Add Music"), init_dir)

                cb = Gtk.CheckButton(_("Watch this folder for new songs"))
                # enable if no folders are being watched
                cb.set_active(not get_scan_dirs())
                cb.show()
                self.set_extra_widget(cb)

            def run(self):
                fns = super(MusicFolderChooser, self).run()
                cb = self.get_extra_widget()
                return fns, cb.get_active()

        class MusicFileChooser(FileChooser):
            def __init__(self, parent, init_dir):
                super(MusicFileChooser, self).__init__(
                    parent, _("Add Music"), formats.filter, init_dir)

        if action.get_name() == "AddFolders":
            dialog = MusicFolderChooser(self, last_dir)
            fns, do_watch = dialog.run()
            dialog.destroy()
            if fns:
                fns = map(glib2fsnative, fns)
                # scan them
                self.last_dir = fns[0]
                copool.add(self.__library.scan, fns, cofuncid="library",
                           funcid="library")

                # add them as library scan directory
                if do_watch:
                    dirs = get_scan_dirs()
                    for fn in fns:
                        if fn not in dirs:
                            dirs.append(fn)
                    set_scan_dirs(dirs)
        else:
            dialog = MusicFileChooser(self, last_dir)
            fns = dialog.run()
            dialog.destroy()
            if fns:
                fns = map(glib2fsnative, fns)
                self.last_dir = os.path.dirname(fns[0])
                for filename in map(os.path.realpath, fns):
                    self.__library.add_filename(filename)

    def __songs_popup_menu(self, songlist):
        path, col = songlist.get_cursor()
        header = col.header_name
        menu = self.songlist.Menu(header, self.browser, self.__library)
        if menu is not None:
            return self.songlist.popup_menu(menu, 0,
                    Gtk.get_current_event_time())

    def __current_song_prop(self, *args):
        song = app.player.song
        if song:
            librarian = self.__library.librarian
            window = SongProperties(librarian, [song], parent=self)
            window.show()

    def __current_song_info(self, *args):
        song = app.player.song
        if song:
            librarian = self.__library.librarian
            window = Information(librarian, [song], self)
            window.show()

    def __browser_activate(self, browser):
        app.player.reset()

    def __browser_cb(self, browser, songs, sorted, library, player):
        if browser.background:
            bg = background_filter()
            if bg:
                songs = filter(bg, songs)
        self.songlist.set_songs(songs, sorted)

        # After the first time the browser activates, which should always
        # happen if we start up and restore, restore the playing song.
        # Because the browser has send us songs we can be sure it has
        # registered all its libraries.
        if self.__first_browser_set:
            self.__first_browser_set = False

            song = library.librarian.get(config.get("memory", "song"))
            seek_pos = config.getfloat("memory", "seek", 0)
            config.set("memory", "seek", 0)
            if song is not None:
                player.setup(self.playlist, song, seek_pos)

            if self.__restore_cb:
                self.__restore_cb()
                self.__restore_cb = None

    def __hide_headers(self, activator=None):
        for column in self.songlist.get_columns():
            if self.browser.headers is None:
                column.set_visible(True)
            else:
                for tag in util.tagsplit(column.header_name):
                    if tag in self.browser.headers:
                        column.set_visible(True)
                        break
                else:
                    column.set_visible(False)

    def __cols_changed(self, songlist):
        headers = [col.header_name for col in songlist.get_columns()]
        try:
            headers.remove('~current')
        except ValueError:
            pass
        if len(headers) == len(get_columns()):
            # Not an addition or removal (handled separately)
            set_columns(headers)
            SongList.headers = headers

    def __make_query(self, query):
        if self.browser.can_filter_text():
            self.browser.filter_text(query.encode('utf-8'))
            self.browser.activate()

    def __set_time(self, info, songs):
        i = len(songs)
        length = sum(song.get("~#length", 0) for song in songs)
        t = self.browser.statusbar(i) % {
            'count': i, 'time': util.format_time_long(length)}
        self.statusbar.set_default_text(t)
