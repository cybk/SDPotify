"""
Lógica de autenticación con Spotify — misma estrategia que usamos en el
servidor MCP (spotify-mcp/server.py): Authorization Code flow vía spotipy,
con el token cacheado en disco para no tener que reautenticar cada vez.

Este módulo es intencionalmente el único lugar que toca el archivo de caché
del token. La autenticación se resuelve una sola vez al arrancar el daemon
(ver run.py); los requests solo reutilizan el cliente ya creado en memoria.
"""

import os
from pathlib import Path

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import CacheFileHandler, SpotifyOAuth, SpotifyOauthError

load_dotenv()

SCOPES = " ".join(
    [
        "user-read-playback-state",
        "user-modify-playback-state",
        "user-read-currently-playing",
    ]
)

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8080/callback")
# Las rutas relativas se resuelven contra la carpeta del proyecto, no contra el
# directorio de trabajo del proceso (que en el Programador de tareas suele ser
# C:\Windows\System32 y haría perder el token guardado).
BASE_DIR = Path(__file__).resolve().parent
CACHE_PATH = str(
    BASE_DIR / os.getenv("SPOTIFY_CACHE_PATH", ".spotify_token_cache")
)

_client: spotipy.Spotify | None = None


class AuthError(RuntimeError):
    """No hay una sesión de Spotify válida y no se puede (o no se debe)
    iniciar el login interactivo."""


def ensure_authenticated(login: bool = False) -> None:
    """Deja listo el cliente de Spotify. Se llama una sola vez al arrancar.

    - login=False (arranque normal / tarea programada): solo usa el token de
      la caché, refrescándolo si hace falta. Nunca abre el navegador; si no
      hay token válido lanza AuthError con instrucciones.
    - login=True (primera vez, a mano): si no hay token válido abre el
      navegador para autorizar y guarda el token en la caché.
    """
    global _client

    if not CLIENT_ID or not CLIENT_SECRET:
        raise AuthError(
            "Faltan SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET. "
            "Revisa el archivo .env (ver .env.example)."
        )

    auth_manager = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPES,
        cache_handler=CacheFileHandler(cache_path=CACHE_PATH),
        open_browser=login,
    )

    try:
        token_info = auth_manager.validate_token(
            auth_manager.cache_handler.get_cached_token()
        )
    except SpotifyOauthError:
        # Refresh token rechazado (revocado, credenciales distintas, etc.)
        token_info = None

    if token_info is None:
        if not login:
            raise AuthError(
                "No hay un token de Spotify válido en "
                f"'{CACHE_PATH}'. Autoriza la app una vez con:\n"
                "  python run.py --login"
            )
        auth_manager.get_access_token(as_dict=False, check_cache=False)

    _client = spotipy.Spotify(auth_manager=auth_manager)


def get_spotify_client() -> spotipy.Spotify:
    """Devuelve el cliente creado por ensure_authenticated() al arrancar."""
    if _client is None:
        raise AuthError(
            "El cliente de Spotify no está inicializado. Arranca el daemon "
            "con 'python run.py' (o 'python run.py --login' la primera vez)."
        )
    return _client
