from rest_framework import serializers

from .models import Sucursal


class SucursalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sucursal
        fields = ["id", "nombre", "direccion", "ciudad", "telefono", "activo"]
        read_only_fields = ["id"]