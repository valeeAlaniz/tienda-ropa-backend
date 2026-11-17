from rest_framework import status

from .models import Pago, Pedido
from .tests import VentasBaseTestCase


class EstadosBaseTestCase(VentasBaseTestCase):
    def comprar(self, cantidad=2, tipo_entrega="RETIRO"):
        """El cliente compra por el checkout (descuenta stock) y devuelve el id del pedido."""
        self.client.force_authenticate(self.usuario)
        if tipo_entrega == "ENVIO":
            respuesta = self.client.post(
                "/api/ventas/pedidos/crear_completo/",
                {
                    "tipo_entrega": "ENVIO",
                    "direccion_envio": {
                        "calle": "Belgrano",
                        "numero": "45",
                        "ciudad": "Río Cuarto",
                        "codigo_postal": "5800",
                    },
                    "prendas": [{"prenda_id": self.prenda.id, "cantidad": cantidad}],
                },
                format="json",
            )
        else:
            respuesta = self.checkout([{"prenda_id": self.prenda.id, "cantidad": cantidad}])
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        return respuesta.data["id"]

    def cambiar(self, pedido_id, estado, usuario=None, **extra):
        self.client.force_authenticate(usuario or self.staff)
        return self.client.patch(
            f"/api/ventas/pedidos/{pedido_id}/cambiar_estado/",
            {"estado": estado, **extra},
            format="json",
        )

    def estado(self, pedido_id):
        return Pedido.objects.get(pk=pedido_id).estado


class TransicionesTests(EstadosBaseTestCase):
    def test_flujo_completo_retiro_pendiente_confirmado_entregado(self):
        pedido_id = self.comprar(tipo_entrega="RETIRO")
        for estado in ["CONFIRMADO", "ENTREGADO"]:
            respuesta = self.cambiar(pedido_id, estado)
            self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
            self.assertEqual(respuesta.data["estado"], estado)
            self.assertEqual(self.estado(pedido_id), estado)

    def test_flujo_completo_envio_pendiente_confirmado_enviado_entregado(self):
        pedido_id = self.comprar(tipo_entrega="ENVIO")
        for estado in ["CONFIRMADO", "ENVIADO", "ENTREGADO"]:
            respuesta = self.cambiar(pedido_id, estado)
            self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
            self.assertEqual(respuesta.data["estado"], estado)
            self.assertEqual(self.estado(pedido_id), estado)

    def test_retiro_bloquea_enviado(self):
        pedido_id = self.comprar(tipo_entrega="RETIRO")
        self.cambiar(pedido_id, "CONFIRMADO")

        respuesta = self.cambiar(pedido_id, "ENVIADO")
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.estado(pedido_id), "CONFIRMADO")

    def test_envio_bloquea_salto_directo_a_entregado(self):
        pedido_id = self.comprar(tipo_entrega="ENVIO")
        self.cambiar(pedido_id, "CONFIRMADO")

        respuesta = self.cambiar(pedido_id, "ENTREGADO")
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.estado(pedido_id), "CONFIRMADO")

    def test_transiciones_invalidas_desde_pendiente_se_rechazan(self):
        pedido_id = self.comprar(tipo_entrega="ENVIO")

        for destino in ["ENVIADO", "ENTREGADO"]:
            respuesta = self.cambiar(pedido_id, destino)
            self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(self.estado(pedido_id), "PENDIENTE")

    def test_no_se_vuelve_atras(self):
        pedido_id = self.comprar(tipo_entrega="ENVIO")
        self.cambiar(pedido_id, "CONFIRMADO")
        self.cambiar(pedido_id, "ENVIADO")

        respuesta = self.cambiar(pedido_id, "CONFIRMADO")

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.estado(pedido_id), "ENVIADO")

    def test_un_pedido_enviado_no_se_puede_cancelar(self):
        pedido_id = self.comprar(cantidad=2, tipo_entrega="ENVIO")
        self.cambiar(pedido_id, "CONFIRMADO")
        self.cambiar(pedido_id, "ENVIADO")

        respuesta = self.cambiar(pedido_id, "CANCELADO")

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.estado(pedido_id), "ENVIADO")
        self.prenda.refresh_from_db()
        self.assertEqual(self.prenda.stock, 8)

    def test_un_pedido_entregado_no_se_puede_cancelar(self):
        pedido_id = self.comprar(cantidad=3, tipo_entrega="RETIRO")
        for estado in ["CONFIRMADO", "ENTREGADO"]:
            self.cambiar(pedido_id, estado)

        respuesta = self.cambiar(pedido_id, "CANCELADO")

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.estado(pedido_id), "ENTREGADO")
        self.prenda.refresh_from_db()
        self.assertEqual(self.prenda.stock, 7)

    def test_un_pedido_cancelado_no_cambia_mas(self):
        pedido_id = self.comprar()
        self.cambiar(pedido_id, "CANCELADO")

        respuesta = self.cambiar(pedido_id, "CONFIRMADO")

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.estado(pedido_id), "CANCELADO")

    def test_estado_inexistente_o_ausente_se_rechaza(self):
        pedido_id = self.comprar()

        self.assertEqual(
            self.cambiar(pedido_id, "INVENTADO").status_code, status.HTTP_400_BAD_REQUEST
        )
        self.client.force_authenticate(self.staff)
        sin_estado = self.client.patch(
            f"/api/ventas/pedidos/{pedido_id}/cambiar_estado/", {}, format="json"
        )
        self.assertEqual(sin_estado.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.estado(pedido_id), "PENDIENTE")

    def test_checkout_con_sucursal_inactiva_se_rechaza(self):
        self.sucursal.activo = False
        self.sucursal.save(update_fields=["activo"])

        self.client.force_authenticate(self.usuario)
        respuesta = self.checkout([{"prenda_id": self.prenda.id, "cantidad": 1}])

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)


