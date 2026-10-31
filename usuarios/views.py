from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.forms import HiddenInput
from django.shortcuts import get_object_or_404, redirect, render
from django.http import FileResponse, Http404
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .contacto import actualizar_telefono, hay_discrepancia, telefono_historico, version_contacto
from .forms import ContactoForm, FotografiaForm, RegistroForm
from .fotografia import cambiar_fotografia
from .models import Perfil
from .permisos import rol_de


def registro(request):
    if request.user.is_authenticated:
        return redirect("panel")
    form = RegistroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            usuario = form.save()
            Perfil.objects.create(usuario=usuario)
        login(request, usuario)
        return redirect("panel")
    return render(request, "registration/registro.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def mi_perfil(request):
    if rol_de(request.user) != "aspirante":
        raise PermissionDenied
    perfil = Perfil.objects.get(usuario=request.user)
    historico = telefono_historico(request.user)
    discrepancia = hay_discrepancia(perfil.telefono, historico)
    form = ContactoForm(request.POST if request.method == "POST" else None,
                        initial={"telefono": perfil.telefono, "version": version_contacto(perfil)})
    if not discrepancia:
        form.fields["confirmar_cambio"].widget = HiddenInput()
    if request.method == "POST":
        permitidos = {"csrfmiddlewaretoken", "telefono", "version", "confirmar_cambio"}
        if set(request.POST) - permitidos:
            raise PermissionDenied("Esta pantalla solo permite actualizar tu propio teléfono.")
        if form.is_valid():
            try:
                cambio = actualizar_telefono(request.user, form.cleaned_data["telefono"],
                                             form.cleaned_data["version"], form.cleaned_data["confirmar_cambio"])
            except ValidationError as error:
                form.add_error(None, error)
            else:
                messages.success(request, "Teléfono actualizado." if cambio else "Tu teléfono ya estaba actualizado.")
                return redirect("mi_perfil")
    nombre = request.user.get_full_name().strip() or request.user.username
    iniciales = "".join(palabra[0] for palabra in nombre.split()[:2]).upper()
    return render(request, "usuarios/perfil.html", {"form": form, "perfil": perfil,
        "nombre_perfil": nombre, "iniciales": iniciales,
        "foto_form": FotografiaForm(), "telefono_actual": perfil.telefono,
                                                    "telefono_historico": historico, "discrepancia": discrepancia})


@login_required
@require_POST
def guardar_fotografia(request):
    if rol_de(request.user) != "aspirante":
        raise PermissionDenied
    if set(request.POST) - {"csrfmiddlewaretoken", "accion"} or set(request.FILES) - {"fotografia"}:
        raise PermissionDenied
    accion = request.POST.get("accion")
    if accion not in {"guardar", "eliminar"}:
        raise PermissionDenied
    if accion == "eliminar":
        if request.FILES:
            raise PermissionDenied
        cambiar_fotografia(request.user, eliminar=True)
        messages.success(request, "Fotografía eliminada. Se mostrarán tus iniciales.")
    else:
        form = FotografiaForm(request.POST, request.FILES)
        if not form.is_valid():
            for error in form.errors.get("fotografia", []):
                messages.error(request, error)
        else:
            try:
                cambiar_fotografia(request.user, form.cleaned_data["fotografia"])
            except ValidationError as error:
                for mensaje in error.messages:
                    messages.error(request, mensaje)
            else:
                messages.success(request, "Fotografía actualizada.")
    return redirect("mi_perfil")


@login_required
@require_http_methods(["GET", "HEAD"])
@never_cache
def ver_fotografia(request, usuario_id):
    if usuario_id != request.user.pk or rol_de(request.user) != "aspirante":
        raise Http404
    perfil = get_object_or_404(Perfil, usuario_id=request.user.pk)
    if not perfil.fotografia:
        raise Http404
    try:
        archivo = perfil.fotografia.open("rb")
    except FileNotFoundError:
        raise Http404
    response = FileResponse(archivo, content_type="image/jpeg")
    response["Content-Disposition"] = 'inline; filename="fotografia.jpg"'
    response["Cache-Control"] = "private, no-store"
    return response
