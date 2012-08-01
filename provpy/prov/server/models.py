'''Django app for the Provenance Web Service

Providing a REST API and a Web user interface for sending and retrieving
provenance graphs from a server 

@author: Trung Dong Huynh <trungdong@donggiang.com>
@copyright: University of Southampton 2012
'''

import logging, json
from django.db import models
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.db.models.signals import  post_save, post_syncdb, pre_delete
from guardian.shortcuts import assign
from guardian.models import UserObjectPermission, GroupObjectPermission
from prov.model import ProvBundle
from prov.persistence.models import PDBundle

logger = logging.getLogger(__name__)

class UserProfile(models.Model):
    user = models.ForeignKey(User, unique=True)


def _create_profile(sender, created, instance, **kwargs):
    if(created):
        UserProfile.objects.create(user=instance)
        instance.groups.add(Group.objects.get(name='public'))

def _create_public_group(**kwargs):
    from prov.settings import ANONYMOUS_USER_ID, PUBLIC_GROUP_ID
    public = Group.objects.get_or_create(id=PUBLIC_GROUP_ID, name='public') 
    User.objects.get_or_create(id=ANONYMOUS_USER_ID, username='AnonymousUser').groups.add(public)
        
 
post_save.connect(_create_profile, sender=User, dispatch_uid=__file__)
post_syncdb.connect(_create_public_group)

def remove_obj_perms_connected_with_user(sender, instance, **kwargs):
    ''' Remove all permissions connected with the user to avoid orphan permissions
    '''
    filters = Q(content_type=ContentType.objects.get_for_model(instance),
        object_pk=instance.pk)
    UserObjectPermission.objects.filter(filters).delete()
    GroupObjectPermission.objects.filter(filters).delete()

pre_delete.connect(remove_obj_perms_connected_with_user, sender=User)

class Container(models.Model):
    '''
    
    '''
    owner = models.ForeignKey(User, blank=True, null=True)
    content = models.ForeignKey(PDBundle, unique=True)
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
    def create(rec_id, raw_json, owner, public=False):
        prov_bundle = ProvBundle();
        try:
            prov_bundle._decode_JSON_container(raw_json)
        except TypeError:
            prov_bundle = json.loads(raw_json, cls=ProvBundle.JSONDecoder)
        pdbundle = PDBundle.create(rec_id)
        pdbundle.save_bundle(prov_bundle)
        container = Container.objects.create(owner=owner, content=pdbundle, public=public)
        
        assign('view_container', owner, container)
        assign('change_container', owner, container)
        assign('delete_container', owner, container)
        assign('admin_container', owner, container)
        assign('ownership_container', owner, container)

        return container