from tests import add, TestCase

from quodlibet.qltk.entry import ValidatingEntry
from quodlibet.parse import Query
import quodlibet.config

class TValidatingEntry(TestCase):
    def setUp(self):
        quodlibet.config.init()
        self.entry = ValidatingEntry(Query.is_valid_color)

    def test_changed_simple(self):
        self.entry.set_text("valid")

    def test_changed_valid(self):
        self.entry.set_text("search = 'valid'")

    def test_changed_invalid(self):
        self.entry.set_text("=#invalid")

    def tearDown(self):
        self.entry.destroy()
        quodlibet.config.quit()
add(TValidatingEntry)
