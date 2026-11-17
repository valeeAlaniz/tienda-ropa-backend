from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from catalogo.models import Prenda


class Alquiler(models.Model):
    """Alquiler de una prenda por un rango de fechas."""

    class Estado(models.TextChoices):
        RESERVADO = "reservado", "Reservado"
        RETIRADO = "retirado", "Retirado"
        DEVUELTO = "devuelto", "Devuelto"
        CANCELADO = "cancelado", "Cancelado"

    cliente = models.ForeignKey(
        "clientes.Cliente", on_delete=models.PROTECT, related_name="alquileres"
    )
    prenda = models.ForeignKey(
        "catalogo.Prenda", on_delete=models.PROTECT, related_name="alquileres"
    )
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.RESERVADO
    )
    precio_por_dia = models.DecimalField(max_digits=10, decimal_places=2)
    precio_total = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, editable=False
    )
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "alquileres"
        ordering = ["-fecha_inicio"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(fecha_fin__gte=models.F("fecha_inicio")),
                name="alquiler_fin_desde_inicio",
            ),
            models.CheckConstraint(
                condition=models.Q(precio_por_dia__gt=0),
                name="alquiler_precio_dia_positivo",
            ),
        ]

    def __str__(self):
        return f"Alquiler #{self.pk} - {self.prenda} ({self.get_estado_display()})"

    @property
    def dias(self):
        """Cantidad de días del alquiler, contando el primero y el último."""
        return (self.fecha_fin - self.fecha_inicio).days + 1

    def calcular_precio_total(self):
        return Decimal(str(self.precio_por_dia)) * self.dias

    def clean(self):
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValidationError(
                {"fecha_fin": "No puede ser anterior a la fecha de inicio."}
            )

    def save(self, *args, **kwargs):
        self.precio_total = self.calcular_precio_total()
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            kwargs["update_fields"] = set(update_fields) | {"precio_total"}
        super().save(*args, **kwargs)

class PrendaAlquiler(models.Model):
    """Prenda disponible para alquilar. Catálogo aparte del de venta."""

    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    precio_por_dia = models.DecimalField(max_digits=10, decimal_places=2)
    categoria = models.ForeignKey(
        "catalogo.Categoria",
        on_delete=models.PROTECT,
        related_name="prendas_alquiler",
    )
    talle = models.CharField(max_length=10, choices=Prenda.TALLES)
    color = models.CharField(max_length=50)
    imagen = models.URLField(max_length=500, blank=True)
    destacado = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "prenda de alquiler"
        verbose_name_plural = "prendas de alquiler"
        ordering = ["id"]

    def __str__(self):
        return f"{self.nombre} ({self.talle}, {self.color})"
