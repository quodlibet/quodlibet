#!/usr/bin/env python

"""A script to remove all translations for languages where Quod Libet doesn't
provide a translation. The passed path should point to $PREFIX/share/locale in
the finished bundle"""

import os
import sys
import shutil


def main(argv):
    target = os.path.abspath(argv[1])
    assert os.path.exists(target)

    for dir_ in os.listdir(target):
        dir_ = os.path.join(target, dir_)
        msgs = os.path.join(dir_, "LC_MESSAGES")
        if not os.path.exists(os.path.join(msgs, "quodlibet.mo")):
            shutil.rmtree(dir_)


if __name__ == "__main__":
    main(sys.argv)
