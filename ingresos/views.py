
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .forms import EmpleadoForm
from .models import Empleado, Registro
from django.utils import timezone

# Huella
from .serial_huella import capturar_huella, verificar_huella
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


# ==============================================================================
# FUNCIÓN DE VISTA: REGISTRO DE EMPLEADOS
# ==============================================================================

def registro(request):
    """
    Controla todo el flujo de la página de registro:
    1. Revisa si el usuario inició sesión.
    2. Si el usuario solo entra a ver, le entrega el formulario vacío (GET).
    3. Si el usuario presiona "Guardar", revisa los datos y los guarda (POST).
    """

    # --------------------------------------------------------------------------
    # PASO 1: CONTROL DE ACCESO (AUTENTICACIÓN)
    # --------------------------------------------------------------------------
    # 'request.user.is_authenticated' verifica si quien está navegando tiene una sesión activa.
    # Si NO ha iniciado sesión, no puede estar aquí.
    if not request.user.is_authenticated:
        # Lo expulsamos de esta página y lo enviamos a la pantalla de login ('inicio_sesion').
        return redirect("inicio_sesion")

    # --------------------------------------------------------------------------
    # PASO 2: IDENTIFICAR QUÉ INTENTA HACER EL USUARIO
    # En la web existen principalmente dos intenciones:
    # - 'GET': "Solo quiero mirar la página / cargar la pantalla".
    # - 'POST': "Presioné el botón de enviar y te estoy mandando datos".
    # --------------------------------------------------------------------------
    if request.method == 'POST':
        # El usuario llenó el formulario y presionó el botón para enviar los datos.
        
        # Le entregamos al recepcionista (EmpleadoForm) los datos que el usuario escribió (request.POST).
        form = EmpleadoForm(request.POST)

        # ----------------------------------------------------------------------
        # PASO 3: VALIDACIÓN DE LOS DATOS
        # ----------------------------------------------------------------------
        # 'form.is_valid()' ejecuta automáticamente todas las revisiones que definiste en forms.py
        # (clean_documento, verificar que la huella no esté repetida, etc.).
        if form.is_valid():
            # Si TODO está correcto:
            
            # 1. Guarda al nuevo empleado de forma permanente en la base de datos.
            empleado = form.save()

            # 2. Prepara un mensaje de éxito verde/positivo para mostrar en la interfaz web.
            messages.success(request, f'Empleado {empleado} registrado correctamente.')

            # 3. Recarga la página limpiándola para que quede lista si se quiere registrar otro empleado.
            return redirect('registro')

        else:
            # Si HUBO ERRORES (ej. el documento tenía letras o la huella estaba repetida):
            
            # Muestra en la consola negra del servidor los detalles exactos del fallo para el desarrollador.
            print('ERRORES FORM:', form.errors.as_json())   # depuración

            # Prepara un aviso de advertencia/rojo para que el usuario sepa que la operación no se realizó.
            messages.error(request, 'No se pudo registrar el empleado. Revisa los campos.')

    else:
        # Si el método NO es POST (es decir, el usuario acaba de entrar a la URL por primera vez):
        # Creamos una ficha totalmente en blanco.
        form = EmpleadoForm()

    # --------------------------------------------------------------------------
    # PASO 4: MOSTRAR LA PÁGINA EN PANTALLA
    # --------------------------------------------------------------------------
    # 'render' une dos cosas:
    # 1. El diseño visual HTML ("paginas/registro.html").
    # 2. Los datos: le pasa la variable 'form' (sea que esté vacía o que contenga los errores a corregir).
    return render(request, "paginas/registro.html", {'form': form})

# ==============================================================================
# ==============================================================================

def validar_empleado(request):

    return render(request, "paginas/validar_empleado.html")

# ==============================================================================
# ==============================================================================

def registrar_entrada(request):
    if request.method == 'POST':
        # 1. Ejecutar la función serial que pide el '2' al Arduino
        resultado = verificar_huella()

        # Si el sensor falló, expiró el tiempo o no reconoció la huella
        if not resultado['ok']:
            messages.error(request, resultado['error'])
            return redirect('validar_empleado')

        huella_id = resultado['huella_id']

        # 2. Localizar al empleado en la BD
        try:
            empleado = Empleado.objects.get(huella_id=huella_id)
        except Empleado.DoesNotExist:
            messages.error(request, f'La huella ID #{huella_id} no está asignada a ningún empleado.')
            return redirect('validar_empleado')

        # 3. Regla: Validar si dejó un turno previo abierto (sin marcar salida)
        turno_abierto_previo = Registro.objects.filter(
            empleado=empleado,
            hora_salida__isnull=True
        ).exists()

        if turno_abierto_previo:
            messages.error(
                request,
                f'Error: {empleado} tiene un turno previo sin salida marcada. Debe cerrar ese turno primero.'
            )
            return redirect('validar_empleado')

        # 4. Regla: Validar si ya registró asistencia hoy
        hoy = timezone.localdate()
        if Registro.objects.filter(empleado=empleado, fecha=hoy).exists():
            messages.warning(request, f'{empleado} ya tiene un registro de asistencia para hoy.')
            return redirect('validar_empleado')

        # 5. Crear el registro oficial con la hora exacta del servidor
        ahora = timezone.now()
        Registro.objects.create(
            empleado=empleado,
            fecha=hoy,
            hora_entrada=ahora
        )

        messages.success(request, f'¡Bienvenido {empleado}! Entrada registrada a las {ahora.strftime("%H:%M:%S")}.')
        return redirect('validar_empleado')

    return redirect('validar_empleado')

# ==============================================================================
# ==============================================================================

def registrar_salida(request):
    if request.method == 'POST':
        resultado = verificar_huella()

        if not resultado['ok']:
            messages.error(request, resultado['error'])
            return redirect('validar_empleado')

        huella_id = resultado['huella_id']

        try:
            empleado = Empleado.objects.get(huella_id=huella_id)
        except Empleado.DoesNotExist:
            messages.error(request, f'La huella ID #{huella_id} no está asignada a ningún empleado.')
            return redirect('validar_empleado')

        # 1. Buscar el turno abierto que tenga este empleado
        registro_abierto = Registro.objects.filter(
            empleado=empleado,
            hora_salida__isnull=True
        ).order_by('-hora_entrada').first()

        # Si no hay entrada pendiente, no puede marcar salida
        if not registro_abierto:
            messages.error(
                request,
                f'No se encontró una entrada abierta para {empleado}. No puedes registrar salida sin haber entrado.'
            )
            return redirect('validar_empleado')

        # 2. Regla temporal: La salida no puede ser anterior a la entrada
        ahora = timezone.now()
        if ahora <= registro_abierto.hora_entrada:
            messages.error(request, 'Inconsistencia de reloj: La hora de salida debe ser posterior a la de entrada.')
            return redirect('validar_empleado')

        # 3. Guardar la salida en el MISMO registro
        registro_abierto.hora_salida = ahora
        registro_abierto.save()

        messages.success(request, f'¡Hasta luego {empleado}! Salida registrada a las {ahora.strftime("%H:%M:%S")}.')
        return redirect('validar_empleado')

    return redirect('validar_empleado')

# ==============================================================================
# ==============================================================================

def empleados(request):

    return render(request, "paginas/empleados.html")



