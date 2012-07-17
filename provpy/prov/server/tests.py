'''Test cases for the prov.server Django app

@author: Trung Dong Huynh <trungdong@donggiang.com>
@copyright: University of Southampton 2012
'''
import unittest, logging
from prov.model.test import examples
from prov.server.models import save_bundle, PDBundle

logger = logging.getLogger(__name__)


class SaveLoadTest(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        self.bundles = {}
        self.bundle_db_id_map = dict()
            
        unittest.TestCase.__init__(self, methodName=methodName)
    
    def setUp(self):
        for bundle_id, create_bundle in examples.tests:
            logger.debug('Creating bundle: %s...' % bundle_id)
            self.bundles[bundle_id] = create_bundle()

            logger.debug('Saving bundle: %s...' % bundle_id)
            pdbundle = save_bundle(self.bundles[bundle_id], bundle_id, __name__)
            self.bundle_db_id_map[bundle_id]= pdbundle.pk

    def tearDown(self):
        logger.debug('Deleting all test bundles (%d in total)' % len(self.bundle_db_id_map))
        PDBundle.objects.filter(pk__in=self.bundle_db_id_map.values()).delete()

    def testName(self):
        for bundle_id in self.bundles:
            logger.debug('Loading bundle from DB: %s...' % bundle_id)
            pdbundle = PDBundle.objects.get(pk=self.bundle_db_id_map[bundle_id])
            prov_bundle = pdbundle.get_prov_bundle()
            assert(prov_bundle == self.bundles[bundle_id])

if __name__ == "__main__":
    from django.test.utils import setup_test_environment
    setup_test_environment()
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()