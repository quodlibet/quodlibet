# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from collections import defaultdict

from quodlibet.formats import AudioFile
from quodlibet.order.reorder import OrderWeighted, OrderShuffle
from quodlibet.qltk.songmodel import PlaylistModel
from tests import TestCase

r0 = AudioFile({'~#rating': 0})
r1 = AudioFile({'~#rating': 0.33})
r2 = AudioFile({'~#rating': 0.66})
r3 = AudioFile({'~#rating': 1.0})


class TOrderWeighted(TestCase):

    def test_weighted(self):
        pl = PlaylistModel()
        pl.set([r3, r1, r2, r0])
        order = OrderWeighted()
        scores = defaultdict(int)
        for i in range(500):
            order.reset(pl)
            cur = pl.current_iter
            for j in range(3, -1, -1):
                cur = order.next_explicit(pl, cur)
                scores[pl[cur][0]] += j
        self.failUnless(scores[r1] > scores[r0])
        self.failUnless(scores[r2] > scores[r1])
        self.failUnless(scores[r3] > scores[r2])


class TOrderShuffle(TestCase):

    def test_remaining(self):
        order = OrderShuffle()
        pl = PlaylistModel()
        pl.set([r3, r1, r2, r0])
        cur = pl.current_iter
        for i in range(4, -1, -1):
            cur = order.next_explicit(pl, cur)
            self.failUnlessEqual(len(order.remaining(pl)), i)
