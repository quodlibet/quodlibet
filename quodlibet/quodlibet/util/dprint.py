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
import re

from senf import print_, path2fsn, fsn2text

from quodlibet import const
from quodlibet.compat import PY2
from .environment import is_py2exe_window
from .string import decode
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


_ANSI_ESC_RE = re.compile(u"(\x1b\[\d\d?m)")
_ANSI_ESC_RE_B = re.compile(b"(\x1b\[\d\d?m)")


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

    if (not debug_only or const.DEBUG) and not is_py2exe_window():
        file_ = sys.stderr
        if not file_.isatty():
            string = strip_color(string)
        print_(string, file=file_)

    logging.log(strip_color(string), logging_category)


def format_exc(*args, **kwargs):
    """Returns text_type"""

    # stack traces can contain byte paths under py2
    return fsn2text(path2fsn(traceback.format_exc(*args, **kwargs)))


def format_exception(*args, **kwargs):
    """Returns a list of text_type"""

    result_lines = traceback.format_exception(*args, **kwargs)
    return [fsn2text(path2fsn(l)) for l in result_lines]


def extract_tb(*args, **kwargs):
    """Returns a list of tuples containing

    (fsnative, int, text_type, text_type)
    """

    tp = traceback.extract_tb(*args, **kwargs)
    if not PY2:
        return tp

    result = []
    for filename, line_number, function_name, text in tp:
        filename = path2fsn(filename)
        function_name = decode(function_name)
        text = decode(text)
        result.append((filename, line_number, function_name, text))
    return result


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
            fsn2text(path2fsn(os.path.basename(filename))), lineno, name, text)

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
