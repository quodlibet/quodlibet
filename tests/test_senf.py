# Copyright 2016 Christoph Reiter
#
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import contextlib
import ctypes
import shutil
import codecs
from typing import TYPE_CHECKING
from io import BytesIO, StringIO
from tempfile import mkdtemp

import pytest

from quodlibet import senf
from quodlibet.senf import (
    fsnative,
    sep,
    pathsep,
    curdir,
    pardir,
    altsep,
    extsep,
    devnull,
    defpath,
    getcwd,
    uri2fsn,
    fsn2uri,
    path2fsn,
    fsn2text,
    fsn2bytes,
    bytes2fsn,
    print_,
    input_,
    expanduser,
    text2fsn,
    expandvars,
    supports_ansi_escape_codes,
    fsn2norm,
)
from quodlibet.senf._winansi import ansi_parse, ansi_split
from quodlibet.senf._stdlib import _get_userdir
from quodlibet.senf._fsnative import _encoding, is_unix, _surrogatepass, _get_encoding
from quodlibet.senf._print import _encode_codepage, _decode_codepage
from quodlibet.senf import _winapi as winapi


is_wine = "WINEDEBUG" in os.environ
linesepb = os.linesep.encode("ascii")
linesepu = os.linesep


def notfsnative(text=""):
    fsn = fsnative(text)
    if isinstance(fsn, bytes):
        return fsn2text(fsn)
    return fsn2bytes(fsn, "utf-8")


assert not isinstance(notfsnative(), fsnative)


def isunicodeencoding():
    try:
        "\u1234".encode(_encoding)
    except UnicodeEncodeError:
        return False
    return True


def iternotfsn():
    yield notfsnative("foo")

    if is_unix and not isunicodeencoding():
        # in case we have a ascii encoding this is an invalid path
        yield "\u1234"

    yield "\x00"


if TYPE_CHECKING:
    _base = os.PathLike
else:
    _base = object


class PathLike(_base):
    def __init__(self, path):
        self._path = path

    def __fspath__(self):
        return self._path


@contextlib.contextmanager
def preserve_environ(environ=os.environ):
    old = environ.copy()
    if environ is not os.environ:
        with preserve_environ(os.environ):
            yield
    else:
        yield
    # don't touch existing values as os.environ is broken for empty
    # keys on Windows: http://bugs.python.org/issue20658
    for key in list(environ.keys()):
        if key not in old:
            del environ[key]
    for key, value in list(old.items()):
        if key not in environ or environ[key] != value:
            environ[key] = value


environ_case_sensitive = True
with preserve_environ():
    os.environ.pop("senf", None)
    os.environ["SENF"] = "foo"
    environ_case_sensitive = "senf" not in os.environ


@contextlib.contextmanager
def capture_output(data=None):
    """
    with capture_output as (stdout, stderr):
        some_action()
    print stdout.getvalue(), stderr.getvalue()
    """

    in_ = BytesIO(data or b"")
    err = BytesIO()
    out = BytesIO()
    old_in = sys.stdin
    old_err = sys.stderr
    old_out = sys.stdout
    sys.stdin = in_
    sys.stderr = err
    sys.stdout = out

    try:
        yield (out, err)
    finally:
        sys.stdin = old_in
        sys.stderr = old_err
        sys.stdout = old_out


def test__get_encoding():
    # type: () -> None

    orig = sys.getfilesystemencoding
    sys.getfilesystemencoding = lambda: None  # type: ignore
    try:
        codecs.lookup(_get_encoding())
    finally:
        sys.getfilesystemencoding = orig


def _get_real_userdir():
    # Tries to return the real userdir of the current user
    # ignore potentially replaced env vars
    with preserve_environ():
        os.environ.pop("HOME", None)
        userdir = _get_userdir()
    return userdir or _get_userdir()


