from django.db import models
from django.contrib.auth.models import User


class Aspirante(models.Model):
    """Modelo para aspirantes a becas"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='aspirante')
    cedula = models.CharField(max_length=20, unique=True)
    telefono = models.CharField(max_length=15)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.cedula}"
    
    class Meta:
        verbose_name = "Aspirante"
        verbose_name_plural = "Aspirantes"
