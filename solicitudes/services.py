"""Único punto de escritura del expediente desde las vistas; operaciones atómicas."""

from decimal import Decimal
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from usuarios.permisos import rol_de
from evaluaciones.models import Evaluacion
from .models import Solicitud, Decision, Documento
from .patterns import ESTADOS, EventoSolicitud, GestorObservadores

UMBRAL_SEGUNDA_APROBACION = Decimal("10000.00")


def puede_ver(usuario, solicitud):
    rol = rol_de(usuario)
    return (
        solicitud.aspirante_id == usuario.pk
        or rol in {"administrador", "aprobador"}
        or (
            rol == "evaluador"
            and solicitud.convocatoria_id
            and usuario.comites.filter(
                convocatoria_id=solicitud.convocatoria_id
            ).exists()
        )
    )


def visibles(usuario):
    qs = Solicitud.objects.select_related("convocatoria", "aspirante")
    rol = rol_de(usuario)
    if rol in {"administrador", "aprobador"}:
        return qs
    if rol == "evaluador":
        return qs.filter(
            Q(aspirante=usuario) | Q(convocatoria__comites__miembros=usuario)
        ).distinct()
    return qs.filter(aspirante=usuario)


def emitir(solicitud, actor, operacion, anterior="", comentario=""):
    GestorObservadores().notificar(
        EventoSolicitud(solicitud, actor, operacion, anterior, comentario)
    )


class ExpedienteFacade:
    """Facade: coordina permisos, estados, decisiones y observadores."""

    @staticmethod
    @transaction.atomic
    def crear(actor, convocatoria, monto, motivacion):
        if rol_de(actor) != "aspirante":
            raise PermissionDenied("Solo los aspirantes pueden presentar solicitudes.")
        if not convocatoria.abierta:
            raise ValidationError("La convocatoria no está abierta.")
        if not monto.is_finite() or monto <= 0 or monto > convocatoria.monto_maximo:
            raise ValidationError(
                "El monto debe ser positivo y no superar el máximo de la convocatoria."
            )
        if Solicitud.objects.filter(
            aspirante=actor, convocatoria=convocatoria
        ).exists():
            raise ValidationError("Ya tienes una solicitud para esta convocatoria.")
        solicitud = Solicitud.objects.create(
            aspirante=actor,
            convocatoria=convocatoria,
            nombre=(actor.get_full_name() or actor.username)[:100],
            email=actor.email,
            monto=monto,
            motivacion=motivacion,
        )
        emitir(solicitud, actor, "crear")
        return solicitud

    @staticmethod
    @transaction.atomic
    def transicionar(actor, solicitud_id, accion, comentario=""):
        solicitud = Solicitud.objects.select_for_update().get(pk=solicitud_id)
        rol = rol_de(actor)
        if not puede_ver(actor, solicitud):
            raise PermissionDenied
        anterior = solicitud.estado
        siguiente = ESTADOS[anterior].siguiente(accion)
        if accion == "enviar":
            if solicitud.aspirante_id != actor.pk:
                raise PermissionDenied
            if not solicitud.convocatoria or not solicitud.convocatoria.abierta:
                raise ValidationError("La convocatoria está cerrada.")
            if not solicitud.documentos.exists():
                raise ValidationError("Adjunta al menos un documento antes de enviar.")
        else:
            permitidos = (
                {"evaluador", "administrador"}
                if accion in {"revisar", "corregir"}
                else {"aprobador", "administrador"}
            )
            if rol not in permitidos or solicitud.aspirante_id == actor.pk:
                raise PermissionDenied
            if not comentario.strip():
                raise ValidationError(
                    "Escribe una justificación para registrar la decisión."
                )
            if accion == "aprobar":
                if not solicitud.evaluaciones.filter(vigente=True).exists():
                    raise ValidationError(
                        "Se requiere al menos una evaluación antes de aprobar."
                    )
                if solicitud.decisiones.filter(
                    accion="aprobar", responsable=actor
                ).exists():
                    raise ValidationError(
                        "La segunda aprobación debe realizarla otra persona."
                    )
                if (
                    anterior == "revision"
                    and solicitud.monto > UMBRAL_SEGUNDA_APROBACION
                ):
                    siguiente = "segunda_aprobacion"
            if accion == "corregir":
                solicitud.evaluaciones.filter(vigente=True).update(vigente=False)
            Decision.objects.create(
                solicitud=solicitud,
                responsable=actor,
                accion=accion,
                comentario=comentario,
            )
        solicitud.estado = siguiente
        solicitud.save(update_fields=["estado", "fecha_actualizacion"])
        emitir(solicitud, actor, accion, anterior, comentario)
        return solicitud

    @staticmethod
    @transaction.atomic
    def evaluar(actor, solicitud_id, puntaje, observaciones):
        solicitud = Solicitud.objects.select_for_update().get(pk=solicitud_id)
        if (
            rol_de(actor) not in {"evaluador", "administrador"}
            or not puede_ver(actor, solicitud)
            or solicitud.aspirante_id == actor.pk
        ):
            raise PermissionDenied
        if solicitud.estado != "revision":
            raise ValidationError("Solo se evalúan solicitudes en revisión.")
        evaluacion = Evaluacion(
            solicitud=solicitud,
            evaluador=actor,
            puntaje=puntaje,
            observaciones=observaciones,
        )
        evaluacion.full_clean()
        evaluacion.save()
        emitir(solicitud, actor, "evaluar", solicitud.estado, observaciones)

    @staticmethod
    @transaction.atomic
    def adjuntar(actor, solicitud_id, nombre, archivo):
        solicitud = Solicitud.objects.select_for_update().get(pk=solicitud_id)
        if solicitud.aspirante_id != actor.pk:
            raise PermissionDenied
        if solicitud.estado not in {"borrador", "correcciones"}:
            raise ValidationError(
                "Solo puedes adjuntar documentos en borrador o durante correcciones."
            )
        documento = Documento(solicitud=solicitud, nombre=nombre, cargado_por=actor)
        documento.archivo = archivo
        documento.save()
        emitir(solicitud, actor, "documento", solicitud.estado, nombre)
        return documento

    @staticmethod
    @transaction.atomic
    def editar(actor, solicitud_id, monto, motivacion):
        solicitud = (
            Solicitud.objects.select_for_update()
            .select_related("convocatoria")
            .get(pk=solicitud_id)
        )
        if solicitud.aspirante_id != actor.pk:
            raise PermissionDenied
        if solicitud.estado not in {"borrador", "correcciones"}:
            raise ValidationError(
                "El expediente no permite modificaciones en este estado."
            )
        if not solicitud.convocatoria or not solicitud.convocatoria.abierta:
            raise ValidationError("La convocatoria está cerrada.")
        if (
            not monto.is_finite()
            or monto <= 0
            or monto > solicitud.convocatoria.monto_maximo
        ):
            raise ValidationError("El monto no es válido para esta convocatoria.")
        cambios = f"Monto: {solicitud.monto} → {monto}. Motivación actualizada: {solicitud.motivacion != motivacion}."
        solicitud.monto, solicitud.motivacion = monto, motivacion
        solicitud.save(update_fields=["monto", "motivacion", "fecha_actualizacion"])
        emitir(solicitud, actor, "editar", solicitud.estado, cambios)
        return solicitud
