# -*- coding: utf-8 -*-
# Copyright 2014 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from .helper import capture_output
from quodlibet import cli
from quodlibet.util.string import join_escape
from tests import TestCase
import os
import tempfile

from contextlib import contextmanager


@contextmanager
def working_directory(directory):
    owd = os.getcwd()
    try:
        os.chdir(directory)
        yield directory
    finally:
        os.chdir(owd)


class Tcli(TestCase):

    def test_process_no_arguments_works(self):
        with capture_output() as (out, err):
            cli.process_arguments(["myprog"])
            self.assertFalse(out.getvalue())
            self.assertFalse(err.getvalue())

    def test_process_arguments_errors_on_invalid_opt(self):
        with self.assertRaises(SystemExit):
            with capture_output():
                cli.process_arguments(["myprog", "--wrong-thing"])

    def test_command_norun(self):
        with self.assertRaises(SystemExit):
            with capture_output():
                cli.process_arguments(["myprog", "--enqueue", "hi"])

    def test_enqueue_notfile(self):
        tdir = tempfile.gettempdir()
        # Can't get known non-file the correct way in some setups so fake it
        # (nfile, npath) = tempfile.mkstemp(dir=tdir)
        # nname = os.path.basename(npath)
        # os.remove(npath)
        nname = "NOT_A_FILE"
        with working_directory(tdir):
            with capture_output():
                self.assertEqual(
                    cli.process_arguments(["myprog", "--run",
                                           "--enqueue", nname]),
                    (['run'], [('enqueue', nname)]))

    def test_enqueue_file(self):
        tdir = tempfile.gettempdir()
        (tfile, tpath) = tempfile.mkstemp(dir=tdir)
        tname = os.path.basename(tpath)
        try:
            with working_directory(tdir):
                with capture_output():
                    self.assertEqual(
                        cli.process_arguments(["myprog", "--run",
                                               "--enqueue", tname]),
                        (['run'], [('enqueue', tpath)]))
        finally:
            True # can't remove files in some test setups - os.remove(tpath)

    def test_enqueue_files(self):
        tdir = tempfile.gettempdir()
        (tfile, tpath) = tempfile.mkstemp(dir=tdir)
        tname = os.path.basename(tpath)
        # Can't get known non-file the correct way in some setups so fake it
        # (nfile, npath) = tempfile.mkstemp(dir=tdir)
        # nname = os.path.basename(npath)
        # os.remove(npath)
        nname = "NOT_A_FILE"
        try:
            with working_directory(tdir):
                with capture_output():
                    self.assertEqual(
                        cli.process_arguments(["myprog", "--run",
                                               "--enqueue-files",
                                               nname + "," + tname]),
                        (['run'], [('enqueue-files',
                                    join_escape([nname, tpath], ","))]))
        finally:
            True # can't remove files in some test setups - os.remove(tpath)
