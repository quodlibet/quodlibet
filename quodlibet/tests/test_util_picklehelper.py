# -*- coding: utf-8 -*-
# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import pickle

from tests import TestCase

from quodlibet.compat import cBytesIO
from quodlibet.util.picklehelper import unpickle_load, unpickle_loads


class A(dict):
    pass


class B(dict):
    pass


class Tunpickle_load(TestCase):

    def test_unpickle_load(self):
        data = {b"foo": u"bar", u"quux": b"baz"}

        for protocol in [0, 1, 2]:
            assert unpickle_loads(pickle.dumps(data)) == data
            assert unpickle_load(cBytesIO(pickle.dumps(data))) == data

    def test_invalid(self):
        with self.assertRaises(pickle.UnpicklingError):
            unpickle_loads(b"")

        with self.assertRaises(pickle.UnpicklingError):
            unpickle_load(cBytesIO(b""))

    def test_switch_class(self):

        def lookup_func(base, module, name):
            if name == "A":
                return B
            return base(module, name)

        value = unpickle_loads(pickle.dumps(A()), lookup_func)
        assert isinstance(value, B)
