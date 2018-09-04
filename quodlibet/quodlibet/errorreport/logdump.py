# -*- coding: utf-8 -*-
# Copyright 2017 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import sys
import platform
import time

import mutagen

import quodlibet
from quodlibet.util import logging
from quodlibet.util.path import mkdir
from quodlibet.util.dprint import print_exc, format_exception


def format_dump_header(exc_info):
    """Returns system information and the traceback

    Args:
        exc_info (tuple): sys.exc_info() result tuple
    Returns:
        str
    """

    lines = [
        u"=== SYSTEM INFORMATION:"
        u"",
        u"Quod Libet %s" % quodlibet.get_build_description(),
        u"Mutagen %s" % mutagen.version_string,
        u"Python %s %s" % (sys.version, sys.platform),
        u"Platform %s" % platform.platform(),
        u"=== STACK TRACE",
        u"",
    ]

    lines.extend(format_exception(*exc_info))
    lines.append(u"")
    return os.linesep.join(lines)


def format_dump_log(limit=75):
    """Returns recent log entries.

    Args:
        limit (int): number of log entries to return
    Returns:
        str
    """

    dump = [u"=== LOG:"]
    dump.extend(logging.get_content(limit=limit))
    return os.linesep.join(dump)


def dump_to_disk(dump_dir, exc_info):
    """Writes a new error log file into 'dump_dir'

    Args:
        dump_dir (path-like)
        exc_info (tuple): sys.exc_info() result tuple
    """

    try:
        mkdir(dump_dir)
    except EnvironmentError:
        print_exc()
        return

    time_ = time.localtime()
    dump_path = os.path.join(
        dump_dir, time.strftime("Dump_%Y%m%d_%H%M%S.txt", time_))

    header = format_dump_header(exc_info).encode("utf-8")
    log = format_dump_log().encode("utf-8")

    try:
        with open(dump_path, "wb") as dump:
            dump.write(header)
            dump.write(log)
    except EnvironmentError:
        print_exc()
