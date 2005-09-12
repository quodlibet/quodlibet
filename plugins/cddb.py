# Copyright 2005 Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import CDDB
import os
from os import path
import gtk
from qltk import ErrorMessage, ConfirmAction, Message
from util import tag, escape
from gettext import ngettext

PLUGIN_NAME = 'CDDB lookup'
PLUGIN_DESC = 'Look up album information in FreeDB (requires CDDB.py)'
PLUGIN_ICON = 'gtk-cdrom'

__all__ = []

class AskAction(ConfirmAction):
    """A message dialog that asks a yes/no question."""
    def __init__(self, *args, **kwargs):
        kwargs["buttons"] = gtk.BUTTONS_YES_NO
        Message.__init__(self, gtk.MESSAGE_QUESTION, *args, **kwargs)


def sumdigits(n): return sum(map(long, str(n)))

def calculate_discid(album):
    lengths = [song['~#length'] for song in album]
    total_time = 0
    offsets = []
    for length in lengths:
        offsets.append(total_time)
        total_time += length
    checksum = sum(map(sumdigits, offsets))
    discid = ((checksum % 0xff) << 24) | (total_time << 8) | len(album)
    return [discid, len(album)] + [75 * o for o in offsets] + [total_time]

def query(category, discid):
    discinfo = {}
    tracktitles = {}
    dump = path.join(path.expanduser("~"), '.cddb', discid)
    try:
        for line in file(dump):
            if line.startswith("TTITLE"):
                track, title = line.split("=", 1)
                try: track = int(track[6:])
                except (ValueError): pass
                else: tracktitles[track] = \
                        title.decode('utf-8', 'replace').strip()
            elif line.startswith("DGENRE"):
                discinfo['genre'] = line.split('=', 1)[1].strip()
            elif line.startswith("DTITLE"):
                dtitle = line.split('=', 1)[1].strip().split(' / ', 1)
                if len(dtitle) == 2:
                    discinfo['artist'], discinfo['title'] = dtitle
                else:
                    discinfo['title' ] = dtitle
            elif line.startswith("DYEAR"):
                discinfo['year'] = line.split('=', 1)[1].strip()
    except EnvironmentError: pass
    else: return discinfo, tracktitles

    read, info = CDDB.read(category, discid)
    if read != 210: return None

    try: os.makedirs(path.join(path.expanduser("~"), '.cddb'))
    except EnvironmentError: pass
    try:
        save = file(dump, 'wU')
        keys = info.keys()
        keys.sort()
        for key in keys:
            print>>save, "%s=%s" % (key, info[key])
        save.close()
    except EnvironmentError: pass

    for key, value in info.iteritems():
        try: value = value.decode('utf-8', 'replace').strip()
        except AttributeError: pass
        if key.startswith('TTITLE'):
            try: tracktitles[int(key[6:])] = value
            except ValueError: pass
        elif key == 'DGENRE': discinfo['genre'] = value
        elif key == 'DTITLE':
            dtitle = value.strip().split(' / ', 1)
            if len(dtitle) == 2: discinfo['artist'], discinfo['title'] = dtitle
            else: discinfo['title' ] = dtitle
        elif key == 'DYEAR': discinfo['year'] = value

    return discinfo, tracktitles

def ask_save_info((disc, track), album):
    message = []

    if 'artist' in disc:
        message.append('%s:\t<b>%s</b>' % (tag("artist"), escape(disc['artist'])))
    if 'title' in disc:
        message.append('%s:\t<b>%s</b>' % (tag("album"), escape(disc['title'])))
    if 'year' in disc:
        message.append('%s:\t<b>%s</b>' % (tag("date"), escape(disc['year'])))
    if 'genre' in disc:
        message.append('%s:\t<b>%s</b>' % (tag("genre"), escape(disc['genre'])))

    message.append('\n<u>%s</u>' % _('Track List'))
    keys = track.keys()
    keys.sort()
    for key in keys:
        message.append('    <b>%d.</b> %s' % (key+1,
            escape(track[key].encode('utf-8'))))

    if AskAction(None, _("Save the following information?"),
            '\n'.join(message)).run():

        for key, song in zip(keys, album):
            song['title'] = track[key]
            song['tracknumber'] = '%d/%d' % (key+1, len(album))
            if 'artist' in disc: song['artist'] = disc['artist']
            if 'title' in disc: song['album'] = disc['title']
            if 'year' in disc: song['date'] = disc['year']
            if 'genre' in disc: song['genre'] = disc['genre']

def plugin_album(album):
    album.sort()

    discid = calculate_discid(album)

    stat, discs = CDDB.query(discid)
    info = None
    if stat in (200,211):
        info = query(discs[0]['category'], discs[0]['disc_id'])

    if not info:
        n = len(album)
        albumname = album[0]('album')
        if not albumname: albumname = ngettext('%d track', '%d tracks', n) % n
        ErrorMessage(None, _("CDDB lookup failed"),
                ngettext("%(title)s and %(count)d more...",
                    "%(title)s and %(count)d more...", n-1) % {
                    'title': album[0]('~basename'), 'count': n-1}).run()
        return

    ask_save_info(info, album)
