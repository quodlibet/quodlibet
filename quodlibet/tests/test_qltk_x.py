from tests import TestCase, add
from helper import visible

from gi.repository import Gtk

from quodlibet.qltk import x

class Window(TestCase):
    def test_ctr(self):
        x.Window().destroy()
add(Window)

class Notebook(TestCase):
    def test_widget_str(self):
        n = x.Notebook()
        c = Gtk.VBox()
        n.append_page(c, "A Test")
        self.failUnlessEqual("A Test", n.get_tab_label(c).get_text())
        n.destroy()

    def test_widget_label(self):
        l = Gtk.Label(label="A Test")
        n = x.Notebook()
        c = Gtk.VBox()
        n.append_page(c, l)
        self.failUnless(l is n.get_tab_label(c))
        c.destroy()

    def test_widget_error(self):
        n = x.Notebook()
        w = Gtk.VBox()
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
        self.failUnless(x.MenuItem("foo", Gtk.STOCK_FIND))
add(MenuItem)

class Button(TestCase):    
    def test_ctr(self):
        self.failUnless(x.Button("foo", Gtk.STOCK_FIND))
add(Button)


class RPaned(object):
    Kind = None

    def test_ctr(self):
        self.Kind().destroy()

    def test_pre_alloc(self):
        p = self.Kind()
        p.set_relative(0.25)
        self.failUnlessEqual(p.get_relative(), 0.25)

    def test_visible_no_setup(self):
        p = self.Kind()
        with visible(p):
            pass

    def test_visible_pre_setup_children(self):
        p = self.Kind()
        p.pack1(Gtk.Button())
        p.pack2(Gtk.Button())
        p.set_relative(0.75)
        self.failUnlessEqual(p.get_relative(), 0.75)
        with visible(p, width=200, height=200) as p:
            self.failUnlessAlmostEqual(p.get_relative(), 0.75, 2)

    def test_visible_pre_setup_empty(self):
        p = self.Kind()
        p.set_relative(0.75)
        self.failUnlessEqual(p.get_relative(), 0.75)
        with visible(p) as p:
            self.failUnlessEqual(p.get_relative(), 0.75)


class RHPaned(TestCase, RPaned):
    Kind = x.RHPaned
add(RHPaned)


class RVPaned(TestCase, RPaned):
    Kind = x.RVPaned
add(RVPaned)


class TAlignment(TestCase):
    def test_ctr(self):
        button = Gtk.Button()
        a = x.Alignment(button, left=2, right=4, top=5, bottom=-2, border=2)
        self.failUnlessEqual(a.get_padding(), (7, 0, 4, 6))
        self.failUnless(a.get_child() is button)
        a.destroy()
add(TAlignment)

class TScrolledWindow(TestCase):
    def test_ctr(self):
        w = x.ScrolledWindow()
        w.destroy()
add(TScrolledWindow)
