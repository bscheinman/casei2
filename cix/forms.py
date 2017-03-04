from django import forms
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.forms import PasswordInput
from django.contrib.auth.models import User


class LoginForm(forms.Form):
    username = forms.CharField(label='username')
    password = forms.CharField(widget=forms.PasswordInput, label='password')


class SignupForm(forms.Form):
    username = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    email_verify = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, max_length=50, required=True)
    password_verify = forms.CharField(widget=forms.PasswordInput, max_length=50, required=True)

    def clean(self):
        super(SignupForm, self).clean()

        cleaned_data = self.cleaned_data
        
        password = cleaned_data.get('password')
        password_verify = cleaned_data.get('password_verify')

        if password and password_verify and password != password_verify:
            self._errors['password_verify'] = self.error_class(['Passwords do not match'])
            del cleaned_data['password']
            del cleaned_data['password_verify']
       
        email = cleaned_data.get('email')
        email_verify = cleaned_data.get('email_verify')

        if email:
            try:
                validate_email(email)
                if email_verify and email != email_verify:
                    self._errors['email_verify'] = self.error_class(['Emails do not match'])
                    del cleaned_data['email']
                    del cleaned_data['email_verify']
            except ValidationError:
                self._errors['email'] = self.error_class(['Please enter a valid email address'])
                del cleaned_data['email']
                del cleaned_data['email_verify']

        username = cleaned_data.get('username')
        if username:
            try:
                user = User.objects.get(username__iexact=username)
            except User.DoesNotExist:
                import re
                user_pattern = r'[^a-zA-Z0-9_]'
                if re.search(user_pattern, username):
                    self._errors['username'] = self.error_class(\
                        ['Username contains invalid characters.  Usernames can only contain letters, numbers and underscores'])
                    del cleaned_data['username']
            else:
                self._errors['username'] = self.error_class(['Username is already taken'])
                del cleaned_data['username']
        if email:
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                pass
            else:
                self._errors['email'] = self.error_class(['Email is already registered'])
                del cleaned_data['email']
                del cleaned_data['email_verify']
        
        return cleaned_data
