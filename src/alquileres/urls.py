from rest_framework.routers import DefaultRouter

from .prendas_views import PrendaAlquilerViewSet

router = DefaultRouter()
router.register("prendas-alquiler", PrendaAlquilerViewSet, basename="prendas-alquiler")

urlpatterns = router.urls
