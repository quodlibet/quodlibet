from tests import TestCase, add

import os
import glob

class PO(TestCase):
    def test_pos(self):
        self.failIf(os.system("msgfmt -c po/%s.po > /dev/null" % self.lang))
        try: os.unlink("messages.mo")
        except OSError: pass

    def test_gtranslator_blows_goats(self):
        for line in file("po/%s.po" % self.lang):
            if line.strip().startswith("#"): continue
            self.failIf("\xc2\xb7" in line,
                        "Broken GTranslator copy/paste in %s:\n%s" % (
                self.lang, line))

    def test_gtk_stock_items(self):
        for line in file("po/%s.po" % self.lang):
            if line.strip().startswith('msgstr "gtk-'):
                parts = line.strip().split()
                value = parts[1].strip('"')[4:]
                self.failIf(value and value not in [
                    'media-next', 'media-previous', 'media-play',
                    'media-pause'],
                            "Invalid stock translation in %s\n%s" %(
                    self.lang, line))

for fn in glob.glob("po/*.po"):
    lang = fn[3:-3]
    testcase = type('PO.' + lang, (PO,), {})
    testcase.lang = lang
    add(testcase)
