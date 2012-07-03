from models import PDAccount, PDRecord, save_records
from django.http import HttpResponse
from django.contrib.auth.models import User
import json
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from prov.model import ProvContainer
from prov.server.forms import ProfileForm
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response


def get_prov_json(request):
    from prov.model.test import examples 
    g1 = examples.w3c_publication_1()
#    account = save_records(g1)
    
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
        account = PDAccount.objects.get(id=1)
        g2 = account.get_graph()
        return render_to_response('server/test.html', {'json_1' : json.dumps(g1, cls=ProvContainer.JSONEncoder, indent=4),
                                                       'json_2' : json.dumps(g2, cls=ProvContainer.JSONEncoder, indent=4),
                                                       'asn_1': g1.get_asn(),
                                                       'asn_2': g2.get_asn()},
                                  context_instance=RequestContext(request))
#        return HttpResponse(content=simplejson.dumps(graph.to_provJSON(), indent=4), mimetype='application/json')

def registration(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST)
        if form.is_valid():
            #import logging
            #logging.debug("validated")
            user=User.objects.create_user(username=form.cleaned_data['username'],
                                     password=form.cleaned_data['password'])
            return HttpResponseRedirect('/prov/home')
        else:
            return render_to_response('server/register.html',{'form': form}, 
                                      context_instance=RequestContext(request))
        
    form = ProfileForm()
    return render_to_response('server/register.html', {'form': form}, context_instance=RequestContext(request))

    