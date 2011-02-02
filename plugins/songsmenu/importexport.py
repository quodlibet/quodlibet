# Copyright 2005 Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk
from os.path import splitext, extsep, dirname

from quodlibet.qltk import ErrorMessage
from quodlibet.const import HOME as lastfolder
from quodlibet.library import library
from quodlibet.plugins.songsmenu import SongsMenuPlugin

__all__ = ['Export', 'Import']

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
    chooser.set_default_response(gtk.RESPONSE_ACCEPT)
    return chooser

class Export(SongsMenuPlugin):

    PLUGIN_ID = "ExportMeta"
    PLUGIN_NAME = _("Export Metadata")
    PLUGIN_ICON = 'gtk-save'

    def plugin_album(self, songs):

        songs.sort(lambda a, b: cmp(a('~#track'), b('~#track')) or cmp(a('~basename'), b('~basename')) or cmp(a, b))

        chooser = filechooser(save=True, title=songs[0]('album'))
        resp = chooser.run()
        fn = chooser.get_filename()
        chooser.destroy()
        if resp != gtk.RESPONSE_ACCEPT: return
        base, ext = splitext(fn)
        if not ext: fn = extsep.join([fn, 'tags'])

        global lastfolder
        lastfolder = dirname(fn)
        out = open(fn, 'w')

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

    PLUGIN_ID = "ImportMeta"
    PLUGIN_NAME = _("Import Metadata")
    PLUGIN_ICON = 'gtk-open'

    # Note: the usage of plugin_album here is sometimes NOT what you want. It
    # supports fixing up tags on several already-known albums just by walking
    # them via the plugin system and just selecting a new .tags; this mimics
    # export of several albums.
    #
    # However if one of the songs in your album is different from the rest (e.g.
    # one isn't tagged, or only one is) it will be passed in as two different
    # invocations, neither of which has the right size. If you find yourself in
    # that scenario a lot more than the previous one, change this to
    #   def plugin_songs(self, songs):
    # and comment out the songs.sort line for safety.
    def plugin_album(self, songs):

        songs.sort(lambda a, b: cmp(a('~#track'), b('~#track')) or cmp(a('~basename'), b('~basename')) or cmp(a, b))

        chooser = filechooser(save=False, title=songs[0]('album'))
        box = gtk.HBox()
        rename = gtk.CheckButton("Rename Files")
        rename.set_active(False)
        box.pack_start(rename)
        append = gtk.CheckButton("Append Metadata")
        append.set_active(True)
        box.pack_start(append)
        box.show_all()
        chooser.set_extra_widget(box)

        resp = chooser.run()
        append = append.get_active()
        rename = rename.get_active()
        fn = chooser.get_filename()
        chooser.destroy()
        if resp != gtk.RESPONSE_ACCEPT: return

        global lastfolder
        lastfolder = dirname(fn)

        metadata = []
        names = []
        index = 0
        for line in open(fn, 'rU'):
            if index == len(metadata):
                names.append(line[:line.rfind('.')])
                metadata.append({})
            elif line == '\n':
                index = len(metadata)
            else:
                key, value = line[:-1].split('=', 1)
                value = value.decode('utf-8')
                try: metadata[index][key].append(value)
                except KeyError: metadata[index][key] = [value]

        if not (len(songs) == len(metadata) == len(names)):
            ErrorMessage(None, "Songs mismatch", "There are %(select)d songs selected, but %(meta)d songs in the file. Aborting." % dict(select=len(songs), meta=len(metadata))).run()
            return

        for song, meta, name in zip(songs, metadata, names):
            for key, values in meta.iteritems():
                if append and key in song:
                    values = song.list(key) + values
                song[key] = '\n'.join(values)
            if rename:
                origname = song['~filename']
                newname = name + origname[origname.rfind('.'):]
                if library is not None: library.rename(origname, newname)
                else: song.rename(newname) # ex falso case doesn't use library