def test_getuserdir():
    # type: () -> None

    userdir = _get_real_userdir()
    assert isinstance(userdir, fsnative)

    with pytest.raises(TypeError):
        _get_userdir(notfsnative("foo"))

    if sys.platform == "win32":
        otherdir = _get_userdir("foo")
        assert otherdir == os.path.join(os.path.dirname(userdir), "foo")
    else:
        user = os.path.basename(userdir)
        assert userdir == _get_userdir(user)

    if sys.platform != "win32":
        with preserve_environ():
            os.environ["HOME"] = "bla"
            assert _get_userdir() == "bla"

    with preserve_environ():
        os.environ.pop("HOME", None)
        if sys.platform != "win32":
            assert _get_userdir()
        else:
            os.environ["USERPROFILE"] = "uprof"
            assert _get_userdir() == "uprof"

    with preserve_environ():
        os.environ.pop("HOME", None)
        os.environ.pop("USERPROFILE", None)
        if sys.platform == "win32":
            os.environ["HOMEPATH"] = "hpath"
            os.environ["HOMEDRIVE"] = "C:\\"
            assert _get_userdir() == os.path.join("C:", senf.sep, "hpath")
            assert _get_userdir("bla") == os.path.join("C:", senf.sep, "bla")

    with preserve_environ():
        os.environ.pop("HOME", None)
        os.environ.pop("USERPROFILE", None)
        os.environ.pop("HOMEPATH", None)
        if sys.platform == "win32":
            assert _get_userdir() is None


def test_expanduser_simple():
    # type: () -> None

    home = _get_userdir()
    assert expanduser("~") == home
    assert isinstance(expanduser("~"), fsnative)
    assert expanduser(os.path.join("~", "a", "b")) == os.path.join(home, "a", "b")
    assert expanduser(senf.sep + "~") == senf.sep + "~"
    if senf.altsep is not None:
        assert expanduser("~" + senf.altsep) == home + senf.altsep


def test_expanduser_user():
    # type: () -> None

    home = _get_real_userdir()
    user = os.path.basename(home)

    assert expanduser("~" + user) == home
    assert expanduser(os.path.join("~" + user, "foo")) == os.path.join(home, "foo")

    if senf.altsep is not None:
        assert expanduser("~" + senf.altsep + "foo") == home + senf.altsep + "foo"

        assert (
            expanduser("~" + user + senf.altsep + "a" + senf.sep)
            == home + senf.altsep + "a" + senf.sep
        )

    if sys.platform == "win32":
        assert expanduser(os.path.join("~nope", "foo")) == os.path.join(
            os.path.dirname(home), "nope", "foo"
        )


def test_ansi_matching():
    # type: () -> None

    to_match = ["\033[39m", "\033[3m", "\033[m", "\033[;m", "\033[;2;m"]
    for t in to_match:
        assert list(ansi_split(t)) == [(True, t)]

    assert list(ansi_split("foo\033[;2;mbla")) == [
        (False, "foo"),
        (True, "\033[;2;m"),
        (False, "bla"),
    ]

    assert ansi_parse("\033[;2;m") == ("m", (0, 2, 0))
    assert ansi_parse("\033[;m") == ("m", (0, 0))
    assert ansi_parse("\033[k") == ("k", (0,))
    assert ansi_parse("\033[;;k") == ("k", (0, 0, 0))
    assert ansi_parse("\033[100k") == ("k", (100,))
    assert ansi_parse("\033[m") == ("m", (0,))


def test_print():
    # type: () -> None

    f = BytesIO()
    print_("foo", file=f)  # type: ignore
    out = f.getvalue()
    assert isinstance(out, bytes)
    assert out == b"foo" + linesepb

    f2 = StringIO()
    print_("foo", file=f2)
    out2 = f2.getvalue()
    assert isinstance(out2, str)
    assert out2 == "foo" + os.linesep

    print_("foo", file=f, flush=True)  # type: ignore

    f3 = StringIO()
    print_("foo", file=f3)
    out3 = f3.getvalue()
    assert isinstance(out3, str)
    assert out3 == "foo" + linesepu

    f4 = StringIO()
    print_("", file=f4, end=b"\n")  # type: ignore
    out4 = f4.getvalue()
    assert isinstance(out4, str)
    assert out4 == linesepu

    f5 = BytesIO()
    print_("", file=f5, end=b"\n")  # type: ignore
    out5 = f5.getvalue()
    assert isinstance(out5, bytes)
    assert out5 == linesepb


