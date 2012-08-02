from django.conf.urls.defaults import patterns
from django.views.generic.simple import direct_to_template

urlpatterns = patterns('server.views',
    (r'register$', 'registration'),
    (r'home$', 'profile'),
    (r'bundles/(?P<container_id>\d+)/$', 'bundle_detail'),
    (r'bundles/(?P<container_id>\d+).svg$', 'bundle_svg'),
    (r'create$', 'create'),
    (r'auth$', 'auth'),
    (r'auth/help$', direct_to_template, {'template': 'server/auth_help.html'}),
    (r'admin/(?P<container_id>\d+)/$', 'admin_bundle')
)
urlpatterns+= patterns('',
                (r'login$', 'django.contrib.auth.views.login', 
                 {'template_name': 'server/login.html'}),
                 (r'^logout$', 'django.contrib.auth.views.logout_then_login')
                )
