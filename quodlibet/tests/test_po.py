import os, glob
from tests import add, TestCase

class TPO(TestCase):
    def test_pos(self):
        for f in glob.glob("po/*.po"):
            self.failIf(os.system("msgfmt -c %s > /dev/null" % f))
        try: os.unlink("messages.mo")
        except OSError: pass

    def test_gtranslator_blows_goats(self):
        for f in glob.glob("po/*.po"):
            for line in file(f):
                if line.strip().startswith("#"): continue
                self.failIf(
                    "\xc2\xb7" in line,
                    "Broken GTranslator copy/paste in %s:\n%s" % (f, line))

    def test_gtk_stock_items(self):
        for f in glob.glob("po/*.po"):
            for line in file(f):
                if line.strip().startswith('msgstr "gtk-'):
                    parts = line.strip().split()
                    value = parts[1].strip('"')[4:]
                    self.failIf(value and value not in [
                        'media-next', 'media-previous', 'media-play',
                        'media-pause'],
                                "Invalid stock translation in %s\n%s" %(
                        f, line))
add(TPO)