@pytest.mark.skipif(os.name != "nt", reason="win only")
def test_print_windows():
    # type: () -> None

    f = BytesIO()
    print_("öäü\ud83d", file=f)  # type: ignore
    out = f.getvalue()
    assert isinstance(out, bytes)
    assert out == b"\xc3\xb6\xc3\xa4\xc3\xbc\xed\xa0\xbd" + linesepb

    f2 = StringIO()
    print_("öäü\ud83d", file=f2)
    out2 = f2.getvalue()
    assert isinstance(out2, str)
    assert out2 == "öäü\ud83d" + linesepu


def test_print_defaults_none():
    # type: () -> None

    # python 3 print takes None as default, try to do the same
    with capture_output() as (out, err):
        print_("foo", "bar")
    first = out.getvalue()
    with capture_output() as (out, err):
        print_("foo", "bar", end=None, sep=None, file=None)  # type: ignore
    assert out.getvalue() == first


def test_print_ansi():
    # type: () -> None

    for i in range(1, 110):
        print_("\033[%dm" % i, end="")
    other = [
        "\033[A",
        "\033[B",
        "\033[C",
        "\033[D",
        "\033[s",
        "\033[u",
        "\033[H",
        "\033[f",
    ]
    for c in other:
        print_(c, end="")


def test_print_anything():
    # type: () -> None

    with capture_output():
        print_("\u1234")

    with capture_output() as (out, err):
        print_(5, end="")
        assert out.getvalue() == b"5"

    with capture_output() as (out, err):
        print_([], end="")
        assert out.getvalue() == b"[]"


def test_print_error():
    # type: () -> None

    with pytest.raises(TypeError):
        print_(end=4)  # type: ignore

    with pytest.raises(TypeError):
        print_(sep=4)  # type: ignore


@pytest.mark.skipif(os.name != "nt", reason="windows only")
def test_win_cp_encodings():
    # type: () -> None

    assert _encode_codepage(437, "foo") == b"foo"
    assert _encode_codepage(437, "\xe4") == b"\x84"
    assert _encode_codepage(437, "") == b""
    assert _encode_codepage(437, "\ud83d") == b"?"
    assert _decode_codepage(437, b"foo") == "foo"
    assert _decode_codepage(437, b"\x84") == "\xe4"
    assert _decode_codepage(437, b"") == ""


@pytest.mark.skipif(os.name == "nt", reason="unix only")
def test_print_strict_strio():
    # type: () -> None

    f = StringIO()

    real_write = f.write

    def strict_write(data):
        if not isinstance(data, str):
            raise TypeError
        real_write(data.encode("utf-8").decode("utf-8"))

    f.write = strict_write  # type: ignore

    print_(b"\xff\xfe".decode(_encoding, "surrogateescape"), file=f)
    assert f.getvalue() == "\ufffd\ufffd\n"


def test_print_real():
    # type: () -> None

    print_("foo")
    print_("foo", file=sys.stderr)
    print_("\033[94mfoo", "\033[0m")
    print_(b"foo")
    print_("foo", flush=True)
    print_("\ud83d")


def test_print_capture():
    # type: () -> None

    with capture_output() as (out, err):
        print_("bla")
        assert out.getvalue() == b"bla" + linesepb
        assert err.getvalue() == b""

    with capture_output() as (out, err):
        print_("bla", end="\n")
        assert out.getvalue() == b"bla" + linesepb

    with capture_output() as (out, err):
        print_()
        assert out.getvalue() == linesepb


def test_print_py3_stringio():
    # type: () -> None

    if os.name != "nt":
        f = StringIO()
        print_(b"\xff\xfe", file=f)
        assert f.getvalue() == b"\xff\xfe\n".decode(_encoding, "surrogateescape")


def test_input():
    # type: () -> None

    with capture_output(b"foo" + linesepb + b"bla"):
        out = input_()
        assert out == "foo"
        assert isinstance(out, fsnative)
        out = input_()
        assert out == "bla"
        assert isinstance(out, fsnative)


def test_input_prompt():
    # type: () -> None

    with capture_output(b"foo") as (out, err):
        in_ = input_("bla")
        assert in_ == "foo"
        assert isinstance(in_, fsnative)
        assert out.getvalue() == b"bla"
        assert err.getvalue() == b""


def test_version():
    # type: () -> None

    assert isinstance(senf.version, tuple)
    assert len(senf.version) == 3


def test_version_string():
    # type: () -> None

    assert isinstance(senf.version_string, str)


