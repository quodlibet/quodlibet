# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import threading

import pytest as pytest

from tests import TestCase, run_gtk_loop

from gi.repository import Gtk

from quodlibet.util.thread import (
    call_async,
    call_async_background,
    Cancellable,
    terminate_all,
)


class Tcall_async(TestCase):
    @pytest.mark.flaky(max_runs=4, min_passes=2)
    def test_main(self):
        cancel = Cancellable()

        data = []

        def func():
            data.append(threading.current_thread().name)

        def callback(result):
            data.append(threading.current_thread().name)

        call_async(func, cancel, callback)
        Gtk.main_iteration()
        run_gtk_loop()

        call_async_background(func, cancel, callback)
        Gtk.main_iteration()
        run_gtk_loop()

        main_name = threading.current_thread().name
        self.assertEqual(len(data), 4)
        self.assertNotEqual(data[0], main_name)
        self.assertEqual(data[1], main_name)
        self.assertNotEqual(data[2], main_name)
        self.assertEqual(data[3], main_name)

    def test_cancel(self):
        def func():
            assert 0

        def callback(result):
            assert 0

        cancel = Cancellable()
        cancel.cancel()
        call_async(func, cancel, callback)
        Gtk.main_iteration()
        run_gtk_loop()

    def test_terminate_all(self):
        terminate_all()
