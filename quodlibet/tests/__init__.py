# -*- coding: utf-8 -*-
import fnmatch
import inspect
from math import log
import os
import sys
import unittest
import tempfile
import shutil
import atexit
import subprocess
from quodlibet.compat import PY3
from quodlibet.util.dprint import Colorise, print_
from quodlibet.util.path import fsnative, is_fsnative, xdg_get_cache_home
from quodlibet.util.misc import environ

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
skipped_warn = set()


def skip(cls, reason=None, warn=True):
    assert inspect.isclass(cls)

    skipped.append(cls)
    if reason:
        skipped_reason[cls] = reason
    if warn:
        skipped_warn.add(cls)

    cls = unittest.skip(cls)
    return cls


def skipUnless(value, *args, **kwargs):
    def dec(cls):
        assert inspect.isclass(cls)

        if value:
            return cls
        return skip(cls, *args, **kwargs)
    return dec


def skipIf(value, *args, **kwargs):
    return skipUnless(not value, *args, **kwargs)


DATA_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")
if os.name == "nt":
    DATA_DIR = DATA_DIR.decode("ascii")
assert is_fsnative(DATA_DIR)
_TEMP_DIR = None


def _wrap_tempfile(func):
    def wrap(*args, **kwargs):
        if kwargs.get("dir") is None and _TEMP_DIR is not None:
            assert is_fsnative(_TEMP_DIR)
            kwargs["dir"] = _TEMP_DIR
        return func(*args, **kwargs)
    return wrap


NamedTemporaryFile = _wrap_tempfile(tempfile.NamedTemporaryFile)


def mkdtemp(*args, **kwargs):
    path = _wrap_tempfile(tempfile.mkdtemp)(*args, **kwargs)
    assert is_fsnative(path)
    return path


def mkstemp(*args, **kwargs):
    fd, filename = _wrap_tempfile(tempfile.mkstemp)(*args, **kwargs)
    assert is_fsnative(filename)
    return (fd, filename)


def init_fake_app():
    from quodlibet import app

    from quodlibet import browsers
    from quodlibet.player.nullbe import NullPlayer
    from quodlibet.library.libraries import SongFileLibrary
    from quodlibet.library.librarians import SongLibrarian
    from quodlibet.qltk.quodlibetwindow import QuodLibetWindow, PlayerOptions
    from quodlibet.util.cover import CoverManager

    browsers.init()
    app.name = "Quod Libet"
    app.id = "quodlibet"
    app.player = NullPlayer()
    app.library = SongFileLibrary()
    app.library.librarian = SongLibrarian()
    app.cover_manager = CoverManager()
    app.window = QuodLibetWindow(app.library, app.player, headless=True)
    app.player_options = PlayerOptions(app.window)


def destroy_fake_app():
    from quodlibet import app

    app.window.destroy()
    app.library.destroy()
    app.library.librarian.destroy()
    app.player.destroy()

    app.window = app.library = app.player = app.name = app.id = None
    app.cover_manager = None


class Result(unittest.TestResult):
    TOTAL_WIDTH = 80
    TEST_RESULTS_WIDTH = 50
    TEST_NAME_WIDTH = TOTAL_WIDTH - TEST_RESULTS_WIDTH - 3
    MAJOR_SEPARATOR = '=' * TOTAL_WIDTH
    MINOR_SEPARATOR = '-' * TOTAL_WIDTH

    CHAR_SUCCESS, CHAR_ERROR, CHAR_FAILURE = '+', 'E', 'F'

    def __init__(self, test_name, num_tests, out=sys.stdout, failfast=False):
        super(Result, self).__init__()
        self.out = out
        self.failfast = failfast
        if hasattr(out, "flush"):
            out.flush()
        pref = '%s (%d): ' % (Colorise.bold(test_name), num_tests)
        line = pref + " " * (self.TEST_NAME_WIDTH - len(test_name)
                             - 7 - int(num_tests and log(num_tests, 10) or 0))
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

    def run(self, test, failfast=False):
        suite = unittest.makeSuite(test)
        result = Result(test.__name__, len(suite._tests), failfast=failfast)
        suite(result)
        result.printErrors()
        return len(result.failures), len(result.errors), len(suite._tests)


