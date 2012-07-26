'''Django app for the Provenance Web Service

Providing a REST API and a Web user interface for sending and retrieving
provenance graphs from a server 

@author: Trung Dong Huynh <trungdong@donggiang.com>
@copyright: University of Southampton 2012
'''

from django.db import models
from django.contrib.auth.models import User, Group
from django.db.models.signals import  post_save, post_syncdb
import logging
logger = logging.getLogger(__name__)
from prov.persistence.models import PDBundle

class UserProfile(models.Model):
    user = models.ForeignKey(User, unique=True)


def _create_profile(sender, created, instance, **kwargs):
    if(created):
        UserProfile.objects.create(user=instance)
        instance.groups.add(Group.objects.get(name='public'))

def _create_public_group(**kwargs):
    from prov.settings import ANONYMOUS_USER_ID, PUBLIC_GROUP_ID
    try:
        public = Group.objects.get(name='public') 
    except Group.DoesNotExist:
        public = Group.objects.create(id=PUBLIC_GROUP_ID,name='public')
    try:
        User.objects.get(id=ANONYMOUS_USER_ID).groups.add(public)
    except User.DoesNotExist:
        User.objects.create(id=ANONYMOUS_USER_ID, username='AnonymousUser').groups.add(public)
    
post_save.connect(_create_profile, sender=User, dispatch_uid=__file__)
post_syncdb.connect(_create_public_group)
    
class Container(models.Model):
    '''
    
    '''
    owner = models.ForeignKey(User, blank=True, null=True)
    content = models.ForeignKey(PDBundle, unique=True)
    public = models.BooleanField(default=False)
