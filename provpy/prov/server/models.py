'''Django app for the Provenance Web Service

Providing a REST API and a Web user interface for sending and retrieving
provenance graphs from a server 


@author: Trung Dong Huynh <trungdong@donggiang.com>
@copyright: University of Southampton 2012
'''

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import  post_save
from prov.persistence.models import PDBundle


class UserProfile(models.Model):
    user = models.ForeignKey(User, unique=True)


def _create_profile(sender, created, instance, **kwargs):
    if(created):
        UserProfile.objects.create(user=instance)

post_save.connect(_create_profile, sender=User, dispatch_uid=__file__)
    
class Container(models.Model):
    '''
    
    '''
    owner = models.ForeignKey(User, blank=True, null=True)
    content = models.ForeignKey(PDBundle, unique=True)
    public = models.BooleanField(default=False)