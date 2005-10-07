from tests import TestCase, add
import gtk
import stock

class TStock(TestCase):
    def test_stock(self):
        lookup = gtk.icon_factory_lookup_default
        for i in stock._ICONS: self.failIf(lookup(i))
        stock.init()
        for i in stock._ICONS: self.failUnless(lookup(i))
add(TStock)
