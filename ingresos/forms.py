# ==============================================================================
# IMPORTACIÓN DE MÓDULOS Y DEPENDENCIAS
# ==============================================================================

# Importamos las herramientas de formularios integradas en el framework Django.
# 'forms' contiene todas las clases y funciones necesarias para capturar y validar datos.
from django import forms

# Importamos la tabla o entidad 'Empleado' que se definió en el archivo models.py.
# Esto nos permite enlazar directamente este formulario con la estructura de la base de datos.
from .models import Empleado, Registro


# ==============================================================================
# DEFINICIÓN DE LA CLASE DEL FORMULARIO
# ==============================================================================

class EmpleadoForm(forms.ModelForm):
    """
    Formulario para el registro y edición de empleados.
    
    Hereda de 'forms.ModelForm', lo que significa que Django creará 
    automáticamente los campos basándose en los tipos de datos definidos 
    en el modelo 'Empleado' (char, int, etc.).
    """

    # --------------------------------------------------------------------------
    # CONFIGURACIÓN INTERNA DEL FORMULARIO (METADATOS)
    # --------------------------------------------------------------------------
    class Meta:
        # Indicamos cuál es el modelo de base de datos vinculado a este formulario.
        model = Empleado

        # Lista blanca de campos que se presentarán al usuario para ser completados.
        # Cualquier otro campo del modelo que no esté aquí no aparecerá en pantalla.
        fields = ['nombre', 'apellidos', 'documento', 'huella_id']

        # Personalización de los textos de error para que sean claros y en español.
        # Si ocurre alguna de estas infracciones, Django mostrará estos mensajes.
        error_messages = {
            'documento': {
                # Se dispara si el número de documento ya está registrado en la base de datos.
                'unique': 'Ya existe un empleado con este documento.'
            },
            'huella_id': {
                # Se dispara si el código de huella ya fue asignado a otro trabajador.
                'unique': 'Esta huella ya está asignada a otro empleado.',
                # Se dispara si el usuario intenta enviar el formulario dejando la huella en blanco.
                'required': 'Debes capturar la huella.',
                # Se dispara si el dato recibido del lector biométrico tiene un formato corrupto o incorrecto.
                'invalid': 'Huella inválida, intenta capturarla de nuevo.',
            },
        }

    # --------------------------------------------------------------------------
    # VALIDACIONES Y TRANSFORMACIONES PERSONALIZADAS (MÉTODOS CLEAN)
    # Django ejecuta estos métodos automáticamente tras validar las reglas básicas.
    # --------------------------------------------------------------------------

    def clean_documento(self):
        """
        Valida y limpia el campo 'documento'.
        Asegura que el dato contenga exclusivamente dígitos numéricos.
        """
        # 1. Recuperamos el valor introducido por el usuario desde el diccionario 'cleaned_data'.
        # 2. Aplicamos '.strip()' para suprimir espacios en blanco accidentales al inicio y al final.
        documento = self.cleaned_data['documento'].strip()

        # Comprobamos con '.isdigit()' si todos los caracteres de la cadena son números (0-9).
        # Si contiene letras, puntos, guiones o símbolos especiales, entra al bloque condicional.
        if not documento.isdigit():
            # Interrumpimos el proceso de guardado y arrojamos un error visible para el usuario.
            raise forms.ValidationError('El documento solo debe contener números.')

        # Si supera la validación, retornamos el valor limpio listo para ser almacenado.
        return documento

    def clean_nombre(self):
        """
        Normaliza el campo 'nombre' aplicando formato de nombre propio.
        """
        # self.cleaned_data['nombre'] obtiene el texto enviado.
        # .strip() elimina espacios sobrantes a los lados ("  Juan  " -> "Juan").
        # .title() pone la primera letra de cada palabra en mayúscula ("juan pablo" -> "Juan Pablo").
        return self.cleaned_data['nombre'].strip().title()

    def clean_apellidos(self):
        """
        Normaliza el campo 'apellidos' aplicando formato de nombre propio.
        """
        # Realiza el mismo saneamiento que en 'clean_nombre':
        # Elimina espacios exteriores y convierte a mayúscula inicial cada apellido ("gonzalez perez" -> "Gonzalez Perez").
        return self.cleaned_data['apellidos'].strip().title()


class MarcajeHuellaForm(forms.Form):
    """
    Formulario simple que captura únicamente el identificador 
    entregado por el lector biométrico tras pulsar el botón.
    """
    huella_id = forms.CharField(
        required=True,
        error_messages={
            'required': 'Debe capturar la huella en el lector.'
        }
    )

    def clean_huella_id(self):
        huella_id = self.cleaned_data['huella_id'].strip()
        # Verificamos si existe un empleado con esa huella
        try:
            empleado = Empleado.objects.get(huella_id=huella_id)
        except Empleado.DoesNotExist:
            raise forms.ValidationError('Huella no reconocida en el sistema.')
        
        # Devolvemos el objeto empleado directamente para usarlo en la vista
        return empleado