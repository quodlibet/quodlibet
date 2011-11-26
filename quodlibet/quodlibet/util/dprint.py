# Copyright 2011 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import sys
import time
import os

import quodlibet.const
import quodlibet.util.logging

from quodlibet.const import ENCODING

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


class COLOR(object):
    @classmethod
    def __reset(cls, text):
        return text + '\033[0m'

    @classmethod
    def Magenta(cls, text):
        return cls.__reset('\033[95m' + text)

    @classmethod
    def Blue(cls, text):
        return cls.__reset('\033[94m' + text)

    @classmethod
    def Cyan(cls, text):
        return cls.__reset('\033[96m' + text)

    @classmethod
    def White(cls, text):
        return cls.__reset('\033[97m' + text)

    @classmethod
    def Yellow(cls, text):
        return cls.__reset('\033[93m' + text)

    @classmethod
    def Green(cls, text):
        return cls.__reset('\033[92m' + text)

    @classmethod
    def Red(cls, text):
        return cls.__reset('\033[91m' + text)

    @classmethod
    def Black(cls, text):
        return cls.__reset('\033[90m' + text)


def _print(string, color=None, frm="utf-8", output=sys.stdout):
    if os.name == 'nt':
        return

    if output:
        # only print with colors if the file is a terminal
        if color is not None and output.isatty():
            string = color

        if isinstance(string, unicode):
            string = string.encode(ENCODING, "replace")
        else:
            string = string.decode(frm).encode(ENCODING, "replace")
        try:
            print >>output, string
        except IOError:
            pass


def print_(string, output=sys.stdout):
    string = _format_print(string)
    quodlibet.util.logging.log(string)
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

    color_string = "%s: %s: %s" % (COLOR.Magenta(timestr),
                                   COLOR.Blue(context), string)
    color_string = _format_print(color_string, COLOR.Green(prefix))

    string = "%s: %s: %s" % (timestr, context, string)
    string = _format_print(string, prefix)

    _print(string, color=color_string, output=output)

    # Translators: Name of the debug tab in the Output Log window
    quodlibet.util.logging.log(string, _("Debug"))


def print_w(string):
    """Print warnings."""
    # Translators: "W" as in "Warning". It is prepended to
    # terminal output. APT uses a similar output format.
    prefix = _("W: ")

    color_string = _format_print(string, COLOR.Red(prefix))
    string = _format_print(string, prefix)

    _print(string, color_string, output=sys.stderr)

    # Translators: Name of the warnings tab in the Output Log window
    quodlibet.util.logging.log(string, _("Warnings"))


def print_e(string, context=None):
    """Print errors."""
    # Translators: "E" as in "Error". It is prepended to
    # terminal output. APT uses a similar output format.
    prefix = _("E: ")

    color_string = _format_print(string, COLOR.Red(prefix))
    string = _format_print(string, prefix)

    _print(string, color_string, output=sys.stderr)

    # Translators: Name of the warnings tab in the Output Log window
    quodlibet.util.logging.log(string, _("Errors"))
