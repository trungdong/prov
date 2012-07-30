from django import template
from django.contrib.auth.models import User
import logging

register = template.Library()

@register.simple_tag
def status_label(perms, bundle):
    if 'ownership_container' in perms:
        return '<span class="label label-inverse">Owned</span>'
    elif User.objects.get(id=-1).has_perm('view_container', bundle):
        return '<span class="label label-info">Public</span>'
    else:
        return '<span class="label label-success">Delegated</span>'