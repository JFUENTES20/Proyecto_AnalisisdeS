from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.forms import HiddenInput
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .contacto import actualizar_telefono, hay_discrepancia, telefono_historico, version_contacto
from .forms import ContactoForm, RegistroForm
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
    return render(request, "usuarios/perfil.html", {"form": form, "telefono_actual": perfil.telefono,
                                                    "telefono_historico": historico, "discrepancia": discrepancia})
