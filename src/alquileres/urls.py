from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PrendaAlquilerViewSet

router = DefaultRouter()
router.register(r'prendas-alquiler', PrendaAlquilerViewSet, basename='prenda-alquiler')

urlpatterns = [
    path('', include(router.urls)),
]