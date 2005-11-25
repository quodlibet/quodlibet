import gtk
from tests import add, TestCase
from qltk.ccb import ConfigCheckButton
import config

class TConfigCheckButton(TestCase):
    def test_toggle(self):
        config.set("memory", "bar", "on")
        c = ConfigCheckButton("dummy", "memory", "bar")
        c.set_active(True)
        self.failUnless(config.getboolean("memory", "bar") and c.get_active())
        c.set_active(False)
        while gtk.events_pending(): gtk.main_iteration()
        self.failIf(config.getboolean("memory", "bar") or c.get_active())
add(TConfigCheckButton)
