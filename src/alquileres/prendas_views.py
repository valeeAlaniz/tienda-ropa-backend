from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from catalogo.permissions import IsStaffOrReadOnly

from .models import PrendaAlquiler
from .prendas_serializers import (
    PrendaAlquilerListSerializer,
    PrendaAlquilerSerializer,
)


class PrendaAlquilerViewSet(viewsets.ModelViewSet):
    """CRUD de prendas de alquiler. El borrado es lógico (activo=False)."""

    queryset = PrendaAlquiler.objects.all().select_related("categoria").order_by("id")
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        "categoria": ["exact"],
        "talle": ["exact"],
        "color": ["exact", "icontains"],
        "precio_por_dia": ["exact", "gt", "lt", "gte", "lte"],
        "destacado": ["exact"],
        "activo": ["exact"],
    }
    search_fields = ["nombre", "descripcion", "categoria__nombre", "color"]
    ordering_fields = ["precio_por_dia", "id", "nombre", "timestamp"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(activo=True)

    def get_serializer_class(self):
        if self.action in ("list", "retrieve", "destacadas"):
            return PrendaAlquilerListSerializer
        return PrendaAlquilerSerializer

    def perform_destroy(self, instance):
        instance.activo = False
        instance.save(update_fields=["activo"])

    @extend_schema(
        summary="Prendas de alquiler destacadas",
        description="Lista las prendas de alquiler activas marcadas como destacadas.",
        responses=PrendaAlquilerListSerializer(many=True),
    )
    @action(detail=False, methods=["get"])
    def destacadas(self, request):
        queryset = self.filter_queryset(
            self.get_queryset().filter(destacado=True, activo=True)
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = PrendaAlquilerListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(PrendaAlquilerListSerializer(queryset, many=True).data)
