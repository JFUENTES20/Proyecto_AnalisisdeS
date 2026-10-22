from django.contrib import admin
from .models import Convocatoria


@admin.register(Convocatoria)
class ConvocatoriaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "nivel", "apertura", "cierre", "publicada")
    list_filter = ("publicada", "nivel")
    search_fields = ("titulo",)
