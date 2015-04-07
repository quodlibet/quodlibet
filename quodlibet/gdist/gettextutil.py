# -*- coding: utf-8 -*-
# Copyright 2014 Christoph Reiter
#
# This software and accompanying documentation, if any, may be freely
# used, distributed, and/or modified, in any form and for any purpose,
# as long as this notice is preserved. There is no warranty, either
# express or implied, for this software.

"""So we don't have to touch intltool directly
(and maybe can get rid of it one day)
"""

import os
import subprocess
from distutils.spawn import find_executable


class GettextError(Exception):
    pass


# pgettext isn't included by default for Python
XGETTEXT_ARGS = "--keyword=C_:1c,2 --keyword=npgettext:1c,2,3"


def update_pot(po_dir, package):
    """Regenerate the pot file in po_dir

        Returns the path to the pot file
    or raise GettextError
    """

    old_dir = os.getcwd()
    os.chdir(po_dir)
    try:
        os.environ["XGETTEXT_ARGS"] = XGETTEXT_ARGS
        subprocess.check_call(["intltool-update", "--pot",
                               "--gettext-package", package])
    except subprocess.CalledProcessError as e:
        raise GettextError(e)
    finally:
        os.chdir(old_dir)

    return os.path.join(po_dir, package + ".pot")


def update_po(po_dir, package, lang_code):
    """Update the <lang_code>.po file base on <package>.pot

    Returns the path to the po file
    or raise GettextError
    """

    old_dir = os.getcwd()
    os.chdir(po_dir)
    try:
        os.environ["XGETTEXT_ARGS"] = XGETTEXT_ARGS
        subprocess.check_call(["intltool-update", "--dist",
                               "--gettext-package", package,
                               lang_code])
    except subprocess.CalledProcessError as e:
        raise GettextError(e)
    finally:
        os.chdir(old_dir)

    return os.path.join(po_dir, lang_code + ".po")


def get_missing(po_dir, package):
    """Returns a list of files which include translatable strings but are
    not listed as translatable.

    or raise GettextError
    """

    old_dir = os.getcwd()
    os.chdir(po_dir)
    try:
        result = subprocess.check_output(
            ["intltool-update", "--maintain",
             "--gettext-package", package],
            stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        raise GettextError(e)
    finally:
        os.chdir(old_dir)

    return result.splitlines()


def _get_xgettext_version():
    """Returns a version tuple e.g. (0, 19, 3) or GettextError"""

    try:
        result = subprocess.check_output(["xgettext", "--version"])
    except subprocess.CalledProcessError as e:
        raise GettextError(e)

    try:
        return tuple(map(int, result.splitlines()[0].split()[-1].split(".")))
    except (IndexError, ValueError) as e:
        raise GettextError(e)


def check_version():
    """Raises GettextError in case intltool and xgettext are missing

    Tries to include a helpful error message..
    """

    if find_executable("intltool-update") is None:
        raise GettextError("intltool-update missing")

    if find_executable("xgettext") is None:
        raise GettextError("xgettext missing")

    if _get_xgettext_version() < (0, 15):
        raise GettextError("xgettext too old, need 0.15+")
