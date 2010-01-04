#! /usr/bin/env python
#
# imagen aims to be an all purpose image tagging library
# Copyright 2007 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

version = (0, 0, -1)
version_string = ".".join(map(str, version))

def utf8(string):
    if isinstance(string, unicode):
        return string.encode("utf-8")
    else:
        return string.decode("utf-8", "replace").encode("utf-8")

def latin1(string):
    if isinstance(string, unicode):
        return string.encode("iso-8859-1")
    else:
        return string.decode("utf-8", "replace").encode("iso-8859-1")
