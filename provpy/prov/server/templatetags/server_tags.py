from django import template
from oauth_provider.consts import CONSUMER_STATES
from django.utils.translation import ugettext

register = template.Library()

@register.simple_tag
def status_label(perm, index):
    if perm[index] == 5:
        return '<span class="label label-inverse">Owned</span>'
    elif perm[index] == 0:
        return '<span class="label label-info">Public</span>'
    else:
        return '<span class="label label-success">Delegated</span>'

@register.filter
def get_at_index(list, index):
    return list[index]

@register.simple_tag
def status_to_options(status):
    d = dict(CONSUMER_STATES)
    if status in d:
        result = '<option>' + ugettext(CONSUMER_STATES[status-1][1]) + '</option>\n'
    for key in d.keys():
        if key != status:
            result += '<option>' + ugettext(CONSUMER_STATES[key-1][1]) + '</option>\n'
    return result
