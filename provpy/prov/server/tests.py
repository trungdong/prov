'''Test cases for the prov.server Django app

@author: Trung Dong Huynh <trungdong@donggiang.com>
@copyright: University of Southampton 2012
'''
import unittest, logging, sys, json, os
from prov.model.test import examples


from django.contrib.auth.models import User,Group
from tastypie.models import ApiKey
from prov.server.models import Container
from django.db import IntegrityError,DatabaseError
from guardian.shortcuts import assign, remove_perm
from django.test.client import Client
from prov.model import ProvBundle
from apport.report import Report
from prov.persistence.models import PDBundle

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
        self.assertTrue(self.users[1].has_perm('server.view_container', bundle))
        self.assertTrue(self.users[1].has_perm('change_container', bundle))
        self.assertTrue(self.users[1].has_perm('delete_container', bundle))
        self.assertTrue(self.users[1].has_perm('admin_container', bundle))
        self.assertTrue(self.users[1].has_perm('ownership_container', bundle))
        
        destination = '/api/v0/bundle/' + `bundle.id` + '/?format=json'
        logging.debug('Checking API permissions...')
        response = self.client.get(destination, **{'HTTP_AUTHORIZATION': auth})
        self.assertEqual(response.status_code, 200)
#        response = self.client.put(destination,data=data,content_type='application/json',
#                                    **{'HTTP_AUTHORIZATION': auth})
#        self.assertEqual(response.status_code, 202)
        
        logging.debug('Checking other users raw permissions...')
        self.assertFalse(self.users[0].has_perm('view_container', bundle))
        self.assertFalse(self.users[0].has_perm('change_container', bundle))
        self.assertFalse(self.users[0].has_perm('delete_container', bundle))
        self.assertFalse(self.users[0].has_perm('admin_container', bundle))
        self.assertFalse(self.users[0].has_perm('ownership_container', bundle))
        
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
        self.assertTrue(self.users[0].has_perm('view_container', bundle))
        self.assertFalse(self.users[0].has_perm('change_container', bundle))
        self.assertFalse(self.users[0].has_perm('delete_container', bundle))
        self.assertFalse(self.users[0].has_perm('admin_container', bundle))
        self.assertFalse(self.users[0].has_perm('ownership_container', bundle))
        response = self.client.get(destination, **{'HTTP_AUTHORIZATION': fakeauth})
        self.assertEqual(response.status_code, 200)
        
        remove_perm('view_container', public, bundle)
        self.assertFalse(self.users[0].has_perm('view_container', bundle))
        self.assertFalse(self.users[0].has_perm('change_container', bundle))
        self.assertFalse(self.users[0].has_perm('delete_container', bundle))
        self.assertFalse(self.users[0].has_perm('admin_container', bundle))
        self.assertFalse(self.users[0].has_perm('ownership_container', bundle))
        
        logging.debug('Deleteing the bundle from the API...')
        response = self.client.delete(destination, **{'HTTP_AUTHORIZATION': auth})
        self.assertEqual(response.status_code, 204)
        self.assertRaises(Container.DoesNotExist, Container.objects.get, id=bundle.id)

from oauth_provider.models import Consumer, Token, Resource
import oauth2 as oauth

class OAuthAuthenticationTestCase(unittest.TestCase):
    def testOAuthAccess(self):
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
        pb = ProvBundle()
        pb._decode_JSON_container('')
        self.bundle = Container.create('test_bundle', pb, self.user)
        
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
        url_path = "/api/v0/bundle/%d/" % self.bundle.id
        oauth_request = oauth.Request.from_token_and_callback(access_token, http_url='http://testserver' + url_path, parameters=parameters)
        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        signature = signature_method.sign(oauth_request, self.consumer, access_token)
        parameters['oauth_signature'] = signature
        response = c.get(url_path + '?format=json', parameters)
        self.assertEqual(response.status_code, 200)

class FileSubmissionTest(unittest.TestCase):
    def setUp(self):
        logging.debug('Setting up user and temp file...')
        self.check_u = User.objects.get_or_create(username='FileTesting')
        self.user = self.check_u[0]
        self.check_k = ApiKey.objects.get_or_create(user=self.user)
        self.key = self.check_k[0]
        self.auth = 'ApiKey' + self.user.username + ':' + self.key.key
        self.path = '/tmp/prov_test.tmp'
        self.check_u = self.check_u[1]
        self.check_k = self.check_k[1]
    
    def tearDown(self):
        logging.debug('Removing user and temp file...')
        os.remove(self.path)
        if self.check_k:
            self.key.delete()
        if self.check_u:
            self.user.delete()
        
    def testFileSubmit(self):
        client = Client()
        bundle = examples.bundles2()
        content = bundle.JSONEncoder().encode(bundle)
        file_tmp = open(self.path, 'w+')
        file_tmp.write(content)
        file_tmp.close()
        file_tmp = open(self.path)
        data="""{"rec_id": "#mockup","content": """+bundle.JSONEncoder().encode(bundle)+'}'
        logging.debug('Executing POST method with the submission attached...')
        response = client.post('/api/v0/bundle/',data={'data' : data, 'submission': file_tmp},
                                    **{'HTTP_AUTHORIZATION': self.auth})
        file_tmp.close()
        self.assertEqual(response.status_code, 201)
        bundle = Container.objects.get(id=json.JSONDecoder().decode(response.content)['id'])
        file_tmp = open(bundle.submission.content.path)
        self.assertEqual(content, file_tmp.read())
        file_tmp.close()
        os.remove(bundle.submission.content.path)

