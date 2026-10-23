from django.contrib import admin
from .models import Solicitud, Decision, EventoAuditoria, Notificacion, Documento


class SoloLecturaAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Solicitud)
class SolicitudAdmin(SoloLecturaAdmin):
    list_display = ("id", "nombre", "convocatoria", "monto", "estado")
    list_filter = ("estado",)
    search_fields = ("nombre", "email")


@admin.register(EventoAuditoria)
class EventoAdmin(SoloLecturaAdmin):
    list_display = ("solicitud", "actor", "operacion", "resultado", "creado_en")
    list_filter = ("operacion",)


admin.site.register([Decision, Notificacion, Documento], SoloLecturaAdmin)
