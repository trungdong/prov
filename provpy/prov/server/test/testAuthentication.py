from django.utils import unittest
import logging
import sys
from tastypie.models import ApiKey
from django.contrib.auth.models import User
from django.test.client import Client
import prov
from prov import manage
logger = logging.getLogger(__name__)

class TestAuthentication(unittest.TestCase):

    user = None  
    def setUp(self):
        manage
        logger.debug("Creating user with credentials %s\n" % 'test2 pass1')
        self.user = User.objects.create_user(username='test1', password='pass1')
    
    def tearDown(self):
        self.user.delete()
    
    def runTestOnAuthentication(self, user):
        api_key = ApiKey.objects.create(user=user)
        logger.debug("Generated API key is %s\n" % api_key.key)
        auth = 'ApiKey '+self.user.username + ':' + api_key.key 
        c = Client()
        response = c.get(path='/api/v0/account?format=json', HTTP_AUTHORIZATION='')
        assert(response.status_code == 200)
        
    def testAllExamples(self):
        logger.info('Testing PROV-JSON server\n')
        self.runTestOnAuthentication(self.user)
                