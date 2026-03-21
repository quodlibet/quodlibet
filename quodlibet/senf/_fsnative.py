# Copyright 2016 Christoph Reiter
#
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import ctypes
import codecs
from typing import TYPE_CHECKING, TypeAlias

from . import _winapi as winapi
from urllib.parse import urlparse, quote, unquote, urlunparse

is_win = os.name == "nt"
is_unix = not is_win
is_darwin = sys.platform == "darwin"

_surrogatepass = "surrogatepass"


def _normalize_codec(codec, _cache={}):
    """Raises LookupError"""

    try:
        return _cache[codec]
    except KeyError:
        _cache[codec] = codecs.lookup(codec).name
        return _cache[codec]


def _decode_surrogatepass(data, codec):
    """Like data.decode(codec, 'surrogatepass') but makes utf-16-le/be work
    on Python 2.

    https://bugs.python.org/issue27971

    Raises UnicodeDecodeError, LookupError
    """

    try:
        return data.decode(codec, _surrogatepass)
    except UnicodeDecodeError:
        raise


def _merge_surrogates(text):
    """Returns a copy of the text with all surrogate pairs merged"""

    return _decode_surrogatepass(text.encode("utf-16-le", _surrogatepass), "utf-16-le")


def fsn2norm(path):
    """
    Args:
        path (fsnative): The path to normalize
    Returns:
        `fsnative`

    Normalizes an fsnative path.

    The same underlying path can have multiple representations as fsnative
    (due to surrogate pairs and variable length encodings). When concatenating
    fsnative the result might be different than concatenating the serialized
    form and then deserializing it.

    This returns the normalized form i.e. the form which os.listdir() would
    return. This is useful when you alter fsnative but require that the same
    underlying path always maps to the same fsnative value.

    All functions like :func:`bytes2fsn`, :func:`fsnative`, :func:`text2fsn`
    and :func:`path2fsn` always return a normalized path, independent of their
    input.
    """

    native = _fsn2native(path)

    if is_win:
        return _merge_surrogates(native)
    return bytes2fsn(native, None)


def _fsnative(text):
    if not isinstance(text, str):
        raise TypeError("%r needs to be a text type (%r)" % (text, str))

    if is_unix:
        # First we go to bytes so we can be sure we have a valid source.
        # Theoretically we should fail here in case we have a non-unicode
        # encoding. But this would make everything complicated and there is
        # no good way to handle a failure from the user side. Instead
        # fall back to utf-8 which is the most likely the right choice in
        # a mis-configured environment
        encoding = _encoding
        try:
            path = text.encode(encoding, _surrogatepass)
        except UnicodeEncodeError:
            path = text.encode("utf-8", _surrogatepass)

        if b"\x00" in path:
            path = path.replace(b"\x00", fsn2bytes(_fsnative("\ufffd"), None))

        return path.decode(_encoding, "surrogateescape")
    if "\x00" in text:
        text = text.replace("\x00", "\ufffd")
    text = fsn2norm(text)
    return text


if TYPE_CHECKING:
    fsnative: TypeAlias = str
else:

    class _meta(type):
        def __instancecheck__(self, instance):
            return _typecheck_fsnative(instance)

        def __subclasscheck__(self, subclass):
            return issubclass(subclass, str)

    class fsnative(str, metaclass=_meta):
        """fsnative(text=u"")

        Args:
            text (text): The text to convert to a path
        Returns:
            fsnative: The new path.
        Raises:
            TypeError: In case something other then `text` has been passed

        This type is a virtual base class for the real path type.
        Instantiating it returns an instance of the real path type and it
        overrides instance and subclass checks so that `isinstance` and
        `issubclass` checks work:

        ::

            isinstance(fsnative(u"foo"), fsnative) == True
            issubclass(type(fsnative(u"foo")), fsnative) == True

        The real returned type is:

        - **Python 2 + Windows:** :obj:`python:unicode`, with ``surrogates``,
            without ``null``
        - **Python 2 + Unix:** :obj:`python:str`, without ``null``
        - **Python 3 + Windows:** :obj:`python3:str`, with ``surrogates``,
            without ``null``
        - **Python 3 + Unix:** :obj:`python3:str`, with ``surrogates``, without
            ``null``, without code points not encodable with the locale encoding

        Constructing a `fsnative` can't fail.

        Passing a `fsnative` to :func:`open` will never lead to `ValueError`
        or `TypeError`.

        Any operation on `fsnative` can also use the `str` type, as long as
        the `str` only contains ASCII and no NULL.
        """

        def __new__(cls, text=""):
            return _fsnative(text)


