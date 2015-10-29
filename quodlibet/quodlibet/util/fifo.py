# -*- coding: utf-8 -*-
# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import errno
import signal
import stat
import tempfile

try:
    import fcntl
    fcntl
except ImportError:
    fcntl = None

from gi.repository import GLib

from quodlibet.util.path import mkdir

FIFO_TIMEOUT = 10
"""time in seconds until we give up writing/reading"""


def _write_fifo(fifo_path, data):
    """Writes the data to the fifo or raises EnvironmentError"""

    # this will raise if the fifo doesn't exist or there is no reader
    try:
        fifo = os.open(fifo_path, os.O_WRONLY | os.O_NONBLOCK)
    except OSError:
        try:
            os.unlink(fifo_path)
        except OSError:
            pass
        raise
    else:
        try:
            os.close(fifo)
        except OSError:
            pass

    try:
        # This is a total abuse of Python! Hooray!
        signal.signal(signal.SIGALRM, lambda: "" + 2)
        signal.alarm(FIFO_TIMEOUT)
        with open(fifo_path, "wb") as f:
            signal.signal(signal.SIGALRM, signal.SIG_IGN)
            f.write(data)
    except (OSError, IOError, TypeError):
        # Unable to write to the fifo. Removing it.
        try:
            os.unlink(fifo_path)
        except OSError:
            pass
        raise EnvironmentError("Couldn't write to fifo %r" % fifo_path)


def split_message(data):
    """Split incoming data in pairs of (command, fifo path or None)

    This supports two data formats:
    Newline seperated commands without a return fifo path.
    and "NULL<command>NULL<fifo-path>NULL"

    Raises ValueError
    """

    arg = 0
    args = []
    while data:
        if arg == 0:
            index = data.find("\x00")
            if index == 0:
                arg = 1
                data = data[1:]
                continue
            if index == -1:
                elm = data
                data = ""
            else:
                elm, data = data[:index], data[index:]
            for l in elm.splitlines():
                yield (l, None)
        elif arg == 1:
            elm, data = data.split("\x00", 1)
            args.append(elm)
            arg = 2
        elif arg == 2:
            elm, data = data.split("\x00", 1)
            args.append(elm)
            yield tuple(args)
            del args[:]
            arg = 0


def write_fifo(fifo_path, data):
    """Writes the data to the fifo and returns a response
    or raises EnvironmentError.
    """

    fd, filename = tempfile.mkstemp()
    try:
        os.close(fd)
        os.unlink(filename)
        # mkfifo fails if the file exists, so this is safe.
        os.mkfifo(filename, 0o600)

        _write_fifo(fifo_path, "\x00" + data + "\x00" + filename + "\x00")

        try:
            signal.signal(signal.SIGALRM, lambda: "" + 2)
            signal.alarm(FIFO_TIMEOUT)
            with open(filename, "rb") as h:
                signal.signal(signal.SIGALRM, signal.SIG_IGN)
                return h.read()
        except TypeError:
            raise EnvironmentError("timeout")
    finally:
        try:
            os.unlink(filename)
        except EnvironmentError:
            pass


def fifo_exists(fifo_path):
    # https://github.com/quodlibet/quodlibet/issues/1131
    # FIXME: There is a race where control() creates a new file
    # instead of writing to the FIFO, confusing the next QL instance.
    # Remove non-FIFOs here for now.
    try:
        if not stat.S_ISFIFO(os.stat(fifo_path).st_mode):
            print_d("%r not a FIFO. Removing it." % fifo_path)
            os.remove(fifo_path)
    except OSError:
        pass
    return os.path.exists(fifo_path)


class FIFOError(Exception):
    pass


class FIFO(object):
    """Creates and reads from a FIFO"""

    def __init__(self, path, callback):
        self._callback = callback
        self._path = path

    def open(self):
        """Create the fifo and listen to it.

        Might raise FIFOError in case another process is already using it.
        """

        self._open(False, None)

    def destroy(self):
        if self._id is not None:
            GLib.source_remove(self._id)
            self._id = None

        try:
            os.unlink(self._path)
        except EnvironmentError:
            pass

    def _open(self, ignore_lock, *args):
        from quodlibet import qltk

        self._id = None
        mkdir(os.path.dirname(self._path))
        try:
            os.mkfifo(self._path, 0o600)
        except OSError:
            # maybe exists, we'll fail below otherwise
            pass

        try:
            fifo = os.open(self._path, os.O_NONBLOCK)
        except OSError:
            return

        while True:
            try:
                fcntl.flock(fifo, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except IOError as e:
                # EINTR on linux
                if e.errno == errno.EINTR:
                    continue
                if ignore_lock:
                    break
                # OSX doesn't support fifo locking, so check errno
                if e.errno == errno.EWOULDBLOCK:
                    raise FIFOError("fifo already locked")
                else:
                    print_d("fifo locking failed: %r" % e)
            break

        try:
            f = os.fdopen(fifo, "r", 4096)
        except OSError:
            pass

        self._id = qltk.io_add_watch(
            f, GLib.PRIORITY_DEFAULT,
            GLib.IO_IN | GLib.IO_ERR | GLib.IO_HUP,
            self._process, *args)

    def _process(self, source, condition, *args):
        if condition in (GLib.IO_ERR, GLib.IO_HUP):
            self._open(True, *args)
            return False

        while True:
            try:
                data = source.read()
            except (IOError, OSError) as e:
                if e.errno in (errno.EWOULDBLOCK, errno.EAGAIN):
                    return True
                elif e.errno == errno.EINTR:
                    continue
                else:
                    self.__open(*args)
                    return False
            break

        if not data:
            self._open(*args)
            return False

        self._callback(data)

        return True
