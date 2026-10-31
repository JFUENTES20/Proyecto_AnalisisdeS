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


class Aspirante(models.Model):
    """Identidad histórica: conservar los datos existentes, sin exigirla a cuentas nuevas."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="aspirante"
    )
    cedula = models.CharField(max_length=20, unique=True)
    telefono = models.CharField(max_length=15)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Aspirante"
        verbose_name_plural = "Aspirantes"

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.cedula}"
