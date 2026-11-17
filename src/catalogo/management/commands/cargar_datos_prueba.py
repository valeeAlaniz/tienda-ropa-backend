from django.core.management.base import BaseCommand

from catalogo.models import Categoria, Prenda


def foto(semilla):
    # Imágenes de prueba. Se reemplazan por fotos reales desde el panel.
    return f"https://picsum.photos/seed/{semilla}/600/800"


CATEGORIAS = [
    ("Camisas y remeras", "Prendas livianas para el día a día."),
    ("Pantalones y faldas", "Cortes clásicos y modernos."),
    ("Abrigos", "Camperas, sacos y tapados."),
]

# nombre, descripción, categoría, talle, color, precio, stock, destacado
PRENDAS = [
    ("Camisa de lino", "Camisa de lino liviana, ideal para el verano.", "Camisas y remeras", "M", "Blanco", "38500", 8, True),
    ("Camisa slim", "Camisa de algodón con corte entallado.", "Camisas y remeras", "L", "Celeste", "35200", 6, False),
    ("Remera básica", "Remera de algodón peinado, cuello redondo.", "Camisas y remeras", "S", "Negro", "18900", 15, False),
    ("Pantalón sastrero", "Pantalón de vestir de corte recto.", "Pantalones y faldas", "M", "Gris", "52000", 5, True),
    ("Jean recto", "Jean de denim con lavado oscuro.", "Pantalones y faldas", "L", "Azul", "47500", 10, False),
    ("Falda midi", "Falda midi con tajo lateral.", "Pantalones y faldas", "S", "Verde", "41000", 4, False),
    ("Saco de lana", "Saco de lana con forro interior.", "Abrigos", "L", "Gris", "89000", 3, True),
    ("Campera de cuero", "Campera de cuero ecológico con cierre.", "Abrigos", "M", "Negro", "112000", 2, False),
    ("Tapado clásico", "Tapado largo con botones y bolsillos.", "Abrigos", "XL", "Camel", "135000", 2, True),
    ("Chaleco acolchado", "Chaleco liviano y abrigado.", "Abrigos", "UNICO", "Azul", "64000", 7, False),
]


class Command(BaseCommand):
    help = "Carga categorías y prendas de prueba. Se puede correr más de una vez."

    def handle(self, *args, **options):
        categorias = {}
        for nombre, descripcion in CATEGORIAS:
            categoria, _ = Categoria.objects.get_or_create(
                nombre=nombre, defaults={"descripcion": descripcion}
            )
            categorias[nombre] = categoria

        creadas = 0
        for nombre, descripcion, categoria, talle, color, precio, stock, destacado in PRENDAS:
            _, nueva = Prenda.objects.get_or_create(
                nombre=nombre,
                talle=talle,
                defaults={
                    "descripcion": descripcion,
                    "categoria": categorias[categoria],
                    "color": color,
                    "precio": precio,
                    "stock": stock,
                    "destacado": destacado,
                    "imagen": foto(nombre.replace(" ", "-").lower()),
                },
            )
            creadas += int(nueva)

        self.stdout.write(
            self.style.SUCCESS(
                f"Listo: {len(categorias)} categorías y {creadas} prendas nuevas."
            )
        )