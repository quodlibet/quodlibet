#! /usr/bin/env python
#
#    VorbisGain plugin for Quod Libet
#    Copyright (C) 2005  Michael Urman
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of version 2 of the GNU General Public License as
#    published by the Free Software Foundation.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#

import gtk, pango, gobject, os, sre

from _subprocobj import Subprocess
from plugins.songsmenu import SongsMenuPlugin

VORBIS_PROGRESS = sre.compile(r'(?P<percent>\d+)% - (?P<file>.+)')
VORBIS_ALBUM = sre.compile(r'Recommended Album Gain:\s+(?P<albumgain>[-+]?\d+\.\d+)\s+dB')
VORBIS_TRACK = sre.compile(r'(?P<gain>[-+]?\d\.\d+) dB \|\s+(?P<peak>\d+) \|\s+(?P<scale>\d+\.\d+) \|\s+(?P<newpeak>\d+) \| (?P<file>.+)')

MP3_PROGRESS = sre.compile(r' (?P<file>.+?)\s+(?P<percent>\d+)% done, ETA.+batch')
MP3_ALBUM = sre.compile(r'(?P<gain>[-+]?\d+\.\d+)dB\s+volume adjustment')
MP3_TRACK = sre.compile(r'(?P<level>[-+]?\d+\.\d+)dBFS\s+(?P<peak>[-+]?\d+\.\d+)dBFS\s+(?P<gain>[-+]?\d+\.\d+)dB\s+(?P<file>.+)')

__all__ = ['ReplayGain']

