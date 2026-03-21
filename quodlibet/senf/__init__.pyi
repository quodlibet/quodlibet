import sys
import os

from typing import Union, Any, Optional

_pathlike = Union[str, bytes, "os.PathLike[Any]"]
_uri = Union[str, str]
_base = str

class fsnative(_base):
    def __init__(self, object: str = "") -> None: ...

_fsnative = Union[fsnative, _base]

if sys.platform == "win32":
    _bytes_default_encoding = str
else:
    _bytes_default_encoding = Optional[str]

def path2fsn(path: _pathlike) -> _fsnative: ...
def fsn2text(path: _fsnative, strict: bool = False) -> str: ...
def text2fsn(text: str) -> _fsnative: ...
def fsn2bytes(
    path: _fsnative, encoding: _bytes_default_encoding = "utf-8"
) -> bytes: ...
def bytes2fsn(
    data: bytes, encoding: _bytes_default_encoding = "utf-8"
) -> _fsnative: ...
def uri2fsn(uri: _uri) -> _fsnative: ...
def fsn2uri(path: _fsnative) -> str: ...
def fsn2norm(path: _fsnative) -> _fsnative: ...

sep: _fsnative
pathsep: _fsnative
curdir: _fsnative
pardir: _fsnative
altsep: _fsnative
extsep: _fsnative
devnull: _fsnative
defpath: _fsnative

def getcwd() -> _fsnative: ...
def getenv(key: _pathlike, value: _fsnative | None = None) -> _fsnative | None: ...
def putenv(key: _pathlike, value: _pathlike): ...
def unsetenv(key: _pathlike) -> None: ...
def supports_ansi_escape_codes(fd: int) -> bool: ...
def expandvars(path: _pathlike) -> _fsnative: ...
def expanduser(path: _pathlike) -> _fsnative: ...

environ: dict[_fsnative, _fsnative]
argv: list[_fsnative]

def gettempdir() -> _fsnative:
    pass

def mkstemp(
    suffix: _pathlike | None = None,
    prefix: _pathlike | None = None,
    dir: _pathlike | None = None,
    text: bool = False,
) -> tuple[int, _fsnative]: ...
def mkdtemp(
    suffix: _pathlike | None = None,
    prefix: _pathlike | None = None,
    dir: _pathlike | None = None,
) -> _fsnative: ...

version_string: str

version: tuple[int, int, int]

print_ = print

def input_(prompt: Any = None) -> _fsnative: ...
