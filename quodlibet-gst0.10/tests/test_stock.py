from tests import TestCase, add
import gtk
import stock
stock.init()

class TStock(TestCase):
    def test_pixbufs(self):
        lookup = gtk.icon_factory_lookup_default
        for i in stock._ICONS: self.failUnless(lookup(i))

    def test_labels(self):
        lookup = gtk.stock_lookup
        for i in [stock.EDIT_TAGS, stock.PLUGINS, stock.PREVIEW, stock.REMOVE,
                  stock.ENQUEUE]: self.failUnless(lookup(i))

    def test_info(self):
        self.failUnless(gtk.STOCK_INFO)
add(TStock)
