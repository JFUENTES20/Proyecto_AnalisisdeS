from django import forms
from django.contrib.auth.models import User
from .models import Aspirante


class RegistroAspiranteForm(forms.ModelForm):
    """Formulario para registro de aspirantes"""
    
    nombre = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Nombre completo',
            'required': True
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'tu@email.com',
            'required': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Contraseña segura',
            'required': True
        })
    )
    cedula = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '1234567890123',
            'required': True
        })
    )
    telefono = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '+502 7777 7777',
            'required': True
        })
    )
    
    class Meta:
        model = Aspirante
        fields = ['cedula', 'telefono']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este email ya está registrado.")
        return email
    
    def clean_cedula(self):
        cedula = self.cleaned_data.get('cedula')
        if Aspirante.objects.filter(cedula=cedula).exists():
            raise forms.ValidationError("Esta cédula ya está registrada.")
        return cedula
    
    def save(self, commit=True):
        aspirante = super().save(commit=False)
        
        # Crear usuario
        user = User.objects.create_user(
            username=self.cleaned_data['email'],
            email=self.cleaned_data['email'],
            first_name=self.cleaned_data['nombre'].split()[0],
            last_name=' '.join(self.cleaned_data['nombre'].split()[1:]),
            password=self.cleaned_data['password']
        )
        
        aspirante.user = user
        if commit:
            aspirante.save()
        return aspirante
