# Copyright 2011-2020 Nick Boultbee
#           2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


from gi.repository import Gtk, Gio, GLib

from quodlibet import _
from quodlibet import config
from quodlibet import qltk
from quodlibet.config import RATINGS
from quodlibet.util import format_rating


class ConfirmRateMultipleDialog(qltk.Message):
    def __init__(self, parent, count: int, value: float | None):
        assert count > 1

        title = _("Are you sure you want to change the rating of all %d songs?") % count
        if value is None:
            desc = _("The saved ratings will be removed")
            action_title = _("_Remove Rating")
        else:
            desc = _(
                "The rating of all selected songs will be changed to %s"
            ) % format_rating(value)
            action_title = _("Change _Rating")

        super().__init__(
            Gtk.MessageType.WARNING, parent, title, desc, Gtk.ButtonsType.NONE
        )

        self.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        self.add_button(action_title, Gtk.ResponseType.YES)


class RatingsMenuItem:
    """Builds a "Rating" submenu on a ``Gio.Menu`` model.

    Registers a stateful "rating" radio action plus a "rating-remove"
    action on ``action_group`` (prefixed with ``prefix``). Expose the
    resulting :class:`Gio.MenuItem` via :attr:`menu_item` for the owner to
    append to its model.
    """

    def __init__(
        self,
        songs,
        library,
        action_group: Gio.SimpleActionGroup,
        prefix: str,
        parent_getter=None,
        label=_("_Rating"),  # noqa: B008
    ):
        self._songs = songs
        self._library = library
        self._prefix = prefix
        self._parent_getter = parent_getter or (lambda: None)

        self._rating_action = Gio.SimpleAction.new_stateful(
            "rating", GLib.VariantType.new("d"), GLib.Variant("d", -1.0)
        )
        self._rating_action.connect("change-state", self._on_rating_change_state)
        self._remove_action = Gio.SimpleAction.new("rating-remove", None)
        self._remove_action.connect("activate", self._on_rating_remove)
        action_group.add_action(self._rating_action)
        action_group.add_action(self._remove_action)

        submenu = Gio.Menu()
        ratings_section = Gio.Menu()
        for value in RATINGS.all:
            item = Gio.MenuItem.new(f"{value:0.2f}\t{format_rating(value)}", None)
            item.set_action_and_target_value(
                f"{prefix}.rating", GLib.Variant("d", value)
            )
            ratings_section.append_item(item)
        submenu.append_section(None, ratings_section)

        remove_section = Gio.Menu()
        remove_section.append(_("_Remove Rating"), f"{prefix}.rating-remove")
        submenu.append_section(None, remove_section)

        self._submenu = submenu
        self.menu_item = Gio.MenuItem.new_submenu(label, submenu)

        self._select_ratings()

    @property
    def submenu(self) -> Gio.Menu:
        return self._submenu

    def set_songs(self, songs):
        """Set a new set of songs affected by the rating menu"""
        self._songs = songs
        self._select_ratings()

    def set_sensitive(self, sensitive: bool):
        self._rating_action.set_enabled(sensitive)
        self._remove_action.set_enabled(sensitive)

    def _select_ratings(self):
        ratings = [song("~#rating") for song in self._songs if song and song.has_rating]
        if ratings and len(set(ratings)) == 1 and len(ratings) == len(self._songs):
            state = ratings[0]
        else:
            state = -1.0
        self._rating_action.set_state(GLib.Variant("d", state))

    def _on_rating_change_state(self, action, value):
        action.set_state(value)
        self.set_rating(value.get_double(), self._songs, self._library)

    def _on_rating_remove(self, action, _param):
        self.remove_rating(self._songs, self._library)

    def set_rating(self, value, songs, librarian):
        count = len(songs)
        if count > 1 and config.getboolean("browsers", "rating_confirm_multiple"):
            dialog = ConfirmRateMultipleDialog(self._parent_getter(), count, value)
            if dialog.run() != Gtk.ResponseType.YES:
                return
        for song in songs:
            song["~#rating"] = value
        librarian.changed(songs)

    def remove_rating(self, songs, librarian):
        count = len(songs)
        if count > 1 and config.getboolean("browsers", "rating_confirm_multiple"):
            dialog = ConfirmRateMultipleDialog(self._parent_getter(), count, None)
            if dialog.run() != Gtk.ResponseType.YES:
                return
        reset = []
        for song in songs:
            if "~#rating" in song:
                del song["~#rating"]
                reset.append(song)
        librarian.changed(reset)
