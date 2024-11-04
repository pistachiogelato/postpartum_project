# forms.py
from django import forms
from .models import User, Family

class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    role = forms.ChoiceField(choices=[('mom', 'Mom'), ('husband', 'Husband'), ('elder', 'Elder'), ('friend', 'Friend')])
    family_name = forms.CharField(max_length=100)

    class Meta:
        model = User
        fields = ['username', 'password', 'role', 'family_name']
