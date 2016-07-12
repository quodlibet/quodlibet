# -*- coding: utf-8 -*-
# Copyright 2013-2015 Ryan "ZDBioHazard" Turner <zdbiohazard2@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.qltk import Icons


# This global info variable is where the song metadata
# is stored so we can use it between plugin activations.
# I know it's kinda ugly, but it's a lot more convenient
# for the user than writing and parsing temporary files.
songinfo = {}


class MetadataCopier(SongsMenuPlugin):
    PLUGIN_ID = "migratemetadata"
    PLUGIN_NAME = _("Migrate Metadata")
    PLUGIN_VERSION = "1.0"
    PLUGIN_ICON = Icons.EDIT_COPY
    PLUGIN_DESC = _("Copies the quodlibet-specific metadata between songs.")

    def plugin_songs(self, songs):
        global songinfo

        # Create a dialog.
        dlg = Gtk.Dialog(title=_("Migrate Metadata"),
                         flags=(Gtk.DialogFlags.MODAL |
                                Gtk.DialogFlags.DESTROY_WITH_PARENT),
                         buttons=(Icons.EDIT_COPY, Gtk.ResponseType.OK,
                                  Icons.EDIT_PASTE, Gtk.ResponseType.APPLY))
        dlg.set_border_width(4)
        dlg.vbox.set_spacing(4)

        # Default to the "Copy" button when the songsinfo
        # list is empty, default to "Paste" button otherwise.
        if len(songinfo) == 0:
            dlg.set_default_response(Gtk.ResponseType.OK)
        else:
            dlg.set_default_response(Gtk.ResponseType.APPLY)

        # Add stuff to the dialog.
        frame = Gtk.Frame(label=_("Information to copy/paste"))
        table = Gtk.Table(rows=3, columns=2, homogeneous=True)
        table.set_border_width(4)
        table.set_row_spacings(4)
        table.set_col_spacings(4)

        # Create check boxes.
        rating = Gtk.CheckButton(label=_("Rating"))
        energy = Gtk.CheckButton(label=_("Energy"))
        playct = Gtk.CheckButton(label=_("Play Count"))
        skipct = Gtk.CheckButton(label=_("Skip Count"))
        dstart = Gtk.CheckButton(label=_("Last Started"))
        dlplay = Gtk.CheckButton(label=_("Last Played"))
        dadded = Gtk.CheckButton(label=_("Date Added"))
        bkmark = Gtk.CheckButton(label=_("Bookmarks"))
        # Check all the checkboxes.
        for box in [rating, energy, playct, skipct,
                    dstart, dlplay, dadded, bkmark]:
            box.set_active(True)

        # Put all those checkboxes into the tble.
        table.attach(rating, 0, 1, 0, 1)
        table.attach(energy, 1, 2, 0, 1)
        table.attach(playct, 0, 1, 1, 2)
        table.attach(skipct, 1, 2, 1, 2)
        table.attach(dstart, 0, 1, 2, 3)
        table.attach(dlplay, 1, 2, 2, 3)
        table.attach(dadded, 0, 1, 3, 4)
        table.attach(bkmark, 1, 2, 3, 4)

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
        dlg.vbox.add(Gtk.Label(_("Currently stored tracks: %d" %
                                 len(songinfo))))
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

            for field in [("~#rating", rating), ("~#energy", energy),
                          ("~#playcount", playct), ("~#skipcount", skipct),
                          ("~#laststarted", dstart), ("~#lastplayed", dlplay),
                          ("~#added", dadded), ("~bookmark", bkmark)]:
                if field[1].get_active() is True:
                    try:
                        if response == Gtk.ResponseType.OK:
                            # Copy information.
                            songinfo[tid][field[0]] = song[field[0]]
                        elif response == Gtk.ResponseType.APPLY:
                            # Paste information.
                            song[field[0]] = songinfo[tid][field[0]]
                    except KeyError:
                        pass  # Just leave out fields that aren't present.

        # Erase songinfo after pasting.
        if response == Gtk.ResponseType.APPLY:
            songinfo = {}

        # Aaaaaand we're done.
        dlg.destroy()
        return
