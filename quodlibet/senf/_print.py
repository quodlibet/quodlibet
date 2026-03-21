# Copyright 2016 Christoph Reiter
#
# SPDX-License-Identifier: GPL-2.0-or-later

import sys
import os
import ctypes
import re
from typing import Any, TYPE_CHECKING

from ._fsnative import _encoding, is_unix, bytes2fsn, fsnative
from ._winansi import AnsiState, ansi_split
from . import _winapi as winapi


def _print_(*objects, **kwargs):
    """print_(*objects, sep=None, end=None, file=None, flush=False)

    Args:
        objects (object): zero or more objects to print
        sep (str): Object separator to use, defaults to ``" "``
        end (str): Trailing string to use, defaults to ``"\\n"``.
            If end is ``"\\n"`` then `os.linesep` is used.
        file (object): A file-like object, defaults to `sys.stdout`
        flush (bool): If the file stream should be flushed
    Raises:
        EnvironmentError

    Like print(), but:

    * Supports printing filenames under Unix + Python 3 and Windows + Python 2
    * Emulates ANSI escape sequence support under Windows
    * Never fails due to encoding/decoding errors. Tries hard to get everything
      on screen as is, but will fall back to "?" if all fails.

    This does not conflict with ``colorama``, but will not use it on Windows.
    """

    sep = kwargs.get("sep")
    sep = sep if sep is not None else " "
    end = kwargs.get("end")
    end = end if end is not None else "\n"
    file = kwargs.get("file")
    file = file if file is not None else sys.stdout
    flush = bool(kwargs.get("flush", False))

    if sys.platform == "win32":
        _print_windows(objects, sep, end, file, flush)
    else:
        _print_unix(objects, sep, end, file, flush)


if TYPE_CHECKING:
    print_ = print
else:
    print_ = _print_


def _print_unix(objects, sep, end, file, flush):
    """A print_() implementation which writes bytes"""

    encoding = _encoding

    if isinstance(sep, str):
        sep = sep.encode(encoding, "replace")
    if not isinstance(sep, bytes):
        raise TypeError

    if isinstance(end, str):
        end = end.encode(encoding, "replace")
    if not isinstance(end, bytes):
        raise TypeError

    if end == b"\n":
        end = os.linesep.encode("ascii")

    parts = []
    for obj in objects:
        if not isinstance(obj, str) and not isinstance(obj, bytes):
            obj = str(obj)
        if isinstance(obj, str):
            try:
                obj = obj.encode(encoding, "surrogateescape")
            except UnicodeEncodeError:
                obj = obj.encode(encoding, "replace")
        assert isinstance(obj, bytes)
        parts.append(obj)

    data = sep.join(parts) + end
    assert isinstance(data, bytes)

    file = getattr(file, "buffer", file)

    try:
        file.write(data)
    except TypeError:
        # For StringIO, first try with surrogates
        surr_data = data.decode(encoding, "surrogateescape")
        try:
            file.write(surr_data)
        except (TypeError, ValueError):
            file.write(data.decode(encoding, "replace"))

    if flush:
        file.flush()


ansi_state = AnsiState()


def _print_windows(objects, sep, end, file, flush):
    """The windows implementation of print_()"""

    h = winapi.INVALID_HANDLE_VALUE

    try:
        fileno = file.fileno()
    except (OSError, AttributeError):
        pass
    else:
        if fileno == 1:
            h = winapi.GetStdHandle(winapi.STD_OUTPUT_HANDLE)
        elif fileno == 2:
            h = winapi.GetStdHandle(winapi.STD_ERROR_HANDLE)

    encoding = _encoding

    parts = []
    for obj in objects:
        if isinstance(obj, bytes):
            obj = obj.decode(encoding, "replace")
        if not isinstance(obj, str):
            obj = str(obj)
        parts.append(obj)

    if isinstance(sep, bytes):
        sep = sep.decode(encoding, "replace")
    if not isinstance(sep, str):
        raise TypeError

    if isinstance(end, bytes):
        end = end.decode(encoding, "replace")
    if not isinstance(end, str):
        raise TypeError

    if end == "\n":
        end = os.linesep

    text = sep.join(parts) + end
    assert isinstance(text, str)

    is_console = True
    if h == winapi.INVALID_HANDLE_VALUE:
        is_console = False
    else:
        # get the default value
        info = winapi.CONSOLE_SCREEN_BUFFER_INFO()
        if not winapi.GetConsoleScreenBufferInfo(h, ctypes.byref(info)):
            is_console = False

    if is_console:
        # make sure we flush before we apply any console attributes
        file.flush()

        # try to force a utf-8 code page, use the output CP if that fails
        cp = winapi.GetConsoleOutputCP()
        try:
            encoding = "utf-8"
            if winapi.SetConsoleOutputCP(65001) == 0:
                encoding = None

            for is_ansi, part in ansi_split(text):
                if is_ansi:
                    ansi_state.apply(h, part)
                else:
                    if encoding is not None:
                        data = part.encode(encoding, "surrogatepass")
                    else:
                        data = _encode_codepage(cp, part)
                    os.write(fileno, data)
        finally:
            # reset the code page to what we had before
            winapi.SetConsoleOutputCP(cp)
    else:
        # try writing bytes first, so in case of Python 2 StringIO we get
        # the same type on all platforms
        try:
            file.write(text.encode("utf-8", "surrogatepass"))
        except (TypeError, ValueError):
            file.write(text)

        if flush:
            file.flush()


