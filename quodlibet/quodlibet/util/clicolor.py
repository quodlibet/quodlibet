# -*- coding: utf-8 -*-
# Copyright 2011,2013,2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import ctypes
import re
import sys
import os


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
