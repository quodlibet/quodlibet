# Copyright 2004-2009 Joe Wreschnig, Michael Urman, Steven Robertson
#           2011-2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import GObject, Gtk, Gio, GLib

from quodlibet.browsers.playlists.menu import PlaylistMenu

from quodlibet import _
from quodlibet import browsers
from quodlibet.qltk.ratingsmenu import RatingsMenuItem
from quodlibet.util import connect_destroy, is_plasma
from quodlibet.qltk import get_top_parent
from quodlibet.qltk.browser import LibraryBrowser
from quodlibet.qltk.information import Information
from quodlibet.qltk.properties import SongProperties
from quodlibet.qltk.util import GSignals


class IndicatorMenu(Gtk.PopoverMenu):
    __gsignals__: GSignals = {
        "action-item-changed": (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, app, add_show_item=False):
        super().__init__()
        self.set_has_arrow(False)

        self._app = app
        player = app.player
        player_options = app.player_options

        self._model = Gio.Menu()
        self._actions = Gio.SimpleActionGroup()
        self.set_menu_model(self._model)
        self.insert_action_group("tray", self._actions)

        show_item_bottom = is_plasma()
        show_section = self._build_show_section(app) if add_show_item else None
        if show_section is not None and not show_item_bottom:
            self._model.append_section(None, show_section)

        # Play/Pause lives in its own section so it can be swapped in place.
        self._playpause_section = Gio.Menu()
        self._add_action("playpause", lambda: player.playpause())
        self._model.append_section(None, self._playpause_section)

        transport = Gio.Menu()
        self._add_action("previous", lambda: player.previous(force=True))
        self._add_action("next", lambda: player.next())
        transport.append(_("Pre_vious"), "tray.previous")
        transport.append(_("_Next"), "tray.next")
        self._model.append_section(None, transport)

        options = Gio.Menu()
        self._add_player_toggle(options, "shuffle", _("_Shuffle"), player_options)
        self._add_player_toggle(options, "repeat", _("_Repeat"), player_options)
        self._add_player_toggle(
            options, "stop-after", _("Stop _After This Song"), player_options
        )
        self._model.append_section(None, options)

        song_section = Gio.Menu()
        self._rating = RatingsMenuItem(
            [], app.library, self._actions, "tray", parent_getter=self._top_parent
        )
        song_section.append_item(self._rating.menu_item)

        pl_lib = app.library and app.library.playlists
        self._playlists = PlaylistMenu(
            [], pl_lib, self._actions, "tray", parent_getter=self._top_parent
        )
        song_section.append_item(self._playlists.menu_item)

        self._add_action("edit", self._on_properties)
        self._add_action("information", self._on_information)
        song_section.append(_("_Edit…"), "tray.edit")
        song_section.append(_("_Information"), "tray.information")
        self._model.append_section(None, song_section)

        browse_section = Gio.Menu()
        browse_menu = Gio.Menu()
        for i, browser_cls in enumerate(browsers.browsers):
            name = f"browse-{i}"
            self._add_action(
                name,
                lambda cls=browser_cls: LibraryBrowser.open(
                    cls, app.library, app.player
                ),
            )
            browse_menu.append(browser_cls.accelerated_name, f"tray.{name}")
        browse_section.append_submenu(_("Open _Browser"), browse_menu)
        self._model.append_section(None, browse_section)

        quit_section = Gio.Menu()
        self._add_action("quit", lambda: app.quit())
        quit_section.append(_("_Quit"), "tray.quit")
        self._model.append_section(None, quit_section)

        if show_section is not None and show_item_bottom:
            self._model.append_section(None, show_section)

        self.set_paused(True)
        self.set_song(None)

    def _top_parent(self):
        return get_top_parent(self._app.window)

    def _add_action(self, name, callback, enabled=True):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", lambda a, p: callback())
        action.set_enabled(bool(enabled))
        self._actions.add_action(action)
        return action

    def _add_player_toggle(self, section, prop, label, player_options):
        action = Gio.SimpleAction.new_stateful(
            prop, None, GLib.Variant("b", player_options.get_property(prop))
        )
        action.connect("change-state", self._on_toggle_state, player_options, prop)
        connect_destroy(
            player_options, f"notify::{prop}", self._on_option_notify, action, prop
        )
        self._actions.add_action(action)
        section.append(label, f"tray.{prop}")

    def _on_toggle_state(self, action, value, player_options, prop):
        action.set_state(value)
        player_options.set_property(prop, value.get_boolean())

    def _on_option_notify(self, options, _pspec, action, prop):
        action.set_state(GLib.Variant("b", options.get_property(prop)))

    def _build_show_section(self, app):
        section = Gio.Menu()
        action = Gio.SimpleAction.new_stateful(
            "show", None, GLib.Variant("b", app.window.get_visible())
        )
        action.connect("change-state", self._on_show_state, app)
        connect_destroy(app.window, "notify::visible", self._on_visible_notify, action)
        self._actions.add_action(action)
        section.append(
            _("_Show %(application-name)s") % {"application-name": app.name},
            "tray.show",
        )
        return section

    def _on_show_state(self, action, value, app):
        action.set_state(value)
        if value.get_boolean():
            app.present()
        else:
            app.hide()

    def _on_visible_notify(self, window, _pspec, action):
        action.set_state(GLib.Variant("b", window.get_visible()))

    def _on_properties(self):
        song = self._app.player.song
        SongProperties(self._app.librarian, [song], self._top_parent()).show()

    def _on_information(self):
        song = self._app.player.song
        Information(self._app.librarian, [song], self._top_parent()).show()

    def get_action_item(self):
        """The 'Play'/'Pause' target for Unity secondary-activate.

        Model menus have no widget items, so this is unavailable under GTK4.
        """

    def set_paused(self, paused):
        """Update the menu based on the player paused state"""
        self._playpause_section.remove_all()
        label = _("_Play") if paused else _("P_ause")
        self._playpause_section.append(label, "tray.playpause")
        self.emit("action-item-changed")

    def set_song(self, song):
        """Update the menu based on the passed song. Can be None.

        This should be the persistent song and not a stream/info one.
        """
        has_song = song is not None
        self._rating.set_sensitive(has_song)
        self._rating.set_songs([song])
        self._actions.lookup_action("edit").set_enabled(has_song)
        self._actions.lookup_action("information").set_enabled(has_song)
        self._playlists.build([song])
        self._playlists.set_sensitive(has_song and song.can_add)
