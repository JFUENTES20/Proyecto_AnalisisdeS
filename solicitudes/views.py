from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from convocatorias.models import Convocatoria
from usuarios.permisos import rol_de
from .forms import SolicitudForm, DocumentoForm, AccionForm, EvaluacionForm
from .models import Solicitud, Documento, Notificacion
from .services import ExpedienteFacade, puede_ver, visibles
from .reportes import ReporteBuilder, ExportadorCSV
from .storage import DjangoStorageAdapter


def inicio(request):
    return render(
        request,
        "inicio.html",
        {"convocatorias": Convocatoria.objects.filter(publicada=True)},
    )


def convocatoria_detalle(request, pk):
    convocatoria = get_object_or_404(Convocatoria, pk=pk, publicada=True)
    return render(request, "convocatorias/detalle.html", {"convocatoria": convocatoria})


@login_required
def panel(request):
    solicitudes = visibles(request.user)
    return render(
        request,
        "panel.html",
        {
            "total": solicitudes.count(),
            "en_revision": solicitudes.filter(
                estado__in=["pendiente", "revision", "segunda_aprobacion"]
            ).count(),
            "aprobadas": solicitudes.filter(
                estado__in=["aprobada", "activa", "completada"]
            ).count(),
            "solicitudes": solicitudes[:6],
            "notificaciones": request.user.notificaciones.all()[:4],
        },
    )


@login_required
def solicitudes_list(request):
    solicitudes = visibles(request.user)
    estado = request.GET.get("estado", "")
    if estado in Solicitud.Estado.values:
        solicitudes = solicitudes.filter(estado=estado)
    from django.core.paginator import Paginator

    pagina = Paginator(solicitudes, 20).get_page(request.GET.get("page"))
    return render(
        request,
        "solicitudes/lista.html",
        {"solicitudes": pagina, "estados": Solicitud.Estado.choices, "filtro": estado},
    )


@login_required
def crear_solicitud(request, pk):
    if rol_de(request.user) != "aspirante":
        raise PermissionDenied
    convocatoria = get_object_or_404(Convocatoria, pk=pk, publicada=True)
    form = SolicitudForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            solicitud = ExpedienteFacade.crear(
                request.user, convocatoria, **form.cleaned_data
            )
        except ValidationError as error:
            form.add_error(None, error)
        except IntegrityError:
            form.add_error(None, "Ya existe una solicitud para esta convocatoria.")
        else:
            messages.success(
                request, "Borrador creado. Adjunta tus documentos y envía la solicitud."
            )
            return redirect("solicitud_detalle", id=solicitud.pk)
    return render(
        request, "solicitudes/crear.html", {"form": form, "convocatoria": convocatoria}
    )


@login_required
def solicitud_detalle(request, id):
    solicitud = get_object_or_404(
        Solicitud.objects.select_related("convocatoria", "aspirante"), pk=id
    )
    if not puede_ver(request.user, solicitud):
        raise PermissionDenied
    rol = rol_de(request.user)
    propia = solicitud.aspirante_id == request.user.pk
    acciones = []
    if propia and solicitud.estado in {"borrador", "correcciones"}:
        acciones = [("enviar", "Enviar solicitud")]
    if not propia:
        if rol in {"evaluador", "administrador"}:
            if solicitud.estado == "pendiente":
                acciones = [("revisar", "Iniciar revisión")]
            elif solicitud.estado == "revision":
                acciones = [("corregir", "Solicitar correcciones")]
        if rol in {"aprobador", "administrador"}:
            if solicitud.estado in {"revision", "segunda_aprobacion"}:
                acciones += [("aprobar", "Aprobar"), ("rechazar", "Rechazar")]
            elif solicitud.estado == "aprobada":
                acciones = [("activar", "Activar beca")]
            elif solicitud.estado == "activa":
                acciones = [("completar", "Completar beca")]
    return render(
        request,
        "solicitudes/detalle.html",
        {
            "solicitud": solicitud,
            "acciones": acciones,
            "puede_adjuntar": propia
            and solicitud.estado in {"borrador", "correcciones"},
            "puede_evaluar": not propia
            and rol in {"evaluador", "administrador"}
            and solicitud.estado == "revision",
            "documento_form": DocumentoForm(),
            "evaluacion_form": EvaluacionForm(),
            "editar_form": SolicitudForm(
                initial={"monto": solicitud.monto, "motivacion": solicitud.motivacion}
            ),
            "eventos": solicitud.eventos.select_related("actor").all()
            if not propia
            else [],
            "decisiones": solicitud.decisiones.select_related("responsable").all()
            if not propia
            else solicitud.decisiones.filter(accion__in=["corregir", "rechazar"]),
            "evaluaciones": solicitud.evaluaciones.select_related("evaluador").all()
            if not propia
            else [],
        },
    )