def _readline_windows():
    """Raises OSError"""

    try:
        fileno = sys.stdin.fileno()
    except (OSError, AttributeError):
        fileno = -1

    # In case stdin is replaced, read from that
    if fileno != 0:
        return _readline_windows_fallback()

    h = winapi.GetStdHandle(winapi.STD_INPUT_HANDLE)
    if h == winapi.INVALID_HANDLE_VALUE:
        return _readline_windows_fallback()

    buf_size = 1024
    buf = ctypes.create_string_buffer(buf_size * ctypes.sizeof(winapi.WCHAR))
    read = winapi.DWORD()

    text = ""
    while True:
        if winapi.ReadConsoleW(h, buf, buf_size, ctypes.byref(read), None) == 0:
            if not text:
                return _readline_windows_fallback()
            raise ctypes.WinError()
        data = buf[: read.value * ctypes.sizeof(winapi.WCHAR)]
        text += data.decode("utf-16-le", "surrogatepass")
        if text.endswith("\r\n"):
            return text[:-2]


def _decode_codepage(codepage, data):
    """
    Args:
        codepage (int)
        data (bytes)
    Returns:
        `text`

    Decodes data using the given codepage. If some data can't be decoded
    using the codepage it will not fail.
    """

    assert isinstance(data, bytes)

    if not data:
        return ""

    # get the required buffer length first
    length = winapi.MultiByteToWideChar(codepage, 0, data, len(data), None, 0)
    if length == 0:
        raise ctypes.WinError()

    # now decode
    buf = ctypes.create_unicode_buffer(length)
    length = winapi.MultiByteToWideChar(codepage, 0, data, len(data), buf, length)
    if length == 0:
        raise ctypes.WinError()

    return buf[:]


def _encode_codepage(codepage, text):
    """
    Args:
        codepage (int)
        text (text)
    Returns:
        `bytes`

    Encode text using the given code page. Will not fail if a char
    can't be encoded using that codepage.
    """

    assert isinstance(text, str)

    if not text:
        return b""

    size = len(text.encode("utf-16-le", "surrogatepass")) // ctypes.sizeof(winapi.WCHAR)

    # get the required buffer size
    length = winapi.WideCharToMultiByte(codepage, 0, text, size, None, 0, None, None)
    if length == 0:
        raise ctypes.WinError()

    # decode to the buffer
    buf = ctypes.create_string_buffer(length)
    length = winapi.WideCharToMultiByte(
        codepage, 0, text, size, buf, length, None, None
    )
    if length == 0:
        raise ctypes.WinError()
    return buf[:length]


def _readline_windows_fallback():
    # In case reading from the console failed (maybe we get piped data)
    # we assume the input was generated according to the output encoding.
    # Got any better ideas?
    assert sys.platform == "win32"
    cp = winapi.GetConsoleOutputCP()
    data = getattr(sys.stdin, "buffer", sys.stdin).readline().rstrip(b"\r\n")
    return _decode_codepage(cp, data)


def _readline_default():
    assert is_unix
    data = getattr(sys.stdin, "buffer", sys.stdin).readline().rstrip(b"\r\n")
    return data.decode(_encoding, "surrogateescape")


def _readline():
    if sys.platform == "win32":
        return _readline_windows()
    return _readline_default()


def input_(prompt: Any = None) -> fsnative:
    """
    Args:
        prompt (object): Prints the passed object to stdout without
            adding a trailing newline
    Returns:
        `fsnative`
    Raises:
        EnvironmentError

    Like :func:`python3:input` but returns a `fsnative` and allows printing
    filenames as prompt to stdout.

    Use :func:`fsn2text` on the result if you just want to deal with text.
    """

    if prompt is not None:
        print_(prompt, end="")

    return _readline()


def _get_file_name_for_handle(handle):
    """(Windows only) Returns a file name for a file handle.

    Args:
        handle (winapi.HANDLE)
    Returns:
       `text` or `None` if no file name could be retrieved.
    """

    assert sys.platform == "win32"
    assert handle != winapi.INVALID_HANDLE_VALUE

    size = winapi.FILE_NAME_INFO.FileName.offset + winapi.MAX_PATH * ctypes.sizeof(
        winapi.WCHAR
    )
    buf = ctypes.create_string_buffer(size)

    if winapi.GetFileInformationByHandleEx is None:
        # Windows XP
        return None

    status = winapi.GetFileInformationByHandleEx(handle, winapi.FileNameInfo, buf, size)
    if status == 0:
        return None

    name_info = ctypes.cast(buf, ctypes.POINTER(winapi.FILE_NAME_INFO)).contents
    offset = winapi.FILE_NAME_INFO.FileName.offset
    data = buf[offset : offset + name_info.FileNameLength]
    return bytes2fsn(data, "utf-16-le")


def supports_ansi_escape_codes(fd: int) -> bool:
    """Returns whether the output device is capable of interpreting ANSI escape
    codes when :func:`print_` is used.

    Args:
        fd (int): file descriptor (e.g. ``sys.stdout.fileno()``)
    Returns:
        `bool`
    """

    if os.isatty(fd):
        return True

    if sys.platform != "win32":
        return False

    # Check for cygwin/msys terminal
    handle = winapi._get_osfhandle(fd)
    if handle == winapi.INVALID_HANDLE_VALUE:
        return False

    if winapi.GetFileType(handle) != winapi.FILE_TYPE_PIPE:
        return False

    file_name = _get_file_name_for_handle(handle)
    match = re.match(
        "^\\\\(cygwin|msys)-[a-z0-9]+-pty[0-9]+-(from|to)-master$", file_name
    )
    return match is not None
