from tests import TestCase, add

from qltk.playorder import PlayOrder


class TPlayOrder(TestCase):
    def setUp(self):
        self.order = -1
        self.volume = 0
        self.replaygain_profiles = []
        self.win = PlayOrder(self, self)
        self.win.set_active(0)

    def test_initial(self):
        self.failUnlessEqual(self.win.get_active(), 0)
        self.failUnlessEqual(self.order, 0)
        self.failUnless(self.replaygain_profiles, ["album", "track"])

    def test_set_name(self):
        self.win.set_active("weighted")
        self.failUnlessEqual(self.order, 2)
        self.failUnlessEqual(self.order, self.win.get_active())
        self.failUnless(self.replaygain_profiles, ["track"])

    def test_set_int(self):
        self.win.set_active(3)
        self.failUnlessEqual(self.order, 3)
        self.failUnlessEqual(self.order, self.win.get_active())
        self.failUnless(self.replaygain_profiles, ["track"])

    def test_get_name(self):
        for i, name in enumerate(["inorder","shuffle","weighted","onesong"]):
            self.win.set_active(i)
            self.failUnlessEqual(self.order, i)
            self.failUnlessEqual(self.order, self.win.get_active())
            self.failUnlessEqual(self.win.get_active_name(), name)

    def tearDown(self):
        self.win.destroy()
add(TPlayOrder)