def test_fsnative():
    # type: () -> None

    assert isinstance(fsnative("foo"), fsnative)
    fsntype = type(fsnative(""))
    assert issubclass(fsntype, fsnative)
    with pytest.raises(TypeError):
        fsnative(b"")  # type: ignore

    assert fsnative("\x00") == fsnative("\ufffd")

    assert isinstance(fsnative("\x00"), fsnative)
    for inst in iternotfsn():
        assert not isinstance(inst, fsnative)

    if isinstance(fsnative("\ud800"), str) and fsnative("\ud800") != "\ud800":
        assert not isinstance("\ud800", fsnative)

    fsn = fsnative("\udcc2\udc80")
    assert fsn == fsn2norm(fsn)

    fsn = fsnative("\ud800\udc01")
    assert fsn == fsn2norm(fsn)


def test_path2fsn():
    # type: () -> None

    assert isinstance(path2fsn(senf.__path__[0]), fsnative)  # type: ignore

    with pytest.raises(ValueError):
        path2fsn(b"\x00")
    with pytest.raises(ValueError):
        path2fsn("\x00")

    if sys.platform == "win32":
        assert path2fsn("\u1234") == "\u1234"
        assert path2fsn("abc") == "abc"
        assert isinstance(path2fsn("abc"), fsnative)
        assert path2fsn(b"abc") == "abc"

        try:
            path = "\xf6".encode(_encoding)
        except UnicodeEncodeError:
            pass
        else:
            assert path2fsn(path) == "\xf6"

    else:
        assert path2fsn("foo") == fsnative("foo")
        assert path2fsn(b"foo") == fsnative("foo")

        # non unicode encoding, e.g. ascii
        if fsnative("\u1234") != "\u1234":
            with pytest.raises(ValueError):
                path2fsn("\u1234")
            assert fsnative("\u1234") == path2fsn(fsnative("\u1234"))

    with pytest.raises(TypeError):
        path2fsn(object())  # type: ignore


@pytest.mark.skipif(not hasattr(os, "fspath"), reason="python3.6 only")
def test_path2fsn_pathlike():
    # type: () -> None

    # basic tests for os.fspath
    with pytest.raises(TypeError):
        os.fspath(PathLike(None))
    assert os.fspath(PathLike(fsnative("foo"))) == fsnative("foo")
    assert os.fspath(PathLike("\u1234")) == "\u1234"

    # now support in path2fsn
    pathlike = PathLike(fsnative("foo"))
    assert path2fsn(pathlike) == fsnative("foo")

    # pathlib should also work..
    from pathlib import Path

    assert path2fsn(Path(".")) == fsnative(".")


def test_fsn2text():
    # type: () -> None

    assert fsn2text(fsnative("foo")) == "foo"
    with pytest.raises(TypeError):
        fsn2text(object())  # type: ignore
    with pytest.raises(TypeError):
        fsn2text(notfsnative("foo"))

    for path in iternotfsn():
        with pytest.raises(TypeError):
            fsn2text(path)

    if sys.platform == "win32":
        assert fsn2text("\ud800\udc01") == "\U00010001"


def test_fsn2text_strict():
    # type: () -> None

    if sys.platform != "win32":
        path = bytes2fsn(b"\xff", None)
    else:
        path = "\ud83d"

    if text2fsn(fsn2text(path)) != path:
        with pytest.raises(ValueError):
            fsn2text(path, strict=True)


def test_text2fsn():
    # type: () -> None

    with pytest.raises(TypeError):
        text2fsn(b"foo")  # type: ignore
    assert text2fsn("foo") == fsnative("foo")


def test_fsn2bytes():
    # type: () -> None

    assert fsn2bytes(fsnative("foo"), "utf-8") == b"foo"
    with pytest.raises(TypeError):
        fsn2bytes(object(), "utf-8")  # type: ignore

    with pytest.raises(TypeError):
        fsn2bytes("\x00", "utf-8")  # type: ignore

    if sys.platform != "win32":
        assert fsn2bytes(fsnative("foo"), None) == b"foo"
    else:
        with pytest.raises(ValueError):
            fsn2bytes(fsnative("foo"), "notanencoding")
        with pytest.raises(ValueError):
            fsn2bytes(fsnative("foo"), None)  # type: ignore
        with pytest.raises(TypeError):
            fsn2bytes(fsnative("foo"), object())  # type: ignore

    for path in iternotfsn():
        with pytest.raises(TypeError):
            fsn2bytes(path)

    assert fsn2bytes(fsnative("foo"), "utf-8") == fsn2bytes(fsnative("foo"))


