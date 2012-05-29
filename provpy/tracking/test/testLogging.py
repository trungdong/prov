'''
Created on Jan 25, 2012

@author: Dong
'''
import unittest
import tracking as prov
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
provlogger = prov.getLogger()

@prov.Activity('TestActivity', {'prov:type': 'TestIncrease'})
def increase(x):
    activity = prov.current_activity()
    activity.uses_object(x)
    y = x + 1;
    activity.generates_object(y)
    activity.derives_object(x, y, {'prov:type': 'ex:PlusOne'})
    return y;

class Test(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testProvLogging(self):
        logger.debug('Calling increase(x)')
        x = 1000
        y = increase(x)
        logger.debug('Calling increase(y)')
        z = increase(y)
        a = increase(1001)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()