from unittest import TestCase
from tests import registerCase
import os, gtk, widgets, gc, time

class TestWidgetLeaks(TestCase):
    def test_AboutWindow(self):
         dummy = gtk.Window()
         widgets.AboutWindow(dummy).destroy()
         while gtk.events_pending(): gtk.main_iteration()
         gc.collect()
         c1 = len(gc.get_objects())
         widgets.AboutWindow(dummy).destroy()
         while gtk.events_pending(): gtk.main_iteration()
         gc.collect()
         c2 = len(gc.get_objects())
         self.failUnlessEqual(c1, c2)
         dummy.destroy()

registerCase(TestWidgetLeaks)