@pytest.mark.skipif(os.name != "nt", reason="win only")
def test_fsn2bytes_surrogate_pairs():
    # type: () -> None

    assert fsn2bytes("\ud800\udc01", "utf-8") == b"\xf0\x90\x80\x81"
    assert fsn2bytes("\ud800\udc01", "utf-16-le") == b"\x00\xd8\x01\xdc"
    assert fsn2bytes("\ud800\udc01", "utf-16-be") == b"\xd8\x00\xdc\x01"
    assert fsn2bytes("\ud800\udc01", "utf-16") == b"\xff\xfe\x00\xd8\x01\xdc"
    assert fsn2bytes("\ud800\udc01", "utf-32-le") == b"\x01\x00\x01\x00"
    assert fsn2bytes("\ud800\udc01", "utf-32-be") == b"\x00\x01\x00\x01"

    for c in ["utf-8", "utf-16-le", "utf-16-be", "utf-32-le", "utf-32-be"]:
        assert fsn2bytes(
            bytes2fsn(fsn2bytes("\ud800", c), c) + bytes2fsn(fsn2bytes("\udc01", c), c),
            c,
        ) == fsn2bytes("\ud800\udc01", c)


@pytest.mark.skipif(os.name != "nt", reason="win only")
def test_fsn2bytes_wtf8():
    # type: () -> None

    test_data = {
        "aé ": b"a\xc3\xa9 ",
        "aé 💩": b"a\xc3\xa9 \xf0\x9f\x92\xa9",
        "\ud83d\x20\udca9": b"\xed\xa0\xbd \xed\xb2\xa9",
        "\ud800\udbff": b"\xed\xa0\x80\xed\xaf\xbf",
        "\ud800\ue000": b"\xed\xa0\x80\xee\x80\x80",
        "\ud7ff\udc00": b"\xed\x9f\xbf\xed\xb0\x80",
        "\x61\udc00": b"\x61\xed\xb0\x80",
        "\udc00": b"\xed\xb0\x80",
    }

    for uni, data in test_data.items():
        assert fsn2bytes(uni, "utf-8") == data

    def cat(*args):
        return fsn2bytes("".join([bytes2fsn(a, "utf-8") for a in args]), "utf-8")

    assert cat(b"\xed\xa0\xbd", b"\xed\xb2\xa9") == b"\xf0\x9f\x92\xa9"
    assert cat(b"\xed\xa0\xbd", b" ", b"\xed\xb2\xa9") == b"\xed\xa0\xbd \xed\xb2\xa9"
    assert cat(b"\xed\xa0\x80", b"\xed\xaf\xbf") == b"\xed\xa0\x80\xed\xaf\xbf"
    assert cat(b"\xed\xa0\x80", b"\xee\x80\x80") == b"\xed\xa0\x80\xee\x80\x80"
    assert cat(b"\xed\x9f\xbf", b"\xed\xb0\x80") == b"\xed\x9f\xbf\xed\xb0\x80"
    assert cat(b"a", b"\xed\xb0\x80") == b"\x61\xed\xb0\x80"
    assert cat(b"\xed\xb0\x80") == b"\xed\xb0\x80"


@pytest.mark.skipif(os.name != "nt", reason="win only")
def test_fsn2bytes_ill_formed_utf16():
    # type: () -> None

    p = bytes2fsn(b"a\x00\xe9\x00 \x00=\xd8=\xd8\xa9\xdc", "utf-16-le")
    assert fsn2bytes(p, "utf-8") == b"a\xc3\xa9 \xed\xa0\xbd\xf0\x9f\x92\xa9"
    assert (
        fsn2bytes("aé " + "\ud83d" + "💩", "utf-16-le")
        == b"a\x00\xe9\x00 \x00=\xd8=\xd8\xa9\xdc"
    )


