import os
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Cliente, Direccion
from .permissions import filtrar_por_cliente


class EnsureStaffSuperuserTests(TestCase):
    variables = {
        "DJANGO_SUPERUSER_USERNAME": "admin_tienda",
        "DJANGO_SUPERUSER_PASSWORD": "Clave-Segura-Tienda-2026!",
        "DJANGO_SUPERUSER_EMAIL": "admin@tienda.example",
    }

    def ejecutar(self):
        salida = StringIO()
        call_command("ensure_staff_superuser", stdout=salida)
        return salida.getvalue()

    def test_no_crea_usuario_si_no_hay_variables(self):
        with patch.dict(
            os.environ,
            {
                "DJANGO_SUPERUSER_USERNAME": "",
                "DJANGO_SUPERUSER_PASSWORD": "",
                "DJANGO_SUPERUSER_EMAIL": "",
            },
        ):
            self.ejecutar()

        self.assertEqual(get_user_model().objects.count(), 0)

    def test_falla_si_faltan_variables(self):
        with patch.dict(os.environ, {**self.variables, "DJANGO_SUPERUSER_EMAIL": ""}):
            with self.assertRaises(CommandError):
                self.ejecutar()

    def test_crea_superusuario_correctamente(self):
        with patch.dict(os.environ, self.variables):
            self.ejecutar()

        usuario = get_user_model().objects.get(username="admin_tienda")

        self.assertTrue(usuario.is_staff)
        self.assertTrue(usuario.is_superuser)
        self.assertTrue(
            usuario.check_password(self.variables["DJANGO_SUPERUSER_PASSWORD"])
        )

    def test_no_duplica_ni_cambia_password_al_reiniciar(self):
        User = get_user_model()

        with patch.dict(os.environ, self.variables):
            self.ejecutar()

        usuario = User.objects.get(username="admin_tienda")
        password_original = usuario.password

        with patch.dict(
            os.environ,
            {**self.variables, "DJANGO_SUPERUSER_PASSWORD": "Otra-Clave-Distinta-2026!"},
        ):
            self.ejecutar()

        usuario.refresh_from_db()

        self.assertEqual(User.objects.filter(username="admin_tienda").count(), 1)
        self.assertEqual(usuario.password, password_original)

    def test_no_eleva_un_usuario_comun_a_superusuario(self):
        User = get_user_model()
        User.objects.create_user(username="admin_tienda", password="Clave-Comun-2026!")

        with patch.dict(os.environ, self.variables):
            with self.assertRaises(CommandError):
                self.ejecutar()

        usuario = User.objects.get(username="admin_tienda")
        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)


