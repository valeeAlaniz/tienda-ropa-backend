from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import F
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from catalogo.models import Prenda
from clientes.models import Direccion
from clientes.permissions import filtrar_por_cliente
from logistica.models import Sucursal

from .models import DetallePedido, Pago, Pedido
from .serializers import DetallePedidoSerializer, PagoSerializer, PedidoSerializer


# Estados a los que se puede pasar según el tipo de entrega. ENTREGADO y CANCELADO son finales.
TRANSICIONES = {
    "PENDIENTE": {"CONFIRMADO", "CANCELADO"},
    "CONFIRMADO": {"ENVIADO", "ENTREGADO", "CANCELADO"},
    "ENVIADO": {"ENTREGADO"},
    "ENTREGADO": set(),
    "CANCELADO": set(),
}


def _cantidad_entera(valor):
    """Convierte la cantidad recibida a int positivo o lanza ValueError."""
    if isinstance(valor, bool):
        raise ValueError("La cantidad debe ser un número entero.")

    try:
        decimal = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("La cantidad debe ser un número entero.")

    if not decimal.is_finite() or decimal != decimal.to_integral_value():
        raise ValueError("La cantidad debe ser un número entero.")

    cantidad = int(decimal)
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser mayor que cero.")
    return cantidad


def _devolver_stock(pedido):
    """Suma de nuevo al stock las unidades de cada detalle del pedido."""
    for detalle in pedido.detalles_pedido.all():
        Prenda.objects.filter(pk=detalle.prenda_id).update(
            stock=F("stock") + detalle.cantidad
        )


