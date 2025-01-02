# Copyright 2012-2015 Ryan "ZDBioHazard" Turner <zdbiohazard2@gmail.com>
#             2016-22 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from quodlibet import _, util
from quodlibet.plugins.songshelpers import each_song, is_writable
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.qltk import Icons


class EditPlaycount(SongsMenuPlugin):
    PLUGIN_ID = "editplaycount"
    PLUGIN_NAME = _("Edit Playcount")
    PLUGIN_DESC_MARKUP = _(
        "Edit a song's <tt>~#playcount</tt> and <tt>~#skipcount.</tt>"
        "\n\n"
        "When multiple songs are selected, counts will be "
        "incremented, rather than set."
        "\n\n"
        "When setting a song's <tt>~#playcount</tt> to 0, "
        "the <tt>~#lastplayed</tt> and <tt>~#laststarted</tt> "
        "entries will be cleared. "
        "However, when setting a 0-play song to a positive play "
        "count, no play times will be created."
    )
    PLUGIN_ICON = Icons.EDIT
    REQUIRES_ACTION = True

    plugin_handles = each_song(is_writable)

    def plugin_songs(self, songs):
        # This is just here so the spinner has something to call. >.>
        def response(win, response_id):
            dlg.response(response_id)
            return

        # Create a dialog.
        dlg = Gtk.Dialog(
            title=_("Edit Playcount"),
            flags=(Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT),
        )
        dlg.add_button(_("_Cancel"), Gtk.ResponseType.REJECT)
        dlg.add_button(_("_Apply"), Gtk.ResponseType.APPLY)
        dlg.set_default_response(Gtk.ResponseType.APPLY)
        dlg.set_border_width(4)
        dlg.vbox.set_spacing(4)

        # Create some spinners.
        play = Gtk.SpinButton()
        play.set_adjustment(Gtk.Adjustment(0, -1000, 1000, 1, 1))
        skip = Gtk.SpinButton()
        skip.set_adjustment(Gtk.Adjustment(0, -1000, 1000, 1, 1))

        # Connect the signals.
        play.connect("activate", response, Gtk.ResponseType.APPLY)
        skip.connect("activate", response, Gtk.ResponseType.APPLY)

        # Set some defaults.
        play.set_numeric(True)
        skip.set_numeric(True)

        # Put all this stuff in a pretty table.
        table = Gtk.Table(rows=2, columns=2)
        table.set_row_spacings(4)
        table.set_col_spacings(4)
        table.attach(Gtk.Label(_("Play Count")), 0, 1, 0, 1)
        table.attach(Gtk.Label(_("Skip Count")), 0, 1, 1, 2)
        table.attach(play, 1, 2, 0, 1)
        table.attach(skip, 1, 2, 1, 2)
        dlg.vbox.add(table)

        # Make a couple tweaks based on the current mode.
        if len(songs) == 1:
            play.set_adjustment(Gtk.Adjustment(0, 0, 9999, 1, 1))
            skip.set_adjustment(Gtk.Adjustment(0, 0, 9999, 1, 1))
            play.set_value(songs[0].get("~#playcount", 0))
            skip.set_value(songs[0].get("~#skipcount", 0))
        else:
            note = Gtk.Label()
            note.set_justify(Gtk.Justification.CENTER)
            note.set_markup(
                util.bold(_("Multiple files selected."))
                + "\n"
                + _("Counts will be incremented.")
            )
            dlg.vbox.add(note)

        dlg.show_all()

        # Only operate if apply is pressed.
        if dlg.run() == Gtk.ResponseType.APPLY:
            for song in songs:
                # Increment when not in single mode.
                if len(songs) == 1:
                    song["~#playcount"] = play.get_value_as_int()
                    song["~#skipcount"] = skip.get_value_as_int()
                else:  # Can't use += here because these tags might not exist.
                    song["~#playcount"] = max(
                        0, (song.get("~#playcount", 0) + play.get_value_as_int())
                    )
                    song["~#skipcount"] = max(
                        0, (song.get("~#skipcount", 0) + skip.get_value_as_int())
                    )

                # When the playcount is set to 0, delete the playcount
                # itself and the last played/started time. We don't
                # want unused or impossible data floating around.
                if song.get("~#playcount", 0) == 0:
                    for tag in ["~#playcount", "~#lastplayed", "~#laststarted"]:
                        song.pop(tag, None)

                # Also delete the skip count if it's zero.
                if song.get("~#skipcount", 0) == 0:
                    song.pop("~#skipcount", None)

        dlg.destroy()
        return
