# Copyright 2011,2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import ctypes
import os
import re
import sys

from ctypes import c_ulong, c_void_p, c_ushort, c_int, byref, c_short


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


WORD = c_ushort
DWORD = c_ulong
HANDLE = c_void_p
BOOL = c_int
SHORT = c_short

STD_INPUT_HANDLE = DWORD(-10)
STD_OUTPUT_HANDLE = DWORD(-11)
STD_ERROR_HANDLE = DWORD(-12)

INVALID_HANDLE_VALUE = HANDLE(-1)

FG_BLUE = 1
FG_GREEN = 2
FG_RED = 4
FG_INTENSITY = 8
FG_MASK = 0xF


class COORD(ctypes.Structure):
    _fields_ = [
        ("X", SHORT),
        ("Y", SHORT),
    ]


class SMALL_RECT(ctypes.Structure):
    _fields_ = [
        ("Left", SHORT),
        ("Top", SHORT),
        ("Right", SHORT),
        ("Bottom", SHORT),
    ]


class PCONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
    _fields_ = [
        ("dwSize", COORD),
        ("dwCursorPosition", COORD),
        ("wAttributes", WORD),
        ("srWindow", SMALL_RECT),
        ("dwMaximumWindowSize", COORD),
    ]


GetStdHandle = None
SetConsoleTextAttribute = None
GetConsoleScreenBufferInfo = None


def _init_windll():
    from ctypes import windll

    global GetStdHandle, SetConsoleTextAttribute, GetConsoleScreenBufferInfo

    GetStdHandle = windll.Kernel32.GetStdHandle
    GetStdHandle.argtypes = [DWORD]
    GetStdHandle.restype = HANDLE

    SetConsoleTextAttribute = windll.Kernel32.SetConsoleTextAttribute
    SetConsoleTextAttribute.argtypes = [HANDLE, WORD]
    SetConsoleTextAttribute.restype = BOOL

    GetConsoleScreenBufferInfo = windll.Kernel32.GetConsoleScreenBufferInfo
    GetConsoleScreenBufferInfo.argtypes = [
        HANDLE, ctypes.POINTER(PCONSOLE_SCREEN_BUFFER_INFO)]
    GetConsoleScreenBufferInfo.restype = BOOL


class WinColor(object):
    MAGENTA = FG_BLUE | FG_RED | FG_INTENSITY
    BLUE = FG_BLUE | FG_INTENSITY
    CYAN = FG_BLUE | FG_GREEN | FG_INTENSITY
    WHITE = FG_BLUE | FG_GREEN | FG_RED | FG_INTENSITY
    YELLOW = FG_GREEN | FG_RED | FG_INTENSITY
    GREEN = FG_GREEN | FG_INTENSITY
    RED = FG_RED | FG_INTENSITY
    BLACK = 0
    GRAY = FG_INTENSITY


def print_color_default(text, output):
    assert isinstance(text, str)

    print >>output, text


def print_color_win(text, output):
    """Parses some ansi escape codes and translates them to Windows
    console API calls.
    """

    assert isinstance(text, str)

    if output is sys.stdout:
        h = GetStdHandle(STD_OUTPUT_HANDLE)
    else:
        h = GetStdHandle(STD_ERROR_HANDLE)

    if h == INVALID_HANDLE_VALUE:
        return

    # get the default value
    info = PCONSOLE_SCREEN_BUFFER_INFO()
    if not GetConsoleScreenBufferInfo(h, byref(info)):
        return

    mapping = {
        Color.NO_COLOR: info.wAttributes & FG_MASK,
        Color.MAGENTA: WinColor.MAGENTA,
        Color.BLUE: WinColor.BLUE,
        Color.CYAN: WinColor.CYAN,
        Color.WHITE: WinColor.WHITE,
        Color.YELLOW: WinColor.YELLOW,
        Color.GREEN: WinColor.GREEN,
        Color.RED: WinColor.RED,
        Color.BLACK: WinColor.BLACK,
        Color.GRAY: WinColor.GRAY,
    }

    bg = info.wAttributes & (~FG_MASK)
    for part in _ANSI_ESC_RE.split(text):
        if part in mapping:
            SetConsoleTextAttribute(h, mapping[part] | bg)
        elif not _ANSI_ESC_RE.match(part):
            output.write(part)
    output.write(os.linesep)


try:
    from ctypes import windll
except ImportError:
    print_color = print_color_default
else:
    _init_windll()
    print_color = print_color_win
