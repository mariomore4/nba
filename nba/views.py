import requests
import datetime
from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import RegistroFormulario
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout as cerrar_sesion
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import User
from django import forms
from urllib.request import Request, urlopen
import json
from django.http import JsonResponse
from django.core.cache import cache
import unicodedata
from .models import PreferenciaUsuario
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
import pytz
from dateutil import parser
from django.conf import settings
import os

# Create your views here.
def index(request):
    return render(request, 'index.html')

def registro(request):
    if request.method == 'POST':
        form = RegistroFormulario(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data['username']
            messages.success(request, f'Usuario {username} creado correctamente')
            return redirect('inicio_sesion')
    else: 
        form = RegistroFormulario()
    return render(request, 'registro.html', { 'form' : form })

def inicio_sesion(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('elegir_equipo')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')
            return render(request, 'inicio_sesion.html', {'error_message': 'Credenciales inválidas. Por favor, inténtalo de nuevo.'})
    else:
        return render(request, 'inicio_sesion.html')




def menu(request):
    url_noticias = "https://nba-latest-news.p.rapidapi.com/articles"
    headers_noticias = {
        "X-RapidAPI-Key": "2edaa0c31cmsh8ef036d43a7ad51p10abd9jsnf4d572ffb618",
        "X-RapidAPI-Host": "nba-latest-news.p.rapidapi.com"
    }

    headers_api = {
        "X-RapidAPI-Key": "2edaa0c31cmsh8ef036d43a7ad51p10abd9jsnf4d572ffb618",
        "X-RapidAPI-Host": "api-nba-v1.p.rapidapi.com"
    }

    equipo_favorito = None
    logo_equipo = None
    ultimo_partido = None

    # Solo si el usuario está autenticado, obtenemos su equipo favorito y partidos
    if request.user.is_authenticated:
        try:
            preferencia = PreferenciaUsuario.objects.get(usuario=request.user)
            equipo_favorito = preferencia.equipo_favorito
            logo_equipo = f"logos/{equipo_favorito.replace(' ', '_')}.png"
        except PreferenciaUsuario.DoesNotExist:
            pass

        if equipo_favorito:
            try:
                url_teams = "https://api-nba-v1.p.rapidapi.com/teams"
                response_teams = requests.get(url_teams, headers=headers_api)
                response_teams.raise_for_status()
                teams_data = response_teams.json().get("response", [])

                equipo_id = None
                for team in teams_data:
                    if team["name"].lower() == equipo_favorito.lower():
                        equipo_id = team["id"]
                        break

                if equipo_id:
                    url_games = f"https://api-nba-v1.p.rapidapi.com/games?team={equipo_id}&season=2024"
                    response_games = requests.get(url_games, headers=headers_api)
                    response_games.raise_for_status()
                    all_games = response_games.json().get("response", [])

                    partidos_finalizados = [
                        {
                            "fecha": game["date"]["start"],
                            "home": game["teams"]["home"]["name"],
                            "home_score": game["scores"]["home"]["points"],
                            "visitor": game["teams"]["visitors"]["name"],
                            "visitor_score": game["scores"]["visitors"]["points"],
                            "estado": game["status"]["long"]
                        }
                        for game in all_games if game["status"]["long"] == "Finished"
                    ]

                    partidos_finalizados.sort(key=lambda x: parser.parse(x["fecha"]), reverse=True)
                    ultimo_partido = partidos_finalizados[0] if partidos_finalizados else None

            except Exception as e:
                print(f"Error al obtener partidos del equipo favorito: {e}")

    # Obtener noticias para todos, logueados o invitados
    try:
        response = requests.get(url_noticias, headers=headers_noticias)
        response.raise_for_status()
        noticias = response.json()
        noticias = [{'title': n['title'], 'description': n.get('description')} for n in noticias]
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener las noticias: {e}")
        noticias = []

    return render(request, 'menu.html', {
        'noticias': noticias,
        'section': 'noticias',
        'equipo_favorito': equipo_favorito,
        'logo_equipo': logo_equipo,
        'ultimo_partido': ultimo_partido,
    })

def salir(request):
    cerrar_sesion(request)
    return redirect('index')

def entrar_invitado(request):
    url_noticias = "https://nba-latest-news.p.rapidapi.com/articles"
    headers_noticias = {
        "X-RapidAPI-Key": "2edaa0c31cmsh8ef036d43a7ad51p10abd9jsnf4d572ffb618",
        "X-RapidAPI-Host": "nba-latest-news.p.rapidapi.com"
    }

    try:
        response = requests.get(url_noticias, headers=headers_noticias)
        response.raise_for_status()
        noticias = response.json()
        noticias = [{'title': n['title'], 'description': n.get('description')} for n in noticias]
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener las noticias: {e}")
        noticias = []

    return render(request, 'menu.html', {
        'noticias': noticias,
        'section': 'noticias',
        'equipo_favorito': None,
        'logo_equipo': None,
        'ultimo_partido': None,
    })

def recuperar_contraseña(request):
    if request.method == 'POST':
        form = CustomSetPasswordForm(request.user, request.POST)
        email = request.POST.get('email')
        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)
            if form.is_valid():
                user.set_password(form.cleaned_data.get('new_password1'))
                user.save()
                messages.success(request, 'Contraseña cambiada exitosamente.')
                return redirect('inicio_sesion')
            else:
                messages.error(request, 'Error al cambiar la contraseña.')
        else:
            messages.error(request, 'Correo electrónico no encontrado.')
    else:
        form = CustomSetPasswordForm(request.user)
    return render(request, 'recuperar_contraseña.html', {'form': form})

class CustomSetPasswordForm(SetPasswordForm):
    def clean_new_password1(self):
        password1 = self.cleaned_data.get('new_password1')
        if len(password1) < 5:
            raise forms.ValidationError("La contraseña debe tener al menos 5 caracteres.")
        return password1

def partidos(request):
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')  # Fecha actual 
    api_url = f"https://api-nba-v1.p.rapidapi.com/games?date={fecha_hoy}"
    headers = {
        "X-RapidAPI-Key": "2edaa0c31cmsh8ef036d43a7ad51p10abd9jsnf4d572ffb618",
        "X-RapidAPI-Host": "api-nba-v1.p.rapidapi.com"
    }

    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        partidos_data = response.json()

        # ✅ Imprimir el JSON formateado en la terminal para inspección
        print(json.dumps(partidos_data, indent=4))

        partidos = partidos_data.get('response', [])

    except requests.exceptions.RequestException as e:
        print(f"Error al hacer la solicitud a la API: {e}")
        partidos = []  # Si hay error, devuelve lista vacía

    # Obtener equipo favorito si el usuario está autenticado
    equipo_favorito = None
    if request.user.is_authenticated:
        try:
            from .models import PreferenciaUsuario  # Asegúrate de importar el modelo si no está al inicio
            equipo_favorito = PreferenciaUsuario.objects.get(usuario=request.user).equipo_favorito
        except PreferenciaUsuario.DoesNotExist:
            pass

    return render(request, 'partidos.html', {
        'partidos': partidos,
        'fecha': fecha_hoy,
        'section': 'partidos',
        'equipo_favorito': equipo_favorito
    })

def clasificacion(request):
    # Obtener el año seleccionado desde el formulario (por defecto la temporada actual)
    current_year = datetime.now().year
    default_season = f"{current_year-1}-{current_year}"
    year = request.GET.get('year', default_season)

    # Generar las temporadas en formato '2018-2019' hasta el año actual
    years = [f"{y}-{y+1}" for y in range(2018, current_year)]
    years = list(dict.fromkeys(years))  # Elimina duplicados

    # Asegurar que "2024-2025" esté en el desplegable
    if "2024-2025" not in years:
        years.append("2024-2025")
    years.sort(reverse=True)

    year_for_api = year.split('-')[0]  # Año para la API (ej: "2021")

    este = []
    oeste = []

    # Cargar JSON local si es la temporada 2024-2025
    if year == "2024-2025":
        try:
            ruta = os.path.join(settings.BASE_DIR, 'nba', 'static', 'json', 'clasificacion_2024_2025.json')
            with open(ruta, 'r', encoding='utf-8') as f:
                datos = json.load(f)
                este = datos.get("este", [])
                oeste = datos.get("oeste", [])
        except FileNotFoundError:
            print("No se encontró el archivo clasificacion_2024_2025.json")
    else:
        url = f"https://api-nba-v1.p.rapidapi.com/standings?league=standard&season={year_for_api}"
        headers = {
            "X-RapidAPI-Key": "2edaa0c31cmsh8ef036d43a7ad51p10abd9jsnf4d572ffb618",
            "X-RapidAPI-Host": "api-nba-v1.p.rapidapi.com"
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            datos = response.json()

            if "response" not in datos:
                raise ValueError("La respuesta de la API no contiene los datos esperados.")

            equipos = datos["response"]
            equipos_vistos = set()

            correccion_logos = {
                20: "https://upload.wikimedia.org/wikipedia/en/f/fb/Miami_Heat_logo.svg",
                21: "https://upload.wikimedia.org/wikipedia/en/4/4a/Milwaukee_Bucks_logo.svg",
                25: "https://upload.wikimedia.org/wikipedia/en/5/5d/Oklahoma_City_Thunder.svg",
                26: "https://upload.wikimedia.org/wikipedia/en/1/10/Orlando_Magic_logo.svg",
                27: "https://upload.wikimedia.org/wikipedia/en/0/0e/Philadelphia_76ers_logo.svg"
            }

            for equipo in equipos:
                team_data = equipo.get("team", {})
                conference_data = equipo.get("conference", {})

                team_id = team_data.get("id")
                name = team_data.get("name", "Equipo Desconocido")
                logo = team_data.get("logo", "ruta/por/defecto/logo.png")
                conference = conference_data.get("name", "")
                rank = str(conference_data.get("rank", "N/A"))
                win = equipo.get("win", {}).get("total", 0)
                loss = equipo.get("loss", {}).get("total", 0)
                percentage = equipo.get("win", {}).get("percentage", "0.000")
                lastTen = equipo.get("win", {}).get("lastTen", 0)

                if team_id in correccion_logos:
                    logo = correccion_logos[team_id]

                if team_id and team_id not in equipos_vistos:
                    equipos_vistos.add(team_id)
                    team_info = {
                        "rank": rank,
                        "name": name,
                        "logo": logo,
                        "win": win,
                        "loss": loss,
                        "percentage": percentage,
                        "lastTen": lastTen
                    }

                    if conference.lower() == "east":
                        este.append(team_info)
                    elif conference.lower() == "west":
                        oeste.append(team_info)

            este.sort(key=lambda x: int(x["rank"]) if x["rank"].isdigit() else float('inf'))
            oeste.sort(key=lambda x: int(x["rank"]) if x["rank"].isdigit() else float('inf'))

        except requests.exceptions.RequestException as e:
            print(f"Error al obtener la clasificación: {e}")
        except ValueError as e:
            print(f"Error con los datos de la API: {e}")

    return render(request, "clasificacion.html", {
        "este": este,
        "oeste": oeste,
        "section": "clasificacion",
        "selected_year": year,
        "years": years
    })

def normalizar(texto):
    """ Normaliza el texto para que no haya acentos y sea todo en minúsculas. """
    if not texto:
        return ''
    texto = texto.lower().replace(' ', '')
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )

def descubrir(request):
    search_query = normalizar(request.GET.get('search', ''))
    jugadores_info = []

    headers = {
        "X-RapidAPI-Key": "2edaa0c31cmsh8ef036d43a7ad51p10abd9jsnf4d572ffb618",
        "X-RapidAPI-Host": "api-nba-v1.p.rapidapi.com"
    }

    if search_query:
        jugadores_totales = []
        
        # Buscar por el nombre o apellido usando la API
        url_busqueda = f"https://api-nba-v1.p.rapidapi.com/players?search={search_query}"
        try:
            response = requests.get(url_busqueda, headers=headers)
            response.raise_for_status()
            data = response.json().get('response', [])
            jugadores_totales.extend(data)
        except requests.exceptions.RequestException as e:
            print(f"Error en la solicitud: {e}")

        # Usamos un diccionario para manejar duplicados por nombre completo y priorizar los jugadores con detalles
        jugadores_vistos = {}

        for jugador in jugadores_totales:
            first_name = jugador.get('firstname', '').strip()
            last_name = jugador.get('lastname', '').strip()
            nombre_completo = f"{first_name} {last_name}"

            # Si el jugador no tiene detalles completos, no lo añadimos como duplicado
            jugador_info = {
                'id': jugador.get('id'),
                'firstName': first_name,
                'lastName': last_name,
                'birthDate': jugador.get('birth', {}).get('date'),
                'birthCountry': jugador.get('birth', {}).get('country'),
                'nbaStart': jugador.get('nba', {}).get('start'),
                'proYears': jugador.get('nba', {}).get('pro'),
                'height': f"{jugador.get('height', {}).get('feets')}′{jugador.get('height', {}).get('inches')}″",
                'heightMeters': jugador.get('height', {}).get('meters'),
                'weightLbs': jugador.get('weight', {}).get('pounds'),
                'weightKg': jugador.get('weight', {}).get('kilograms'),
                'college': jugador.get('college'),
                'affiliation': jugador.get('affiliation'),
                'jersey': jugador.get('leagues', {}).get('standard', {}).get('jersey'),
                'position': jugador.get('leagues', {}).get('standard', {}).get('pos'),
                'active': jugador.get('leagues', {}).get('standard', {}).get('active'),
            }

            # Si ya hemos visto un jugador con este nombre completo, aseguramos que tomamos el que tiene detalles completos
            if nombre_completo.lower() in jugadores_vistos:
                # Si ya existe pero este jugador tiene más detalles, reemplazamos
                if jugador_info['birthDate'] and jugador_info['birthCountry']:  # Verificamos si tiene detalles completos
                    jugadores_vistos[nombre_completo.lower()] = jugador_info
            else:
                # Si no lo hemos visto antes, añadimos
                jugadores_vistos[nombre_completo.lower()] = jugador_info

        # Convertimos el diccionario a lista para que se pueda enviar al frontend
        jugadores_info = list(jugadores_vistos.values())

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'jugadores': jugadores_info})

    return render(request, 'descubrir.html', {
        'section': 'descubrir',
        'search_query': request.GET.get('search', ''),
        'jugadores': jugadores_info
    })


