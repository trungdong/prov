from django.contrib.auth.models import User
from tastypie import fields
from tastypie.authorization import Authorization
from tastypie.authentication import BasicAuthentication
from tastypie.resources import ModelResource
from models import PDBundle
from prov.model import ProvBundle

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
        list_allowed_methods = ['get', 'post', 'delete']
        detail_allowed_methods = ['get', 'post', 'delete']
        always_return_data = True
        authorization= Authorization()
        authentication = BasicAuthentication()
        
    content = fields.DictField(attribute='content', null=True)
    owner = fields.CharField(attribute='owner', null=True)
    
    def obj_create(self, bundle, request=None, **kwargs):
        prov_bundle = ProvBundle()
        prov_bundle._decode_JSON_container(bundle.data['content'])
        
        account = PDBundle.create(bundle.data['rec_id'], bundle.data['asserter'], request.user)
        account.save_bundle(prov_bundle)

        bundle.obj = account
        return bundle
        
    def dehydrate_content(self, bundle):
        if self.get_resource_uri(bundle) == bundle.request.path:
            prov_graph = bundle.obj.get_prov_bundle()
            return prov_graph._encode_JSON_container()
        else:
            return None