_BUS_INFO = None


def init_test_environ():
    """This needs to be called before any test can be run.

    Before exiting the process call exit_test_environ() to clean up
    any resources created.
    """

    global _TEMP_DIR, _BUS_INFO

    # create a user dir in /tmp and set env vars
    _TEMP_DIR = tempfile.mkdtemp(prefix=fsnative(u"QL-TEST-"))

    # needed for dbus/dconf
    runtime_dir = tempfile.mkdtemp(prefix=fsnative(u"RUNTIME-"), dir=_TEMP_DIR)
    os.chmod(runtime_dir, 0o700)
    environ["XDG_RUNTIME_DIR"] = runtime_dir

    # force the old cache dir so that GStreamer can re-use the GstRegistry
    # cache file
    environ["XDG_CACHE_HOME"] = xdg_get_cache_home()

    # set HOME and remove all XDG vars that default to it if not set
    home_dir = tempfile.mkdtemp(prefix=fsnative(u"HOME-"), dir=_TEMP_DIR)
    environ["HOME"] = home_dir

    # set to new default
    environ.pop("XDG_DATA_HOME", None)

    _BUS_INFO = None
    if os.name != "nt" and "DBUS_SESSION_BUS_ADDRESS" in environ:
        try:
            out = subprocess.check_output(["dbus-launch"])
        except (subprocess.CalledProcessError, OSError):
            pass
        else:
            if PY3:
                out = out.decode("ascii")
            _BUS_INFO = dict([l.split("=", 1) for l in out.splitlines()])
            environ.update(_BUS_INFO)

    # Ideally nothing should touch the FS on import, but we do atm..
    # Get rid of all modules so QUODLIBET_USERDIR gets used everywhere.
    for key in list(sys.modules.keys()):
        if key.startswith('quodlibet'):
            del(sys.modules[key])

    import quodlibet
    quodlibet.init(no_translations=True, no_excepthook=True)
    quodlibet.app.name = "QL Tests"


def exit_test_environ():
    """Call after init_test_environ() and all tests are finished"""

    global _TEMP_DIR, _BUS_INFO

    try:
        shutil.rmtree(_TEMP_DIR)
    except EnvironmentError:
        pass

    if _BUS_INFO:
        try:
            subprocess.check_call(
                ["kill", "-9", _BUS_INFO["DBUS_SESSION_BUS_PID"]])
        except (subprocess.CalledProcessError, OSError):
            pass


# we have to do this on import so the tests work with other test runners
# like py.test which don't know about out setup code and just import
init_test_environ()
atexit.register(exit_test_environ)


def unit(run=[], filter_func=None, main=False, subdirs=None,
               strict=False, stop_first=False):

    path = os.path.dirname(__file__)
    if subdirs is None:
        subdirs = []

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

    if main:
        # include plugin tests by default
        subdirs = (subdirs or []) + ["plugin"]

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
        # don't warn for tests we won't run anyway
        if run and case not in run:
            continue
        name = "%s.%s" % (case.__module__, case.__name__)
        reason = skipped_reason.get(case, "??")
        if case in skipped_warn:
            print_w("Skipped test: %s (%s)" % (name, reason))

    import quodlibet.config

    runner = Runner()
    failures = errors = all_ = 0
    use_suites = filter(filter_func, suites)
    for test in sorted(use_suites, key=repr):
        if (not run
                or test.__name__ in run
                or test.__module__[11:] in run):
            df, de, num = runner.run(test, failfast=stop_first)
            failures += df
            errors += de
            all_ += num
            if stop_first and (df or de):
                break
            quodlibet.config.quit()

    return failures, errors, all_
