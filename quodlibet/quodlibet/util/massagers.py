# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import locale
import re

class Massager(object):
    """Massage a tag value from various 'okay' formats to the
    'correct' format."""

    tags = []
    error = "Metaerror. This should be overridden in subclasses."
    def validate(self, value):
        raise NotImplementedError

class DateMassager(Massager):
    tags = ["date"]
    error = _("The date must be entered in 'YYYY', 'YYYY-MM-DD' or "
              "'YYYY-MM-DD HH:MM:SS' format.")
    __match = re.compile(r"^\d{4}([-.]\d{2}([-.]\d{2}([T ]\d{2}"
                          "([:.]\d{2}([:.]\d{2})?)?)?)?)?$").match
    def validate(self, value):
        value = value.strip().replace(".", "-").replace("/", "-")
        return self.__match(value) and value

class GainMassager(Massager):
    tags = ["replaygain_album_gain", "replaygain_track_gain"]
    error = _("Replay Gain gains must be entered in 'x.yy dB' format.")
    __match = re.compile(r"^[+-]\d+\.?\d+?\s+dB$").match

    def validate(self, value):
        if self.__match(value): return value
        else:
            try: f = float(value.split()[0])
            except (IndexError, TypeError, ValueError):
                try: f = locale.atof(value.split()[0])
                except (IndexError, TypeError, ValueError): return False
            else: return ("%+f" % f).rstrip("0") + " dB"

class PeakMassager(Massager):
    tags = ["replaygain_album_peak", "replaygain_track_peak"]
    error = _("Replay Gain peaks must be entered in 'x.yy' format.")
    def validate(self, value):
        value = value.strip()
        try: f = float(value)
        except (TypeError, ValueError):
            try: f = locale.atof(value)
            except (TypeError, ValueError): return False
        else: return (f >= 0) and (f < 2) and str(f)

class MBIDMassager(Massager):
    tags = ["musicbrainz_trackid", "musicbrainz_albumid",
            "musicbrainz_artistid", "musicbrainz_albumartistid",
            "musicbrainz_trmid", "musicip_puid"]
    error = _("MusicBrainz IDs must be in UUID format.")
    def validate(self, value):
        value = value.encode('ascii', 'replace')
        value = filter(str.isalnum, value.strip().lower())
        try: int(value, 16)
        except ValueError: return False
        else:
            if len(value) != 32: return False
            else: return "-".join([value[:8], value[8:12], value[12:16],
                                   value[16:20], value[20:]])

class MBAlbumStatus(Massager):
    tags = ["musicbrainz_albumstatus"]
    # Translators: Leave "official", "promotional", and "bootleg"
    # untranslated. They are the three possible literal values.
    error = _("MusicBrainz release status must be 'official', "
              "'promotional', or 'bootleg'.")
    def validate(self, value):
        return value in ["official", "promotional", "bootleg"] and value

tags = {}
for f in globals().values():
    if isinstance(f, type) and issubclass(f, Massager):
        for t in f.tags:
            tags[t] = f()
del(f)
del(t)
