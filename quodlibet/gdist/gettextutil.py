# Copyright 2015-2017 Christoph Reiter
#                2019 Nick Boultbee
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

import os
import glob
import subprocess
import contextlib
import fnmatch
import tempfile
import shutil
import functools

# pattern -> (language, [keywords])
XGETTEXT_CONFIG = {
    "*.py": ("Python", [
        "", "_", "N_", "C_:1c,2", "NC_:1c,2", "Q_", "pgettext:1c,2",
        "npgettext:1c,2,3", "numeric_phrase:1,2", "dgettext:2",
        "ngettext:1,2", "dngettext:2,3",
    ]),
    "*.appdata.xml": ("", []),
    "*.desktop": ("Desktop", [
        "", "Name", "GenericName", "Comment", "Keywords"]),
}


class GettextError(Exception):
    pass


def _read_potfiles(src_root, potfiles):
    """Returns a list of paths for a POTFILES.in file"""

    paths = []
    with open(potfiles, "r", encoding="utf-8") as h:
        for line in h:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            paths.append(os.path.normpath(os.path.join(src_root, line)))
    return paths


def _write_potfiles(src_root, potfiles, paths):
    with open(potfiles, "w", encoding="utf-8") as h:
        for path in paths:
            path = os.path.relpath(path, src_root)
            h.write(path + "\n")


def _src_root(po_dir):
    return os.path.normpath(os.path.join(po_dir, ".."))


def get_pot_dependencies(po_dir):
    """Returns a list of paths that are used as input for the .pot file"""

    src_root = _src_root(po_dir)
    potfiles_path = os.path.join(po_dir, "POTFILES.in")
    return _read_potfiles(src_root, potfiles_path)


def _create_pot(potfiles_path, src_root, strict):
    potfiles = _read_potfiles(src_root, potfiles_path)

    groups = {}
    for path in potfiles:
        for pattern in XGETTEXT_CONFIG:
            match_part = os.path.basename(path)
            if match_part.endswith(".in"):
                match_part = match_part.rsplit(".", 1)[0]
            if fnmatch.fnmatch(match_part, pattern):
                groups.setdefault(pattern, []).append(path)
                break
        else:
            if strict:
                raise ValueError("Unknown filetype: " + path)

    specs = []
    for pattern, paths in groups.items():
        language, keywords = XGETTEXT_CONFIG[pattern]
        specs.append((language, keywords, paths))
    # no language last, otherwise we get charset errors
    specs.sort(reverse=True)

    fd, out_path = tempfile.mkstemp(".pot")
    try:
        os.close(fd)
        for language, keywords, paths in specs:
            args = []
            if language:
                args.append("--language=" + language)

            for kw in keywords:
                if kw:
                    args.append("--keyword=" + kw)
                else:
                    args.append("-k")

            fd, potfiles_in = tempfile.mkstemp()
            try:
                os.close(fd)
                _write_potfiles(src_root, potfiles_in, paths)

                args = ["xgettext", "--from-code=utf-8", "--add-comments",
                        "--files-from=" + potfiles_in,
                        "--directory=" + src_root,
                        "--output=" + out_path, "--force-po",
                        "--join-existing"] + args

                p = subprocess.Popen(
                    args,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    universal_newlines=True)
                stdout, stderr = p.communicate()
                if p.returncode != 0:
                    raise GettextError(stderr
                                       or ("Got error: %d" % p.returncode))
                if strict and stderr:
                    raise GettextError(stderr)
            finally:
                os.unlink(potfiles_in)
    except Exception:
        os.unlink(out_path)
        raise

    return out_path


@contextlib.contextmanager
def create_pot(po_dir, strict=False):
    """Temporarily creates a .pot file in a temp directory.

    If strict then error out on extraction warnings.
    """

    src_root = _src_root(po_dir)
    potfiles_path = os.path.join(po_dir, "POTFILES.in")
    pot_path = _create_pot(potfiles_path, src_root, strict)
    try:
        yield pot_path
    finally:
        os.unlink(pot_path)


def update_linguas(po_dir):
    """Create a LINGUAS file in po_dir"""

    linguas = os.path.join(po_dir, "LINGUAS")
    with open(linguas, "w", encoding="utf-8") as h:
        for l in list_languages(po_dir):
            h.write(l + "\n")


def list_languages(po_dir):
    """Returns a list of available language codes"""

    po_files = glob.glob(os.path.join(po_dir, "*.po"))
    return sorted([os.path.basename(po[:-3]) for po in po_files])


