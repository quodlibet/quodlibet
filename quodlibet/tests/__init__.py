import unittest, sys
suites = []
registerCase = suites.append

class Mock(object):
    # A generic mocking object.
    def __init__(self, **kwargs): self.__dict__.update(kwargs)

# well-tested code
import test_util, test_audio
# not well-tested code
import test_parser, test_leaks, test_qltk
import test_library, test_match, test_player

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

def unit():
    runner = Runner()
    for suite in suites: runner.run(suite)
