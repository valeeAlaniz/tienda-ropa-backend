from rest_framework.routers import DefaultRouter

from .views import HorarioAtencionViewSet, SucursalViewSet, TurnoViewSet

router = DefaultRouter()
router.register("sucursales", SucursalViewSet)
router.register("horarios-atencion", HorarioAtencionViewSet)
router.register("turnos", TurnoViewSet)

urlpatterns = router.urls