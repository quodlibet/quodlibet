# -*- coding: utf-8 -*-
# Copyright 2018 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys

import pytest


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    """A pytest hook which takes over sys.excepthook and raises any uncaught
    exception (with PyGObject this happesn often when we get called from C,
    like any signal handler, vfuncs tc)
    """

    assert sys.excepthook is sys.__excepthook__

    exceptions = []

    def on_hook(type_, value, tback):
        exceptions.append((type_, value, tback))

    sys.excepthook = on_hook
    try:
        yield
    finally:
        sys.excepthook = sys.__excepthook__
        if exceptions:
            tp, value, tb = exceptions[0]
            raise tp(value).with_traceback(tb)
