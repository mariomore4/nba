from django.db import models
from django.contrib.auth.models import User

class PreferenciaUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    equipo_favorito = models.CharField(max_length=100)
    logo_equipo = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.usuario.username} - {self.equipo_favorito}"
