from tastypie.authentication import Authentication
from tastypie.authorization import Authorization
from prov.server.models import PDAccount

class CustomAuthentication(Authentication):
    """
    Authenticates only Anonymous users 
    """
    def is_authenticated(self, request, **kwargs):
        if request.user and request.user.is_anonymous():
            return True
        return False
    
    
class CustomAuthorization(Authorization):
    """
    Authorization of the RESTfull web service
    with object permissions provided by 'django-guardian' package
    """
    def apply_limits(self, request, object_list):
        #return get_objects_for_user(user= request.user, perms=self.methodToPerms(request.method))
#         Does a per-object check that "can't" be expressed as part of a
#         ``QuerySet``. This helps test that all objects in the ``QuerySet``
#         aren't loaded & evaluated, only results that match the request.
#        final_list = []
#        for obj in object_list:
#            if request.user.has_perm(request.method,obj):
#                final_list.append(obj)
#        return final_list
        return filter(lambda obj: request.user.has_perm(request.method,obj), object_list)
    
    def is_authorized(self, request, object=None): #@ReservedAssignment
        path = request.path.split('/');
        if self.checkRequest(path=path):
            try:
                return request.user.has_perm(request.method, PDAccount.objects.get(id=int(path[-2])))
            except:
                pass
        return True
    
    def methodToPerms(self, method):
        if method == 'GET':
            return 'server.view_pdaccount'
        if method == 'POST' or method == 'PUT':
            return 'server.change_pdaccount'
        if method == 'DELETE':
            return 'server.delete_pdaccount'
        return None
    
    def checkRequest(self, path):
        try:
            if int(path[-2]):
                return True
        except:
            pass
        return False 
        