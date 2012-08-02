'''Django Admin interface for prov.server

@author: Trung Dong Huynh <trungdong@donggiang.com>
@copyright: University of Southampton 2012
'''
from django.contrib import admin
from guardian.admin import GuardedModelAdmin
from prov.server.models import Container


class ContainerAdmin(GuardedModelAdmin):
    pass

admin.site.register(Container, ContainerAdmin)
        