from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio_sesion, name='inicio_sesion'),
    path('login/', views.inicio_sesion, name='inicio_sesion'),
    path('cerrar-sesion/', views.cerrar_sesion, name='cerrar_sesion'),
    path("registro/", views.registro, name="registro"),
    path("empleados/", views.empleados, name="empleados"),
    path("validar_empleado/", views.validar_empleado, name="validar_empleado"),
    path("eliminar_empleado/<int:huella_id>", views.eliminar_empleado, name="eliminar_empleado"),
    path('validar_entrada/', views.registrar_entrada, name='registrar_entrada'),
    path('validar_salida/', views.registrar_salida, name='registrar_salida'),
    path('capturar-huella/', views.capturar_huella_view, name='capturar_huella'),
    path("auditoria/", views.auditoria, name="auditoria"),
]