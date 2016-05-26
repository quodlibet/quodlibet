# -*- coding: utf-8 -*-
# Copyright 2011,2013,2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import sys
import time
import os
import traceback
import ctypes
import re

from quodlibet import const
from quodlibet.compat import text_type, PY2
from .misc import get_locale_encoding
from .environment import is_py2exe_window, is_windows
from .path import fsdecode
from . import logging


class Color(object):

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


class Colorise(object):

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


_ANSI_ESC_RE = re.compile("(\x1b\[\d\d?m)")


def strip_color(text):
    """Strip ansi escape codes from the passed text"""

    return _ANSI_ESC_RE.sub("", text)


def print_(*objects, **kwargs):
    """print_(*objects, sep=None, end=None, file=None, has_color=True)

    objects can be valid paths or text (can be mixed).
    If has_color is True the text can include ansi color codes.
    """

    file_ = kwargs.get("file", sys.stdout)

    if is_windows() and file_ in (sys.__stdout__, sys.__stderr__):
        _print_windows(*objects, **kwargs)
    else:
        _print_unix(*objects, **kwargs)


def _print_unix(*objects, **kwargs):
    """A print_() implementation for tests. Writes utf-8 or bytes.

    Also used when stdout is replaced, for example in tests etc..
    """

    sep = kwargs.get("sep", " ")
    end = kwargs.get("end", os.linesep)
    file_ = kwargs.get("file", sys.stdout)
    has_color = kwargs.get("has_color", True)

    encoding = get_locale_encoding()

    parts = []
    for obj in objects:
        if isinstance(obj, text_type):
            if PY2:
                obj = obj.encode(encoding, "replace")
            else:
                obj = obj.encode(encoding, "surrogateescape")
        parts.append(obj)

    if isinstance(sep, text_type):
        sep = sep.encode(encoding, "replace")

    if isinstance(end, text_type):
        end = end.encode(encoding, "replace")

    data = sep.join(parts) + end

    if has_color and not file_.isatty():
        data = strip_color(data)

    file_ = getattr(file_, "buffer", file_)
    file_.write(data)


def _print_windows(*objects, **kwargs):
    """The windows implementation of print_()"""

    if is_py2exe_window():
        return

    sep = kwargs.get("sep", u" ")
    end = kwargs.get("end", os.linesep)
    file_ = kwargs.get("file", sys.stdout)
    has_color = kwargs.get("has_color", True)

    from quodlibet.util import winapi

    if file_ is sys.__stdout__:
        h = winapi.GetStdHandle(winapi.STD_OUTPUT_HANDLE)
    elif file_ is sys.__stderr__:
        h = winapi.GetStdHandle(winapi.STD_ERROR_HANDLE)
    else:
        raise AssertionError("only stdout/stderr supported")

    if h == winapi.INVALID_HANDLE_VALUE:
        return

    # get the default value
    info = winapi.PCONSOLE_SCREEN_BUFFER_INFO()
    if not winapi.GetConsoleScreenBufferInfo(h, ctypes.byref(info)):
        return

    mapping = {
        Color.NO_COLOR: info.wAttributes & 0xF,
        Color.MAGENTA: (winapi.FOREGROUND_BLUE | winapi.FOREGROUND_RED |
                        winapi.FOREGROUND_INTENSITY),
        Color.BLUE: winapi.FOREGROUND_BLUE | winapi.FOREGROUND_INTENSITY,
        Color.CYAN: (winapi.FOREGROUND_BLUE | winapi.FOREGROUND_GREEN |
                     winapi.FOREGROUND_INTENSITY),
        Color.WHITE: (winapi.FOREGROUND_BLUE | winapi.FOREGROUND_GREEN |
                      winapi.FOREGROUND_RED | winapi.FOREGROUND_INTENSITY),
        Color.YELLOW: (winapi.FOREGROUND_GREEN | winapi.FOREGROUND_RED |
                       winapi.FOREGROUND_INTENSITY),
        Color.GREEN: winapi.FOREGROUND_GREEN | winapi.FOREGROUND_INTENSITY,
        Color.RED: winapi.FOREGROUND_RED | winapi.FOREGROUND_INTENSITY,
        Color.BLACK: 0,
        Color.GRAY: winapi.FOREGROUND_INTENSITY,
    }

    parts = []
    for obj in objects:
        if not isinstance(obj, text_type):
            obj = obj.decode("utf-8")
        parts.append(obj)

    text = sep.join(parts) + end
    assert isinstance(text, text_type)

    fileno = file_.fileno()
    file_.flush()

    # try to force a utf-8 code page
    old_cp = winapi.GetConsoleOutputCP()
    encoding = "utf-8"
    if winapi.SetConsoleOutputCP(65001) == 0:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        old_cp = None

    if not has_color:
        os.write(fileno, text.encode(encoding, 'replace'))
    else:
        bg = info.wAttributes & (~0xF)
        for part in _ANSI_ESC_RE.split(text):
            if part in mapping:
                winapi.SetConsoleTextAttribute(h, mapping[part] | bg)
            elif not _ANSI_ESC_RE.match(part):
                os.write(fileno, part.encode(encoding, 'replace'))

    # reset the code page to what we had before
    if old_cp is not None:
        winapi.SetConsoleOutputCP(old_cp)


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

        # the arg has an attr that is named like the function
        if hasattr(cls, co_name):
            # If it's an instance get the class
            if not hasattr(cls, '__name__'):
                cls = cls.__class__
            info = cls.__name__

    # else, get the module name
    if not info:
        info = frame.f_globals.get("__name__", "")

    # append the function/method name
    if info:
        info += "." + co_name

    return info


def _print_message(string, custom_context, debug_only, prefix,
                   color, logging_category, start_time=time.time()):

    context = frame_info(2)

    # strip the package name
    if context.count(".") > 1:
        context = context.split(".", 1)[-1]

    if custom_context:
        context = "%s(%r)" % (context, custom_context)

    timestr = ("%2.3f" % (time.time() - start_time))[-6:]

    info = "%s: %s: %s:" % (
        getattr(Colorise, color)(prefix),
        Colorise.magenta(timestr),
        Colorise.blue(context))

    lines = string.splitlines()
    if len(lines) > 1:
        string = os.linesep.join([info] + [" " * 4 + l for l in lines])
    else:
        string = info + " " + lines[0]

    if not debug_only or const.DEBUG:
        print_(string, file=sys.stderr)

    logging.log(strip_color(string), logging_category)


def format_exc(*args, **kwargs):
    """Returns text_type"""

    # stack traces can contain byte paths under py2
    return fsdecode(traceback.format_exc(*args, **kwargs))


def print_exc():
    """Prints the stack trace of the current exception. Depending
    on the configuration will either print a short summary or the whole
    stacktrace.
    """

    if const.DEBUG:
        string = format_exc()
    else:
        # try to get a short error message pointing at the cause of
        # the exception
        tp = traceback.extract_tb(sys.exc_info()[2])[-1]
        filename, lineno, name, line = tp
        text = os.linesep.join(format_exc(0).splitlines()[1:])
        string = u"%s:%s:%s: %s" % (
            fsdecode(os.path.basename(filename)), lineno, name, text)

    _print_message(string, None, False, "E", "red", "errors")


def print_d(string, context=None):
    """Print debugging information."""

    _print_message(string, context, True, "D", "green", "debug")


def print_w(string, context=None):
    """Print warnings"""

    _print_message(string, context, True, "W", "yellow", "warnings")


def print_e(string, context=None):
    """Print errors"""

    _print_message(string, context, False, "E", "red", "errors")
