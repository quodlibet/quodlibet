import os
import glob
import sys
import unittest

from unittest import TestCase

suites = []
add = suites.append

class Mock(object):
    # A generic mocking object.
    def __init__(self, **kwargs): self.__dict__.update(kwargs)

class Result(unittest.TestResult):

    separator1 = '=' * 70
    separator2 = '-' * 70

    def addSuccess(self, test):
        unittest.TestResult.addSuccess(self, test)
        sys.stdout.write('.')
        sys.stdout.flush()

    def addError(self, test, err):
        unittest.TestResult.addError(self, test, err)
        sys.stdout.write('E')
        sys.stdout.flush()

    def addFailure(self, test, err):
        unittest.TestResult.addFailure(self, test, err)
        sys.stdout.write('F')
        sys.stdout.flush()

    def printErrors(self):
        if self.errors: self.printErrorList('ERROR', self.errors)
        if self.failures: self.printErrorList('FAIL', self.failures)

    def printErrorList(self, flavour, errors):
        print
        for test, err in errors:
            sys.stdout.write(self.separator1 + "\n")
            sys.stdout.write("%s: %s\n" % (flavour, str(test)))
            sys.stdout.write(self.separator2 + "\n")
            sys.stdout.write("%s\n" % err)

class Runner(object):
    def run(self, test):
        suite = unittest.makeSuite(test)
        result = Result()
        suite(result)
        result.printErrors()

def import_module (modname, tracer=None):
    if tracer is None:
        mod = __import__(modname)
    else:
        mod = tracer.runfunc(__import__, modname)
    return mod

def init (tracer=None):
    import pygst
    pygst.require("0.10")

    const = import_module("const", tracer=tracer)
    const.CONFIG = os.path.join(const.BASEDIR, 'tests', 'data', "config")
    const.CURRENT = os.path.join(const.BASEDIR, 'tests', 'data', "current")
    const.LIBRARY = os.path.join(const.BASEDIR, 'tests', 'data', "library")

    util = import_module("util", tracer=tracer)
    util.python_init()
    util.ctypes_init()
    util.gtk_init()

    ui18n = import_module("util.i18n", tracer=tracer)
    ui18n.GlibTranslations().install()

    library = import_module("library", tracer=tracer)
    library.init()

    config = import_module("config", tracer=tracer)
    config.init()

    # get test suites
    for fn in glob.glob(os.path.join(os.path.dirname(__file__), "test_*.py")):
        args = (fn[:-3].replace("/", "."), globals(), locals(), "tests")
        if tracer is None:
            __import__(*args)
        else:
            tracer.runfunc(__import__, *args)

def unit(run=[]):
    if run and run[0] == "--trace":
        run.pop()
        import trace
        ignoremods = ['tests']
        ignoredirs = [sys.prefix, sys.exec_prefix]
        tracer = trace.Trace(count=True, trace=False,
                             ignoremods=ignoremods, ignoredirs=ignoredirs)
    else:
        tracer = None
    init(tracer=tracer)
    # filter tests
    if run:
        torun = [t for t in suites if (t.__name__ in run or
                 (t.__name__.startswith("T") and t.__name__[1:] in run))]
    else:
        torun = suites
    # run tests
    runner = Runner()
    if tracer is None:
        map(runner.run, torun)
    else:
        map(lambda t: tracer.runfunc(runner.run, t), torun)
        results = tracer.results()
        results.write_results(show_missing=True, coverdir='coverage')
    import const
    for f in [const.CONFIG, const.CURRENT, const.LIBRARY]:
       try: os.unlink(f)
       except OSError: pass
    print

if __name__ == "__main__":
    unit(sys.argv[1:])
