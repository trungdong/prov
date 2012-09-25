'''Django app for the Provenance Web Service

Providing a REST API and a Web user interface for sending and retrieving
provenance graphs from a server 

@author: Trung Dong Huynh <trungdong@donggiang.com>
@copyright: University of Southampton 2012
'''

import logging, os
from django.db import models
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.db.models.signals import  post_save, post_syncdb, pre_delete
from django.contrib.auth.signals import user_logged_out
from django.core.cache import cache
from guardian.shortcuts import assign
from guardian.models import UserObjectPermission, GroupObjectPermission
from prov.persistence.models import PDBundle
from prov.settings import ANONYMOUS_USER_ID, PUBLIC_GROUP_ID, MEDIA_ROOT

logger = logging.getLogger(__name__)

class UserProfile(models.Model):
    user = models.ForeignKey(User, unique=True)


def _create_profile(sender, created, instance, **kwargs):
    if(created):
        UserProfile.objects.create(user=instance)
        instance.groups.add(Group.objects.get(name='public'))

def _create_public_group(**kwargs):
    public_group, _ = Group.objects.get_or_create(id=PUBLIC_GROUP_ID, defaults={'name': 'public'}) 
    user, _ = User.objects.get_or_create(id=ANONYMOUS_USER_ID, defaults={'username': 'AnonymousUser'})
    user.groups.add(public_group)
        
def _create_submission_folder(**kwargs):
    if not os.path.exists(MEDIA_ROOT+'submissions/'):
        os.makedirs(MEDIA_ROOT+'submissions/')

def _clear_user_cache(user, **kwargs):
    cache.delete(user.username+'_l')
    cache.delete(user.username+'_s')

post_save.connect(_create_profile, sender=User, dispatch_uid=__file__)

post_syncdb.connect(_create_public_group)

post_syncdb.connect(_create_submission_folder)

user_logged_out.connect(_clear_user_cache)

def remove_obj_perms_connected_with_user(sender, instance, **kwargs):
    ''' Remove all permissions connected with the user to avoid orphan permissions
    '''
    filters = Q(content_type=ContentType.objects.get_for_model(instance),
        object_pk=instance.pk)
    UserObjectPermission.objects.filter(filters).delete()
    GroupObjectPermission.objects.filter(filters).delete()

pre_delete.connect(remove_obj_perms_connected_with_user, sender=User)


class Submission(models.Model):
    '''
    Model to represent a file submitted together with the bundle to be stored
    '''
    timestamp = models.DateTimeField(auto_now_add = True)
    format = models.CharField(max_length=255)
    content = models.FileField(upload_to='submissions')
    

class License(models.Model):
    '''
    Model for different Licenses 
    '''
    title = models.CharField(max_length=30)
    description = models.CharField(max_length=255)
    url = models.URLField()

    
class Container(models.Model):
    '''
    Model for a container of the top level bundles
    '''
    owner = models.ForeignKey(User, blank=True, null=True)
    content = models.ForeignKey(PDBundle, unique=True)
    submission = models.ForeignKey(Submission, blank=True, null=True)
    license = models.ManyToManyField(License)
    url = models.URLField(blank=True, null=True)
    public = models.BooleanField(default=False)
    
    class Meta:
        permissions = (
            ("view_container", "View the container."),
            ("admin_container", "Administrate permissions on the container."),
            ("ownership_container", "Changing ownership of the container."),
        )
    
    def delete(self):
        if self.content:
            self.content.delete()
        super(Container, self).delete()

    @staticmethod
    def create(rec_id, prov_bundle, owner, public=False):
        pdbundle = PDBundle.create(rec_id)
        pdbundle.save_bundle(prov_bundle)
        container = Container.objects.create(owner=owner, content=pdbundle, public=public)

        assign('view_container', owner, container)
        assign('change_container', owner, container)
        assign('delete_container', owner, container)
        assign('admin_container', owner, container)
        assign('ownership_container', owner, container)
        if public == True:
            assign('view_container', Group.objects.get(name='public'), container)
        return container
