# Copyright 2018 Christoph Reiter
#           2022 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys

import pytest
from _pytest.config import Config
from _pytest.reports import TestReport
from quodlibet.util.logging import _logs

LOG_JOINER = "\n\t"


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    """A pytest hook which takes over sys.excepthook and raises any uncaught
    exception (with PyGObject this happens often when we get called from C,
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


@pytest.hookimpl(hookwrapper=True)
def pytest_report_teststatus(report: TestReport, config: Config):
    """Spits out relevant logs only if a test fails."""
    yield
    if report.failed:
        msg = (f"\nERROR: failed {report.nodeid}:{LOG_JOINER}"
               + LOG_JOINER.join(_logs.get_content()))
        print(msg)
        return report.outcome, ".", msg
    # Each test should clear the logs. This won't work well if parallelised
    _logs.clear()
    return None
