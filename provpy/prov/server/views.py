import json
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template.context import RequestContext
from django.utils.datastructures import MultiValueDictKeyError
from tastypie.models import ApiKey
from guardian.shortcuts import *#assign, remove_perm, get_perms_for_model, get_objects_for_user, get_users_with_perms
from prov.model import ProvBundle
from prov.model.graph import prov_to_dot
from prov.server.forms import ProfileForm, AppForm, BundleForm
from models import Container
from guardian.decorators import permission_required_or_403
from prov.settings import ANONYMOUS_USER_ID
from oauth_provider.models import Consumer
#from prov.persistence.models import PDBundle 
def registration(request):
    if(request.user.is_authenticated()):
        return redirect(list_bundles)
    if request.method == 'POST':
        form = ProfileForm(request.POST)
        if form.is_valid():
            form.save()
            user = authenticate(username=form.cleaned_data['username'], password=form.cleaned_data['password'])
            login(request,user)
            messages.success(request, 'You have successfully registered!')
            if form.data['next']:
                return redirect(form.data['next'])
            return redirect(list_bundles)
        else:
            for error in form.non_field_errors():
                messages.error(request,error)
            return render_to_response('server/register.html',{'form': form, 'next': form.data['next']}, 
                                      context_instance=RequestContext(request))
    form = ProfileForm()
    if 'next' in request.GET:
        next_page = request.GET['next']
    else:
        next_page = ''
    return render_to_response('server/register.html', {'form': form, 'next': next_page}, 
                              context_instance=RequestContext(request))
    

def list_bundles(request):
        if request.method == 'POST':
            if 'delete_id' in request.POST:
                container_id = request.POST['delete_id']
                container = get_object_or_404(Container, pk=container_id)
                if not request.user.has_perm('delete_container', container):
                    return render_to_response('server/403.html', context_instance=RequestContext(request))
                messages.success(request, 'The bundle with ID ' + container.content.rec_id + ' was successfully deleted.')
                container.delete()
                
        perms = get_perms_for_model(Container)
        l_perm = []
        for i in range(len(perms)):
            l_perm.append(perms[i].codename)
        
        if request.user.is_anonymous() or request.user.id == ANONYMOUS_USER_ID:
            bundles = Container.objects.filter(public = True)
        else:
            bundles = get_objects_for_user(user=request.user, perms = l_perm, klass=Container, any_perm=True).order_by('id')
        return render_to_response('server/private/list_bundles.html', 
                                  {'bundles': bundles},
                                  context_instance=RequestContext(request))

@permission_required_or_403('view_container', (Container, 'pk', 'container_id'))
def bundle_detail(request, container_id):
    container = get_object_or_404(Container, pk=container_id)
    prov_g = container.content.get_prov_bundle() 
    prov_n = prov_g.get_provn()
    prov_json = json.dumps(prov_g, indent=4, cls=ProvBundle.JSONEncoder)
    licenses = container.license.all() 
    return render_to_response('server/private/bundle_detail.html',
                              {'bundle': container, 'prov_n': prov_n, 
                               'prov_json': prov_json, 'license': licenses},
                              context_instance=RequestContext(request))
    
@permission_required_or_403('view_container', (Container, 'pk', 'container_id'))
def bundle_svg(request, container_id):
    container = get_object_or_404(Container, pk=container_id)
    prov_g = container.content.get_prov_bundle()
    dot = prov_to_dot(prov_g)
    svg_content = dot.create(format='svg')
    return HttpResponse(content=svg_content, mimetype='image/svg+xml')
    
@login_required
def create_bundle(request):
    if request.method == 'POST':
        form = BundleForm(request.POST, request.FILES or None)
        if form.is_valid():
            container = form.save(owner=request.user)
            messages.success(request, 'The bundle was successfully created with ID ' + str(container.content.rec_id) + ".")
            return redirect(list_bundles)
        else:
            for error in form.non_field_errors():
                messages.error(request,error)
            return render_to_response('server/private/create_bundle.html',{'form': form}, 
                                      context_instance=RequestContext(request))
    return render_to_response('server/private/create_bundle.html', {'form': BundleForm()},
                              context_instance=RequestContext(request))

@login_required
def api_key(request):
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
        
    return render_to_response('server/private/api_key.html',{'key': key, 'date': date,},
                              context_instance=RequestContext(request))

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
            
@permission_required_or_403('admin_container', (Container, 'pk', 'container_id'))
def admin_bundle(request, container_id):
    container = get_object_or_404(Container, pk=container_id)
    if request.method == 'POST':
        try:
            name = request.POST['name']
            role = request.POST['role']
            perm_type = request.POST['perm_type']
            if role not in ('none','Reader','Contributor','Editor','Administrator'):
                raise Exception
            if perm_type == 'user':
                target = User.objects.get(username=name)
                _update_perms(target, role, container)
            elif perm_type == 'group':
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
    all_users = [user.username for user in User.objects.all() if user.id != ANONYMOUS_USER_ID]
    all_users.sort()
    all_groups=[group.username for group in Group.objects.all() if group.name != 'public']
    all_groups.sort()    
    return render_to_response('server/private/admin_bundle.html',
                              {'bundle': container, 'public': public,
                               'users': users, 'groups': groups,
                               'all_users': all_users, 'all_groups': all_groups},
                              context_instance=RequestContext(request))

@login_required
def register_app(request):
    if request.method == 'POST':
        form = AppForm(request.POST)
        if form.is_valid():
            consumer = form.save()
            consumer.user = request.user
            consumer.generate_random_codes()
            messages.success(request, 'The app ' + consumer.name + ' was successfully added to your list.')
            return redirect(manage_apps)
    else:
        form = AppForm()
    return render_to_response('server/private/register_app.html',
                              {'form': form},
                              context_instance=RequestContext(request))
    
@login_required
def manage_apps(request):
    if request.method == 'POST':
        consumer = get_object_or_404(Consumer, pk=request.POST['app_id'])
        if request.POST['status'] == 'Pending':
            status = 1
        elif request.POST['status'] == 'Accepted':
            status = 2
        elif request.POST['status'] == 'Canceled':
            status = 3
        elif request.POST['status'] == 'Rejected':
            status = 4
        consumer.status = status
        consumer.save()
        
    apps = request.user.consumer_set.all()
    return render_to_response('server/private/manage_apps.html', 
                              {'apps': apps}, context_instance=RequestContext(request))

@login_required   
def oauth_authorize(request, token, callback, params):
    from oauth_provider.forms import AuthorizeRequestTokenForm
    return render_to_response('server/oauth_authorize.html',
                              {'name': token.consumer.name, 'description': token.consumer.description, 
                               'form': AuthorizeRequestTokenForm(), 'oauth_token': token.key},
                              context_instance=RequestContext(request))
    