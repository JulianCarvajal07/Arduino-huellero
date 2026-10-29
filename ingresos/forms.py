from django import forms
from .models import Empleado

class EmpleadoForm(forms.ModelForm):
    class Meta:
        model = Empleado
        fields = ['nombre', 'apellidos', 'documento', 'huella_id']
        error_messages = {
            'documento': {'unique': 'Ya existe un empleado con este documento.'},
            'huella_id': {
                'unique': 'Esta huella ya está asignada a otro empleado.',
                'required': 'Debes capturar la huella.',
                'invalid': 'Huella inválida, intenta capturarla de nuevo.',
            },
        }

    def clean_documento(self):
        documento = self.cleaned_data['documento'].strip()
        if not documento.isdigit():
            raise forms.ValidationError('El documento solo debe contener números.')
        return documento

    def clean_nombre(self):
        return self.cleaned_data['nombre'].strip().title()

    def clean_apellidos(self):
        return self.cleaned_data['apellidos'].strip().title()