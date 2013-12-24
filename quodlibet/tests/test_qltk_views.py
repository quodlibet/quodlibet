from tests import TestCase, add
from quodlibet.qltk.views import AllTreeView, BaseView, TreeViewColumn
import quodlibet.config
from gi.repository import Gtk


class THintedTreeView(TestCase):
    def setUp(self):
        quodlibet.config.init()
        self.c = AllTreeView()

    def test_exists(self):
        self.failUnless(self.c)

    def tearDown(self):
        self.c.destroy()
        quodlibet.config.quit()
add(THintedTreeView)


class TBaseView(TestCase):
    def setUp(self):
        self.m = Gtk.ListStore(str)
        self.c = BaseView(self.m)

    def test_remove(self):
        self.m.append(row=["foo"])
        self.c.remove_iters([self.m[0].iter])
        self.failIf(len(self.m))

        self.m.append(row=["foo"])
        self.c.remove_iters([])
        self.failUnless(len(self.m))

        self.c.remove_paths([self.m[0].path])
        self.failIf(len(self.m))

    def test_select_func(self):
        self.m.append(row=["foo"])
        self.m.append(row=["bar"])
        self.failUnless(self.c.select_by_func(lambda r: True))
        self.failIf(self.c.select_by_func(lambda r: False))
        self.c.select_by_func(lambda r: False, scroll=False, one=True)

    def test_remove_select(self):
        self.c.remove_selection()

    def test_without_model(self):
        column = TreeViewColumn()
        self.c.append_column(column)

        column = self.c.get_columns()[0]
        column.set_sort_indicator(True)
        self.c.set_search_column(0)

        with self.c.without_model() as model:
            self.assertEqual(model, self.m)
            self.assertTrue(self.c.get_model() is None)

        self.assertEqual(self.c.get_search_column(), 0)
        column = self.c.get_columns()[0]
        self.assertTrue(column.get_sort_indicator())

    def tearDown(self):
        self.c.destroy()
add(TBaseView)
