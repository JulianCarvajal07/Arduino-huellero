import threading
import time
import serial

PUERTO = 'COM5'            # Linux: '/dev/ttyUSB0' o '/dev/ttyACM0'
BAUDIOS = 9600             # debe coincidir con Serial.begin() del sketch
TIMEOUT_CAPTURA = 30       # segundos esperando el dedo

_lock = threading.Lock()
_ser = None


def _get_serial():
    global _ser
    if _ser is None or not _ser.is_open:
        _ser = serial.Serial(PUERTO, BAUDIOS, timeout=1)
        time.sleep(2)  # el Arduino se reinicia al abrir el puerto
    return _ser


def capturar_huella():
    global _ser
    with _lock:  # evita dos capturas simultáneas
        try:
            ser = _get_serial()
            ser.reset_input_buffer()
            ser.write(b'1\n')

            inicio = time.time()
            while time.time() - inicio < TIMEOUT_CAPTURA:
                linea = ser.readline().decode(errors='ignore').strip()
                if not linea:
                    continue
                if linea.startswith('OK:'):
                    return {'ok': True, 'huella_id': int(linea[3:])}
                if linea.startswith('ERROR'):
                    return {'ok': False, 'error': linea}
            return {'ok': False, 'error': 'Tiempo agotado, intenta de nuevo'}

        except serial.SerialException:
            _ser = None
            return {'ok': False, 'error': 'No se pudo abrir el puerto del sensor'}