# -*- coding: utf-8 -*-
# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import struct
import ctypes
from uuid import UUID
from ctypes import wintypes, cdll, windll

from .enum import enum


LPTSTR = wintypes.LPWSTR
REFKNOWNFOLDERID = ctypes.c_char_p

SetEnvironmentVariableW = ctypes.windll.kernel32.SetEnvironmentVariableW
SetEnvironmentVariableW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
SetEnvironmentVariableW.restype = ctypes.c_bool

GetEnvironmentStringsW = ctypes.windll.kernel32.GetEnvironmentStringsW
GetEnvironmentStringsW.argtypes = []
GetEnvironmentStringsW.restype = ctypes.c_void_p

FreeEnvironmentStringsW = ctypes.windll.kernel32.FreeEnvironmentStringsW
FreeEnvironmentStringsW.argtypes = [ctypes.c_void_p]
FreeEnvironmentStringsW.restype = ctypes.c_bool

SHGetFolderPathW = ctypes.windll.shell32.SHGetFolderPathW
SHGetFolderPathW.argtypes = [
    wintypes.HWND, ctypes.c_int, wintypes.HANDLE, wintypes.DWORD, LPTSTR]
SHGetFolderPathW.restype = wintypes.HRESULT

SHGetKnownFolderPath = windll.shell32.SHGetKnownFolderPath
SHGetKnownFolderPath.argtypes = [
    REFKNOWNFOLDERID, wintypes.DWORD, wintypes.HANDLE,
    ctypes.POINTER(wintypes.c_wchar_p)]
SHGetKnownFolderPath.restype = wintypes.HRESULT

CoTaskMemFree = windll.ole32.CoTaskMemFree
CoTaskMemFree.argtypes = [ctypes.c_void_p]
CoTaskMemFree.restype = None

GetCommandLineW = cdll.kernel32.GetCommandLineW
GetCommandLineW.argtypes = []
GetCommandLineW.restype = wintypes.LPCWSTR

CommandLineToArgvW = windll.shell32.CommandLineToArgvW
CommandLineToArgvW.argtypes = [
    wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
CommandLineToArgvW.restype = ctypes.POINTER(wintypes.LPWSTR)

LocalFree = windll.kernel32.LocalFree
LocalFree.argtypes = [wintypes.HLOCAL]
LocalFree.restype = wintypes.HLOCAL

S_OK = wintypes.HRESULT(0).value
MAX_PATH = wintypes.MAX_PATH


def guid2bytes(id_):
    assert isinstance(id_, UUID)

    fields = id_.fields
    return b"".join([
        struct.pack("<IHH", *fields[:3]),
        struct.pack("BB", *fields[3:5]),
        struct.pack(">Q", fields[5])[2:],
    ])


@enum
class FOLDERID(UUID):
    LINKS = "{bfb9d5e0-c6a9-404c-b2b2-ae6db6af4968}"


@enum
class SHGFPType(int):
    CURRENT = 0
    DEFAULT = 1


@enum
class CSIDL(int):
    DESKTOP = 0x0000
    PERSONAL = 0x0005
    APPDATA = 0x001A
    MYMUSIC = 0x000d
    PROFILE = 0x0028


@enum
class CSIDLFlag(int):
    PER_USER_INIT = 0x0800
    NO_ALIAS = 0x1000
    DONT_UNEXPAND = 0x2000
    DONT_VERIFY = 0x4000
    CREATE = 0x8000
    MASK = 0xFF00


@enum
class KnownFolderFlag(long):
    SIMPLE_IDLIST = 0x00000100
    NOT_PARENT_RELATIVE = 0x00000200
    DEFAULT_PATH = 0x00000400
    INIT = 0x00000800
    NO_ALIAS = 0x00001000
    DONT_UNEXPAND = 0x00002000
    DONT_VERIFY = 0x00004000
    CREATE = 0x00008000
    NO_APPCONTAINER_REDIRECTION = 0x00010000
    ALIAS_ONLY = 0x80000000
