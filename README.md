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


## Alquileres (alquileres)

Modelo `Alquiler`: el alquiler de una prenda por parte de un cliente durante un rango de fechas. Por ahora está disponible el modelo y su gestión desde el panel de administración (`/admin/`); los endpoints de la API se agregan en una etapa posterior.

Campos:

| Campo | Descripción |
|-------|-------------|
| `cliente` | Cliente que alquila (no se puede borrar un cliente con alquileres) |
| `prenda` | Prenda alquilada (no se puede borrar una prenda con alquileres) |
| `fecha_inicio` / `fecha_fin` | Rango del alquiler; `fecha_fin` no puede ser anterior a `fecha_inicio` |
| `estado` | `reservado` (por defecto), `retirado`, `devuelto` o `cancelado` |
| `precio_por_dia` | Precio diario al momento de alquilar (debe ser mayor a 0) |
| `precio_total` | Se calcula solo al guardar: `precio_por_dia` × días |
| `creado` | Fecha y hora de creación |

Cálculo de días: se cuentan el primer y el último día. Por ejemplo, del 20 al 22 son 3 días, y un alquiler de un solo día cuenta como 1. El `precio_total` se recalcula cada vez que se guarda el alquiler.

Validaciones: la fecha de fin anterior al inicio y un precio por día menor o igual a 0 se rechazan, tanto en el modelo como en la base de datos.

Tests: `uv run src/manage.py test alquileres`