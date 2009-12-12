from tests import add, TestCase

import os
import shutil
import tempfile

from quodlibet import config, const
from quodlibet.formats.mp3 import MP3File

import mutagen

class TID3File(TestCase):
    def setUp(self):
        config.init()
        self.filename = tempfile.mkstemp(".mp3")[1]
        shutil.copy(os.path.join('tests', 'data', 'silence-44-s.mp3'), self.filename)

    def test_optional_POPM_count(self):
        #http://code.google.com/p/quodlibet/issues/detail?id=364
        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.POPM(const.EMAIL, 42))
        try: f.save()
        except TypeError:
            #http://code.google.com/p/mutagen/issues/detail?id=33
            pass
        else:
            MP3File(self.filename)

    def tearDown(self):
        os.unlink(self.filename)
        config.quit()

add(TID3File)
