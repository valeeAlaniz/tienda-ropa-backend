from rest_framework import serializers
from .models import Pedido, DetallePedido, Pago

class DetallePedidoSerializer(serializers.ModelSerializer):
    prenda_nombre = serializers.ReadOnlyField(source='prenda.nombre')

    class Meta: 
        model = DetallePedido
        fields = ['id', 'pedido', 'prenda', 'prenda_nombre', 'cantidad', 'precio_unitario']


class PagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pago
        fields = ['id', 'pedido', 'metodo', 'monto', 'fecha_monto', 'aprobado', 'transaccion_id']


class PedidoSerializer(serializers.ModelSerializer):
    detalles_pedido = DetallePedidoSerializer(many=True, read_only=True)
    pago = PagoSerializer(read_only=True)

    class Meta:
        model = Pedido
        fields = [
            'id',
            'cliente',
            'fecha_venta',
            'monto_total',
            'estado',
            'tipo_entrega',
            'sucursal_retiro',
            'direccion_envio',
            'detalles_pedido',
            'pago'
        ]
        read_only_fields = ['cliente', 'fecha_venta', 'monto_total', 'estado', 'pago']