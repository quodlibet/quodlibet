from tests import TestCase, AbstractTestCase

import os
import glob
import subprocess

import quodlibet
from quodlibet.util.path import iscommand


PODIR = os.path.join(os.path.dirname(quodlibet.__path__[0]), "po")


class TPOTFILESIN(TestCase):

    def test_missing(self):
        if not iscommand("intltool-update"):
            return

        old_cd = os.getcwd()
        try:
            os.chdir(PODIR)
            result = subprocess.check_output(
                ["intltool-update", "--maintain",
                 "--gettext-package", "quodlibet"],
                 stderr=subprocess.STDOUT)
        finally:
            os.chdir(old_cd)

        if result:
            raise Exception(result)


class PO(AbstractTestCase):
    def test_pos(self):
        if not iscommand("msgfmt"):
            return

        self.failIf(os.system("msgfmt -c po/%s.po > /dev/null" % self.lang))
        try:
            os.unlink("messages.mo")
        except OSError:
            pass

    def test_gtranslator_blows_goats(self):
        for line in open(os.path.join(PODIR, "%s.po" % self.lang), "rb"):
            if line.strip().startswith("#"):
                continue
            self.failIf("\xc2\xb7" in line,
                        "Broken GTranslator copy/paste in %s:\n%s" % (
                self.lang, line))

    def test_gtk_stock_items(self):
        for line in open(os.path.join(PODIR, "%s.po" % self.lang), "rb"):
            if line.strip().startswith('msgstr "gtk-'):
                parts = line.strip().split()
                value = parts[1].strip('"')[4:]
                self.failIf(value and value not in [
                    'media-next', 'media-previous', 'media-play',
                    'media-pause'],
                            "Invalid stock translation in %s\n%s" % (
                    self.lang, line))


for fn in glob.glob(os.path.join(PODIR, "*.po")):
    lang = os.path.basename(fn)[:-3]
    testcase = type('PO.' + lang, (PO,), {})
    testcase.lang = lang
    globals()['PO.' + lang] = testcase
