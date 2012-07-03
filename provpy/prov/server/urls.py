from django.conf.urls.defaults import patterns, include, url
from django.contrib.auth.views import login

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('server.views',
    # Examples:
    # url(r'^$', 'provdjango.views.home', name='home'),
    # url(r'^provdjango/', include('provdjango.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
    
    (r'^get$', 'get_prov_json'),
    (r'register$', 'registration'),
)
urlpatterns+= patterns('',
                (r'^home', 'django.contrib.auth.views.login', 
                 {'template_name': 'server/home.html'}),
                )
