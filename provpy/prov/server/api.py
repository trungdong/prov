from tastypie import fields
from prov.server.auth import MultiAuthentication, CustomAuthorization
from tastypie.resources import ModelResource
from guardian.shortcuts import assign
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.http import HttpBadRequest
from models import Container,Submission
from prov.model import ProvBundle
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
        authentication = MultiAuthentication()        
    prov_json = fields.DictField(attribute='prov_json', null=True)
#    original_file = fields.FileField(attribute='original', null=True)
    
    def obj_create(self, bundle, request=None, **kwargs):
        try:
            prov_bundle = ProvBundle()
            prov_bundle._decode_JSON_container(bundle.data['content'])
            container = Container.create(bundle.data['rec_id'], prov_bundle, request.user)
            save = False
            if 'public' in bundle.data: 
                container.public = bundle.data['public']
                save = True
                if bundle.data['public']:
                    assign('view_container', Group.objects.get(id=PUBLIC_GROUP_ID), container)
            
            if 'licenses' in bundle.data:
                for l in bundle.data['licenses']:
                    import logging
                    logging.debug(l)
            if 'submission' in request.FILES:
                file_sub = request.FILES['submission']
                sub = Submission.objects.create()
                sub.content.save(sub.timestamp.strftime('%Y-%m-%d%H-%M-%S')+file_sub._name, file_sub)
                container.submission = sub
                save = True
                
            if save:
                container.save()
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
    
    #===========================================================================
    # def strip_multiForm(self, raw_data):
    #    start = raw_data.find('{')
    #    end = raw_data.rfind('}')
    #    import logging
    #    logging.debug(raw_data[end:])
    #    return raw_data[start:end+1]
    #===========================================================================
    
    def post_list(self, request, **kwargs):
        from tastypie import http
        from tastypie.utils import dict_strip_unicode_keys
        """
        Creates a new resource/object with the provided data.

        Calls ``obj_create`` with the provided data and returns a response
        with the new resource's location.

        If a new resource is created, return ``HttpCreated`` (201 Created).
        If ``Meta.always_return_data = True``, there will be a populated body
        of serialized data.
        """
        import logging
        logging.debug(request.FILES)
        if request.META.get('CONTENT_TYPE').startswith('multipart'):
            request.META['CONTENT_TYPE'] = 'application/json'
            #===================================================================
            # if ' name' in request.POST:
            #    data = self.strip_multiForm(request.POST[' name'])
            #    logging.debug('SDADSA')
            #    #logging.debug(data[1098] + data[1099] + data[1100] + data[1101])
            # else:
            #    data = request.POST['data']
            #===================================================================
            if not 'data' in request.POST:
                return ImmediateHttpResponse(HttpBadRequest)
            deserialized = self.deserialize(request, request.POST['data'], format=request.META.get('CONTENT_TYPE', 'application/json'))
            
        else:
            deserialized = self.deserialize(request, request.raw_post_data, format=request.META.get('CONTENT_TYPE', 'application/json'))
        deserialized = self.alter_deserialized_detail_data(request, deserialized)
        bundle = self.build_bundle(data=dict_strip_unicode_keys(deserialized), request=request)
        updated_bundle = self.obj_create(bundle, request=request, **self.remove_api_resource_names(kwargs))
        location = self.get_resource_uri(updated_bundle)

        if not self._meta.always_return_data:
            return http.HttpCreated(location=location)
        else:
            updated_bundle = self.full_dehydrate(updated_bundle)
            updated_bundle = self.alter_detail_data_to_serialize(request, updated_bundle)
            return self.create_response(request, updated_bundle, response_class=http.HttpCreated, location=location)
        