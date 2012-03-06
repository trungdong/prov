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
    
#    def get_object_list(self, request):
#        return ModelResource.get_object_list(self, request)
#    
#    def obj_get(self, request=None, **kwargs):
#        return ModelResource.obj_get(self, request=request, **kwargs)
    
    def obj_create(self, bundle, request=None, **kwargs):
        prov_graph = ProvContainer()
        prov_graph._decode_JSON_container(bundle.data['content'])
        
        account = PDAccount.create(bundle.data['rec_id'], bundle.data['asserter'])
        account.save_graph(prov_graph)

        bundle.obj = account
        return bundle
        
    def dehydrate_content(self, bundle):
        if self.get_resource_uri(bundle) == bundle.request.path:
            prov_graph = bundle.obj.get_graph()
            return prov_graph._encode_JSON_container()
        else:
            return None
