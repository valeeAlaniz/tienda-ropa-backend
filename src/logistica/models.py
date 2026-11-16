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