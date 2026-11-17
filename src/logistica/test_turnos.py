from datetime import time, timedelta

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.test import APITestCase

from clientes.models import Cliente

from .models import EstadoTurno, HorarioAtencion, Sucursal, TipoTurno, Turno

URL = "/api/logistica/turnos/"
HORARIOS_LIBRES = f"{URL}horarios_libres/"
FECHA = timezone.localdate() + timedelta(days=7)


class TurnosBase(APITestCase):
    def setUp(self):
        self.sucursal = Sucursal.objects.create(
            nombre="Centro", direccion="San Martín 123", ciudad="Río Cuarto"
        )
        # Atiende el día de FECHA, de 09:00 a 12:00, turnos de 60 minutos
        HorarioAtencion.objects.create(
            sucursal=self.sucursal,
            dia_semana=FECHA.weekday(),
            hora_apertura=time(9, 0),
            hora_cierre=time(12, 0),
            duracion_turno_min=60,
        )
        self.usuario = User.objects.create_user("ana", password="clave12345")
        self.cliente = Cliente.objects.create(
            usuario=self.usuario, nombre="Ana", apellido="Pérez", email="ana@mail.com"
        )
        self.otro_usuario = User.objects.create_user("beto", password="clave12345")
        self.otro_cliente = Cliente.objects.create(
            usuario=self.otro_usuario, nombre="Beto", apellido="Gómez", email="beto@mail.com"
        )
        self.staff = User.objects.create_user(
            "staff", password="clave12345", is_staff=True
        )

    def datos(self, **extra):
        base = {
            "sucursal": self.sucursal.id,
            "tipo": TipoTurno.PRUEBA,
            "fecha": FECHA.isoformat(),
            "hora": "10:00",
        }
        base.update(extra)
        return base

    def crear_turno_orm(self, hora=time(10, 0), cliente=None, estado=EstadoTurno.PENDIENTE):
        return Turno.objects.create(
            sucursal=self.sucursal,
            cliente=cliente or self.cliente,
            tipo=TipoTurno.PRUEBA,
            fecha=FECHA,
            hora=hora,
            estado=estado,
        )


class HorariosDeAtencionTests(TurnosBase):
    def test_horarios_libres_sigue_el_horario_de_atencion(self):
        r = self.client.get(
            HORARIOS_LIBRES, {"sucursal": self.sucursal.id, "fecha": FECHA.isoformat()}
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["horarios"], ["09:00", "10:00", "11:00"])

    def test_dia_sin_atencion_no_tiene_horarios(self):
        otro_dia = FECHA + timedelta(days=1)
        r = self.client.get(
            HORARIOS_LIBRES, {"sucursal": self.sucursal.id, "fecha": otro_dia.isoformat()}
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["horarios"], [])

    def test_no_se_reserva_fuera_del_horario_de_atencion(self):
        self.client.force_authenticate(self.usuario)
        r = self.client.post(URL, self.datos(hora="15:00"))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Turno.objects.count(), 0)

    def test_la_hora_de_cierre_no_se_puede_reservar(self):
        self.client.force_authenticate(self.usuario)
        r = self.client.post(URL, self.datos(hora="12:00"))
        self.assertEqual(r.status_code, 400)

    def test_no_se_reserva_un_dia_sin_atencion(self):
        self.client.force_authenticate(self.usuario)
        otro_dia = FECHA + timedelta(days=1)
        r = self.client.post(URL, self.datos(fecha=otro_dia.isoformat()))
        self.assertEqual(r.status_code, 400)

    def test_sucursal_inactiva_no_ofrece_horarios(self):
        self.sucursal.activo = False
        self.sucursal.save()
        r = self.client.get(
            HORARIOS_LIBRES, {"sucursal": self.sucursal.id, "fecha": FECHA.isoformat()}
        )
        self.assertEqual(r.status_code, 400)

    def test_cliente_comun_no_puede_crear_horarios(self):
        self.client.force_authenticate(self.usuario)
        r = self.client.post(
            "/api/logistica/horarios-atencion/",
            {
                "sucursal": self.sucursal.id,
                "dia_semana": 0,
                "hora_apertura": "09:00",
                "hora_cierre": "12:00",
                "duracion_turno_min": 30,
            },
        )
        self.assertEqual(r.status_code, 403)

    def test_staff_no_puede_crear_horario_con_cierre_anterior_a_la_apertura(self):
        self.client.force_authenticate(self.staff)
        r = self.client.post(
            "/api/logistica/horarios-atencion/",
            {
                "sucursal": self.sucursal.id,
                "dia_semana": 0,
                "hora_apertura": "18:00",
                "hora_cierre": "09:00",
                "duracion_turno_min": 30,
            },
        )
        self.assertEqual(r.status_code, 400)


