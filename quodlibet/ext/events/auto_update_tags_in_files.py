# Copyright 2019-2020 Joschua Gandert
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
from enum import IntEnum
from traceback import format_exc

import mutagen
from mutagen._vorbis import VCommentDict
from mutagen.mp3 import MP3

from gi.repository import Gtk
from quodlibet.formats import AudioFile

from quodlibet import _, app, config, qltk
from quodlibet.qltk import Icons, ErrorMessage, Message
from quodlibet.plugins import PluginConfig, BoolConfProp, IntConfProp
from quodlibet.plugins.events import EventPlugin
from quodlibet.plugins.songshelpers import is_writable
from quodlibet.util import print_e
from quodlibet.util.songwrapper import SongWrapper, \
    background_check_wrapper_changed


class UpdateStrategy(IntEnum):
    AFTER_PLAY_NOT_SKIP = 0
    AFTER_PLAY_OR_SKIP = 1
    ONCE_ALBUM_RATED = 2


STRATEGY_TO_NAME = [_("After every play (default)"),
                    _("After every play or skip"),
                    _("Once, when album fully rated")]

STRATEGY_TO_DESC = [  #
    _("Whenever a song was played but not skipped, the plugin will write the "
      "tags to the file. The skip count isn't saved, so this avoids "
      "unnecessary writes."),
    _("Whenever a song was played or skipped, the plugin will write the tags "
      "to the file. Can be useful if you want to make sure that ratings of "
      "songs you dislike and thus skipped are written to the files."),
    _("When a song was played or skipped, the album of that song will be "
      "checked. If every song in the album has been rated and at least one "
      "has no ratings or play counts stored in its file, the plugin will "
      "write the tags to the songs' files. \n\nUse this to avoid constant "
      "file updates, but be aware that once an album was updated, you'll have "
      "to use the 'Update Tags in Files' plugin whenever you want modified "
      "ratings and play counts to be written to the files.")]

PLAY_COUNT_ABOVE_ZERO_TOOLTIP = _(
        "When the plugin writes the tags of an album, it will "
        "first set the play count of the songs which are zero to one.\n"
        "Sometimes you already know that you don't like a song, so "
        "setting it to one when saving can be useful later on, when "
        "searching for albums you have fully listened to (%s).")

WRITE_ERROR_FMT = _("Couldn't write '%s'")


class Config(object):
    _config = PluginConfig("autoupdatetagsinfiles")

    update_strategy = IntConfProp(_config, "update_strategy",
                                  UpdateStrategy.AFTER_PLAY_NOT_SKIP.value)
    ensure_play_counts_above_zero = BoolConfProp(  # useful for searching
            _config, "ensure_play_counts_above_zero", False)


CONFIG = Config()


class AutoUpdateTagsInFiles(EventPlugin):
    PLUGIN_ID = "AutoUpdateTagsInFiles"
    PLUGIN_NAME = _("Auto Update Tags in Files")
    PLUGIN_DESC = _("When songs were played, update the tags in their files. "
                    "This will ensure play counts and ratings are up to date.")
    PLUGIN_ICON = Icons.DOCUMENT_SAVE

    def PluginPreferences(self, _):
        return AutoUpdateTagsPrefs()

    def enabled(self):
        if not config.getboolean("editing", "save_to_songs"):
            config.set("editing", "save_to_songs", True)

            warning_text = _("The following setting was enabled as it's "
                             "required for this plugin to work:\n\n%s")
            setting_name = _("Save ratings and play _counts in tags")

            Message(Gtk.MessageType.INFO, app.window, _("Settings updated"),
                    warning_text % setting_name.replace("_", "")).run()

    def plugin_on_song_ended(self, song, skipped):
        if song is None or not is_writable(song):
            return

        strategy = CONFIG.update_strategy
        if strategy == UpdateStrategy.AFTER_PLAY_NOT_SKIP:
            if not skipped:
                self._try_to_update_song(song)
            return
        elif strategy == UpdateStrategy.AFTER_PLAY_OR_SKIP:
            self._try_to_update_song(song)
            return

        self._update_album_if_fully_rated(song.album_key)

    def _try_to_update_song(self, song_wrapper):
        try:
            song_wrapper._needs_write = True
            self._write_tags_to_files([song_wrapper])
        except Exception as e:
            print_e(e)
            self._error_msg(WRITE_ERROR_FMT % song_wrapper._song)

    def _error_msg(self, message):
        title = _("Error in %s") % self.PLUGIN_NAME
        ErrorMessage(app.window, title, message).run()

    def _update_album_if_fully_rated(self, album_key):
        album = app.library.albums.get(album_key, None)
        if album is None:
            return

        songs = album.songs
        # first check for ratings to avoid costly file checks
        if not songs or not all(song.has_rating for song in songs):
            return

        if all(has_rating_and_play_count_in_file(song) for song in songs):
            return

        # at least one song has no ratings or play counts stored in files
        try:
            self._update_album(songs)
        except Exception as e:
            print_e(e)
            self._error_msg(WRITE_ERROR_FMT % album_key)

    def _update_album(self, songs):
        song_wrappers = []

        req_play_counts_above_zero = CONFIG.ensure_play_counts_above_zero
        for song in songs:
            if req_play_counts_above_zero and not song.get("~#playcount", 0):
                song['~#playcount'] = 1

            wrapper = SongWrapper(song)
            wrapper._needs_write = True
            song_wrappers.append(wrapper)

        self._write_tags_to_files(song_wrappers)

    def _write_tags_to_files(self, song_wrappers):
        background_check_wrapper_changed(app.library, song_wrappers)


