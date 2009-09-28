from tests import TestCase, add

import gtk
from quodlibet.qltk import x

class Window(TestCase):
    def test_ctr(self):
        x.Window().destroy()
add(Window)

class Notebook(TestCase):
    def test_widget_str(self):
        n = x.Notebook()
        c = gtk.VBox()
        n.append_page(c, "A Test")
        self.failUnlessEqual("A Test", n.get_tab_label(c).get_text())
        n.destroy()

    def test_widget_label(self):
        l = gtk.Label("A Test")
        n = x.Notebook()
        c = gtk.VBox()
        n.append_page(c, l)
        self.failUnless(l is n.get_tab_label(c))
        c.destroy()

    def test_widget_error(self):
        n = x.Notebook()
        w = gtk.VBox()
        self.failUnlessRaises(TypeError, n.append_page, w)
        w.destroy()
        n.destroy()
add(Notebook)

class Frame(TestCase):
    def test_label(self):
        self.failUnlessEqual(
            x.Frame("foo").get_label_widget().get_text(), "foo")
add(Frame)

class MenuItem(TestCase):
    def test_ctr(self):
        self.failUnless(x.MenuItem("foo", gtk.STOCK_FIND))
add(MenuItem)

class Button(TestCase):    
    def test_ctr(self):
        self.failUnless(x.Button("foo", gtk.STOCK_FIND))
add(Button)

class RHPaned(TestCase):
    def test_ctr(self): x.RHPaned().destroy()
add(RHPaned)

class RVPaned(TestCase):
    def test_ctr(self): x.RVPaned().destroy()
add(RVPaned)

