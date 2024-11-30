# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from collections import defaultdict

from quodlibet.formats import AudioFile
from quodlibet.order import OrderInOrder
from quodlibet.order.reorder import OrderWeighted, OrderShuffle
from quodlibet.order.repeat import OneSong
from quodlibet.qltk.songmodel import PlaylistModel
from tests import TestCase

r0 = AudioFile({"~#rating": 0})
r1 = AudioFile({"~#rating": 0.33})
r2 = AudioFile({"~#rating": 0.66})
r3 = AudioFile({"~#rating": 1.0})


class TOrderWeighted(TestCase):

    def test_weighted(self):
        pl = PlaylistModel()
        pl.set([r3, r1, r2, r0])
        order = OrderWeighted()
        scores = defaultdict(int)
        for _i in range(500):
            order.reset(pl)
            cur = pl.current_iter
            for j in range(3, -1, -1):
                cur = order.next_explicit(pl, cur)
                scores[pl[cur][0]] += j
        assert scores[r1] > scores[r0]
        assert scores[r2] > scores[r1]
        assert scores[r3] > scores[r2]


class TOrderShuffle(TestCase):

    def test_remaining(self):
        order = OrderShuffle()
        pl = PlaylistModel()
        songs = [r3, r1, r2, r0]
        pl.set(songs)
        cur = pl.current_iter
        for i in range(4, 0, -1):
            cur = order.next_explicit(pl, cur)
            self.assertEqual(len(order.remaining(pl)), i)
        # The playlist should reset after the last song
        cur = order.next_explicit(pl, cur)
        self.assertEqual(len(order.remaining(pl)), len(songs))


class TOrderOneSong(TestCase):

    def test_remaining(self):
        order = OneSong(OrderInOrder())
        pl = PlaylistModel(OrderInOrder)
        pl.set([r0, r1])
        for _i in range(2):
            self.assertEqual(order.next(pl, pl.current_iter), None)
