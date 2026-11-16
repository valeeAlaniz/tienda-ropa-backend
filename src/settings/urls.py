from django.contrib import admin
from django.urls import include, path  
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    # Apps del proyecto (cada una con su respectiva línea include)
    path("api/categorias/", include("catalogo.urls")),  # O la ruta que maneje el catálogo de Valentina
    path("api/ventas/", include("ventas.urls")),  
    # Próximamente se sumarán aquí las de clientes, logistica/turnos y alquileres según avancen tus compañeros...
]