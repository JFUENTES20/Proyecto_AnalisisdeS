from django.urls import path
from . import legacy_views

app_name = "usuarios_legacy"
urlpatterns = [
    path("registro/", legacy_views.registro, name="registro"),
    path("login/", legacy_views.acceso, name="login_aspirante"),
    path("dashboard/", legacy_views.panel, name="dashboard_aspirante"),
    path("logout/", legacy_views.salida, name="logout"),
]
