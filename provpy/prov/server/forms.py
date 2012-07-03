from django.forms import ModelForm
from django import forms
from django.db import models
from prov.server.models import UserProfile
from django.contrib.auth.models import User


class ProfileForm(ModelForm):
    username = forms.CharField(label=("Username"))
    password = forms.CharField(label=("Password"), widget=forms.PasswordInput)
    confirm_password =  forms.CharField(label=("Confirm password"), widget=forms.PasswordInput)
    class Meta:
        model = UserProfile
        exclude = ('user')
        password=forms.CharField(label=("Password"), widget=forms.PasswordInput)
        
    def clean_username(self):
        username = self.cleaned_data['username']
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            return username
        raise forms.ValidationError(u'The username already exists')
    def clean_confirm_password(self):
        try:
            password = self.cleaned_data['password']
            confirm_password = self.cleaned_data['confirm_password']
            if password == confirm_password:
                return password
            raise forms.ValidationError(u'Passwords did not match')
        except KeyError:
            raise forms.ValidationError(u'You must provide password')
       
