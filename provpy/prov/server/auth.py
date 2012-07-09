
import base64
from tastypie.authentication import ApiKeyAuthentication
from django.contrib.auth.models import User


class ProvApiKeyAuthentication(ApiKeyAuthentication):
    def is_authenticated(self, request, **kwargs):
        """
        Checks a user's basic auth credentials against the current
        Django auth backend.

        Should return either ``True`` if allowed, ``False`` if not or an
        ``HttpResponse`` if you need something custom.
        """
        if not request.META.get('HTTP_AUTHORIZATION'):
            return self._unauthorized()

        try:
            (auth_type, data) = request.META['HTTP_AUTHORIZATION'].split()
            if auth_type != 'Prov-API':
                return self._unauthorized()
            user_pass = base64.b64decode(data)
        except:
            return self._unauthorized()

        bits = user_pass.split(':', 1)

        if len(bits) != 2:
            return self._unauthorized()
        
        try:
            user = User.objects.get(username=bits[0])
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            return self._unauthorized()

        request.user = user
        return self.get_key(user, bits[1])
    