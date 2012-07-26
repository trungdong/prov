from tastypie import fields
from tastypie.authorization import Authorization
from tastypie.authentication import ApiKeyAuthentication
from tastypie.resources import ModelResource
from models import Container
from prov.model import ProvBundle
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
        list_allowed_methods = ['get', 'post', 'delete']
        detail_allowed_methods = ['get', 'post', 'delete']
        always_return_data = True
        authorization= Authorization()
        authentication = ApiKeyAuthentication()
        
    prov_json = fields.DictField(attribute='prov_json', null=True)
    
    def obj_create(self, bundle, request=None, **kwargs):
        prov_bundle = ProvBundle()
        prov_bundle._decode_JSON_container(bundle.data['prov_json'])
        
        pdbundle = save_bundle(prov_bundle)
        # TODO: Get the value of the 'public' variable from 'bundle' and set it here 
        container = Container.objects.create(owner=request.user, content=pdbundle)

        bundle.obj = container
        return bundle
    
    
    def dehydrate_content(self, bundle):
        if self.get_resource_uri(bundle) == bundle.request.path:
            prov_bundle = bundle.obj.content.get_prov_bundle()
            return prov_bundle._encode_JSON_container()
        else:
            return None
