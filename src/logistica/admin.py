from django.contrib import admin

from .models import Sucursal


@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = ("nombre", "ciudad", "direccion", "telefono", "activo")
    list_filter = ("activo", "ciudad")
    search_fields = ("nombre", "ciudad", "direccion")
    ordering = ("nombre",)
    list_editable = ("activo",)