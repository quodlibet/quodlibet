# -*- coding: utf-8 -*-
# Copyright 2011,2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import sys
import time
import os

import quodlibet.const
import quodlibet.util.logging

from quodlibet.util.clicolor import Colorise
from quodlibet.util import clicolor
from quodlibet.compat import text_type, PY2
from .misc import get_locale_encoding
from .environment import is_py2exe, is_py2exe_console


_ENCODING = get_locale_encoding()


def _format_print(string, prefix=""):
    """Inserts the given prefix at the beginning of each line"""
    if prefix:
        string = prefix + ("\n" + prefix).join(string.splitlines())
    return string


def extract_caller_info():
    """Returns a string describing the caller of the caller of this function.

    It currently checks if the caller got arguments that have an attribute
    with the same name as the caller (so it's probably the class of a method)
    or returns the module name for everything else.
    """
    try:
        raise ZeroDivisionError
    except:
        try:
            info = ""

            # The frame of the calling function
            frame = sys.exc_info()[2].tb_frame.f_back.f_back
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
        except (AttributeError, IndexError):
            return ""
        else:
            return info


def _print(string, output, frm="utf-8", strip_color=True, end=os.linesep):
    if is_py2exe() and not is_py2exe_console():
        return

    can_have_color = True
    if strip_color and not output.isatty():
        string = clicolor.strip_color(string)
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
            clicolor.print_color(string, output)
        else:
            output.write(string)
        output.write(end)
    except IOError:
        pass


def print_(string, output=None, end=os.linesep):
    if output is None:
        if PY2:
            output = sys.stdout
        else:
            output = sys.stdout.buffer

    _print(string, output, end=end)


def print_d(string, context=""):
    """Print debugging information."""
    if quodlibet.const.DEBUG:
        if PY2:
            output = sys.stderr
        else:
            output = sys.stderr.buffer
    else:
        output = None

    if PY2:
        context = extract_caller_info()
    else:
        # FIXME: PY3PORT
        context = ""
    # strip the package name
    if context.startswith("quodlibet.") and context.count(".") > 1:
        context = context[10:]

    timestr = ("%0.2f" % time.time())[-6:]

    # Translators: "D" as in "Debug". It is prepended to
    # terminal output. APT uses a similar output format.
    prefix = _("D:") + " "

    string = "%s: %s: %s" % (Colorise.magenta(timestr),
                             Colorise.blue(context), string)
    string = _format_print(string, Colorise.green(prefix))

    if output is not None:
        _print(string, output)

    # Translators: Name of the debug tab in the Output Log window
    quodlibet.util.logging.log(clicolor.strip_color(string), "debug")


def print_w(string):
    """Print warnings."""
    # Translators: "W" as in "Warning". It is prepended to
    # terminal output. APT uses a similar output format.
    prefix = _("W:") + " "

    string = _format_print(string, Colorise.red(prefix))
    if PY2:
        _print(string, sys.stderr)
    else:
        _print(string, sys.stderr.buffer)

    # Translators: Name of the warnings tab in the Output Log window
    quodlibet.util.logging.log(clicolor.strip_color(string), "warnings")


def print_e(string, context=None):
    """Print errors."""
    # Translators: "E" as in "Error". It is prepended to
    # terminal output. APT uses a similar output format.
    prefix = _("E:") + " "

    string = _format_print(string, Colorise.red(prefix))
    _print(string, sys.stderr)

    # Translators: Name of the warnings tab in the Output Log window
    quodlibet.util.logging.log(clicolor.strip_color(string), "errors")
