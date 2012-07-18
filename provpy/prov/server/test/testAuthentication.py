from django.utils import unittest
import logging, sys
from tastypie.models import ApiKey
from prov.server.auth import CustomAuthentication
from tastypie.authentication import MultiAuthentication, ApiKeyAuthentication
from django.contrib.auth.models import User
from django.test.client import Client
logger = logging.getLogger(__name__)
USER_COUNT = 2

'''
When running the tests in the main 'urls.py' leave only
the api urls. For some reason django Client can not 
resolve the module paths and will raise exception.
'''

class AuthenticationTest(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        self.users = {}
        self.client = Client()
        self.bundles = {}
        self.bundle_db_id_map = dict()
        unittest.TestCase.__init__(self, methodName=methodName)
    
    def setUp(self):
        self.authentication = MultiAuthentication(ApiKeyAuthentication(), CustomAuthentication())
        try:
            logging.debug('Creating users...')
            for u in range(USER_COUNT):
                self.users[u] = User.objects.create_user(username='test'+`u`, password='pass')
        except:
            sys.exit('Users already exists!')

    def tearDown(self):
        logging.debug('Deleting users...')
        for u in range(USER_COUNT):
            self.users[u].delete()
    
    def testApiKeyAuth(self):
        logging.debug('Creating API Key for user test0...')
        api_key = ApiKey.objects.create(user=self.users[0]).key
        auth = 'ApiKey ' + self.users[0].username + ':' + api_key
        logging.debug(auth)
        response = self.client.get('/api/v0/bundle/?format=json', **{'HTTP_AUTHORIZATION': auth})
        self.assertEqual(response.status_code, 200)
        fake_key = ApiKey().generate_key()
        fake_auth = 'ApiKey ' + self.users[0].username + ':' + fake_key
        response = self.client.get('/api/v0/bundle/?format=json', **{'HTTP_AUTHORIZATION': fake_auth})
        self.assertEqual(response.status_code, 401)
        
    def testAnonymousAuth(self):
        response = self.client.get('/api/v0/bundle/?format=json')
        self.assertEqual(response.status_code, 200)
    
if __name__ == "__main__":
    from django.test.utils import setup_test_environment
    setup_test_environment()
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()