# Copyright 2016 Christoph Reiter
#
# SPDX-License-Identifier: GPL-2.0-or-later

import tempfile

from ._fsnative import path2fsn, fsnative


def gettempdir():
    """
    Returns:
        `fsnative`

    Like :func:`python3:tempfile.gettempdir`, but always returns a `fsnative`
    path
    """

    # FIXME: I don't want to reimplement all that logic, reading env vars etc.
    # At least for the default it works.
    return path2fsn(tempfile.gettempdir())


def gettempprefix():
    """
    Returns:
        `fsnative`

    Like :func:`python3:tempfile.gettempprefix`, but always returns a
    `fsnative` path
    """

    return path2fsn(tempfile.gettempprefix())


def mkstemp(suffix=None, prefix=None, dir=None, text=False):
    """
    Args:
        suffix (`pathlike` or `None`): suffix or `None` to use the default
        prefix (`pathlike` or `None`): prefix or `None` to use the default
        dir (`pathlike` or `None`): temp dir or `None` to use the default
        text (bool): if the file should be opened in text mode
    Returns:
        Tuple[`int`, `fsnative`]:
            A tuple containing the file descriptor and the file path
    Raises:
        EnvironmentError

    Like :func:`python3:tempfile.mkstemp` but always returns a `fsnative`
    path.
    """

    suffix = fsnative() if suffix is None else path2fsn(suffix)
    prefix = gettempprefix() if prefix is None else path2fsn(prefix)
    dir = gettempdir() if dir is None else path2fsn(dir)

    return tempfile.mkstemp(suffix, prefix, dir, text)


def mkdtemp(suffix=None, prefix=None, dir=None):
    """
    Args:
        suffix (`pathlike` or `None`): suffix or `None` to use the default
        prefix (`pathlike` or `None`): prefix or `None` to use the default
        dir (`pathlike` or `None`): temp dir or `None` to use the default
    Returns:
        `fsnative`: A path to a directory
    Raises:
        EnvironmentError

    Like :func:`python3:tempfile.mkstemp` but always returns a `fsnative` path.
    """

    suffix = fsnative() if suffix is None else path2fsn(suffix)
    prefix = gettempprefix() if prefix is None else path2fsn(prefix)
    dir = gettempdir() if dir is None else path2fsn(dir)

    return tempfile.mkdtemp(suffix, prefix, dir)
