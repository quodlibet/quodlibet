# -*- coding: utf-8 -*-
# Copyright 2017 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
from collections import namedtuple
try:
    import configparser
except ImportError:
    import ConfigParser as configparser

import quodlibet
from quodlibet.util import get_module_dir


SetupConfig = namedtuple("SetupConfig", ["ignore", "builtins", "exclude"])


def parse_setup_cfg():
    """Parses the flake8 config from the setup.cfg file in the root dir

    Returns:
        SetupConfig
    """

    base_dir = os.path.dirname(get_module_dir(quodlibet))

    cfg = os.path.join(base_dir, "setup.cfg")
    config = configparser.RawConfigParser()
    config.read(cfg)

    ignore = str(config.get("flake8", "ignore")).split(",")
    builtins = str(config.get("flake8", "builtins")).split(",")
    exclude = str(config.get("flake8", "exclude")).split(",")
    exclude = [
        os.path.join(base_dir, e.replace("/", os.sep)) for e in exclude]

    return SetupConfig(ignore, builtins, exclude)


setup_cfg = parse_setup_cfg()


def iter_py_files(root):
    for base, dirs, files in os.walk(root):
        for file_ in files:
            path = os.path.join(base, file_)
            if os.path.splitext(path)[1] == ".py":
                yield path


def iter_project_py_files():
    root = os.path.dirname(get_module_dir(quodlibet))
    skip = setup_cfg.exclude
    for path in iter_py_files(root):
        if any((path.startswith(s + os.sep) or s == path)
               for s in skip):
            continue
        yield path
