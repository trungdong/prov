from tastypie.authentication import Authentication
from tastypie.authorization import Authorization
from tastypie.authentication import HttpUnauthorized
from tastypie.http import HttpForbidden
from tastypie.exceptions import ImmediateHttpResponse
from django.contrib.auth.models import User
from prov.settings import ANONYMOUS_USER_ID
from models import Container


class AnnonymousAuthentication(Authentication):
    """
    Authenticates only Anonymous users 
    """
    def is_authenticated(self, request, **kwargs):
        request.user = User.objects.get(id=ANONYMOUS_USER_ID)
        return True
    
    
class CustomAuthorization(Authorization):
    """
    Authorization of the RESTfull web service
    with object permissions provided by 'django-guardian' package
    """
    
    def methodToPerms(self, method):
        if method == 'GET':
            return 'server.view_container'
        if method == 'POST' or method == 'PUT':
            return 'server.change_container'
        if method == 'DELETE':
            return 'server.delete_container'
        return None
    
    def checkRequest(self, path):
        try:
            if int(path[-2]):
                return True
        except:
            pass
        return False 
    
    def is_authorized(self, request, object=None): #@ReservedAssignment
        path = request.path.split('/');
        if not self.checkRequest(path=path):
            return True
        if request.user.has_perm(self.methodToPerms(request.method), Container.objects.get(id=int(path[-2]))):
            return True
        else:    
            raise ImmediateHttpResponse(HttpForbidden())
    
    def apply_limits(self, request, object_list):
        return filter(lambda obj: request.user.has_perm(self.methodToPerms(request.method),obj), object_list)


"""
Authentication classes imported from tastypie developers version
for compatibility with official one.
"""

class MultiAuthentication(object):
    """
    An authentication backend that tries a number of backends in order.
    """
    def __init__(self, *backends, **kwargs):
        super(MultiAuthentication, self).__init__(**kwargs)
        self.backends = backends

    def is_authenticated(self, request, **kwargs):
        """
        Identifies if the user is authenticated to continue or not.

        Should return either ``True`` if allowed, ``False`` if not or an
        ``HttpResponse`` if you need something custom.
        """
        unauthorized = False

        for backend in self.backends:
            check = backend.is_authenticated(request, **kwargs)

            if check:
                if isinstance(check, HttpUnauthorized):
                    unauthorized = unauthorized or check
                elif check is True:
                    request._authentication_backend = backend
                    return check

        return unauthorized

    def get_identifier(self, request):
        """
        Provides a unique string identifier for the requestor.

        This implementation returns a combination of IP address and hostname.
        """
        try:
            return request._authentication_backend.get_identifier(request)
        except AttributeError:
            return 'nouser'