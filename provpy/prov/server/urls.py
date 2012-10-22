from django.conf.urls.defaults import patterns
from django.views.generic.base import TemplateView

urlpatterns = patterns('server.views',
    (r'^register/$', 'registration'),
    (r'^bundles/$', 'list_bundles'),
    (r'^bundles/(?P<container_id>\d+)/$', 'bundle_detail'),
    (r'^bundles/(?P<container_id>\d+).svg$', 'bundle_svg'),
    (r'^bundles/create/$', 'create_bundle'),
    (r'^bundles/admin/(?P<container_id>\d+)/$', 'admin_bundle'),
    (r'^apikey/$', 'api_key'),
    (r'^help/apikey/$', TemplateView.as_view(template_name='server/api_key_help.html')),
    (r'^help/oauth/$', TemplateView.as_view(template_name='server/oauth_help.html')),
    (r'^help/search/$', TemplateView.as_view(template_name='server/search_help.html')),
    (r'^apps/$', 'manage_apps'),
    (r'^apps/register/$', 'register_app'),
    (r'^contact/$', 'contact'),
    (r'^about/$', TemplateView.as_view(template_name='server/about.html')),
    (r'^$', TemplateView.as_view(template_name='server/dashboard.html')),
)

urlpatterns+= patterns('',
    (r'^login/$', 'django.contrib.auth.views.login', {'template_name': 'server/login.html'}),
    (r'^logout/$', 'django.contrib.auth.views.logout', {'next_page': '/'})
)
