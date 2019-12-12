# Copyright 2012,2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import stat
import shlex
import shutil

from senf import environ

from quodlibet import _
from quodlibet.util.tags import MACHINE_TAGS, sortkey
from quodlibet.util.dprint import print_, Colorise
from quodlibet import util

from .base import CommandError


def copy_mtime(src, dst):
    """Copy mtime/atime from src to dst. Might raise OSError."""

    stat_src = os.stat(src)
    os.utime(dst, (stat_src[stat.ST_ATIME], stat_src[stat.ST_MTIME]))


def filter_table(rows, nicks, order):
    """Returns a new table with rows filtered and reordered"""

    if nicks == order:
        return rows

    mapping = []
    lower = [h.lower() for h in nicks]
    for o in order:
        try:
            index = lower.index(o.lower())
        except ValueError:
            raise CommandError(
                _("'%(column-id)s' is not a valid column "
                  "name (%(all-column-ids)s).") % {
                    "column-id": o,
                    "all-column-ids": ", ".join(nicks),
                  })
        else:
            mapping.append(index)

    if not mapping:
        return []

    new_rows = []
    for row in rows:
        new_rows.append([row[i] for i in mapping])
    return new_rows


def print_table(rows, headers, nicks, order):
    """Print a fancy table"""

    rows.insert(0, headers)
    rows = filter_table(rows, nicks, order)
    if not rows:
        return

    widths = []
    for c in range(len(rows[0])):
        widths.append(max(map(lambda r: len(r[c]), rows)))

    seperator = " %s " % Colorise.gray("|")
    format_string = seperator.join(["%%-%ds" % w for w in widths])

    header = []
    for i, h in enumerate(rows.pop(0)):
        header.append(h.ljust(widths[i], " "))
    line_width = len("   ".join(header)) + 2
    header = [Colorise.bold(h) for h in header]
    header_line = " " + (" %s " % Colorise.gray("|")).join(header)

    print_(header_line.rstrip())
    print_(Colorise.gray("-" * line_width))

    for row in rows:
        print_(" " + (format_string % tuple(row)).rstrip())


def print_terse_table(rows, nicks, order):
    """Print a terse table"""

    for row in filter_table(rows, nicks, order):
        row = [r.replace("\\", "\\\\") for r in row]
        row = [r.replace(":", r"\:") for r in row]
        print_(":".join(row))


def list_tags(song, machine=False, terse=False):
    """Return a list of key, value pairs"""

    keys = set(song.realkeys())
    if not machine:
        keys.difference_update(MACHINE_TAGS)

    tags = []
    for key in sorted(keys, key=sortkey):
        for value in song.list(key):
            if not terse:
                # QL can't handle multiline values and splits them by \n.
                # Tags with Windows line endings leave a \r, messing up the
                # table layout
                value = value.rstrip("\r")
                # Normalize tab
                value = value.replace("\t", " ")
            tags.append((util.tag(key), value, key))
    return tags


def get_editor_args(fallback_command="nano"):
    """Returns a list starting with a command and optional arguments
    for editing text files.

    List is never empty.
    Can't fail, but the result might not be a valid/existing command.
    """

    if "VISUAL" in environ:
        editor = environ["VISUAL"]
    elif "EDITOR" in environ:
        editor = environ["EDITOR"]
    elif shutil.which("editor"):
        editor = "editor"
    else:
        editor = fallback_command

    # to support VISUAL="geany -i"
    try:
        editor_args = shlex.split(editor)
    except ValueError:
        # well, no idea
        editor_args = [editor]

    if not editor_args:
        editor_args = [fallback_command]

    return editor_args
