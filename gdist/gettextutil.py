# Copyright 2015-2017 Christoph Reiter
#             2019-21 Nick Boultbee
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
import subprocess
import contextlib
import fnmatch
import tempfile
import shutil
import functools
import warnings

from pathlib import Path
from typing import List, Optional, Tuple, Iterable, Dict

from quodlibet import print_w

QL_SRC_DIR = "quodlibet"

XGETTEXT_CONFIG: Dict[str, Tuple[str, List[str]]] = {
    "*.py": ("Python", [
        "", "_", "N_", "C_:1c,2", "NC_:1c,2", "Q_", "pgettext:1c,2",
        "npgettext:1c,2,3", "numeric_phrase:1,2", "dgettext:2",
        "ngettext:1,2", "dngettext:2,3",
    ]),
    "*.appdata.xml": ("", []),
    "*.desktop": ("Desktop", [
        "", "Name", "GenericName", "Comment", "Keywords"]),
}
"""Dict of pattern -> (language, [keywords])"""


class GettextError(Exception):
    pass


class GettextWarning(Warning):
    pass


def _read_potfiles(src_root: Path, potfiles: Path) -> List[Path]:
    """Returns a list of paths for a POTFILES.in file"""

    paths = []
    with open(potfiles, "r", encoding="utf-8") as h:
        for line in h:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            paths.append((src_root / line).resolve())
    return paths


def _write_potfiles(src_root: Path, potfiles: Path, paths: Iterable[Path]):
    with open(potfiles, "w", encoding="utf-8") as h:
        for path in paths:
            path = src_root / path
            h.write(str(path) + "\n")


def _src_root(po_dir: Path) -> Path:
    assert isinstance(po_dir, Path)
    return po_dir.parent.resolve()


def get_pot_dependencies(po_dir: Path) -> List[Path]:
    """Returns a list of paths that are used as input for the .pot file"""

    src_root = _src_root(po_dir)
    potfiles_path = po_dir / "POTFILES.in"
    return _read_potfiles(src_root, potfiles_path)


def _get_pattern(path: Path) -> Optional[str]:
    for pattern in XGETTEXT_CONFIG:
        match_part = path.name
        if match_part.endswith(".in"):
            match_part = match_part.rsplit(".", 1)[0]
        if fnmatch.fnmatch(match_part, pattern):
            return pattern
    return None


def _create_pot(potfiles_path: Path, src_root: Path) -> Path:
    """Create a POT file for the specified POs and source code

        :returns: the output path
    """
    potfiles = _read_potfiles(src_root, potfiles_path)

    groups = {}
    for path in potfiles:
        pattern = _get_pattern(path)
        if pattern is not None:
            groups.setdefault(pattern, []).append(path)
        else:
            raise ValueError(f"Unknown filetype: {path!s}")

    specs = []
    for pattern, paths in groups.items():
        language, keywords = XGETTEXT_CONFIG[pattern]
        specs.append((language, keywords, paths))
    # no language last, otherwise we get charset errors
    specs.sort(reverse=True)

    fd, out_path = tempfile.mkstemp(".pot")
    out_path = Path(out_path)
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
            potfiles_in = Path(potfiles_in)
            try:
                os.close(fd)
                _write_potfiles(src_root, potfiles_in, paths)

                args = ["xgettext", "--from-code=utf-8", "--add-comments",
                        "--files-from=" + str(potfiles_in),
                        "--directory=" + str(src_root / "quodlibet"),
                        "--output=" + str(out_path),
                        "--force-po",
                        "--join-existing"] + args

                p = subprocess.Popen(
                    args,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    universal_newlines=True)
                stdout, stderr = p.communicate()
                if p.returncode != 0:
                    path_strs = ", ".join(str(p) for p in paths)
                    msg = f"Error running `{' '.join(args)}`:\nPaths: {path_strs}...\n"
                    msg += stderr or ("Got error: %d" % p.returncode)
                    raise GettextError(msg)
                if stderr:
                    warnings.warn(stderr, GettextWarning)
            finally:
                potfiles_in.unlink()
    except Exception:
        out_path.unlink()
        raise

    return out_path


@contextlib.contextmanager
def create_pot(po_path: Path):
    """Temporarily creates a .pot file in a temp directory."""
    src_root = _src_root(po_path)
    potfiles_path = po_path / "POTFILES.in"
    pot_path = _create_pot(potfiles_path, src_root)
    try:
        yield pot_path
    finally:
        os.unlink(pot_path)


def update_linguas(po_path: Path) -> None:
    """Create a LINGUAS file in po_dir"""

    linguas = po_path / "LINGUAS"
    with open(linguas, "w", encoding="utf-8") as h:
        for l in list_languages(po_path):
            h.write(l + "\n")


def list_languages(po_path: Path) -> List[str]:
    """Returns a list of available language codes"""

    po_files = po_path.glob("*.po")
    return sorted([os.path.basename(str(po)[:-3]) for po in po_files])


