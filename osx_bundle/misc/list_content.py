#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

import os
import sys
from collections import namedtuple
from xml.dom import minidom

# .py <jhbuild_prefix> <bundle.app>
# takes a jhbuild prefix and an app bundle and lists all the
# files and from which jhbuild package they come from


def main(argv):
    assert len(argv) == 3

    jhbuild = os.path.join(argv[1], "_jhbuild")
    bundle_base = os.path.join(argv[2], "Contents", "Resources")
    info = os.path.join(jhbuild, "info")

    Entry = namedtuple("Entry", ["package", "version", "files"])
    entries = {}

    for key in os.listdir(info):
        path = os.path.join(info, key)
        xmldoc = minidom.parse(path)
        item = xmldoc.getElementsByTagName('entry')[0]
        package = item.attributes['package'].value
        version = item.attributes['version'].value

        entry = Entry(package, version, set())
        entries[key] = entry

    def norm_py(path):
        # reduce all paths to their source variant so we can connect
        # different variants between the installed state and the
        # final one in the bundle (since we compile and delete
        # the sources..)
        if path.endswith((".pyc", ".pyo")):
            return path[:-1]
        return path

    manifests = os.path.join(jhbuild, "manifests")
    for key in os.listdir(manifests):
        path = os.path.join(manifests, key)

        with open(path, "rb") as h:
            for file_ in h.read().splitlines():
                entries[key].files.add(norm_py(file_))

    found = set()
    for root, dirs, files in os.walk(bundle_base):
        for f in files:
            path = os.path.relpath(os.path.join(root, f), bundle_base)
            found.add(norm_py(path))

    for entry in sorted(entries.values(), key=lambda e: e.package):
        here = set([p for p in entry.files if p in found])
        if here:
            print entry.package, entry.version
        found -= here
        for p in sorted(here):
            print "  ", p

    if found:
        print "__UNKNOWN_SOURCE__"
        for p in sorted(found):
            print "  ", p


if __name__ == '__main__':
    main(sys.argv)
