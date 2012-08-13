from django.forms import ModelForm, Textarea, Form, CheckboxSelectMultiple
from django import forms
from prov.server.models import UserProfile, Container, Submission, License
from django.contrib.auth.models import User
from oauth_provider.models import Consumer
from prov.model import ProvBundle
from django.utils.safestring import mark_safe
from urllib2 import URLError, urlopen
from json import loads

class ProfileForm(ModelForm):
    username = forms.CharField(label=("Username"), min_length=3)
    password = forms.CharField(label=("Password"), widget=forms.PasswordInput, min_length=3)
    confirm_password =  forms.CharField(label=("Confirm password"), widget=forms.PasswordInput, min_length=3)
    class Meta:
        model = UserProfile
        exclude = ('user')
        
    def clean(self):
        if 'username' in self.cleaned_data:
            if User.objects.filter(username=self.cleaned_data['username']).exists():
                raise forms.ValidationError(u'The username already exists.')
            
        if 'password' in self.cleaned_data and 'confirm_password' in self.cleaned_data:
            if self.cleaned_data['password'] != self.cleaned_data['confirm_password']:
                raise forms.ValidationError(u'Passwords did not match.')
        return self.cleaned_data
    
    def save(self, commit=True):
        if self.instance.pk is None:
            fail_message = 'created'
        else:
            fail_message = 'changed'
        if self.errors:
            raise ValueError("The %s could not be %s because the data didn't"
                         " validate." % ('UserProfile', fail_message))
        self.instance = User.objects.create_user(username=self.cleaned_data['username'], password=self.cleaned_data['password'])
        return self.instance
    
class AppForm(ModelForm):
    class Meta:
        model = Consumer
        fields = ('name', 'status', 'description')
        widgets ={'description': Textarea(attrs={'class': 'span6'}),}

class LicenseMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return mark_safe('{t}({d})</br><a href="{u}">{u}</a>'.format(t=obj.title, d=obj.description,u=obj.url))

class BundleForm(Form):
    rec_id = forms.CharField(label=('Record ID'))
    public = forms.BooleanField(label=('Public'), required = False)
    submission = forms.FileField(label=('Original File'), required = False)
    license = LicenseMultipleChoiceField(License.objects, widget=CheckboxSelectMultiple, required=False)
    url = forms.URLField(label='URL to the bundle file:', required=False)
    content = forms.CharField(label=('Content (in JSON format)'), widget=Textarea(attrs={'class': 'span7'}), required=False)
    
    def clean(self):
        self.bundle = ProvBundle()
        if self.cleaned_data['content']:
            try:
                self.bundle._decode_JSON_container(loads(self.cleaned_data['content']))
            except ValueError:
                raise forms.ValidationError(u'Wrong syntax in the JSON content.')
        elif self.cleaned_data['url']:
            try:
                source = urlopen(self.cleaned_data['url'])
                url_content = source.read()
                source.close()
            except URLError:
                raise forms.ValidationError(u'There was a problem accessing the URL.')
            try:
                self.bundle._decode_JSON_container(loads(url_content))
            except ValueError:
                raise forms.ValidationError(u'Wrong syntax in the JSON content at the URL.')
        else:
            raise forms.ValidationError(u'No content or URL provided.')
        return self.cleaned_data
    
    def save(self, owner, commit=True):
        if self.errors:
            raise ValueError("The %s could not be %s because the data didn't"
                         " validate." % ('BundleContainer', 'created'))
        container = Container.create(self.cleaned_data['rec_id'], self.bundle, owner, self.cleaned_data['public'])
        save = False
        if 'submission' in self.files:
            file_sub = self.files['submission']
            sub = Submission.objects.create()
            sub.content.save(sub.timestamp.strftime('%Y-%m-%d%H-%M-%S')+file_sub._name, file_sub)
            container.submission = sub
            save = True
        for l in self.cleaned_data['license']:
            container.license.add(l)
            save = True
        if save:
            container.save()
        return container
        