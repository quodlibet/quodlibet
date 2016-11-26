# -*- coding: utf-8 -*-
# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import pickle

from tests import TestCase

from quodlibet.compat import cBytesIO
from quodlibet.util.picklehelper import pickle_load, pickle_loads, pickle_dumps


class A(dict):
    pass


class B(dict):
    pass


class Tpickle_load(TestCase):

    def test_pickle_load(self):
        data = {b"foo": u"bar", u"quux": b"baz"}

        for protocol in [0, 1, 2]:
            assert pickle_loads(pickle.dumps(data)) == data
            assert pickle_load(cBytesIO(pickle.dumps(data))) == data

    def test_invalid(self):
        with self.assertRaises(pickle.UnpicklingError):
            pickle_loads(b"")

        with self.assertRaises(pickle.UnpicklingError):
            pickle_load(cBytesIO(b""))

    def test_switch_class(self):

        def lookup_func(base, module, name):
            if name == "A":
                return B
            return base(module, name)

        value = pickle_loads(pickle.dumps(A()), lookup_func)
        assert isinstance(value, B)

    def test_pickle_dumps(self):
        v = [u"foo", b"bar", 42]
        for protocol in [0, 1, 2]:
            assert pickle_loads(pickle_dumps(v)) == v

    def test_pickle_dumps_fail(self):

        class A(object):
            def __getstate__(self):
                raise Exception

        with self.assertRaises(pickle.PicklingError):
            pickle_dumps(A())
