# Tienda de ropa - Backend

API REST (Django y Django REST Framework) de una tienda de ropa con alquiler de prendas.


## Ejecutar en local

    uv sync
    uv run src/manage.py migrate
    uv run src/manage.py runserver

Documentacion de la API: http://localhost:8000/api/schema/swagger/

## Sucursales (logistica)

Locales de la tienda donde se retiran pedidos y se atienden los turnos.

| Método | Ruta | Quién puede |
|--------|------|-------------|
| GET | `/api/logistica/sucursales/` | Cualquiera (solo ve las activas) |
| GET | `/api/logistica/sucursales/{id}/` | Cualquiera (solo activas) |
| POST | `/api/logistica/sucursales/` | Staff |
| PUT / PATCH | `/api/logistica/sucursales/{id}/` | Staff |
| DELETE | `/api/logistica/sucursales/{id}/` | Staff (borrado lógico: `activo=False`) |

El staff también ve las sucursales inactivas.

Campos: `nombre` (único), `direccion`, `ciudad`, `telefono` (opcional) y `activo`.

Filtros y búsqueda: `?ciudad=`, `?activo=`, `?search=` y `?ordering=`.

Tests: `uv run manage.py test logistica`