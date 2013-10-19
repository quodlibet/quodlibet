# Copyright 2005 Michael Urman
#           2013 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

try:
    import CDDB
except ImportError as e:
    from quodlibet import plugins
    raise (plugins.MissingModulePluginException("cddb") if
           hasattr(plugins, "MissingModulePluginException") else e)

import os
from os import path
from gi.repository import Gtk

from quodlibet.qltk import ErrorMessage, ConfirmAction, Message
from quodlibet.const import VERSION
from quodlibet.util import tag, escape
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.util.path import expanduser

CDDB.proto = 6 # utf8 instead of latin1
CLIENTINFO = {'client_name': "quodlibet", 'client_version': VERSION}


class AskAction(ConfirmAction):
    """A message dialog that asks a yes/no question."""
    def __init__(self, *args, **kwargs):
        kwargs["buttons"] = Gtk.ButtonsType.YES_NO
        Message.__init__(self, Gtk.MessageType.QUESTION, *args, **kwargs)


def sumdigits(n):
    return sum(map(long, str(n)))


def calculate_discid(album):
    lengths = [song.get('~#length', 0) for song in album]
    total_time = 0
    offsets = []
    for length in lengths:
        offsets.append(total_time)
        total_time += length
    checksum = sum(map(sumdigits, offsets))
    discid = ((checksum % 0xff) << 24) | (total_time << 8) | len(album)
    return [discid, len(album)] + [75 * o for o in offsets] + [total_time]


def query(category, discid, xcode='utf8:utf8'):
    discinfo = {}
    tracktitles = {}
    dump = path.join(expanduser("~"), '.cddb', category, discid)
    try:
        for line in file(dump):
            if line.startswith("TTITLE"):
                track, title = line.split("=", 1)
                try:
                    track = int(track[6:])
                except (ValueError):
                    pass
                else:
                    tracktitles[track] = \
                        title.decode('utf-8', 'replace').strip()
            elif line.startswith("DGENRE"):
                discinfo['genre'] = line.split('=', 1)[1].strip()
            elif line.startswith("DTITLE"):
                dtitle = line.split('=', 1)[1].strip().split(' / ', 1)
                if len(dtitle) == 2:
                    discinfo['artist'], discinfo['title'] = dtitle
                else:
                    discinfo['title'] = dtitle[0].strip()
            elif line.startswith("DYEAR"):
                discinfo['year'] = line.split('=', 1)[1].strip()
    except EnvironmentError:
        pass
    else:
        return discinfo, tracktitles

    read, info = CDDB.read(category, discid, **CLIENTINFO)
    if read != 210:
        return None

    try:
        os.makedirs(path.join(expanduser("~"), '.cddb'))
    except EnvironmentError:
        pass
    try:
        save = file(dump, 'w')
        keys = info.keys()
        keys.sort()
        for key in keys:
            print>>save, "%s=%s" % (key, info[key])
        save.close()
    except EnvironmentError:
        pass

    xf, xt = xcode.split(':')
    for key, value in info.iteritems():
        try:
            value = value.decode('utf-8', 'replace').strip().encode(
                xf, 'replace').decode(xt, 'replace')
        except AttributeError:
            pass
        if key.startswith('TTITLE'):
            try:
                tracktitles[int(key[6:])] = value
            except ValueError:
                pass
        elif key == 'DGENRE':
            discinfo['genre'] = value
        elif key == 'DTITLE':
            dtitle = value.strip().split(' / ', 1)
            if len(dtitle) == 2:
                discinfo['artist'], discinfo['title'] = dtitle
            else:
                discinfo['title'] = dtitle[0].strip()
        elif key == 'DYEAR':
            discinfo['year'] = value

    return discinfo, tracktitles


def make_info_label((disc, track), album, discid):
    message = []

    if 'artist' in disc:
        message.append('%s:\t<b>%s</b>' % (
            tag("artist"), escape(disc['artist'])))
    if 'title' in disc:
        message.append('%s:\t<b>%s</b>' % (
            tag("album"), escape(disc['title'])))
    if 'year' in disc:
        message.append('%s:\t<b>%s</b>' % (tag("date"), escape(disc['year'])))
    if 'genre' in disc:
        message.append('%s:\t<b>%s</b>' % (
            tag("genre"), escape(disc['genre'])))
    if discid:
        message.append('%s:\t<b>%s</b>' % (tag("CDDB ID"), escape(discid)))

    message.append('\n<u>%s</u>' % _('Track List'))
    keys = track.keys()
    keys.sort()
    for key in keys:
        message.append('    <b>%d.</b> %s' % (key + 1,
            escape(track[key].encode('utf-8'))))

    return '\n'.join(message)


