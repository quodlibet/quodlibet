from __future__ import division

import glob
import os
import sys
import unittest
import tempfile
import shutil

from unittest import TestCase
suites = []
add = suites.append

class Result(unittest.TestResult):

    separator1 = '=' * 70
    separator2 = '-' * 70

    def addSuccess(self, test):
        unittest.TestResult.addSuccess(self, test)
        sys.stdout.write('.')

    def addError(self, test, err):
        unittest.TestResult.addError(self, test, err)
        sys.stdout.write('E')

    def addFailure(self, test, err):
        unittest.TestResult.addFailure(self, test, err)
        sys.stdout.write('F')

    def printErrors(self):
        succ = self.testsRun - (len(self.errors) + len(self.failures))
        v = "%3d" % succ
        count = 50 - self.testsRun
        sys.stdout.write((" " * count) + v + "\n")
        self.printErrorList('ERROR', self.errors)
        self.printErrorList('FAIL', self.failures)

    def printErrorList(self, flavour, errors):
        for test, err in errors:
            sys.stdout.write(self.separator1 + "\n")
            sys.stdout.write("%s: %s\n" % (flavour, str(test)))
            sys.stdout.write(self.separator2 + "\n")
            sys.stdout.write("%s\n" % err)

class Runner(object):
    def run(self, test):
        suite = unittest.makeSuite(test)
        pref = '%s (%d): ' % (test.__name__, len(suite._tests))
        print pref + " " * (25 - len(pref)),
        sys.stdout.flush()
        result = Result()
        suite(result)
        result.printErrors()
        return bool(result.failures + result.errors)

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
    failures = False
    use_suites = filter(filter_func, suites)
    for test in sorted(use_suites, key=repr):
        if (not run
            or test.__name__ in run
            or test.__module__[11:] in run):
            setup_test(test)
            failures |= runner.run(test)
            teardown_test(test)
            quodlibet.config.quit()

    try: shutil.rmtree(user_dir)
    except EnvironmentError: pass

    return failures
