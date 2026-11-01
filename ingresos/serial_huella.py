import re          # Expresiones regulares: sirven para extraer el número del ID dentro de un texto
import threading   # Aporta el "lock" para que solo una operación use el sensor a la vez
import time        # Se usa para medir cuánto tiempo llevamos esperando una respuesta
import serial      # pyserial: permite hablar con el Arduino por el puerto USB (COM)

# ---------------------------------------------------------------------------
# CONFIGURACIÓN
# ---------------------------------------------------------------------------
PUERTO = 'COM5'            # Puerto USB donde está conectado el Arduino (se ve en el Administrador de dispositivos)
BAUDIOS = 9600             # Velocidad de comunicación; debe ser igual a Serial.begin(9600) del Arduino

# Tiempos máximos (en segundos) que Python espera cada respuesta antes de rendirse
TIMEOUT_MENU = 5           # Esperar el menú después de abrir el puerto
TIMEOUT_PROMPT = 5         # Esperar a que el Arduino pida el ID
TIMEOUT_CAPTURA = 60       # Registro: el usuario debe poner el dedo dos veces
TIMEOUT_VERIFICACION = 40  # Verificación: tiempo para colocar el dedo al marcar asistencia

# Candado compartido por todas las funciones. Solo hay un sensor y un puerto, así que
# si dos personas lanzaran una operación al mismo tiempo, los mensajes se mezclarían.
# Con el lock, la segunda operación espera a que termine la primera.
_lock = threading.Lock()


def _leer_hasta(ser, condicion, timeout):
    """
    Función auxiliar que usan todas las demás.

    Lee lo que imprime el Arduino línea por línea hasta que una línea cumpla la
    'condicion' (una función que recibe la línea y responde True o False).
    - Si la encuentra: devuelve esa línea.
    - Si pasa el 'timeout' sin encontrarla: devuelve None.
    """
    inicio = time.time()                              # Marca la hora de inicio
    while time.time() - inicio < timeout:             # Repite mientras no se acabe el tiempo
        # readline() espera hasta 1 segundo (timeout del Serial) una línea completa.
        # decode convierte los bytes a texto (errors='ignore' evita fallos con caracteres raros)
        # strip() quita espacios y saltos de línea sobrantes.
        linea = ser.readline().decode(errors='ignore').strip()
        if linea:                                     # Ignora las lecturas vacías
            print('ARDUINO:', linea)                  # depuración, quítalo cuando funcione
            if condicion(linea):                      # ¿Es la línea que estábamos esperando?
                return linea
    return None                                       # Se acabó el tiempo sin ver la línea


# ---------------------------------------------------------------------------
# REGISTRAR HUELLA (opción 1 del menú del Arduino)
# ---------------------------------------------------------------------------
def capturar_huella(huella_id):
    """
    Le pide al Arduino que registre una huella nueva con el ID indicado.
    Devuelve un diccionario: {'ok': True, 'huella_id': ...} o {'ok': False, 'error': '...'}.
    """
    with _lock:  # una captura a la vez
        ser = None   # Se define antes del try para poder cerrarlo en el finally
        try:
            # Abrir el puerto reinicia el Arduino UNO, por eso luego esperamos su menú.
            # timeout=1 significa que readline() espera como máximo 1 segundo por línea.
            ser = serial.Serial(PUERTO, BAUDIOS, timeout=1)

            # 1) Esperar el menú; si no aparece, forzar que se reimprima.
            # El menú termina con "...presione Enter:", así que usamos esa frase para detectarlo.
            es_menu = lambda l: 'presione enter' in l.lower()
            if _leer_hasta(ser, es_menu, TIMEOUT_MENU) is None:
                ser.write(b'\n')   # Enviar un Enter hace que el loop() del Arduino vuelva a mostrar el menú
                if _leer_hasta(ser, es_menu, TIMEOUT_MENU) is None:
                    return {'ok': False, 'error': 'El Arduino no respondió'}

            # 2) Escribir la opción 1 (como si la tecleáramos en el monitor serial)
            # y esperar a que el Arduino pregunte por el ID.
            ser.write(b'1\n')
            if _leer_hasta(ser, lambda l: 'ingrese el id' in l.lower(), TIMEOUT_PROMPT) is None:
                return {'ok': False, 'error': 'El Arduino no pidió el ID'}

            # 3) Enviar el ID libre (el número donde se guardará la huella en el sensor).
            # f'{huella_id}\n' lo convierte en texto y .encode() lo pasa a bytes.
            ser.write(f'{huella_id}\n'.encode())

            # 4) Esperar el resultado. Desde aquí el Arduino pide poner el dedo dos veces;
            # Python solo espera una de estas señales de que el proceso terminó:
            def es_final(l):
                bajo = l.lower()
                return (l.startswith('OK:') or 'exito' in bajo      # Se registró bien
                        or bajo.startswith('error')                  # Falló el guardado
                        or 'presione enter' in bajo)                 # Volvió el menú (falló sin mensaje de error)

            resultado = _leer_hasta(ser, es_final, TIMEOUT_CAPTURA)

            # 5) Interpretar el resultado
            if resultado is None:
                return {'ok': False, 'error': 'Tiempo agotado, intenta de nuevo'}
            bajo = resultado.lower()
            if resultado.startswith('OK:') or 'exito' in bajo:
                return {'ok': True, 'huella_id': huella_id}
            if bajo.startswith('error'):
                return {'ok': False, 'error': 'No se pudo guardar la huella'}
            # Si llegamos aquí, lo que apareció fue el menú: el Arduino abandonó el registro
            return {'ok': False, 'error': 'Las lecturas no coincidieron'}

        except serial.SerialException:
            # Pasa cuando el puerto no existe, está desconectado o lo usa otro programa
            return {'ok': False, 'error': 'No se pudo abrir el puerto del sensor'}
        finally:
            # El finally se ejecuta siempre (haya éxito o error): cierra el puerto.
            if ser is not None and ser.is_open:
                ser.close()   # la próxima captura reinicia el Arduino limpio


