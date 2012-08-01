from tastypie import fields
from tastypie.resources import *
from tastypie.authentication import Authentication
from tastypie.authorization import Authorization
from prov.server.auth import ApiKeyAuthentication,AnnonymousAuthentication, MultiAuthentication, CustomAuthorization
from tastypie.resources import ModelResource
from guardian.shortcuts import assign
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.http import HttpBadRequest
from models import Container, Submission
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
        authentication = MultiAuthentication(ApiKeyAuthentication(), AnnonymousAuthentication())
        
    prov_json = fields.DictField(attribute='prov_json', null=True)
    original_file = fields.FileField(attribute='original', null=True)
    
    def obj_create(self, bundle, request=None, **kwargs):
        try:
            container = Container.create(bundle.data['rec_id'], bundle.data['content'], request.user)
            if 'public' in bundle.data: 
                container.public = bundle.data['public']
                container.save()
                if bundle.data['public']:
                    assign('view_container', Group.objects.get(id=PUBLIC_GROUP_ID), container)
            #===================================================================
            # if 'file_id' in bundle.data:
            #    file_sub = request.FILES['file_id']
            #    sub = Submission.objects.create()
            #    sub.content.save(sub.timestap.strftime('%Y-%m-%d%H-%M-%S')+file_sub._name, file_sub)
            #    container.submission = sub
            #    container.save()
            #===================================================================
                
        except: 
            raise ImmediateHttpResponse(HttpBadRequest())
        assign('view_container',request.user, container)
        assign('change_container',request.user, container)
        assign('delete_container',request.user, container)
        assign('admin_container',request.user, container)
        assign('ownership_container',request.user, container)
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
    
    def deserialize(self, request, data, format=None):
        if not format:
            format = request.META.get('CONTENT_TYPE', 'application/json')

        if format == 'application/x-www-form-urlencoded':
            return request.POST

        if format.startswith('multipart'):
            data = request.POST.copy()
            data.update(request.FILES)

            return data

        return super(ModelResource, self).deserialize(request, data, format)
