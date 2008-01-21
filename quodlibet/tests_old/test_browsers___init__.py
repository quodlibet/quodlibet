from tests import TestCase, add

from quodlibet import browsers

class TBrowsers(TestCase):
    def test_presence(self):
        self.failUnless(browsers.search)
        self.failUnless(browsers.paned)
        self.failUnless(browsers.iradio)
        self.failUnless(browsers.audiofeeds)
        self.failUnless(browsers.albums)
        self.failUnless(browsers.playlists)
        self.failUnless(browsers.filesystem)

    def test_get(self):
        self.failUnless(browsers.get("EmptyBar") is browsers.search.EmptyBar)
        self.failUnless(
            browsers.get("FileSystem") is browsers.filesystem.FileSystem)

    def test_get_invalid(self):
        self.failUnless(
            browsers.get("DoesNotExist") is browsers.search.EmptyBar)
add(TBrowsers)
