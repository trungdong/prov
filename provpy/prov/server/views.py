from models import PDAccount, PDRecord
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from prov.model import ProvContainer
from prov.model import json
from prov.server.forms import ProfileForm
from django.utils.datastructures import MultiValueDictKeyError
from tastypie.models import ApiKey


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
    if(request.user.is_authenticated()):
        return HttpResponseRedirect('/prov/home')
    if request.method == 'POST':
        form = ProfileForm(request.POST)
        if form.is_valid():
            User.objects.create_user(username=form.cleaned_data['username'],
                                            password=form.cleaned_data['password'])
            user = authenticate(username=form.cleaned_data['username'],
                                password=form.cleaned_data['password'])
            login(request,user)
            if form.data['next']:
                return HttpResponseRedirect(form.data['next'])
            return HttpResponseRedirect('/prov/home')
        else:
            return render_to_response('server/register.html',{'form': form, 'next': form.data['next']}, 
                                      context_instance=RequestContext(request))
    form = ProfileForm()
    try:
        next_page = request.GET['next']
    except MultiValueDictKeyError:
        next_page = ''
    return render_to_response('server/register.html', {'form': form, 'next': next_page}, 
                              context_instance=RequestContext(request))
    
@login_required
def profile(request):
        if request.method == 'GET':
            try:
                message = request.GET['message']
            except MultiValueDictKeyError:
                message = None
                
        elif request.method == 'POST':
            try:
                rid = request.POST['delete_id']
                PDAccount.objects.get(id=rid).delete()
                message = 'The bundle with ID ' + rid + ' was successfully deleted.'
            except MultiValueDictKeyError:
                prov_graph = ProvContainer()
                prov_graph._decode_JSON_container(json.loads('{' + request.POST['content']+'}'))
                account = PDAccount.create(request.POST['rec_id'], request.POST['asserter'], request.user)
                account.save_graph(prov_graph)
                message = 'The bundle was successfully created with ID ' + `account.id` + "."
            
        return render_to_response('server/profile.html', 
                                  {'user': request.user.username,
                                   'bundles': request.user.pdaccount_set.all(),
                                   'message': message,
                                   'logged': True},
                                  context_instance=RequestContext(request))

@login_required
def detail(request, bundle_id):
    PDAccount.objects.get(id=bundle_id).get_graph().print_records()
    return render_to_response('server/detail.html',
                              {'logged': True, 'bundle': PDAccount.objects.get(id=bundle_id)},
                              context_instance=RequestContext(request))
    
@login_required
def create(request):
    return render_to_response('server/create.html',{'logged': True},
                              context_instance=RequestContext(request))

@login_required
def auth(request):
    key = None
    date = None
    message = None
    try:
        api_key = ApiKey.objects.get(user=request.user)
    except ApiKey.DoesNotExist:
        api_key = None
    
    if request.method == 'POST':
        try:
            action = request.POST['action']
            if action == 'delete' and api_key:
                api_key.delete()
                api_key = None
                message = 'The API key was successfully deleted.'
            elif action == 'generate':
                if not api_key:
                    api_key = ApiKey.objects.create(user=request.user)
                else:
                    api_key.key = ApiKey.generate_key(api_key)
                message = 'The API key was successfully generated.'
        except MultiValueDictKeyError:
            pass

    if api_key:
        key = api_key.key
        date = api_key.created
        
    return render_to_response('server/auth.html',{'logged': True, 'key': key, 'date': date,
                                                     'message': message},
                              context_instance=RequestContext(request))

@login_required
def auth_help(request):
    return render_to_response('server/auth_help.html',{'logged': True})