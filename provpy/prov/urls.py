from django.conf.urls.defaults import patterns, include, url
from tastypie.api import Api
from server.api import ContainerResource

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

# Tasty Pie API configurations
v0_api = Api(api_name='v0')
v0_api.register(ContainerResource())


urlpatterns = patterns('',
    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    (r'^api/', include(v0_api.urls)),
    (r'^prov/', include('server.urls')),
)
