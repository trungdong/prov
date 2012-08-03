from django.forms import ModelForm
from django import forms
from prov.server.models import UserProfile, Container
from django.contrib.auth.models import User, Group
from oauth_provider.models import Consumer

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
        exclude = ('user', 'key', 'secret')


class BundleForm(ModelForm):
    class Meta:
        model = Container
        
        
    
