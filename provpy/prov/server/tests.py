'''Test cases for the prov.server Django app

@author: Trung Dong Huynh <trungdong@donggiang.com>
@copyright: University of Southampton 2012
'''
import unittest, logging, sys, json
from prov.model.test import examples


from django.contrib.auth.models import User,Group
from tastypie.models import ApiKey
from prov.server.models import Container
from django.db import IntegrityError,DatabaseError
from guardian.shortcuts import assign, remove_perm
from django.test.client import Client

logger = logging.getLogger(__name__)       

class AuthenticationTest(unittest.TestCase):
    USER_COUNT = 2
    users = {}
    client = Client()
    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName=methodName)
    
    @classmethod
    def setUpClass(cls):
        super(AuthenticationTest, cls).setUpClass()
        try:
            logging.debug('Creating users...')
            for u in range(cls.USER_COUNT):
                cls.users[u] = User.objects.create_user(username='test'+`u`, password='pass')
        except IntegrityError, DatabaseError:
            sys.exit('Users already exist!')
    
    @classmethod
    def tearDownClass(cls):
        logging.debug('Deleting users...')
        for u in range(cls.USER_COUNT):
            cls.users[u].delete()
    
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
        data="""{"rec_id": "#mockup","content": """+bundle.JSONEncoder().encode(bundle)+'}'
        logging.debug('Executing POST method with the authentication...')
        response = self.client.post('/api/v0/bundle/',data=data,content_type='application/json',
                                    **{'HTTP_AUTHORIZATION': auth})
        
        self.assertEqual(response.status_code, 201)
        bundle = Container.objects.get(id=json.JSONDecoder().decode(response.content)['id'])
        logging.debug('Bundle created with id '+`bundle.id`)
        logging.debug('Checking all raw permissions...')
        self.assertEqual(self.users[1].has_perm('view_container', bundle), True)
        self.assertEqual(self.users[1].has_perm('change_container', bundle), True)
        self.assertEqual(self.users[1].has_perm('delete_container', bundle), True)
        self.assertEqual(self.users[1].has_perm('admin_container', bundle), True)
        self.assertEqual(self.users[1].has_perm('ownership_container', bundle), True)
        
        destination = '/api/v0/bundle/' + `bundle.id` + '/?format=json'
        logging.debug('Checking API permissions...')
        response = self.client.get(destination, **{'HTTP_AUTHORIZATION': auth})
        self.assertEqual(response.status_code, 200)
#        response = self.client.put(destination,data=data,content_type='application/json',
#                                    **{'HTTP_AUTHORIZATION': auth})
#        self.assertEqual(response.status_code, 202)
        
        logging.debug('Checking other users raw permissions...')
        self.assertEqual(self.users[0].has_perm('view_container', bundle), False)
        self.assertEqual(self.users[0].has_perm('change_container', bundle), False)
        self.assertEqual(self.users[0].has_perm('delete_container', bundle), False)
        self.assertEqual(self.users[0].has_perm('admin_container', bundle), False)
        self.assertEqual(self.users[0].has_perm('ownership_container', bundle), False)
        
        try:
            fake_key = ApiKey.objects.get(user=self.users[0]).key
        except ApiKey.DoesNotExist:
            fake_key = ApiKey.objects.create(user=self.users[0]).key
        fakeauth = 'ApiKey ' + self.users[0].username + ':' + fake_key
        logging.debug('Checking API permissions for other user...')
        response = self.client.get(destination, **{'HTTP_AUTHORIZATION': fakeauth})
        self.assertEqual(response.status_code, 403)
        
        logging.debug('Checking group permissions...')
        public = Group.objects.get(name='public')
        assign('view_container', public, bundle)
        self.assertEqual(self.users[0].has_perm('view_container', bundle), True)
        self.assertEqual(self.users[0].has_perm('change_container', bundle), False)
        self.assertEqual(self.users[0].has_perm('delete_container', bundle), False)
        self.assertEqual(self.users[0].has_perm('admin_container', bundle), False)
        self.assertEqual(self.users[0].has_perm('ownership_container', bundle), False)
        response = self.client.get(destination, **{'HTTP_AUTHORIZATION': fakeauth})
        self.assertEqual(response.status_code, 200)
        
        remove_perm('view_container', public, bundle)
        self.assertEqual(self.users[0].has_perm('view_container', bundle), False)
        self.assertEqual(self.users[0].has_perm('change_container', bundle), False)
        self.assertEqual(self.users[0].has_perm('delete_container', bundle), False)
        self.assertEqual(self.users[0].has_perm('admin_container', bundle), False)
        self.assertEqual(self.users[0].has_perm('ownership_container', bundle), False)
        
        logging.debug('Deleteing the bundle from the API...')
        response = self.client.delete(destination, **{'HTTP_AUTHORIZATION': auth})
        self.assertEqual(response.status_code, 204)
        self.assertRaises(Container.DoesNotExist, Container.objects.get, id=bundle.id)

