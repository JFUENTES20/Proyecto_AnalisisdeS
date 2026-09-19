from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from .models import Solicitud


def solicitudes_list(request):
    """Lista todas las solicitudes"""
    solicitudes = Solicitud.objects.all()
    return render(request, 'solicitudes/lista.html', {'solicitudes': solicitudes})


def solicitud_detalle(request, id):
    """Detalle de una solicitud"""
    solicitud = get_object_or_404(Solicitud, id=id)
    return render(request, 'solicitudes/detalle.html', {'solicitud': solicitud})


@require_http_methods(["POST"])
def cambiar_estado(request, id):
    """Cambia el estado de una solicitud"""
    solicitud = get_object_or_404(Solicitud, id=id)
    nuevo_estado = request.POST.get('estado')
    solicitud.cambiar_estado(nuevo_estado)
    return redirect('solicitud_detalle', id=solicitud.id)
