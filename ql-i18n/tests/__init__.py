import unittest
suites = []
def registerSuite(suite):
    suites.append(suite)

def registerCase(testcase):
    registerSuite(unittest.makeSuite(testcase))

import test_util, test_library, test_match, test_parser, test_player

def unit():
    runner = unittest.TextTestRunner()
    for suite in suites:
        runner.run(suite)
