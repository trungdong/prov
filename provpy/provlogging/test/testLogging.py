'''
Created on Jan 25, 2012

@author: Dong
'''
import unittest
import provlogging as prov
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
provlogger = prov.getLogger()

@prov.Activity('TestActivity', {'prov:type': 'TestActivityType'})
def activity1():
    logging.debug('This is activity 1')
    activity = prov.current_activity()
    activity.uses('test_resource')
    activity.generates('test_output')
#    raise Exception()
    activity.derives('test_output', 'test_resource', {'prov:type': 'DummyDerivation'})

class Test(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testProvLogging(self):
        logger.debug('Calling activity1 the 1st time')
        activity1()
        logger.debug('Calling activity1 the 2nd time')
        activity1()

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()