class PagoTests(EstadosBaseTestCase):
    def test_confirmar_crea_el_pago_aprobado_con_el_total_del_pedido(self):
        pedido_id = self.comprar(cantidad=2)

        self.cambiar(pedido_id, "CONFIRMADO", metodo="TRANSFERENCIA")

        pago = Pago.objects.get(pedido_id=pedido_id)
        self.assertTrue(pago.aprobado)
        self.assertEqual(pago.metodo, "TRANSFERENCIA")
        self.assertEqual(str(pago.monto), "20000.00")

    def test_confirmar_sin_metodo_usa_tarjeta(self):
        pedido_id = self.comprar()
        self.cambiar(pedido_id, "CONFIRMADO")
        self.assertEqual(Pago.objects.get(pedido_id=pedido_id).metodo, "TARJETA")

    def test_metodo_de_pago_invalido_no_confirma_ni_crea_pago(self):
        pedido_id = self.comprar()

        respuesta = self.cambiar(pedido_id, "CONFIRMADO", metodo="BITCOIN")

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.estado(pedido_id), "PENDIENTE")
        self.assertFalse(Pago.objects.filter(pedido_id=pedido_id).exists())

    def test_confirmar_dos_veces_no_duplica_el_pago(self):
        pedido_id = self.comprar()
        self.cambiar(pedido_id, "CONFIRMADO")

        segunda = self.cambiar(pedido_id, "CONFIRMADO")

        self.assertEqual(segunda.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Pago.objects.filter(pedido_id=pedido_id).count(), 1)

    def test_el_pedido_serializado_incluye_el_pago(self):
        pedido_id = self.comprar()
        respuesta = self.cambiar(pedido_id, "CONFIRMADO")
        self.assertTrue(respuesta.data["pago"]["aprobado"])


class StockTests(EstadosBaseTestCase):
    def test_el_checkout_descuenta_y_cancelar_desde_staff_lo_devuelve(self):
        pedido_id = self.comprar(cantidad=4)
        self.prenda.refresh_from_db()
        self.assertEqual(self.prenda.stock, 6)

        self.cambiar(pedido_id, "CANCELADO")

        self.prenda.refresh_from_db()
        self.assertEqual(self.prenda.stock, 10)

    def test_cancelar_un_pedido_confirmado_tambien_devuelve_el_stock(self):
        pedido_id = self.comprar(cantidad=3)
        self.cambiar(pedido_id, "CONFIRMADO")

        self.cambiar(pedido_id, "CANCELADO")

        self.prenda.refresh_from_db()
        self.assertEqual(self.prenda.stock, 10)

    def test_el_stock_no_se_devuelve_dos_veces(self):
        pedido_id = self.comprar(cantidad=4)
        self.cambiar(pedido_id, "CANCELADO")
        self.cambiar(pedido_id, "CANCELADO")  # rechazado: ya está cancelado

        self.prenda.refresh_from_db()
        self.assertEqual(self.prenda.stock, 10)

    def test_si_el_cliente_ya_cancelo_el_staff_no_puede_devolver_stock_de_nuevo(self):
        pedido_id = self.comprar(cantidad=4)
        self.client.force_authenticate(self.usuario)
        self.client.post(f"/api/ventas/pedidos/{pedido_id}/cancelar/")

        respuesta = self.cambiar(pedido_id, "CANCELADO")

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.prenda.refresh_from_db()
        self.assertEqual(self.prenda.stock, 10)

    def test_si_el_staff_ya_cancelo_el_cliente_no_puede_volver_a_cancelar(self):
        pedido_id = self.comprar(cantidad=4)
        self.cambiar(pedido_id, "CANCELADO")

        self.client.force_authenticate(self.usuario)
        respuesta = self.client.post(f"/api/ventas/pedidos/{pedido_id}/cancelar/")

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.prenda.refresh_from_db()
        self.assertEqual(self.prenda.stock, 10)


class PermisosEstadosTests(EstadosBaseTestCase):
    def test_el_cliente_no_puede_cambiar_estados_ni_siquiera_de_su_pedido(self):
        pedido_id = self.comprar()

        respuesta = self.cambiar(pedido_id, "CONFIRMADO", usuario=self.usuario)

        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.estado(pedido_id), "PENDIENTE")

    def test_anonimo_no_puede_cambiar_estados(self):
        pedido_id = self.comprar()
        self.client.force_authenticate(None)

        respuesta = self.client.patch(
            f"/api/ventas/pedidos/{pedido_id}/cambiar_estado/",
            {"estado": "CONFIRMADO"},
            format="json",
        )

        self.assertIn(
            respuesta.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
        )

    def test_el_staff_ve_y_gestiona_pedidos_de_cualquier_cliente(self):
        pedido_id = self.comprar()
        respuesta = self.cambiar(pedido_id, "CONFIRMADO")
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

    def test_el_cliente_no_cancela_pedidos_ajenos(self):
        ajeno, _ = self.crear_pedido(self.otro_cliente)
        self.client.force_authenticate(self.usuario)

        respuesta = self.client.post(f"/api/ventas/pedidos/{ajeno.id}/cancelar/")

        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.estado(ajeno.id), "PENDIENTE")

    def test_el_staff_no_usa_la_cancelacion_del_cliente_en_pedidos_ajenos(self):
        pedido_id = self.comprar()
        self.client.force_authenticate(self.staff)

        respuesta = self.client.post(f"/api/ventas/pedidos/{pedido_id}/cancelar/")

        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)
        