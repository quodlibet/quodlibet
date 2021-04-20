# Copyright 2018 Phidica Veia
#           2021 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sqlite3
from senf import fsn2uri

from quodlibet.formats import AudioFile

from tests.helper import temp_filename
from quodlibet.library import SongFileLibrary
from . import PluginTestCase


def get_example_db(song_path, rating, playcount, skipcount, lastplayed,
                   dateadded):
    # create a temporary database in memory
    db = sqlite3.connect(':memory:')

    # create a simplified version of a banshee track table
    csr = db.cursor()
    csr.execute('''CREATE TABLE CoreTracks(
                ArtistID INTEGER,
                AlbumID INTEGER,
                Uri TEXT,
                Title TEXT,
                Rating INTEGER,
                PlayCount INTEGER,
                SkipCount INTEGER,
                LastPlayedStamp INTEGER,
                DateAddedStamp INTEGER
                )
                ''')

    # insert song and save
    song_uri = fsn2uri(song_path)
    csr.execute('INSERT INTO CoreTracks VALUES (?,?,?,?,?,?,?,?,?)',
                (1, 1, song_uri, 'Music', rating, playcount, skipcount,
                lastplayed, dateadded))
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

            # test recovery of basic song
            data = {"path": song("~filename"), "rating": 1,
            "playcount": 1, "skipcount": 2,
            "lastplayed": 1371802107, "added": 1260691996}

            db = get_example_db(data["path"], data["rating"],
                                data["playcount"], data["skipcount"],
                                data["lastplayed"], data["added"])

            importer = self.mod.BansheeDBImporter(lib)
            importer.read(db)
            count = importer.finish()
            db.close()

            self.assertEqual(song("~#rating"), data["rating"] / 5.0)
            self.assertEqual(song("~#playcount"), data["playcount"])
            self.assertEqual(song("~#skipcount"), data["skipcount"])
            self.assertEqual(song("~#lastplayed"), data["lastplayed"])
            self.assertEqual(song("~#added"), data["added"])
            self.assertEqual(count, 1)

            # test recovery of different version of same song
            data_mod = {"path": song("~filename"), "rating": 2,
            "playcount": 4, "skipcount": 1,
            "lastplayed": data["lastplayed"] - 1, "added": data["added"] + 1}

            db = get_example_db(data_mod["path"], data_mod["rating"],
                                data_mod["playcount"], data_mod["skipcount"],
                                data_mod["lastplayed"], data_mod["added"])

            importer = self.mod.BansheeDBImporter(lib)
            importer.read(db)
            count = importer.finish()
            db.close()

            self.assertEqual(song("~#rating"), data_mod["rating"] / 5.0)
            self.assertEqual(song("~#playcount"), data_mod["playcount"])
            self.assertEqual(song("~#skipcount"), data_mod["skipcount"])
            self.assertEqual(song("~#lastplayed"), data["lastplayed"])
            self.assertEqual(song("~#added"), data["added"])
            self.assertEqual(count, 1)

            # test that no recovery is performed when data is identical
            db = get_example_db(data_mod["path"], data_mod["rating"],
                                data_mod["playcount"], data_mod["skipcount"],
                                data_mod["lastplayed"], data_mod["added"])

            importer = self.mod.BansheeDBImporter(lib)
            importer.read(db)
            count = importer.finish()
            db.close()

            self.assertEqual(count, 0)
