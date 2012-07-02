from django.contrib.auth.models import User
from tastypie import fields
from tastypie.authorization import Authorization, DjangoAuthorization
from tastypie.authentication import BasicAuthentication
from tastypie.resources import ModelResource
from models import PDAccount
from prov.model import ProvContainer

class UserResource(ModelResource):
    class Meta:
        queryset = User.objects.all()
        fields = ['username']

class AccountResource(ModelResource):
    creator = fields.ForeignKey(UserResource, 'owner')

    class Meta:
        queryset = PDAccount.objects.all()
        resource_name = 'account'
        excludes = ['rec_type']
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get', 'post']
        always_return_data = True
        authorization= Authorization()
        authentication = BasicAuthentication()
        
    content = fields.DictField(attribute='content', null=True)
    
    def obj_create(self, bundle, request=None, **kwargs):
        prov_graph = ProvContainer()
        prov_graph._decode_JSON_container(bundle.data['content'])
        
        account = PDAccount.create(bundle.data['rec_id'], bundle.data['asserter'], request.user)
        account.save_graph(prov_graph)

        bundle.obj = account
        return bundle
        
    def dehydrate_content(self, bundle):
        if self.get_resource_uri(bundle) == bundle.request.path:
            prov_graph = bundle.obj.get_graph()
            return prov_graph._encode_JSON_container()
        else:
            return None
