from django.forms import ModelForm, Textarea, Form
from django import forms
from prov.server.models import UserProfile, Container, Submission
from django.contrib.auth.models import User
from oauth_provider.models import Consumer
from prov.model import ProvBundle
import json

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


class BundleForm(Form):
    rec_id = forms.CharField(label=('Record ID'))
    submission = forms.FileField(label=('Original File'), required = False)
    public = forms.BooleanField(label=('Public'), required = False)
    content = forms.CharField(label=('Content (in JSON format)'), widget=Textarea(attrs={'class': 'span9'}))
        
    def clean(self):
        if 'content' in self.cleaned_data:
            try:
                self.bundle = ProvBundle()
                self.bundle._decode_JSON_container(json.loads(self.cleaned_data['content']))
            except ValueError:
                raise forms.ValidationError(u'Wrong syntax in the JSON content.')
        return self.cleaned_data
    
    def save(self, owner, commit=True):
        if self.errors:
            raise ValueError("The %s could not be %s because the data didn't"
                         " validate." % ('UserProfile', 'created'))
        container = Container.create(self.cleaned_data['rec_id'], self.bundle, owner, self.cleaned_data['public'])
        if 'submission' in self.files:
            file_sub = self.files['submission']
            sub = Submission.objects.create()
            sub.content.save(sub.timestamp.strftime('%Y-%m-%d%H-%M-%S')+file_sub._name, file_sub)
            container.submission = sub
            container.save()
        return container
        
    
