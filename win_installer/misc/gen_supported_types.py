# -*- coding: utf-8 -*-
# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet.formats import init, loaders

if __name__ == "__main__":
    init()

    # these are for showing up in the openwith dialog
    for ext in sorted(loaders.keys()):
        print('WriteRegStr HKLM "${QL_ASSOC_KEY}" '
              '"%s" "${QL_ID}.assoc.ANY"' % ext)
