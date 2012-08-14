from prov.server.models import Container    
from prov.persistence.models import PDRecord, LiteralAttribute
from django.db.models import Q
from sets import Set

def _get_containers(rec_set):
        final_list = Set(rec_set.filter(bundle=None).values_list('id', flat=True))
        temp_list = Set(rec_set.filter(~Q(bundle=None)).values_list('bundle', flat=True))
        while len(temp_list) > 0:
            temp_list = PDRecord.objects.filter(id__in=temp_list)
            final_list = final_list.union(Set(temp_list.filter(bundle=None).values_list('id', flat=True)))
            temp_list = Set(temp_list.filter(~Q(bundle=None)).values_list('bundle', flat=True))
        return Container.objects.filter(content__id__in=final_list)
    
def search_name(q_str=None, exact=False):
    if q_str:
        if exact:
            return Container.objects.filter(content__rec_id=q_str)
        return Container.objects.filter(content__rec_id__contains=q_str)
    return None

def search_id(q_str=None, exact=False):
    if q_str:
        if exact:
            init_set = PDRecord.objects.filter(rec_id=q_str)
        else:
            init_set = PDRecord.objects.filter(rec_id__contains=q_str)
        return _get_containers(init_set)
    return None

def search_literal(q_str, literal='prov:type', exact=False):
    if q_str:
        if exact:
            init_set = LiteralAttribute.objects.filter(name=literal, value=q_str)
        else:
            init_set = LiteralAttribute.objects.filter(name=literal, value__contains=q_str)
        init_set = Set(init_set.values_list('record', flat=True))
        return _get_containers(PDRecord.objects.filter(id__in=init_set))