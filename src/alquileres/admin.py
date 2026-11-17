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

from .models import PrendaAlquiler  # noqa: E402


@admin.register(PrendaAlquiler)
class PrendaAlquilerAdmin(admin.ModelAdmin):
    list_display = (
        "nombre", "categoria", "talle", "color", "precio_por_dia", "destacado", "activo",
    )
    list_filter = ("categoria", "talle", "destacado", "activo")
    search_fields = ("nombre", "descripcion", "color")
