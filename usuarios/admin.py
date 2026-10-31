from django.contrib import admin
from .models import Aspirante, Perfil, EventoContacto


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ("usuario", "rol", "centro_educativo")
    list_filter = ("rol",)
    readonly_fields = ("telefono",)
    search_fields = ("usuario__username", "usuario__email")


@admin.register(Aspirante)
class AspiranteAdmin(admin.ModelAdmin):
    list_display = ("user", "cedula", "telefono", "fecha_registro")
    search_fields = ("user__username", "user__email", "cedula")
    readonly_fields = ("fecha_registro", "telefono")


@admin.register(EventoContacto)
class EventoContactoAdmin(admin.ModelAdmin):
    list_display = ("perfil", "responsable", "operacion", "resultado", "fecha")
    readonly_fields = tuple(f.name for f in EventoContacto._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
