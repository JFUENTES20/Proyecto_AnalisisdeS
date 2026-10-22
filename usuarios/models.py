from django.conf import settings
from django.db import models


class Perfil(models.Model):
    class Rol(models.TextChoices):
        ASPIRANTE = "aspirante", "Aspirante"
        EVALUADOR = "evaluador", "Evaluador"
        APROBADOR = "aprobador", "Aprobador"
        ADMINISTRADOR = "administrador", "Administrador"

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil"
    )
    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.ASPIRANTE)
    telefono = models.CharField(max_length=20, blank=True)
    centro_educativo = models.CharField(max_length=160, blank=True)

    def __str__(self):
        return f"{self.usuario} · {self.get_rol_display()}"
