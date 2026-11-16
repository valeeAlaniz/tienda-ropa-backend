from rest_framework.routers import DefaultRouter

from .views import CategoriaViewSet, PrendaViewSet

router = DefaultRouter()
router.register("categorias", CategoriaViewSet, basename="categorias")
router.register("prendas", PrendaViewSet, basename="prendas")

urlpatterns = router.urls