class DobleReservaTests(TurnosBase):
    def test_reserva_valida_se_crea(self):
        self.client.force_authenticate(self.usuario)
        r = self.client.post(URL, self.datos())
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["estado"], EstadoTurno.PENDIENTE)
        self.assertEqual(r.data["cliente"], self.cliente.id)

    def test_doble_reserva_es_rechazada(self):
        self.client.force_authenticate(self.usuario)
        self.assertEqual(self.client.post(URL, self.datos()).status_code, 201)
        self.client.force_authenticate(self.otro_usuario)
        r = self.client.post(URL, self.datos())
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Turno.objects.count(), 1)

    def test_horario_reservado_no_aparece_como_libre(self):
        self.crear_turno_orm()
        r = self.client.get(
            HORARIOS_LIBRES, {"sucursal": self.sucursal.id, "fecha": FECHA.isoformat()}
        )
        self.assertEqual(r.data["horarios"], ["09:00", "11:00"])

    def test_turno_cancelado_libera_el_horario(self):
        self.client.force_authenticate(self.usuario)
        creado = self.client.post(URL, self.datos())
        cancelado = self.client.post(f"{URL}{creado.data['id']}/cancelar/")
        self.assertEqual(cancelado.status_code, 200)
        self.client.force_authenticate(self.otro_usuario)
        r = self.client.post(URL, self.datos())
        self.assertEqual(r.status_code, 201)

    def test_la_base_de_datos_impide_la_doble_reserva(self):
        self.crear_turno_orm()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.crear_turno_orm(cliente=self.otro_cliente)

    def test_sucursales_distintas_pueden_tener_el_mismo_horario(self):
        otra = Sucursal.objects.create(
            nombre="Norte", direccion="Belgrano 456", ciudad="Córdoba"
        )
        HorarioAtencion.objects.create(
            sucursal=otra,
            dia_semana=FECHA.weekday(),
            hora_apertura=time(9, 0),
            hora_cierre=time(12, 0),
            duracion_turno_min=60,
        )
        self.client.force_authenticate(self.usuario)
        self.assertEqual(self.client.post(URL, self.datos()).status_code, 201)
        r = self.client.post(URL, self.datos(sucursal=otra.id))
        self.assertEqual(r.status_code, 201)


class FechasPasadasTests(TurnosBase):
    def test_no_se_reserva_en_el_pasado(self):
        self.client.force_authenticate(self.usuario)
        ayer = timezone.localdate() - timedelta(days=1)
        r = self.client.post(URL, self.datos(fecha=ayer.isoformat()))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Turno.objects.count(), 0)

    def test_no_se_consultan_horarios_de_una_fecha_pasada(self):
        ayer = timezone.localdate() - timedelta(days=1)
        r = self.client.get(
            HORARIOS_LIBRES, {"sucursal": self.sucursal.id, "fecha": ayer.isoformat()}
        )
        self.assertEqual(r.status_code, 400)

    def test_la_fecha_es_obligatoria(self):
        r = self.client.get(HORARIOS_LIBRES, {"sucursal": self.sucursal.id})
        self.assertEqual(r.status_code, 400)


class PermisosYEstadosTests(TurnosBase):
    def test_visitante_no_puede_reservar(self):
        r = self.client.post(URL, self.datos())
        self.assertIn(r.status_code, (401, 403))

    def test_usuario_sin_perfil_de_cliente_no_puede_reservar(self):
        self.client.force_authenticate(self.staff)
        r = self.client.post(URL, self.datos())
        self.assertEqual(r.status_code, 400)

    def test_cliente_solo_ve_sus_turnos(self):
        propio = self.crear_turno_orm(hora=time(9, 0))
        self.crear_turno_orm(hora=time(10, 0), cliente=self.otro_cliente)
        self.client.force_authenticate(self.usuario)
        r = self.client.get(URL)
        self.assertEqual([t["id"] for t in r.data["results"]], [propio.id])

    def test_staff_ve_todos_los_turnos(self):
        self.crear_turno_orm(hora=time(9, 0))
        self.crear_turno_orm(hora=time(10, 0), cliente=self.otro_cliente)
        self.client.force_authenticate(self.staff)
        r = self.client.get(URL)
        self.assertEqual(len(r.data["results"]), 2)

    def test_cliente_no_puede_cancelar_turno_ajeno(self):
        ajeno = self.crear_turno_orm(cliente=self.otro_cliente)
        self.client.force_authenticate(self.usuario)
        r = self.client.post(f"{URL}{ajeno.id}/cancelar/")
        self.assertEqual(r.status_code, 404)
        ajeno.refresh_from_db()
        self.assertEqual(ajeno.estado, EstadoTurno.PENDIENTE)

    def test_no_se_cancela_un_turno_completado(self):
        turno = self.crear_turno_orm(estado=EstadoTurno.COMPLETADO)
        self.client.force_authenticate(self.usuario)
        r = self.client.post(f"{URL}{turno.id}/cancelar/")
        self.assertEqual(r.status_code, 400)
        turno.refresh_from_db()
        self.assertEqual(turno.estado, EstadoTurno.COMPLETADO)

    def test_cliente_no_puede_cambiar_estado(self):
        turno = self.crear_turno_orm()
        self.client.force_authenticate(self.usuario)
        r = self.client.post(
            f"{URL}{turno.id}/cambiar_estado/", {"estado": EstadoTurno.CONFIRMADO}
        )
        self.assertEqual(r.status_code, 403)

    def test_staff_cambia_estado_con_transiciones_validas(self):
        turno = self.crear_turno_orm()
        self.client.force_authenticate(self.staff)
        ok = self.client.post(
            f"{URL}{turno.id}/cambiar_estado/", {"estado": EstadoTurno.CONFIRMADO}
        )
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.data["estado"], EstadoTurno.CONFIRMADO)
        invalida = self.client.post(
            f"{URL}{turno.id}/cambiar_estado/", {"estado": EstadoTurno.PENDIENTE}
        )
        self.assertEqual(invalida.status_code, 400)