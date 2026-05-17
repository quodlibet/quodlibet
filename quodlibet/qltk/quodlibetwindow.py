# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2012 Christoph Reiter
#           2012-2023 Nick Boultbee
#           2017 Uriel Zajaczkovski
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

from gi.repository import Gtk, Gdk, GLib, Gio, GObject
from quodlibet.fsn import uri2fsn, fsnative, path2fsn

import quodlibet

from quodlibet import browsers
from quodlibet import config
from quodlibet import const
from quodlibet import formats
from quodlibet import qltk
from quodlibet import util
from quodlibet import app
from quodlibet import ngettext
from quodlibet import _
from quodlibet.qltk.paned import ConfigRHPaned

from quodlibet.qltk.appwindow import AppWindow
from quodlibet.update import UpdateDialog
from quodlibet.formats.remote import RemoteFile
from quodlibet.qltk.browser import LibraryBrowser, FilterMenu
from quodlibet.qltk.chooser import choose_folders, choose_files, create_chooser_filter
from quodlibet.qltk.controls import PlayControls
from quodlibet.qltk.cover import CoverImage
from quodlibet.qltk.getstring import GetStringDialog
from quodlibet.qltk.bookmarks import EditBookmarks
from quodlibet.qltk.shortcuts import show_shortcuts
from quodlibet.qltk.info import SongInfo
from quodlibet.qltk.information import Information
from quodlibet.qltk.msg import ErrorMessage, WarningMessage
from quodlibet.qltk.notif import StatusBar, TaskController
from quodlibet.qltk.playorder import (
    PlayOrderWidget,
    RepeatSongForever,
    RepeatListForever,
)
from quodlibet.qltk.pluginwin import PluginWindow
from quodlibet.qltk.properties import SongProperties
from quodlibet.qltk.prefs import PreferencesWindow
from quodlibet.qltk.queue import QueueExpander
from quodlibet.qltk.songlist import SongList, get_columns, set_columns
from quodlibet.qltk.songmodel import PlaylistMux
from quodlibet.qltk.x import RVPaned, Align, ScrolledWindow
from quodlibet.qltk.x import HighlightToggleButton
from quodlibet.qltk.x import MenuItem, SeparatorMenuItem
from quodlibet.qltk import Icons
from quodlibet.qltk.about import AboutDialog
from quodlibet.util import copool, connect_destroy, connect_after_destroy
from quodlibet.util.library import get_scan_dirs
from quodlibet.util import connect_obj, print_d
from quodlibet.util.library import background_filter, scan_library
from quodlibet.util.path import uri_is_valid
from quodlibet.qltk.window import PersistentWindowMixin, Window, on_first_map
from quodlibet.qltk.songlistcolumns import CurrentColumn