def test_surrogates():
    # type: () -> None

    if sys.platform == "win32":
        assert fsn2bytes("\ud83d", "utf-16-le") == b"=\xd8"
        assert bytes2fsn(b"\xd8=", "utf-16-be") == "\ud83d"

        with pytest.raises(ValueError):
            bytes2fsn(b"\xd8=a", "utf-16-be")

        with pytest.raises(ValueError):
            bytes2fsn(b"=\xd8a", "utf-16-le")

        # for utf-16-le we have a workaround
        assert bytes2fsn(b"=\xd8", "utf-16-le") == "\ud83d"
        assert bytes2fsn(b"=\xd8=\xd8", "utf-16-le") == "\ud83d\ud83d"

        with pytest.raises(ValueError):
            bytes2fsn(b"=\xd8\x00\x00", "utf-16-le")

        # 4 byte code point
        assert fsn2bytes("\U0001f600", "utf-16-le") == b"=\xd8\x00\xde"
        assert bytes2fsn(b"=\xd8\x00\xde", "utf-16-le") == "\U0001f600"

        # 4 byte codepoint + lone surrogate
        assert bytes2fsn(b"=\xd8\x00\xde=\xd8", "utf-16-le") == "\U0001f600\ud83d"

        with pytest.raises(UnicodeDecodeError):
            bytes2fsn(b"a", "utf-16-le")

        assert fsn2bytes("\ud83d", "utf-8") == b"\xed\xa0\xbd"
        assert bytes2fsn(b"\xed\xa0\xbd", "utf-8") == "\ud83d"

        assert fsnative("\ud83d") == "\ud83d"
        assert fsn2text("\ud83d") == "\ufffd"

        # at least don't fail...
        assert fsn2uri("C:\\\ud83d") == "file:///C:/%ED%A0%BD"
    else:
        # this shouldn't fail and produce the same result on py2/3 at least.
        assert fsn2bytes(fsnative("\ud83d"), None) == b"\xed\xa0\xbd"
        text2fsn(fsn2text(fsnative("\ud83d")))

        # under Python 3 the decoder don't allow surrogates
        assert fsn2text(fsnative("\ud83d")) == "\ufffd\ufffd\ufffd"


def test_bytes2fsn():
    # type: () -> None

    assert bytes2fsn(b"foo", "utf-8") == fsnative("foo")
    assert bytes2fsn(fsn2bytes(fsnative("\u1234"), "utf-8"), "utf-8") == fsnative(
        "\u1234"
    )

    with pytest.raises(ValueError):
        bytes2fsn(b"\x00", "utf-8")

    with pytest.raises(ValueError):
        bytes2fsn(b"\x00\x00", "utf-16-le")

    with pytest.raises(TypeError):
        bytes2fsn(object(), "utf-8")  # type: ignore

    with pytest.raises(TypeError):
        bytes2fsn("data", "utf-8")  # type: ignore

    if sys.platform == "win32":
        with pytest.raises(ValueError):
            bytes2fsn(b"data", "notanencoding")
        with pytest.raises(ValueError):
            bytes2fsn(b"data", None)  # type: ignore
        with pytest.raises(TypeError):
            bytes2fsn(b"data", object())  # type: ignore

    assert bytes2fsn(b"foo", "utf-8") == bytes2fsn(b"foo")


def test_constants():
    # type: () -> None

    assert isinstance(sep, fsnative)
    assert isinstance(pathsep, fsnative)
    assert isinstance(curdir, fsnative)
    assert isinstance(pardir, fsnative)
    assert altsep is None or isinstance(altsep, fsnative)
    assert isinstance(extsep, fsnative)
    assert isinstance(devnull, fsnative)
    assert isinstance(defpath, fsnative)


def test_getcwd():
    # type: () -> None

    assert isinstance(getcwd(), fsnative)