# ---------------------------------------------------------------------------
# VERIFICAR HUELLA (opción 2 del menú del Arduino)
# ---------------------------------------------------------------------------
def verificar_huella():
    """
    Opción 2: Activa el modo de verificación en el Arduino.
    Espera a que el empleado coloque el dedo y extrae el huella_id.
    Si se agotan los 5 intentos, cancela la operación.
    Devuelve {'ok': True, 'huella_id': '...'} o {'ok': False, 'error': '...'}.
    """
    with _lock:
        ser = None
        try:
            ser = serial.Serial(PUERTO, BAUDIOS, timeout=1)

            # 1) Sincronizar y esperar el menú principal (igual que en capturar_huella)
            es_menu = lambda l: 'presione enter' in l.lower()

            if _leer_hasta(ser, es_menu, TIMEOUT_MENU) is None:
                ser.write(b'\n')

                if _leer_hasta(ser, es_menu, TIMEOUT_MENU) is None:
                    return {
                        'ok': False,
                        'error': 'El sensor biométrico no responde'
                    }

            # 2) Enviar la opción 2. Desde aquí el Arduino se encarga de todo:
            # espera el dedo, compara, enciende el LED verde o rojo y permite hasta 5 intentos.
            ser.write(b'2\n')

            # 3) Definir qué mensajes del Arduino significan "ya hay un resultado".
            # Las demás líneas (como "Intento 2 de 5...") se ignoran y se sigue esperando.
            def es_respuesta_verificacion(l):
                bajo = l.lower()

                return (
                    'encontrada' in bajo               # "¡Huella ENCONTRADA! ID coincidente: #N"
                    or 'coincidente' in bajo
                    or 'no coincidencia' in bajo
                    or 'no encontrada' in bajo
                    or 'error' in bajo
                    or 'se agotaron los 5 intentos' in bajo   # Falló los 5 intentos
                    or 'tiempo agotado' in bajo               # Pasaron los 40 s dentro del Arduino
                )

            resultado = _leer_hasta(
                ser,
                es_respuesta_verificacion,
                TIMEOUT_VERIFICACION
            )

            # Si Python esperó los 40 s y no llegó ningún resultado
            if resultado is None:
                return {
                    'ok': False,
                    'error': 'Tiempo agotado. Coloca el dedo a tiempo en el sensor'
                }

            bajo = resultado.lower()

            # 4) Revisar los casos de fallo primero, del más específico al más general.
            # Cancelar si se agotaron los 5 intentos
            if 'se agotaron los 5 intentos' in bajo:
                return {
                    'ok': False,
                    'error': 'Operacion cancelada. Se agotaron los 5 intentos de reconocimiento'
                }

            if 'tiempo agotado' in bajo:
                return {
                    'ok': False,
                    'error': 'Tiempo agotado. Operacion cancelada'
                }

            # 5) Validar si no hubo coincidencia
            if 'no coincidencia' in bajo or 'no encontrada' in bajo:
                return {
                    'ok': False,
                    'error': 'Huella no reconocida en el sistema'
                }

            if 'error' in bajo:
                return {
                    'ok': False,
                    'error': 'Error durante la lectura del sensor'
                }

            # 6) Si no fue ningún fallo, es el éxito: "¡Huella ENCONTRADA! ID coincidente: #7".
            # La expresión r'#(\d+)' busca el símbolo # seguido de uno o más dígitos
            # y group(1) devuelve solo los dígitos (el ID, por ejemplo '7').
            coincidencia = re.search(r'#(\d+)', resultado)

            if coincidencia:
                return {
                    'ok': True,
                    'huella_id': coincidencia.group(1)   # Django usará este ID para buscar al colaborador
                }

            # Llegó un mensaje de éxito pero sin número
            return {
                'ok': False,
                'error': 'No se pudo determinar el ID de la huella'
            }

        except serial.SerialException:
            return {
                'ok': False,
                'error': 'No se pudo establecer conexión con el puerto COM'
            }

        finally:
            if ser is not None and ser.is_open:
                ser.close()


