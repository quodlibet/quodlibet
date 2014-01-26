from tests import TestCase

from quodlibet.qltk.window import Window
from quodlibet.util import InstanceTracker


class TWindows(TestCase):

    def test_instance_tracking(self):

        class SomeWindow(Window, InstanceTracker):
            def __init__(self):
                super(SomeWindow, self).__init__()
                self._register_instance()

        self.assertFalse(SomeWindow.windows)
        other = Window()
        a = SomeWindow()
        self.assertTrue(a in SomeWindow.windows)
        self.assertTrue(a in SomeWindow.instances())
        a.destroy()
        self.assertFalse(SomeWindow.instances())
        self.assertTrue(SomeWindow.windows)
        other.destroy()
        self.assertFalse(SomeWindow.windows)
