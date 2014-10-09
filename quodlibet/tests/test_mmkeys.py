from tests import TestCase

from gi.repository import Gtk

from quodlibet.player.nullbe import NullPlayer
from quodlibet.mmkeys import MMKeysHandler, iter_backends


class TMmKeys(TestCase):

    def test_handler(self):
        win = Gtk.Window()
        handler = MMKeysHandler(win, NullPlayer())
        handler.quit()

    def test_backends(self):
        for backend in iter_backends():
            backend.is_active()
            instance = backend("Foo", lambda action: None)
            instance.grab()
            instance.cancel()
            instance.cancel()
