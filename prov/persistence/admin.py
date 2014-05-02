"""Django Admin interface for prov.persistence

@author: Trung Dong Huynh <trungdong@donggiang.com>
@copyright: University of Southampton 2014
"""

from django.contrib import admin
from prov.persistence.models import PDBundle, PDNamespace
from prov.model import PROV_REC_BUNDLE


class PDBundleAdmin(admin.ModelAdmin):
    exclude = ('rec_type',)
    list_display = ('rec_id',)

    def save_model(self, request, obj, form, change):
        obj.rec_type = PROV_REC_BUNDLE
        admin.ModelAdmin.save_model(self, request, obj, form, change)


class PDNamespaceAdmin(admin.ModelAdmin):
    pass


admin.site.register(PDBundle, PDBundleAdmin)
admin.site.register(PDNamespace, PDNamespaceAdmin)
