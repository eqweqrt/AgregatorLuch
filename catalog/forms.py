from django import forms
from .models import File

class UserForm(forms.Form):
    name = forms.CharField()
    age = forms.IntegerField()

class FileUploadForm(forms.ModelForm):
    class Meta:
        model = File
        fields = ['name', 'file']
        labels = {
            'name': 'Название файла',
            'file': 'Файл',
        }