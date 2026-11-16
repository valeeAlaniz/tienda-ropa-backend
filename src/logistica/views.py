from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (
    SAFE_METHODS,
    AllowAny,
    BasePermission,
    IsAdminUser,
    IsAuthenticated,
)
from rest_framework.response import Response

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


class AdminOSoloLectura(BasePermission):
    """Cualquiera puede leer; solo el personal puede crear, editar o borrar."""

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or bool(
            request.user and request.user.is_staff
        )


class SucursalViewSet(viewsets.ModelViewSet):
    queryset = Sucursal.objects.all()
    serializer_class = SucursalSerializer
    permission_classes = [AdminOSoloLectura]


class HorarioAtencionViewSet(viewsets.ModelViewSet):
    queryset = HorarioAtencion.objects.select_related("sucursal")
    serializer_class = HorarioAtencionSerializer
    permission_classes = [AdminOSoloLectura]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["sucursal", "dia_semana"]


class TurnoViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Turno.objects.select_related("sucursal")
    serializer_class = TurnoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["sucursal", "tipo", "estado", "fecha"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if getattr(self, "swagger_fake_view", False):
            return queryset.none()
        usuario = self.request.user
        # El personal ve todos los turnos; cada cliente, solo los suyos
        return queryset if usuario.is_staff else queryset.filter(cliente=usuario)

    @extend_schema(request=TurnoCrearSerializer, responses={201: TurnoSerializer})
    def create(self, request, *args, **kwargs):
        entrada = TurnoCrearSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        turno = servicios.crear_turno(cliente=request.user, **entrada.validated_data)
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