class PlayerOptions(GObject.Object):
    """Provides a simplified interface for playback options.

    This currently provides a limited view on the play order state which is
    useful for external interfaces (mpd, mpris, etc.) and for reducing
    the dependency on the state holding widgets in the main window.

    Usable as long as the main window is not destroyed, or until `destroy()`
    is called.
    """

    __gproperties__ = {
        "shuffle": (
            bool,
            "",
            "",
            False,
            GObject.ParamFlags.READABLE | GObject.ParamFlags.WRITABLE,
        ),
        "repeat": (
            bool,
            "",
            "",
            False,
            GObject.ParamFlags.READABLE | GObject.ParamFlags.WRITABLE,
        ),
        "single": (
            bool,
            "",
            "",
            False,
            GObject.ParamFlags.READABLE | GObject.ParamFlags.WRITABLE,
        ),
        "stop-after": (
            bool,
            "",
            "",
            False,
            GObject.ParamFlags.READABLE | GObject.ParamFlags.WRITABLE,
        ),
    }

    def __init__(self, window):
        """`window` is a QuodLibetWindow"""

        super().__init__()

        self._stop_after = window.stop_after
        self._said = self._stop_after.connect(
            "notify::state", lambda *x: self.notify("stop-after")
        )

        def order_changed(*args):
            self.notify("shuffle")
            self.notify("single")

        self._order_widget = window.order
        self._oid = self._order_widget.connect("changed", order_changed)

        window.connect("destroy", self._window_destroy)

    def _window_destroy(self, window):
        # GTK4: destroy() removed - self cleaned up automatically
        pass

    def destroy(self):
        if self._order_widget:
            self._order_widget.disconnect(self._oid)
            self._order_widget = None
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

        When `repeat` is False the playlist will end after this song finishes.
        When `repeat` is True the current song will be replayed.
        """

        return (
            self._order_widget
            and self._order_widget.repeated
            and self._order_widget.repeater is RepeatSongForever
        )

    @single.setter
    def single(self, value):
        if value:
            self.repeat = True
            self._order_widget.repeater = RepeatSongForever
        else:
            self.repeat = False
            self._order_widget.repeater = RepeatListForever

    @property
    def shuffle(self):
        """If a shuffle-like (reordering) play order is active"""

        return self._order_widget.shuffled

    @shuffle.setter
    def shuffle(self, value):
        self._order_widget.shuffled = value

    @property
    def repeat(self):
        """If the player is in some kind of repeat mode"""

        return self._order_widget.repeated

    @repeat.setter
    def repeat(self, value):
        print_d(f"setting repeated to {value}")
        self._order_widget.repeated = value

    @property
    def stop_after(self):
        """If the player will pause after the current song ends"""

        return self._stop_after.get_state().get_boolean()

    @stop_after.setter
    def stop_after(self, value):
        self._stop_after.set_state(GLib.Variant.new_boolean(value))


class DockMenu(Gtk.PopoverMenu):
    """Menu used for the OSX dock and the tray icon"""

    def __init__(self, app):
        super().__init__()

        player = app.player

        play_item = MenuItem(_("_Play"), Icons.MEDIA_PLAYBACK_START)
        play_item.connect("activate", self._on_play, player)
        pause_item = MenuItem(_("P_ause"), Icons.MEDIA_PLAYBACK_PAUSE)
        pause_item.connect("activate", self._on_pause, player)
        self.append(play_item)
        self.append(pause_item)

        previous = MenuItem(_("Pre_vious"), Icons.MEDIA_SKIP_BACKWARD)
        previous.connect("activate", lambda *args: player.previous())
        self.append(previous)

        next_ = MenuItem(_("_Next"), Icons.MEDIA_SKIP_FORWARD)
        next_.connect("activate", lambda *args: player.next())
        self.append(next_)

        browse = qltk.MenuItem(_("_Browse Library"), Icons.EDIT_FIND)
        browse_sub = Gtk.PopoverMenu()
        for Kind in browsers.browsers:
            i = Gtk.MenuItem(label=Kind.accelerated_name, use_underline=True)
            connect_obj(
                i, "activate", LibraryBrowser.open, Kind, app.library, app.player
            )
            browse_sub.append(i)

        browse.set_submenu(browse_sub)
        self.append(SeparatorMenuItem())
        self.append(browse)

        self.hide()

    def _on_play(self, item, player):
        player.paused = False

    def _on_pause(self, item, player):
        player.paused = True


class MainSongList(SongList):
    """SongList for the main browser's displayed songs."""

    _activated = False

    def __init__(self, library, player):
        super().__init__(library, player, update=True)
        self.set_first_column_type(CurrentColumn)

        self.connect("row-activated", self.__select_song, player)

        # ugly.. so the main window knows if the next song-started
        # comes from an row-activated or anything else.
        def reset_activated(*args):
            self._activated = False

        connect_after_destroy(player, "song-started", reset_activated)

        self.connect("orders-changed", self.__orders_changed)

    def __orders_changed(self, *args):
        l = []
        for tag, reverse in self.get_sort_orders():
            l.append("%d%s" % (int(reverse), tag))
        config.setstringlist("memory", "sortby", l)

    def __select_song(self, widget, indices, col, player):
        self._activated = True
        iter = self.model.get_iter(indices)
        if player.go_to(iter, explicit=True, source=self.model):
            player.paused = False


class TopBar(Gtk.Box):
    def __init__(self, parent, player, library):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.add_css_class("toolbar")

        # play controls
        t = PlayControls(player, library.librarian)
        self.volume = t.volume

        # only restore the volume in case it is managed locally, otherwise
        # this could affect the system volume
        if not player.has_external_volume:
            player.volume = config.getfloat("memory", "volume")

        connect_destroy(player, "notify::volume", self._on_volume_changed)
        self.append(t)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        self.append(spacer)

        info_item = Gtk.Box()
        self.append(info_item)

        box = Gtk.Box(spacing=6)
        info_item.append(box)
        qltk.add_css(self, "GtkToolbar {padding: 3px;}")

        self._pattern_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)

        # song text
        info_pattern_path = os.path.join(quodlibet.get_user_dir(), "songinfo")
        text = SongInfo(library.librarian, player, info_pattern_path)
        self._pattern_box.append(text)
        box.append(self._pattern_box)

        # cover image
        self.image = CoverImage(resize=True)
        connect_destroy(player, "song-started", self.__new_song)

        # FIXME: makes testing easier
        if app.cover_manager:
            connect_destroy(
                app.cover_manager, "cover-changed", self.__song_art_changed, library
            )

        box.append(Align(self.image, top=3, right=3))

        context = self.get_style_context()
        context.add_class("primary-toolbar")

    def set_seekbar_widget(self, widget):
        from quodlibet.qltk import get_children

        children = get_children(self._pattern_box)
        if len(children) > 1:
            self._pattern_box.remove(children[-1])

        if widget:
            self._pattern_box.append(widget)

    def _on_volume_changed(self, player, *args):
        config.set("memory", "volume", str(player.volume))

    def __new_song(self, player, song):
        self.image.set_song(song)

    def __song_art_changed(self, player, songs, library):
        self.image.refresh()


class QueueButton(HighlightToggleButton):
    def __init__(self):
        # XXX: view-list isn't part of the fdo spec, so fall back t justify..
        gicon = Gio.ThemedIcon.new_from_names(
            [
                "view-list-symbolic",
                "format-justify-fill-symbolic",
                "view-list",
                "format-justify",
            ]
        )
        # GTK4: Image.new_from_gicon() only takes gicon, not size
        image = Gtk.Image.new_from_gicon(gicon)

        super().__init__(image=image)

        self.set_name("ql-queue-button")
        qltk.add_css(
            self,
            """
            #ql-queue-button {
                padding: 0px;
            }
        """,
        )
        self.set_size_request(26, 26)

        self.set_tooltip_text(_("Toggle queue visibility"))


