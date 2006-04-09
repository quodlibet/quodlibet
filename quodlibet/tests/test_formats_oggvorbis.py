import os
import shutil
import tempfile

from tests import add
from formats.oggvorbis import OggFile
from tests.test_formats__vorbis import TVCFile

class TOggFile(TVCFile):
    def setUp(self):
        self.filename = tempfile.mkstemp(".ogg")[1]
        shutil.copy(os.path.join('tests', 'data', 'empty.ogg'), self.filename)
        self.song = OggFile(self.filename)

    def tearDown(self):
        os.unlink(self.filename)

add(TOggFile)
