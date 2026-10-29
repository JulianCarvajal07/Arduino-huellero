import threading
import time
import serial

PUERTO = 'COM5'
BAUDIOS = 9600
TIMEOUT_MENU = 5           # espera del menú tras abrir el puerto
TIMEOUT_PROMPT = 5         # espera del prompt del ID
TIMEOUT_CAPTURA = 60       # el usuario coloca el dedo dos veces

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