def test_uri2fsn():
    # type: () -> None

    if sys.platform != "win32":
        with pytest.raises(ValueError):
            assert uri2fsn("file:///%00")
        with pytest.raises(ValueError):
            assert uri2fsn("file:///%00")
        assert uri2fsn("file:///foo") == fsnative("/foo")
        assert uri2fsn("file:///foo") == fsnative("/foo")
        assert isinstance(uri2fsn("file:///foo"), fsnative)
        assert isinstance(uri2fsn("file:///foo"), fsnative)
        assert uri2fsn("file:///foo-%E1%88%B4") == path2fsn(b"/foo-\xe1\x88\xb4")
        assert uri2fsn("file:NOPE") == fsnative("NOPE")
        assert uri2fsn("file:/NOPE") == fsnative("/NOPE")
        with pytest.raises(ValueError):
            assert uri2fsn("file://NOPE")
        assert uri2fsn("file:///bla:foo@NOPE.com") == fsnative("/bla:foo@NOPE.com")
        assert uri2fsn("file:///bla?x#b") == fsnative("/bla?x#b")
    else:
        assert uri2fsn("file:///C:/%ED%A0%80") == fsnative("C:\\\ud800")
        assert uri2fsn("file:///C:/%20") == "C:\\ "
        assert uri2fsn("file:NOPE") == "NOPE"
        assert uri2fsn("file:/NOPE") == "\\NOPE"
        with pytest.raises(ValueError):
            assert uri2fsn("file:///C:/%00")
        with pytest.raises(ValueError):
            assert uri2fsn("file:///C:/%00")
        assert uri2fsn("file:///C:/foo") == fsnative("C:\\foo")
        assert uri2fsn("file:///C:/foo") == fsnative("C:\\foo")
        assert isinstance(uri2fsn("file:///C:/foo"), fsnative)
        assert isinstance(uri2fsn("file:///C:/foo"), fsnative)
        assert uri2fsn("file:///C:/foo-\u1234") == fsnative("C:\\foo-\u1234")
        assert uri2fsn("file:///C:/foo-%E1%88%B4") == fsnative("C:\\foo-\u1234")
        assert uri2fsn("file://UNC/foo/bar") == "\\\\UNC\\foo\\bar"
        assert uri2fsn("file://\u1234/\u4321") == "\\\\\u1234\\\u4321"

        # Also handle legacy UNC URIs
        assert uri2fsn("file:////UNC/foo") == "\\\\UNC\\foo"
        assert fsn2uri(uri2fsn("file:////UNC/foo")) == "file://UNC/foo"

    with pytest.raises(TypeError):
        uri2fsn(object())  # type: ignore

    with pytest.raises(ValueError):
        uri2fsn("http://www.foo.bar")

    if os.name == "nt":
        with pytest.raises(ValueError):
            uri2fsn("\u1234")

    with pytest.raises(TypeError):
        uri2fsn(b"file:///foo")  # type: ignore


def test_fsn2uri():
    # type: () -> None

    with pytest.raises(TypeError):
        fsn2uri(object())  # type: ignore

    if sys.platform == "win32":
        with pytest.raises(TypeError):
            fsn2uri("\x00")
        assert fsn2uri(fsnative("C:\\\ud800")) == "file:///C:/%ED%A0%80"
        if is_wine:
            # FIXME: fails on native Windows
            assert fsn2uri(fsnative("C:\\ ")) == "file:///C:/%20"
        assert fsn2uri(fsnative("C:\\foo")) == "file:///C:/foo"
        assert fsn2uri("C:\\ö ä%") == "file:///C:/%C3%B6%20%C3%A4%25"
        assert fsn2uri("C:\\foo-\u1234") == "file:///C:/foo-%E1%88%B4"
        assert isinstance(fsn2uri("C:\\foo-\u1234"), str)
        assert fsn2uri("\\\\serv\\share\\") == "file://serv/share/"
        assert fsn2uri("\\\\serv\\\u1234\\") == "file://serv/%E1%88%B4/"
        assert fsn2uri(fsnative("\\\\UNC\\foo\\bar")) == "file://UNC/foo/bar"

        # winapi can't handle too large paths. make sure we raise properly
        with pytest.raises(ValueError):
            fsn2uri("C:\\" + 4000 * "a")

        assert fsn2uri("C:\\\ud800\udc01") == "file:///C:/%F0%90%80%81"
    else:
        with pytest.raises(TypeError):
            fsn2uri(b"\x00")  # type: ignore
        path = fsnative("/foo-\u1234")
        assert fsn2uri(path) == "file:///foo-%E1%88%B4"
        assert isinstance(fsn2uri(path), str)


