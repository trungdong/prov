from django.utils import unittest
import logging, sys
from tastypie.models import ApiKey
from django.contrib.auth.models import User, Group
from django.test.client import Client
from guardian.shortcuts import assign, remove_perm
from prov.model.test import examples
from prov.model import json
from prov.server.models import PDBundle
from django.db.utils import IntegrityError, DatabaseError
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
        unittest.TestCase.__init__(self, methodName=methodName)
    
    def setUp(self):
        try:
            logging.debug('Creating users...')
            for u in range(USER_COUNT):
                self.users[u] = User.objects.create_user(username='test'+`u`, password='pass')
        except IntegrityError, DatabaseError:
            sys.exit('Users already exist!')

    def tearDown(self):
        logging.debug('Deleting users...')
        for u in range(USER_COUNT):
            self.users[u].delete()
    
    def testApiKeyAuth(self):
        logging.debug('Creating API Key for user test0...')
        api_key = ApiKey.objects.create(user=self.users[0]).key
        auth = 'ApiKey ' + self.users[0].username + ':' + api_key
        logging.debug('Executing GET method with the authentication...')
        response = self.client.get('/api/v0/bundle/?format=json', **{'HTTP_AUTHORIZATION': auth})
        self.assertEqual(response.status_code, 200)
        fake_key = ApiKey().generate_key()
        fake_auth = 'ApiKey ' + self.users[0].username + ':' + fake_key
        logging.debug('Executing GET method with same username and fake authentication...')
        response = self.client.get('/api/v0/bundle/?format=json', **{'HTTP_AUTHORIZATION': fake_auth})
        self.assertEqual(response.status_code, 401)
        
    def testAnonymousAuth(self):
        logging.debug('Executing GET method with anonymous user...')
        response = self.client.get('/api/v0/bundle/?format=json')
        self.assertEqual(response.status_code, 200)
        
    def testUserPermissions(self):
        logging.debug('Creating API Key for user test1...')
        api_key = ApiKey.objects.create(user=self.users[1]).key
        auth = 'ApiKey ' + self.users[1].username + ':' + api_key
        bundle = examples.bundles1()
        data="""{"asserter": "#test2","rec_id": "#mockup","content": """+bundle.JSONEncoder().encode(bundle)+'}'
        logging.debug('Executing POST method with the authentication...')
        response = self.client.post('/api/v0/bundle/',data=data,content_type='application/json',
                                    **{'HTTP_AUTHORIZATION': auth})
        
        self.assertEqual(response.status_code, 201)
        bundle = PDBundle.objects.get(id=json.JSONDecoder().decode(response.content)['id'])
        logging.debug('Bundle created with id '+`bundle.id`)
        logging.debug('Checking all raw permissions...')
        self.assertEqual(self.users[1].has_perm('view_pdbundle', bundle), True)
        self.assertEqual(self.users[1].has_perm('change_pdbundle', bundle), True)
        self.assertEqual(self.users[1].has_perm('delete_pdbundle', bundle), True)
        self.assertEqual(self.users[1].has_perm('admin_pdbundle', bundle), True)
        self.assertEqual(self.users[1].has_perm('ownership_pdbundle', bundle), True)
        
        destination = '/api/v0/bundle/' + `bundle.id` + '/?format=json'
        logging.debug('Checking API permissions...')
        response = self.client.get(destination, **{'HTTP_AUTHORIZATION': auth})
        self.assertEqual(response.status_code, 200)
        response = self.client.put(destination,data=data,content_type='application/json',
                                    **{'HTTP_AUTHORIZATION': auth})
        self.assertEqual(response.status_code, 202)
        
        logging.debug('Checking other users raw permissions...')
        self.assertEqual(self.users[0].has_perm('view_pdbundle', bundle), False)
        self.assertEqual(self.users[0].has_perm('change_pdbundle', bundle), False)
        self.assertEqual(self.users[0].has_perm('delete_pdbundle', bundle), False)
        self.assertEqual(self.users[0].has_perm('admin_pdbundle', bundle), False)
        self.assertEqual(self.users[0].has_perm('ownership_pdbundle', bundle), False)
        
        fakeauth = 'ApiKey ' + self.users[0].username + ':' + ApiKey.objects.create(user=self.users[0]).key
        logging.debug('Checking API permissions for other user...')
        response = self.client.get(destination, **{'HTTP_AUTHORIZATION': fakeauth})
        self.assertNotEqual(response.status_code, 200)
        
        logging.debug('Checking group permissions...')
        public = Group.objects.get(name='public')
        assign('view_pdbundle',public,bundle)
        self.assertEqual(self.users[0].has_perm('view_pdbundle', bundle), True)
        self.assertEqual(self.users[0].has_perm('change_pdbundle', bundle), False)
        self.assertEqual(self.users[0].has_perm('delete_pdbundle', bundle), False)
        self.assertEqual(self.users[0].has_perm('admin_pdbundle', bundle), False)
        self.assertEqual(self.users[0].has_perm('ownership_pdbundle', bundle), False)
        remove_perm('view_pdbundle', public, bundle)
        self.assertEqual(self.users[0].has_perm('view_pdbundle', bundle), False)
        self.assertEqual(self.users[0].has_perm('change_pdbundle', bundle), False)
        self.assertEqual(self.users[0].has_perm('delete_pdbundle', bundle), False)
        self.assertEqual(self.users[0].has_perm('admin_pdbundle', bundle), False)
        self.assertEqual(self.users[0].has_perm('ownership_pdbundle', bundle), False)
        
        logging.debug('Deleteing the bundle from the API...')
        response = self.client.delete(destination, **{'HTTP_AUTHORIZATION': auth})
        self.assertEqual(response.status_code, 204)
        self.assertRaises(PDBundle.DoesNotExist, PDBundle.objects.get, id=bundle.id)
                
                
if __name__ == "__main__":
    from django.test.utils import setup_test_environment
    setup_test_environment()
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()