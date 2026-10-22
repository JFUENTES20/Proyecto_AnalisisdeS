"""State y Observer: reglas de transición y efectos persistentes, sin envío externo."""

from dataclasses import dataclass
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError


class EstadoSolicitud:
    transiciones = {}

    def siguiente(self, accion):
        if accion not in self.transiciones:
            raise ValidationError("Esta acción no está disponible en el estado actual.")
        return self.transiciones[accion]


class Borrador(EstadoSolicitud):
    transiciones = {"enviar": "pendiente"}


class Enviada(EstadoSolicitud):
    transiciones = {"revisar": "revision"}


class Revision(EstadoSolicitud):
    transiciones = {
        "corregir": "correcciones",
        "aprobar": "aprobada",
        "rechazar": "rechazada",
    }


class Correcciones(EstadoSolicitud):
    transiciones = {"enviar": "pendiente"}


class SegundaAprobacion(EstadoSolicitud):
    transiciones = {"aprobar": "aprobada", "rechazar": "rechazada"}


class Aprobada(EstadoSolicitud):
    transiciones = {"activar": "activa"}


class Activa(EstadoSolicitud):
    transiciones = {"completar": "completada"}


ESTADOS = {
    "borrador": Borrador(),
    "pendiente": Enviada(),
    "revision": Revision(),
    "correcciones": Correcciones(),
    "segunda_aprobacion": SegundaAprobacion(),
    "aprobada": Aprobada(),
    "activa": Activa(),
    "rechazada": EstadoSolicitud(),
    "completada": EstadoSolicitud(),
}


@dataclass(frozen=True)
class EventoSolicitud:
    solicitud: object
    actor: object
    operacion: str
    anterior: str
    comentario: str = ""


class AuditoriaObserver:
    def actualizar(self, evento):
        from .models import EventoAuditoria

        EventoAuditoria.objects.create(
            solicitud=evento.solicitud,
            actor=evento.actor,
            operacion=evento.operacion,
            anterior=evento.anterior,
            resultado=evento.solicitud.estado,
            comentario=evento.comentario,
        )


class NotificacionObserver:
    def actualizar(self, evento):
        from .models import Notificacion

        solicitud = evento.solicitud
        if (
            evento.operacion not in {"crear", "documento", "evaluar", "editar"}
            and solicitud.aspirante_id
        ):
            Notificacion.objects.create(
                destinatario=solicitud.aspirante,
                solicitud=solicitud,
                mensaje=f"Solicitud BEC-{solicitud.pk:05d}: {solicitud.get_estado_display()}.",
            )
        if evento.operacion in {"enviar", "aprobar"} and solicitud.estado in {
            "pendiente",
            "segunda_aprobacion",
        }:
            rol = "evaluador" if solicitud.estado == "pendiente" else "aprobador"
            personas = get_user_model().objects.filter(is_active=True, perfil__rol=rol)
            if rol == "evaluador":
                personas = personas.filter(
                    comites__convocatoria=solicitud.convocatoria
                ).distinct()
            personas = personas.exclude(pk=evento.actor.pk)
            Notificacion.objects.bulk_create(
                [
                    Notificacion(
                        destinatario=p,
                        solicitud=solicitud,
                        mensaje=f"Expediente BEC-{solicitud.pk:05d} pendiente de atención.",
                    )
                    for p in personas
                ]
            )


class GestorObservadores:
    def __init__(self, observadores=None):
        self.observadores = (
            tuple(observadores)
            if observadores is not None
            else (AuditoriaObserver(), NotificacionObserver())
        )

    def notificar(self, evento):
        for observador in self.observadores:
            observador.actualizar(evento)