def _typecheck_fsnative(path):
    """
    Args:
        path (object)
    Returns:
        bool: if path is a fsnative
    """

    if not isinstance(path, str):
        return False

    if "\x00" in path:
        return False

    if is_unix:
        try:
            path.encode(_encoding, "surrogateescape")
        except UnicodeEncodeError:
            return False

    return True


def _fsn2native(path):
    """
    Args:
        path (fsnative)
    Returns:
        `text` on Windows, `bytes` on Unix
    Raises:
        TypeError: in case the type is wrong or the ´str` on Py3 + Unix
            can't be converted to `bytes`

    This helper allows to validate the type and content of a path.
    To reduce overhead the encoded value for Py3 + Unix is returned so
    it can be reused.
    """

    if not isinstance(path, str):
        raise TypeError(
            "path needs to be %s, not %s" % (str.__name__, type(path).__name__)
        )

    if is_unix:
        try:
            path = path.encode(_encoding, "surrogateescape")
        except UnicodeEncodeError:
            # This look more like ValueError, but raising only one error
            # makes things simpler... also one could say str + surrogates
            # is its own type
            raise TypeError(
                "path contained Unicode code points not valid in"
                "the current path encoding. To create a valid "
                "path from Unicode use text2fsn()"
            )

        if b"\x00" in path:
            raise TypeError("fsnative can't contain nulls")
    else:
        if "\x00" in path:
            raise TypeError("fsnative can't contain nulls")

    return path


def _get_encoding():
    """The encoding used for paths, argv, environ, stdout and stdin"""

    encoding = sys.getfilesystemencoding()
    if encoding is None:
        if is_darwin:
            encoding = "utf-8"
        elif is_win:
            encoding = "mbcs"
        else:
            encoding = "ascii"
    encoding = _normalize_codec(encoding)
    return encoding


_encoding = _get_encoding()


def path2fsn(path):
    """
    Args:
        path (pathlike): The path to convert
    Returns:
        `fsnative`
    Raises:
        TypeError: In case the type can't be converted to a `fsnative`
        ValueError: In case conversion fails

    Returns a `fsnative` path for a `pathlike`.
    """

    path = getattr(os, "fspath", lambda x: x)(path)
    if isinstance(path, bytes):
        if b"\x00" in path:
            raise ValueError("embedded null")
        path = path.decode(_encoding, "surrogateescape")
    elif is_unix and isinstance(path, str):
        # make sure we can encode it and this is not just some random
        # unicode string
        data = path.encode(_encoding, "surrogateescape")
        if b"\x00" in data:
            raise ValueError("embedded null")
        path = fsn2norm(path)
    else:
        if "\x00" in path:
            raise ValueError("embedded null")
        path = fsn2norm(path)

    if not isinstance(path, str):
        raise TypeError("path needs to be %s", str.__name__)

    return path


def fsn2text(path, strict=False):
    """
    Args:
        path (fsnative): The path to convert
        strict (bool): Fail in case the conversion is not reversible
    Returns:
        `text`
    Raises:
        TypeError: In case no `fsnative` has been passed
        ValueError: In case ``strict`` was True and the conversion failed

    Converts a `fsnative` path to `text`.

    Can be used to pass a path to some unicode API, like for example a GUI
    toolkit.

    If ``strict`` is True the conversion will fail in case it is not
    reversible. This can be useful for converting program arguments that are
    supposed to be text and erroring out in case they are not.

    Encoding with a Unicode encoding will always succeed with the result.
    """

    path = _fsn2native(path)

    errors = "strict" if strict else "replace"

    if is_win:
        return path.encode("utf-16-le", _surrogatepass).decode("utf-16-le", errors)
    return path.decode(_encoding, errors)


def text2fsn(text):
    """
    Args:
        text (text): The text to convert
    Returns:
        `fsnative`
    Raises:
        TypeError: In case no `text` has been passed

    Takes `text` and converts it to a `fsnative`.

    This operation is not reversible and can't fail.
    """

    return fsnative(text)


def fsn2bytes(path, encoding="utf-8"):
    """
    Args:
        path (fsnative): The path to convert
        encoding (`str`): encoding used for Windows
    Returns:
        `bytes`
    Raises:
        TypeError: If no `fsnative` path is passed
        ValueError: If encoding fails or the encoding is invalid

    Converts a `fsnative` path to `bytes`.

    The passed *encoding* is only used on platforms where paths are not
    associated with an encoding (Windows for example).

    For Windows paths, lone surrogates will be encoded like normal code points
    and surrogate pairs will be merged before encoding. In case of ``utf-8``
    or ``utf-16-le`` this is equal to the `WTF-8 and WTF-16 encoding
    <https://simonsapin.github.io/wtf-8/>`__.
    """

    path = _fsn2native(path)

    if is_win:
        if encoding is None:
            raise ValueError("invalid encoding %r" % encoding)

        try:
            return path.encode(encoding)
        except LookupError:
            raise ValueError("invalid encoding %r" % encoding)
        except UnicodeEncodeError:
            # Fallback implementation for text including surrogates
            # merge surrogate codepoints
            if _normalize_codec(encoding).startswith("utf-16"):
                # fast path, utf-16 merges anyway
                return path.encode(encoding, _surrogatepass)
            return _merge_surrogates(path).encode(encoding, _surrogatepass)
    else:
        return path