def has_rating_and_play_count_in_file(song: AudioFile):
    save_email = config.get("editing", "save_email").strip()
    f = mutagen.File(song['~filename'])

    if isinstance(f, MP3):
        if 'POPM:' + save_email in f:
            return True
    elif f.tags is not None and isinstance(f.tags, VCommentDict):
        if 'rating:' + save_email in f and 'playcount:' + save_email in f:
            return True

    return False


class AutoUpdateTagsPrefs(Gtk.Box):
    def __init__(self):
        super(AutoUpdateTagsPrefs, self).__init__(
                orientation=Gtk.Orientation.VERTICAL, spacing=6)

        strategy_boxes = []
        for desc in STRATEGY_TO_DESC:
            desc_label = Gtk.Label(label=desc, wrap=True)

            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            box.pack_start(desc_label, False, False, 0)

            strategy_boxes.append(box)

        def ensure_play_count_toggled(button, *args):
            CONFIG.ensure_play_counts_above_zero = button.get_active()

        ensure_play_count_checkbutton = Gtk.CheckButton(
                label=_("Ensure play counts are above zero when saving"),
                valign=Gtk.Align.START)
        ensure_play_count_checkbutton.set_tooltip_text(
                PLAY_COUNT_ABOVE_ZERO_TOOLTIP % "#(playcount:min = 1)")
        ensure_play_count_checkbutton.set_active(
                CONFIG.ensure_play_counts_above_zero)
        ensure_play_count_checkbutton.connect("toggled",
                                              ensure_play_count_toggled)

        album_box = strategy_boxes[UpdateStrategy.ONCE_ALBUM_RATED]
        album_box.pack_start(ensure_play_count_checkbutton, False, False, 0)

        def show_only_current_box():
            current = CONFIG.update_strategy
            for n, box in enumerate(strategy_boxes):
                box.set_visible(n == current)

        grid = Gtk.Grid(column_spacing=6, row_spacing=6)

        def grid_add(x, y, child):
            grid.attach(child, x, y, 1, 1)

        def change_strategy(button):
            new_strategy = button.get_active()
            CONFIG.update_strategy = new_strategy
            show_only_current_box()

        update_combobox = Gtk.ComboBoxText()
        for name in STRATEGY_TO_NAME:
            update_combobox.append_text(name)
        update_combobox.set_active(CONFIG.update_strategy)
        update_combobox.connect('changed', change_strategy)

        update_lbl = ConfigLabel(_("_Update strategy:"), update_combobox)

        grid_add(0, 0, update_lbl)
        grid_add(1, 0, update_combobox)
        for box in strategy_boxes:
            # show_all will be called on the plugin preference interface, so
            # without the following that would result in overlapping text
            box.show_all()
            box.props.no_show_all = True

            grid_add(1, 1, box)

        show_only_current_box()

        frame = qltk.Frame(label=_("Preferences"), child=grid)
        frame.set_border_width(6)
        self.pack_start(frame, False, False, 0)


class ConfigLabel(Gtk.Label):
    """Customised Label for configuration, tied to a widget"""

    def __init__(self, text, widget):
        super(Gtk.Label, self).__init__(label=text, use_underline=True)
        self.set_mnemonic_widget(widget)
        self.set_alignment(0.0, 0.5)