# ---------------------------------------------------------------------------
# ELIMINAR HUELLA (opción 3 del menú del Arduino)
# ---------------------------------------------------------------------------
def eliminar_huella(huella_id):
    """
    Opción 3: Elimina una huella específica de la memoria del sensor biométrico.
    Recibe el 'huella_id' asociado al empleado en la base de datos.
    """
    with _lock:
        ser = None
        try:
            ser = serial.Serial(PUERTO, BAUDIOS, timeout=1)

            # 1) Sincronizar y esperar el menú principal
            es_menu = lambda l: 'presione enter' in l.lower()
            if _leer_hasta(ser, es_menu, TIMEOUT_MENU) is None:
                ser.write(b'\n')
                if _leer_hasta(ser, es_menu, TIMEOUT_MENU) is None:
                    return {'ok': False, 'error': 'El sensor biométrico no responde'}

            # 2) Enviar la opción 3 (Eliminar huella)
            ser.write(b'3\n')

            # 3) Esperar a que el Arduino pida el ID a eliminar.
            # Antes de pedirlo, el Arduino imprime la lista de "IDs ocupados". Por eso se busca
            # específicamente "ingrese el id" y no solo "id", para no confundir ambas líneas.
            if _leer_hasta(ser, lambda l: 'ingrese el id' in l.lower(), TIMEOUT_PROMPT) is None:
                return {'ok': False, 'error': 'El Arduino no pidió el ID para eliminar'}

            # 4) Enviar el ID del empleado que viene desde la base de datos
            ser.write(f'{huella_id}\n'.encode())

            # 5) Evaluar la respuesta del sensor al intento de borrado
            def es_respuesta_eliminacion(l):
                bajo = l.lower()
                # Se busca 'eliminad' (sin la última letra) para que sirva tanto con
                # "eliminado" como con "eliminada".
                return (
                    'eliminad' in bajo or 'borrado' in bajo or 'exito' in bajo
                    or 'error' in bajo or 'no encontrado' in bajo
                )

            # Usamos un timeout corto (10 seg): borrar es instantáneo, no hay que esperar al usuario
            resultado = _leer_hasta(ser, es_respuesta_eliminacion, 10)

            if resultado is None:
                return {'ok': False, 'error': 'Tiempo agotado al intentar borrar la huella en el sensor'}

            bajo = resultado.lower()
            # Éxito: "Huella #N eliminada correctamente."
            if 'eliminad' in bajo or 'borrado' in bajo or 'exito' in bajo:
                return {'ok': True}

            # Si la huella ya no estaba en el sensor, igual se considera correcto
            # porque el objetivo (que no exista) ya se cumple; 'nota' explica la situación.
            if 'no encontrado' in bajo:
                return {'ok': True, 'nota': 'La huella ya no existía en el sensor'}

            if 'error' in bajo:
                return {'ok': False, 'error': 'El sensor reportó un error al intentar borrar la huella'}

            return {'ok': False, 'error': 'Respuesta desconocida del sensor al eliminar'}

        except serial.SerialException:
            return {'ok': False, 'error': 'No se pudo abrir el puerto del sensor'}
        finally:
            if ser is not None and ser.is_open:
                ser.close()