from urllib2 import urlopen

class URLSubmissionTest(unittest.TestCase):
    
    def setUp(self):
        logging.debug('Setting up user and checking the URL file...')
        self.check_u = User.objects.get_or_create(username='FileTesting')
        self.user = self.check_u[0]
        self.check_k = ApiKey.objects.get_or_create(user=self.user)
        self.key = self.check_k[0]
        self.auth = 'ApiKey' + self.user.username + ':' + self.key.key
        self.check_u = self.check_u[1]
        self.check_k = self.check_k[1]
        self.url = 'http://users.ecs.soton.ac.uk/ab9g10/test.json'
        source = urlopen(self.url)
        url_content = ProvBundle()
        url_content._decode_JSON_container(json.loads(source.read()))
        source.close()
        self.content = PDBundle.create('url_test')
        self.content.save_bundle(url_content)
        self.content = self.content.get_prov_bundle()
    
    def tearDown(self):
        logging.debug('Removing user and temp file...')
        if self.check_k:
            self.key.delete()
        if self.check_u:
            self.user.delete()
            
    def testURLSubmission(self):
        client = Client()
        data='''{"rec_id": "#mockup","content": "", "public": "True", "url": "''' + self.url + '''"}'''
        response = client.post('/api/v0/bundle/',data=data,content_type='application/json',
                                    **{'HTTP_AUTHORIZATION': self.auth})
        self.assertEqual(response.status_code, 201)
        bundle = Container.objects.get(id=json.JSONDecoder().decode(response.content)['id'])
        self.assertEqual(self.url, bundle.url)


from prov.server.search import search_name, search_id, search_literal, search_timeframe

class SearchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logging.debug('Clearing the db...')
        Container.objects.all().delete()
        logging.debug('Creating user...')
        user = User.objects.get_or_create(username='search_test')[0]
        logging.debug('Adding to the DB two bundles...')
        cls.ids = [Container.create('search_test_1', examples.bundles1(), user, False).id,
                   Container.create('search_test_1_other', examples.bundles2(), user, False).id]
    
    @classmethod
    def tearDownClass(cls):
        logging.debug('Deleting user...')
        User.objects.get(username='search_test').delete()
        
    def testSearchName(self):
        logging.debug('Testing different searches on name...')
        containers = search_name('search_test_1', exact=True)
        self.assertEqual(len(containers), 1)
        self.assertEqual(containers.get(content__rec_id='search_test_1').id, self.ids[0])
        containers = search_name('search_test')
        self.assertEqual(len(containers), 2)
        containers = search_name('other')
        self.assertEqual(len(containers), 1)
        self.assertEqual(containers.get(content__rec_id='search_test_1_other').id, self.ids[1])
        containers = search_name('other', exact=True)
        self.assertEqual(len(containers), 0)
        containers = search_name('bundle1')
        self.assertEqual(len(containers), 0)
    
    def testSearchId(self):
        logging.debug('Testing different searches on ids...')
        containers = search_id('report1bis')
        self.assertEqual(len(containers), 1)
        self.assertEqual(containers.get(content__rec_id='search_test_1_other').id, self.ids[1])
        containers = search_id('bundle1', exact=True)
        self.assertEqual(len(containers), 0)
        containers = search_id('alice')
        self.assertEqual(len(containers), 2)
        self.assertEqual(containers.get(content__rec_id='search_test_1').id, self.ids[0])
        
    def testSearchLiteral(self):
        pass
#        logging.debug('Testing different searches on prov:type...')
#        containers = search_literal('report')
#        self.assertEqual(len(containers), 2)
#        containers = search_literal('rep')
#        self.assertEqual(len(containers), 2)
#        containers = search_literal('rep', exact=True)
#        self.assertEqual(len(containers), 0)
    
    def testSearchTime(self):
        logging.debug('Testing different searches on time...')
        containers = search_timeframe(start='2012-05-24')
        self.assertEqual(len(containers), 2)
        containers = search_timeframe(end='2012-05-24')
        self.assertEqual(len(containers), 0)
        containers = search_timeframe(start='2012-05-24', end='2012-05-25')
        self.assertEqual(len(containers), 2)
        containers = search_timeframe(start='2012-05-25T12:00:00')
        self.assertEqual(len(containers), 0)

                
if __name__ == "__main__":
    from django.test.utils import setup_test_environment
    setup_test_environment()
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
