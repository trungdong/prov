import json
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext
from django.utils.datastructures import MultiValueDictKeyError
from tastypie.models import ApiKey
from prov.model import ProvBundle
from prov.model.graph import prov_to_dot
from prov.persistence.models import PDBundle 
from prov.server.forms import ProfileForm


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
                PDBundle.objects.get(id=rid).delete()
                message = 'The bundle with ID ' + rid + ' was successfully deleted.'
            except MultiValueDictKeyError:
                prov_bundle = json.loads(request.POST['content'], cls=ProvBundle.JSONDecoder)
                pdbundle = PDBundle.create(request.POST['rec_id'], request.POST['asserter'], request.user)
                pdbundle.save_bundle(prov_bundle)
                message = 'The bundle was successfully created with ID ' + `pdbundle.id` + "."
            
        return render_to_response('server/profile.html', 
                                  {'user': request.user.username,
                                   'bundles': request.user.pdbundle_set.all(),
                                   'message': message,
                                   'logged': True},
                                  context_instance=RequestContext(request))

@login_required
def bundle_detail(request, bundle_id):
    pdBundle = get_object_or_404(PDBundle, pk=bundle_id)
    prov_g = pdBundle.get_prov_bundle() 
    prov_n = prov_g.get_provn()
    prov_json = json.dumps(prov_g, indent=4, cls=ProvBundle.JSONEncoder) 
    return render_to_response('server/detail.html',
                              {'logged': True, 'bundle': pdBundle, 'prov_n': prov_n, 'prov_json': prov_json},
                              context_instance=RequestContext(request))
    
def bundle_svg(request, bundle_id):
    pdBundle = get_object_or_404(PDBundle, pk=bundle_id)
    prov_g = pdBundle.get_prov_bundle()
    dot = prov_to_dot(prov_g)
    svg_content = dot.create(format='svg')
    return HttpResponse(content=svg_content, mimetype='image/svg+xml')
    
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