def compile_po(po_path, target_file):
    """Creates an .mo from a .po"""

    try:
        subprocess.check_output(
            ["msgfmt", "-o", target_file, po_path],
            universal_newlines=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        raise GettextError(e.output)


def po_stats(po_path):
    """Returns a string containing translation statistics"""

    try:
        return subprocess.check_output(
            ["msgfmt", "--statistics", po_path, "-o", os.devnull],
            universal_newlines=True, stderr=subprocess.STDOUT).strip()
    except subprocess.CalledProcessError as e:
        raise GettextError(e.output)


def merge_file(po_dir, file_type, source_file, target_file):
    """Using a template input create a new file including translations"""

    if file_type not in ("xml", "desktop"):
        raise ValueError
    style = "--" + file_type

    linguas = os.path.join(po_dir, "LINGUAS")
    if not os.path.exists(linguas):
        raise GettextError("{!r} doesn't exist".format(linguas))

    try:
        subprocess.check_output(
            ["msgfmt", style, "--template", source_file, "-d", po_dir,
             "-o", target_file],
            universal_newlines=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        raise GettextError(e.output)


def get_po_path(po_dir, lang_code):
    """The default path to the .po file for a given language code"""

    return os.path.join(po_dir, lang_code + ".po")


def update_po(pot_path, po_path, out_path=None):
    """Update .po at po_path based on .pot at po_path.

    If out_path is given will not touch po_path and write to out_path instead.

    Returns the path written to.
    Raises GettextError on error.
    """

    if out_path is None:
        out_path = po_path

    try:
        subprocess.check_output(
            ["msgmerge", "-o", out_path, po_path, pot_path],
            universal_newlines=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        raise GettextError(e.output)


def check_po(po_path, ignore_header=False):
    """Makes sure the .po is well formed

    Raises GettextError if not
    """

    check_arg = "--check" if not ignore_header else "--check-format"
    try:
        subprocess.check_output(
            ["msgfmt", check_arg, "--check-domain", po_path, "-o", os.devnull],
            stderr=subprocess.STDOUT, universal_newlines=True)
    except subprocess.CalledProcessError as e:
        raise GettextError(e.output)


def check_pot(pot_path):
    """Makes sure that the .pot is well formed

    Raises GettextError if not
    """

    # msgfmt doesn't like .pot files, but we can create a dummy .po
    # and test that instead.
    fd, po_path = tempfile.mkstemp(".po")
    os.close(fd)
    os.unlink(po_path)
    create_po(pot_path, po_path)

    try:
        check_po(po_path, ignore_header=True)
    finally:
        os.remove(po_path)


def create_po(pot_path, po_path):
    """Create a new <po_path> file based on <pot_path>

    Returns the path to the new po file or raise GettextError
    in case something went wrong or the file already exists.
    """

    if os.path.exists(po_path):
        raise GettextError("%r already exists" % po_path)

    if not os.path.exists(pot_path):
        raise GettextError("%r missing" % pot_path)

    try:
        subprocess.check_output(
            ["msginit", "--no-translator", "-i", pot_path, "-o", po_path],
            universal_newlines=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        raise GettextError(e.output)

    if not os.path.exists(po_path):
        raise GettextError(
            "something went wrong; %r didn't get created" % po_path)

    update_po(pot_path, po_path)


def get_missing(po_dir):
    """Returns a list of file information for translatable strings
    found in files not listed in POTFILES.in and not skipped in
    POTFILES.skip.
    """

    src_root = _src_root(po_dir)
    potfiles_path = os.path.join(po_dir, "POTFILES.in")
    skip_path = os.path.join(po_dir, "POTFILES.skip")
    potfiles = _read_potfiles(src_root, potfiles_path)
    skipfiles = _read_potfiles(src_root, skip_path)

    # generate a list of paths of files which are not marked translatable
    # and not skipped
    potfiles = [os.path.relpath(p, src_root) for p in potfiles]
    skipfiles = [os.path.relpath(p, src_root) for p in skipfiles]
    not_translatable = []
    for root, dirs, files in os.walk(src_root):
        for dirname in list(dirs):
            dirpath = os.path.relpath(os.path.join(root, dirname), src_root)
            if dirpath in skipfiles:
                dirs.remove(dirname)

        for name in files:
            path = os.path.relpath(os.path.join(root, name), src_root)
            if path not in potfiles and path not in skipfiles:
                not_translatable.append(path)

    # filter out any unknown filetypes
    fd, temp_path = tempfile.mkstemp("POTFILES.in")
    try:
        os.close(fd)
        _write_potfiles(src_root, temp_path, not_translatable)

        pot_path = _create_pot(temp_path, src_root, strict=False)
        try:
            infos = set()
            with open(pot_path, "r", encoding="utf-8") as h:
                for line in h.readlines():
                    if not line.startswith("#:"):
                        continue
                    infos.update(line.split()[1:])
            return sorted(infos)
        finally:
            os.unlink(pot_path)
    finally:
        os.unlink(temp_path)


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


@functools.lru_cache(None)
def check_version():
    """Raises GettextError in case the required gettext programs are missing

    Tries to include a helpful error message..
    """

    required_programs = ["xgettext", "msgmerge", "msgfmt"]
    for prog in required_programs:
        if shutil.which(prog) is None:
            raise GettextError("{} missing".format(prog))

    if _get_xgettext_version() < (0, 19, 8):
        raise GettextError("xgettext too old, need 0.19.8+")
