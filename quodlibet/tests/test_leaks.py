from unittest import TestCase
from tests import registerCase
import os, gtk, widgets, gc, time

class TestWidgetLeaks(TestCase):
    def test_AboutWindow(self):
         dummy = gtk.Window()
         self.failIfLeaky(widgets.AboutWindow, dummy)
         dummy.destroy()

    def test_BCI(self):
         self.failIfLeaky(
             widgets.BigCenteredImage, "woo",
             "/home/piman/audio/Ani DiFranco - Dilate/cover.jpg")

    def failIfLeaky(self, Ctr, *args):
         gc.collect()
         c0 = len(gc.get_objects())
         Ctr(*args).destroy()
         while gtk.events_pending(): gtk.main_iteration()
         gc.collect()
         c1 = len(gc.get_objects())
         Ctr(*args).destroy()
         while gtk.events_pending(): gtk.main_iteration()
         gc.collect()
         c2 = len(gc.get_objects())
         self.failUnlessEqual(c0, c1)
         self.failUnlessEqual(c1, c2)

registerCase(TestWidgetLeaks)
