from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from .models import Sucursal

URL = "/api/logistica/sucursales/"


class SucursalApiTests(APITestCase):
    def setUp(self):
        self.cliente = User.objects.create_user("cliente", password="clave12345")
        self.staff = User.objects.create_user(
            "staff", password="clave12345", is_staff=True
        )
        self.centro = Sucursal.objects.create(
            nombre="Centro", direccion="San Martín 123", ciudad="Río Cuarto"
        )
        self.norte = Sucursal.objects.create(
            nombre="Norte", direccion="Belgrano 456", ciudad="Córdoba"
        )

    def datos(self, **extra):
        base = {
            "nombre": "Sur",
            "direccion": "Sarmiento 789",
            "ciudad": "Río Cuarto",
            "telefono": "358 4000000",
        }
        base.update(extra)
        return base

    def test_listado_es_publico(self):
        respuesta = self.client.get(URL)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.data["results"]), 2)

    def test_detalle_es_publico(self):
        respuesta = self.client.get(f"{URL}{self.centro.id}/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["nombre"], "Centro")

    def test_filtro_por_ciudad(self):
        respuesta = self.client.get(f"{URL}?ciudad=Córdoba")
        self.assertEqual(len(respuesta.data["results"]), 1)
        self.assertEqual(respuesta.data["results"][0]["nombre"], "Norte")

    def test_busqueda_por_nombre(self):
        respuesta = self.client.get(f"{URL}?search=cent")
        self.assertEqual(len(respuesta.data["results"]), 1)

    def test_visitante_no_puede_crear(self):
        respuesta = self.client.post(URL, self.datos())
        self.assertIn(respuesta.status_code, (401, 403))

    def test_cliente_comun_recibe_403_al_crear(self):
        self.client.force_authenticate(self.cliente)
        respuesta = self.client.post(URL, self.datos())
        self.assertEqual(respuesta.status_code, 403)

    def test_cliente_comun_no_puede_editar_ni_borrar(self):
        self.client.force_authenticate(self.cliente)
        editar = self.client.patch(f"{URL}{self.centro.id}/", {"nombre": "X"})
        borrar = self.client.delete(f"{URL}{self.centro.id}/")
        self.assertEqual(editar.status_code, 403)
        self.assertEqual(borrar.status_code, 403)
        self.centro.refresh_from_db()
        self.assertEqual(self.centro.nombre, "Centro")
        self.assertTrue(self.centro.activo)

    def test_staff_puede_crear(self):
        self.client.force_authenticate(self.staff)
        respuesta = self.client.post(URL, self.datos())
        self.assertEqual(respuesta.status_code, 201)
        self.assertTrue(Sucursal.objects.filter(nombre="Sur").exists())

    def test_staff_puede_editar(self):
        self.client.force_authenticate(self.staff)
        respuesta = self.client.patch(
            f"{URL}{self.centro.id}/", {"telefono": "358 4111111"}
        )
        self.assertEqual(respuesta.status_code, 200)
        self.centro.refresh_from_db()
        self.assertEqual(self.centro.telefono, "358 4111111")

    def test_nombre_debe_ser_unico(self):
        self.client.force_authenticate(self.staff)
        respuesta = self.client.post(URL, self.datos(nombre="Centro"))
        self.assertEqual(respuesta.status_code, 400)

    def test_direccion_y_ciudad_son_obligatorias(self):
        self.client.force_authenticate(self.staff)
        sin_direccion = self.client.post(URL, {"nombre": "Sur", "ciudad": "X"})
        sin_ciudad = self.client.post(URL, {"nombre": "Sur", "direccion": "Y 1"})
        self.assertEqual(sin_direccion.status_code, 400)
        self.assertEqual(sin_ciudad.status_code, 400)

    def test_borrado_es_logico(self):
        self.client.force_authenticate(self.staff)
        respuesta = self.client.delete(f"{URL}{self.centro.id}/")
        self.assertEqual(respuesta.status_code, 204)
        self.centro.refresh_from_db()
        self.assertFalse(self.centro.activo)

    def test_sucursal_inactiva_no_aparece_para_el_publico(self):
        self.norte.activo = False
        self.norte.save()
        listado = self.client.get(URL)
        detalle = self.client.get(f"{URL}{self.norte.id}/")
        self.assertEqual(len(listado.data["results"]), 1)
        self.assertEqual(detalle.status_code, 404)

    def test_staff_ve_tambien_las_inactivas(self):
        self.norte.activo = False
        self.norte.save()
        self.client.force_authenticate(self.staff)
        respuesta = self.client.get(URL)
        self.assertEqual(len(respuesta.data["results"]), 2)