from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Sucursal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, unique=True)),
                ('direccion', models.CharField(max_length=200)),
                ('ciudad', models.CharField(max_length=100)),
                ('telefono', models.CharField(blank=True, max_length=30)),
                ('activo', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name_plural': 'sucursales',
                'ordering': ['nombre'],
            },
        ),
    ]