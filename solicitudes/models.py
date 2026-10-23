from django.conf import settings
from django.db import models
from django.db.models import Q


class Solicitud(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        PENDIENTE = "pendiente", "Enviada"
        REVISION = "revision", "En revisión"
        CORRECCIONES = "correcciones", "Requiere correcciones"
        SEGUNDA = "segunda_aprobacion", "Pendiente de segunda aprobación"
        APROBADA = "aprobada", "Aprobada"
        RECHAZADA = "rechazada", "Rechazada"
        ACTIVA = "activa", "Activa"
        COMPLETADA = "completada", "Completada"

    # Se conservan nombre/email y la migración original para no borrar expedientes antiguos.
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    email = models.EmailField()
    aspirante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="solicitudes",
    )
    convocatoria = models.ForeignKey(
        "convocatorias.Convocatoria",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="solicitudes",
    )
    monto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    motivacion = models.TextField(blank=True)
    estado = models.CharField(
        max_length=24, choices=Estado.choices, default=Estado.BORRADOR
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Solicitud"
        verbose_name_plural = "Solicitudes"
        ordering = ["-fecha_creacion"]
        constraints = [
            models.UniqueConstraint(
                fields=["aspirante", "convocatoria"],
                name="solicitud_unica_por_convocatoria",
            ),
            models.CheckConstraint(
                condition=Q(monto__gte=0), name="monto_solicitud_no_negativo"
            ),
        ]

    def __str__(self):
        return f"BEC-{self.pk:05d} · {self.nombre}" if self.pk else self.nombre


class Documento(models.Model):
    solicitud = models.ForeignKey(
        Solicitud, on_delete=models.PROTECT, related_name="documentos"
    )
    nombre = models.CharField(max_length=160)
    archivo = models.FileField(upload_to="expedientes/%Y/%m/")
    cargado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    creado_en = models.DateTimeField(auto_now_add=True)


class Decision(models.Model):
    solicitud = models.ForeignKey(
        Solicitud, on_delete=models.PROTECT, related_name="decisiones"
    )
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    accion = models.CharField(max_length=30)
    comentario = models.TextField()
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["creada_en"]
        constraints = [
            models.UniqueConstraint(
                fields=["solicitud", "responsable"],
                condition=Q(accion="aprobar"),
                name="una_aprobacion_por_persona",
            )
        ]


class EventoAuditoria(models.Model):
    solicitud = models.ForeignKey(
        Solicitud, on_delete=models.PROTECT, related_name="eventos"
    )
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    operacion = models.CharField(max_length=40)
    anterior = models.CharField(max_length=24, blank=True)
    resultado = models.CharField(max_length=160)
    comentario = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en", "-pk"]


class Notificacion(models.Model):
    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="notificaciones",
    )
    solicitud = models.ForeignKey(Solicitud, on_delete=models.PROTECT)
    mensaje = models.CharField(max_length=240)
    leida = models.BooleanField(default=False)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creada_en"]
