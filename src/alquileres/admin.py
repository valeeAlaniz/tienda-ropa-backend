from django.contrib import admin

from .models import Alquiler


@admin.register(Alquiler)
class AlquilerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cliente",
        "prenda",
        "fecha_inicio",
        "fecha_fin",
        "estado",
        "precio_total",
    )
    list_filter = ("estado", "fecha_inicio")
    search_fields = ("cliente__nombre", "cliente__apellido", "prenda__nombre")
    readonly_fields = ("precio_total", "creado")
    date_hierarchy = "fecha_inicio"