class BaseClientesTestCase(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.usuario = User.objects.create_user(
            username="propietario", password="Clave-Test-2026!"
        )
        self.otro_usuario = User.objects.create_user(
            username="otro", password="Clave-Test-2026!"
        )
        self.staff = User.objects.create_user(
            username="personal", password="Clave-Test-2026!", is_staff=True
        )

        self.cliente = Cliente.objects.create(
            usuario=self.usuario,
            nombre="Cliente",
            apellido="Propietario",
            email="propietario@example.test",
        )
        self.otro_cliente = Cliente.objects.create(
            usuario=self.otro_usuario,
            nombre="Otro",
            apellido="Cliente",
            email="otro@example.test",
        )

        self.direccion = Direccion.objects.create(
            cliente=self.cliente,
            calle="San Martín",
            numero="100",
            ciudad="Río Cuarto",
            codigo_postal="5800",
        )
        self.otra_direccion = Direccion.objects.create(
            cliente=self.otro_cliente,
            calle="Belgrano",
            numero="200",
            ciudad="Córdoba",
            codigo_postal="5000",
        )


class ClienteOwnershipTests(BaseClientesTestCase):
    def test_cliente_solo_consulta_su_perfil(self):
        self.client.force_authenticate(self.usuario)

        listado = self.client.get("/api/clientes/clientes/")
        propio = self.client.get(f"/api/clientes/clientes/{self.cliente.id}/")
        ajeno = self.client.get(f"/api/clientes/clientes/{self.otro_cliente.id}/")

        self.assertEqual(listado.status_code, status.HTTP_200_OK)
        self.assertEqual(listado.data["count"], 1)
        self.assertEqual(propio.status_code, status.HTTP_200_OK)
        self.assertEqual(ajeno.status_code, status.HTTP_404_NOT_FOUND)

    def test_staff_ve_todos_los_clientes(self):
        self.client.force_authenticate(self.staff)

        listado = self.client.get("/api/clientes/clientes/")

        self.assertEqual(listado.status_code, status.HTTP_200_OK)
        self.assertEqual(listado.data["count"], 2)

    def test_cliente_solo_consulta_sus_direcciones(self):
        self.client.force_authenticate(self.usuario)

        listado = self.client.get("/api/clientes/direcciones/")
        propia = self.client.get(f"/api/clientes/direcciones/{self.direccion.id}/")
        ajena = self.client.get(
            f"/api/clientes/direcciones/{self.otra_direccion.id}/"
        )

        self.assertEqual(listado.status_code, status.HTTP_200_OK)
        self.assertEqual(listado.data["count"], 1)
        self.assertEqual(propia.status_code, status.HTTP_200_OK)
        self.assertEqual(ajena.status_code, status.HTTP_404_NOT_FOUND)

    def test_crear_direccion_asigna_al_cliente_autenticado(self):
        self.client.force_authenticate(self.usuario)

        respuesta = self.client.post(
            "/api/clientes/direcciones/",
            {
                "cliente": self.otro_cliente.id,
                "calle": "Mitre",
                "numero": "300",
                "ciudad": "Río Cuarto",
                "codigo_postal": "5800",
            },
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        direccion = Direccion.objects.get(pk=respuesta.data["id"])
        self.assertEqual(direccion.cliente_id, self.cliente.id)

    def test_anonimo_no_accede_a_los_clientes(self):
        respuesta = self.client.get("/api/clientes/clientes/")
        self.assertIn(respuesta.status_code, (401, 403))


class FiltrarPorClienteTests(BaseClientesTestCase):
    def test_el_staff_ve_todo(self):
        resultado = filtrar_por_cliente(Direccion.objects.all(), self.staff, "cliente")
        self.assertEqual(resultado.count(), 2)

    def test_el_cliente_ve_solo_lo_suyo(self):
        resultado = filtrar_por_cliente(
            Direccion.objects.all(), self.usuario, "cliente"
        )
        self.assertEqual(list(resultado), [self.direccion])

    def test_un_usuario_sin_perfil_no_ve_nada(self):
        sin_perfil = get_user_model().objects.create_user(
            username="sin_perfil", password="Clave-Test-2026!"
        )
        resultado = filtrar_por_cliente(Direccion.objects.all(), sin_perfil, "cliente")
        self.assertEqual(resultado.count(), 0)


class LoginTests(BaseClientesTestCase):
    def login(self, username, password):
        return self.client.post(
            "/api/token/", {"username": username, "password": password}, format="json"
        )

    def test_login_de_cliente_devuelve_token_y_no_es_staff(self):
        respuesta = self.login("propietario", "Clave-Test-2026!")

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertTrue(respuesta.data["token"])
        self.assertEqual(respuesta.data["username"], "propietario")
        self.assertFalse(respuesta.data["is_staff"])

    def test_login_de_staff_marca_is_staff(self):
        respuesta = self.login("personal", "Clave-Test-2026!")

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertTrue(respuesta.data["is_staff"])

    def test_credenciales_invalidas_se_rechazan(self):
        respuesta = self.login("propietario", "clave-equivocada")
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)


class RegistroClienteTests(APITestCase):
    def datos_validos(self):
        return {
            "username": "nuevo_usuario",
            "email": "nuevo@example.test",
            "nombre": "Ana",
            "apellido": "García",
            "telefono": "3584000000",
            "password": "Registro-Privado-2026!",
            "password_confirm": "Registro-Privado-2026!",
        }

    def registrar(self, datos=None):
        return self.client.post(
            "/api/clientes/registro/", datos or self.datos_validos(), format="json"
        )

    def test_registro_crea_usuario_y_perfil_cliente(self):
        respuesta = self.registrar()

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)

        usuario = get_user_model().objects.get(username="nuevo_usuario")
        self.assertTrue(usuario.check_password("Registro-Privado-2026!"))
        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)

        cliente = Cliente.objects.get(usuario=usuario)
        self.assertEqual(cliente.nombre, "Ana")
        self.assertEqual(cliente.apellido, "García")
        self.assertEqual(cliente.email, "nuevo@example.test")

    def test_no_permite_usuario_duplicado(self):
        get_user_model().objects.create_user(
            username="nuevo_usuario", password="Otra-Password-2026!"
        )

        respuesta = self.registrar()

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            Cliente.objects.filter(usuario__username="nuevo_usuario").exists()
        )

    def test_no_permite_correo_duplicado(self):
        User = get_user_model()
        User.objects.create_user(
            username="usuario_existente",
            email="nuevo@example.test",
            password="Otra-Password-2026!",
        )

        respuesta = self.registrar()

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username="nuevo_usuario").exists())

    def test_no_permite_contrasenas_distintas(self):
        datos = self.datos_validos()
        datos["password_confirm"] = "Otra-Password-2026!"

        respuesta = self.registrar(datos)

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            get_user_model().objects.filter(username="nuevo_usuario").exists()
        )

    def test_registro_no_otorga_permisos_administrativos(self):
        respuesta = self.registrar()

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)

        usuario = get_user_model().objects.get(username="nuevo_usuario")
        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)

    def test_registro_no_requiere_autenticacion(self):
        respuesta = self.registrar()
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)