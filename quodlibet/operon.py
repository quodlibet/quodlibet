#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright 2012,2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

"""A simple command line tagger"""

import sys

import quodlibet
from quodlibet.operon import main
from quodlibet import util


if __name__ == "__main__":
    quodlibet.init_cli()
    sys.exit(main(util.argv))
