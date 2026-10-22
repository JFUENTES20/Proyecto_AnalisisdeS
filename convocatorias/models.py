from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class Convocatoria(models.Model):
    class Nivel(models.TextChoices):
        MEDIO = "medio", "Nivel medio"
        UNIVERSITARIO = "universitario", "Universitario"
        POSGRADO = "posgrado", "Posgrado"

    titulo = models.CharField(max_length=180)
    descripcion = models.TextField()
    requisitos = models.TextField(help_text="Un requisito por línea")
    nivel = models.CharField(max_length=20, choices=Nivel.choices)
    apertura = models.DateField()
    cierre = models.DateField()
    monto_maximo = models.DecimalField(max_digits=12, decimal_places=2)
    publicada = models.BooleanField(default=False)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-apertura", "-pk"]
        constraints = [
            models.CheckConstraint(
                condition=Q(cierre__gte=F("apertura")),
                name="fechas_convocatoria_validas",
            ),
            models.CheckConstraint(
                condition=Q(monto_maximo__gt=0), name="monto_convocatoria_positivo"
            ),
        ]

    @property
    def abierta(self):
        return self.publicada and self.apertura <= timezone.localdate() <= self.cierre

    def __str__(self):
        return self.titulo
