from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from .forms import RegistroAspiranteForm
from solicitudes.models import Solicitud


@require_http_methods(["GET", "POST"])
def registro(request):
    """Vista de registro para aspirantes"""
    if request.method == 'POST':
        form = RegistroAspiranteForm(request.POST)
        if form.is_valid():
            aspirante = form.save()
            # Log in automáticamente después del registro
            login(request, aspirante.user)
            return redirect('dashboard_aspirante')
    else:
        form = RegistroAspiranteForm()
    
    return render(request, 'usuarios/registro.html', {'form': form})


@login_required(login_url='registro')
def dashboard_aspirante(request):
    """Dashboard del aspirante - ve sus solicitudes"""
    aspirante = request.user.aspirante
    solicitudes = Solicitud.objects.filter(email=request.user.email)
    
    return render(request, 'usuarios/dashboard.html', {
        'aspirante': aspirante,
        'solicitudes': solicitudes
    })


@require_http_methods(["GET"])
def logout_view(request):
    """Cerrar sesión"""
    logout(request)
    return redirect('registro')
