from rest_framework import serializers

from .models import Categoria, Prenda


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ["id", "nombre", "descripcion", "activa"]
        read_only_fields = ["id"]


class PrendaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prenda
        fields = [
            "id",
            "nombre",
            "descripcion",
            "precio",
            "stock",
            "categoria",
            "talle",
            "color",
            "imagen",
            "destacado",
            "activo",
            "timestamp",
        ]
        read_only_fields = ["id", "timestamp"]

    def validate_precio(self, value):
        if value <= 0:
            raise serializers.ValidationError("El precio debe ser mayor a 0.")
        return value


class PrendaListSerializer(PrendaSerializer):
    categoria = CategoriaSerializer(read_only=True)