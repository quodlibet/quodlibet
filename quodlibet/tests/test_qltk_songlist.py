from tests import TestCase, add

import gtk
import gobject

from quodlibet.player.nullbe import NullPlayer
from quodlibet.library import SongLibrary
from quodlibet.formats._audio import AudioFile
from quodlibet.qltk.songlist import PlaylistModel, PlaylistMux, SongList
from quodlibet.qltk.playorder import ORDERS
from quodlibet.qltk.songmodel import CustomListStore
import quodlibet.config

def do_events():
    while gtk.events_pending():
        gtk.main_iteration()

class TPlaylistListStore(TestCase):
    def setUp(self):
        self.m = PlaylistModel()
        self.m.set(range(10))

    def shutDown(self):
        self.m.destroy()

    def test_get_iter(self):
        self.failUnlessRaises(ValueError, self.m.get_iter, 11)
        self.failUnlessRaises(ValueError, self.m.get_iter, 999)
        self.m.get_iter((0,))
        self.m.get_iter("1")

    def test_len(self):
        self.failUnlessEqual(len(self.m), 10)
        self.m.clear()
        self.failUnlessEqual(len(self.m), 0)

    def test_iter_valid(self):
        it = self.m.get_iter(5)
        self.failUnless(self.m.iter_is_valid(it))
        self.m.remove(it)
        self.failIf(self.m.iter_is_valid(it))

    def test_get_value(self):
        self.failUnlessEqual(self.m.get_value(self.m.get_iter(0), 0), 0)

    def test_iter_has_child(self):
        has_child = self.m.iter_has_child(self.m.get_iter(0))
        self.failUnlessEqual(has_child, False)

    def test_iter_n_children(self):
        num = self.m.iter_n_children(self.m.get_iter(0))
        self.failUnlessEqual(num, 0)
        num = self.m.iter_n_children(None)
        self.failUnlessEqual(num, 10)

    def test_iter_nth_child(self):
        child = self.m.iter_nth_child(None, 5)
        self.failUnlessEqual(self.m.get_path(child), (5,))
        child = self.m.iter_nth_child(self.m.get_iter(9), 5)
        self.failUnlessEqual(child, None)

    def test_iter_parent(self):
        parent = self.m.iter_parent(self.m.get_iter(9))
        self.failUnlessEqual(parent, None)

    def test_get(self):
        # get is overridden, but test anyway
        values = gtk.TreeModel.get(self.m, self.m.get_iter(9), 0, 0)
        self.failUnlessEqual(values, (9, 9))

    def test_columns(self):
        self.failUnlessEqual(self.m.get_n_columns(), 1)
        self.failUnlessEqual(self.m.get_column_type(0), gobject.TYPE_PYOBJECT)
        self.failUnlessEqual(self.m.get_column_type(1), gobject.TYPE_INVALID)

    def test_set_column_types(self):
        self.m.set_column_types(object)
        self.m.set_column_types(gobject.TYPE_PYOBJECT)
        self.failUnlessRaises(ValueError, self.m.set_column_types, int)
        self.failUnlessRaises(ValueError,
                              self.m.set_column_types, object, object)

    def test_set_value(self):
        it = self.m.get_iter(9)
        self.m.set_value(it, 0, 42)
        self.failUnlessEqual(self.m[it][0], 42)
        self.failUnlessRaises(ValueError, self.m.set_value, it, 1, 0)

    def test_set(self):
        # set is overridden, but test anyway
        it = self.m.get_iter(0)
        CustomListStore.set(self.m, it, 0, 24)
        self.failUnlessEqual(self.m[it][0], 24)
        CustomListStore.set(self.m, it, 0, 24, 0, 42)
        self.failUnlessEqual(self.m[it][0], 42)
        self.failUnlessRaises(ValueError,
                              CustomListStore.set, self.m, it, 0, 24, 1, 42)
        self.failUnlessRaises(TypeError,
                              CustomListStore.set, self.m, it, 0, 24, 1)

    def test_remove(self):
        valid = self.m.remove(self.m.get_iter(0))
        self.failIf(valid)
        self.failUnlessEqual(self.m.get(), range(1, 10))
        valid = self.m.remove(self.m.get_iter(8))
        self.failIf(valid)
        self.failUnlessEqual(self.m.get(), range(1, 9))

    def test_insert(self):
        x = range(10)
        it = self.m.insert(0, row=[42])
        x.insert(0, 42)
        self.failUnless(self.m.iter_is_valid(it))
        self.failUnlessEqual(self.m.get(), x)

        it = self.m.insert(1)
        x.insert(1, None)
        self.failUnless(self.m.iter_is_valid(it))
        self.failUnlessEqual(self.m.get(), x)

        it = self.m.insert(99, row=[123])
        x.append(123)
        self.failUnless(self.m.iter_is_valid(it))
        self.failUnlessEqual(self.m.get(), x)

    def test_insert_before(self):
        x = range(10)
        it = self.m.insert_before(None, row=[123])
        x.append(123)
        self.failUnless(self.m.iter_is_valid(it))
        self.failUnlessEqual(self.m.get(), x)

        it = self.m.insert_before(it, row=[456])
        x.insert(len(x)-1, 456)
        self.failUnless(self.m.iter_is_valid(it))
        self.failUnlessEqual(self.m.get(), x)

        it = self.m.insert_before(self.m.get_iter(0), row=[789])
        x.insert(0, 789)
        self.failUnless(self.m.iter_is_valid(it))
        self.failUnlessEqual(self.m.get(), x)

    def test_insert_after(self):
        x = range(10)
        it = self.m.insert_after(None, row=[123])
        x.insert(0, 123)
        self.failUnless(self.m.iter_is_valid(it))
        self.failUnlessEqual(self.m.get(), x)

        it = self.m.insert_after(it, row=[456])
        x.insert(1, 456)
        self.failUnless(self.m.iter_is_valid(it))
        self.failUnlessEqual(self.m.get(), x)

        it = self.m.insert_after(self.m.get_iter(11), row=[789])
        x.append(789)
        self.failUnless(self.m.iter_is_valid(it))
        self.failUnlessEqual(self.m.get(), x)

    def test_prepend(self):
        x = range(10)
        it = self.m.prepend(row=[42])
        x.insert(0, 42)
        self.failUnless(self.m.iter_is_valid(it))
        self.failUnlessEqual(self.m.get(), x)
        self.failUnlessEqual(self.m.get_path(it), (0,))
        self.m.clear()
        it = self.m.prepend(row=[42])
        self.failUnless(self.m.iter_is_valid(it))
        self.failUnlessEqual(self.m.get(), [42])
        self.failUnlessEqual(self.m.get_path(it), (0,))

    def test_append(self):
        x = range(10)
        it = self.m.append(row=[42])
        x.append(42)
        self.failUnless(self.m.iter_is_valid(it))
        self.failUnlessEqual(self.m.get(), x)
        self.failUnlessEqual(self.m.get_path(it), (10,))
        self.m.clear()
        it = self.m.append(row=[42])
        self.failUnless(self.m.iter_is_valid(it))
        self.failUnlessEqual(self.m.get(), [42])
        self.failUnlessEqual(self.m.get_path(it), (0,))

    def test_clear(self):
        self.m.clear()
        self.failIf(self.m.get())
        self.failUnlessEqual(self.m.get_iter_first(), None)
        self.failUnlessEqual(self.m.get_iter_root(), None)

    def test_reorder(self):
        order = list(reversed(range(10)))
        self.m.reorder(order)
        self.failUnlessEqual(self.m.get(), order)

    def test_reorder_2(self):
        order = list(range(10))
        order[9] = 0
        order[0] = 9
        self.m.reorder(order)
        self.failUnlessEqual(self.m.get(), order)

    def test_swap(self):
        x = range(10)
        it1 = self.m.get_iter(9)
        it2 = self.m.get_iter(0)
        self.m.swap(it1, it2)
        x[0], x[9] = x[9], x[0]
        self.failUnlessEqual(self.m.get(), x)

        it1 = self.m.get_iter(9)
        self.m.swap(it1, it1)
        self.failUnlessEqual(self.m.get(), x)

    def test_move_after(self):
        x = range(10)
        it = self.m.get_iter(0)
        self.m.move_after(it, None)
        self.failUnlessEqual(self.m.get(), x)

        it = self.m.get_iter(0)
        it2 = self.m.get_iter(1)
        self.m.move_after(it, it2)
        x[0], x[1] = x[1], x[0]
        self.failUnlessEqual(self.m.get(), x)

    def test_move_after_2(self):
        x = range(10)
        it = self.m.get_iter(0)
        it2 = self.m.get_iter(1)
        self.m.move_after(it2, it)
        self.failUnlessEqual(self.m.get(), x)

        it3 = self.m.get_iter(0)
        it4 = self.m.get_iter(9)
        self.m.move_after(it3, it4)
        self.failIf(self.m.iter_is_valid(it3))
        self.failIf(self.m.iter_is_valid(it4))
        x.append(x.pop(0))
        self.failUnlessEqual(self.m.get(), x)

    def test_move_before(self):
        x = range(10)
        it = self.m.get_iter(9)
        self.m.move_before(it, None)
        self.failUnlessEqual(self.m.get(), x)

        it = self.m.get_iter(0)
        it2 = self.m.get_iter(1)
        self.m.move_before(it2, it)
        x[0], x[1] = x[1], x[0]
        self.failUnlessEqual(self.m.get(), x)

    def test_move_before_2(self):
        x = range(10)
        it = self.m.get_iter(0)
        it2 = self.m.get_iter(1)
        self.m.move_before(it, it2)
        self.failUnlessEqual(self.m.get(), x)

        it3 = self.m.get_iter(0)
        it4 = self.m.get_iter(9)
        self.m.move_before(it4, it3)
        self.failIf(self.m.iter_is_valid(it3))
        self.failIf(self.m.iter_is_valid(it4))
        x.insert(0, x.pop(9))
        self.failUnlessEqual(self.m.get(), x)

