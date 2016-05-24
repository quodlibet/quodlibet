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
from .environment import is_py2exe, is_py2exe_console
from . import logging


_ENCODING = get_locale_encoding()
_TIME = time.time()


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


def print_color_default(text, output):
    assert isinstance(text, str)

    output.write(text)


def print_color_win(text, output):
    """Parses some ansi escape codes and translates them to Windows
    console API calls.
    """

    assert isinstance(text, str)

    from quodlibet.util import winapi

    if output is sys.stdout:
        h = winapi.GetStdHandle(winapi.STD_OUTPUT_HANDLE)
    else:
        h = winapi.GetStdHandle(winapi.STD_ERROR_HANDLE)

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

    bg = info.wAttributes & (~0xF)
    for part in _ANSI_ESC_RE.split(text):
        if part in mapping:
            winapi.SetConsoleTextAttribute(h, mapping[part] | bg)
        elif not _ANSI_ESC_RE.match(part):
            output.write(part)


def print_color(text, output):
    if os.name == "nt":
        print_color_win(text, output)
    else:
        print_color_default(text, output)


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


def _print(string, output, frm="utf-8", end=os.linesep):
    if is_py2exe() and not is_py2exe_console():
        return

    can_have_color = True
    if can_have_color and not output.isatty():
        string = strip_color(string)
        can_have_color = False

    if not PY2:
        # FIXME: PY3PORT
        can_have_color = False

    if isinstance(string, text_type):
        string = string.encode(_ENCODING, "replace")
    else:
        string = string.decode(frm).encode(_ENCODING, "replace")

    if isinstance(end, text_type):
        end = end.encode(_ENCODING, "replace")

    assert isinstance(string, bytes)
    assert isinstance(end, bytes)

    try:
        if can_have_color:
            print_color(string, output)
        else:
            output.write(string)
        output.write(end)
    except IOError:
        pass


def print_(string, output=None, end=os.linesep):
    """Print something to `output`. This should be used instead of
    the Python built-in print statement or function.

    output defaults to sys.stdout
    """

    if output is None:
        if PY2:
            output = sys.stdout
        else:
            output = sys.stdout.buffer

    _print(string, output, end=end)


def _print_message(string, custom_context, debug_only, prefix,
                   color, logging_category):

    if not debug_only or const.DEBUG:
        if PY2:
            output = sys.stderr
        else:
            output = sys.stderr.buffer
    else:
        output = None

    context = frame_info(2)

    # strip the package name
    if context.count(".") > 1:
        context = context.split(".", 1)[-1]

    if custom_context:
        context = "%s(%r)" % (context, custom_context)

    timestr = ("%2.3f" % (time.time() - _TIME))[-6:]

    info = "%s: %s: %s:" % (
        getattr(Colorise, color)(prefix),
        Colorise.magenta(timestr),
        Colorise.blue(context))

    lines = string.splitlines()
    if len(lines) > 1:
        string = os.linesep.join([info] + [" " * 4 + l for l in lines])
    else:
        string = info + " " + lines[0]

    if output is not None:
        _print(string, output)

    logging.log(strip_color(string), logging_category)


def print_exc():
    """Prints the stack trace of the current exception. Depending
    on the configuration will either print a short summary or the whole
    stacktrace.
    """

    if const.DEBUG:
        string = traceback.format_exc()
    else:
        # try to get a short error message pointing at the cause of
        # the exception
        tp = traceback.extract_tb(sys.exc_info()[2])[-1]
        filename, lineno, name, line = tp
        text = os.linesep.join(traceback.format_exc(0).splitlines()[1:])
        string = "%s:%s:%s: %s" % (
            os.path.basename(filename), lineno, name, text)

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
