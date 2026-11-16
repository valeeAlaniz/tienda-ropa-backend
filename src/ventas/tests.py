from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from catalogo.models import Categoria, Prenda
from clientes.models import Cliente, Direccion
from logistica.models import Sucursal

from .models import DetallePedido, Pago, Pedido


class VentasBaseTestCase(APITestCase):
    def setUp(self):
        User = get_user_model()

        self.usuario = User.objects.create_user(username="cliente1", password="Clave-Test-2026!")
        self.otro_usuario = User.objects.create_user(username="cliente2", password="Clave-Test-2026!")
        self.staff = User.objects.create_user(
            username="staff", password="Clave-Test-2026!", is_staff=True
        )

        self.cliente = Cliente.objects.create(
            usuario=self.usuario, nombre="Cliente", apellido="Uno", email="cliente1@example.test"
        )
        self.otro_cliente = Cliente.objects.create(
            usuario=self.otro_usuario, nombre="Cliente", apellido="Dos", email="cliente2@example.test"
        )

        categoria = Categoria.objects.create(nombre="Vestidos test")
        self.prenda = Prenda.objects.create(
            nombre="Vestido test",
            descripcion="Vestido de prueba",
            talle="M",
            color="Negro",
            precio="10000.00",
            stock=10,
            categoria=categoria,
        )

        self.sucursal = Sucursal.objects.create(
            nombre="Centro", direccion="San Martín 123", ciudad="Río Cuarto"
        )

    def crear_pedido(self, cliente, monto="10000.00"):
        pedido = Pedido.objects.create(
            cliente=cliente,
            tipo_entrega="RETIRO",
            sucursal_retiro=self.sucursal,
            monto_total=monto,
        )
        detalle = DetallePedido.objects.create(
            pedido=pedido, prenda=self.prenda, cantidad=1, precio_unitario=monto
        )
        return pedido, detalle

    def checkout(self, prendas, **extra):
        datos = {
            "tipo_entrega": "RETIRO",
            "sucursal_retiro": self.sucursal.id,
            "prendas": prendas,
        }
        datos.update(extra)
        return self.client.post("/api/ventas/pedidos/crear_completo/", datos, format="json")


