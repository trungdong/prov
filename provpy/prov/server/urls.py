from django.conf.urls.defaults import patterns

urlpatterns = patterns('server.views',
    (r'register$', 'registration'),
    (r'home$', 'profile'),
    (r'bundles/(?P<bundle_id>\d+)/$', 'bundle_detail'),
    (r'bundles/(?P<bundle_id>\d+).svg$', 'bundle_svg'),
    (r'create$', 'create'),
    (r'auth$', 'auth'),
    (r'auth/help$', 'auth_help'),
    (r'admin/(?P<bundle_id>\d+)/$', 'admin_bundle')
)
urlpatterns+= patterns('',
                (r'login$', 'django.contrib.auth.views.login', 
                 {'template_name': 'server/login.html'}),
                 (r'^logout$', 'django.contrib.auth.views.logout_then_login')
                )
