from django.urls import path
from . import views

urlpatterns = [
    path('registro/', views.registro, name='registro'),
    path('dashboard/', views.dashboard_aspirante, name='dashboard_aspirante'),
    path('logout/', views.logout_view, name='logout'),
]
