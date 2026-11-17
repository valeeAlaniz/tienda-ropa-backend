from django.contrib import admin

from .models import HorarioAtencion, Sucursal, Turno


@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = ("nombre", "ciudad", "direccion", "telefono", "activo")
    list_filter = ("activo", "ciudad")
    search_fields = ("nombre", "ciudad", "direccion")
    ordering = ("nombre",)
    list_editable = ("activo",)


@admin.register(HorarioAtencion)
class HorarioAtencionAdmin(admin.ModelAdmin):
    list_display = ("sucursal", "dia_semana", "hora_apertura", "hora_cierre", "duracion_turno_min")
    list_filter = ("sucursal", "dia_semana")


@admin.register(Turno)
class TurnoAdmin(admin.ModelAdmin):
    list_display = ("fecha", "hora", "sucursal", "tipo", "estado", "cliente")
    list_filter = ("sucursal", "tipo", "estado", "fecha")