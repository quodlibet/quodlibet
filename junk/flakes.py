#!/usr/bin/env python

# ./flakes.py [--all] <path>
# ./flakes.py ../quodlibet

# pyflakes has no way to define additions to __builtin__,
# so add them manually
NAMES = ["_", "print_d", "print_w", "print_e", "print_", "Q_", "ngettext"]

import __builtin__
for name in NAMES:
    setattr(__builtin__, name, getattr(__builtin__, name, None))
del __builtin__
del NAMES

class NullStream:
    BL = ["imported but unused", "redefinition of unused",
          "unable to detect undefined names", "redefinition of function"]
    def __init__(self, out):
        self.stdout = out

    def write(self, text):
        for p in self.BL:
            if p in text:
                return
        if not text.strip():
            return
        print>>self.stdout, text

import sys
argv = sys.argv
if "--all" in argv:
    argv.remove("--all")
else:
    sys.stdout = NullStream(sys.stdout)
del sys

from pyflakes.scripts.pyflakes import main
main(argv)
