# -*- coding: utf-8 -*-
# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase
from io import BytesIO

from quodlibet.util.picklehelper import pickle_load, pickle_loads, \
    pickle_dumps, pickle_dump, PicklingError, UnpicklingError


class A(dict):
    pass


class B(dict):
    pass


class Tpickle_load(TestCase):

    def test_pickle_load(self):
        data = {b"foo": u"bar", u"quux": b"baz"}

        for protocol in [0, 1, 2]:
            assert pickle_loads(pickle_dumps(data)) == data
            assert pickle_load(BytesIO(pickle_dumps(data))) == data

    def test_invalid(self):
        with self.assertRaises(UnpicklingError):
            pickle_loads(b"")

        with self.assertRaises(UnpicklingError):
            pickle_load(BytesIO(b""))

    def test_switch_class(self):

        def lookup_func(base, module, name):
            if name == "A":
                return B
            return base(module, name)

        value = pickle_loads(pickle_dumps(A()), lookup_func)
        assert isinstance(value, B)

    def test_pickle_dumps(self):
        v = [u"foo", b"bar", 42]
        for protocol in [0, 1, 2]:
            assert pickle_loads(pickle_dumps(v)) == v

    def test_pickle_dumps_fail(self):

        class A(object):
            def __getstate__(self):
                raise Exception

        with self.assertRaises(PicklingError):
            pickle_dumps(A())

    def test_pickle_dump(self):
        f = BytesIO()
        pickle_dump(42, f)
        assert pickle_loads(f.getvalue()) == 42

    def test_protocols(self):
        pickle_dumps(42, 0)
        pickle_dumps(42, 1)
        pickle_dumps(42, 2)

        with self.assertRaises(ValueError):
            pickle_dumps(42, -1)

        with self.assertRaises(ValueError):
            pickle_dumps(42, 3)
