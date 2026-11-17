from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from catalogo.models import Categoria, Prenda
from clientes.models import Cliente

from .models import Alquiler


class AlquilerModelTests(TestCase):
    def setUp(self):
        usuario = User.objects.create_user("cliente", password="clave12345")
        self.cliente = Cliente.objects.create(
            usuario=usuario,
            nombre="Ana",
            apellido="Pérez",
            email="ana@example.test",
        )
        categoria = Categoria.objects.create(nombre="Vestidos")
        self.prenda = Prenda.objects.create(
            nombre="Vestido largo",
            precio=50000,
            stock=2,
            categoria=categoria,
            talle="M",
            color="Negro",
        )

    def crear(self, **extra):
        datos = {
            "cliente": self.cliente,
            "prenda": self.prenda,
            "fecha_inicio": date(2026, 11, 20),
            "fecha_fin": date(2026, 11, 22),
            "precio_por_dia": Decimal("1500.00"),
        }
        datos.update(extra)
        return Alquiler.objects.create(**datos)

    def test_estado_por_defecto_es_reservado(self):
        self.assertEqual(self.crear().estado, Alquiler.Estado.RESERVADO)

    def test_estados_disponibles(self):
        self.assertEqual(
            set(Alquiler.Estado.values),
            {"reservado", "retirado", "devuelto", "cancelado"},
        )

    def test_precio_total_se_calcula_por_dias(self):
        alquiler = self.crear()
        self.assertEqual(alquiler.dias, 3)
        self.assertEqual(alquiler.precio_total, Decimal("4500.00"))

    def test_un_solo_dia_cuenta_como_un_dia(self):
        alquiler = self.crear(fecha_fin=date(2026, 11, 20))
        self.assertEqual(alquiler.dias, 1)
        self.assertEqual(alquiler.precio_total, Decimal("1500.00"))

    def test_cambiar_fechas_recalcula_el_total(self):
        alquiler = self.crear()
        alquiler.fecha_fin = date(2026, 11, 25)
        alquiler.save()
        alquiler.refresh_from_db()
        self.assertEqual(alquiler.precio_total, Decimal("9000.00"))

    def test_recalcula_aunque_se_guarde_con_update_fields(self):
        alquiler = self.crear()
        alquiler.fecha_fin = date(2026, 11, 25)
        alquiler.save(update_fields=["fecha_fin"])
        alquiler.refresh_from_db()
        self.assertEqual(alquiler.precio_total, Decimal("9000.00"))

    def test_cambiar_estado_no_altera_el_total(self):
        alquiler = self.crear()
        alquiler.estado = Alquiler.Estado.RETIRADO
        alquiler.save(update_fields=["estado"])
        alquiler.refresh_from_db()
        self.assertEqual(alquiler.estado, "retirado")
        self.assertEqual(alquiler.precio_total, Decimal("4500.00"))

    def test_fecha_fin_anterior_a_inicio_no_es_valida(self):
        alquiler = Alquiler(
            cliente=self.cliente,
            prenda=self.prenda,
            fecha_inicio=date(2026, 11, 22),
            fecha_fin=date(2026, 11, 20),
            precio_por_dia=Decimal("1500.00"),
        )
        with self.assertRaises(ValidationError) as contexto:
            alquiler.full_clean()
        self.assertIn("fecha_fin", contexto.exception.message_dict)

    def test_base_de_datos_rechaza_fecha_fin_anterior(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.crear(
                    fecha_inicio=date(2026, 11, 22), fecha_fin=date(2026, 11, 20)
                )

    def test_base_de_datos_rechaza_precio_por_dia_cero(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.crear(precio_por_dia=Decimal("0"))