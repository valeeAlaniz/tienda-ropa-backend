from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from catalogo.permissions import IsStaffOrReadOnly

from .models import Sucursal
from .serializers import SucursalSerializer


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