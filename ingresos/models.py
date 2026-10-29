from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Empleado(models.Model):
    nombre = models.CharField(max_length=200, null=True, blank=True)
    apellidos = models.CharField(max_length=200, null=True, blank=True)
    documento = models.CharField(max_length=20, unique=True)
    huella_id = models.PositiveIntegerField(unique=True)

    class Meta:
        db_table = 'empleado'

    def __str__(self):
        return f'{self.nombre} {self.apellidos}'



class Registro(models.Model):
    empleado = models.ForeignKey(
        Empleado,
        on_delete=models.CASCADE,
        related_name='registros'
    )
    fecha = models.DateField(default=timezone.localdate)
    hora_entrada = models.DateTimeField(default=timezone.now)
    hora_salida = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'registro'
        ordering = ['-fecha', '-hora_entrada']
        constraints = [
            models.UniqueConstraint(
                fields=['empleado', 'fecha'],
                name='un_registro_por_empleado_por_dia'
            )
        ]

    def __str__(self):
        return f'{self.empleado} - {self.fecha}'

