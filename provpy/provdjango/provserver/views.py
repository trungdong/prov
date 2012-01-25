from models import PDAccount, PDRecord
from django.http import HttpResponse

def get_prov_json(request):
#    from provdjango.provserver.test.testModel import Test
#    graph = Test.build_prov_graph()
#    save_records(graph)
    
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
        graph = account.get_PROVContainer()
        return HttpResponse(content=graph.to_provJSON(), mimetype='application/json')

