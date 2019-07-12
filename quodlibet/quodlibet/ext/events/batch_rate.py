# Copyright 2019 Joschua Gandert
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


from traceback import format_exc
import os.path

from gi.repository import Gtk

from quodlibet import _, app, config, get_user_dir
from quodlibet.qltk import Icons, ErrorMessage
from quodlibet.plugins import PluginConfig, ConfProp
from quodlibet.plugins.events import EventPlugin
from quodlibet.plugins.songshelpers import is_writable
from quodlibet.util.songwrapper import check_wrapper_changed

INSTRUCTIONS = _("Add the ratings one after another to the file (at most 20). "
                 "Don't use spaces, commas or newlines. (Unless you have a "
                 "rating scale with more than nine digits. Then you'll need "
                 "to separate them with spaces or newlines.)\n\nThe file is "
                 "read right after a song was skipped or finished playing. "
                 "The last rating in the file is applied to the last song "
                 "(the one that just played).\n\nYou can use _ if you don't "
                 "want to change the value of certain songs while rating "
                 "others. For example, a file that contains only '4_0' "
                 "(without the quotes) would give the song that just played "
                 "the lowest rating, while not changing the one before that. "
                 "And the one before that would get a four.")

OUT_OF_RANGE_MSG = _(
    "%(value)s is not 0, %(max-value)s, or a number in between.")


class BatchRateConfig(object):
    _config = PluginConfig("BatchRate")

    path_to_rate_file = ConfProp(_config, "path_to_rate_file",
                                 os.path.join(get_user_dir(), 'lists',
                                              'batch_rate'))


class BatchRate(EventPlugin):
    PLUGIN_ID = "BatchRate"
    PLUGIN_NAME = _("Batch Rate")
    PLUGIN_DESC = _("Uses the content from a file to rate the last played "
                    "song(s).")
    PLUGIN_ICON = Icons.DOCUMENT_SAVE

    def __init__(self):
        self._config = BatchRateConfig()
        self._last_songs = []

    def PluginPreferences(self, parent):
        def changed_file(entry):
            fn = entry.get_text()
            self._config.path_to_rate_file = fn

        e = Gtk.Entry()
        e.set_text(self._config.path_to_rate_file)
        e.connect('changed', changed_file)

        hb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hb.set_border_width(6)
        hb.pack_start(Gtk.Label(label=_("File:")), False, False, 0)
        hb.pack_start(e, True, True, 0)

        instructions_lbl = Gtk.Label(label=INSTRUCTIONS, wrap=True)

        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main.set_border_width(0)

        main.pack_start(hb, False, False, 0)
        main.pack_start(instructions_lbl, False, False, 0)

        return main

    def plugin_on_song_started(self, song):
        rate_path = self._config.path_to_rate_file
        if os.path.exists(rate_path):
            return

        try:
            open(rate_path, 'a').close()
        except IOError:
            self._error_msg(_("Couldn't create file at %s") % rate_path)

    def plugin_on_song_ended(self, song, skipped):
        if song is not None:
            self._last_songs.append(song)

        if len(self._last_songs) > 20:
            del self._last_songs[0]

        with open(self._config.path_to_rate_file, "r+") as f:
            ratings = f.read().strip()
            if not ratings:
                return
            f.truncate(0)

        rating_num = config.getint("settings", "ratings")
        if rating_num > 9:
            ratings = ratings.split()

        changed = []
        for rating, song in zip(reversed(ratings), reversed(self._last_songs)):
            if rating == '_':  # skip rating
                continue

            try:
                rating = int(rating)
            except ValueError:
                msg = _("%s is not a number.") % rating
                self._error_msg(msg)
                return

            if 0 <= rating <= rating_num:
                song['~#rating'] = float(rating) / rating_num
                changed.append(song)
            else:
                d = {'value': rating, 'max-value': rating_num}
                self._error_msg(OUT_OF_RANGE_MSG % d)
                return

        if config.getboolean("editing", "save_to_songs"):
            self._try_write_changes_to_files(changed)

    def _error_msg(self, message):
        title = _("Error in %s") % self.PLUGIN_NAME
        ErrorMessage(app.window, title, message).run()

    def _try_write_changes_to_files(self, changed):
        try:
            self._write_changes_to_files(changed)
        except Exception:
            msg = _("There was a problem when writing the tags:")
            self._error_msg(msg + "\n\n" + format_exc())

    def _write_changes_to_files(self, changed):
        for song in changed:
            if not is_writable(song):
                continue
            song._needs_write = True

        check_wrapper_changed(app.library, app.window, changed)
