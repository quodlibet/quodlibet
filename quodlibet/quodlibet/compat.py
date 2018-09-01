# -*- coding: utf-8 -*-
# Copyright (C) 2013  Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

cmp = lambda a, b: (a > b) - (a < b)

text_type = str

iteritems = lambda d: iter(d.items())
itervalues = lambda d: iter(d.values())
iterkeys = lambda d: iter(d.keys())
listitems = lambda d: list(d.items())
listkeys = lambda d: list(d.keys())
listvalues = lambda d: list(d.values())

listfilter = lambda *x: list(filter(*x))