def compile_po(po_path: Path, target_file: Path):
    """Creates an .mo from a .po"""

    try:
        subprocess.check_output(
            ["msgfmt", "-o", str(target_file), str(po_path)],
            universal_newlines=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        raise GettextError(e.output)


def po_stats(po_path: Path):
    """Returns a string containing translation statistics"""

    try:
        return subprocess.check_output(
            ["msgfmt", "--statistics", str(po_path), "-o", os.devnull],
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


def get_po_path(po_path: Path, lang_code: str) -> Path:
    """The default path to the .po file for a given language code"""

    return po_path / (lang_code + ".po")


def update_po(pot_path: Path, po_path: Path, out_path: Optional[Path] = None) -> None:
    """Update .po at po_path based on .pot at po_path.

    If out_path is given will not touch po_path and write to out_path instead.

    Raises GettextError on error.
    """

    if out_path is None:
        out_path = po_path

    try:
        subprocess.check_output(
            ["msgmerge", "-o", str(out_path), str(po_path), str(pot_path)],
            universal_newlines=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        raise GettextError(e.output)


def check_po(po_path: Path, ignore_header=False):
    """Makes sure the .po is well formed

    Raises GettextError if not
    """

    check_arg = "--check" if not ignore_header else "--check-format"
    try:
        subprocess.check_output(
            ["msgfmt", check_arg, "--check-domain", str(po_path), "-o", os.devnull],
            stderr=subprocess.STDOUT, universal_newlines=True)
    except subprocess.CalledProcessError as e:
        raise GettextError(e.output)


def check_pot(pot_path: Path) -> None:
    """Makes sure that the .pot is well formed

    Raises GettextError if not
    """

    # msgfmt doesn't like .pot files, but we can create a dummy .po
    # and test that instead.
    fd, po_path = tempfile.mkstemp(".po")
    po_path = Path(po_path)
    os.close(fd)
    po_path.unlink()
    create_po(pot_path, po_path)

    try:
        check_po(po_path, ignore_header=True)
    finally:
        os.remove(po_path)


def create_po(pot_path: Path, po_path: Path) -> None:
    """Create a new <po_path> file based on <pot_path>

    :raises GettextError: in case something went wrong or the file already exists.
    """

    if po_path.exists():
        raise GettextError(f"{po_path!s} already exists")

    if not pot_path.exists():
        raise GettextError(f"{pot_path!s} missing")

    try:
        subprocess.check_output(
            ["msginit", "--no-translator", "-i", str(pot_path), "-o", str(po_path)],
            universal_newlines=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        raise GettextError(e.output)

    if not po_path.exists():
        raise GettextError(f"something went wrong; {po_path!s} didn't get created")

    update_po(pot_path, po_path)


def get_missing(po_dir: Path) -> Iterable[str]:
    """Gets missing strings

       :returns: a list of file information for translatable strings
                 found in files not listed in POTFILES.in
                 and not skipped in POTFILES.skip.
    """

    src_root = _src_root(po_dir)
    potfiles_path = po_dir / "POTFILES.in"
    skip_path = po_dir / "POTFILES.skip"

    # Generate a set of paths of files which are not marked translatable
    # and not skipped
    pot_files = {p.relative_to(src_root)
                 for p in _read_potfiles(src_root, potfiles_path)}
    skip_files = {p.relative_to(src_root)
                  for p in _read_potfiles(src_root, skip_path)}
    not_translatable = set()
    for root, dirs, files in os.walk(src_root):
        root = Path(root)
        for dirname in dirs:
            dirpath = (root / dirname).relative_to(src_root)
            if (dirpath in skip_files
                    or dirname.startswith(".") or dirpath in skip_files):
                dirs.remove(dirname)

        for name in files:
            path = (root / name).relative_to(src_root)
            if path not in pot_files and path not in skip_files:
                not_translatable.add(path)

    # Filter out any unknown filetypes
    not_translatable = [p for p in not_translatable if _get_pattern(p) is not None]

    # Filter out any files not containing translations
    fd, temp_path = tempfile.mkstemp("POTFILES.in")
    temp_path = Path(temp_path)
    try:
        os.close(fd)
        _write_potfiles(src_root, temp_path, not_translatable)

        pot_path = _create_pot(temp_path, src_root)
        try:
            infos = set()
            with open(pot_path, "r", encoding="utf-8") as h:
                for line in h.readlines():
                    if not line.startswith("#:"):
                        continue
                    infos.update(line.split()[1:])
            return sorted(infos)
        finally:
            pot_path.unlink()
    finally:
        temp_path.unlink()


def _get_xgettext_version() -> Tuple:
    """:returns: a version tuple e.g. (0, 19, 3) or GettextError"""

    try:
        result = subprocess.check_output(["xgettext", "--version"])
    except subprocess.CalledProcessError as e:
        raise GettextError(e)

    try:
        return tuple(map(int, result.splitlines()[0].split()[-1].split(b".")))
    except (IndexError, ValueError) as e:
        raise GettextError(e)


@functools.lru_cache(None)
def check_version() -> None:
    """Check Gettext version.
    :raises GettextError: (with message) if required gettext programs are missing

    """

    required_programs = ["xgettext", "msgmerge", "msgfmt"]
    for prog in required_programs:
        if shutil.which(prog) is None:
            raise GettextError("{} missing".format(prog))

    if _get_xgettext_version() < (0, 19, 8):
        raise GettextError("xgettext too old, need 0.19.8+")
