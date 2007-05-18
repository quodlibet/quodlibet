from tests import TestCase, add

import gtk
import quodlibet.stock
quodlibet.stock.init()

class TStock(TestCase):
    def test_pixbufs(self):
        lookup = gtk.icon_factory_lookup_default
        for i in quodlibet.stock._ICONS: self.failUnless(lookup(i))

    def test_labels(self):
        lookup = gtk.stock_lookup
        for i in [quodlibet.stock.EDIT_TAGS,
                  quodlibet.stock.PLUGINS,
                  quodlibet.stock.PREVIEW,
                  quodlibet.stock.REMOVE,
                  quodlibet.stock.ENQUEUE]:
            self.failUnless(lookup(i))

    def test_info(self):
        self.failUnless(gtk.STOCK_INFO)
add(TStock)
