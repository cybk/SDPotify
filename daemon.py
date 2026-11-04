"""
Daemon local para controlar Spotify desde botones del Stream Deck.

Corre un servidor HTTP en 127.0.0.1 (solo accesible desde tu misma máquina)
con endpoints simples que los scripts delgados de scripts/ pueden invocar.

Seguridad:
- Bind exclusivo a 127.0.0.1 (nunca 0.0.0.0) -> nada fuera de tu máquina
  puede conectarse, ni siquiera otros dispositivos en tu misma red WiFi.
- Requiere un token compartido en el header 'X-Daemon-Token' en cada request
  -> evita que una pestaña de navegador random (localhost drive-by) controle
  tu Spotify sin que te des cuenta.
- Sin CORS habilitado -> ninguna página web puede pegarle a este daemon
  desde JavaScript, con o sin token.

Arrancar (siempre con run.py, que autentica antes de levantar el servidor):
    python run.py --login   # primera vez
    python run.py
"""

import logging
import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyOauthError

from spotify_auth import AuthError, get_spotify_client

load_dotenv()

logger = logging.getLogger(__name__)  # 'daemon'; run.py lo envía a daemon.log

DAEMON_TOKEN = os.getenv("DAEMON_TOKEN")

if not DAEMON_TOKEN:
    raise RuntimeError(
        "Falta DAEMON_TOKEN en el archivo .env. Genera uno con:\n"
        "  python -c \"import secrets; print(secrets.token_hex(16))\"\n"
        "y agrégalo a .env como DAEMON_TOKEN=<valor generado>"
    )

app = FastAPI(title="Spotify Stream Deck Daemon")

_REAUTH_MESSAGE = (
    "El token de Spotify es inválido o fue revocado. Detén el daemon y "
    "ejecuta: python run.py --login"
)


@app.exception_handler(SpotifyOauthError)
@app.exception_handler(AuthError)
def auth_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Token revocado/inválido con el daemon ya en marcha: lo deja en el log
    con instrucciones y responde 401 en vez de un 500 genérico."""
    logger.error("%s %s -> %s | detalle: %s", request.method, request.url.path, _REAUTH_MESSAGE, exc)
    return JSONResponse(status_code=401, content={"detail": _REAUTH_MESSAGE})


def verify_token(x_daemon_token: str = Header(default=None)) -> None:
    """Dependencia de FastAPI: valida el token compartido en cada request."""
    if x_daemon_token != DAEMON_TOKEN:
        logger.warning("Request rechazado: X-Daemon-Token inválido o ausente.")
        raise HTTPException(status_code=403, detail="Token inválido o ausente.")


def _upstream_error(e: SpotifyException) -> HTTPException:
    logger.error("Error de la Web API de Spotify (HTTP %s): %s", e.http_status, e)
    return HTTPException(status_code=502, detail=str(e))


def _no_active_device_error() -> HTTPException:
    logger.warning("Spotify respondió 404: no hay ningún dispositivo activo.")
    return HTTPException(
        status_code=409,
        detail=(
            "No hay ningún dispositivo Spotify activo. Abre Spotify en algún "
            "dispositivo y dale play/pausa una vez."
        ),
    )


@app.get("/health")
def health() -> dict:
    """Endpoint sin autenticación, solo para confirmar que el daemon está
    corriendo (útil para depurar problemas de arranque)."""
    return {"status": "ok"}


@app.post("/play", dependencies=[Depends(verify_token)])
def play_action() -> dict:
    sp = get_spotify_client()
    try:
        sp.start_playback()
        return {"status": "ok", "action": "play"}
    except SpotifyException as e:
        if e.http_status == 404:
            raise _no_active_device_error()
        raise _upstream_error(e)


@app.post("/pause", dependencies=[Depends(verify_token)])
def pause_action() -> dict:
    sp = get_spotify_client()
    try:
        sp.pause_playback()
        return {"status": "ok", "action": "pause"}
    except SpotifyException as e:
        if e.http_status == 404:
            raise _no_active_device_error()
        raise _upstream_error(e)


@app.post("/next", dependencies=[Depends(verify_token)])
def next_action() -> dict:
    sp = get_spotify_client()
    try:
        sp.next_track()
        return {"status": "ok", "action": "next"}
    except SpotifyException as e:
        if e.http_status == 404:
            raise _no_active_device_error()
        raise _upstream_error(e)


@app.post("/previous", dependencies=[Depends(verify_token)])
def previous_action() -> dict:
    sp = get_spotify_client()
    try:
        sp.previous_track()
        return {"status": "ok", "action": "previous"}
    except SpotifyException as e:
        if e.http_status == 404:
            raise _no_active_device_error()
        raise _upstream_error(e)


@app.post("/volume", dependencies=[Depends(verify_token)])
def volume_action(level: int) -> dict:
    """Cambia el volumen. Uso: POST /volume?level=50"""
    if not 0 <= level <= 100:
        raise HTTPException(status_code=400, detail="level debe estar entre 0 y 100.")

    sp = get_spotify_client()
    try:
        sp.volume(level)
        return {"status": "ok", "action": "volume", "level": level}
    except SpotifyException as e:
        if e.http_status == 404:
            raise _no_active_device_error()
        raise _upstream_error(e)


@app.get("/now-playing", dependencies=[Depends(verify_token)])
def now_playing_action() -> dict:
    sp = get_spotify_client()
    playback = sp.current_playback()

    if not playback or not playback.get("item"):
        return {"status": "ok", "playing": False}

    item = playback["item"]
    return {
        "status": "ok",
        "playing": playback.get("is_playing", False),
        "track": item["name"],
        "artists": [a["name"] for a in item["artists"]],
        "progress_ms": playback.get("progress_ms", 0),
        "duration_ms": item.get("duration_ms", 0),
    }
