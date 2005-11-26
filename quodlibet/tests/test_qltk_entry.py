from tests import add, TestCase
from qltk.entry import ValidatingEntry
import parser

class TValidatingEntry(TestCase):
    def setUp(self):
        self.entry = ValidatingEntry(parser.is_valid_color)

    def test_changed_simple(self):
        self.entry.set_text("valid")

    def test_changed_valid(self):
        self.entry.set_text("search = 'valid'")

    def test_changed_invalid(self):
        self.entry.set_text("=#invalid")

    def tearDown(self):
        self.entry.destroy()
add(TValidatingEntry)
