# Copyright 2011,2013,2016 Christoph Reiter
#           2020 Nick Boultbee
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from __future__ import absolute_import

import sys
import time
import os
import traceback
import re
import logging
import errno

from senf import print_, path2fsn, fsn2text, fsnative, \
    supports_ansi_escape_codes

from quodlibet import const
from . import logging as ql_logging


class Color:

    NO_COLOR = '\033[0m'
    MAGENTA = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    BLACK = '\033[90m'
    GRAY = '\033[2m'


class Colorise:

    @classmethod
    def __reset(cls, text):
        return text + Color.NO_COLOR

    @classmethod
    def magenta(cls, text):
        return cls.__reset(Color.MAGENTA + text)

    @classmethod
    def blue(cls, text):
        return cls.__reset(Color.BLUE + text)

    @classmethod
    def cyan(cls, text):
        return cls.__reset(Color.CYAN + text)

    @classmethod
    def white(cls, text):
        return cls.__reset(Color.WHITE + text)

    @classmethod
    def yellow(cls, text):
        return cls.__reset(Color.YELLOW + text)

    @classmethod
    def green(cls, text):
        return cls.__reset(Color.GREEN + text)

    @classmethod
    def red(cls, text):
        return cls.__reset(Color.RED + text)

    @classmethod
    def black(cls, text):
        return cls.__reset(Color.BLACK + text)

    @classmethod
    def bold(cls, text):
        return cls.__reset('\033[1m' + text)

    @classmethod
    def gray(cls, text):
        return cls.__reset(Color.GRAY + text)


_ANSI_ESC_RE = re.compile(u"(\x1b\\[\\d\\d?m)")
_ANSI_ESC_RE_B = re.compile(b"(\x1b\\[\\d\\d?m)")


def strip_color(text):
    """Strip ansi escape codes from the passed text"""

    if isinstance(text, bytes):
        return _ANSI_ESC_RE_B.sub(b"", text)
    return _ANSI_ESC_RE.sub(u"", text)


def frame_info(level=0):
    """Return a short string describing the current stack frame which can
    be used for debug messages.

    level defines which frame should be used. 0 means the caller, 1 the caller
    of the caller etc.
    """

    info = ""

    # The frame of the calling function
    if hasattr(sys, "_getframe"):
        frame = sys._getframe()
    else:
        return ""

    for i in range(level + 1):
        try:
            frame = frame.f_back
        except AttributeError:
            break

    f_code = frame.f_code

    co_name = f_code.co_name
    co_varnames = f_code.co_varnames

    # the calling function got arguments
    if co_varnames and co_varnames[0] in frame.f_locals:
        # the first one could be the class
        cls = frame.f_locals[co_varnames[0]]

        # If it's an instance get the class
        if not hasattr(cls, '__name__'):
            cls = cls.__class__

        # the arg has an attr that is named like the function
        if hasattr(cls, co_name):
            info = cls.__name__

    # else, get the module name
    if not info:
        info = frame.f_globals.get("__name__", "")

    info = str(info)

    # append the function/method name
    if info:
        info += "." + co_name

    return info


def _should_write_to_file(file_):
    """In Windows UI mode we don't have a working stdout/stderr.
    With Python 2 sys.stdout.fileno() returns a negative fd, with Python 3
    sys.stdout is None.
    """

    if file_ is None:
        return False

    try:
        return file_.fileno() >= 0
    except (IOError, AttributeError):
        return True


def _supports_ansi_escape_codes(file_):
    assert file_ is not None
    try:
        return supports_ansi_escape_codes(file_.fileno())
    except (IOError, AttributeError):
        return False


def _print_message(string, custom_context, debug_only, prefix,
                   color, logging_category, start_time=time.time()):

    if not isinstance(string, (str, fsnative)):
        string = str(string)

    context = frame_info(2)

    # strip the package name
    if context.count(".") > 1:
        context = context.split(".", 1)[-1]

    if custom_context:
        context = "%s(%r)" % (context, custom_context)

    timestr = ("%08.3f" % (time.time() - start_time))[-9:]

    info = "%s: [%s] %s:" % (
        getattr(Colorise, color)(prefix),
        Colorise.magenta(timestr),
        Colorise.blue(context))

    lines = string.splitlines()
    if len(lines) > 1:
        string = os.linesep.join([info] + [" " * 4 + l for l in lines])
    else:
        string = info + " " + lines[0]

    if not debug_only or const.DEBUG:
        file_ = sys.stderr
        if _should_write_to_file(file_):
            if not _supports_ansi_escape_codes(file_):
                string = strip_color(string)
            try:
                print_(string, file=file_, flush=True)
            except (IOError, OSError) as e:
                if e.errno == errno.EIO:
                    # When we are started in a terminal with --debug and the
                    # terminal gets closed we lose stdio/err before we stop
                    # printing debug message, resulting in EIO and aborting the
                    # exit process -> Just ignore it.
                    pass
                else:
                    raise

    ql_logging.log(strip_color(string), logging_category)


def format_exception(etype, value, tb, limit=None):
    """Returns a list of str"""

    result_lines = traceback.format_exception(etype, value, tb, limit)
    return [fsn2text(path2fsn(l)) for l in result_lines]


def format_exception_only(etype, value):
    """Returns a list of str"""

    result_lines = traceback.format_exception_only(etype, value)
    return [fsn2text(path2fsn(l)) for l in result_lines]


def format_exc(limit=None):
    """Returns str"""

    etype, value, tb = sys.exc_info()
    return u''.join(format_exception(etype, value, tb, limit))


def extract_tb(*args, **kwargs):
    """Returns a list of tuples containing

    (fsnative, int, str, str)
    """

    return traceback.extract_tb(*args, **kwargs)


def print_exc(exc_info=None, context=None):
    """Prints the stack trace of the current exception or the passed one.
    Depending on the configuration will either print a short summary or the
    whole stacktrace.
    """

    if exc_info is None:
        exc_info = sys.exc_info()

    etype, value, tb = exc_info

    if const.DEBUG:
        string = u"".join(format_exception(etype, value, tb))
    else:
        # try to get a short error message pointing at the cause of
        # the exception
        text = u"".join(format_exception_only(etype, value))
        try:
            filename, lineno, name, line = extract_tb(tb)[-1]
        except IndexError:
            # no stack
            string = text
        else:
            string = u"%s:%s:%s: %s" % (
                fsn2text(path2fsn(os.path.basename(filename))),
                lineno, name, text)

    _print_message(string, context, False, "E", "red", "errors")


def print_d(string, context=None):
    """Print debugging information."""

    _print_message(string, context, True, "D", "green", "debug")


def print_w(string, context=None):
    """Print warnings"""

    _print_message(string, context, True, "W", "yellow", "warnings")


def print_e(string, context=None):
    """Print errors"""

    _print_message(string, context, False, "E", "red", "errors")


class PrintHandler(logging.Handler):
    """Converts logging records to our logging format"""

    def emit(self, record):
        print_func = {
            'DEBUG': print_d, 'INFO': print_d, 'WARNING': print_w,
            'ERROR': print_e, 'CRITICAL': print_e,
        }.get(record.levelname, print_d)

        exc_info = record.exc_info
        context = "%s.%s" % (record.module, record.funcName)
        record.exc_info = None
        print_func(self.format(record), context=context)
        if exc_info is not None:
            print_exc(record.exc_info, context=context)
