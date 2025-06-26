from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('registro/', views.registro, name='registro'),
    path('inicio_sesion/', views.inicio_sesion, name='inicio_sesion'),
    path('menu/', views.menu, name='menu_principal'),
    path('cerrar_sesion/', views.salir, name='cerrar_sesion'),
    path('entrar_invitado/', views.entrar_invitado, name='entrar_invitado'),
    path('recuperar_contraseña/', views.recuperar_contraseña, name='recuperar_contraseña'),
    
    path('noticias/', views.menu, name='noticias'),
    path('partidos/', views.partidos, name='partidos'),
    path('clasificacion/', views.clasificacion, name='clasificacion'),
    path('descubrir/', views.descubrir, name='descubrir'),

    path('obtener_partidos/', views.obtener_partidos, name='obtener_partidos'),
    path('obtener_clasificacion/', views.obtener_clasificacion, name='obtener_clasificacion'),

    path('stats_partido/<int:partido_id>/', views.stats_partido, name='stats_partido'),

    path('elegir-equipo/', views.elegir_equipo, name='elegir_equipo')
    
]