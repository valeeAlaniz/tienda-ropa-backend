from datetime import datetime, timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import EstadoTurno, HorarioAtencion, Turno

TRANSICIONES = {
    EstadoTurno.PENDIENTE: {EstadoTurno.CONFIRMADO, EstadoTurno.CANCELADO},
    EstadoTurno.CONFIRMADO: {EstadoTurno.COMPLETADO, EstadoTurno.CANCELADO},
    EstadoTurno.CANCELADO: set(),
    EstadoTurno.COMPLETADO: set(),
}


def horarios_del_dia(sucursal, fecha):
    """Todos los horarios de inicio posibles según los horarios de atención."""
    franjas = HorarioAtencion.objects.filter(
        sucursal=sucursal, dia_semana=fecha.weekday()
    )
    horas = set()
    for franja in franjas:
        actual = datetime.combine(fecha, franja.hora_apertura)
        fin = datetime.combine(fecha, franja.hora_cierre)
        paso = timedelta(minutes=franja.duracion_turno_min)
        while actual + paso <= fin:
            horas.add(actual.time())
            actual += paso
    return sorted(horas)


def horarios_libres(sucursal, fecha):
    """Horarios del día sin turno activo y que todavía no pasaron."""
    ocupados = set(
        Turno.objects.filter(sucursal=sucursal, fecha=fecha)
        .exclude(estado=EstadoTurno.CANCELADO)
        .values_list("hora", flat=True)
    )
    libres = [h for h in horarios_del_dia(sucursal, fecha) if h not in ocupados]

    ahora = timezone.localtime()
    if fecha == ahora.date():
        libres = [h for h in libres if h > ahora.time()]
    return libres


def crear_turno(*, sucursal, cliente, tipo, fecha, hora):
    """Crea un turno validando fecha, horario de atención y doble reserva.

    Lanza rest_framework.exceptions.ValidationError si algo no se cumple.
    """
    ahora = timezone.localtime()
    if fecha < ahora.date() or (fecha == ahora.date() and hora <= ahora.time()):
        raise ValidationError({"fecha": "No se puede reservar un turno en el pasado."})

    if hora not in horarios_del_dia(sucursal, fecha):
        raise ValidationError(
            {"hora": "Ese horario está fuera del horario de atención de la sucursal."}
        )

    ocupado = (
        Turno.objects.filter(sucursal=sucursal, fecha=fecha, hora=hora)
        .exclude(estado=EstadoTurno.CANCELADO)
        .exists()
    )
    if ocupado:
        raise ValidationError({"hora": "Ese horario ya está reservado."})

    try:
        with transaction.atomic():
            return Turno.objects.create(
                sucursal=sucursal, cliente=cliente, tipo=tipo, fecha=fecha, hora=hora
            )
    except IntegrityError:
        # Dos personas reservaron a la vez: la restricción de la base lo frena
        raise ValidationError({"hora": "Ese horario ya está reservado."})


def cambiar_estado(turno, nuevo_estado):
    """Cambia el estado respetando las transiciones permitidas."""
    if nuevo_estado not in TRANSICIONES[turno.estado]:
        raise ValidationError(
            {"estado": f"No se puede pasar de {turno.estado} a {nuevo_estado}."}
        )
    turno.estado = nuevo_estado
    turno.save(update_fields=["estado"])
    return turno