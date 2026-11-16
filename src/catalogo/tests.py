from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from .models import Categoria, Prenda


class PrendaApiTests(APITestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nombre="Camisas")
        self.cliente = User.objects.create_user("cliente", password="clave12345")
        self.staff = User.objects.create_user(
            "staff", password="clave12345", is_staff=True
        )
        self.blanca = Prenda.objects.create(
            nombre="Camisa lino", precio=100, stock=5,
            categoria=self.categoria, talle="M", color="Blanco",
        )
        self.negra = Prenda.objects.create(
            nombre="Camisa slim", precio=150, stock=3,
            categoria=self.categoria, talle="L", color="Negro",
        )

    def datos(self, **extra):
        base = {
            "nombre": "Camisa nueva", "precio": "200.00", "stock": 4,
            "categoria": self.categoria.id, "talle": "S", "color": "Azul",
        }
        base.update(extra)
        return base

    def test_listado_es_publico(self):
        respuesta = self.client.get("/api/prendas/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.data["results"]), 2)

    def test_filtro_por_talle(self):
        respuesta = self.client.get("/api/prendas/?talle=L")
        self.assertEqual(len(respuesta.data["results"]), 1)
        self.assertEqual(respuesta.data["results"][0]["color"], "Negro")

    def test_filtro_por_color(self):
        respuesta = self.client.get("/api/prendas/?color=Blanco")
        self.assertEqual(len(respuesta.data["results"]), 1)
        self.assertEqual(respuesta.data["results"][0]["talle"], "M")

    def test_visitante_no_puede_crear(self):
        respuesta = self.client.post("/api/prendas/", self.datos())
        self.assertIn(respuesta.status_code, (401, 403))

    def test_cliente_comun_recibe_403_al_crear(self):
        self.client.force_authenticate(self.cliente)
        respuesta = self.client.post("/api/prendas/", self.datos())
        self.assertEqual(respuesta.status_code, 403)

    def test_staff_puede_crear(self):
        self.client.force_authenticate(self.staff)
        respuesta = self.client.post("/api/prendas/", self.datos())
        self.assertEqual(respuesta.status_code, 201)

    def test_precio_debe_ser_mayor_a_cero(self):
        self.client.force_authenticate(self.staff)
        respuesta = self.client.post("/api/prendas/", self.datos(precio="0"))
        self.assertEqual(respuesta.status_code, 400)

    def test_borrado_es_logico(self):
        self.client.force_authenticate(self.staff)
        respuesta = self.client.delete(f"/api/prendas/{self.blanca.id}/")
        self.assertEqual(respuesta.status_code, 204)
        self.blanca.refresh_from_db()
        self.assertFalse(self.blanca.activo)

    def test_prenda_borrada_no_aparece_para_el_publico(self):
        self.negra.activo = False
        self.negra.save()
        respuesta = self.client.get("/api/prendas/")
        self.assertEqual(len(respuesta.data["results"]), 1)