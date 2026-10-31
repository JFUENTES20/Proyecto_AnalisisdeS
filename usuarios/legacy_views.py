from urllib.parse import urlencode

from django.contrib.auth.views import LogoutView
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from django.urls import reverse


@require_http_methods(["GET", "POST"])
def registro(request):
    return redirect("registro", preserve_request=request.method == "POST")


@require_http_methods(["GET"])
def acceso(request):
    # La vista de acceso moderna valida el parámetro next.
    url = reverse("login")
    if request.GET.get("next"):
        url += "?" + urlencode({"next": request.GET["next"]})
    return redirect(url)


@require_http_methods(["GET"])
def panel(request):
    return redirect("panel")


@require_http_methods(["GET", "POST"])
def salida(request):
    if request.method == "POST":
        return LogoutView.as_view()(request)
    # Las URL antiguas cerraban sesión por GET: ahora requieren confirmación CSRF.
    return render(request, "registration/salir.html")
