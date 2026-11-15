from django.contrib import admin

from .models import Pedido, DetallePedido, Pago


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "fecha_venta", "estado", "monto_total", "tipo_entrega")
    list_filter = ("estado", "tipo_entrega", "fecha_venta")
    search_fields = ("id", "estado", "cliente__nombre", "cliente__apellido")
    ordering = ("-fecha_venta",)


@admin.register(DetallePedido)
class DetallePedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "pedido", "prenda", "cantidad", "precio_unitario")
    list_filter = ("pedido",)
    search_fields = ("pedido__id", "prenda__nombre")


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ("id", "pedido", "monto", "fecha_monto", "metodo", "aprobado")
    list_filter = ("metodo", "aprobado", "fecha_monto")
    search_fields = ("id", "pedido__id", "metodo", "transaccion_id")
    ordering = ("-fecha_monto",)
