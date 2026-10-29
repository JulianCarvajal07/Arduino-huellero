from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio_sesion, name='inicio_sesion'),
    path('login/', views.inicio_sesion, name='inicio_sesion'),
    path("registro/", views.registro, name="registro"),
    path("empleados/", views.empleados, name="empleados"),
    path("validar_empleado/", views.validar_empleado, name="validar_empleado"),
    path('capturar-huella/', views.capturar_huella_view, name='capturar_huella'),
]