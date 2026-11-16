from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from .models import Categoria, Prenda
from .permissions import IsStaffOrReadOnly
from .serializers import CategoriaSerializer, PrendaListSerializer, PrendaSerializer


class CategoriaViewSet(viewsets.ModelViewSet):
    """CRUD de categorías. El borrado es lógico (activa=False)."""

    queryset = Categoria.objects.all().order_by("id")
    serializer_class = CategoriaSerializer
    permission_classes = [IsStaffOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(activa=True)

    def perform_destroy(self, instance):
        instance.activa = False
        instance.save(update_fields=["activa"])

    @extend_schema(
        summary="Prendas de una categoría",
        description="Lista las prendas activas de la categoría indicada.",
        responses=PrendaSerializer(many=True),
    )
    @action(detail=True, methods=["get"])
    def prendas(self, request, pk=None):
        categoria = self.get_object()
        queryset = categoria.prendas.filter(activo=True).order_by("id")
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = PrendaSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(PrendaSerializer(queryset, many=True).data)


class PrendaViewSet(viewsets.ModelViewSet):
    """CRUD de prendas a la venta. El borrado es lógico (activo=False)."""

    queryset = Prenda.objects.all().select_related("categoria").order_by("id")
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        "categoria": ["exact"],
        "talle": ["exact"],
        "color": ["exact", "icontains"],
        "precio": ["exact", "gt", "lt", "gte", "lte"],
        "destacado": ["exact"],
        "activo": ["exact"],
    }
    search_fields = ["nombre", "descripcion", "categoria__nombre", "color"]
    ordering_fields = ["precio", "id", "nombre", "timestamp"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(activo=True)

    def get_serializer_class(self):
        if self.action == "list":
            return PrendaListSerializer
        return PrendaSerializer

    def perform_destroy(self, instance):
        instance.activo = False
        instance.save(update_fields=["activo"])

    @extend_schema(
        summary="Prendas destacadas",
        description="Lista las prendas activas marcadas como destacadas.",
        responses=PrendaListSerializer(many=True),
    )
    @action(detail=False, methods=["get"])
    def destacadas(self, request):
        queryset = self.filter_queryset(
            self.get_queryset().filter(destacado=True, activo=True)
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = PrendaListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(PrendaListSerializer(queryset, many=True).data)