def mostrar_error(request, error):
    texto = (
        "; ".join(error.messages)
        if isinstance(error, ValidationError)
        else "La operación entró en conflicto. Recarga e inténtalo de nuevo."
    )
    messages.error(request, texto)


@login_required
@require_POST
def cambiar_estado(request, id):
    form = AccionForm(request.POST)
    if form.is_valid():
        try:
            ExpedienteFacade.transicionar(request.user, id, **form.cleaned_data)
        except Solicitud.DoesNotExist:
            from django.http import Http404

            raise Http404
        except (ValidationError, IntegrityError) as error:
            mostrar_error(request, error)
        else:
            messages.success(request, "Operación registrada y notificación generada.")
    else:
        messages.error(request, "La acción solicitada no es válida.")
    return redirect("solicitud_detalle", id=id)


@login_required
@require_POST
def adjuntar(request, id):
    get_object_or_404(Solicitud, pk=id)
    form = DocumentoForm(request.POST, request.FILES)
    if form.is_valid():
        try:
            ExpedienteFacade.adjuntar(request.user, id, **form.cleaned_data)
        except ValidationError as error:
            mostrar_error(request, error)
        else:
            messages.success(request, "Documento incorporado al expediente.")
    else:
        for errores in form.errors.values():
            for error in errores:
                messages.error(request, error)
    return redirect("solicitud_detalle", id=id)


@login_required
@require_POST
def evaluar(request, id):
    get_object_or_404(Solicitud, pk=id)
    form = EvaluacionForm(request.POST)
    if form.is_valid():
        try:
            ExpedienteFacade.evaluar(request.user, id, **form.cleaned_data)
        except ValidationError as error:
            mostrar_error(request, error)
        else:
            messages.success(request, "Evaluación registrada.")
    else:
        messages.error(
            request, "Revisa la puntuación y la fundamentación de la evaluación."
        )
    return redirect("solicitud_detalle", id=id)


@login_required
def descargar_documento(request, pk):
    documento = get_object_or_404(Documento.objects.select_related("solicitud"), pk=pk)
    if not puede_ver(request.user, documento.solicitud):
        raise PermissionDenied
    stream = DjangoStorageAdapter(documento.archivo.storage).abrir(
        documento.archivo.name
    )
    return FileResponse(
        stream, as_attachment=True, filename=documento.archivo.name.rsplit("/", 1)[-1]
    )


@login_required
def notificaciones(request):
    return render(
        request,
        "notificaciones.html",
        {"notificaciones": request.user.notificaciones.all()[:100]},
    )


@login_required
@require_POST
def leer_notificacion(request, pk):
    aviso = get_object_or_404(Notificacion, pk=pk, destinatario=request.user)
    aviso.leida = True
    aviso.save(update_fields=["leida"])
    return redirect("solicitud_detalle", id=aviso.solicitud_id)


@login_required
def reporte_csv(request):
    if rol_de(request.user) not in {"administrador", "aprobador"}:
        raise PermissionDenied
    reporte = (
        ReporteBuilder(visibles(request.user))
        .identificacion()
        .seguimiento()
        .construir()
    )
    respuesta = HttpResponse(
        ExportadorCSV().exportar(reporte), content_type="text/csv; charset=utf-8"
    )
    respuesta["Content-Disposition"] = 'attachment; filename="becanet-reporte.csv"'
    return respuesta


@login_required
@require_POST
def editar_solicitud(request, id):
    get_object_or_404(Solicitud, pk=id)
    form = SolicitudForm(request.POST)
    if form.is_valid():
        try:
            ExpedienteFacade.editar(request.user, id, **form.cleaned_data)
        except ValidationError as error:
            mostrar_error(request, error)
        else:
            messages.success(request, "Cambios guardados y registrados en auditoría.")
    else:
        messages.error(request, "Revisa el monto y la motivación del expediente.")
    return redirect("solicitud_detalle", id=id)
