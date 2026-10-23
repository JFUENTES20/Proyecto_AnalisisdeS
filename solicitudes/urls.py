from django.urls import path
from . import views

urlpatterns = [
    path("", views.solicitudes_list, name="solicitudes_list"),
    path("<int:id>/", views.solicitud_detalle, name="solicitud_detalle"),
    path("<int:id>/cambiar-estado/", views.cambiar_estado, name="cambiar_estado"),
    path("<int:id>/editar/", views.editar_solicitud, name="editar_solicitud"),
    path("<int:id>/documentos/", views.adjuntar, name="adjuntar"),
    path("<int:id>/evaluar/", views.evaluar, name="evaluar"),
]
