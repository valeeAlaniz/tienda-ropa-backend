from rest_framework import serializers

from catalogo.serializers import CategoriaSerializer

from .models import PrendaAlquiler


class PrendaAlquilerSerializer(serializers.ModelSerializer):
    """Para escribir (crear y editar): la categoría va por id."""

    class Meta:
        model = PrendaAlquiler
        fields = [
            "id",
            "nombre",
            "descripcion",
            "precio_por_dia",
            "categoria",
            "talle",
            "color",
            "imagen",
            "destacado",
            "activo",
            "timestamp",
        ]
        read_only_fields = ["id", "timestamp"]

    def validate_precio_por_dia(self, value):
        if value <= 0:
            raise serializers.ValidationError("El precio por día debe ser mayor a 0.")
        return value


class PrendaAlquilerListSerializer(PrendaAlquilerSerializer):
    """Para leer (listado y detalle): la categoría va anidada."""

    categoria = CategoriaSerializer(read_only=True)
