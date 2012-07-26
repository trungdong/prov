from tastypie import fields
from tastypie.authentication import Authentication, ApiKeyAuthentication
from tastypie.authorization import Authorization
from prov.server.auth import AnnonymousAuthentication, MultiAuthentication, CustomAuthorization
from tastypie.resources import ModelResource
from guardian.shortcuts import assign
from prov.model import ProvBundle
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.http import HttpBadRequest
from models import Container
from prov.persistence.models import save_bundle

#===============================================================================
# class UserResource(ModelResource):
#    class Meta:
#        queryset = User.objects.all()
#        fields = ['username']
#===============================================================================

class ContainerResource(ModelResource):
#    creator = fields.ForeignKey(UserResource, 'owner')

    class Meta:
        queryset = Container.objects.all()
        resource_name = 'container'
        excludes = ['content']
        list_allowed_methods = ['get', 'post', 'delete', 'put']
        detail_allowed_methods = ['get', 'post', 'delete', 'put']
        always_return_data = True
        authorization = Authorization() #CustomAuthorization()
        authentication = MultiAuthentication(ApiKeyAuthentication(), AnnonymousAuthentication())
        
    editable = fields.BooleanField()
    prov_json = fields.DictField(attribute='prov_json', null=True)
    
    def obj_create(self, bundle, request=None, **kwargs):
        prov_bundle = ProvBundle()
        try:
            prov_bundle._decode_JSON_container(bundle.data['prov_json'])
            pdbundle = save_bundle(prov_bundle)
            # TODO: Get the value of the 'public' variable from 'bundle' and set it here 
            container = Container.objects.create(owner=request.user, content=pdbundle)
        except:
            raise ImmediateHttpResponse(HttpBadRequest())
        assign('view_pdbundle',request.user, container)
        assign('change_pdbundle',request.user, container)
        assign('delete_pdbundle',request.user, container)
        assign('admin_pdbundle',request.user, container)
        assign('ownership_pdbundle',request.user, container)
        bundle.obj = container
        return bundle
    
    
    def dehydrate_content(self, bundle):
        if self.get_resource_uri(bundle) == bundle.request.path:
            prov_bundle = bundle.obj.content.get_prov_bundle()
            return prov_bundle._encode_JSON_container()
        else:
            return None
        
    def dehydrate_editable(self, bundle):
        return bundle.request.user.has_perm('change_pdbundle', bundle)
