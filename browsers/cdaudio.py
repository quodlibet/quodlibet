# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

# Serious props to James Livingston; much of this comes from his
# implementation of CD audio support for Rhythmbox.

import gobject, gtk, gst
from formats.remote import RemoteFile
from browsers._base import Browser
drive = gst.element_make_from_uri(gst.URI_SRC, "cdda://", "")

gst.FORMAT_TRACK = 6

class CDDAPipeline(gst.Pipeline):
    def __init__(self):
        super(CDDAPipeline, self).__init__()
        self.cdda = gst.element_make_from_uri(gst.URI_SRC, "cdda://", "")
        self.sink = gst.element_factory_make("fakesink")
        self.cdda.link(self.sink)
        self.add_many(self.sink, self.cdda)

    tracks = property(
        lambda s: s.cdda.query(gst.QUERY_TOTAL, gst.FORMAT_TRACK))
    device = property(lambda s: s.cdda.get_property('device'))
    discid = property(lambda s: s.cdda.get_property('discid'))

class CDAudio(Browser, gtk.Label):
    __gsignals__ = Browser.__gsignals__

    def __init__(self, main):
        super(CDAudio, self).__init__(_("Unknown CD"))
        self.show_all()
        self.activate()

    def __make_tracks(self, bin):
        tracks = []
        for track in range(1, bin.tracks + 1):
            uri = "cdda://%d" % track
            f = RemoteFile(uri)
            f["title"] = "Track %d" % track
            f["tracknumber"] = "%d/%d" % (track, bin.tracks)
            f["album"] = bin.discid
            event = gst.event_new_seek(gst.FORMAT_TRACK|gst.SEEK_METHOD_SET|
                                       gst.SEEK_FLAG_FLUSH, track - 1)
            result = bin.sink.send_event(event)
            if result:
                length = bin.sink.query(gst.QUERY_TOTAL, gst.FORMAT_TIME)
                if length: f["~#length"] = length / gst.SECOND

            tracks.append(f)
        return tracks

    def activate(self):
        pipe = CDDAPipeline()
        pipe.set_state(gst.STATE_PAUSED)
        tracks = self.__make_tracks(pipe)
        self.set_text("%s %s" % (pipe.device, pipe.discid))
        self.emit('songs-selected', tracks, None)

    def restore(self): pass
gobject.type_register(CDAudio)

if drive: browsers = [(100, _("CD Audio"), CDAudio, False)]
else: browsers = []
del(drive)

