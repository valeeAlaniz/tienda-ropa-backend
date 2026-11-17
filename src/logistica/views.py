from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from catalogo.permissions import IsStaffOrReadOnly
from clientes.permissions import filtrar_por_cliente

from . import servicios
from .models import EstadoTurno, HorarioAtencion, Sucursal, Turno
from .serializers import (
    CambiarEstadoSerializer,
    ConsultaHorariosSerializer,
    HorarioAtencionSerializer,
    SucursalSerializer,
    TurnoCrearSerializer,
    TurnoSerializer,
)


class SucursalViewSet(viewsets.ModelViewSet):
    """CRUD de sucursales. El borrado es lógico (activo=False).

    Cualquiera puede consultar las sucursales activas; solo el staff puede
    crear, editar o borrar, y es el único que ve las inactivas.
    """

    queryset = Sucursal.objects.all().order_by("nombre")
    serializer_class = SucursalSerializer
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["ciudad", "activo"]
    search_fields = ["nombre", "ciudad", "direccion"]
    ordering_fields = ["nombre", "ciudad", "id"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(activo=True)

    def perform_destroy(self, instance):
        instance.activo = False
        instance.save(update_fields=["activo"])


class HorarioAtencionViewSet(viewsets.ModelViewSet):
    """Horarios de atención por sucursal. Lectura pública; edita el staff."""

    queryset = HorarioAtencion.objects.select_related("sucursal")
    serializer_class = HorarioAtencionSerializer
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["sucursal", "dia_semana"]


class TurnoViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Cada cliente ve y cancela sus turnos; el staff ve y gestiona todos."""

    queryset = Turno.objects.select_related("sucursal")
    serializer_class = TurnoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["sucursal", "tipo", "estado", "fecha"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if getattr(self, "swagger_fake_view", False):
            return queryset.none()
        return filtrar_por_cliente(queryset, self.request.user, "cliente")

    @extend_schema(request=TurnoCrearSerializer, responses={201: TurnoSerializer})
    def create(self, request, *args, **kwargs):
        cliente = getattr(request.user, "cliente", None)
        if cliente is None:
            raise ValidationError(
                "El usuario debe tener un perfil de cliente para reservar un turno."
            )
        entrada = TurnoCrearSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        turno = servicios.crear_turno(cliente=cliente, **entrada.validated_data)
        return Response(TurnoSerializer(turno).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        parameters=[ConsultaHorariosSerializer],
        responses={200: OpenApiTypes.OBJECT},
        summary="Horarios libres de una sucursal en un día",
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="horarios_libres",
        permission_classes=[AllowAny],
    )
    def horarios_libres(self, request):
        consulta = ConsultaHorariosSerializer(data=request.query_params)
        consulta.is_valid(raise_exception=True)
        sucursal = consulta.validated_data["sucursal"]
        fecha = consulta.validated_data["fecha"]
        libres = servicios.horarios_libres(sucursal, fecha)
        return Response(
            {
                "sucursal": sucursal.id,
                "fecha": fecha,
                "horarios": [h.strftime("%H:%M") for h in libres],
            }
        )

    @extend_schema(request=None, responses=TurnoSerializer)
    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        turno = self.get_object()
        servicios.cambiar_estado(turno, EstadoTurno.CANCELADO)
        return Response(TurnoSerializer(turno).data)

    @extend_schema(request=CambiarEstadoSerializer, responses=TurnoSerializer)
    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
    def cambiar_estado(self, request, pk=None):
        turno = self.get_object()
        entrada = CambiarEstadoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        servicios.cambiar_estado(turno, entrada.validated_data["estado"])
        return Response(TurnoSerializer(turno).data)