from oauth_provider.models import Consumer, Token, Resource
import oauth2 as oauth

class OAuthAuthenticationTestCase(unittest.TestCase):
    def setUp(self):
        super(OAuthAuthenticationTestCase, self).setUp()
        
        self.user = User.objects.create_user('jane', 'jane@example.com', 'toto')
        self.resource = Resource.objects.get_or_create(name='api', url='/api/')
        self.CONSUMER_KEY = 'dpf43f3p2l4k3l03'
        self.CONSUMER_SECRET = 'kd94hf93k423kf44'
        self.consumer, _ = Consumer.objects.get_or_create(
            key=self.CONSUMER_KEY, secret=self.CONSUMER_SECRET,
            defaults={
                'name': 'Test',
                'description': 'Testing...'
        })
        self.bundle = Container.create('test_bundle', '', self.user)

        
    def testOAuthAccess(self):
        c = Client()
        response = c.get("/oauth/request_token/")
        self.assertEqual(response.status_code, 401)
        import time
        parameters = {
            'oauth_consumer_key': self.CONSUMER_KEY,
            'oauth_signature_method': 'PLAINTEXT',
            'oauth_signature': '%s&' % self.CONSUMER_SECRET,
            'oauth_timestamp': str(int(time.time())),
            'oauth_nonce': 'requestnonce',
            'oauth_version': '1.0',
            'oauth_callback': 'http://test/request_token_ready',
            'scope': 'api',
            }
        response = c.get("/oauth/request_token/", parameters)
        self.assertEqual(response.status_code, 200)
        token = list(Token.objects.all())[-1]
        self.assertIn(token.key, response.content)
        self.assertIn(token.secret, response.content)
        self.assertTrue(token.callback_confirmed)

        parameters = {'oauth_token': token.key,}
        response = c.get("/oauth/authorize/", parameters)
        self.assertEqual(response.status_code, 302)
        self.assertIn(token.key, response['Location'])
        c.login(username='jane', password='toto')
        self.assertFalse(token.is_approved)
        response = c.get("/oauth/authorize/", parameters)
        self.assertEqual(response.status_code, 200)
        
        # fake authorization by the user
        parameters['authorize_access'] = 1
        response = c.post("/oauth/authorize/", parameters)
        self.assertEqual(response.status_code, 302)
        token = Token.objects.get(key=token.key)
        self.assertIn(token.key, response['Location'])
        self.assertTrue(token.is_approved)
        c.logout()
        
        # Exchange the Request token for an Access token
        parameters = {
            'oauth_consumer_key': self.CONSUMER_KEY,
            'oauth_token': token.key,
            'oauth_signature_method': 'PLAINTEXT',
            'oauth_signature': '%s&%s' % (self.CONSUMER_SECRET, token.secret),
            'oauth_timestamp': str(int(time.time())),
            'oauth_nonce': 'accessnonce',
            'oauth_version': '1.0',
            'oauth_verifier': token.verifier,
            'scope': 'api',
            }
        response = c.get("/oauth/access_token/", parameters)
        self.assertEqual(response.status_code, 200)
        access_token = list(Token.objects.filter(token_type=Token.ACCESS))[-1]
        self.assertIn(access_token.key, response.content)
        self.assertIn(access_token.secret, response.content)
        self.assertEqual(access_token.user.username, self.user.username)
        
        # Generating signature base string
        parameters = {
            'oauth_consumer_key': self.CONSUMER_KEY,
            'oauth_token': access_token.key,
            'oauth_signature_method': 'HMAC-SHA1',
            'oauth_timestamp': str(int(time.time())),
            'oauth_nonce': 'accessresourcenonce',
            'oauth_version': '1.0',
        }
        oauth_request = oauth.Request.from_token_and_callback(access_token, http_url='http://testserver/api/v0/bundle/1/', parameters=parameters)
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(oauth_request, self.consumer, access_token)
        parameters['oauth_signature'] = signature
        response = c.get("/api/v0/bundle/1/?format=json", parameters)
        self.assertEqual(response.status_code, 200)
        
if __name__ == "__main__":
    from django.test.utils import setup_test_environment
    setup_test_environment()
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()