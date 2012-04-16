#!/usr/bin/env python

# ./flakes.py <path>

# pyflakes has no way to define additions to __builtin__,
# so add them manually
NAMES = ["_", "print_d", "print_w", "print_e", "print_", "Q_", "ngettext"]

import __builtin__
for name in NAMES:
    setattr(__builtin__, name, getattr(__builtin__, name, None))
del __builtin__
del NAMES

import sys
argv = sys.argv
del sys

from pyflakes.scripts.pyflakes import main
main(argv)
