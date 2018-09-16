# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase

from gi.repository import Gtk

from quodlibet.player.nullbe import NullPlayer
from quodlibet.qltk.songmodel import PlaylistModel, PlaylistMux
from quodlibet.qltk.playorder import Order, OrderShuffle, OrderInOrder, \
    RepeatSongForever, RepeatListForever
import quodlibet.config


def do_events():
    while Gtk.events_pending():
        Gtk.main_iteration()


class TPlaylistModel(TestCase):
    def setUp(self):
        self.pl = PlaylistModel()
        self.pl.set(range(10))
        do_events()
        self.failUnless(self.pl.current is None)

    def test_current_recover(self):
        self.pl.set(range(10))
        self.pl.next()
        self.failUnlessEqual(self.pl.current, 0)
        self.pl.set(range(20, 30))
        self.failUnless(self.pl.current is None)
        self.pl.current_iter = self.pl.current_iter
        self.failUnless(self.pl.current is None)
        self.pl.set(range(10))
        self.failUnlessEqual(self.pl.current, 0)

    def test_current_recover_unknown(self):
        self.pl.set([1, 2, 3, 4])
        self.assertIs(self.pl.go_to(5), None)
        self.pl.set([1, 2, 3, 4, 5])
        self.assertEqual(self.pl.current, 5)
        self.assertIsNot(self.pl.go_to(4), None)
        self.assertEqual(self.pl.current, 4)

    def test_isempty(self):
        self.failIf(self.pl.is_empty())
        self.pl.clear()
        self.failUnless(self.pl.is_empty())

    def test_get(self):
        self.assertEqual(self.pl.get(), list(range(10)))
        self.pl.set(range(12))
        Gtk.main_iteration_do(False)
        self.assertEqual(self.pl.get(), list(range(12)))

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

    def test_find_all_duplicates(self):
        # ignore duplicates in parameters
        self.assertTrue(len(self.pl.find_all([1, 1])), 1)
        # but find duplicates
        self.pl.set([1, 1])
        self.assertTrue(len(self.pl.find_all([1])), 2)

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

    def test_next_at_end_finishes(self):
        self.pl.go_to(9)
        self.pl.next()
        self.assertEqual(self.pl.current, None)

    def test_shuffle(self):
        self.pl.order = OrderShuffle()
        for i in range(5):
            history = [self.pl.current for _ in range(10)
                       if self.pl.next() or True]
            self.assertNotEqual(history, list(range(10)))
            self.assertEqual(sorted(history), list(range(10)))
            self.pl.next()
            self.assertEqual(self.pl.current, None)
            self.pl.order.reset(self.pl)

    def test_shuffle_repeat_forever(self):
        self.pl.order = RepeatSongForever(OrderShuffle())
        old = self.pl.current
        for i in range(5):
            self.pl.next_ended()
            self.assertEqual(self.pl.current, old)

    def test_shuffle_repeat(self):
        self.pl.order = RepeatListForever(OrderShuffle())
        numbers = [self.pl.current for _ in range(30)
                   if self.pl.next_ended() or True]
        allnums = sorted(list(range(10)) * 3)
        self.assertNotEqual(numbers, allnums)
        numbers.sort()
        self.assertEqual(numbers, allnums)

    def test_repeat_song_repeats_on_end(self):
        self.pl.order = RepeatSongForever(OrderInOrder())
        self.pl.go_to(3)
        self.failUnlessEqual(self.pl.current, 3)
        self.pl.next_ended()
        self.failUnlessEqual(self.pl.current, 3)

    def test_repeat_song_uses_underlying_on_explicit(self):
        self.pl.order = RepeatSongForever(OrderInOrder())
        self.pl.go_to(3)
        self.pl.next()
        self.failUnlessEqual(self.pl.current, 4)

    def test_repeat_all_cycles_playlist(self):
        self.pl.go_to(3)
        self.pl.order = RepeatListForever(OrderInOrder())
        self.failUnlessEqual(self.pl.current, 3)
        self.pl.next()
        self.failUnlessEqual(self.pl.current, 4)
        for i in range(9):
            self.pl.next_ended()
        self.failUnlessEqual(self.pl.current, 3)

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
        Gtk.main_iteration_do(False)
        self.pl.next()
        self.failUnlessEqual(self.pl.current, 10)

    def test_go_to_order(self):
        self.pl.order = OrderShuffle()
        for i in range(5):
            self.pl.go_to(5)
            self.failUnlessEqual(self.pl.current, 5)
            self.pl.go_to(1)
            self.failUnlessEqual(self.pl.current, 1)

    def test_go_to(self):

        class SetOrder(Order):
            # most orders don't change iter here,
            # so make sure this gets handled right
            def set_explicit(self, playlist, iter):
                return playlist.iter_next(iter)

            def set_implicit(self, playlist, iter):
                return playlist.iter_next(playlist.iter_next(iter))

        self.pl.order = SetOrder()
        self.failUnlessEqual(self.pl[self.pl.go_to(5, True)][0], 6)
        self.failUnlessEqual(self.pl[self.pl.go_to(5, False)][0], 7)

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
        self.failUnlessEqual(self.pl.current, 0)

    def test_reset_order(self):
        self.pl.order = OrderInOrder()
        self.pl.go_to(5)
        self.failUnlessEqual(self.pl.current, 5)
        self.pl.reset()
        self.failUnlessEqual(self.pl.current, 0)

    def test_restart(self):
        self.pl.go_to(1)
        self.pl.set([101, 102, 103, 104])
        Gtk.main_iteration_do(False)
        self.pl.next()
        self.failUnlessEqual(self.pl.current, 101)

    def test_next_nosong_536(self):
        self.pl.go_to(1)
        self.pl.order = OrderShuffle()
        self.pl.set([])
        Gtk.main_iteration_do(False)
        self.pl.next()

    def test_clear_current(self):
        self.pl.go_to(1)
        self.pl.clear()
        self.pl.go_to(None)

    def shutDown(self):
        self.pl.destroy()


