# Copyright 2005 Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gtk
from qltk import ErrorMessage
from os.path import splitext, extsep, dirname
from const import HOME as lastfolder
__all__ = ['Export', 'Import']

from plugins.songsmenu import SongsMenuPlugin

def filechooser(save, title):
    chooser = gtk.FileChooserDialog(
        title=(save and "Export %s Metadata to ..." or "Import %s Metadata from ...") % title,
        action=(save and gtk.FILE_CHOOSER_ACTION_SAVE or gtk.FILE_CHOOSER_ACTION_OPEN),
        buttons=(gtk.STOCK_OK, gtk.RESPONSE_ACCEPT, gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT))

    for name, pattern in [('Tag files (*.tags)','*.tags'), ('All Files','*')]:
        filter = gtk.FileFilter()
        filter.set_name(name)
        filter.add_pattern(pattern)
        chooser.add_filter(filter)

    chooser.set_current_folder(lastfolder)
    return chooser

class Export(SongsMenuPlugin):

    PLUGIN_NAME = "ExportMeta"
    PLUGIN_DESC = "Export Metadata"
    PLUGIN_ICON = 'gtk-save'

    def plugin_album(self, songs):

        songs.sort(lambda a, b: cmp(a('~#track'), b('~#track')) or cmp(a('~basename'), b('~basename')) or cmp(a, b))

        chooser = filechooser(save=True, title=songs[0]('album'))
        resp = chooser.run()
        fn = chooser.get_filename()
        base, ext = splitext(fn)
        if not ext: fn = extsep.join([fn, 'tags'])
        chooser.destroy()
        if resp != gtk.RESPONSE_ACCEPT: return

        global lastfolder
        lastfolder = dirname(fn)
        out = open(fn, 'wU')

        for song in songs:
            print>>out, str(song('~basename'))
            keys = song.keys()
            keys.sort()
            for key in keys:
                if key.startswith('~'): continue
                for val in song.list(key):
                    print>>out, '%s=%s' % (key, val.encode('utf-8'))
            print>>out

class Import(SongsMenuPlugin):

    PLUGIN_NAME = "ImportMeta"
    PLUGIN_DESC = "Import Metadata"
    PLUGIN_ICON = 'gtk-open'

    def plugin_album(self, songs):

        songs.sort(lambda a, b: cmp(a('~#track'), b('~#track')) or cmp(a('~basename'), b('~basename')) or cmp(a, b))

        chooser = filechooser(save=False, title=songs[0]('album'))
        append = gtk.CheckButton("Append Metadata")
        append.set_active(True)
        append.show()
        chooser.set_extra_widget(append)

        resp = chooser.run()
        append = append.get_active()
        fn = chooser.get_filename()
        chooser.destroy()
        if resp != gtk.RESPONSE_ACCEPT: return

        global lastfolder
        lastfolder = dirname(fn)

        metadata = []
        index = 0
        for line in open(fn, 'rU'):
            if index == len(metadata):
                metadata.append({})
            elif line == '\n':
                index = len(metadata)
            else:
                key, value = line[:-1].split('=', 1)
                value = value.decode('utf-8')
                try: metadata[index][key].append(value)
                except KeyError: metadata[index][key] = [value]

        if len(songs) != len(metadata):
            ErrorMessage(None, "Songs mismatch", "There are %(select)d songs selected, but %(meta)d songs in the file. Aborting." % dict(select=len(songs), meta=len(metadata))).run()
            return

        for song, meta in zip(songs, metadata):
            for key, values in meta.iteritems():
                if append: values = song.list(key) + values
                song[key] = '\n'.join(values)
