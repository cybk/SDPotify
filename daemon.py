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

Arrancar:
    uvicorn daemon:app --host 127.0.0.1 --port 5111
"""

import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from spotipy.exceptions import SpotifyException

from spotify_auth import get_spotify_client

load_dotenv()

DAEMON_TOKEN = os.getenv("DAEMON_TOKEN")

if not DAEMON_TOKEN:
    raise RuntimeError(
        "Falta DAEMON_TOKEN en el archivo .env. Genera uno con:\n"
        "  python -c \"import secrets; print(secrets.token_hex(16))\"\n"
        "y agrégalo a .env como DAEMON_TOKEN=<valor generado>"
    )

app = FastAPI(title="Spotify Stream Deck Daemon")


def verify_token(x_daemon_token: str = Header(default=None)) -> None:
    """Dependencia de FastAPI: valida el token compartido en cada request."""
    if x_daemon_token != DAEMON_TOKEN:
        raise HTTPException(status_code=403, detail="Token inválido o ausente.")


def _no_active_device_error() -> HTTPException:
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
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/pause", dependencies=[Depends(verify_token)])
def pause_action() -> dict:
    sp = get_spotify_client()
    try:
        sp.pause_playback()
        return {"status": "ok", "action": "pause"}
    except SpotifyException as e:
        if e.http_status == 404:
            raise _no_active_device_error()
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/next", dependencies=[Depends(verify_token)])
def next_action() -> dict:
    sp = get_spotify_client()
    try:
        sp.next_track()
        return {"status": "ok", "action": "next"}
    except SpotifyException as e:
        if e.http_status == 404:
            raise _no_active_device_error()
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/previous", dependencies=[Depends(verify_token)])
def previous_action() -> dict:
    sp = get_spotify_client()
    try:
        sp.previous_track()
        return {"status": "ok", "action": "previous"}
    except SpotifyException as e:
        if e.http_status == 404:
            raise _no_active_device_error()
        raise HTTPException(status_code=502, detail=str(e))


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
        raise HTTPException(status_code=502, detail=str(e))


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
