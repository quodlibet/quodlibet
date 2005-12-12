import unittest, os, sys, glob
from unittest import TestCase
suites = []
add = registerCase = suites.append
import __builtin__
__builtin__.__dict__.setdefault("_", lambda a: a)
__builtin__.__dict__.setdefault(
    "ngettext", lambda a, b, c: (c == 1 and a) or b)

import const
const.CONFIG = "./const-config"
const.CURRENT = "./const-current"
const.LIBRARY = "./const-songs"
const.QUEUE = "./const-queue"

import util; util.ctypes_init()
import config; config.init()
import library; library.init()

class Mock(object):
    # A generic mocking object.
    def __init__(self, **kwargs): self.__dict__.update(kwargs)

for fn in glob.glob(os.path.join(os.path.dirname(__file__), "test_*.py")):
    __import__(fn[:-3].replace("/", "."), globals(), locals(), "tests")

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

class Runner:
    def run(self, test):
        suite = unittest.makeSuite(test)
        result = Result()
        suite(result)
        result.printErrors()

def unit(run=[]):
    runner = Runner()
    if not run: map(runner.run, suites)
    else:
        for t in suites:
            if (t.__name__ in run or
                (t.__name__.startswith("T") and t.__name__[1:] in run)):
                runner.run(t)

    for f in [const.CONFIG, const.CURRENT, const.LIBRARY, const.QUEUE]:
       try: os.unlink(f)
       except OSError: pass
    print

if __name__ == "__main__":
    unit(sys.argv[1:])

