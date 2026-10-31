from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from solicitudes import views
from usuarios.views import registro, mi_perfil

admin.site.site_header = "GuateBecas · Administración"
admin.site.site_title = "GuateBecas"
admin.site.index_title = "Configuración de la plataforma"
urlpatterns = [
    path("", views.inicio, name="inicio"),
    path(
        "convocatorias/<int:pk>/",
        views.convocatoria_detalle,
        name="convocatoria_detalle",
    ),
    path(
        "convocatorias/<int:pk>/solicitar/",
        views.crear_solicitud,
        name="crear_solicitud",
    ),
    path("acceso/", auth_views.LoginView.as_view(), name="login"),
    path("salir/", auth_views.LogoutView.as_view(), name="logout"),
    path("registro/", registro, name="registro"),
    path("panel/", views.panel, name="panel"),
    path("mi-perfil/", mi_perfil, name="mi_perfil"),
    path("solicitudes/", include("solicitudes.urls")),
    path("documentos/<int:pk>/", views.descargar_documento, name="descargar_documento"),
    path("notificaciones/", views.notificaciones, name="notificaciones"),
    path(
        "notificaciones/<int:pk>/leer/",
        views.leer_notificacion,
        name="leer_notificacion",
    ),
    path("reportes/solicitudes.csv", views.reporte_csv, name="reporte_csv"),
    path("usuarios/", include("usuarios.urls")),
    path("admin/", admin.site.urls),
]
