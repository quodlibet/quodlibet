from tests import TestCase, add

from quodlibet.qltk.playorder import PlayOrder
import quodlibet.config
import quodlibet.plugins

class TPlayOrder(TestCase):
    def setUp(self):
        self.order = -1
        self.volume = 0
        self.replaygain_profiles = [None, None, None]
        quodlibet.plugins.init()
        quodlibet.config.init()
        self.win = PlayOrder(self, self)
        self.win.set_active(0)

    def test_initial(self):
        self.failUnlessEqual(self.win.get_active(), 0)
        self.failUnless(self.replaygain_profiles[2], ["album", "track"])

    def test_set_name(self):
        self.win.set_active("weighted")
        self.failUnlessEqual(2, self.win.get_active())
        self.failUnless(self.replaygain_profiles[2], ["track"])

    def test_set_int(self):
        self.win.set_active(3)
        self.failUnlessEqual(3, self.win.get_active())
        self.failUnless(self.replaygain_profiles[2], ["track"])

    def test_get_name(self):
        for i, name in enumerate(["inorder","shuffle","weighted","onesong"]):
            self.win.set_active(name)
            self.failUnlessEqual(
                self.win.get_active_name().lower(), name.lower())

    def tearDown(self):
        self.win.destroy()
        quodlibet.plugins.quit()
        quodlibet.config.quit()

add(TPlayOrder)
