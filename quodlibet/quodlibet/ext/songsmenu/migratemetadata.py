# -*- coding: utf-8 -*-
# Copyright 2013-2015 Ryan "ZDBioHazard" Turner <zdbiohazard2@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import math

from gi.repository import Gtk

from quodlibet import _, ngettext
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.formats._audio import MIGRATE
from quodlibet.util.tags import readable
from quodlibet.qltk import Icons
from quodlibet.qltk.window import Dialog


# This global info variable is where the song metadata
# is stored so we can use it between plugin activations.
# I know it's kinda ugly, but it's a lot more convenient
# for the user than writing and parsing temporary files.
songinfo = {}


class MetadataCopier(SongsMenuPlugin):
    PLUGIN_ID = "Migrate Metadata"
    PLUGIN_NAME = _("Migrate Metadata")
    PLUGIN_VERSION = "1.0"
    PLUGIN_ICON = Icons.EDIT_COPY
    PLUGIN_DESC = _("Copies the quodlibet-specific metadata between songs.")

    def plugin_songs(self, songs):
        global songinfo

        # Create a dialog.
        dlg = Dialog(title=_("Migrate Metadata"),
                     transient_for=self.plugin_window,
                     flags=(Gtk.DialogFlags.MODAL |
                            Gtk.DialogFlags.DESTROY_WITH_PARENT))
        dlg.set_border_width(4)
        dlg.vbox.set_spacing(4)

        dlg.add_icon_button(_("_Copy"), Icons.EDIT_COPY, Gtk.ResponseType.OK)
        dlg.add_icon_button(
            _("_Paste"), Icons.EDIT_PASTE, Gtk.ResponseType.APPLY)

        # Default to the "Copy" button when the songsinfo
        # list is empty, default to "Paste" button otherwise.
        if len(songinfo) == 0:
            dlg.set_default_response(Gtk.ResponseType.OK)
        else:
            dlg.set_default_response(Gtk.ResponseType.APPLY)

        # Create the tag table.
        frame = Gtk.Frame(label=_("Information to copy/paste"))
        # Try to make a nice even square-ish table.
        bias = 3  # Columns count for 3 rows, due to label text using space.
        columns = int(max(1, math.ceil(math.sqrt(len(MIGRATE) / bias))))
        rows = int(max(1, math.ceil(len(MIGRATE) / columns)))
        table = Gtk.Table(rows=rows, columns=columns, homogeneous=True)
        table.set_border_width(4)
        table.set_row_spacings(4)
        table.set_col_spacings(4)

        # Create check boxes.
        tags = {}
        for ctr, tag in enumerate(sorted(MIGRATE)):
            tags[tag] = Gtk.CheckButton(label=readable(tag).capitalize())
            tags[tag].set_active(True)

            # These floors and casts make sure we don't get floats.
            col = int(math.floor(ctr % columns))
            row = int(math.floor(ctr / columns))
            table.attach(tags[tag], col, col + 1, row, row + 1)

        # Create the indexing box.
        index = Gtk.CheckButton(label=_("Map tracks by disc and track number"))
        index.set_tooltip_markup(_("Enable this when you want to migrate "
                                   "metadata from one album to another while "
                                   "matching the disc and track numbers."
                                   "\n\n"
                                   "<b>Note:</b> this must be enabled when "
                                   "metadata is copied for track information "
                                   "to be stored."))
        # Automatically check when there is more
        # than one song in the songs or songinfo lists.
        if len(songs) > 1 or len(songinfo) > 1:
            index.set_active(True)

        # Assemble the window.
        frame.add(table)
        dlg.vbox.add(frame)
        dlg.vbox.add(index)
        dlg.vbox.add(Gtk.Label(ngettext("There is %d stored track.",
                                        "There are %d stored tracks.",
                                        len(songinfo)) % len(songinfo)))
        dlg.show_all()
        response = dlg.run()

        # Only accept expected responses.
        if response not in [Gtk.ResponseType.OK, Gtk.ResponseType.APPLY]:
            dlg.destroy()
            return

        # If copying, erase the currently stored metadata.
        if response == Gtk.ResponseType.OK:
            songinfo = {}

        # Go through the songs list and process it.
        for tid, song in enumerate(songs):
            # This tid will be what we index all of our tracks by,
            # so they will be easier to find when pasting metadata.
            if index.get_active() is True:
                tid = "%d-%d" % (int(song.get("discnumber", 0)),
                                 int(song.get("tracknumber", 0).split("/")[0]))

            # Erase track info if copying.
            if response == Gtk.ResponseType.OK:
                songinfo[tid] = {}

            for tag in tags.keys():
                if tags[tag].get_active() is False:
                    continue  # Skip unchecked tags.

                try:
                    if response == Gtk.ResponseType.OK:
                        # Copy information.
                        songinfo[tid][tag] = song[tag]
                    elif response == Gtk.ResponseType.APPLY:
                        # Paste information.
                        song[tag] = songinfo[tid][tag]
                except KeyError:
                    continue  # Just leave out tags that aren't present.

        # Erase songinfo after pasting.
        if response == Gtk.ResponseType.APPLY:
            songinfo = {}

        # Aaaaaand we're done.
        dlg.destroy()
        return
