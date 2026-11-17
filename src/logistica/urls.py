from rest_framework.routers import DefaultRouter

from .views import HorarioAtencionViewSet, SucursalViewSet, TurnoViewSet

router = DefaultRouter()
router.register("sucursales", SucursalViewSet, basename="sucursales")
router.register("horarios-atencion", HorarioAtencionViewSet, basename="horarios-atencion")
router.register("turnos", TurnoViewSet, basename="turnos")

urlpatterns = router.urls