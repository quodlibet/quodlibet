# Copyright 2005 Michael Urman
#           2016-18 Nick Boultbee
#           2018 Fredrik Strupe
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
from typing import Dict, List

from gi.repository import Gtk
from os.path import splitext, dirname

from senf import fsn2bytes, extsep

from quodlibet import _
from quodlibet import app, print_e
from quodlibet.plugins.songshelpers import each_song, is_writable, is_a_file, \
    is_finite
from quodlibet.qltk import ErrorMessage, Icons
from quodlibet.util.path import get_home_dir
from quodlibet.plugins.songsmenu import SongsMenuPlugin

__all__ = ['Export', 'Import']


lastfolder = get_home_dir()


def filechooser(save, title):
    chooser = Gtk.FileChooserDialog(
        title=(save and "Export %s Metadata to ..." or
               "Import %s Metadata from ...") % title,
        action=(save and Gtk.FileChooserAction.SAVE or
                Gtk.FileChooserAction.OPEN))

    chooser.add_button(_("_OK"), Gtk.ResponseType.ACCEPT)
    chooser.add_button(_("_Cancel"), Gtk.ResponseType.REJECT)

    for name, pattern in [('Tag files (*.tags)', '*.tags'),
                          ('All Files', '*')]:
        filter = Gtk.FileFilter()
        filter.set_name(name)
        filter.add_pattern(pattern)
        chooser.add_filter(filter)

    chooser.set_current_folder(lastfolder)
    chooser.set_default_response(Gtk.ResponseType.ACCEPT)
    return chooser


def sort_key_for(s):
    return s('~#track', 1), s('~basename'), s


class Export(SongsMenuPlugin):
    PLUGIN_ID = "ExportMeta"
    PLUGIN_NAME = _("Export Metadata")
    PLUGIN_DESC = _("Exports metadata of selected songs as a .tags file.")
    PLUGIN_ICON = Icons.DOCUMENT_SAVE_AS
    REQUIRES_ACTION = True

    plugin_handles = each_song(is_finite)

    def plugin_album(self, songs):
        songs.sort(key=sort_key_for)
        chooser = filechooser(save=True, title=songs[0]('album'))
        resp = chooser.run()
        fn = chooser.get_filename()
        chooser.destroy()
        if resp != Gtk.ResponseType.ACCEPT:
            return
        base, ext = splitext(fn)
        if not ext:
            fn = extsep.join([fn, 'tags'])

        global lastfolder
        lastfolder = dirname(fn)

        export_metadata(songs, fn)


def export_metadata(songs, target_path):
    """Raises OSError/IOError"""

    with open(target_path, 'wb') as out:
        for song in songs:
            out.write(fsn2bytes(song('~basename'), "utf-8"))
            out.write(os.linesep.encode("utf-8"))

            for key in sorted(song.keys()):
                if key.startswith('~'):
                    continue
                for val in song.list(key):
                    line = '%s=%s' % (key, val)
                    out.write(line.encode("utf-8"))
                    out.write(os.linesep.encode("utf-8"))
            out.write(os.linesep.encode("utf-8"))


class Import(SongsMenuPlugin):
    PLUGIN_ID = "ImportMeta"
    PLUGIN_NAME = _("Import Metadata")
    PLUGIN_DESC = _("Imports metadata for selected songs from a .tags file.")
    PLUGIN_ICON = Icons.DOCUMENT_OPEN
    REQUIRES_ACTION = True

    plugin_handles = each_song(is_writable, is_a_file)

    # Note: the usage of plugin_album here is sometimes NOT what you want. It
    # supports fixing up tags on several already-known albums just by walking
    # them via the plugin system and just selecting a new .tags; this mimics
    # export of several albums.
    #
    # However if one of the songs in your album is different from the rest
    # (e.g.
    # one isn't tagged, or only one is) it will be passed in as two different
    # invocations, neither of which has the right size. If you find yourself in
    # that scenario a lot more than the previous one, change this to
    #   def plugin_songs(self, songs):
    # and comment out the songs.sort line for safety.
    def plugin_album(self, songs):

        songs.sort(key=sort_key_for)

        chooser = filechooser(save=False, title=songs[0]('album'))
        box = Gtk.HBox()
        rename = Gtk.CheckButton("Rename Files")
        rename.set_active(False)
        box.pack_start(rename, True, True, 0)
        append = Gtk.CheckButton("Append Metadata")
        append.set_active(True)
        box.pack_start(append, True, True, 0)
        box.show_all()
        chooser.set_extra_widget(box)

        resp = chooser.run()
        append = append.get_active()
        rename = rename.get_active()
        fn = chooser.get_filename()
        chooser.destroy()
        if resp != Gtk.ResponseType.ACCEPT:
            return

        global lastfolder
        lastfolder = dirname(fn)

        metadata = []
        names = []
        index = 0
        for line in open(fn, 'r', encoding="utf-8"):
            if index == len(metadata):
                names.append(line[:line.rfind('.')])
                metadata.append({})
            elif line == '\n':
                index = len(metadata)
            else:
                key, value = line[:-1].split('=', 1)
                try:
                    metadata[index][key].append(value)
                except KeyError:
                    metadata[index][key] = [value]

        if not (len(songs) == len(metadata) == len(names)):
            ErrorMessage(None, "Songs mismatch",
                         "There are %(select)d songs selected, but %(meta)d "
                         "songs in the file. Aborting." %
                         dict(select=len(songs), meta=len(metadata))).run()
            return

        self.update_files(songs, metadata, names, append=append, rename=rename)

    def update_files(self,
                     songs: List,
                     metadata: List[Dict[str, List]],
                     names: List,
                     append=True, rename=False):
        for song, meta, name in zip(songs, metadata, names):
            for key, values in meta.items():
                if append and key in song:
                    values = song.list(key) + values
                song[key] = '\n'.join(values)
            if rename:
                origname = song['~filename']
                path = os.path.dirname(origname)
                suffix_index = origname.rfind('.')
                suffix = origname[suffix_index:] if suffix_index >= 0 else ''
                newname = os.path.join(path, name + suffix)
                try:
                    app.library.rename(song._song, newname)
                except ValueError:
                    print_e("File {} already exists. Ignoring file "
                            "rename.".format(newname))
        app.library.changed(songs)
