from tastypie import fields
from tastypie.authentication import Authentication, ApiKeyAuthentication
from tastypie.authorization import Authorization
from prov.server.auth import AnnonymousAuthentication, MultiAuthentication, CustomAuthorization
from tastypie.resources import ModelResource
from guardian.shortcuts import assign
from models import PDBundle
from prov.model import ProvBundle
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.http import HttpBadRequest

#===============================================================================
# class UserResource(ModelResource):
#    class Meta:
#        queryset = User.objects.all()
#        fields = ['username']
#===============================================================================

class AccountResource(ModelResource):
#    creator = fields.ForeignKey(UserResource, 'owner')

    class Meta:
        queryset = PDBundle.objects.all()
        resource_name = 'bundle'
        excludes = ['rec_type']
        list_allowed_methods = ['get', 'post', 'delete', 'put']
        detail_allowed_methods = ['get', 'post', 'delete', 'put']
        always_return_data = True
        authorization = Authorization() #CustomAuthorization()
        authentication = MultiAuthentication(ApiKeyAuthentication(), AnnonymousAuthentication())
        
    content = fields.DictField(attribute='content', null=True)
    owner = fields.CharField(attribute='owner', null=True)
    editable = fields.BooleanField()
    
    def obj_create(self, bundle, request=None, **kwargs):
        prov_bundle = ProvBundle()
        try:
            prov_bundle._decode_JSON_container(bundle.data['content'])
            account = PDBundle.create(bundle.data['rec_id'], bundle.data['asserter'], request.user)
        except:
            raise ImmediateHttpResponse(HttpBadRequest())
        account.save_bundle(prov_bundle)
        assign('view_pdbundle',request.user,account)
        assign('change_pdbundle',request.user,account)
        assign('delete_pdbundle',request.user,account)
        assign('admin_pdbundle',request.user,account)
        assign('ownership_pdbundle',request.user,account)
        
        bundle.obj = account
        return bundle
    
#    def apply_authorization_limits(self, request, object_list):
#        return object_list.filter(owner=request.user)
    
    def dehydrate_content(self, bundle):
        if self.get_resource_uri(bundle) == bundle.request.path:
            prov_graph = bundle.obj.get_prov_bundle()
            return prov_graph._encode_JSON_container()
        else:
            return None
        
    def dehydrate_editable(self, bundle):
        return bundle.request.user.has_perm('change_pdbundle', bundle)
