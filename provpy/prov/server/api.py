from tastypie import fields
from tastypie.authentication import OAuthAuthentication
from prov.server.auth import ApiKeyAuthentication,AnnonymousAuthentication, MultiAuthentication, CustomAuthorization
from tastypie.resources import ModelResource
from guardian.shortcuts import assign
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.http import HttpBadRequest
from models import Container
from django.contrib.auth.models import Group
from prov.settings import PUBLIC_GROUP_ID

class ContainerResource(ModelResource):
    
    class Meta:
        queryset = Container.objects.all()
        resource_name = 'bundle'
        excludes = ['content']
        list_allowed_methods = ['get', 'post', 'delete']
        detail_allowed_methods = ['get', 'post', 'delete']
        always_return_data = True
        authorization = CustomAuthorization()
        authentication = MultiAuthentication(OAuthAuthentication(), ApiKeyAuthentication(), AnnonymousAuthentication())        
    prov_json = fields.DictField(attribute='prov_json', null=True)
    
    def obj_create(self, bundle, request=None, **kwargs):
        try:
            container = Container.create(bundle.data['rec_id'], bundle.data['content'], request.user)
            if 'public' in bundle.data: 
                container.public = bundle.data['public']
                container.save()
                if bundle.data['public']:
                    assign('view_container', Group.objects.get(id=PUBLIC_GROUP_ID), container)
                
        except: 
            raise ImmediateHttpResponse(HttpBadRequest())

        bundle.obj = container
        return bundle
    
    def dehydrate_prov_json(self, bundle):
        if self.get_resource_uri(bundle) == bundle.request.path:
            prov_bundle = bundle.obj.content.get_prov_bundle()
            return prov_bundle._encode_JSON_container()
        else:
            return None
        
    def dehydrate_editable(self, bundle):
        return bundle.request.user.has_perm('change_container', bundle)