class StatusBarBox(Gtk.Box):
    def __init__(self, play_order, queue):
        super().__init__(spacing=6)
        self.append(play_order)
        self.statusbar = StatusBar(TaskController.default_instance)
        self.append(self.statusbar)
        queue_button = QueueButton()
        queue_button.bind_property(
            "active", queue, "visible", GObject.BindingFlags.BIDIRECTIONAL
        )
        queue_button.props.active = queue.props.visible

        self.append(queue_button)


class PlaybackErrorDialog(ErrorMessage):
    def __init__(self, parent, player_error):
        def add_full_stop(s):
            return s and s.rstrip(".") + "."

        description = add_full_stop(util.escape(player_error.short_desc))
        details = add_full_stop(util.escape(player_error.long_desc or ""))
        if details:
            description += " " + details

        super().__init__(parent, _("Playback Error"), description)


class ConfirmLibDirSetup(WarningMessage):
    RESPONSE_SETUP = 1

    def __init__(self, parent):
        title = _("Set up library directories?")
        description = _(
            "You don't have any music library set up. Would you like to do that now?"
        )

        super().__init__(parent, title, description, buttons=Gtk.ButtonsType.NONE)

        self.add_button(_("_Not Now"), Gtk.ResponseType.CANCEL)
        self.add_button(_("_Set Up"), self.RESPONSE_SETUP)
        self.set_default_response(Gtk.ResponseType.CANCEL)


def _browser_kinds(external):
    return [k for k in browsers.browsers if k.uses_main_library ^ external]


class SongListPaned(RVPaned):
    def __init__(self, song_scroller, qexpander):
        super().__init__()

        # GTK4: pack1/pack2() → set_start_child/set_end_child() + set_resize/shrink
        self.set_start_child(song_scroller)
        self.set_resize_start_child(True)
        self.set_shrink_start_child(False)
        self.set_end_child(qexpander)
        self.set_resize_end_child(True)
        self.set_shrink_end_child(False)

        self.set_relative(config.getfloat("memory", "queue_position", 0.75))
        self.connect("notify::position", self._changed, "memory", "queue_position")

        self._handle_position = self.get_relative()
        qexpander.connect("notify::visible", self._expand_or)
        qexpander.connect("notify::expanded", self._expand_or)
        qexpander.connect("draw", self._check_minimize)

        self.connect("button-press-event", self._on_button_press)
        self.connect("notify", self._moved_pane_handle)

    @property
    def _expander(self):
        return self.get_end_child()

    def _on_button_press(self, pane, event):
        # If we start to drag the pane handle while the
        # queue expander is unexpanded, expand it and move the handle
        # to the bottom, so we can 'drag' the queue out

        if event.window != pane.get_handle_window():
            return False

        if not self._expander.get_expanded():
            self._expander.set_expanded(True)
            pane.set_relative(1.0)
        return False

    def _expand_or(self, widget, prop):
        if self._expander.get_property("expanded"):
            self.set_relative(self._handle_position)

    def _moved_pane_handle(self, widget, prop):
        if self._expander.get_property("expanded"):
            self._handle_position = self.get_relative()

    def _check_minimize(self, *args):
        if not self._expander.get_property("expanded"):
            p_max = self.get_property("max-position")
            p_cur = self.get_property("position")
            if p_max != p_cur:
                self.set_property("position", p_max)

    def _changed(self, widget, event, section, option):
        if self._expander.get_expanded() and self.get_property("position-set"):
            config.set(section, option, str(self.get_relative()))