add(TPlaylistListStore)

class TPlaylistModel(TestCase):
    def setUp(self):
        self.pl = PlaylistModel()
        self.pl.set(range(10))
        do_events()
        self.failUnless(self.pl.current is None)

    def test_isempty(self):
        self.failIf(self.pl.is_empty())
        self.pl.clear()
        self.failUnless(self.pl.is_empty())

    def test_get(self):
        self.assertEqual(self.pl.get(), range(10))
        self.pl.set(range(12))
        gtk.main_iteration(False)
        self.assertEqual(self.pl.get(), range(12))

    def test_next(self):
        self.pl.next()
        self.failUnlessEqual(self.pl.current, 0)
        self.pl.next()
        self.failUnlessEqual(self.pl.current, 1)
        self.pl.go_to(9)
        self.failUnlessEqual(self.pl.current, 9)
        self.pl.next()
        self.failUnless(self.pl.current is None)

    def test_find(self):
        self.failUnlessEqual(self.pl[self.pl.find(8)][0], 8)
    def test_find_not_there(self):
        self.failUnless(self.pl.find(22) is None)

    def test_find_all(self):
        to_find = [1, 4, 5, 8, 9]
        iters = self.pl.find_all(to_find)
        for i, v in zip(iters, to_find):
            self.failUnlessEqual(self.pl[i][0], v)

    def test_find_all_some_missing(self):
        to_find = [1, 4, 18, 5, 8, 9, -1]
        iters = self.pl.find_all(to_find)
        to_find.remove(18)
        to_find.remove(-1)
        for i, v in zip(iters, to_find):
            self.failUnlessEqual(self.pl[i][0], v)

    def test_find_all_empty(self):
        to_find = [100, 200, -11]
        iters = self.pl.find_all(to_find)
        self.failUnlessEqual(iters, [])

    def test_contains(self):
        self.failUnless(1 in self.pl)
        self.failUnless(8 in self.pl)
        self.failIf(22 in self.pl)

    def test_removal(self):
        self.pl.go_to(8)
        for i in range(3, 8):
            self.pl.remove(self.pl.find(i))
        self.pl.next()
        self.failUnlessEqual(self.pl.current, 9)

    def test_next_repeat(self):
        self.pl.repeat = True
        self.pl.go_to(3)
        for i in range(9): self.pl.next()
        self.assertEqual(self.pl.current, 2)
        for i in range(12): self.pl.next()
        self.assertEqual(self.pl.current, 4)

    def test_shuffle(self):
        self.pl.order = ORDERS[1](self.pl)
        for i in range(5):
            numbers = [self.pl.current for i in range(10)
                       if self.pl.next() or True]
            self.assertNotEqual(numbers, range(10))
            numbers.sort()
            self.assertEqual(numbers, range(10))
            self.pl.next()
            self.assertEqual(self.pl.current, None)

    def test_weighted(self):
        self.pl.order = ORDERS[2](self.pl)
        r0 = AudioFile({'~#rating': 0})
        r1 = AudioFile({'~#rating': 1})
        r2 = AudioFile({'~#rating': 2})
        r3 = AudioFile({'~#rating': 3})
        self.pl.set([r0, r1, r2, r3])
        gtk.main_iteration(False)
        songs = [self.pl.current for i in range(1000)
                 if self.pl.next() or True]
        self.assert_(songs.count(r1) > songs.count(r0))
        self.assert_(songs.count(r2) > songs.count(r1))
        self.assert_(songs.count(r3) > songs.count(r2))

    def test_shuffle_repeat(self):
        self.pl.order = ORDERS[1](self.pl)
        self.pl.repeat = True
        numbers = [self.pl.current for i in range(30)
                   if self.pl.next() or True]
        allnums = range(10) * 3
        allnums.sort()
        self.assertNotEqual(numbers, allnums)
        numbers.sort()
        self.assertEqual(numbers, allnums)

    def test_onesong(self):
        self.pl.go_to(3)
        self.pl.order = ORDERS[3](self.pl)
        self.failUnlessEqual(self.pl.current, 3)
        self.pl.next()
        self.failUnlessEqual(self.pl.current, 4)
        self.pl.next_ended()
        self.failUnlessEqual(self.pl.current, None)

    def test_onesong_repeat(self):
        self.pl.go_to(3)
        self.pl.order = ORDERS[3](self.pl)
        self.pl.repeat = True
        self.failUnlessEqual(self.pl.current, 3)
        self.pl.next()
        self.failUnlessEqual(self.pl.current, 4)
        self.pl.next_ended()
        self.failUnlessEqual(self.pl.current, 4)

    def test_previous(self):
        self.pl.go_to(2)
        self.failUnlessEqual(self.pl.current, 2)
        self.pl.previous()
        self.failUnlessEqual(self.pl.current, 1)
        self.pl.previous()
        self.failUnlessEqual(self.pl.current, 0)
        self.pl.previous()
        self.failUnlessEqual(self.pl.current, 0)

    def test_go_to_saves_current(self):
        self.pl.go_to(5)
        self.failUnlessEqual(self.pl.current, 5)
        self.pl.set([5, 10, 15, 20])
        gtk.main_iteration(False)
        self.pl.next()
        self.failUnlessEqual(self.pl.current, 10)

    def test_go_to_order(self):
        self.pl.order = ORDERS[1](self.pl)
        for i in range(5):
            self.pl.go_to(5)
            self.failUnlessEqual(self.pl.current, 5)
            self.pl.go_to(1)
            self.failUnlessEqual(self.pl.current, 1)

    def test_go_to_none(self):
        for i in range(5):
            self.pl.go_to(None)
            self.failUnlessEqual(self.pl.current, None)
            self.pl.next()
            self.failUnlessEqual(self.pl.current, 0)

    def test_reset(self):
        self.pl.go_to(5)
        self.failUnlessEqual(self.pl.current, 5)
        self.pl.reset()
        self.failUnlessEqual(self.pl.current, None)
        self.pl.next()
        self.failUnlessEqual(self.pl.current, 0)

    def test_reset_order(self):
        self.pl.order = ORDERS[1](self.pl)
        self.pl.go_to(5)
        self.failUnlessEqual(self.pl.current, 5)
        self.pl.reset()
        self.failUnlessEqual(self.pl.current, None)

    def test_restart(self):
        self.pl.go_to(1)
        self.pl.set([101, 102, 103, 104])
        gtk.main_iteration(False)
        self.pl.next()
        self.failUnlessEqual(self.pl.current, 101)

    def test_next_nosong_536(self):
        self.pl.go_to(1)
        self.pl.repeat = True
        self.pl.order = ORDERS[1](self.pl)
        self.pl.set([])
        gtk.main_iteration(False)
        self.pl.next()

    def shutDown(self):
        self.pl.destroy()
