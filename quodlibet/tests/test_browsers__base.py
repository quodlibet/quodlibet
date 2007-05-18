from tests import TestCase, add

from quodlibet.browsers._base import Browser

class TBrowser(TestCase):
    def setUp(self):
        self.browser = Browser()

    def test_can_filter(self):
        for key in ["foo", "title", "fake~key", "~woobar", "~#huh"]:
            self.failIf(self.browser.can_filter(key))

    def test_defaults(self):
        self.failUnless(self.browser.background)
        self.failIf(self.browser.expand)
        self.failIf(self.browser.expand)
        self.failIf(self.browser.reordered)
        self.failIf(self.browser.headers)
        self.failUnless(self.browser.dynamic(None))

    def tearDown(self):
        self.browser = None
add(TBrowser)
