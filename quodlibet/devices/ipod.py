# -*- coding: utf-8 -*-
# Copyright 2006 Markus Koller
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

try: import gpod
except ImportError: raise NotImplementedError

import os
import popen2
import time
import gtk

import const
import util

from devices._base import Device
from formats._audio import AudioFile
from qltk.entry import ValidatingEntry
from qltk.msg import ErrorMessage
from qltk.wlw import WaitLoadWindow

# Wraps an itdb_track from libgpod in an AudioFile instance
class IPodSong(AudioFile):
    is_file = False

    def __init__(self, track):
        super(IPodSong, self).__init__()
        self.sanitize(gpod.itdb_filename_on_ipod(track))
        self.itdb_track = track

        for key in ['artist', 'album', 'title', 'genre', 'grouping']:
            value = getattr(track, key)
            if value: self[key] = value
        for key in ['bitrate', 'playcount', 'year']:
            value = getattr(track, key)
            if value != 0: self['~#'+key] = value
        for key, value in {
            '~#disc': track.cd_nr,
            '~#discs': track.cds,
            '~#rating': track.rating / 100.0,
            '~#length': track.tracklen / 1000.0,
        }.items():
            if value != 0: self[key] = value
        self['~format'] = track.filetype
        self['tracknumber'] = "%d/%d" % (track.track_nr, track.tracks)

    def can_change(self, k=None): return []

