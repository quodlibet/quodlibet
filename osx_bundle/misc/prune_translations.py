#!/usr/bin/env python

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
