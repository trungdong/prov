'''Django Admin interface for prov.persistence

@author: Trung Dong Huynh <trungdong@donggiang.com>
@copyright: University of Southampton 2012
'''

from django.contrib import admin
from prov.persistence.models import PDBundle, PDNamespace

class PDBundleAdmin(admin.ModelAdmin):
    pass

class PDNamespaceAdmin(admin.ModelAdmin):
    pass

admin.site.register(PDBundle, PDBundleAdmin)
admin.site.register(PDNamespace, PDNamespaceAdmin)