class VentasPermisosTests(VentasBaseTestCase):
    def setUp(self):
        super().setUp()
        self.pedido, self.detalle = self.crear_pedido(self.cliente)
        self.otro_pedido, self.otro_detalle = self.crear_pedido(self.otro_cliente)

    def test_cliente_solo_consulta_sus_pedidos(self):
        self.client.force_authenticate(self.usuario)

        respuesta = self.client.get("/api/ventas/pedidos/")
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["count"], 1)
        self.assertEqual(respuesta.data["results"][0]["id"], self.pedido.id)

        propio = self.client.get(f"/api/ventas/pedidos/{self.pedido.id}/")
        ajeno = self.client.get(f"/api/ventas/pedidos/{self.otro_pedido.id}/")
        self.assertEqual(propio.status_code, status.HTTP_200_OK)
        self.assertEqual(ajeno.status_code, status.HTTP_404_NOT_FOUND)

    def test_usuario_anonimo_no_ve_pedidos(self):
        respuesta = self.client.get("/api/ventas/pedidos/")
        self.assertIn(
            respuesta.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
        )

    def test_cliente_no_puede_hacer_crud_directo_de_pedidos(self):
        self.client.force_authenticate(self.usuario)

        crear = self.client.post(
            "/api/ventas/pedidos/",
            {"cliente": self.cliente.id, "tipo_entrega": "RETIRO"},
            format="json",
        )
        editar = self.client.patch(
            f"/api/ventas/pedidos/{self.pedido.id}/", {"estado": "CONFIRMADO"}, format="json"
        )
        eliminar = self.client.delete(f"/api/ventas/pedidos/{self.pedido.id}/")

        self.assertEqual(crear.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(editar.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(eliminar.status_code, status.HTTP_403_FORBIDDEN)

        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, "PENDIENTE")

    def test_cliente_solo_consulta_sus_detalles(self):
        self.client.force_authenticate(self.usuario)

        respuesta = self.client.get("/api/ventas/detalles/")
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["count"], 1)

        ajeno = self.client.get(f"/api/ventas/detalles/{self.otro_detalle.id}/")
        self.assertEqual(ajeno.status_code, status.HTTP_404_NOT_FOUND)

    def test_cliente_no_puede_crear_editar_ni_borrar_detalles(self):
        self.client.force_authenticate(self.usuario)

        crear = self.client.post(
            "/api/ventas/detalles/",
            {
                "pedido": self.pedido.id,
                "prenda": self.prenda.id,
                "cantidad": 2,
                "precio_unitario": "10000.00",
            },
            format="json",
        )
        editar = self.client.patch(
            f"/api/ventas/detalles/{self.detalle.id}/", {"cantidad": 5}, format="json"
        )
        eliminar = self.client.delete(f"/api/ventas/detalles/{self.detalle.id}/")

        self.assertEqual(crear.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(editar.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(eliminar.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_ve_todos_los_pedidos_y_puede_editar_detalles(self):
        self.client.force_authenticate(self.staff)

        listado = self.client.get("/api/ventas/pedidos/")
        editar_detalle = self.client.patch(
            f"/api/ventas/detalles/{self.detalle.id}/", {"cantidad": 2}, format="json"
        )

        self.assertEqual(listado.data["count"], 2)
        self.assertEqual(editar_detalle.status_code, status.HTTP_200_OK)

    def test_el_estado_no_se_edita_por_patch_ni_siquiera_el_staff(self):
        # El estado solo cambia por cambiar_estado, que cuida el stock y el pago.
        self.client.force_authenticate(self.staff)
        self.client.patch(
            f"/api/ventas/pedidos/{self.pedido.id}/", {"estado": "ENTREGADO"}, format="json"
        )
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, "PENDIENTE")

    def test_pagos_son_solo_lectura_y_filtrados_por_cliente(self):
        Pago.objects.create(pedido=self.pedido, metodo="EFECTIVO", monto="10000.00")
        Pago.objects.create(pedido=self.otro_pedido, metodo="EFECTIVO", monto="10000.00")

        self.client.force_authenticate(self.usuario)
        respuesta = self.client.get("/api/ventas/pagos/")
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["count"], 1)

        crear = self.client.post(
            "/api/ventas/pagos/",
            {"pedido": self.pedido.id, "metodo": "EFECTIVO", "monto": "10000"},
            format="json",
        )
        self.assertEqual(crear.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class CheckoutTests(VentasBaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.usuario)

    def test_compra_con_retiro_crea_pedido_detalle_y_descuenta_stock(self):
        respuesta = self.checkout([{"prenda_id": self.prenda.id, "cantidad": 3}])

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        pedido = Pedido.objects.get(pk=respuesta.data["id"])
        self.assertEqual(pedido.cliente, self.cliente)
        self.assertEqual(pedido.estado, "PENDIENTE")
        self.assertEqual(pedido.detalles_pedido.count(), 1)

        self.prenda.refresh_from_db()
        self.assertEqual(self.prenda.stock, 7)

    def test_el_total_es_la_suma_de_precio_por_cantidad(self):
        otra = Prenda.objects.create(
            nombre="Saco test", talle="L", color="Azul", precio="2500.50",
            stock=5, categoria=self.prenda.categoria,
        )
        respuesta = self.checkout([
            {"prenda_id": self.prenda.id, "cantidad": 2},   # 2 x 10000.00
            {"prenda_id": otra.id, "cantidad": 3},          # 3 x 2500.50
        ])

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        self.assertEqual(str(respuesta.data["monto_total"]), "27501.50")

    def test_el_precio_unitario_sale_del_catalogo_y_no_del_cliente(self):
        respuesta = self.checkout(
            [{"prenda_id": self.prenda.id, "cantidad": 1, "precio": "1.00"}]
        )
        detalle = DetallePedido.objects.get(pedido_id=respuesta.data["id"])
        self.assertEqual(str(detalle.precio_unitario), "10000.00")

    def test_stock_insuficiente_rechaza_todo_y_no_descuenta_nada(self):
        otra = Prenda.objects.create(
            nombre="Saco test", talle="L", color="Azul", precio="2500.00",
            stock=1, categoria=self.prenda.categoria,
        )
        respuesta = self.checkout([
            {"prenda_id": self.prenda.id, "cantidad": 2},
            {"prenda_id": otra.id, "cantidad": 5},  # no alcanza
        ])

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Pedido.objects.count(), 0)
        self.prenda.refresh_from_db()
        self.assertEqual(self.prenda.stock, 10)

    def test_cantidades_invalidas_se_rechazan(self):
        for cantidad in (0, -2, 1.5, "abc", True, None):
            with self.subTest(cantidad=cantidad):
                respuesta = self.checkout([{"prenda_id": self.prenda.id, "cantidad": cantidad}])
                self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

        self.prenda.refresh_from_db()
        self.assertEqual(self.prenda.stock, 10)  # una cantidad negativa no puede sumar stock
        self.assertEqual(Pedido.objects.count(), 0)

    def test_prenda_inactiva_o_inexistente_se_rechaza(self):
        self.prenda.activo = False
        self.prenda.save()
        inactiva = self.checkout([{"prenda_id": self.prenda.id, "cantidad": 1}])
        inexistente = self.checkout([{"prenda_id": 99999, "cantidad": 1}])

        self.assertEqual(inactiva.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(inexistente.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pedido_sin_prendas_se_rechaza(self):
        self.assertEqual(self.checkout([]).status_code, status.HTTP_400_BAD_REQUEST)

    def test_retiro_exige_sucursal_activa(self):
        sin_sucursal = self.client.post(
            "/api/ventas/pedidos/crear_completo/",
            {"tipo_entrega": "RETIRO", "prendas": [{"prenda_id": self.prenda.id, "cantidad": 1}]},
            format="json",
        )
        self.sucursal.activo = False
        self.sucursal.save()
        inactiva = self.checkout([{"prenda_id": self.prenda.id, "cantidad": 1}])

        self.assertEqual(sin_sucursal.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(inactiva.status_code, status.HTTP_400_BAD_REQUEST)

    def test_envio_a_domicilio_guarda_la_direccion(self):
        respuesta = self.client.post(
            "/api/ventas/pedidos/crear_completo/",
            {
                "tipo_entrega": "ENVIO",
                "direccion_envio": {
                    "calle": "Belgrano", "numero": "45",
                    "ciudad": "Río Cuarto", "codigo_postal": "5800",
                },
                "prendas": [{"prenda_id": self.prenda.id, "cantidad": 1}],
            },
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        pedido = Pedido.objects.get(pk=respuesta.data["id"])
        self.assertEqual(pedido.direccion_envio.calle, "Belgrano")
        self.assertEqual(pedido.direccion_envio.cliente, self.cliente)

    def test_envio_con_direccion_incompleta_no_deja_nada_guardado(self):
        respuesta = self.client.post(
            "/api/ventas/pedidos/crear_completo/",
            {
                "tipo_entrega": "ENVIO",
                "direccion_envio": {"calle": "Belgrano", "numero": "", "ciudad": "X", "codigo_postal": "1"},
                "prendas": [{"prenda_id": self.prenda.id, "cantidad": 1}],
            },
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Direccion.objects.count(), 0)
        self.assertEqual(Pedido.objects.count(), 0)

    def test_usuario_sin_perfil_de_cliente_no_puede_comprar(self):
        self.client.force_authenticate(self.staff)  # el staff de prueba no tiene Cliente
        respuesta = self.checkout([{"prenda_id": self.prenda.id, "cantidad": 1}])
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_anonimo_no_puede_comprar(self):
        self.client.force_authenticate(None)
        respuesta = self.checkout([{"prenda_id": self.prenda.id, "cantidad": 1}])
        self.assertIn(
            respuesta.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
        )


class CancelacionTests(VentasBaseTestCase):
    def test_cliente_cancela_su_pedido_pendiente_y_recupera_el_stock(self):
        self.client.force_authenticate(self.usuario)
        creado = self.checkout([{"prenda_id": self.prenda.id, "cantidad": 4}])
        self.prenda.refresh_from_db()
        self.assertEqual(self.prenda.stock, 6)

        cancelado = self.client.post(f"/api/ventas/pedidos/{creado.data['id']}/cancelar/")

        self.assertEqual(cancelado.status_code, status.HTTP_200_OK)
        self.assertEqual(cancelado.data["estado"], "CANCELADO")
        self.prenda.refresh_from_db()
        self.assertEqual(self.prenda.stock, 10)

    def test_no_se_puede_cancelar_un_pedido_ajeno_ni_uno_ya_confirmado(self):
        ajeno, _ = self.crear_pedido(self.otro_cliente)
        confirmado, _ = self.crear_pedido(self.cliente)
        Pedido.objects.filter(pk=confirmado.pk).update(estado="CONFIRMADO")

        self.client.force_authenticate(self.usuario)
        r_ajeno = self.client.post(f"/api/ventas/pedidos/{ajeno.id}/cancelar/")
        r_confirmado = self.client.post(f"/api/ventas/pedidos/{confirmado.id}/cancelar/")

        self.assertEqual(r_ajeno.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(r_confirmado.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cambiar_estado_es_solo_para_staff(self):
        pedido, _ = self.crear_pedido(self.cliente)

        self.client.force_authenticate(self.usuario)
        denegado = self.client.patch(
            f"/api/ventas/pedidos/{pedido.id}/cambiar_estado/", {"estado": "CONFIRMADO"}, format="json"
        )
        self.assertEqual(denegado.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.staff)
        permitido = self.client.patch(
            f"/api/ventas/pedidos/{pedido.id}/cambiar_estado/", {"estado": "CONFIRMADO"}, format="json"
        )
        self.assertEqual(permitido.status_code, status.HTTP_200_OK)
        self.assertTrue(Pago.objects.filter(pedido=pedido, aprobado=True).exists())

class TransicionesEstadoTests(VentasBaseTestCase):
    def test_retiro_confirmado_a_entregado(self):
        """Un pedido de RETIRO pasa correctamente de CONFIRMADO a ENTREGADO."""
        pedido, _ = self.crear_pedido(self.cliente)
        pedido.estado = "CONFIRMADO"
        pedido.save()

        self.client.force_authenticate(self.staff)
        response = self.client.patch(
            f"/api/ventas/pedidos/{pedido.id}/cambiar_estado/",
            {"estado": "ENTREGADO"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["estado"], "ENTREGADO")

    def test_retiro_bloquea_enviado(self):
        """Un pedido de RETIRO NO puede pasar al estado ENVIADO."""
        pedido, _ = self.crear_pedido(self.cliente)
        pedido.estado = "CONFIRMADO"
        pedido.save()

        self.client.force_authenticate(self.staff)
        response = self.client.patch(
            f"/api/ventas/pedidos/{pedido.id}/cambiar_estado/",
            {"estado": "ENVIADO"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_envio_bloquea_salto_directo_a_entregado(self):
        """Un pedido de ENVIO NO puede pasar de CONFIRMADO a ENTREGADO sin pasar por ENVIADO."""
        direccion = Direccion.objects.create(
            cliente=self.cliente, calle="Belgrano", numero="100", ciudad="Río Cuarto", codigo_postal="5800"
        )
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            tipo_entrega="ENVIO",
            direccion_envio=direccion,
            estado="CONFIRMADO",
            monto_total="10000.00",
        )

        self.client.force_authenticate(self.staff)
        response = self.client.patch(
            f"/api/ventas/pedidos/{pedido.id}/cambiar_estado/",
            {"estado": "ENTREGADO"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
