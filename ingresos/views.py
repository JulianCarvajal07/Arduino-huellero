
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .forms import EmpleadoForm

# Huella
from .serial_huella import capturar_huella
from django.http import JsonResponse
from django.views.decorators.http import require_POST


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
            return redirect('registro')   # cambia por el nombre de tu URL
    else:
        form = EmpleadoForm()

    return render(request, "paginas/registro.html", {'form': form})


@require_POST
def capturar_huella(request):
    return JsonResponse(capturar_huella())



def empleados(request):

    return render(request, "paginas/empleados.html")


def validar_empleado(request):

    return render(request, "paginas/validar_empleado.html")
