"""
Lógica de autenticación con Spotify — misma estrategia que usamos en el
servidor MCP (spotify-mcp/server.py): Authorization Code flow vía spotipy,
con el token cacheado en disco para no tener que reautenticar cada vez.

Este módulo es intencionalmente el único lugar que toca el archivo de caché
del token, para evitar condiciones de carrera si varios requests llegan casi
al mismo tiempo (spotipy internamente serializa el refresh, pero mantener un
solo cliente vivo en memoria evita además abrir/leer el archivo en cada
request).
"""

import os

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

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
CACHE_PATH = os.getenv("SPOTIFY_CACHE_PATH", ".spotify_token_cache")

_client: spotipy.Spotify | None = None


def get_spotify_client() -> spotipy.Spotify:
    """Devuelve un cliente de Spotify autenticado, reutilizando la misma
    instancia entre requests (arranca el auth manager una sola vez)."""
    global _client

    if not CLIENT_ID or not CLIENT_SECRET:
        raise RuntimeError(
            "Faltan SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET. "
            "Revisa el archivo .env (ver .env.example)."
        )

    if _client is None:
        auth_manager = SpotifyOAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            scope=SCOPES,
            cache_path=CACHE_PATH,
            open_browser=True,
        )
        _client = spotipy.Spotify(auth_manager=auth_manager)

    return _client
