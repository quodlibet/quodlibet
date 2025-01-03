# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import xml.sax
from senf import fsn2uri

from quodlibet.formats import AudioFile

from tests.helper import temp_filename
from quodlibet.library import SongFileLibrary
from quodlibet.util.path import find_mount_point
from . import PluginTestCase


def get_example_xml(song_path, rating, lastplayed):
    song_uri = fsn2uri(song_path)
    mount_uri = fsn2uri(find_mount_point(song_path))

    return (
        """\
<?xml version="1.0" standalone="yes"?>
<rhythmdb version="1.9">
  <entry type="song">
    <title>Music</title>
    <genre>Unknown</genre>
    <track-number>7</track-number>
    <duration>199</duration>
    <file-size>4799124</file-size>
    <location>%s</location>
    <mountpoint>%s</mountpoint>
    <mtime>1378717158</mtime>
    <first-seen>1339576187</first-seen>
    <last-seen>1409855394</last-seen>
    <last-played>%d</last-played>
    <play-count>1</play-count>
    <bitrate>191</bitrate>
    <rating>%d</rating>
    <date>731881</date>
    <media-type>audio/mpeg</media-type>
    <composer>Unknown</composer>
  </entry>
</rhythmdb>\
"""
        % (song_uri, mount_uri, lastplayed, rating)
    ).encode("utf-8")


class TRBImport(PluginTestCase):
    def setUp(self):
        self.mod = self.modules["rbimport"]

    def test(self):
        lib = SongFileLibrary()

        with temp_filename() as song_fn:
            song = AudioFile({"~filename": song_fn})
            song.sanitize()
            lib.add([song])

            with temp_filename() as xml_fn:
                with open(xml_fn, "wb") as h:
                    x = get_example_xml(song("~filename"), 1, 1371802107)
                    h.write(x)

                handler = self.mod.RBDBContentHandler(lib)
                xml.sax.parse(xml_fn, handler)

                self.assertEqual(song("~#rating"), 0.2)
                self.assertEqual(song("~#lastplayed"), 1371802107)
                self.assertEqual(song("~#playcount"), 1)

                with open(xml_fn, "wb") as h:
                    x = get_example_xml(song("~filename"), 2, 1371802107 - 1)
                    h.write(x)

                handler = self.mod.RBDBContentHandler(lib)
                xml.sax.parse(xml_fn, handler)

                self.assertEqual(song("~#rating"), 0.4)
                self.assertEqual(song("~#lastplayed"), 1371802107)
