from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .registration import RegistroClienteView
from .views import ClienteViewSet, DireccionViewSet

router = DefaultRouter()
router.register("clientes", ClienteViewSet, basename="cliente")
router.register("direcciones", DireccionViewSet, basename="direccion")

urlpatterns = [
    path("registro/", RegistroClienteView.as_view(), name="registro-cliente"),
    path("", include(router.urls)),
]