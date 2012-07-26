from django.conf.urls.defaults import patterns

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
    
    (r'register$', 'registration'),
    (r'home$', 'profile'),
    (r'bundles/(?P<container_id>\d+)/$', 'bundle_detail'),
    (r'bundles/(?P<container_id>\d+).svg$', 'bundle_svg'),
    (r'create$', 'create'),
    (r'auth$', 'auth'),
    (r'auth/help$', 'auth_help'),
    (r'admin/(?P<container_id>\d+)/$', 'admin_bundle')
)
urlpatterns+= patterns('',
                (r'login$', 'django.contrib.auth.views.login', 
                 {'template_name': 'server/login.html'}),
                 (r'^logout$', 'django.contrib.auth.views.logout_then_login')
                )
