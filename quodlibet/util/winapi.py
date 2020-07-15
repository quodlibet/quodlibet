# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
Error handling: every function which has ctypes.HRESULT as restype
will automatically raise WindowsError if a bad result is returned.
For all other functions check the return status and raise ctypes.WinError()
"""

import sys
import ctypes

from .enum import enum


if sys.platform == 'win32':
    from ctypes import wintypes, cdll, windll, oledll

    class GUID(ctypes.Structure):
        # https://msdn.microsoft.com/en-us/library/windows/desktop/
        #   aa373931%28v=vs.85%29.aspx

        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", wintypes.BYTE * 8),
        ]

        def __init__(self, name=None):
            if name is not None:
                IIDFromString(str(name), ctypes.byref(self))

        def __str__(self):
            ptr = wintypes.LPOLESTR()
            StringFromIID(ctypes.byref(self), ctypes.byref(ptr))
            string = str(ptr.value)
            CoTaskMemFree(ptr)
            return string

    LPGUID = ctypes.POINTER(GUID)
    IID = GUID
    LPIID = ctypes.POINTER(IID)
    REFIID = ctypes.POINTER(IID)
    CLSID = GUID
    REFCLSID = ctypes.POINTER(CLSID)

    WORD = wintypes.WORD
    DWORD = wintypes.DWORD
    ULONG = wintypes.ULONG
    SHORT = wintypes.SHORT

    ULONG_PTR = wintypes.WPARAM
    LONG_PTR = wintypes.LPARAM
    LRESULT = LONG_PTR
    HHOOK = wintypes.HANDLE
    HRESULT = ctypes.HRESULT

    HC_ACTION = 0
    HC_NOREMOVE = 3

    VK_MEDIA_NEXT_TRACK = 0xB0
    VK_MEDIA_PREV_TRACK = 0xB1
    VK_MEDIA_STOP = 0xB2
    VK_MEDIA_PLAY_PAUSE = 0xB3

    WM_KEYDOWN = 0x0100
    WM_KEYUP = 0x0101
    WM_SYSKEYDOWN = 0x0104
    WM_SYSKEYUP = 0x0105

    CallNextHookEx = windll.user32.CallNextHookEx
    CallNextHookEx.argtypes = [
        HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
    CallNextHookEx.restype = LRESULT

    class KBDLLHOOKSTRUCT(ctypes.Structure):
        _fields_ = [
            ("vkCode", DWORD),
            ("scanCode", DWORD),
            ("flags", DWORD),
            ("time", DWORD),
            ("dwExtraInfo", ULONG_PTR),
        ]

    LPKBDLLHOOKSTRUCT = PKBDLLHOOKSTRUCT = ctypes.POINTER(KBDLLHOOKSTRUCT)

    LowLevelKeyboardProc = ctypes.WINFUNCTYPE(
        LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

    _SetWindowsHookExW = windll.user32.SetWindowsHookExW
    _SetWindowsHookExW.argtypes = [
        ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD]
    _SetWindowsHookExW.restype = HHOOK

    def SetWindowsHookExW(idHook, lpfn, hMod, dwThreadId):
        assert idHook == WH_KEYBOARD_LL
        assert isinstance(lpfn, LowLevelKeyboardProc)
        return _SetWindowsHookExW(idHook, lpfn, hMod, dwThreadId)

    UnhookWindowsHookEx = windll.user32.UnhookWindowsHookEx
    UnhookWindowsHookEx.argtypes = [HHOOK]
    UnhookWindowsHookEx.restype = wintypes.BOOL

    WH_KEYBOARD_LL = 13

    LPWIN32_FIND_DATAW = ctypes.POINTER(wintypes.WIN32_FIND_DATAW)

    IIDFromString = windll.ole32.IIDFromString
    IIDFromString.argtypes = [wintypes.LPCOLESTR, LPIID]
    IIDFromString.restype = HRESULT

    StringFromIID = windll.ole32.StringFromIID
    StringFromIID.argtypes = [REFIID, ctypes.POINTER(wintypes.LPOLESTR)]
    StringFromIID.restype = HRESULT

    CoInitialize = windll.ole32.CoInitialize
    CoInitialize.argtypes = [wintypes.LPVOID]
    CoInitialize.restype = HRESULT

    LPDWORD = ctypes.POINTER(wintypes.DWORD)
    REFKNOWNFOLDERID = ctypes.POINTER(GUID)

    CLSCTX_INPROC_SERVER = 1

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
        wintypes.HWND, ctypes.c_int, wintypes.HANDLE, wintypes.DWORD,
        wintypes.LPWSTR]
    SHGetFolderPathW.restype = HRESULT

    SHGetKnownFolderPath = windll.shell32.SHGetKnownFolderPath
    SHGetKnownFolderPath.argtypes = [
        REFKNOWNFOLDERID, wintypes.DWORD, wintypes.HANDLE,
        ctypes.POINTER(ctypes.c_wchar_p)]
    SHGetKnownFolderPath.restype = HRESULT

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

    WaitNamedPipeW = windll.kernel32.WaitNamedPipeW
    WaitNamedPipeW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD]
    WaitNamedPipeW.restype = wintypes.BOOL

    LANGID = wintypes.WORD

    GetUserDefaultUILanguage = ctypes.windll.kernel32.GetUserDefaultUILanguage
    GetUserDefaultUILanguage.argtypes = []
    GetUserDefaultUILanguage.restype = LANGID

    GetSystemDefaultUILanguage = ctypes.windll.kernel32.GetSystemDefaultUILanguage
    GetSystemDefaultUILanguage.argtypes = []
    GetSystemDefaultUILanguage.restype = LANGID

    class SECURITY_ATTRIBUTES(ctypes.Structure):

        _fields_ = [
            ("nLength", wintypes.DWORD),
            ("lpSecurityDescriptor", wintypes.LPVOID),
            ("bInheritHandle", wintypes.BOOL),
        ]

    LPSECURITY_ATTRIBUTES = ctypes.POINTER(SECURITY_ATTRIBUTES)
    PSECURITY_ATTRIBUTES = LPSECURITY_ATTRIBUTES

    CreateNamedPipeW = windll.kernel32.CreateNamedPipeW
    CreateNamedPipeW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
        wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, LPSECURITY_ATTRIBUTES]
    CreateNamedPipeW.restype = wintypes.HANDLE

    LPOVERLAPPED = ctypes.c_void_p

    PIPE_ACCEPT_REMOTE_CLIENTS = 0x00000000
    PIPE_REJECT_REMOTE_CLIENTS = 0x00000008

    PIPE_ACCESS_DUPLEX = 0x00000003
    PIPE_ACCESS_INBOUND = 0x00000001
    PIPE_ACCESS_OUTBOUND = 0x00000002

    PIPE_TYPE_BYTE = 0x00000000
    PIPE_TYPE_MESSAGE = 0x00000004

    PIPE_READMODE_BYTE = 0x00000000
    PIPE_READMODE_MESSAGE = 0x00000002

    PIPE_WAIT = 0x00000000
    PIPE_NOWAIT = 0x00000001

    FILE_FLAG_FIRST_PIPE_INSTANCE = 0x00080000
    FILE_FLAG_WRITE_THROUGH = 0x80000000
    FILE_FLAG_OVERLAPPED = 0x40000000

    PIPE_UNLIMITED_INSTANCES = 255

    NMPWAIT_USE_DEFAULT_WAIT = 0x00000000
    NMPWAIT_WAIT_FOREVER = 0xffffffff

    ConnectNamedPipe = windll.kernel32.ConnectNamedPipe
    ConnectNamedPipe.argtypes = [wintypes.HANDLE, LPOVERLAPPED]
    ConnectNamedPipe.restype = wintypes.BOOL

    DisconnectNamedPipe = windll.kernel32.DisconnectNamedPipe
    DisconnectNamedPipe.argtypes = [wintypes.HANDLE]
    DisconnectNamedPipe.restype = wintypes.BOOL

    ReadFile = windll.kernel32.ReadFile
    ReadFile.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                        LPDWORD, LPOVERLAPPED]
    ReadFile.restype = wintypes.BOOL

    CloseHandle = windll.kernel32.CloseHandle
    CloseHandle.argtypes = [wintypes.HANDLE]
    CloseHandle.restype = wintypes.BOOL

    MOVEFILE_WRITE_THROUGH = 0x8
    MOVEFILE_REPLACE_EXISTING = 0x1

    MoveFileExW = windll.kernel32.MoveFileExW
    MoveFileExW.argtypes = [wintypes.LPWSTR, wintypes.LPWSTR, wintypes.DWORD]
    MoveFileExW.restype = wintypes.BOOL

    GetStdHandle = windll.kernel32.GetStdHandle
    GetStdHandle.argtypes = [DWORD]
    GetStdHandle.restype = wintypes.HANDLE

    SetConsoleTextAttribute = windll.kernel32.SetConsoleTextAttribute
    SetConsoleTextAttribute.argtypes = [wintypes.HANDLE, WORD]
    SetConsoleTextAttribute.restype = wintypes.BOOL

    GetConsoleOutputCP = windll.kernel32.GetConsoleOutputCP
    GetConsoleOutputCP.argtypes = []
    GetConsoleOutputCP.restype = wintypes.UINT

    SetConsoleOutputCP = windll.kernel32.SetConsoleOutputCP
    SetConsoleOutputCP.argtypes = [wintypes.UINT]
    SetConsoleOutputCP.restype = wintypes.BOOL

    WinError = ctypes.WinError
    S_OK = HRESULT(0).value
    MAX_PATH = wintypes.MAX_PATH
    INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value

    STD_INPUT_HANDLE = DWORD(-10)
    STD_OUTPUT_HANDLE = DWORD(-11)
    STD_ERROR_HANDLE = DWORD(-12)

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

    GetConsoleScreenBufferInfo = windll.kernel32.GetConsoleScreenBufferInfo
    GetConsoleScreenBufferInfo.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(PCONSOLE_SCREEN_BUFFER_INFO)]
    GetConsoleScreenBufferInfo.restype = wintypes.BOOL

    FOREGROUND_BLUE = 0x0001
    FOREGROUND_GREEN = 0x0002
    FOREGROUND_RED = 0x0004
    FOREGROUND_INTENSITY = 0x0008
    BACKGROUND_BLUE = 0x0010
    BACKGROUND_GREEN = 0x0020
    BACKGROUND_RED = 0x0040
    BACKGROUND_RED = 0x0040

    class COMMethod(object):

        def __init__(self, name, offset, restype, argtypes):
            self._name = name
            self._restype = restype
            self._offset = offset
            self._argtypes = argtypes

        def __get__(self, instance, owner):
            func = ctypes.WINFUNCTYPE(
                self._restype, *self._argtypes)(self._offset, self._name)

            def wrapper(self, *args, **kwargs):
                return func(self, *args, **kwargs)

            setattr(owner, self._name, wrapper)
            return getattr(instance or owner, self._name)

    class COMInterface(type(ctypes.c_void_p)):

        def __new__(mcls, cls_name, bases, d):

            offset = 0
            for base in bases:
                for realbase in base.__mro__:
                    offset += len(realbase.__dict__.get("_methods_", []))

            for i, args in enumerate(d.get("_methods_", [])):
                name = args[0]
                restype = args[1]
                if restype is None:
                    continue
                argtypes = args[2:]
                m = COMMethod(name, offset + i, restype, argtypes)
                d[name] = m

            return type(ctypes.c_void_p).__new__(mcls, cls_name, bases, dict(d))

    class IUnknown(ctypes.c_void_p, metaclass=COMInterface):

        IID = GUID("{00000001-0000-0000-c000-000000000046}")

        _methods_ = [
        ("QueryInterface", HRESULT, LPGUID, wintypes.LPVOID),
        ("AddRef", wintypes.DWORD),
        ("Release", wintypes.DWORD),
        ]

    LPUNKNOWN = ctypes.POINTER(IUnknown)

    CoCreateInstance = windll.ole32.CoCreateInstance
    CoCreateInstance.argtypes = [REFCLSID, LPUNKNOWN, wintypes.DWORD, REFIID,
                                wintypes.LPVOID]
    CoCreateInstance.restype = HRESULT

    class IShellLinkW(IUnknown):

        IID = GUID("{000214F9-0000-0000-C000-000000000046}")

        _methods_ = [
            ("GetPath", HRESULT, wintypes.LPWSTR, wintypes.INT,
            LPWIN32_FIND_DATAW, wintypes.DWORD),
        ]

    class IPersist(IUnknown):

        IID = GUID("{0000010c-0000-0000-C000-000000000046}")

        _methods_ = [
            ("GetClassID", HRESULT, LPGUID),
        ]

    class IPersistFile(IPersist):

        IID = GUID("{0000010b-0000-0000-c000-000000000046}")

        _methods_ = [
            ("IsDirty", HRESULT),
            ("Load", HRESULT, wintypes.LPOLESTR, wintypes.DWORD),
        ]

    class ITEMIDLIST(ctypes.Structure):
        pass

    IBindCtx = ctypes.c_void_p
    ITEMIDLIST_ABSOLUTE = ITEMIDLIST
    ITEMIDLIST_RELATIVE = ITEMIDLIST
    PIDLIST_ABSOLUTE = ctypes.POINTER(ITEMIDLIST_ABSOLUTE)
    PCUIDLIST_RELATIVE = ctypes.POINTER(ITEMIDLIST_RELATIVE)
    PIDLIST_RELATIVE = ctypes.POINTER(ITEMIDLIST_RELATIVE)
    PCIDLIST_ABSOLUTE = ctypes.POINTER(ITEMIDLIST_ABSOLUTE)
    ITEMID_CHILD = ITEMIDLIST
    PCUITEMID_CHILD = ctypes.POINTER(ITEMID_CHILD)
    PCUITEMID_CHILD_ARRAY = ctypes.POINTER(PCUITEMID_CHILD)

    class IShellFolder(IUnknown):

        IID = GUID("{000214E6-0000-0000-C000-000000000046}")

        _methods_ = [
            ("ParseDisplayName", HRESULT, wintypes.HWND,
            ctypes.POINTER(IBindCtx), wintypes.LPWSTR,
            ctypes.POINTER(wintypes.ULONG), ctypes.POINTER(PIDLIST_RELATIVE),
            ctypes.POINTER(wintypes.ULONG)),
            ("EnumObjects", None),
            ("BindToObject", HRESULT, PCUIDLIST_RELATIVE,
            ctypes.POINTER(IBindCtx), REFIID, ctypes.c_void_p),
        ]

    CLSID_ShellLink = GUID("{00021401-0000-0000-C000-000000000046}")

    SHGetDesktopFolder = oledll.shell32.SHGetDesktopFolder
    SHGetDesktopFolder.argtypes = [ctypes.POINTER(IShellFolder)]
    SHGetDesktopFolder.restype = HRESULT

    ILCombine = windll.shell32.ILCombine
    ILCombine.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    ILCombine.restype = ctypes.c_void_p

    ILCreateFromPathW = windll.shell32.ILCreateFromPathW
    ILCreateFromPathW.argtypes = [wintypes.LPCWSTR]
    ILCreateFromPathW.restype = PIDLIST_ABSOLUTE

    ILFree = windll.shell32.ILFree
    ILFree.argtypes = [PIDLIST_RELATIVE]
    ILFree.restype = None

    SHOpenFolderAndSelectItems = windll.shell32.SHOpenFolderAndSelectItems
    SHOpenFolderAndSelectItems.argtypes = [
        PCIDLIST_ABSOLUTE, wintypes.UINT, PCUITEMID_CHILD_ARRAY, DWORD]
    SHOpenFolderAndSelectItems.restype = HRESULT

    SFGAOF = wintypes.ULONG

    SHParseDisplayName = windll.shell32.SHParseDisplayName
    SHParseDisplayName.argtypes = [
        wintypes.LPCWSTR, ctypes.POINTER(IBindCtx),
        ctypes.POINTER(PIDLIST_ABSOLUTE), SFGAOF, ctypes.POINTER(SFGAOF)]
    SHParseDisplayName.restype = HRESULT

    @enum
    class FOLDERID(str):
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
    class KnownFolderFlag(int):
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
