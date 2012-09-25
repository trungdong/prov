from tastypie import fields
from prov.server.auth import MultiAuthentication, CustomAuthorization
from tastypie.resources import ModelResource
from guardian.shortcuts import assign
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.http import HttpBadRequest
from models import Container,Submission, License
from prov.model import ProvBundle
from django.contrib.auth.models import Group
from prov.settings import PUBLIC_GROUP_ID
from urllib2 import urlopen
from json import loads
from prov.server.search import search_id, search_literal, search_name, search_timeframe, search_any_text_field

class ContainerResource(ModelResource):
    
    class Meta:
        queryset = Container.objects.all()
        resource_name = 'bundle'
        excludes = ['content', 'url']
        list_allowed_methods = ['get', 'post', 'delete']
        detail_allowed_methods = ['get', 'post', 'delete']
        always_return_data = True
        authorization = CustomAuthorization()
        authentication = MultiAuthentication()
#        limit = 0        
    prov_json = fields.DictField(attribute='prov_json', null=True)
#    original_file = fields.FileField(attribute='original', null=True)
    
    def obj_create(self, bundle, request=None, **kwargs):
        '''
        Function to create a bundle via the API.
        Arguments (in JSON) are as follows:
            rec_id - the name for the Bundle (REQUIRED)
            content - the content in JSON format (or URL REQUIRDE)
            URL - a URL reference to the JSON content of the bundle * (OR content REQUIRED)
            public - indicator whether the Bundle to be made public, False if not provided
            licenses - a list of names corresponding to License objects in the DB
            submission - a file submitted which represents the Bundle **
        
        * - The URL is only opened and it's content parsed if and only if 'content' is empty
        ** - The file content is not parsed at all, it is just saved for later usage and
             if file is submitted the HTTP call should be in 'multipart' encoding format.
        '''
        
        try:
            '''Try to read the content else download and parse the URL file '''
            prov_bundle = ProvBundle()
            if bundle.data['content']:
                prov_bundle._decode_JSON_container(bundle.data['content'])
            else:
                source = urlopen(bundle.data['url'], timeout=5)
                content = source.read()
                source.close()
                prov_bundle._decode_JSON_container(loads(content))
            container = Container.create(bundle.data['rec_id'], prov_bundle, request.user)
        except: 
            raise ImmediateHttpResponse(HttpBadRequest())

        save = False
        if 'public' in bundle.data: 
            container.public = bundle.data['public']
            save = True
            if bundle.data['public']:
                assign('view_container', Group.objects.get(id=PUBLIC_GROUP_ID), container) 
                           
        if 'licenses' in bundle.data:
            for title in bundle.data['licenses']:
                try:
                    lic = License.objects.get(title=title)
                    container.license.add(lic)
                    save = True
                except License.DoesNotExist:
                    pass
        
        if 'submission' in request.FILES:
            file_sub = request.FILES['submission']
            sub = Submission.objects.create()
            sub.content.save(sub.timestamp.strftime('%Y-%m-%d%H-%M-%S')+file_sub._name, file_sub)
            container.submission = sub
            save = True
            
        if 'url' in bundle.data:
            container.url = bundle.data['url']
            save = True
            
        if save:
            container.save()
        bundle.obj = container
        return bundle
    
    def dehydrate_prov_json(self, bundle):
        ''' Sets the prov_json field to the appropriate JSON content of the bundle '''
        
        if self.get_resource_uri(bundle) == bundle.request.path:
            prov_bundle = bundle.obj.content.get_prov_bundle()
            return prov_bundle._encode_JSON_container()
        else:
            return None
        
    def dehydrate_editable(self, bundle):
        ''' Sets the editable field to the permission rule '''
        return bundle.request.user.has_perm('change_container', bundle)
    
    def get_object_list(self, request):
        ''' Method to return the list of objects via GET method to the Resource (not concrete).
        If the variable 'search_type' is present returns the appropriate bundles
        which match the searching query. 'search_type' can have several values:
            'name' - accompanied by 'q_str' variable containing the search string
                     returns all Bundles containing the q_str in their name.
            'id' - accompanied by 'q_str' variable containing the search string
                           returns all Bundles containing a record that contains the q_str in their name.
            'type' - accompanied by 'q_str' variable containing the search string
                          returns all Bundles containing a literal attribute with type prov:type
                          and value containing q_str.
            'time' - accompanied by 'start' and/or 'end' variable containing the times
                          returns all Bundles with within the time frame [strat:end]
            'any' - accompanied by 'q_str' variable containing the search string
                     returns all Bundles containing anything matching q_str.
        '''
        
        search_type = request.GET.get('search_type', None)
        if not search_type:    
            return ModelResource.get_object_list(self, request)
        try:
            if search_type == 'name':
                result = search_name(request.GET.get('q_str', None))
            elif search_type == 'id':
                result = search_id(request.GET.get('q_str', None))
            elif search_type == 'type':
                result = search_literal(request.GET.get('literal', None) + 'prov#type', request.GET.get('q_str', None))
            elif search_type == 'time': 
                result = search_timeframe(request.GET.get('start', None), request.GET.get('end', None))
            elif search_type == 'any':
                result = search_any_text_field(request.GET.get('q_str', None))
            else:
                raise ImmediateHttpResponse(HttpBadRequest())
            return result
        except:
            raise ImmediateHttpResponse(HttpBadRequest())
    
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
        
        '''
        This method is overridden only for the purpose of accepting a 'multipart'
        request for the purpose of receiving a 'submission' file.
        Changes of the original method are enclosed in <--- CHANGE ---> tags. (commented)
        '''
        
        '''<--- CHANGE ---> '''
        '''
        For some reason without accessing the variable request it fails,
        so without the debugging line print it won't work
        '''
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
        ''' <--- CHANGE ---> '''
        
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
        