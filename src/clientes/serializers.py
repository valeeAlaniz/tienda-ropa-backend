from rest_framework import serializers

from .models import Cliente, Direccion


class DireccionResumenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Direccion
        fields = ("id", "calle", "numero", "ciudad", "codigo_postal")


class ClienteResumenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = ("id", "nombre", "apellido", "email")


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        read_only_fields = ("usuario",)
        fields = ("id", "usuario", "nombre", "apellido", "email", "telefono")


class ClienteListSerializer(ClienteSerializer):
    direcciones = DireccionResumenSerializer(many=True, read_only=True)

    class Meta(ClienteSerializer.Meta):
        fields = ClienteSerializer.Meta.fields + ("direcciones",)


class DireccionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Direccion
        read_only_fields = ("cliente",)
        fields = ("id", "cliente", "calle", "numero", "ciudad", "codigo_postal")


class DireccionListSerializer(DireccionSerializer):
    cliente = ClienteResumenSerializer(read_only=True)