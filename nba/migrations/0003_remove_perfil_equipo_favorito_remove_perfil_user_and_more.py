# Generated by Django 5.0.3 on 2025-05-06 16:59

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('nba', '0002_equipo_perfil_delete_perfilusuario'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='perfil',
            name='equipo_favorito',
        ),
        migrations.RemoveField(
            model_name='perfil',
            name='user',
        ),
        migrations.DeleteModel(
            name='Equipo',
        ),
        migrations.DeleteModel(
            name='Perfil',
        ),
    ]