add(TPlaylistModel)

class TPlaylistMux(TestCase):
    def setUp(self):
        self.q = PlaylistModel()
        self.pl = PlaylistModel()
        self.p = NullPlayer()
        self.mux = PlaylistMux(self.p, self.q, self.pl)
        self.failUnless(self.pl.current is None)

    def test_only_pl(self):
        self.pl.set(range(10))
        do_events()
        self.failUnless(self.mux.current is None)
        songs = [self.next() for i in range(10)]
        self.failUnlessEqual(songs, range(10))
        self.next()
        self.failUnless(self.mux.current is None)

    def test_only_q(self):
        self.q.set(range(10))
        do_events()
        self.failUnless(self.mux.current is None)
        songs = [self.next() for i in range(10)]
        self.failUnlessEqual(songs, range(10))
        self.next()
        self.failUnless(self.mux.current is None)

    def test_mixed(self):
        self.q.set(range(5))
        self.pl.set(range(5, 10))
        do_events()
        self.failUnless(self.mux.current is None)
        songs = [self.next() for i in range(10)]
        self.failUnlessEqual(songs, range(10))
        self.next()
        self.failUnless(self.mux.current is None)

    def test_newplaylist(self):
        self.pl.set(range(5, 10))
        do_events()
        self.failUnless(self.mux.current is None)
        self.mux.go_to(7)
        self.failUnlessEqual(self.mux.current, 7)
        self.pl.set([3, 5, 12, 11])
        do_events()
        self.failUnlessEqual(self.mux.current, None)
        self.pl.set([19, 8, 12, 3])
        do_events()
        self.failUnlessEqual(self.mux.current, None)
        self.pl.set([3, 7, 9, 11])
        do_events()
        self.mux.next()
        self.failUnlessEqual(self.mux.current, 9)

    def test_halfway(self):
        self.pl.set(range(10))
        do_events()
        self.failUnless(self.mux.current is None)
        songs = [self.next() for i in range(5)]
        self.q.set(range(100, 105))
        do_events()
        songs.extend([self.next() for i in range(10)])
        self.failUnlessEqual(
            songs, [0, 1, 2, 3, 4, 100, 101, 102, 103, 104, 5, 6, 7, 8, 9])
        self.next()
        self.failUnless(self.mux.current is None)

    def test_removal(self):
        self.pl.set(range(0, 5))
        self.q.set(range(10, 15))
        do_events()
        songs = [self.next() for i in range(3)]
        self.q.remove(self.q.find(14))
        self.q.remove(self.q.find(13))
        songs.extend([self.next() for i in range(5)])
        self.failUnlessEqual(songs, [10, 11, 12, 0, 1, 2, 3, 4])

    def next(self):
        self.mux.next()
        song = self.mux.current
        self.p.emit('song-started', self.mux.current)
        do_events()
        return song

    def test_goto(self):
        self.pl.set(range(10))
        self.q.set(range(10, 20))
        do_events()
        self.failUnless(self.mux.current is None)
        self.mux.go_to(5)
        self.failUnlessEqual(self.mux.current, 5)
        self.mux.go_to(2)
        self.failUnlessEqual(self.mux.current, 2)
        self.failUnlessEqual(self.next(), 10)
        self.mux.go_to(7)
        self.failUnlessEqual(self.mux.current, 7)
        self.failUnlessEqual(self.next(), 11)

    def test_random_queue_666(self):
        for i in range(5):
            self.mux.go_to(None)
            self.pl.set([1])
            do_events()
            self.failUnless(self.mux.current is None)
            self.q.order = ORDERS[1](self.pl)
            self.failUnless(self.next() == 1)
            self.q.set([10, 11])
            do_events()
            value = self.next()
            self.failUnless(
                value in [10, 11], "got %r, expected 10 or 11" % value)
            if value == 10: next = 11
            else: next = 10
            self.failUnlessEqual(self.next(), next)

    def tearDown(self):
        self.p.destroy()
