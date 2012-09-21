# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import struct

from quodlibet.formats._audio import AudioFile


class MidiError(Exception):
    pass


class MidiFile(AudioFile):
    format = "MIDI"
    mimes = ["audio/midi", "audio/x-midi"]

    def __init__(self, filename):
        h = open(filename, "rb")
        try:
            if h.read(4) != "MThd":
                raise MidiError("Not a Midi file")
            h.seek(0, 0)
            try:
                self["~#length"] = read_midi_length(h)
            except Exception:
                pass
        finally:
            h.close()

        self.sanitize(filename)

    def write(self):
        pass

    def reload(self, *args):
        title = self.get("title")
        super(MidiFile, self).reload(*args)
        if title is not None:
            self.setdefault("title", title)

    def can_change(self, k=None):
        if k is None:
            return ["title"]
        else:
            return k == "title"

info = MidiFile
types = [MidiFile]
extensions = [".mid"]


TEMPO, MIDI = range(2)


def var_int(string):
    val = 0
    i = 0
    while 1:
        x = ord(string[i])
        i += 1
        val = (val << 7) + (x & 0x7F)
        if not (x & 0x80):
            return val, i


def read_track(chunk):
    """Retuns a list of midi events and tempo change events"""

    # Deviations: The running status should be reset on non midi events, but
    # some files contain meta events inbetween.
    # Offset and time signature are not used.

    tempos = []
    events = []

    deltasum = 0
    status = ""
    while chunk:
        delta, i = var_int(chunk)
        deltasum += delta
        chunk = chunk[i:]
        event_type = chunk[0]
        if event_type == "\xFF":
            num, i = var_int(chunk[2:])
            size = 2 + i + num
            data = chunk[size - num:size]
            # TODO: support offset/time signature
            if chunk[1] == "\x51":
                tempo = struct.unpack(">I", "\x00" + data)[0]
                tempos.append((deltasum, TEMPO, tempo))
            chunk = chunk[size:]
        elif event_type in ("\xF0", "\xF7"):
            chunk = chunk[1 + sum(var_int(chunk[1:])):]
        else:
            # if < 0x80 take the type from the previous midi event
            event_num = ord(event_type)
            if event_num < 0x80:
                offset = -1
                event_num = ord(status)
            elif event_num >= 0xF0:
                # garbage... better stop
                break
            else:
                offset = 0
                status = event_type

            events.append((deltasum, MIDI, delta))

            if event_num >> 4 in (0xD, 0xC):
                chunk = chunk[2 + offset:]
            else:
                chunk = chunk[3 + offset:]

    return events, tempos


def read_midi_length(fileobj):
    """Returns the duration in seconds. Can raise all kind of errors..."""

    def read_chunk(fileobj):
        info = fileobj.read(8)
        chunklen = struct.unpack(">I", info[4:])[0]
        return info[:4], fileobj.read(chunklen)

    identifier, chunk = read_chunk(fileobj)
    if identifier != "MThd":
        raise MidiError("Not a MIDI file")

    format_ = struct.unpack(">H", chunk[:2])[0]
    if format_ > 1:
        raise MidiError("Not supported format %d" % format_)
    ntracks = struct.unpack(">H", chunk[2:4])[0]
    tickdiv = struct.unpack(">H", chunk[4:6])[0]
    if tickdiv >> 15:
        # fps = (-(tickdiv >> 8)) & 0xFF
        # subres = tickdiv & 0xFF
        # never saw one of those
        raise MidiError("Not supported timing interval")

    # get a list of events and tempo changes for each track
    tracks = []
    first_tempos = None
    for tracknum in xrange(ntracks):
        identifier, chunk = read_chunk(fileobj)
        if identifier != "MTrk":
            break
        events, tempos = read_track(chunk)

        # In case of format == 1, copy the first tempo list to all tracks
        first_tempos = first_tempos or tempos
        if format_ == 1:
            tempos = list(first_tempos)
        events += tempos
        events.sort()
        tracks.append(events)

    # calculate the duration of each track
    durations = []
    for events in tracks:
        tempo = 500000
        parts = []
        deltasum = 0
        for (dummy, type_, data) in events:
            if type_ == TEMPO:
                parts.append((deltasum, tempo))
                tempo = data
                deltasum = 0
            else:
                deltasum += data
        parts.append((deltasum, tempo))

        duration = 0
        for (deltasum, tempo) in parts:
            quarter, tpq = deltasum / float(tickdiv), tempo
            duration += (quarter * tpq)
        duration /= 10 ** 6

        durations.append(duration)

    # return the longest one
    return max(durations)
