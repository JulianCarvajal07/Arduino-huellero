import re
import threading
import time
import serial

PUERTO = 'COM5'
BAUDIOS = 9600
TIMEOUT_MENU = 5           # espera del menú tras abrir el puerto
TIMEOUT_PROMPT = 5         # espera del prompt del ID
TIMEOUT_CAPTURA = 60       # el usuario coloca el dedo dos veces
TIMEOUT_VERIFICACION = 20   # tiempo para colocar el dedo al marcar asistencia

_lock = threading.Lock()


def _leer_hasta(ser, condicion, timeout):
    """Lee líneas hasta que condicion(linea) sea True. Devuelve la línea o None."""
    inicio = time.time()
    while time.time() - inicio < timeout:
        linea = ser.readline().decode(errors='ignore').strip()
        if linea:
            print('ARDUINO:', linea)   # depuración, quítalo cuando funcione
            if condicion(linea):
                return linea
    return None


def capturar_huella(huella_id):
    with _lock:  # una captura a la vez
        ser = None
        try:
            ser = serial.Serial(PUERTO, BAUDIOS, timeout=1)  # abrir reinicia el Uno

            # 1) Esperar el menú; si no aparece, forzar que se reimprima
            es_menu = lambda l: 'presione enter' in l.lower()
            if _leer_hasta(ser, es_menu, TIMEOUT_MENU) is None:
                ser.write(b'\n')
                if _leer_hasta(ser, es_menu, TIMEOUT_MENU) is None:
                    return {'ok': False, 'error': 'El Arduino no respondió'}

            # 2) Opción 1 y esperar el prompt del ID
            ser.write(b'1\n')
            if _leer_hasta(ser, lambda l: 'ingrese el id' in l.lower(), TIMEOUT_PROMPT) is None:
                return {'ok': False, 'error': 'El Arduino no pidió el ID'}

            # 3) Enviar el ID libre
            ser.write(f'{huella_id}\n'.encode())

            # 4) Esperar el resultado: éxito, error o regreso del menú
            def es_final(l):
                bajo = l.lower()
                return (l.startswith('OK:') or 'exito' in bajo
                        or bajo.startswith('error') or 'presione enter' in bajo)

            resultado = _leer_hasta(ser, es_final, TIMEOUT_CAPTURA)

            if resultado is None:
                return {'ok': False, 'error': 'Tiempo agotado, intenta de nuevo'}
            bajo = resultado.lower()
            if resultado.startswith('OK:') or 'exito' in bajo:
                return {'ok': True, 'huella_id': huella_id}
            if bajo.startswith('error'):
                return {'ok': False, 'error': 'No se pudo guardar la huella'}
            return {'ok': False, 'error': 'Las lecturas no coincidieron'}

        except serial.SerialException:
            return {'ok': False, 'error': 'No se pudo abrir el puerto del sensor'}
        finally:
            if ser is not None and ser.is_open:
                ser.close()   # la próxima captura reinicia el Arduino limpio


def verificar_huella():
    """
    Opción 2: Activa el modo de verificación en el Arduino.
    Espera a que el empleado pose el dedo y extrae el huella_id detectado.
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

            # 2) Enviar la opción 2 (Verificar / Buscar huella)
            ser.write(b'2\n')

            # 3) Evaluar la respuesta del sensor:
            # Reconoce mensajes comunes como "ID:#5", "Encontrado ID #5", "No coincidencia" o errores
            def es_respuesta_verificacion(l):
                bajo = l.lower()
                return (
                    'encontrada' in bajo          # "¡Huella ENCONTRADA! ..."
                    or 'coincidente' in bajo
                    or 'no coincidencia' in bajo
                    or 'no encontrada' in bajo
                    or 'error' in bajo
                )

            resultado = _leer_hasta(ser, es_respuesta_verificacion, TIMEOUT_VERIFICACION)

            if resultado is None:
                return {'ok': False, 'error': 'Tiempo agotado. Coloca el dedo a tiempo en el sensor'}

            bajo = resultado.lower()

            if 'no coincidencia' in bajo or 'no encontrada' in bajo:
                return {'ok': False, 'error': 'Huella no reconocida en el sistema'}

            if 'error' in bajo:
                return {'ok': False, 'error': 'Error durante la lectura del sensor'}

            coincidencia = re.search(r'#(\d+)', resultado)
            if coincidencia:
                return {'ok': True, 'huella_id': coincidencia.group(1)}

            return {'ok': False, 'error': 'No se pudo determinar el ID de la huella'}
        except serial.SerialException:
            return {'ok': False, 'error': 'No se pudo establecer conexión con el puerto COM'}
        finally:
            if ser is not None and ser.is_open:
                ser.close()


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

            # 3) Esperar a que el Arduino pida el ID a eliminar
            # CORRECCIÓN: Buscamos específicamente "ingrese el id" para no confundirlo con la lista de IDs ocupados
            if _leer_hasta(ser, lambda l: 'ingrese el id' in l.lower(), TIMEOUT_PROMPT) is None:
                return {'ok': False, 'error': 'El Arduino no pidió el ID para eliminar'}

            # 4) Enviar el ID del empleado que viene desde la base de datos
            ser.write(f'{huella_id}\n'.encode())

            # 5) Evaluar la respuesta del sensor al intento de borrado
            def es_respuesta_eliminacion(l):
                bajo = l.lower()
                # CORRECCIÓN: Usamos 'eliminad' para que detecte tanto "eliminado" como "eliminada"
                return (
                    'eliminad' in bajo or 'borrado' in bajo or 'exito' in bajo
                    or 'error' in bajo or 'no encontrado' in bajo
                )

            # Usamos un timeout corto (10 seg)
            resultado = _leer_hasta(ser, es_respuesta_eliminacion, 10)

            if resultado is None:
                return {'ok': False, 'error': 'Tiempo agotado al intentar borrar la huella en el sensor'}

            bajo = resultado.lower()
            if 'eliminad' in bajo or 'borrado' in bajo or 'exito' in bajo:
                return {'ok': True}
            
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