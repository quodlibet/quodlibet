# -*- coding: utf-8 -*-
# Copyright 2015-2017 Christoph Reiter
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""So we don't have to touch intltool directly
(and maybe can get rid of it one day)
"""

import os
import glob
import subprocess
import contextlib
from distutils.spawn import find_executable


class GettextError(Exception):
    pass


def _get_xgettext_args():
    # pgettext isn't included by default for Python for example
    EXTRA_KEYWORDS = {
        "_": "",
        "N_": "",
        "C_": "1c,2",
        "NC_": "1c,2",
        "Q_": "",
        "pgettext": "1c,2",
        "npgettext": "1c,2,3",
        "numeric_phrase": "1,2",
        "dgettext": "2",
        "ngettext": "1,2",
        "dngettext": "2,3",
    }

    # The lone -k disables default xgettext keywords
    args = ["-k"]

    # There are still some keywords defined by intltool-update which we can't
    # change, but they shouldn't conflict with anything.

    for name, spec in EXTRA_KEYWORDS.items():
        if spec:
            args.append("--keyword=%s:%s" % (name, spec))
        else:
            args.append("--keyword=%s" % name)

    return args

XGETTEXT_ARGS = " ".join(_get_xgettext_args())


def cyg2winpath(path):
    assert os.name == "nt"
    win_path = subprocess.check_output(
        ["cygpath.exe", "-m" if os.sep == "/" else "-w", "--", path])
    return win_path.decode("utf-8").strip()


def intltool(*args):
    command = args[0]
    args = args[1:]
    if os.name == "nt":
        return [cyg2winpath("/usr/bin/perl"),
                "/usr/bin/intltool-%s" % command] + list(args)
    else:
        return ["intltool-%s" % command] + list(args)


def _update_pot(po_dir, package):
    """Regenerate the pot file in po_dir

    Returns the path to the pot file or raise GettextError
    """

    try:
        os.environ["XGETTEXT_ARGS"] = XGETTEXT_ARGS
        with open(os.devnull, 'wb') as devnull:
            subprocess.check_call(
                intltool("update", "--pot", "--gettext-package", package),
                stderr=devnull, stdout=devnull, cwd=po_dir)
    except subprocess.CalledProcessError as e:
        raise GettextError(e)

    return os.path.join(po_dir, package + ".pot")


@contextlib.contextmanager
def create_pot(po_dir, package):
    """Temporarily creates a .pot file in po_dir"""

    path = _update_pot(po_dir, package)
    try:
        yield path
    finally:
        os.unlink(path)


def list_languages(po_dir):
    """Returns a list of available language codes"""

    po_files = glob.glob(os.path.join(po_dir, "*.po"))
    return sorted([os.path.basename(po[:-3]) for po in po_files])


def update_po(po_dir, package, lang_code, output_file=None):
    """Update the <lang_code>.po file based on <package>.pot

    If output_file is given the resulting po file will be save to that path.

    Returns the path to the po file
    or raise GettextError
    """

    try:
        os.environ["XGETTEXT_ARGS"] = XGETTEXT_ARGS
        args = intltool(
            "update", "--dist", "--gettext-package", package, lang_code)
        if output_file is not None:
            args.extend(["--output-file", output_file])
        with open(os.devnull, 'wb') as devnull:
            subprocess.check_call(
                args, stderr=devnull, stdout=devnull, cwd=po_dir)
    except subprocess.CalledProcessError as e:
        raise GettextError(e)

    if output_file is not None:
        return output_file

    return os.path.join(po_dir, lang_code + ".po")


def create_po(po_dir, package, lang_code):
    """Create a new <lang_code>.po file based on <package>.pot

    Returns the path to the new po file or raise GettextError
    in case something went wrong or the file already exists.
    """

    pot_path = os.path.join(po_dir, package + ".pot")
    po_path = os.path.join(po_dir, lang_code + ".po")

    if os.path.exists(po_path):
        raise GettextError("%r already exists" % po_path)

    if not os.path.exists(pot_path):
        raise GettextError("%r missing" % pot_path)

    try:
        subprocess.check_call(["msginit", "--no-translator",
                               "-i", pot_path, "-o", po_path])
    except subprocess.CalledProcessError as e:
        raise GettextError(e)

    if not os.path.exists(po_path):
        raise GettextError(
            "something went wrong; %r didn't get created" % po_path)

    return po_path


def get_missing(po_dir, package):
    """Returns a list of files which include translatable strings but are
    not listed as translatable.

    or raise GettextError
    """

    missing_path = os.path.join(po_dir, "missing")

    try:
        os.remove(missing_path)
    except OSError:
        pass

    # While intltool prints the result also to stderr it gets mixed with
    # warnings etc. so we have to check the "missing" file
    try:
        with open(os.devnull, 'wb') as devnull:
            subprocess.check_call(
                intltool("update", "--maintain", "--gettext-package", package),
                stderr=devnull, stdout=devnull, cwd=po_dir)
    except subprocess.CalledProcessError as e:
        raise GettextError(e)
    else:
        try:
            with open(missing_path) as h:
                result = h.read()
        except IOError:
            result = ""

    return result.splitlines()


def _get_xgettext_version():
    """Returns a version tuple e.g. (0, 19, 3) or GettextError"""

    try:
        result = subprocess.check_output(["xgettext", "--version"])
    except subprocess.CalledProcessError as e:
        raise GettextError(e)

    try:
        return tuple(map(int, result.splitlines()[0].split()[-1].split(b".")))
    except (IndexError, ValueError) as e:
        raise GettextError(e)


def check_version():
    """Raises GettextError in case intltool and xgettext are missing

    Tries to include a helpful error message..
    """

    if os.name != "nt" and find_executable("intltool-update") is None:
        raise GettextError("intltool-update missing")

    if find_executable("xgettext") is None:
        raise GettextError("xgettext missing")

    if _get_xgettext_version() < (0, 15):
        raise GettextError("xgettext too old, need 0.15+")
