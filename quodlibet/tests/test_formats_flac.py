from tests import add

import os
import shutil
import tempfile

from mutagen.flac import FLAC

from formats.flac import FLACFile
from tests.test_formats__vorbis import TVCFile

class TFLACFile(TVCFile):
    def setUp(self):
        self.filename = tempfile.mkstemp(".flac")[1]
        shutil.copy(os.path.join('tests', 'data', 'empty.flac'), self.filename)
        self.song = FLACFile(self.filename)

    def test_save_empty(self):
        self.song.write()
        flac = FLAC(self.filename)
        self.failIf(flac.tags)
        self.failIf(flac.tags is None)

    def tearDown(self):
        os.unlink(self.filename)

add(TFLACFile)