class ReplayGain(SongsMenuPlugin):

    PLUGIN_ID = 'ReplayGain'
    PLUGIN_NAME = 'Replay Gain'
    PLUGIN_DESC = ('Invokes vorbisgain or normalize-audio on selected '
                   'songs, grouped by album')
    PLUGIN_ICON = gtk.STOCK_CDROM
    PLUGIN_VERSION = "0.16"

    class VorbisGainer(object):
        def __init__(self, gain):
            self.gain = gain
            self.command = ['vorbisgain']
            self.args = ['--album', '--skip', ]#'--display-only']

        def run(self, songs):
            files = [song['~filename'] for song in songs]
            win = self.gain.get_window()
            win.process = Subprocess(
                self.command + self.args + files, newlines='\r\n')
            win.ids = [
                win.process.connect(
                'output-line', self.__output, song('album')),
                win.process.connect('output-eof', self.__eof),
            ]
            self.complete = False
            win.process.start()

        def __output(self, process, fd, line, album,
                     progressre=VORBIS_PROGRESS,
                     trackre=VORBIS_TRACK, albumre=VORBIS_ALBUM):

            match = progressre.search(line)
            if match:
                d = match.groupdict()
                p = d.get('percent','')
                f = d.get('file', '')
                self.gain.update_song(f, percent=p)

            match = trackre.search(line)
            if match:
                d = match.groupdict()
                g = d.get('gain', '')
                f = d.get('file', '')
                self.gain.update_song(f, gain=g)

            match = albumre.search(line)
            if match:
                d = match.groupdict()
                g = d.get('albumgain')
                self.gain.update_album(album, gain=g)

        def __eof(self, process, fd):
            self.gain.set_buttons(True)
            self.gain.complete = True

    class MP3Gainer(object):
        def __init__(self, gain):
            self.gain = gain
            self.command = ['normalize-audio']
            self.args1 = ['-n']
            self.args2 = ['-n', '-b']

        def run(self, songs):
            files = [song['~filename'] for song in songs]
            self.__files = [(song('~basename'), song['~filename'], song)
                            for song in songs]
            win = self.gain.get_window()
            win.process = Subprocess(self.command + self.args1 + files,
                    newlines='\r\n')
            win.ids = [
                win.process.connect(
                'output-line', self.__output, song('album')),
                win.process.connect('output-eof', self.__eof1),
            ]
            self.__set_album = False
            self.complete = False
            win.process.start()

            while not self.complete: gtk.main_iteration()
            self.complete = 100
            for id in win.ids: win.process.disconnect(id)

            win.process = Subprocess(
                self.command + self.args2 + files, newlines='\r\n')
            win.ids = [
                win.process.connect(
                'output-line', self.__output, song('album')),
                win.process.connect('output-eof', self.__eof2),
            ]
            win.process.start()

        def __match_file(self, shortfile):
            if not shortfile: return shortfile, None
            for b, f, s in self.__files:
                if b.startswith(shortfile): return f, s
            for b, f, s in self.__files:
                if f == shortfile: return f, s
            return shortfile, None

        def __output(self, process, fd, line, album, progressre=MP3_PROGRESS,
                     trackre=MP3_TRACK, albumre=MP3_ALBUM):

            match = progressre.search(line)
            if match:
                d = match.groupdict()
                p = str(int((int(d.get('percent',''))+self.complete)*0.5))
                f, s = self.__match_file(d.get('file', ''))
                return self.gain.update_song(f, percent=p)
            
            match = trackre.search(line)
            if match:
                try:
                    d = match.groupdict()
                    g = d.get('gain', '')
                    f, s = self.__match_file(d.get('file', ''))
                    self.gain.update_song(f, gain=g)
                    s['replaygain_track_gain'] = g + ' dB'
                    s['replaygain_track_peak'] = '0' # unsupported; required
                except:
                    from traceback import print_exc
                    print_exc()
                return

            match = albumre.search(line)
            if match:
                d = match.groupdict()
                g = d.get('gain')
                self.__set_album = True
                self.gain.update_album(album, gain=g)
                for b, f, s in self.__files:
                    s['replaygain_album_gain'] = g + ' dB'
                    s['replaygain_album_peak'] = '0' # unsupported; required
                return

        def __eof1(self, process, fd):
            self.complete = True

        def __eof2(self, process, fd):
            if not self.__set_album:
                for b, f, s in self.__files:
                    s['replaygain_album_peak'] = '0'
                    s['replaygain_album_gain'] = '0'
            self.gain.set_buttons(True)
            self.gain.complete = True

    def get_window(self):
        try: return ReplayGain.win
        except AttributeError: pass

        win = gtk.Dialog(title='ReplayGain',
                buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                    gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
        win.set_default_size(400, 300)
        win.set_border_width(6)
        swin = gtk.ScrolledWindow()
        win.vbox.pack_start(swin)
        swin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        swin.set_shadow_type(gtk.SHADOW_IN)
        from qltk.views import HintedTreeView
        ReplayGain.model = gtk.ListStore(object, str, str, int, str, str)
        ReplayGain.view = view = HintedTreeView(ReplayGain.model)
        swin.add(view)

        columns = [gtk.TreeViewColumn(n.title()) for n in 
                    ['track', 'progress', 'gain', 'album']]
        for col in columns:
            col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            col.set_resizable(True)
            view.append_column(col)
        columns[0].set_expand(True)
        columns[0].set_fixed_width(1)

        def add(render, col, **kw):
            expand = not isinstance(render, gtk.CellRendererPixbuf)
            col.pack_start(render, expand=expand)
            if col.get_title() == "Track" and expand:
                render.set_property('ellipsize', pango.ELLIPSIZE_END)
            for k, v in kw.items():
                col.add_attribute(render, k, v)

        add(gtk.CellRendererPixbuf(), columns[0], stock_id=1)
        add(gtk.CellRendererText(), columns[0], text=2)
        add(gtk.CellRendererProgress(), columns[1], value=3)
        add(gtk.CellRendererText(), columns[2], text=4)
        add(gtk.CellRendererText(), columns[3], text=5)

        ReplayGain.win = win
        win.ids = []
        win.connect('response', self.__response)
        win.connect('delete-event', self.__delete)
        return win

    def add_song(self, song):
        if song('~basename').endswith('.ogg'): pixbuf = gtk.STOCK_CDROM
        elif song('~basename').endswith('.mp3'): pixbuf = gtk.STOCK_CDROM
        else: pixbuf = gtk.STOCK_DIALOG_WARNING
        self.model.append(
            [song, pixbuf, song('~tracknumber~title~version'), 0, 0, 0])

    def update_song(self, song, percent=None, gain=None):
        if not percent and not gain: return
        for row in self.model:
            if row[0]('~filename') == song:
                self.view.scroll_to_cell(row.path)
                if percent: row[3] = int(percent)
                if gain: row[4] = gain
                break

    def update_album(self, album, gain):
        for row in self.model:
            if row[0]('album') == album:
                row[5] = gain

    def set_buttons(self, to):
        try:
            buttons = self.win.vbox.get_children()[2].get_children()
        except IndexError:
            pass
        else:
            buttons[0].set_sensitive(to)
            buttons[1].set_sensitive(not to)

    def plugin_album(self, songs):
        win = self.get_window()
        win.show_all()
        self.complete = True

        songs.sort()

        for song in songs: self.add_song(song)

        mp3s = [ song for song in songs if song('~basename').endswith('.mp3')]
        oggs = [ song for song in songs if song('~basename').endswith('.ogg')]

        if len(mp3s) == len(songs): gainer = self.MP3Gainer(self)
        elif len(oggs) == len(songs): gainer = self.VorbisGainer(self)
        else: return

        self.set_buttons(False)

        self.complete = False
        gainer.run(songs)

        while not self.complete: gtk.main_iteration()
        
        self.complete = False

    def __delete(self, win, event):
        self.__response(win, gtk.RESPONSE_CANCEL)
        return True

    def __response(self, win, response):
        win.hide()
        self.model.clear()
        if response != gtk.RESPONSE_CLOSE and not self.complete:
            import signal
            os.kill(win.process.pid, signal.SIGKILL)
            win.process.wait()
        for id in win.ids: win.process.disconnect(id)
        del win.ids[:]
        self.complete = True

