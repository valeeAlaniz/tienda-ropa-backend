from django.db import models


class Sucursal(models.Model):
    """Local de la tienda donde se retiran pedidos y se atienden los turnos."""

    nombre = models.CharField(max_length=100, unique=True)
    direccion = models.CharField(max_length=200)
    ciudad = models.CharField(max_length=100)
    telefono = models.CharField(max_length=30, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "sucursales"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.ciudad})"


class DiaSemana(models.IntegerChoices):
    # Mismos valores que date.weekday()
    LUNES = 0, "Lunes"
    MARTES = 1, "Martes"
    MIERCOLES = 2, "Miércoles"
    JUEVES = 3, "Jueves"
    VIERNES = 4, "Viernes"
    SABADO = 5, "Sábado"
    DOMINGO = 6, "Domingo"


class HorarioAtencion(models.Model):
    sucursal = models.ForeignKey(
        Sucursal, on_delete=models.CASCADE, related_name="horarios"
    )
    dia_semana = models.PositiveSmallIntegerField(choices=DiaSemana.choices)
    hora_apertura = models.TimeField()
    hora_cierre = models.TimeField()
    duracion_turno_min = models.PositiveSmallIntegerField(
        default=30, help_text="Duración de cada turno, en minutos"
    )

    class Meta:
        verbose_name = "horario de atención"
        verbose_name_plural = "horarios de atención"
        ordering = ["sucursal", "dia_semana", "hora_apertura"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(hora_apertura__lt=models.F("hora_cierre")),
                name="horario_apertura_antes_de_cierre",
            ),
            models.CheckConstraint(
                condition=models.Q(duracion_turno_min__gt=0),
                name="horario_duracion_positiva",
            ),
        ]

    def __str__(self):
        dia = DiaSemana(self.dia_semana).label
        return f"{self.sucursal} - {dia} {self.hora_apertura:%H:%M}-{self.hora_cierre:%H:%M}"


class TipoTurno(models.TextChoices):
    PRUEBA = "PRUEBA", "Prueba"
    RETIRO = "RETIRO", "Retiro"
    DEVOLUCION = "DEVOLUCION", "Devolución"


class EstadoTurno(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    CONFIRMADO = "CONFIRMADO", "Confirmado"
    CANCELADO = "CANCELADO", "Cancelado"
    COMPLETADO = "COMPLETADO", "Completado"


class Turno(models.Model):
    sucursal = models.ForeignKey(
        Sucursal, on_delete=models.PROTECT, related_name="turnos"
    )
    cliente = models.ForeignKey(
        "clientes.Cliente", on_delete=models.PROTECT, related_name="turnos"
    )
    tipo = models.CharField(max_length=20, choices=TipoTurno.choices)
    estado = models.CharField(
        max_length=20, choices=EstadoTurno.choices, default=EstadoTurno.PENDIENTE
    )
    fecha = models.DateField()
    hora = models.TimeField()
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha", "hora"]
        constraints = [
            # Evita la doble reserva: un mismo horario de una sucursal solo
            # puede tener un turno que no esté cancelado.
            models.UniqueConstraint(
                fields=["sucursal", "fecha", "hora"],
                condition=~models.Q(estado=EstadoTurno.CANCELADO),
                name="turno_unico_por_horario",
            ),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.sucursal.nombre} - {self.fecha} {self.hora:%H:%M}"