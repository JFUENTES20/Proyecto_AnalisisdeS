from .permisos import es_personal, rol_de


def identidad(request):
    pendientes = 0
    if request.user.is_authenticated:
        pendientes = request.user.notificaciones.filter(leida=False).count()
    return {
        "rol_actual": rol_de(request.user),
        "es_personal": es_personal(request.user),
        "avisos_pendientes": pendientes,
    }
