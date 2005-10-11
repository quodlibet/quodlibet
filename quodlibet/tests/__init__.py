import unittest, os, sys, glob
from unittest import TestCase
suites = []
add = registerCase = suites.append
import __builtin__; __builtin__.__dict__.setdefault("_", lambda a: a)

import const
const.CONFIG = "./const-config"
const.CURRENT = "./const-current"
const.PAUSED = "./const-paused"
const.LIBRARY = "./const-songs"
const.QUEUE = "./const-queue"

class Mock(object):
    # A generic mocking object.
    def __init__(self, **kwargs): self.__dict__.update(kwargs)

class TPO(unittest.TestCase):
    def test_pos(self):
        for f in glob.glob("po/*.po"):
            self.failIf(os.system("msgfmt -c %s > /dev/null" % f))
        try: os.unlink("messages.mo")
        except OSError: pass
registerCase(TPO)

import test_util, test_audio, test_parser, test_metadata
import test_playlist, test_pattern, test_stock
import test_qltk, test_widgets, test_player
import test_library, test_plugins, test_efwidgets, test_properties

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

class Runner:
    def run(self, test):
        suite = unittest.makeSuite(test)
        pref = '%s (%d): ' % (test.__name__, len(suite._tests))
        print pref + " " * (25 - len(pref)),
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

if __name__ == "__main__":
    unit(sys.argv[1:])
