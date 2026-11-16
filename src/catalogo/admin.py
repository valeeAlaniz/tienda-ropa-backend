from django.contrib import admin

from .models import Categoria, Prenda


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activa")
    list_filter = ("activa",)
    search_fields = ("nombre", "descripcion")


@admin.register(Prenda)
class PrendaAdmin(admin.ModelAdmin):
    list_display = (
        "nombre", "categoria", "talle", "color", "precio", "stock", "destacado", "activo",
    )
    list_filter = ("categoria", "talle", "destacado", "activo")
    search_fields = ("nombre", "descripcion", "color")