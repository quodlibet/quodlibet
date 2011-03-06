# -*- coding: utf-8 -*-

# Copyright 2005 Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#

# My songs are in file systems in the form:
#   /path_to/Artist/date - album/trackno - title.ext

import os
from quodlibet.qltk import ConfirmAction
from quodlibet.plugins.songsmenu import SongsMenuPlugin

# convert to unicode
def convert2unicode(buf):
    if type(buf) == type(unicode('')):
        return buf
    codecs_lst = ('ascii', 'latin-1', 'cp850')
    for c in codecs_lst:
        try:
            buf2 = unicode(buf, c)
        except UnicodeDecodeError:
            pass
        else:
            break
    else:
        buf2 = unicode(buf, c, 'replace')
    return buf2

class FixSongTags(SongsMenuPlugin):
    PLUGIN_ID = 'Fix song tags'
    PLUGIN_NAME = _('Fix song tags')
    PLUGIN_DESC = ('Fix songs tags based on filename and directory, '
                   'guessing encoding')
    PLUGIN_ICON = 'gtk-edit'
    PLUGIN_VERSION = '0.1'

    def plugin_songs(self, songs):
        if not songs:
            return
        ss = []
        for song in songs:
            filename = song['~filename']

            # tracknumber, title
            if not os.path.isfile(filename):
                continue
            basename = os.path.basename(filename)
            basename = os.path.splitext(basename)[0]
            ds = [f.strip() for f in basename.split('-')]
            if len(ds) > 1:
                try:
                    trackno = str(int(ds[0]))
                except ValueError:
                    trackno = ''
                    title = basename
                else:
                    title = ''.join(ds[1:])
            else:
                trackno = ''
                title = basename
            trackno = convert2unicode(trackno)
            title = convert2unicode(title)

            # date, album
            dirname = os.path.dirname(filename)
            if not os.path.isdir(dirname):
                continue
            dirname = dirname.split(os.sep)[-1]
            ds = [d.strip() for d in dirname.split('-')]
            if len(ds) > 1:
                try:
                    date = str(int(ds[0]))
                except ValueError:
                    date = ''
                    album = dirname
                else:
                    album = ''.join(ds[1:])
            else:
                date = ''
                album = dirname
            date = convert2unicode(date)
            album = convert2unicode(album)

            # get DB values
            try:
                title_orig = convert2unicode(song['title'])
            except KeyError:
                title_orig = u''
            try:
                trackno_orig = convert2unicode(song['tracknumber'])
            except KeyError:
                trackno_orig = u''
            try:
                album_orig = convert2unicode(song['album'])
            except KeyError:
                album_orig = u''
            try:
                date_orig = convert2unicode(song['date'])
            except KeyError:
                date_orig = u''

            ans = ConfirmAction(None, "Change Song Info",
                         "<b>Filename:</b> %s\n"
                         "<b>Track:</b> %s -> %s\n"
                         "<b>Title:</b> %s -> %s\n"
                         "<b>Album:</b> %s ->. %s\n"
                         "<b>Date:</b> %s -> %s\n"
                         "\nIt will only update non empty values.\n" % \
                         (convert2unicode(filename),
                          trackno_orig, trackno, title_orig, title,
                          album_orig, album, date_orig, date)).run()
            if ans == True:
                if trackno: song['tracknumber'] = trackno
                if title: song['title'] = title
                if album: song['album'] = album
                if date: song['date'] = date
