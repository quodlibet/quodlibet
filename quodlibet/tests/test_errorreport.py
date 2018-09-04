# -*- coding: utf-8 -*-
# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys
import os
import shutil

from gi.repository import Gtk

from quodlibet.errorreport import faulthandling, enable_errorhook, errorhook
from quodlibet.errorreport.faulthandling import FaultHandlerCrash
from quodlibet.errorreport.logdump import dump_to_disk
from quodlibet.errorreport.ui import ErrorDialog, SubmitErrorDialog
from quodlibet.errorreport.main import get_sentry
from quodlibet.errorreport.sentrywrapper import SentryError, CapturedException

from . import TestCase, mkdtemp
from .helper import temp_filename


class Tfaulthandling(TestCase):

    def test_basic(self):
        with temp_filename() as filename:
            faulthandling.enable(filename)
            faulthandling.raise_and_clear_error()
            faulthandling.disable()

    def test_error(self):
        with temp_filename() as filename:
            with open(filename, "wb") as h:
                h.write(b"something")
            faulthandling.enable(filename)
            with self.assertRaises(FaultHandlerCrash):
                faulthandling.raise_and_clear_error()
            faulthandling.disable()

    def test_stacktrace_grouping(self):
        stack1 = 'File "%s", line 486 in string_at' % (
            os.path.join("foo", "bar", "quux.py"),)
        stack2 = 'File "%s", line 350 in string_at' % (
            os.path.join("baz", "bar", "quux.py"),)
        stack3 = 'File "%s", line 350 in other' % (
            os.path.join("baz", "bar", "quux.py"),)

        key1 = FaultHandlerCrash(stack1).get_grouping_key()
        key2 = FaultHandlerCrash(stack2).get_grouping_key()
        key3 = FaultHandlerCrash(stack3).get_grouping_key()

        assert key1 and key2 and key3
        assert key1 == key2 != key3


class Tlogdump(TestCase):

    def test_main(self):
        temp_dir = mkdtemp()
        try:
            dump_dir = os.path.join(temp_dir, "dump")

            try:
                raise Exception("foo")
            except Exception:
                dump_to_disk(dump_dir, sys.exc_info())

            assert len(os.listdir(dump_dir)) == 1
        finally:
            shutil.rmtree(temp_dir)


class Terrorui(TestCase):

    def test_main(self):
        w = Gtk.Window()
        ErrorDialog(w, u"foo").destroy()
        ErrorDialog(w, u"foo").destroy()
        SubmitErrorDialog(w, u"foo").destroy()


class Terrorreport(TestCase):

    def test_enable(self):
        enable_errorhook(True)
        enable_errorhook(False)
        try:
            raise Exception
        except Exception:
            errorhook()


class Tsentrywrapper(TestCase):

    def test_main(self):
        sentry = get_sentry()
        try:
            raise Exception
        except Exception:
            exc_info = sys.exc_info()

        try:
            err = sentry.capture(exc_info)
        except SentryError:
            return

        assert isinstance(err, CapturedException)
        assert isinstance(err.get_report(), str)

        err.set_comment(u"foo")
        err.set_comment(u"bar")
