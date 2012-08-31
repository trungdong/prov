from prov.server.models import Container    
from prov.persistence.models import PDRecord, LiteralAttribute
from prov.model import PROV_ATTR_TIME, PROV_ATTR_STARTTIME, PROV_ATTR_ENDTIME
from django.db.models import Q
from sets import Set

def _get_containers(rec_set):
    ''' Function returning a django Query_Set of Containers given a Set of record ids.
    The Query_Set is composed of the Containers which contain any of the records in the 'rec_set'
    '''
    
    final_list = Set(rec_set.filter(bundle=None).values_list('id', flat=True))
    temp_list = Set(rec_set.filter(~Q(bundle=None)).values_list('bundle', flat=True))
    while len(temp_list) > 0:
        temp_list = PDRecord.objects.filter(id__in=temp_list)
        final_list = final_list.union(Set(temp_list.filter(bundle=None).values_list('id', flat=True)))
        temp_list = Set(temp_list.filter(~Q(bundle=None)).values_list('bundle', flat=True))
    return Container.objects.filter(content__id__in=final_list)
    
def search_name(q_str=None, exact=False):
    if not q_str:
        return None
    if exact:
        return Container.objects.filter(content__rec_id=q_str)
    return Container.objects.filter(content__rec_id__contains=q_str)
    
def search_id(q_str=None, exact=False):
    if not q_str:
        return None
    if exact:
        init_set = PDRecord.objects.filter(rec_id=q_str)
    else:
        init_set = PDRecord.objects.filter(rec_id__contains=q_str)
    return _get_containers(init_set)

def search_literal(q_str, literal='prov:type', exact=False):
    literal = literal.replace(':', '#')
    if not q_str:
        return None
    if exact:
        lit_set = LiteralAttribute.objects.filter(name__contains=literal, value=q_str)
    else:
        lit_set = LiteralAttribute.objects.filter(name__contains=literal, value__contains=q_str)
    rec_set = Set(lit_set.values_list('record', flat=True))
    return _get_containers(PDRecord.objects.filter(id__in=rec_set))

def search_timeframe(start=None, end=None):
    if not start and not end:
        return None
    from datetime import datetime
    if isinstance(start, datetime):
        start = str(start).replace(" ", "T")
    if isinstance(end, datetime):
        end = str(end).replace(" ", "T")
    if start and end:
        lit_set = LiteralAttribute.objects.filter(Q(prov_type__in=[PROV_ATTR_TIME,PROV_ATTR_STARTTIME,PROV_ATTR_ENDTIME]), 
                                                  Q(value__gte=start) & Q(value__lte=end))                                  
    elif start:
        lit_set = LiteralAttribute.objects.filter(Q(prov_type__in=[PROV_ATTR_TIME,PROV_ATTR_STARTTIME,PROV_ATTR_ENDTIME]), 
                                                  Q(value__gte=start))
    elif end:
        lit_set = LiteralAttribute.objects.filter(Q(prov_type__in=[PROV_ATTR_TIME,PROV_ATTR_STARTTIME,PROV_ATTR_ENDTIME]), 
                                                  Q(value__lte=end))
    rec_set = Set(lit_set.values_list('record', flat=True))
    return _get_containers(PDRecord.objects.filter(id__in=rec_set))

def search_any_text_field(q_str, exact=False):
    if not q_str:
        return None
    if exact:
#        namepsace_set = PDNamespace.objects.filter(Q(prefix=q_str), Q(uri=q_str))
#        record_set = PDRecord.objects.filter(Q(rec_id=q_str), Q(rec_type=q_str))
#        attribute_set = RecordAttribute.objects.filter(prov_type=q_str)
#        literal_set = LiteralAttribute.objects.filter(Q(prov_type=q_str), Q(name=q_str), 
#                                                      Q(value=q_str), Q(data_type=q_str))
        record_set = PDRecord.objects.filter(rec_id=q_str)
        literal_set = LiteralAttribute.objects.filter(value=q_str)
    else: 
#        namepsace_set = PDNamespace.objects.filter(Q(prefix__contains=q_str), Q(uri__contains=q_str))
#        record_set = PDRecord.objects.filter(Q(rec_id__contains=q_str), Q(rec_type__contains=q_str))
#        attribute_set = RecordAttribute.objects.filter(prov_type__contains=q_str)
#        literal_set = LiteralAttribute.objects.filter(Q(prov_type__contains=q_str), Q(name__contains=q_str), 
#                                                      Q(value__contains=q_str), Q(data_type__contains=q_str))
        record_set = PDRecord.objects.filter(rec_id__contains=q_str)
        literal_set = LiteralAttribute.objects.filter(value__contains=q_str)
#    rec_set = Set(namepsace_set.values.list('pdbundle', flat=True))
#    rec_set = rec_set.union(Set(record_set))
#    rec_set = rec_set.union(Set(attribute_set.values_list('record', flat=True)))
#    rec_set = rec_set.union(Set(attribute_set.values_list('value', flat=True)))
#    rec_set = rec_set.union(Set(literal_set.values_list('record', flat=True)))
    rec_set = Set(record_set.values_list('id', flat=True))
    rec_set.union(Set(literal_set.values_list('record', flat=True)))
    return _get_containers(PDRecord.objects.filter(id__in=rec_set))
    
    