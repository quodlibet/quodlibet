from tests import TestCase

from quodlibet.qltk.window import Window
from quodlibet.util import InstanceTracker


class TWindows(TestCase):

    def test_ctr(self):
        Window().destroy()

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

    def test_show_maybe(self):
        Window.prevent_inital_show(True)
        w = Window()
        w.show_maybe()
        self.assertFalse(w.get_visible())
        Window.prevent_inital_show(False)
        w.show_maybe()
        self.assertTrue(w.get_visible())
