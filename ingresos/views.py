
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .forms import EmpleadoForm
from .models import Empleado

# Huella
from .serial_huella import capturar_huella
from django.http import JsonResponse
from django.views.decorators.http import require_POST

MAX_HUELLAS = 127   # capacidad que use tu sketch

def siguiente_id_libre():
    usados = set(Empleado.objects.values_list('huella_id', flat=True))
    for i in range(1, MAX_HUELLAS + 1):
        if i not in usados:
            return i
    return None

@require_POST
def capturar_huella_view(request):
    huella_id = siguiente_id_libre()
    if huella_id is None:
        return JsonResponse({'ok': False, 'error': 'La memoria del sensor está llena'})
    return JsonResponse(capturar_huella(huella_id))


def inicio_sesion(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        usuario = authenticate(
            request,
            username=username,
            password=password
        )

        if usuario is not None:
            if usuario.is_active:
                login(request, usuario)
                return redirect("registro")
            else:
                messages.error(request, "El usuario está desactivado.")
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")

    return render(request, "paginas/inicio_sesion.html")


def registro(request):
    if not request.user.is_authenticated:
        return redirect("inicio_sesion")

    if request.method == 'POST':
        form = EmpleadoForm(request.POST)
        if form.is_valid():
            empleado = form.save()
            messages.success(request, f'Empleado {empleado} registrado correctamente.')
            return redirect('registro')
        else:
            print('ERRORES FORM:', form.errors.as_json())   # depuración
            messages.error(request, 'No se pudo registrar el empleado. Revisa los campos.')
    else:
        form = EmpleadoForm()

    return render(request, "paginas/registro.html", {'form': form})





def empleados(request):

    return render(request, "paginas/empleados.html")


def validar_empleado(request):

    return render(request, "paginas/validar_empleado.html")
