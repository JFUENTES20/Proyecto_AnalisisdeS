from django.conf import settings
from django.db import models


class Perfil(models.Model):
    """Fuente vigente del teléfono; las actualizaciones pasan por contacto.actualizar_telefono."""
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
    """Identidad histórica: telefono se conserva como archivo, no como contacto vigente."""

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


class EventoContacto(models.Model):
    perfil = models.ForeignKey(Perfil, on_delete=models.PROTECT, related_name="cambios_contacto")
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    telefono_anterior = models.CharField(max_length=20, blank=True)
    telefono_nuevo = models.CharField(max_length=20)
    operacion = models.CharField(max_length=40, default="actualizar_telefono")
    resultado = models.CharField(max_length=20, default="actualizado")
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-pk"]