class TPlaylistMux(TestCase):
    def setUp(self):
        self.q = PlaylistModel()
        self.pl = PlaylistModel()
        self.p = NullPlayer()
        self.mux = PlaylistMux(self.p, self.q, self.pl)
        self.p.setup(self.mux, None, 0)
        self.failUnless(self.pl.current is None)
        quodlibet.config.init()

    def test_destroy(self):
        self.mux.destroy()

    def test_only_pl(self):
        self.pl.set(range(10))
        do_events()
        self.failUnless(self.mux.current is None)
        songs = [self.next() for i in range(10)]
        self.failUnlessEqual(songs, list(range(10)))
        self.next()
        self.failUnless(self.mux.current is None)

    def test_only_q(self):
        self.q.set(range(10))
        do_events()
        self.failUnless(self.mux.current is None)
        songs = [self.next() for i in range(10)]
        self.failUnlessEqual(songs, list(range(10)))
        self.next()
        self.failUnless(self.mux.current is None)

    def test_mixed(self):
        self.q.set(range(5))
        self.pl.set(range(5, 10))
        do_events()
        self.failUnless(self.mux.current is None)
        songs = [self.next() for i in range(10)]
        self.failUnlessEqual(songs, list(range(10)))
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
            self.q.order = OrderShuffle()
            self.failUnless(self.next() == 1)
            self.q.set([10, 11])
            do_events()
            value = self.next()
            self.failUnless(
                value in [10, 11], "got %r, expected 10 or 11" % value)
            if value == 10:
                next = 11
            else:
                next = 10
            self.failUnlessEqual(self.next(), next)

    def test_sourced(self):
        self.pl.set(range(10))
        self.q.set(range(10))
        self.mux.go_to(None)
        self.failUnless(self.pl.sourced)
        self.q.go_to(1)
        self.p.next()
        self.failIf(self.pl.sourced)

    def test_unqueue(self):
        self.q.set(range(100))
        self.mux.unqueue(range(100))
        self.failIf(len(self.q))

    def test_queue(self):
        self.mux.enqueue(range(40))
        self.failUnlessEqual(list(self.q.itervalues()), list(range(40)))

    def test_queue_move_entry(self):
        self.q.set(range(10))
        self.p.next()
        self.assertEqual(self.p.song, 0)
        self.q.move_after(self.q[-1].iter, None)
        self.p.next()
        self.assertEqual(self.p.song, 9)

    def test_goto_queue(self):
        self.pl.set(range(20, 30))
        self.q.set(range(10))
        self.mux.go_to(self.q[-1].iter, source=self.q)
        self.assertTrue(self.q.sourced)
        self.assertEqual(self.mux.current, self.q[-1][0])

    def test_queue_ignore(self):
        self.pl.set(range(10))
        self.q.set(range(10))

        quodlibet.config.set("memory", "queue_ignore", True)
        self.next()
        self.failUnlessEqual(len(self.pl.get()), len(range(10)))
        self.failUnlessEqual(len(self.q.get()), len(range(10)))

        quodlibet.config.set("memory", "queue_ignore", False)
        self.next()
        self.failUnlessEqual(len(self.pl.get()), len(range(10)))
        self.failUnlessEqual(len(self.q.get()), len(range(10)) - 1)

    def test_queue_keep_songs(self):
        self.q.set(range(10))

        quodlibet.config.set("memory", "queue_keep_songs", True)
        self.next()
        self.failUnlessEqual(len(self.q.get()), len(range(10)))
        self.failUnlessEqual(self.q.current, 0)
        self.next()
        self.failUnlessEqual(len(self.q.get()), len(range(10)))
        self.failUnlessEqual(self.q.current, 1)

        quodlibet.config.set("memory", "queue_keep_songs", False)
        self.next()
        self.failUnlessEqual(len(self.q.get()), len(range(10)) - 1)
        self.failUnless(self.q.current is None)

    def tearDown(self):
        self.p.destroy()
