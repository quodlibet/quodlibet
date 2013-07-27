from tests import TestCase, add, DATA_DIR, mkstemp

import os
import shutil

import mutagen

from mutagen.apev2 import BINARY, APEValue

from quodlibet.formats.monkeysaudio import MonkeysAudioFile
from quodlibet.formats.mpc import MPCFile

class TAPEv2FileBase(TestCase):
    def setUp(self):
        raise NotImplementedError

    def test_can_change(self):
        self.failUnlessEqual(self.s.can_change(), True)
        self.failUnlessEqual(self.s.can_change("~"), False)
        self.failUnlessEqual(self.s.can_change("a"), False)
        self.failUnlessEqual(self.s.can_change("OggS"), True)
        self.failUnlessEqual(self.s.can_change("\xc3\xa4\xc3\xb6"), False)
        self.failUnlessEqual(self.s.can_change("sUbtitle"), False)
        self.failUnlessEqual(self.s.can_change("indeX"), False)
        self.failUnlessEqual(self.s.can_change("yEar"), False)

    def test_trans_keys(self):
        self.s["date"] = "2010"
        self.s.write()
        m = mutagen.apev2.APEv2(self.f)
        self.failUnlessEqual(m["Year"], "2010")
        m["yEar"] = "2011"
        m.save()
        self.s.reload()
        self.failUnlessEqual(self.s["date"], "2011")

    def test_ignore(self):
        for tag in ["inDex", "index"]:
            m = mutagen.apev2.APEv2(self.f)
            m[tag] = "foobar"
            m.save()
            self.s.reload()
            self.failUnlessEqual(self.s.get(tag), None)
            m = mutagen.apev2.APEv2(self.f)
            self.failUnlessEqual(m[tag], "foobar")

    def test_multi_case(self):
        self.s["AA"] = "B"
        self.s["aa"] = "C"
        self.s["BB"] = "D"
        self.s["Aa"] = "E"
        self.s.write()
        self.s.reload()
        self.failUnlessEqual(set(self.s["aa"].split()), set(["C", "B", "E"]))

    def test_binary_ignore(self):
        m = mutagen.apev2.APEv2(self.f)
        m["foo"] = APEValue("bar", BINARY)
        m.save()
        self.s.reload()
        self.failUnlessEqual(self.s.get("foo"), None)
        self.s.write()
        m = mutagen.apev2.APEv2(self.f)
        self.failUnlessEqual("foo" in m, True)

    def test_titlecase(self):
        self.s["isRc"] = "1234"
        self.s["fOoBaR"] = "5678"
        self.s.write()
        self.s.reload()
        self.failUnlessEqual("isrc" in self.s, True)
        self.failUnlessEqual("foobar" in self.s, True)
        m = mutagen.apev2.APEv2(self.f)
        self.failUnlessEqual("ISRC" in m, True)
        self.failUnlessEqual("Foobar" in m, True)

    def test_disc_mapping(self):
        m = mutagen.apev2.APEv2(self.f)
        m["disc"] = "99/102"
        m.save()
        self.s.reload()
        self.failUnlessEqual(self.s("~#disc"), 99)
        self.failUnlessEqual(self.s("discnumber"), "99/102")

        self.s["discnumber"] = "77/88"
        self.s.write()
        m = mutagen.apev2.APEv2(self.f)
        self.failUnlessEqual(m["disc"], "77/88")

    def test_track_mapping(self):
        m = mutagen.apev2.APEv2(self.f)
        m["track"] = "99/102"
        m.save()
        self.s.reload()
        self.failUnlessEqual(self.s("~#track"), 99)
        self.failUnlessEqual(self.s("tracknumber"), "99/102")

        self.s["tracknumber"] = "77/88"
        self.s.write()
        m = mutagen.apev2.APEv2(self.f)
        self.failUnlessEqual(m["track"], "77/88")

    def tearDown(self):
        os.unlink(self.f)

class TMPCFile(TAPEv2FileBase):
    def setUp(self):
        self.f = mkstemp(".mpc")[1]
        shutil.copy(os.path.join(DATA_DIR, 'silence-44-s.mpc'), self.f)
        self.s = MPCFile(self.f)
add(TMPCFile)

class TMAFile(TAPEv2FileBase):
    def setUp(self):
        self.f = mkstemp(".ape")[1]
        shutil.copy(os.path.join(DATA_DIR, 'silence-44-s.ape'), self.f)
        self.s = MonkeysAudioFile(self.f)
add(TMAFile)