class IPodDevice(Device):
    name = _("iPod")
    description = _("First to fifth generation iPods")
    icon = os.path.join(const.BASEDIR, "device-ipod.png")
    writable = True

    mountpoint = ""
    gain = 0.0
    covers = True

    __itdb = None

    def __init__(self):
        mountpoint = os.getenv('IPOD_MOUNTPOINT') # gtkpod uses this
        if mountpoint: self.mountpoint = mountpoint

    # We don't want to pickle the iTunesDB
    def __getstate__(self):
        self.__itdb = None
        return self.__dict__

    def Properties(self, dialog):
        entry = ValidatingEntry(os.path.ismount)
        entry.set_text(self.mountpoint)
        dialog.add_property(_("Mountpoint"), entry, 'mountpoint')

        spin = gtk.SpinButton()
        spin.set_range(-20, 20)
        spin.set_digits(1)
        spin.set_increments(0.1, 1)
        spin.set_value(float(self.gain))
        dialog.add_property(_("Volume gain (dB)"), spin, 'gain')

        check = gtk.CheckButton()
        check.set_active(self.covers)
        dialog.add_property(_("Copy album covers"), check, 'covers')

        if self.is_connected():
            details = self.__get_details()
            dialog.add_separator()
            dialog.add_property(_("Model"),
                details.get('model', '-'))
            dialog.add_property(_("Capacity"),
                details.get('space', '-'))
            dialog.add_property(_("Firmware Version"),
                details.get('firmware', '-'))

    def __get_details(self):
        details = {}

        try: file = open(os.path.join(self.mountpoint,
                         "iPod_Control", "Device", "SysInfo"))
        except IOError: return details

        while True:
            line = file.readline()
            if not line: break
            parts = line.split()
            if len(parts) == 0: continue

            parts[0] = parts[0].rstrip(":")
            if parts[0] == "ModelNumStr":
                info = self.__models.get(parts[1], ('-', '-'))
                details['model'], details['space'] = info
            elif parts[0] == "visibleBuildID":
                details['firmware'] = parts[2].strip("()")

        return details

    def is_connected(self):
        return os.path.ismount(self.mountpoint) and \
               os.path.isdir(os.path.join(self.mountpoint, "iPod_Control"))

    def eject(self):
        dev = self.__get_device()
        if dev:
            pipe = popen2.Popen4("eject %s" % dev)
            if pipe.wait() == 0: return True
            else: return pipe.fromchild.read()
        else:
            return _("Unable to find a device for %s") % self.mountpoint

    def __get_device(self):
        try: file = open("/etc/mtab")
        except IOError: return None

        while True:
            line = file.readline()
            parts = line.split()
            if len(parts) < 2: continue
            if parts[1] == self.mountpoint: return parts[0]
        else: return None

    def get_space(self):
        info = os.statvfs(self.mountpoint)
        space = info.f_bsize * info.f_blocks
        free = info.f_bsize * info.f_bavail
        return (space, free)

    def list(self, browser, rescan=False):
        songs = []
        if self.__load_db():
            for track in gpod.sw_get_tracks(self.__itdb):
                filename = gpod.itdb_filename_on_ipod(track)
                if filename: songs.append(IPodSong(track))
                else:
                    # Handle database corruption
                    self.__remove_track(track)
        return songs

    def __create_db(self):
        db = gpod.itdb_new();
        gpod.itdb_set_mountpoint(self.mountpoint)

        master = gpod.itdb_playlist_new('iPod', False)
        gpod.itdb_playlist_set_mpl(master)
        gpod.itdb_playlist_add(db, master, 0)

        return db

    def __load_db(self):
        if self.__itdb: return self.__itdb

        self.__itdb = gpod.itdb_parse(self.mountpoint, None)
        if not self.__itdb and self.is_connected() and qltk.ConfirmAction(
            qltk.get_top_parent(self), _("Uninitialized iPod"),
            _("Do you want to create an empty iTunesDB on this iPod?")
            ).run():
            self.__itdb = self.create_db()
        return self.__itdb

    def copy(self, songlist, song):
        track = gpod.itdb_track_new()

        # String keys, we only store the first one
        for key in ['artist', 'album', 'title', 'genre', 'grouping']:
            try: setattr(track, key, str(song.list(key)[0]))
            except: continue
        # Numeric keys
        for key in ['bitrate', 'playcount', 'year']:
            try: setattr(track, key, int(song('~#'+key)))
            except: continue
        # Keys where the names differ
        for key, value in {
            'cd_nr':         song('~#disc'),
            'cds':           song('~#discs'),
            'rating':        song('~#rating') * 100,
            'time_added':    self.__mactime(time.time()),
            'time_modified': self.__mactime(util.mtime(song('~filename'))),
            'track_nr':      song('~#track'),
            'tracklen':      song('~#length') * 1000,
            'tracks':        song('~#tracks'),
            'size':          util.size(song('~filename')),
            'soundcheck':    self.__soundcheck(song),
        }.items():
            try: setattr(track, key, int(value))
            except: continue
        track.filetype = song('~format')

        if self.covers:
            cover = song.find_cover()
            if cover: gpod.itdb_track_set_thumbnails(track, cover.name)

        # Add the track to the master playlist
        gpod.itdb_track_add(self.__itdb, track, -1)
        master = gpod.itdb_playlist_mpl(self.__itdb)
        gpod.itdb_playlist_add_track(master, track, -1)

        # Copy the actual file
        if gpod.itdb_cp_track_to_ipod(track, song['~filename'], None) == 1:
            return IPodSong(track)
        else:
            return False

    def __mactime(self, time):
        time = int(time)
        if time == 0: return time
        else: return time + 2082844800

    def __soundcheck(self, song):
        if 'replaygain_album_gain' in song:
            db = float(song['replaygain_album_gain'].split()[0])
        elif 'replaygain_track_gain' in song:
            db = float(song['replaygain_track_gain'].split()[0])
        else: db = 0.0

        soundcheck = int(round(1000 * 10.**(-0.1 * (db + float(self.gain)))))
        return soundcheck

    def delete(self, songlist, song):
        try:
            track = song.itdb_track
            filename = gpod.itdb_filename_on_ipod(track)
            if filename: os.remove(filename)
            self.__remove_track(track)
        except IOError, exc: return exc.args[-1]
        else: return True

    def __remove_track(self, track):
        master = gpod.itdb_playlist_mpl(self.__itdb)
        gpod.itdb_playlist_remove_track(master, track)
        gpod.itdb_track_remove(track)

    def cleanup(self, wlw, action):
        wlw._WaitLoadWindow__text = _("<b>Saving iPod database...</b>")
        wlw.count = 0
        wlw.step()
        if gpod.itdb_write(self.__itdb, None) != 1:
            ErrorMessage(browser, _("Unable to save iPod database"),
                _("The song database could not be saved on your iPod.")).run()

    # This list is taken from
    # http://en.wikipedia.org/wiki/List_of_iPod_model_numbers
    __models = {
        # First Generation
        'M8513': ('iPod', '5GB'),
        'M8541': ('iPod', '5GB'),
        'M8697': ('iPod', '5GB'),
        'M8709': ('iPod', '10GB'),
        # Second Generation
        'M8737': ('iPod', '10GB'),
        'M8740': ('iPod', '10GB'),
        'M8738': ('iPod', '20GB'),
        'M8741': ('iPod', '20GB'),
        # Third Generation
        'M8976': ('iPod', '10GB'),
        'M8946': ('iPod', '15GB'),
        'M9460': ('iPod', '15GB'),
        'M9244': ('iPod', '20GB'),
        'M8948': ('iPod', '30GB'),
        'M9245': ('iPod', '40GB'),
        # Fourth Generation
        'M9282': ('iPod', '20GB'),
        'M9787': ('iPod (U2 edition)', '20GB'),
        'M9268': ('iPod', '40GB'),
        # Photo / Fourth Generation
        'MA079': ('iPod photo', '20GB'),
        'MA127': ('iPod photo (U2 edition)', '20GB'),
        'M9829': ('iPod photo', '30GB'),
        'M9585': ('iPod photo', '40GB'),
        'M9586': ('iPod photo', '60GB'),
        'M9830': ('iPod photo', '60GB'),
        # Shuffle / Fourth Generation
        'M9724': ('iPod shuffle', '512MB'),
        'M9725': ('iPod shuffle', '1GB'),
        'MA133': ('iPod shuffle', '512MB'),
        # Video / Fifth Generation
        'MA002': ('iPod video white', '30GB'),
        'MA146': ('iPod video black', '30GB'),
        'MA003': ('iPod video white', '60GB'),
        'MA147': ('iPod video black', '60GB'),
        # Nano / Fifth Generation
        'MA350': ('iPod nano white', '1GB'),
        'MA352': ('iPod nano black', '1GB'),
        'MA004': ('iPod nano white', '2GB'),
        'MA099': ('iPod nano black', '2GB'),
        'MA005': ('iPod nano white', '4GB'),
        'MA107': ('iPod nano black', '4GB'),
        # First Generation Mini
        'M9160': ('iPod mini silver', '4GB'),
        'M9436': ('iPod mini blue', '4GB'),
        'M9435': ('iPod mini pink', '4GB'),
        'M9434': ('iPod mini green', '4GB'),
        'M9437': ('iPod mini gold', '4GB'),
        # Second Generation Mini
        'M9800': ('iPod mini silver', '4GB'),
        'M9802': ('iPod mini blue', '4GB'),
        'M9804': ('iPod mini pink', '4GB'),
        'M9806': ('iPod mini green', '4GB'),
        'M9801': ('iPod mini silver', '6GB'),
        'M9803': ('iPod mini blue', '6GB'),
        'M9805': ('iPod mini pink', '6GB'),
        'M9807': ('iPod mini green', '6GB'),
    }