class CDDBLookup(SongsMenuPlugin):
    PLUGIN_ID = 'CDDB lookup'
    PLUGIN_NAME = _('CDDB Lookup')
    PLUGIN_DESC = 'Look up album information in FreeDB (requires CDDB.py)'
    PLUGIN_ICON = 'gtk-cdrom'

    def plugin_album(self, album):
        discid = calculate_discid(album)

        try:
            stat, discs = CDDB.query(discid, **CLIENTINFO)
        except IOError:
            ErrorMessage(None, _("Timeout"), _(
                "Query could not be executed, connection timed out")).run()
            return

        if stat in (200, 211):
            xcode = 'utf8:utf8'
            dlg = Gtk.Dialog(_('Select an album'))
            dlg.set_border_width(6)
            dlg.set_has_separator(False)
            dlg.set_resizable(False)
            dlg.add_buttons(Gtk.STOCK_OK, Gtk.ResponseType.OK)
            dlg.vbox.set_spacing(6)
            dlg.set_default_response(Gtk.ResponseType.OK)
            model = Gtk.ListStore(str, str, str, str, str, str)
            for disc in discs:
                model.append(
                    [disc[s] for s in ('title', 'category', 'disc_id')] * 2)
            box = Gtk.ComboBox(model)
            box.set_active(0)
            for i in range(3):
                crt = Gtk.CellRendererText()
                box.pack_start(crt, True, True, 0)
                box.set_attributes(crt, text=i)
            discinfo = Gtk.Label()
            crosscode = Gtk.ListStore(str)
            crosscode.append(['utf8:utf8'])
            crosscode.append(['latin1:latin2'])
            crosscode.append(['latin1:cp1251'])
            crosscode.append(['latin1:sjis'])
            crosscode.append(['latin1:euc-jp'])
            cbo = Gtk.ComboBoxEntry(crosscode, column=0)
            cbo.set_active(0)

            def update_discinfo(combo):
                xcode = cbo.get_child().get_text()
                model = combo.get_model()
                t, c, d, title, cat, discid = model[box.get_active()]
                info = query(cat, discid, xcode=xcode)
                discinfo.set_markup(
                    make_info_label(info, album, discs[0]['disc_id']))

            def crosscode_cddbinfo(combo):
                try:
                    xf, xt = combo.get_child().get_text().split(':')
                    for row in model:
                        for show, store in zip(range(0, 3), range(3, 6)):
                            row[show] = row[store].encode(
                                xf, 'replace').decode(xt, 'replace')
                except:
                    for row in model:
                        for show, store in zip(range(0, 3), range(3, 6)):
                            row[show] = row[store]
                update_discinfo(box)

            cbo.connect('changed', crosscode_cddbinfo)
            box.connect('changed', update_discinfo)
            update_discinfo(box)
            dlg.vbox.pack_start(Gtk.Label(
                _("Select the album you wish to retrieve.", True, True, 0)))
            dlg.vbox.pack_start(box, True, True, 0)
            dlg.vbox.pack_start(discinfo, True, True, 0)
            dlg.vbox.pack_start(cbo, True, True, 0)
            dlg.vbox.show_all()
            resp = dlg.run()

            xcode = cbo.get_child().get_text()
            if resp == Gtk.ResponseType.OK:
                t, c, d, title, cat, discid = model[box.get_active()]
                (disc, track) = query(cat, discid, xcode=xcode)
                keys = track.keys()
                keys.sort()
                for key, song in zip(keys, album):
                    if 'artist' in disc:
                        song['artist'] = disc['artist']
                    if 'title' in disc:
                        song['album'] = disc['title']
                    if 'year' in disc:
                        song['date'] = disc['year']
                    if 'genre' in disc:
                        song['genre'] = disc['genre']
                    s = track[key].split("/")
                    if len(s) == 2:
                        song['artist'] = s[0]
                        song['title'] = s[1]
                    else:
                        song['title'] = track[key]
                    song['tracknumber'] = '%d/%d' % (key + 1, len(album))
            dlg.destroy()
        else:
            n = len(album)
            albumname = album[0]('album')
            if not albumname:
                albumname = ngettext('%d track', '%d tracks', n) % n
            ErrorMessage(None, _("CDDB lookup failed (%s)" % stat),
                    ngettext("%(title)s and %(count)d more...",
                        "%(title)s and %(count)d more...", n - 1) % {
                        'title': album[0]('~basename'), 'count':
                        n - 1}).run()
