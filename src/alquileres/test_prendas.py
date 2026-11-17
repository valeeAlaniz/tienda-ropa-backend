from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from catalogo.models import Categoria

from .models import PrendaAlquiler


class PrendaAlquilerApiTests(APITestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nombre="Vestidos")
        self.cliente = User.objects.create_user("cliente", password="clave12345")
        self.staff = User.objects.create_user(
            "staff", password="clave12345", is_staff=True
        )
        self.negro = PrendaAlquiler.objects.create(
            nombre="Vestido largo", precio_por_dia=5000,
            categoria=self.categoria, talle="M", color="Negro", destacado=True,
        )
        self.rojo = PrendaAlquiler.objects.create(
            nombre="Vestido corto", precio_por_dia=3500,
            categoria=self.categoria, talle="S", color="Rojo",
        )

    def datos(self, **extra):
        base = {
            "nombre": "Traje azul", "precio_por_dia": "8000.00",
            "categoria": self.categoria.id, "talle": "L", "color": "Azul",
        }
        base.update(extra)
        return base

    def test_listado_es_publico(self):
        respuesta = self.client.get("/api/prendas-alquiler/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.data["results"]), 2)

    def test_listado_trae_la_categoria_anidada(self):
        respuesta = self.client.get("/api/prendas-alquiler/")
        self.assertEqual(
            respuesta.data["results"][0]["categoria"]["nombre"], "Vestidos"
        )

    def test_detalle_trae_la_categoria_anidada(self):
        respuesta = self.client.get(f"/api/prendas-alquiler/{self.negro.id}/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["categoria"]["id"], self.categoria.id)

    def test_filtro_por_talle(self):
        respuesta = self.client.get("/api/prendas-alquiler/?talle=S")
        self.assertEqual(len(respuesta.data["results"]), 1)
        self.assertEqual(respuesta.data["results"][0]["color"], "Rojo")

    def test_filtro_por_precio_por_dia(self):
        respuesta = self.client.get("/api/prendas-alquiler/?precio_por_dia__lte=4000")
        self.assertEqual(len(respuesta.data["results"]), 1)

    def test_destacadas(self):
        respuesta = self.client.get("/api/prendas-alquiler/destacadas/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.data["results"]), 1)

    def test_visitante_no_puede_crear(self):
        respuesta = self.client.post("/api/prendas-alquiler/", self.datos())
        self.assertIn(respuesta.status_code, (401, 403))

    def test_cliente_comun_recibe_403_al_crear(self):
        self.client.force_authenticate(self.cliente)
        respuesta = self.client.post("/api/prendas-alquiler/", self.datos())
        self.assertEqual(respuesta.status_code, 403)

    def test_staff_puede_crear(self):
        self.client.force_authenticate(self.staff)
        respuesta = self.client.post("/api/prendas-alquiler/", self.datos())
        self.assertEqual(respuesta.status_code, 201)

    def test_precio_por_dia_debe_ser_mayor_a_cero(self):
        self.client.force_authenticate(self.staff)
        respuesta = self.client.post(
            "/api/prendas-alquiler/", self.datos(precio_por_dia="0")
        )
        self.assertEqual(respuesta.status_code, 400)

    def test_borrado_es_logico(self):
        self.client.force_authenticate(self.staff)
        respuesta = self.client.delete(f"/api/prendas-alquiler/{self.negro.id}/")
        self.assertEqual(respuesta.status_code, 204)
        self.negro.refresh_from_db()
        self.assertFalse(self.negro.activo)

    def test_prenda_inactiva_no_aparece_para_el_publico(self):
        self.rojo.activo = False
        self.rojo.save()
        respuesta = self.client.get("/api/prendas-alquiler/")
        self.assertEqual(len(respuesta.data["results"]), 1)

    def test_staff_ve_las_inactivas(self):
        self.rojo.activo = False
        self.rojo.save()
        self.client.force_authenticate(self.staff)
        respuesta = self.client.get("/api/prendas-alquiler/")
        self.assertEqual(len(respuesta.data["results"]), 2)
