from models import *
import simplejson
from django.http import HttpResponse

def get_prov_json(request):
    if 'id' in request.GET:
        entity_id = request.GET.get('id')
        records = Record.objects.filter(rec_id=entity_id)
        accounts = set()
        for record in records:
            accounts.add(record.account)
        # TODO Deal with records from multiple account
        if accounts:
            return HttpResponse(content='{id : %s}' % entity_id, mimetype='application/json')
        return HttpResponse(content='{Not found}', mimetype='application/json')
    else:
        accounts = ProvDJAccount.objects.all()
        
        return HttpResponse(content=accounts[0].to_provJSON(), mimetype='application/json')

