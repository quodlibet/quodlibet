# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import sys
from pathlib import Path
from unittest import mock

import pytest
from gi.repository import GLib, Gio
from senf import fsn2bytes, bytes2fsn

from . import TestCase, skipIf
from .helper import temp_filename

import quodlibet
from quodlibet.remote import QuodLibetUnixRemote
from quodlibet.util import is_windows


QLPATH = str(Path(quodlibet.__file__).resolve().parent.parent)


class Mock:
    def __init__(self, resp=None):
        self.lines = []
        self.resp = resp

    def handle_line(self, app, line):
        self.lines.append(line)
        return self.resp


@skipIf(is_windows(), "unix only")
class TUnixRemote(TestCase):

    def test_fifo(self):
        mock = Mock()
        remote = QuodLibetUnixRemote(None, mock)
        remote._callback(b"foo\n")
        remote._callback(b"bar\nbaz")
        self.assertEqual(
            mock.lines, [bytes2fsn(b, None) for b in [b"foo", b"bar", b"baz"]])

    def test_response(self):
        with temp_filename() as fn:
            mock = Mock(resp=bytes2fsn(b"resp", None))
            remote = QuodLibetUnixRemote(None, mock)
            remote._callback(b"\x00foo\x00" + fsn2bytes(fn, None) + b"\x00")
            self.assertEqual(mock.lines, [bytes2fsn(b"foo", None)])
            with open(fn, "rb") as h:
                self.assertEqual(h.read(), b"resp")


@skipIf(is_windows(), "unix only")
class TUnixRemoteFifoFullCycle(TestCase):
    @pytest.fixture(autouse=True)
    def tmp_fifo_path(self, tmp_path):
        self.registry = Mock(resp=bytes2fsn(b"response", None))
        self.tmp_path = tmp_path
        with mock.patch.object(QuodLibetUnixRemote, "_PATH", str(tmp_path / "control")):
            yield

    def _send_message_remote_proc(self, msg, callback):
        """Execute QuodLibetUnixRemote.send_message() in a child process"""
        # Using a child process is the only way to execute send_message, as it
        # can only be run on the main thread, and blocks waiting for the
        # response. It can't be run in a separate thread, because it uses
        # signals to handle timeouts and we can't run the GLib mainloop in a
        # thread as Gtk has already been initialised on the Python main thread.
        # Attempting to use the loop in a thread leads to segfaults.
        temp_script = self.tmp_path / "send_message.py"
        with temp_script.open("w") as fpy:
            fpy.write(
                f"""\
import sys
import traceback
from quodlibet.remote import QuodLibetUnixRemote

QuodLibetUnixRemote._PATH = {QuodLibetUnixRemote._PATH!r}

msg = sys.stdin.read()
try:
    result = QuodLibetUnixRemote.send_message(msg)
except Exception:
    traceback.print_exc(file=sys.stderr)
else:
    sys.stdout.buffer.write(result)
    sys.stdout.flush()
"""
            )

        def finished(proc, result):
            try:
                success, stdout, stderr = proc.communicate_finish(result)
            except GLib.Error as ex:
                callback(None, ex)
            else:
                if not success:
                    return
                if stderr.get_size():
                    callback(None, stderr.get_data().decode())
                callback(stdout.get_data(), None)

        try:
            launcher = Gio.SubprocessLauncher.new(
                Gio.SubprocessFlags.STDOUT_PIPE
                | Gio.SubprocessFlags.STDERR_PIPE
                | Gio.SubprocessFlags.STDIN_PIPE
            )
            path = [QLPATH]
            if "PYTHONPATH" in os.environ:
                path.append(os.environ["PYTHONPATH"])
            launcher.setenv("PYTHONPATH", ":".join(path), True)
            proc = launcher.spawnv([sys.executable, str(temp_script)])

            input = GLib.Bytes.new(msg)
            proc.communicate_async(input, None, finished)
        except Exception as ex:
            callback(None, ex)

    def send_message(self, msg: str) -> bytes:
        """Send a message to a remote

        Runs the GLib main loop, with the QuodLibetUnixRemote listener active,
        sends it a message and waits for the response.

        """
        result = error = None
        remote = None
        loop = GLib.MainLoop()

        def proc_callback(*res):
            nonlocal result, error
            result, error = res
            remote.stop()
            loop.quit()

        def run_receiver_and_remote():
            nonlocal remote
            remote = QuodLibetUnixRemote(None, self.registry)
            remote.start()
            GLib.idle_add(self._send_message_remote_proc, msg, proc_callback)

        GLib.idle_add(run_receiver_and_remote)
        loop.run()
        if error is not None:
            if isinstance(error, str):
                pytest.fail(error, pytrace=False)
            raise error
        return result

    def test_remote_send_message(self):
        response = self.send_message(b"foo 42")

        self.assertEqual(self.registry.lines, [bytes2fsn(b"foo 42", None)])
        self.assertEqual(response, b"response")
