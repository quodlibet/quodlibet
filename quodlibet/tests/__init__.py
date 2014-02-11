# -*- coding: utf-8 -*-
import fnmatch
import inspect
from math import log
import os
import sys
import unittest
import tempfile
import shutil
from quodlibet.util.dprint import Colorise, print_
from quodlibet.util.path import fsnative

from unittest import TestCase as OrigTestCase


class TestCase(OrigTestCase):

    # silence deprec warnings about useless renames
    failUnless = OrigTestCase.assertTrue
    failIf = OrigTestCase.assertFalse
    failUnlessEqual = OrigTestCase.assertEqual
    failUnlessRaises = OrigTestCase.assertRaises
    failUnlessAlmostEqual = OrigTestCase.assertAlmostEqual
    failIfEqual = OrigTestCase.assertNotEqual
    failIfAlmostEqual = OrigTestCase.assertNotAlmostEqual


class AbstractTestCase(TestCase):
    """If a class is a direct subclass of this one it gets skipped"""


skipped = []
skipped_reason = {}


def skip(cls, reason=None):
    assert inspect.isclass(cls)

    skipped.append(cls)
    if reason:
        skipped_reason[cls] = reason

    return cls


def skipUnless(value, reason=None):
    def dec(cls):
        if value:
            return cls
        return skip(cls, reason=reason)
    return dec


def skipIf(value, *args, **kwargs):
    return skipUnless(not value, *args, **kwargs)


DATA_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")
_TEMP_DIR = None


def _wrap_tempfile(func):
    def wrap(*args, **kwargs):
        if kwargs.get("dir") is None:
            kwargs["dir"] = _TEMP_DIR
        return func(*args, **kwargs)
    return wrap


NamedTemporaryFile = _wrap_tempfile(tempfile.NamedTemporaryFile)


def mkdtemp(*args, **kwargs):
    return fsnative(_wrap_tempfile(tempfile.mkdtemp)(*args, **kwargs))


def mkstemp(*args, **kwargs):
    fd, filename = _wrap_tempfile(tempfile.mkstemp)(*args, **kwargs)
    return (fd, fsnative(filename))


class Result(unittest.TestResult):
    TOTAL_WIDTH = 80
    TEST_RESULTS_WIDTH = 50
    TEST_NAME_WIDTH = TOTAL_WIDTH - TEST_RESULTS_WIDTH - 3
    MAJOR_SEPARATOR = '=' * TOTAL_WIDTH
    MINOR_SEPARATOR = '-' * TOTAL_WIDTH

    CHAR_SUCCESS, CHAR_ERROR, CHAR_FAILURE = '+', 'E', 'F'

    def __init__(self, test_name, num_tests, out=sys.stdout):
        super(Result, self).__init__()
        self.out = out
        if hasattr(out, "flush"):
            out.flush()
        pref = '%s (%d): ' % (Colorise.bold(test_name), num_tests)
        line = pref + " " * (self.TEST_NAME_WIDTH - len(test_name)
                             - 6 - int(num_tests and log(num_tests, 10) or 0))
        print_(line, end="")

    def addSuccess(self, test):
        unittest.TestResult.addSuccess(self, test)
        print_(Colorise.green(self.CHAR_SUCCESS), end="")

    def addError(self, test, err):
        unittest.TestResult.addError(self, test, err)
        print_(Colorise.red(self.CHAR_ERROR), end="")

    def addFailure(self, test, err):
        unittest.TestResult.addFailure(self, test, err)
        print_(Colorise.red(self.CHAR_FAILURE), end="")

    def printErrors(self):
        succ = self.testsRun - (len(self.errors) + len(self.failures))
        v = Colorise.bold("%3d" % succ)
        cv = Colorise.green(v) if succ == self.testsRun else Colorise.red(v)
        count = self.TEST_RESULTS_WIDTH - self.testsRun
        print_((" " * count) + cv)
        self.printErrorList('ERROR', self.errors)
        self.printErrorList('FAIL', self.failures)

    def printErrorList(self, flavour, errors):
        for test, err in errors:
            print_(self.MAJOR_SEPARATOR)
            print_(Colorise.red("%s: %s" % (flavour, str(test))))
            print_(self.MINOR_SEPARATOR)
            # tracebacks can contain encoded paths, not sure
            # what the right fix is here, so use repr
            for line in err.splitlines():
                print_(repr(line)[1:-1])


class Runner(object):

    def run(self, test):
        suite = unittest.makeSuite(test)
        result = Result(test.__name__, len(suite._tests))
        suite(result)
        result.printErrors()
        return len(result.failures), len(result.errors)


def unit(run=[], filter_func=None, main=False, subdirs=None, strict=False,
         stop_first=False):

    global _TEMP_DIR

    # Ideally nothing should touch the FS on import, but we do atm..
    # Get rid of all modules so QUODLIBET_USERDIR gets used everywhere.
    for key in sys.modules.keys():
        if key.startswith('quodlibet'):
            del(sys.modules[key])

    # create a user dir in /tmp
    _TEMP_DIR = tempfile.mkdtemp(prefix="QL-TEST-")
    user_dir = tempfile.mkdtemp(prefix="QL-USER-", dir=_TEMP_DIR)
    os.environ['QUODLIBET_USERDIR'] = user_dir

    path = os.path.dirname(__file__)
    if subdirs is None:
        subdirs = []

    import quodlibet
    quodlibet._dbus_init()
    quodlibet._gtk_init()
    quodlibet._python_init()

    # make glib warnings fatal
    if strict:
        from gi.repository import GLib
        GLib.log_set_always_fatal(
            GLib.LogLevelFlags.LEVEL_CRITICAL |
            GLib.LogLevelFlags.LEVEL_ERROR |
            GLib.LogLevelFlags.LEVEL_WARNING)

    suites = []
    abstract = []

    def discover_tests(mod):
        for k in vars(mod):
            value = getattr(mod, k)

            if value not in (TestCase, AbstractTestCase) and \
                    inspect.isclass(value) and issubclass(value, TestCase):
                if AbstractTestCase in value.__bases__:
                    abstract.append(value)
                elif value not in skipped:
                    suites.append(value)

    if main:
        for name in os.listdir(path):
            if fnmatch.fnmatch(name, "test_*.py"):
                mod = __import__(".".join([__name__, name[:-3]]), {}, {}, [])
                discover_tests(getattr(mod, name[:-3]))

    for subdir in subdirs:
        sub_path = os.path.join(path, subdir)
        for name in os.listdir(sub_path):
            if fnmatch.fnmatch(name, "test_*.py"):
                mod = __import__(
                    ".".join([__name__, subdir, name[:-3]]), {}, {}, [])
                discover_tests(getattr(getattr(mod, subdir), name[:-3]))

    # check if each abstract class is actually used (also by skipped ones)
    unused_abstract = set(abstract)
    for case in suites:
        unused_abstract -= set(case.__mro__)
    for case in skipped:
        unused_abstract -= set(case.__mro__)
    if unused_abstract:
        raise Exception("The following abstract test cases have no "
                        "implementation: %r" % list(unused_abstract))

    for case in skipped:
        name = "%s.%s" % (case.__module__, case.__name__)
        reason = skipped_reason.get(case, "??")
        print_w("Skipped test: %s (%s)" % (name, reason))

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
            df, de = runner.run(test)
            if stop_first and (df or de):
                break
            failures += df
            errors += de
            teardown_test(test)
            quodlibet.config.quit()

    try:
        shutil.rmtree(_TEMP_DIR)
    except EnvironmentError:
        pass

    return failures, errors
