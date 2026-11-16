from rest_framework import serializers
from .models import PrendaAlquiler

class PrendaAlquilerSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.ReadOnlyField(source='categoria.nombre')

    class Meta:
        model = PrendaAlquiler
        fields = '__all__'