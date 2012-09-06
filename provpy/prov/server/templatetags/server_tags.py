from django import template
from oauth_provider.consts import CONSUMER_STATES
from django.utils.translation import ugettext

register = template.Library()

@register.simple_tag
def status_label(perm):
    if perm == 'o':
        return '<span class="label label-inverse">Owned</span>'
    elif perm == 'p':
        return '<span class="label label-info">Public</span>'
    else:
        return '<span class="label label-success">Delegated</span>'

@register.simple_tag
def status_to_options(status):
    d = dict(CONSUMER_STATES)
    if status in d:
        result = '<option>' + ugettext(CONSUMER_STATES[status-1][1]) + '</option>\n'
    for key in d.keys():
        if key != status:
            result += '<option>' + ugettext(CONSUMER_STATES[key-1][1]) + '</option>\n'
    return result
