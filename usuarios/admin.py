from django.contrib import admin
from .models import Aspirante


@admin.register(Aspirante)
class AspiranteAdmin(admin.ModelAdmin):
    list_display = ('user', 'cedula', 'telefono', 'fecha_registro')
    search_fields = ('user__first_name', 'user__email', 'cedula')
    readonly_fields = ('fecha_registro',)
    
    fieldsets = (
        ('Usuario', {
            'fields': ('user',)
        }),
        ('Información Personal', {
            'fields': ('cedula', 'telefono')
        }),
        ('Fechas', {
            'fields': ('fecha_registro',),
            'classes': ('collapse',)
        }),
    )