def obtener_partidos(request):
    fecha = request.GET.get('fecha', None)
    if not fecha:
        return JsonResponse({'error': 'Fecha no proporcionada'}, status=400)
    
    # Verificar si los datos ya están en caché
    partidos_cache_key = f"partidos_{fecha}"
    partidos = cache.get(partidos_cache_key)
    
    if not partidos:
        url = f"https://api-nba-v1.p.rapidapi.com/games?date={fecha}"
        headers = {
            'X-RapidAPI-Key': '2edaa0c31cmsh8ef036d43a7ad51p10abd9jsnf4d572ffb618',
            'X-RapidAPI-Host': 'api-nba-v1.p.rapidapi.com'
        }

        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            partidos = response.json()
            # Guardar en caché por 1 hora
            cache.set(partidos_cache_key, partidos, timeout=3600)
        else:
            return JsonResponse({'error': 'Error al obtener los partidos de la API'}, status=response.status_code)
    
    return JsonResponse(partidos)


def obtener_clasificacion(request):
    year = request.GET.get('year', None)
    if not year:
        return JsonResponse({'error': 'Año no proporcionado'}, status=400)
    
    # Verificar si los datos ya están en caché
    clasificacion_cache_key = f"clasificacion_{year}"
    clasificacion = cache.get(clasificacion_cache_key)
    
    if not clasificacion:
        url = f"https://api-nba-v1.p.rapidapi.com/standings?season={year}"
        headers = {
            'X-RapidAPI-Key': '2edaa0c31cmsh8ef036d43a7ad51p10abd9jsnf4d572ffb618',
            'X-RapidAPI-Host': 'api-nba-v1.p.rapidapi.com'
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Esto lanzará una excepción si el status code no es 200
        except requests.exceptions.HTTPError as errh:
            return JsonResponse({'error': f'Error de HTTP: {errh}'}, status=500)
        except requests.exceptions.RequestException as err:
            return JsonResponse({'error': f'Error al realizar la solicitud: {err}'}, status=500)
        
        if response.status_code == 200:
            clasificacion = response.json()
            # Guardar en caché por 1 hora (3600 segundos)
            cache.set(clasificacion_cache_key, clasificacion, timeout=3600)
        else:
            return JsonResponse({'error': 'Error al obtener la clasificación de la API'}, status=response.status_code)
    
    return JsonResponse(clasificacion)



def stats_partido(request, partido_id):
    # URL base y headers para las peticiones API
    url_base = "https://api-nba-v1.p.rapidapi.com"
    headers = {
        "X-RapidAPI-Host": "api-nba-v1.p.rapidapi.com",
        "X-RapidAPI-Key": "2edaa0c31cmsh8ef036d43a7ad51p10abd9jsnf4d572ffb618"
    }

    # Diccionario de logos personalizados
    logos_personalizados = {
        "Milwaukee Bucks": "https://upload.wikimedia.org/wikipedia/en/4/4a/Milwaukee_Bucks_logo.svg",
        "Oklahoma City Thunder": "https://upload.wikimedia.org/wikipedia/en/5/5d/Oklahoma_City_Thunder.svg",
        "Orlando Magic": "https://upload.wikimedia.org/wikipedia/en/1/10/Orlando_Magic_logo.svg",  # Nueva URL
        "Miami Heat": "https://upload.wikimedia.org/wikipedia/en/f/fb/Miami_Heat_logo.svg",
        "Philadelphia 76ers": "https://upload.wikimedia.org/wikipedia/en/0/0e/Philadelphia_76ers_logo.svg"
    }

    # Estadísticas que queremos mostrar
    estadisticas_deseadas = [
        'points', 'fgm', 'fga', 'fgp', 'ftm', 'fta', 'ftp', 'tpm', 'tpa', 'tpp', 
        'offReb', 'defReb', 'totReb', 'assists', 'pFouls', 'steals', 'turnovers', 
        'blocks', 'plusMinus', 'min'
    ]

    # 1. Petición para obtener las estadísticas de los equipos
    url_equipo = f"{url_base}/games/statistics"
    params_equipo = {"id": partido_id}  # El 'id' es el identificador del partido
    response_equipo = requests.get(url_equipo, headers=headers, params=params_equipo)
    data_equipo = response_equipo.json()

    # Verificamos si la respuesta tiene resultados
    if data_equipo['results'] == 0:
        return render(request, 'stats_partido.html', {'error': 'No se encontraron datos del partido o el partido no existe.'})

    # Aseguramos que tenemos la respuesta de los equipos
    if 'response' not in data_equipo or len(data_equipo['response']) < 2:
        return render(request, 'stats_partido.html', {'error': 'No se encontraron los equipos para este partido.'})

    # Obtenemos los equipos y sus estadísticas
    equipos = data_equipo['response']
    equipo_1 = equipos[0]['team']  # Equipo 1
    equipo_2 = equipos[1]['team']  # Equipo 2

    # Comprobamos y asignamos los logos personalizados si es necesario
    if equipo_1['name'] in logos_personalizados:
        equipo_1['logo'] = logos_personalizados[equipo_1['name']]
    if equipo_2['name'] in logos_personalizados:
        equipo_2['logo'] = logos_personalizados[equipo_2['name']]

    # Filtramos solo las estadísticas deseadas
    equipo_1_stats = {key: equipos[0]['statistics'][0].get(key) for key in estadisticas_deseadas}
    equipo_2_stats = {key: equipos[1]['statistics'][0].get(key) for key in estadisticas_deseadas}

    # 2. Petición para obtener las estadísticas de los jugadores
    url_jugadores = f"{url_base}/players/statistics"
    params_jugadores = {"game": partido_id}  # Usamos el mismo 'game' (partido_id)
    response_jugadores = requests.get(url_jugadores, headers=headers, params=params_jugadores)
    data_jugadores = response_jugadores.json()

    # Si no hay resultados de jugadores, asignamos una lista vacía
    jugadores = data_jugadores.get('response', [])

    # Pasamos los datos al template
    return render(request, 'stats_partido.html', {
        'equipos': [equipo_1, equipo_2],
        'estadisticas_equipo_1': equipo_1_stats,
        'estadisticas_equipo_2': equipo_2_stats,
        'jugadores': jugadores,
        'fecha_partido': data_equipo['response'][0].get('date', {}).get('start', 'No disponible'),
        'arena': data_equipo['response'][0].get('arena', {}).get('name', 'No disponible'),
        'ciudad': data_equipo['response'][0].get('arena', {}).get('city', 'No disponible')
    })


def elegir_equipo(request):
    equipos = [
        {'id': 1, 'nombre': 'Atlanta Hawks', 'logo': 'Atlanta_Hawks.png'},
        {'id': 2, 'nombre': 'Boston Celtics', 'logo': 'Boston_Celtics.png'},
        {'id': 3, 'nombre': 'Brooklyn Nets', 'logo': 'Brooklyn_Nets.png'},
        {'id': 4, 'nombre': 'Charlotte Hornets', 'logo': 'Charlotte_Hornets.png'},
        {'id': 5, 'nombre': 'Chicago Bulls', 'logo': 'Chicago_Bulls.png'},
        {'id': 6, 'nombre': 'Cleveland Cavaliers', 'logo': 'Cleveland_Cavaliers.png'},
        {'id': 7, 'nombre': 'Dallas Mavericks', 'logo': 'Dallas_Mavericks.png'},
        {'id': 8, 'nombre': 'Denver Nuggets', 'logo': 'Denver_Nuggets.png'},
        {'id': 9, 'nombre': 'Detroit Pistons', 'logo': 'Detroit_Pistons.png'},
        {'id': 10, 'nombre': 'Golden State Warriors', 'logo': 'Golden_State_Warriors.png'},
        {'id': 11, 'nombre': 'Houston Rockets', 'logo': 'Houston_Rockets.png'},
        {'id': 12, 'nombre': 'Indiana Pacers', 'logo': 'Indiana_Pacers.png'},
        {'id': 13, 'nombre': 'LA Clippers', 'logo': 'LA_Clippers.png'},
        {'id': 14, 'nombre': 'Los Angeles Lakers', 'logo': 'Los_Angeles_Lakers.png'},
        {'id': 15, 'nombre': 'Memphis Grizzlies', 'logo': 'Memphis_Grizzlies.png'},
        {'id': 16, 'nombre': 'Miami Heat', 'logo': 'Miami_Heat.png'},
        {'id': 17, 'nombre': 'Milwaukee Bucks', 'logo': 'Milwaukee_Bucks.png'},
        {'id': 18, 'nombre': 'Minnesota Timberwolves', 'logo': 'Minnesota_Timberwolves.png'},
        {'id': 19, 'nombre': 'New Orleans Pelicans', 'logo': 'New_Orleans_Pelicans.png'},
        {'id': 20, 'nombre': 'New York Knicks', 'logo': 'New_York_Knicks.png'},
        {'id': 21, 'nombre': 'Oklahoma City Thunder', 'logo': 'Oklahoma_City_Thunder.png'},
        {'id': 22, 'nombre': 'Orlando Magic', 'logo': 'Orlando_Magic.png'},
        {'id': 23, 'nombre': 'Philadelphia 76ers', 'logo': 'Philadelphia_76ers.png'},
        {'id': 24, 'nombre': 'Phoenix Suns', 'logo': 'Phoenix_Suns.png'},
        {'id': 25, 'nombre': 'Portland Trail Blazers', 'logo': 'Portland_Trail_Blazers.png'},
        {'id': 26, 'nombre': 'Sacramento Kings', 'logo': 'Sacramento_Kings.png'},
        {'id': 27, 'nombre': 'San Antonio Spurs', 'logo': 'San_Antonio_Spurs.png'},
        {'id': 28, 'nombre': 'Toronto Raptors', 'logo': 'Toronto_Raptors.png'},
        {'id': 29, 'nombre': 'Utah Jazz', 'logo': 'Utah_Jazz.png'},
        {'id': 30, 'nombre': 'Washington Wizards', 'logo': 'Washington_Wizards.png'},
    ]

    if request.method == 'POST':
        equipo_nombre = request.POST.get('equipo_nombre')
        equipo_logo = request.POST.get('equipo_logo')
        
        if equipo_nombre and equipo_logo and request.user.is_authenticated:
            PreferenciaUsuario.objects.update_or_create(
                usuario=request.user,
                defaults={
                    'equipo_favorito': equipo_nombre,
                    'logo_equipo': equipo_logo  # ← Asegúrate que exista este campo en tu modelo
                }
            )
            return redirect('menu_principal')

    return render(request, 'elegir_equipo.html', {'equipos': equipos})