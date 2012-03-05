from tastypie import fields
from tastypie.authorization import Authorization
from tastypie.resources import ModelResource
from models import PDAccount
from provdjango.provmodel import ProvContainer
import json


class AccountResource(ModelResource):
    class Meta:
        queryset = PDAccount.objects.all()
        resource_name = 'account'
        excludes = ['rec_type']
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get', 'post']
        authorization= Authorization()
        
    content = fields.DictField(attribute='content', null=True)
#    json.dumps(prov_graph, cls=ProvContainer.JSONEncoder)
    
    def get_object_list(self, request):
        return ModelResource.get_object_list(self, request)
    
    def obj_create(self, bundle, request=None, **kwargs):
        return ModelResource.obj_create(self, bundle, request=request, **kwargs)
    
    def obj_get(self, request=None, **kwargs):
        account = ModelResource.obj_get(self, request=request, **kwargs)
        prov_graph = account.get_PROVContainer()
        self.content = prov_graph._encode_JSON_container()
        return account
    
    def dehydrate(self, bundle):
        prov_graph = bundle.obj.get_PROVContainer()
#        bundle.data['content'] = prov_graph._encode_JSON_container()
        self.content = prov_graph._encode_JSON_container()
        return bundle