add(TPlaylistMux)

class TSongList(TestCase):
    HEADERS = ["acolumn", "~#lastplayed", "~foo~bar", "~#rating",
               "~#length", "~dirname", "~#track"]
    def setUp(self):
        quodlibet.config.init()
        self.songlist = SongList(SongLibrary())

    def test_set_all_column_headers(self):
        SongList.set_all_column_headers(self.HEADERS)
        headers = [col.header_name for col in self.songlist.get_columns()]
        self.failUnlessEqual(headers, self.HEADERS)

    def test_set_column_headers(self):
        self.songlist.set_column_headers(self.HEADERS)
        headers = [col.header_name for col in self.songlist.get_columns()]
        self.failUnlessEqual(headers, self.HEADERS)

    def test_drop(self):
        self.songlist.enable_drop()
        self.songlist.disable_drop()

    def test_sort_by(self):
        self.songlist.set_column_headers(["one", "two", "three"])
        for key, order in [("one", True),
                           ("two", False),
                           ("three", False)]:
            self.songlist.set_sort_by(None, tag=key, order=order)
            self.failUnlessEqual(self.songlist.get_sort_by(), (key, order))
        self.songlist.set_sort_by(self.songlist.get_columns()[-1], tag="three")
        self.failUnlessEqual(self.songlist.get_sort_by(), ("three", True))

    def tearDown(self):
        self.songlist.destroy()
        quodlibet.config.quit()
add(TSongList)
