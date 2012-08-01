import json
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template.context import RequestContext
from django.utils.datastructures import MultiValueDictKeyError
from tastypie.models import ApiKey
from guardian.shortcuts import *#assign, remove_perm, get_perms_for_model, get_objects_for_user, get_users_with_perms
from prov.model import ProvBundle
from prov.model.graph import prov_to_dot
from prov.server.forms import ProfileForm
from models import Container, Submission
#from prov.persistence.models import PDBundle 

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
        if request.method == 'POST':
            if 'delete_id' in request.POST:
                container_id = request.POST['delete_id']
                container = get_object_or_404(Container, pk=container_id)
                if not request.user.has_perm('delete_container', container):
                    return render_to_response('server/403.html', {'logged': True}, context_instance=RequestContext(request))
                messages.success(request, 'The bundle with ID ' + container.content.rec_id + ' was successfully deleted.')
                container.delete()
            elif 'rec_id' and 'content' in request.POST:                
                try:
                    bundle_dict = json.loads(request.POST['content'])
                    container = Container.create(request.POST['rec_id'], bundle_dict, request.user)
                    if 'file_id' in request.FILES:
                        file_sub = request.FILES['file_id']
                        sub = Submission.objects.create()
                        sub.content.save(sub.timestap.strftime('%Y-%m-%d%H-%M-%S')+file_sub._name, file_sub)
                        container.submission = sub
                        container.save()
                    messages.success(request, 'The bundle was successfully created with ID ' + str(container.content.rec_id) + ".")
                    assign('view_container',request.user, container)
                    assign('change_container',request.user, container)
                    assign('delete_container',request.user, container)
                    assign('admin_container',request.user, container)
                    assign('ownership_container',request.user, container)                    
                except:
                    messages.error(request, 'The bundle provided has wrong syntax.')
                    return redirect(create)
                
        perms = get_perms_for_model(Container)
        l_perm = []
        for i in range(len(perms)):
            l_perm.append(perms[i].codename)
        
        return render_to_response('server/profile.html', 
                                  {'bundles': get_objects_for_user
                                   (user=request.user, 
                                    perms = l_perm, klass=Container, any_perm=True).order_by('id'),
                                   'logged': True },
                                  context_instance=RequestContext(request))

@login_required
def bundle_detail(request, container_id):
    container = get_object_or_404(Container, pk=container_id)
    if not request.user.has_perm('view_container', container):
        return render_to_response('server/403.html', {'logged': True}, context_instance=RequestContext(request))
    #===========================================================================
    # if request.method == 'POST' and 'json' in request.POST:
    #    prov_bundle = ProvBundle();
    #    try:
    #        prov_bundle._decode_JSON_container(request.POST['json'])
    #    except TypeError:
    #        try: 
    #            prov_bundle = json.loads(request.POST['json'], cls=ProvBundle.JSONDecoder)
    #        except:
    #            messages.error(request, 'The bundle provided has wrong syntax.')
    #            prov_bundle = None
    #    if prov_bundle:
    #        container.content.save_bundle(prov_bundle)
    #        messages.success(request, 'The bundle was successfully saved.')
    #===========================================================================
    prov_g = container.content.get_prov_bundle() 
    prov_n = prov_g.get_provn()
    prov_json = json.dumps(prov_g, indent=4, cls=ProvBundle.JSONEncoder) 
    return render_to_response('server/detail.html',
                              {'logged': True, 'bundle': container, 'prov_n': prov_n, 'prov_json': prov_json},
                              context_instance=RequestContext(request))
    
def bundle_svg(request, container_id):
    container = get_object_or_404(Container, pk=container_id)
    if not request.user.has_perm('view_container', container):
        return render_to_response('server/403.html', {'logged': True}, context_instance=RequestContext(request))
    prov_g = container.content.get_prov_bundle()
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
                messages.success(request, 'The API key was successfully deleted.')
            elif action == 'generate':
                if not api_key:
                    api_key = ApiKey.objects.create(user=request.user)
                else:
                    api_key.key = ApiKey.generate_key(api_key)
                    api_key.save()
                messages.success(request, 'The API key was successfully generated.')
        except MultiValueDictKeyError:
            pass

    if api_key:
        key = api_key.key
        date = api_key.created
        
    return render_to_response('server/auth.html',{'logged': True, 'key': key, 'date': date,},
                              context_instance=RequestContext(request))


def auth_help(request):
    if request.user.is_anonymous():
        logged = False
    else:
        logged = True
    return render_to_response('server/auth_help.html',{'logged': logged})

def _update_perms(target, role, container):
        perms = get_perms_for_model(Container)
        l_perm = []
        for i in range(len(perms)):
            l_perm.append(perms[i].codename)
        for permission in l_perm:
                remove_perm(permission, target, container)
        if role == 'none':
            if target == Group.objects.get(name='public'):
                container.public = False
                container.save()
            return
        assign('view_container', target, container)
        if role == 'Reader':
            if target == Group.objects.get(name='public'):
                container.public = True
                container.save()
            return
        assign('change_container', target, container)
        if role == 'Contributor':
            return
        assign('delete_container', target, container)
        if role == 'Editor':
            return
        assign('admin_container', target, container)
            
@login_required
def admin_bundle(request, container_id):
    container = get_object_or_404(Container, pk=container_id)
    if not request.user.has_perm('admin_container', container):
        return render_to_response('server/403.html', {'logged': True}, context_instance=RequestContext(request))
    if request.method == 'POST':
        try:
            name = request.POST['name']
            role = request.POST['role']
            type = request.POST['type']
            if role not in ('none','Reader','Contributor','Editor','Administrator'):
                raise Exception
            if type == 'user':
                target = User.objects.get(username=name)
                _update_perms(target, role, container)
            elif type == 'group':
                target = Group.objects.get(name=name)
                _update_perms(target, role, container)
        except User.DoesNotExist:
            messages.error(request, 'User does not exist!')
        except Group.DoesNotExist:
            messages.error(request, 'Group does not exist!')
        except Exception:
            pass

    initial_list = get_users_with_perms(container, attach_perms = True, with_group_users=False)
    users={}
    for user in initial_list:
        users[user] = len(initial_list[user])
    initial_list = get_groups_with_perms(container, attach_perms=True)
    public = False
    groups={}
    for group in initial_list:
        groups[group] = len(initial_list[group])
        if group.name == 'public':
            public = True
    all_users=[]
    for user in User.objects.all():
        if user.id != -1:
            all_users.append(user.username)
    all_users.sort()
    all_groups=[]
    for group in Group.objects.all():
        if group.name != 'public':
            all_groups.append(group.username)
    all_groups.sort()    
    return render_to_response('server/admin.html',
                              {'logged': True, 'bundle': container, 'public': public,
                               'users': users, 'groups': groups,
                               'all_users': all_users, 'all_groups': all_groups},
                              context_instance=RequestContext(request))
