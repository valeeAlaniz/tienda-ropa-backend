from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Cliente, Direccion
from .permissions import filtrar_por_cliente
from .serializers import (
    ClienteListSerializer,
    ClienteSerializer,
    DireccionListSerializer,
    DireccionResumenSerializer,
    DireccionSerializer,
)


class ClienteViewSet(viewsets.ModelViewSet):
    """El cliente ve y edita su propio perfil; el staff ve a todos."""

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["nombre", "apellido"]
    search_fields = ["nombre", "apellido", "email"]
    ordering_fields = ["nombre", "apellido", "id"]
    ordering = ["apellido", "nombre"]

    def get_queryset(self):
        queryset = Cliente.objects.select_related("usuario").prefetch_related(
            "direcciones"
        )
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(usuario=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return ClienteListSerializer
        return ClienteSerializer

    def perform_create(self, serializer):
        if Cliente.objects.filter(usuario=self.request.user).exists():
            raise ValidationError("Ya existe un perfil para este usuario.")
        serializer.save(usuario=self.request.user)

    @action(detail=True, methods=["get"])
    def direcciones(self, request, pk=None):
        cliente = self.get_object()
        serializer = DireccionResumenSerializer(cliente.direcciones.all(), many=True)
        return Response(serializer.data)


class DireccionViewSet(viewsets.ModelViewSet):
    """Cada cliente maneja solo sus direcciones."""

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["ciudad"]
    search_fields = ["calle", "ciudad", "codigo_postal"]
    ordering_fields = ["ciudad", "calle", "id"]
    ordering = ["ciudad", "calle"]

    def get_queryset(self):
        queryset = Direccion.objects.select_related("cliente")
        return filtrar_por_cliente(queryset, self.request.user, "cliente")

    def get_serializer_class(self):
        if self.action == "list":
            return DireccionListSerializer
        return DireccionSerializer

    def perform_create(self, serializer):
        cliente = getattr(self.request.user, "cliente", None)
        if cliente is None:
            raise ValidationError(
                "El usuario debe tener un perfil de cliente para registrar direcciones."
            )
        serializer.save(cliente=cliente)