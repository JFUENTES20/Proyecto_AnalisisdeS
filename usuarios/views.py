from django.contrib.auth import login
from django.db import transaction
from django.shortcuts import redirect, render
from .forms import RegistroForm
from .models import Perfil


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
