from unittest import TestCase
from tests import registerCase, Mock
import gtk, qltk

class TestNotebook(TestCase):
    def test_widget_str(self):
        n = qltk.Notebook()
        c = gtk.VBox()
        n.append_page(c, "A Test")
        self.failUnlessEqual("A Test", n.get_tab_label(c).get_text())
        n.destroy()

    def test_widget_label(self):
        l = gtk.Label("A Test")
        n = qltk.Notebook()
        c = gtk.VBox()
        n.append_page(c, l)
        self.failUnless(l is n.get_tab_label(c))
        c.destroy()

    def test_wrapper_error(self):
        n = qltk.Notebook()
        w = Mock(widget = gtk.VBox())
        self.failUnlessRaises(TypeError, n.append_page, w)
        w.widget.destroy()
        n.destroy()

registerCase(TestNotebook)

