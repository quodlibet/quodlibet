# Copyright 2011,2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import sys
import time
import os
import re

import quodlibet.const
import quodlibet.util.logging

from quodlibet.const import ENCODING
from quodlibet.util.clicolor import Colorise
from quodlibet.util import clicolor


def _is_py2exe():
    return os.name == 'nt' and hasattr(sys, "frozen")


def _is_py2exe_console():
    """If True, stdout/stderr can be used"""

    return sys.frozen == "console_exe"


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


def _print(string, frm="utf-8", output=None, strip_color=True):
    if _is_py2exe() and not _is_py2exe_console():
        return

    if output is None:
        output = sys.stdout

    can_have_color = True
    if strip_color and not output.isatty():
        string = clicolor.strip_color(string)
        can_have_color = False

    if isinstance(string, unicode):
        string = string.encode(ENCODING, "replace")
    else:
        string = string.decode(frm).encode(ENCODING, "replace")

    try:
        if can_have_color:
            clicolor.print_color(string, output)
        else:
            print >>output, string
    except IOError:
        pass


def print_(string, output=None):
    if output is None:
        output = sys.stdout
    string = _format_print(string)
    quodlibet.util.logging.log(clicolor.strip_color(string))
    _print(string, output=output)


def print_d(string, context=""):
    """Print debugging information."""
    if quodlibet.const.DEBUG:
        output = sys.stderr
    else:
        output = None

    context = extract_caller_info()
    # strip the package name
    if context.startswith("quodlibet.") and context.count(".") > 1:
        context = context[10:]

    timestr = ("%0.2f" % time.time())[-6:]

    # Translators: "D" as in "Debug". It is prepended to
    # terminal output. APT uses a similar output format.
    prefix = _("D: ")

    string = "%s: %s: %s" % (Colorise.magenta(timestr),
                             Colorise.blue(context), string)
    string = _format_print(string, Colorise.green(prefix))

    if output is not None:
        _print(string, output=output)

    # Translators: Name of the debug tab in the Output Log window
    quodlibet.util.logging.log(clicolor.strip_color(string), _("Debug"))


def print_w(string):
    """Print warnings."""
    # Translators: "W" as in "Warning". It is prepended to
    # terminal output. APT uses a similar output format.
    prefix = _("W: ")

    string = _format_print(string, Colorise.red(prefix))
    _print(string, output=sys.stderr)

    # Translators: Name of the warnings tab in the Output Log window
    quodlibet.util.logging.log(clicolor.strip_color(string), _("Warnings"))


def print_e(string, context=None):
    """Print errors."""
    # Translators: "E" as in "Error". It is prepended to
    # terminal output. APT uses a similar output format.
    prefix = _("E: ")

    string = _format_print(string, Colorise.red(prefix))
    _print(string, output=sys.stderr)

    # Translators: Name of the warnings tab in the Output Log window
    quodlibet.util.logging.log(clicolor.strip_color(string), _("Errors"))
