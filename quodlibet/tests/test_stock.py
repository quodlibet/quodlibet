from tests import TestCase, add

import gtk
import quodlibet.stock
quodlibet.stock.init()

class TStock(TestCase):
    def test_icon_theme(self):
        theme = gtk.icon_theme_get_default()
        for i in ["audio-volume-high", "audio-volume-high",
            "audio-volume-medium", "audio-volume-muted",
            "multimedia-player", "multimedia-player-apple-ipod",
            "quodlibet", "exfalso", "quodlibet-missing-cover"]:
            self.failUnless(theme.has_icon(i))

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