def bytes2fsn(data, encoding="utf-8"):
    """
    Args:
        data (bytes): The data to convert
        encoding (`str`): encoding used for Windows
    Returns:
        `fsnative`
    Raises:
        TypeError: If no `bytes` path is passed
        ValueError: If decoding fails or the encoding is invalid

    Turns `bytes` to a `fsnative` path.

    The passed *encoding* is only used on platforms where paths are not
    associated with an encoding (Windows for example).

    For Windows paths ``WTF-8`` is accepted if ``utf-8`` is used and
    ``WTF-16`` accepted if ``utf-16-le`` is used.
    """

    if not isinstance(data, bytes):
        raise TypeError("data needs to be bytes")

    if is_win:
        if encoding is None:
            raise ValueError("invalid encoding %r" % encoding)
        try:
            path = _decode_surrogatepass(data, encoding)
        except LookupError:
            raise ValueError("invalid encoding %r" % encoding)
        if "\x00" in path:
            raise ValueError("contains nulls")
        return path
    if b"\x00" in data:
        raise ValueError("contains nulls")
    return data.decode(_encoding, "surrogateescape")


def uri2fsn(uri):
    """
    Args:
        uri (`text` or :obj:`python:str`): A file URI
    Returns:
        `fsnative`
    Raises:
        TypeError: In case an invalid type is passed
        ValueError: In case the URI isn't a valid file URI

    Takes a file URI and returns a `fsnative` path
    """

    if not isinstance(uri, str):
        raise TypeError("uri needs to be str")

    parsed = urlparse(uri)
    scheme = parsed.scheme
    netloc = parsed.netloc
    parsed_path = parsed.path

    if scheme != "file":
        raise ValueError("Not a file URI: %r" % uri)

    if not parsed_path:
        raise ValueError("Invalid file URI: %r" % uri)

    uri = urlunparse(parsed)[5:]
    if not parsed_path.startswith("/") and uri.startswith("/"):
        uri = uri.lstrip("/")
    if not netloc and uri.startswith("///"):
        uri = uri[2:]

    if is_win:
        try:
            drive, rest = uri.split(":", 1)
        except ValueError:
            path = ""
            rest = uri.replace("/", "\\")
        else:
            path = drive[-1] + ":"
            rest = rest.replace("/", "\\")
        path += unquote(rest, encoding="utf-8", errors="surrogatepass")
        if "\x00" in path:
            raise ValueError("embedded null")
        return path
    path = unquote(uri, encoding=_encoding, errors="surrogateescape")
    if "\x00" in path:
        raise ValueError("embedded null")
    return path


def fsn2uri(path):
    """
    Args:
        path (fsnative): The path to convert to an URI
    Returns:
        `text`: An ASCII only URI
    Raises:
        TypeError: If no `fsnative` was passed
        ValueError: If the path can't be converted

    Takes a `fsnative` path and returns a file URI.

    On Windows non-ASCII characters will be encoded using utf-8 and then
    percent encoded.
    """

    path = _fsn2native(path)

    def _quote_path(path):
        # RFC 2396
        path = quote(path, "/:@&=+$,")
        return path

    if is_win:
        buf = ctypes.create_unicode_buffer(winapi.INTERNET_MAX_URL_LENGTH)
        length = winapi.DWORD(winapi.INTERNET_MAX_URL_LENGTH)
        flags = 0
        try:
            winapi.UrlCreateFromPathW(path, buf, ctypes.byref(length), flags)
        except OSError as e:
            raise ValueError(e)
        uri = buf[: length.value]
        # https://bitbucket.org/pypy/pypy/issues/3133
        uri = _merge_surrogates(uri)

        # For some reason UrlCreateFromPathW escapes some chars outside of
        # ASCII and some not. Unquote and re-quote with utf-8.
        # latin-1 maps code points directly to bytes, which is what we want
        uri = unquote(uri, "latin-1")

        return _quote_path(uri.encode("utf-8", _surrogatepass))

    return "file://" + _quote_path(path)