class QuodLibetWindow(Window, PersistentWindowMixin, AppWindow):
    def __init__(self, library, player, headless=False, restore_cb=None):
        super().__init__(dialog=False)

        self.__destroyed = False
        self.__update_title(player)
        self.set_default_size(600, 480)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(main_box)
        self.side_book = qltk.Notebook()

        # get the playlist up before other stuff
        self.songlist = MainSongList(library, player)
        key_controller = Gtk.EventControllerKey()
        self.songlist.add_controller(key_controller)
        key_controller.connect("key-pressed", self.__songlist_key_press)
        self.song_scroller = ScrolledWindow()
        self.song_scroller.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
        )
        self.song_scroller.set_property("has-frame", True)
        self.song_scroller.set_child(self.songlist)
        self.songlist.show()
        self.song_scroller.show()

        self.qexpander = QueueExpander(library, player)
        self.qexpander.set_visible(config.getboolean("memory", "queue"))

        def on_queue_visible(qex, param):
            config.set("memory", "queue", str(qex.get_visible()))

        self.qexpander.connect("notify::visible", on_queue_visible)

        self.playlist = PlaylistMux(player, self.qexpander.model, self.songlist.model)

        self.__player = player
        self.__library = library
        action_group, menu_model = self.__create_menu(player, library)
        self.insert_action_group("win", action_group)
        self._action_group = action_group
        menubar = Gtk.PopoverMenuBar.new_from_model(menu_model)
        main_box.append(menubar)
        self.__wire_shortcuts(player)

        top_bar = TopBar(self, player, library)
        main_box.append(top_bar)
        self.top_bar = top_bar

        self.__browserbox = Align(top=3, bottom=3)
        self.__browserbox.set_vexpand(True)
        self.__paned = paned = ConfigRHPaned("memory", "sidebar_pos", 0.25)
        paned.set_vexpand(True)
        paned.set_start_child(self.__browserbox)
        paned.set_resize_start_child(True)
        # We'll set_end_child when necessary (when the first sidebar plugin is set up)

        main_box.append(paned)

        play_order = PlayOrderWidget(self.songlist.model, player)
        statusbox = StatusBarBox(play_order, self.qexpander)
        self.order = play_order
        self.statusbar = statusbox.statusbar

        align = Align(statusbox, top=1, bottom=4, left=6, right=6)
        main_box.append(align)

        self.songpane = SongListPaned(self.song_scroller, self.qexpander)
        self.songpane.show()

        try:
            orders = []
            for e in config.getstringlist("memory", "sortby", []):
                orders.append((e[1:], int(e[0])))
        except ValueError:
            pass
        else:
            self.songlist.set_sort_orders(orders)

        self.browser = None

        self._playback_error_dialog = None
        connect_destroy(player, "song-started", self.__song_started)
        connect_destroy(player, "paused", self.__update_paused, True)
        connect_destroy(player, "unpaused", self.__update_paused, False)
        # make sure we redraw all error indicators before opening
        # a dialog (blocking the main loop), so connect after default handlers
        connect_after_destroy(player, "error", self.__player_error)
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
                self, config.get("memory", "browser"), library, player, restore_browser
            )
        except Exception:
            config.set("memory", "browser", browsers.name(browsers.default))
            config.save()
            raise

        self.songlist.connect("popup-menu", self.__songs_popup_menu)
        self.songlist.connect("columns-changed", self.__cols_changed)
        self.songlist.connect("columns-changed", self.__hide_headers)
        self.songlist.info.connect("changed", self.__set_totals)

        lib = library.librarian
        connect_destroy(lib, "changed", self.__song_changed, player)

        drop_target = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        drop_target.connect("drop", self.__on_drop_files)
        self.add_controller(drop_target)

        uri_drop = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.COPY)
        uri_drop.connect("drop", self.__on_drop_uri)
        self.add_controller(uri_drop)

        if not headless:
            on_first_map(self, self.__configure_scan_dirs, library)

        if config.getboolean("library", "refresh_on_start"):
            self.__rebuild(None, False)

        self.connect("key-press-event", self.__key_pressed, player)

        self.connect("destroy", self.__destroy)

        self.enable_window_tracking("quodlibet")

    def hide_side_book(self):
        self.side_book.hide()

    def add_sidebar(self, box, name):
        vbox = Gtk.Box()
        vbox.append(box)
        vbox.show()
        if self.side_book_empty:
            self.add_sidebar_to_layout(self.side_book)
        self.side_book.append_page(vbox, label=name)
        self.side_book.set_tab_detachable(vbox, False)
        return vbox

    def remove_sidebar(self, widget):
        self.side_book.remove_page(self.side_book.page_num(widget))
        if self.side_book_empty:
            print_d("Hiding sidebar")
            self.__paned.remove(qltk.get_children(self.__paned)[1])

    def add_sidebar_to_layout(self, widget):
        print_d("Recreating sidebar")
        align = Align(widget, top=6, bottom=3)
        self.__paned.set_end_child(align)
        self.__paned.set_resize_end_child(True)
        self.__paned.set_shrink_end_child(True)

    @property
    def side_book_empty(self):
        return not qltk.get_children(self.side_book)

    def set_seekbar_widget(self, widget):
        """Add an alternative seek bar widget.

        Args:
            widget (Gtk.Widget): a new widget or None to remove the current one
        """

        self.top_bar.set_seekbar_widget(widget)

    def set_as_osx_window(self, osx_app):
        assert osx_app

        self._dock_menu = DockMenu(app)
        osx_app.set_dock_menu(self._dock_menu)
        # macOS native menubar (GtkosxApplication.set_menu_bar) expects a
        # GtkMenuBar, which doesn't exist under GTK4. Skipped until a GTK4
        # equivalent is wired up.

    def get_is_persistent(self):
        return True

    def open_file(self, filename):
        assert isinstance(filename, fsnative)

        song = self.__library.add_filename(filename, add=False)
        if song is not None:
            if self.__player.go_to(song):
                self.__player.paused = False
            return True
        return False

    def enqueue(self, songs, limit=0):
        """Append `songs` to the queue

        Ask for confimation if the number of songs exceeds `limit`.
        """

        if len(songs) > limit:
            dialog = ConfirmEnqueue(self, len(songs))
            if dialog.run() != Gtk.ResponseType.YES:
                return

        self.playlist.enqueue(songs)

    def __player_error(self, player, song, player_error):
        # it's modal, but mmkeys etc. can still trigger new ones
        dialog = PlaybackErrorDialog(self, player_error)
        self._playback_error_dialog = dialog
        dialog.run()
        self._playback_error_dialog = None

    def __configure_scan_dirs(self, library):
        """Get user to configure scan dirs, if none is set up"""
        if (
            not get_scan_dirs()
            and not len(library)
            and quodlibet.is_first_session("quodlibet")
        ):
            print_d("Couldn't find any scan dirs")

            resp = ConfirmLibDirSetup(self).run()
            if resp == ConfirmLibDirSetup.RESPONSE_SETUP:
                prefs = PreferencesWindow(self)
                prefs.set_page("library")
                prefs.show()

    def __keyboard_shortcuts(self, action):
        show_shortcuts(self)

    def __edit_bookmarks(self, librarian, player):
        if player.song:
            window = EditBookmarks(self, librarian, player)
            window.show()

    def __key_pressed(self, widget, event, player):
        if not player.song:
            return None

        def seek_relative(seconds):
            current = player.get_position()
            current += seconds * 1000
            current = min(player.song("~#length") * 1000 - 1, current)
            current = max(0, current)
            player.seek(current)

        if qltk.is_accel(event, "<alt>Right"):
            seek_relative(10)
            return True
        if qltk.is_accel(event, "<alt>Left"):
            seek_relative(-10)
            return True
        return None

    def __destroy(self, *args):
        # The tray icon plugin tries to unhide QL because it gets disabled
        # on Ql exit. The window should stay hidden after destroy.
        self.show = lambda: None
        self.present = self.show

    def __on_drop_files(self, target, value, x, y):
        if not isinstance(value, Gdk.FileList):
            return False
        dirs = []
        for f in value.get_files():
            path = f.get_path()
            if not path:
                continue
            loc = os.path.normpath(path)
            if os.path.isdir(loc):
                dirs.append(loc)
            else:
                loc = os.path.realpath(loc)
                if loc not in self.__library:
                    self.__library.add_filename(loc)
        if dirs:
            copool.add(self.__library.scan, dirs, cofuncid="library", funcid="library")
        return True

    def __on_drop_uri(self, target, value, x, y):
        if not isinstance(value, str):
            return False
        uris = [u.strip() for u in value.splitlines() if u.strip()]
        error_uri = None
        for uri in uris:
            try:
                filename = uri2fsn(uri)
            except ValueError:
                filename = None
            if filename is not None:
                continue  # local files handled by the FileList drop target
            if app.player.can_play_uri(uri):
                if uri not in self.__library:
                    self.__library.add([RemoteFile(uri)])
            else:
                error_uri = uri
                break
        if error_uri:
            ErrorMessage(
                self,
                _("Unable to add songs"),
                _("%s uses an unsupported protocol.") % util.bold(error_uri),
                escape_desc=False,
            ).run()
            return False
        return True

    def __songlist_key_press(self, controller, keyval, keycode, state):
        # GTK4: EventControllerKey.key-pressed has different signature
        # Create a simple event-like object for compatibility with browser.key_pressed()
        class KeyEvent:
            def __init__(self, keyval, keycode, state):
                self.type = Gdk.EventType.KEY_PRESS
                self.keyval = keyval
                self.keycode = keycode
                self.state = state

            def get_state(self):
                return self.state

        event = KeyEvent(keyval, keycode, state)
        return self.browser.key_pressed(event)

    def __songlist_drag_data_recv(self, view, *args):
        if self.browser.can_reorder:
            songs = view.get_songs()
            self.browser.reordered(songs)
        self.songlist.clear_sort()

    def __wire_shortcuts(self, player):
        """Attach keyboard shortcuts that drive the action group."""

        def add(trigger, action_name, target=None):
            shortcut_trigger = Gtk.ShortcutTrigger.parse_string(trigger)
            if target is None:
                action = Gtk.NamedAction.new(action_name)
            else:
                action = Gtk.NamedAction.new(action_name)
            sc = Gtk.Shortcut.new(shortcut_trigger, action)
            if target is not None:
                sc.set_arguments(target)
            controller.add_shortcut(sc)

        controller = Gtk.ShortcutController()
        controller.set_scope(Gtk.ShortcutScope.GLOBAL)

        add("<Primary>q", "win.Quit")
        add("<Primary>i", "win.Information")
        add("<Primary>j", "win.Jump")
        add("F5", "win.RefreshLibrary")
        add("<Primary>p", "win.Preferences")

        # Custom: Ctrl+Shift+J scrolls and jumps
        scroll_trigger = Gtk.ShortcutTrigger.parse_string("<Primary><Shift>j")

        def scroll_jump(widget, args):
            self.__jump_to_current(True, None, True)
            return True

        callback = Gtk.CallbackAction.new(scroll_jump)
        controller.add_shortcut(Gtk.Shortcut.new(scroll_trigger, callback))

        self.add_controller(controller)

    def __create_menu(self, player, library):
        """Build the main menubar (Gio.Menu) and its backing action group.

        Returns (action_group, menu_model). The action group should be
        attached to the window with the "win" prefix so menu items can
        reference actions as e.g. "win.AddFolders".
        """
        ag = Gio.SimpleActionGroup()
        actions: dict[str, Gio.SimpleAction] = {}

        def simple(name, handler=None, *handler_args):
            act = Gio.SimpleAction.new(name, None)
            if handler is not None:

                def adapter(action, _parameter, *args, _h=handler):
                    return _h(action, *args)

                act.connect("activate", adapter, *handler_args)
            ag.add_action(act)
            actions[name] = act
            return act

        simple("AddFolders", self.open_chooser)
        simple("AddFiles", self.open_chooser)
        simple("AddLocation", self.open_location)
        simple("Preferences", self.__preferences)
        simple("Plugins", self.__plugins)
        simple("RefreshLibrary", self.__rebuild, False)
        simple("Quit", lambda *x: self.destroy())

        simple("EditBookmarks").connect(
            "activate",
            lambda *a: self.__edit_bookmarks(library.librarian, player),
        )
        simple("EditTags", self.__current_song_prop)
        simple("Information", self.__current_song_info)
        simple("Jump", self.__jump_to_current)
        # Original code calls __jump_to_current once at action setup time
        self.__jump_to_current(True, None, True)

        simple("Previous", self.__previous_song)
        simple("PlayPause", self.__play_pause)
        simple("Next", self.__next_song)
        simple("Stop", self.__stop)

        stop_after = Gio.SimpleAction.new_stateful(
            "StopAfter", None, GLib.Variant.new_boolean(False)
        )
        stop_after.connect(
            "change-state",
            lambda act, state: act.set_state(state),
        )
        ag.add_action(stop_after)
        actions["StopAfter"] = stop_after
        # access point for the tray icon and PlayerOptions
        self.stop_after = stop_after

        simple("Shortcuts", self.__keyboard_shortcuts)
        simple("About", self.__show_about)
        simple("OnlineHelp", lambda *a: util.website(const.ONLINE_HELP))
        simple("SearchHelp", lambda *a: util.website(const.SEARCH_HELP))

        def check_updates_handler(*args):
            UpdateDialog(self).run()

        simple("CheckUpdates", check_updates_handler)

        # Stateful action for the radio "View<Browser>" group: a single
        # string-valued action whose state is the current browser name.
        current = config.get("memory", "browser")
        try:
            browsers.get(current)
        except ValueError:
            current = browsers.name(browsers.default)

        view_browser = Gio.SimpleAction.new_stateful(
            "SelectBrowser",
            GLib.VariantType.new("s"),
            GLib.Variant.new_string(current),
        )

        def on_select_browser(action, parameter):
            name = parameter.get_string()
            action.set_state(parameter)
            self._select_browser(action, name, library, player)

        view_browser.connect("activate", on_select_browser)
        ag.add_action(view_browser)
        actions["SelectBrowser"] = view_browser
        self._browser_action = view_browser

        # Per-browser "open in new window" actions
        for Kind in browsers.browsers:
            name = "Browser" + Kind.__name__

            def opener(action, _param, browser_cls=Kind):
                LibraryBrowser.open(browser_cls, library, player)

            act = Gio.SimpleAction.new(name, None)
            act.connect("activate", opener)
            ag.add_action(act)
            actions[name] = act

        # Build the menu model
        menu = Gio.Menu()

        file_menu = Gio.Menu()
        sec = Gio.Menu()
        sec.append(_("_Add a Folder…"), "win.AddFolders")
        sec.append(_("_Add a File…"), "win.AddFiles")
        sec.append(_("_Add a Location…"), "win.AddLocation")
        file_menu.append_section(None, sec)
        sec = Gio.Menu()
        sec.append(_("_Preferences"), "win.Preferences")
        sec.append(_("_Plugins"), "win.Plugins")
        file_menu.append_section(None, sec)
        sec = Gio.Menu()
        item = Gio.MenuItem.new(_("_Scan Library"), "win.RefreshLibrary")
        item.set_attribute_value(
            "tooltip", GLib.Variant.new_string(_("Check for changes in your library"))
        )
        sec.append_item(item)
        file_menu.append_section(None, sec)
        sec = Gio.Menu()
        sec.append(_("_Quit"), "win.Quit")
        file_menu.append_section(None, sec)
        menu.append_submenu(_("_File"), file_menu)

        song_menu = Gio.Menu()
        sec = Gio.Menu()
        sec.append(_("Edit Bookmarks…"), "win.EditBookmarks")
        sec.append(_("_Edit…"), "win.EditTags")
        song_menu.append_section(None, sec)
        sec = Gio.Menu()
        sec.append(_("_Information"), "win.Information")
        song_menu.append_section(None, sec)
        sec = Gio.Menu()
        sec.append(_("_Jump to Playing Song"), "win.Jump")
        song_menu.append_section(None, sec)
        menu.append_submenu(_("_Song"), song_menu)

        control_menu = Gio.Menu()
        control_menu.append(_("Pre_vious"), "win.Previous")
        # PlayPause label flips between Play/Pause; we store the section
        # for dynamic relabeling in __update_paused.
        self._playpause_section = Gio.Menu()
        self._playpause_section.append(_("_Play"), "win.PlayPause")
        control_menu.append_section(None, self._playpause_section)
        control_menu.append(_("_Next"), "win.Next")
        control_menu.append(_("Stop"), "win.Stop")
        control_menu.append(_("Stop After This Song"), "win.StopAfter")
        menu.append_submenu(_("_Control"), control_menu)

        browse_menu = Gio.Menu()
        # Filters submenu is owned by FilterMenu; it will append itself.
        self._filter_menu = FilterMenu(library, player, ag)
        browse_menu.append_submenu(_("_Filters"), self._filter_menu.menu_model)

        # "Open Browser" submenu - opens each browser kind in a new window
        open_browser = Gio.Menu()
        main_open = Gio.Menu()
        for Kind in _browser_kinds(external=False):
            main_open.append(Kind.accelerated_name, "win.Browser" + Kind.__name__)
        open_browser.append_section(None, main_open)
        ext_open = Gio.Menu()
        for Kind in _browser_kinds(external=True):
            ext_open.append(Kind.accelerated_name, "win.Browser" + Kind.__name__)
        if ext_open.get_n_items():
            open_browser.append_section(None, ext_open)
        browse_menu.append_submenu(_("Open _Browser"), open_browser)

        # View<Browser> radio section: switches the active main browser.
        view_section_main = Gio.Menu()
        for Kind in _browser_kinds(external=False):
            item = Gio.MenuItem.new(Kind.accelerated_name, None)
            item.set_action_and_target_value(
                "win.SelectBrowser", GLib.Variant.new_string(browsers.name(Kind))
            )
            view_section_main.append_item(item)
        browse_menu.append_section(None, view_section_main)
        ext_kinds = _browser_kinds(external=True)
        if ext_kinds:
            view_section_ext = Gio.Menu()
            for Kind in ext_kinds:
                item = Gio.MenuItem.new(Kind.accelerated_name, None)
                item.set_action_and_target_value(
                    "win.SelectBrowser",
                    GLib.Variant.new_string(browsers.name(Kind)),
                )
                view_section_ext.append_item(item)
            browse_menu.append_section(None, view_section_ext)
        menu.append_submenu(_("_Browse"), browse_menu)

        help_menu = Gio.Menu()
        help_menu.append(_("Online Help"), "win.OnlineHelp")
        help_menu.append(_("_Keyboard Shortcuts"), "win.Shortcuts")
        help_menu.append(_("Search Help"), "win.SearchHelp")
        sec = Gio.Menu()
        sec.append(_("_Check for Updates…"), "win.CheckUpdates")
        sec.append(_("_About"), "win.About")
        help_menu.append_section(None, sec)
        menu.append_submenu(_("_Help"), help_menu)

        self._actions = actions
        return ag, menu

    def __show_about(self, *args):
        about = AboutDialog(self, app)
        about.run()
        # GTK4: destroy() removed - about cleaned up automatically

    def select_browser(self, browser_key, library, player):
        """Given a browser name (see browsers.get()) changes the current
        browser.

        Returns True if the passed browser ID is known and the change
        was initiated.
        """

        try:
            browsers.get(browser_key)
        except ValueError:
            return False

        self._browser_action.activate(GLib.Variant.new_string(browser_key))
        return True

    def _select_browser(self, activator, current, library, player, restore=False):
        Browser = browsers.get(current)

        # GTK4: Use set_cursor() directly on widget instead of get_window()
        self.set_cursor_from_name("wait")

        # Wait for the cursor to update before continuing
        context = GLib.MainContext.default()
        while context.pending():
            context.iteration(False)

        config.set("memory", "browser", current)
        if self.browser:
            if not (self.browser.uses_main_library and Browser.uses_main_library):
                self.songlist.clear()
            container = self.browser.__container
            self.browser.unpack(container, self.songpane)
            if self.browser.accelerators:
                self.remove_accel_group(self.browser.accelerators)
            # GTK4: destroy() removed - container cleaned up automatically
            # GTK4: self.destroy() removed - browser cleaned up automatically
        self.browser = Browser(library)
        self.browser.connect("songs-selected", self.__browser_cb, library, player)
        self.browser.connect("songs-activated", self.__browser_activate)
        if restore:
            self.browser.restore()
            self.browser.activate()
        self.browser.finalize(restore)
        if not restore:
            self.browser.unfilter()
        if self.browser.can_reorder:
            self.songlist.enable_drop()
        elif self.browser.dropped:
            self.songlist.enable_drop(False)
        else:
            self.songlist.disable_drop()
        if self.browser.accelerators:
            self.add_accel_group(self.browser.accelerators)
        self.set_sortability()
        container = self.browser.__container = self.browser.pack(self.songpane)

        # GTK4: Reset the cursor when done loading the browser
        GLib.idle_add(self.set_cursor, None)

        player.replaygain_profiles[1] = self.browser.replaygain_profiles
        player.reset_replaygain()
        self.__browserbox.add(container)
        container.show()
        self._filter_menu.set_browser(self.browser)
        self.__hide_headers()

    def set_sortability(self):
        self.songlist.sortable = not self.browser.can_reorder

    def __update_paused(self, player, paused):
        label = _("_Play") if paused else _("P_ause")
        self._playpause_section.remove(0)
        self._playpause_section.append(label, "win.PlayPause")

    def __song_ended(self, player, song, stopped):
        # Check if the song should be removed, based on the
        # active filter of the current browser.
        active_filter = self.browser.active_filter
        if song and active_filter and not active_filter(song):
            iter_ = self.songlist.model.find(song)
            if iter_:
                self.songlist.remove_iters([iter_])

        if self.stop_after.get_state().get_boolean():
            player.paused = True
            self.stop_after.set_state(GLib.Variant.new_boolean(False))

    def __song_changed(self, library, songs, player):
        if player.info in songs:
            self.__update_title(player)

    def __update_title(self, player):
        song = player.info
        title = "Quod Libet"
        if song:
            tag = config.gettext("settings", "window_title_pattern")
            if tag:
                title = song.comma(tag) + " - " + title
        self.set_title(title)

    def __song_started(self, player, song):
        self.__update_title(player)

        for name in (
            "Next",
            "StopAfter",
            "EditTags",
            "Information",
            "EditBookmarks",
            "Jump",
        ):
            self._actions[name].set_enabled(bool(song))

        # don't jump on stream changes (player.info != player.song)
        main_should_jump = (
            song
            and player.song is song
            and not self.songlist._activated
            and config.getboolean("settings", "jump")
            and self.songlist.sourced
        )
        queue_should_jump = (
            song
            and player.song is song
            and not self.qexpander.queue._activated
            and config.getboolean("settings", "jump")
            and self.qexpander.queue.sourced
            and config.getboolean("memory", "queue_keep_songs")
        )
        if main_should_jump:
            self.__jump_to_current(False, self.songlist)
        elif queue_should_jump:
            self.__jump_to_current(False, self.qexpander.queue)

    def __play_pause(self, *args):
        app.player.playpause()

    def __stop(self, *args):
        app.player.stop()

    def __jump_to_current(self, explicit, songlist=None, force_scroll=False):
        """Select/scroll to the current playing song in the playlist.
        If it can't be found tell the browser to properly fill the playlist
        with an appropriate selection containing the song.

        explicit means that the jump request comes from the user and not
        from an event like song-started.

        songlist is the songlist to be jumped within. Usually the main song
        list or the queue. If None, the currently sourced songlist will be
        used.

        force_scroll will ask the browser to refill the playlist in any case.
        """

        def idle_jump_to(song, select):
            ok = songlist.jump_to_song(song, select=select)
            if ok:
                songlist.grab_focus()
            return False

        if not songlist:
            if (
                config.getboolean("memory", "queue_keep_songs")
                and self.qexpander.queue.sourced
            ):
                songlist = self.qexpander.queue
            else:
                songlist = self.songlist

        if app.player is None:
            return

        song = app.player.song

        # We are not playing a song
        if song is None:
            return

        if not force_scroll:
            ok = songlist.jump_to_song(song, select=explicit)
        else:
            assert explicit
            ok = False

        if ok:
            songlist.grab_focus()
        elif explicit:
            # if we can't find it and the user requested it, try harder
            self.browser.scroll(song)
            # We need to wait until the browser has finished
            # scrolling/filling and the songlist is ready.
            # Not perfect, but works for now.
            GLib.idle_add(idle_jump_to, song, explicit, priority=GLib.PRIORITY_LOW)

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
        name = GetStringDialog(
            self,
            _("Add a Location"),
            _("Enter the location of an audio file:"),
            button_label=_("_Add"),
            button_icon=Icons.LIST_ADD,
        ).run()
        if name:
            if not uri_is_valid(name):
                ErrorMessage(
                    self,
                    _("Unable to add location"),
                    _("%s is not a valid location.") % util.bold(name),
                ).run()
            elif not app.player.can_play_uri(name):
                ErrorMessage(
                    self,
                    _("Unable to add location"),
                    _("%s uses an unsupported protocol.") % (util.bold(name)),
                    escape_desc=False,
                ).run()
            else:
                if name not in self.__library:
                    self.__library.add([RemoteFile(name)])

    def open_chooser(self, action):
        if action.get_name() == "AddFolders":
            fns = choose_folders(self, _("Add Music"), _("_Add Folders"))
            if fns:
                # scan them
                copool.add(
                    self.__library.scan, fns, cofuncid="library", funcid="library"
                )
        else:
            patterns = ["*" + path2fsn(k) for k in formats.loaders.keys()]
            choose_filter = create_chooser_filter(_("Music Files"), patterns)
            fns = choose_files(self, _("Add Music"), _("_Add Files"), choose_filter)
            if fns:
                for filename in fns:
                    self.__library.add_filename(filename)

    def __songs_popup_menu(self, songlist):
        path, col = songlist.get_cursor()
        header = col.header_name
        menu = self.songlist.menu(header, self.browser, self.__library)
        if menu is not None:
            return self.songlist.popup_menu(menu, 0, GLib.CURRENT_TIME)
        return None

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
        app.player._reset()

    def __browser_cb(self, browser, songs, sorted, library, player):
        if browser.background:
            bg = background_filter()
            if bg:
                songs = list(filter(bg, songs))
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
                player.setup(self.playlist, song, seek_pos, False)

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
            headers.remove("~current")
        except ValueError:
            pass
        if len(headers) == len(get_columns()):
            # Not an addition or removal (handled separately)
            set_columns(headers)
            SongList.headers = headers

    def __make_query(self, query):
        if self.browser.can_filter_text():
            self.browser.filter_text(query.encode("utf-8"))
            self.browser.activate()

    def __set_totals(self, info, songs):
        length = sum(song.get("~#length", 0) for song in songs)
        t = self.browser.status_text(
            count=len(songs), time=util.format_time_preferred(length)
        )
        self.statusbar.set_default_text(t)


class ConfirmEnqueue(qltk.Message):
    def __init__(self, parent, count):
        title = (
            ngettext(
                "Are you sure you want to enqueue %d song?",
                "Are you sure you want to enqueue %d songs?",
                count,
            )
            % count
        )
        description = ""

        super().__init__(
            Gtk.MessageType.WARNING, parent, title, description, Gtk.ButtonsType.NONE
        )

        self.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        self.add_icon_button(_("_Enqueue"), Icons.LIST_ADD, Gtk.ResponseType.YES)
