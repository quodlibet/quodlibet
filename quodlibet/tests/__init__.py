# -*- coding: utf-8 -*-
import glob
from math import log
import os
import sys
import unittest
import tempfile
import shutil
from quodlibet.util.dprint import Colorise

from unittest import TestCase
suites = []
add = suites.append


class Result(unittest.TestResult):
    TOTAL_WIDTH = 90
    TEST_RESULTS_WIDTH = 50
    TEST_NAME_WIDTH = TOTAL_WIDTH - TEST_RESULTS_WIDTH - 3
    MAJOR_SEPARATOR = '=' * TOTAL_WIDTH
    MINOR_SEPARATOR = '-' * TOTAL_WIDTH
    USE_COLORS = True

    def _markup(self, call, text):
        try:
            return call(text) if self.use_colors or False else text
        except AttributeError:
            return text

    def bold(self, text):
        return self._markup(Colorise.bold, text)

    def red(self, text):
        return self._markup(Colorise.red, text)

    def green(self, text):
        return self._markup(Colorise.green, text)

    CHAR_SUCCESS, CHAR_ERROR, CHAR_FAILURE = '+', 'E', 'F'

    def __init__(self, test_name, num_tests, out=sys.stdout):
        super(Result, self).__init__()
        self.out = out
        self.use_colors = (self.USE_COLORS and self.out.isatty()
                           and os.name != 'nt')
        if hasattr(out, "flush"):
            out.flush()
        pref = '%s (%d): ' % (self.bold(test_name), num_tests)
        line = pref + " " * (self.TEST_NAME_WIDTH - len(test_name)
                             - 6 - int(num_tests and log(num_tests, 10) or 0))
        out.write(line)

    def addSuccess(self, test):
        unittest.TestResult.addSuccess(self, test)
        self.out.write(self.green(self.CHAR_SUCCESS))

    def addError(self, test, err):
        unittest.TestResult.addError(self, test, err)
        self.out.write(self.red(self.CHAR_ERROR))

    def addFailure(self, test, err):
        unittest.TestResult.addFailure(self, test, err)
        self.out.write(self.red(self.CHAR_FAILURE))

    def printErrors(self):
        succ = self.testsRun - (len(self.errors) + len(self.failures))
        v = self.bold("%3d" % succ)
        cv = self.green(v) if succ == self.testsRun else self.red(v)
        count = self.TEST_RESULTS_WIDTH - self.testsRun
        self.out.write((" " * count) + cv + "\n")
        self.printErrorList('ERROR', self.errors)
        self.printErrorList('FAIL', self.failures)

    def printErrorList(self, flavour, errors):
        for test, err in errors:
            self.out.write(self.MAJOR_SEPARATOR + "\n")
            self.out.write(self.red("%s: %s\n" % (flavour, str(test))))
            self.out.write(self.MINOR_SEPARATOR + "\n")
            self.out.write("%s\n" % err)

class Runner(object):

    def run(self, test):
        suite = unittest.makeSuite(test)
        result = Result(test.__name__, len(suite._tests))
        suite(result)
        result.printErrors()
        return len(result.failures), len(result.errors)

def unit(run=[], filter_func=None, subdir=None):
    path = os.path.dirname(__file__)
    if subdir is not None:
        path = os.path.join(path, subdir)

    import quodlibet
    quodlibet._dbus_init()

    for name in glob.glob(os.path.join(path, "test_*.py")):
        parts = filter(None, [__name__, subdir, os.path.basename(name)[:-3]])
        __import__(".".join(parts), {}, {}, [])

    # create a user dir in /tmp
    user_dir = tempfile.mkdtemp(prefix="QL-TEST-")
    os.environ['QUODLIBET_USERDIR'] = user_dir
    import quodlibet.const
    reload(quodlibet.const)

    import quodlibet.config

    # emulate python2.7 behavior
    def setup_test(test):
        if hasattr(TestCase, "setUpClass"):
            return
        if hasattr(test, "setUpClass"):
            test.setUpClass()

    def teardown_test(test):
        if hasattr(TestCase, "setUpClass"):
            return
        if hasattr(test, "tearDownClass"):
            test.tearDownClass()

    runner = Runner()
    failures = errors = 0
    use_suites = filter(filter_func, suites)
    for test in sorted(use_suites, key=repr):
        if (not run
            or test.__name__ in run
            or test.__module__[11:] in run):
            setup_test(test)
            df,de = runner.run(test)
            failures += df
            errors += de
            teardown_test(test)
            quodlibet.config.quit()

    try:
        shutil.rmtree(user_dir)
    except EnvironmentError:
        pass

    return failures, errors
