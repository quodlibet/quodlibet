# -*- coding: utf-8 -*-
# Copyright 2018 Phidica Veia
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sqlite3
from senf import fsn2uri

from quodlibet.formats import AudioFile

from tests.helper import temp_filename
from quodlibet.library.libraries import SongFileLibrary
from . import PluginTestCase


def get_example_db(song_path, rating, lastplayed, dateadded):
    # create a temporary database in memory
    db = sqlite3.connect(':memory:')

    # create table
    csr = db.cursor()
    csr.execute('''CREATE TABLE CoreTracks
                (Uri, Title, ArtistID, AlbumID, Rating, PlayCount, SkipCount,
                LastPlayedStamp, DateAddedStamp)''')

    # insert song and save
    song_uri = fsn2uri(song_path)
    csr.execute('INSERT INTO CoreTracks VALUES (?,?,?,?,?,?,?,?,?)',
                (song_uri, 'Music', 1, 1, rating, 1, 2, lastplayed, dateadded))
    db.commit()

    # give the user the in-memory database
    return db


class TBansheeImport(PluginTestCase):

    def setUp(self):
        self.mod = self.modules["bansheeimport"]

    def test(self):
        lib = SongFileLibrary()

        with temp_filename() as song_fn:
            song = AudioFile({"~filename": song_fn})
            song.sanitize()
            lib.add([song])

            data = {"path" : song("~filename"), "rating" : 1,
            "lastplayed" : 1371802107, "dateadded" : 1260691996}

            db = get_example_db(data["path"], data["rating"],
                                data["lastplayed"], data["dateadded"])

            importer = self.mod.BansheeDBImporter(lib)
            importer.read(db)
            importer.finish()

            db.close()
