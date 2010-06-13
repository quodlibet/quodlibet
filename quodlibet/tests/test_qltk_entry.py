from tests import add, TestCase

from quodlibet.qltk.entry import ValidatingEntry, UndoEntry
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

class TUndoEntry(TestCase):
    def setUp(self):
        self.entry = UndoEntry()

    def __equal(self, value):
        entry_val = self.entry.get_text().decode("utf-8")
        self.failUnlessEqual(value, entry_val)

    def __insert(self, text, pos):
        self.entry.insert_text(text, position=pos)
        self.entry.set_position(pos + len(text))

    def __delete_left(self, start, end):
        self.entry.set_position(start)
        self.entry.delete_text(start, end)
        self.entry.set_position(start)

    def __delete_right(self, start, end):
        self.entry.set_position(end)
        self.entry.delete_text(start, end)
        self.entry.set_position(start)

    def test_undo_reset(self):
        entry = self.entry
        self.__insert("foo", 0)
        self.__insert("bar", 0)
        entry.reset_undo()
        entry.undo()
        entry.undo()
        entry.undo()
        self.__equal("barfoo")

    def test_undo_norm(self):
        entry = self.entry
        self.__insert("foo", 0)
        entry.undo()
        self.__equal("")
        entry.redo()
        self.__equal("foo")

    def test_undo_space(self):
        entry = self.entry
        self.__insert("f", 0)
        self.__insert(" ", 1)
        self.__insert("o", 2)
        entry.undo()
        self.__equal("f ")
        entry.undo()
        self.__equal("")

    def test_undo_insert_end(self):
        entry = self.entry
        self.__insert("f", 0)
        self.__insert("o", 1)
        self.__insert("o", 2)
        entry.undo()
        self.__equal("")
        entry.redo()
        self.__equal("foo")

    def test_undo_insert_end_2(self):
        entry = self.entry
        self.__insert("f", 0)
        self.__insert("o", 1)
        self.__insert("o", 2)
        self.__insert("bar", 3)
        entry.undo()
        self.__equal("foo")
        entry.redo()
        self.__equal("foobar")

    def test_undo_insert_middle(self):
        entry = self.entry
        self.__insert("foo", 0)
        self.__insert("b", 1)
        self.__equal("fboo")
        entry.undo()
        self.__equal("foo")
        entry.undo()
        self.__equal("")

    def test_undo_delete(self):
        entry = self.entry
        self.__insert("foobar", 0)
        self.__delete_left(3, 4)
        self.__equal("fooar")
        self.__delete_right(1, 3)
        self.__equal("far")
        entry.undo()
        self.__equal("fooar")
        entry.undo()
        self.__equal("foobar")

    def test_undo_delete_space(self):
        entry = self.entry
        self.__insert("foob ar", 0)
        self.__delete_right(6, 7)
        self.__equal("foob a")
        self.__delete_right(5, 6)
        self.__delete_right(4, 5)
        self.__delete_right(3, 4)
        self.__delete_right(2, 3)
        entry.undo()
        self.__equal("foob")

    def tearDown(self):
        self.entry.destroy()
add(TUndoEntry)