class PedidoViewSet(viewsets.ModelViewSet):
    serializer_class = PedidoSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["estado", "tipo_entrega", "cliente__nombre"]
    ordering_fields = ["fecha_venta", "monto_total"]

    def get_permissions(self):
        # El cliente compra solo por crear_completo; el CRUD directo es del staff.
        if self.action in {"create", "update", "partial_update", "destroy", "cambiar_estado"}:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = Pedido.objects.all().order_by("-fecha_venta")
        return filtrar_por_cliente(queryset, self.request.user, "cliente")

    @action(detail=False, methods=["post"], url_path="crear_completo")
    def crear_completo(self, request):
        cliente = getattr(request.user, "cliente", None)
        if cliente is None:
            return Response(
                {"error": "El usuario no tiene un perfil de cliente."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        prendas = request.data.get("prendas", [])
        tipo_entrega = request.data.get("tipo_entrega")

        if not isinstance(prendas, list) or not prendas:
            return Response(
                {"error": "El pedido debe contener prendas."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if tipo_entrega not in ["RETIRO", "ENVIO"]:
            return Response(
                {"error": "Tipo de entrega inválido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                direccion = None
                sucursal = None

                if tipo_entrega == "ENVIO":
                    datos = request.data.get("direccion_envio")
                    if not isinstance(datos, dict):
                        raise ValueError("Debés indicar los datos de la dirección.")

                    campos = ["calle", "numero", "ciudad", "codigo_postal"]
                    if any(not str(datos.get(c, "")).strip() for c in campos):
                        raise ValueError("Todos los campos de la dirección son obligatorios.")

                    direccion = Direccion.objects.create(
                        cliente=cliente,
                        calle=str(datos["calle"]).strip(),
                        numero=str(datos["numero"]).strip(),
                        ciudad=str(datos["ciudad"]).strip(),
                        codigo_postal=str(datos["codigo_postal"]).strip(),
                    )
                else:
                    sucursal_id = request.data.get("sucursal_retiro")
                    if not sucursal_id:
                        raise ValueError("Debés indicar una sucursal de retiro.")
                    try:
                        sucursal = Sucursal.objects.get(pk=sucursal_id, activo=True)
                    except (Sucursal.DoesNotExist, ValueError, TypeError):
                        raise ValueError("La sucursal no existe o no está disponible.")

                pedido = Pedido.objects.create(
                    cliente=cliente,
                    tipo_entrega=tipo_entrega,
                    direccion_envio=direccion,
                    sucursal_retiro=sucursal,
                    monto_total=Decimal("0.00"),
                )

                total = Decimal("0.00")

                for item in prendas:
                    if not isinstance(item, dict):
                        raise ValueError("Formato de prenda inválido.")

                    prenda_id = item.get("prenda_id")
                    if prenda_id is None or item.get("cantidad") is None:
                        raise ValueError("Faltan datos de la prenda.")

                    cantidad = _cantidad_entera(item["cantidad"])

                    try:
                        prenda = Prenda.objects.get(pk=prenda_id, activo=True)
                    except (Prenda.DoesNotExist, ValueError, TypeError):
                        raise ValueError("Una de las prendas no existe o no está activa.")

                    # Descuento atómico: si no alcanza el stock, no actualiza nada.
                    actualizado = Prenda.objects.filter(
                        pk=prenda.pk, activo=True, stock__gte=cantidad
                    ).update(stock=F("stock") - cantidad)

                    if actualizado == 0:
                        raise ValueError(f"Stock insuficiente para la prenda {prenda.nombre}.")

                    DetallePedido.objects.create(
                        pedido=pedido,
                        prenda=prenda,
                        cantidad=cantidad,
                        precio_unitario=prenda.precio,
                    )
                    total += prenda.precio * cantidad

                pedido.monto_total = total
                pedido.save(update_fields=["monto_total"])

        except (ValueError, InvalidOperation, TypeError, KeyError) as error:
            return Response(
                {"error": str(error) or "Los datos del pedido son inválidos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(PedidoSerializer(pedido).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch"], url_path="cambiar_estado")
    def cambiar_estado(self, request, pk=None):
        """Solo staff: aplica una transición válida, crea el pago al confirmar
        y devuelve el stock al cancelar."""
        pedido = self.get_object()
        nuevo_estado = request.data.get("estado")

        if nuevo_estado not in TRANSICIONES:
            return Response({"error": "Estado inválido."}, status=status.HTTP_400_BAD_REQUEST)

        metodo = request.data.get("metodo", "TARJETA")
        if nuevo_estado == "CONFIRMADO" and metodo not in [m[0] for m in Pago.METODO_PAGO_CHOICES]:
            return Response({"error": "Método de pago inválido."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            pedido = Pedido.objects.select_for_update().get(pk=pedido.pk)

            if nuevo_estado not in TRANSICIONES[pedido.estado]:
                return Response(
                    {"error": f"No se puede pasar de {pedido.estado} a {nuevo_estado}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if nuevo_estado == "ENVIADO" and pedido.tipo_entrega == "RETIRO":
                return Response(
                    {"error": "Un pedido de retiro no puede ser marcado como enviado."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if nuevo_estado == "ENTREGADO" and pedido.tipo_entrega == "ENVIO" and pedido.estado != "ENVIADO":
                return Response(
                    {"error": "Un pedido de envío debe pasar por el estado enviado antes de ser entregado."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if nuevo_estado == "CONFIRMADO":
                Pago.objects.create(
                    pedido=pedido, metodo=metodo, monto=pedido.monto_total, aprobado=True
                )
            elif nuevo_estado == "CANCELADO":
                _devolver_stock(pedido)

            pedido.estado = nuevo_estado
            pedido.save(update_fields=["estado"])

        return Response(PedidoSerializer(pedido).data)

    @action(detail=True, methods=["post"], url_path="cancelar")
    def cancelar(self, request, pk=None):
        """El cliente cancela su propio pedido pendiente y se devuelve el stock."""
        pedido = self.get_object()

        if pedido.cliente.usuario != request.user:
            return Response({"error": "No es tu pedido."}, status=status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            pedido = Pedido.objects.select_for_update().get(pk=pedido.pk)

            if pedido.estado != "PENDIENTE":
                return Response(
                    {"error": "Solo se pueden cancelar pedidos en estado pendiente."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            _devolver_stock(pedido)
            pedido.estado = "CANCELADO"
            pedido.save(update_fields=["estado"])

        return Response(PedidoSerializer(pedido).data)


class DetallePedidoViewSet(viewsets.ModelViewSet):
    serializer_class = DetallePedidoSerializer

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = DetallePedido.objects.all().order_by("id")
        return filtrar_por_cliente(queryset, self.request.user, "pedido__cliente")


class PagoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PagoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Pago.objects.all().order_by("-fecha_monto", "-id")
        return filtrar_por_cliente(queryset, self.request.user, "pedido__cliente")
