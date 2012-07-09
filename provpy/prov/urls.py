from django.conf.urls.defaults import patterns, include, url
from tastypie.api import Api
from server.api import AccountResource

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

# Tasty Pie API configurations
v0_api = Api(api_name='v0')
v0_api.register(AccountResource())
#v0_api.register(UserResource())


urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'provdjango.views.home', name='home'),
    # url(r'^provdjango/', include('provdjango.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
    (r'^prov/', include('server.urls')),
    (r'^api/', include(v0_api.urls)),
)
