from models import PDAccount, PDRecord
from django.http import HttpResponse
import simplejson
from django.shortcuts import render_to_response
from django.template.context import RequestContext

def get_prov_json(request):
    from provdjango.provserver.test.testModel import Test
    graph = Test.build_prov_graph()
    from models import save_records
    account = save_records(graph)
    
    if 'id' in request.GET:
        entity_id = request.GET.get('id')
        records = PDRecord.objects.filter(rec_id=entity_id)
        accounts = set()
        for record in records:
            accounts.add(record.account)
        # TODO Deal with records from multiple account
        if accounts:
            return HttpResponse(content='{id : %s}' % entity_id, mimetype='application/json')
        return HttpResponse(content='{Not found}', mimetype='application/json')
    else:
        account = PDAccount.objects.get()
        graph2 = account.get_PROVContainer()
        return render_to_response('provserver/test.html', {'input' : simplejson.dumps(graph.to_provJSON(), indent=4),
                                                           'output' : simplejson.dumps(graph2.to_provJSON(), indent=4)},
                                  context_instance=RequestContext(request))
#        return HttpResponse(content=simplejson.dumps(graph.to_provJSON(), indent=4), mimetype='application/json')