def test_uri_roundtrip():
    # type: () -> None

    if sys.platform == "win32":
        for path in [
            "C:\\foo-\u1234",
            "C:\\bla\\quux ha",
            "\\\\\u1234\\foo\\\u1423",
            "\\\\foo;\\f",
        ]:
            path = fsnative(path)
            assert uri2fsn(fsn2uri(path)) == path
            assert isinstance(uri2fsn(fsn2uri(path)), fsnative)
    else:
        path = path2fsn(b"/foo-\xe1\x88\xb4")

        assert uri2fsn(fsn2uri(path2fsn(b"/\x80"))) == path2fsn(b"/\x80")
        assert uri2fsn(fsn2uri(fsnative("/foo"))) == "/foo"
        assert uri2fsn(fsn2uri(path)) == path
        assert isinstance(uri2fsn(fsn2uri(path)), fsnative)


def test_expandvars():
    # type: () -> None

    with preserve_environ():
        os.environ["foo"] = "bar"
        os.environ["nope b"] = "xxx"
        os.environ["f/oo"] = "bar"
        os.environ.pop("nope", "")

        assert expandvars("$foo") == "bar"
        assert expandvars("$nope b") == "$nope b"
        assert expandvars("/$foo/") == "/bar/"
        assert expandvars("$f/oo") == "$f/oo"
        assert expandvars("$nope") == "$nope"
        assert expandvars("$foo_") == "$foo_"

        assert expandvars("${f/oo}") == "bar"
        assert expandvars("${nope b}") == "xxx"
        assert expandvars("${nope}") == "${nope}"
        assert isinstance(expandvars("$foo"), fsnative)

    with preserve_environ():
        if os.name == "nt":
            os.environ["ö"] = "ä"
            os.environ.pop("ä", "")
            assert isinstance(expandvars("$ö"), fsnative)
            assert expandvars("$ö") == "ä"
            assert expandvars("${ö}") == "ä"
            assert expandvars("${ä}") == "${ä}"
            assert expandvars("$ä") == "$ä"

            assert expandvars("%ö") == "%ö"
            assert expandvars("ö%") == "ö%"
            assert expandvars("%ö%") == "ä"
            assert expandvars("%ä%") == "%ä%"


def test_expandvars_case():
    # type: () -> None

    if not environ_case_sensitive:
        with preserve_environ():
            os.environ.pop("foo", None)
            os.environ["FOO"] = "bar"
            assert expandvars("$foo") == "bar"
            os.environ["FOo"] = "baz"
            assert expandvars("$fOO") == "baz"
    else:
        with preserve_environ():
            os.environ.pop("foo", None)
            os.environ["FOO"] = "bar"
            assert expandvars("$foo") == "$foo"


def test_python_handling_broken_utf16():
    # type: () -> None

    # Create a file with an invalid utf-16 name.
    # Mainly to see how Python handles it

    tmp = mkdtemp()
    try:
        path = os.path.join(tmp, "foo")
        with open(path, "wb") as h:
            h.write(b"content")
        assert "foo" in os.listdir(tmp)

        if sys.platform == "win32":
            faulty = path.encode("utf-16-le") + b"=\xd8\x01\xde" + b"=\xd8-\x00\x01\xde"
            buf = ctypes.create_string_buffer(faulty + b"\x00\x00")

            if winapi.MoveFileW(path, ctypes.cast(buf, ctypes.c_wchar_p)) == 0:
                raise ctypes.WinError()
            assert "foo" not in os.listdir(tmp)

            newpath = os.path.join(tmp, os.listdir(tmp)[0])
            if not is_wine:  # this is broken on wine..
                assert newpath.encode("utf-16-le", _surrogatepass) == faulty

            with open(newpath, "rb") as h:
                assert h.read() == b"content"
    finally:
        shutil.rmtree(tmp)


def test_fsn2norm():
    # type: () -> None
    if sys.platform == "win32":
        assert fsn2norm("\ud800\udc01") == fsn2norm("\U00010001")

    if is_unix and isunicodeencoding():
        assert fsn2norm("\udcc2\udc80") == fsn2norm("\x80")

    for path in iternotfsn():
        with pytest.raises(TypeError):
            fsn2norm(path)


def test_supports_ansi_escape_codes():
    # type: () -> None
    supports_ansi_escape_codes(sys.stdout.fileno())
