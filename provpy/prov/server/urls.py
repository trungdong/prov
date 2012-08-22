from django.conf.urls.defaults import patterns
from django.views.generic.simple import direct_to_template

urlpatterns = patterns('server.views',
    (r'^register/$', 'registration'),
    (r'^home/$', direct_to_template, {'template': 'server/dashboard.html'}),
    (r'^bundles/$', 'list_bundles'),
    (r'^bundles/search/$', 'search'),
    (r'^bundles/(?P<container_id>\d+)/$', 'bundle_detail'),
    (r'^bundles/(?P<container_id>\d+).svg$', 'bundle_svg'),
    (r'^bundles/create/$', 'create_bundle'),
    (r'^bundles/admin/(?P<container_id>\d+)/$', 'admin_bundle'),
    (r'^apikey/$', 'api_key'),
    (r'^help/apikey/$', direct_to_template, {'template': 'server/api_key_help.html'}),
    (r'^help/oauth/$', direct_to_template, {'template': 'server/oauth_help.html'}),
    (r'^apps/$', 'manage_apps'),
    (r'^apps/register/$', 'register_app'),
)
urlpatterns+= patterns('',
                (r'^login/$', 'django.contrib.auth.views.login', 
                {'template_name': 'server/login.html'}),
                 (r'^logout/$', 'django.contrib.auth.views.logout_then_login')
                )
