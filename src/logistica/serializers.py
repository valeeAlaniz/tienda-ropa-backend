from django.utils import timezone
from rest_framework import serializers

from .models import EstadoTurno, HorarioAtencion, Sucursal, TipoTurno, Turno


class SucursalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sucursal
        fields = ["id", "nombre", "direccion", "ciudad", "telefono", "activo"]
        read_only_fields = ["id"]


class HorarioAtencionSerializer(serializers.ModelSerializer):
    class Meta:
        model = HorarioAtencion
        fields = [
            "id",
            "sucursal",
            "dia_semana",
            "hora_apertura",
            "hora_cierre",
            "duracion_turno_min",
        ]

    def validate(self, attrs):
        apertura = attrs.get("hora_apertura", getattr(self.instance, "hora_apertura", None))
        cierre = attrs.get("hora_cierre", getattr(self.instance, "hora_cierre", None))
        if apertura and cierre and apertura >= cierre:
            raise serializers.ValidationError(
                {"hora_cierre": "La hora de cierre debe ser posterior a la de apertura."}
            )
        return attrs


class TurnoSerializer(serializers.ModelSerializer):
    sucursal_nombre = serializers.CharField(source="sucursal.nombre", read_only=True)

    class Meta:
        model = Turno
        fields = [
            "id",
            "sucursal",
            "sucursal_nombre",
            "cliente",
            "tipo",
            "estado",
            "fecha",
            "hora",
            "creado",
        ]
        read_only_fields = fields


class TurnoCrearSerializer(serializers.Serializer):
    sucursal = serializers.PrimaryKeyRelatedField(
        queryset=Sucursal.objects.filter(activo=True)
    )
    tipo = serializers.ChoiceField(choices=TipoTurno.choices)
    fecha = serializers.DateField()
    hora = serializers.TimeField()


class CambiarEstadoSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(choices=EstadoTurno.choices)


class ConsultaHorariosSerializer(serializers.Serializer):
    sucursal = serializers.PrimaryKeyRelatedField(
        queryset=Sucursal.objects.filter(activo=True)
    )
    fecha = serializers.DateField()

    def validate_fecha(self, value):
        if value < timezone.localdate():
            raise serializers.ValidationError("No se puede consultar una fecha pasada.")
        return value