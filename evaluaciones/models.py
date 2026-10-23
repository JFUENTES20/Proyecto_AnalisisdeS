from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q


class Comite(models.Model):
    nombre = models.CharField(max_length=150)
    convocatoria = models.ForeignKey(
        "convocatorias.Convocatoria", on_delete=models.PROTECT, related_name="comites"
    )
    miembros = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="comites", blank=True
    )

    def __str__(self):
        return self.nombre


class Evaluacion(models.Model):
    solicitud = models.ForeignKey(
        "solicitudes.Solicitud", on_delete=models.PROTECT, related_name="evaluaciones"
    )
    evaluador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    puntaje = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    observaciones = models.TextField()
    vigente = models.BooleanField(default=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["solicitud", "evaluador"],
                condition=Q(vigente=True),
                name="evaluacion_vigente_unica",
            ),
            models.CheckConstraint(
                condition=Q(puntaje__gte=0, puntaje__lte=100),
                name="puntaje_entre_cero_y_cien",
            ),
        ]
