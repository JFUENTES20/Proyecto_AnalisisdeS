from django.contrib import admin
from .models import Aspirante, Perfil


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ("usuario", "rol", "centro_educativo")
    list_filter = ("rol",)
    search_fields = ("usuario__username", "usuario__email")


@admin.register(Aspirante)
class AspiranteAdmin(admin.ModelAdmin):
    list_display = ("user", "cedula", "telefono", "fecha_registro")
    search_fields = ("user__username", "user__email", "cedula")
    readonly_fields = ("fecha_registro",)
