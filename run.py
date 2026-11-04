"""
Punto de entrada para arrancar el daemon con el bind correcto y seguro.

Usa esto en vez de invocar uvicorn directamente a mano, para no arriesgarte
a olvidar el --host 127.0.0.1 y terminar exponiendo el daemon a tu red local.

    python run.py --login   # primera vez: abre el navegador para autorizar
    python run.py           # uso normal / tarea programada: nunca abre navegador
"""

import argparse
import sys

import uvicorn

from spotify_auth import AuthError, ensure_authenticated

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Daemon Spotify para Stream Deck")
    parser.add_argument(
        "--login",
        action="store_true",
        help="si no hay token válido, abre el navegador para autorizar con Spotify",
    )
    args = parser.parse_args()

    try:
        ensure_authenticated(login=args.login)
    except AuthError as e:
        print(f"Error de autenticación: {e}", file=sys.stderr)
        sys.exit(1)

    uvicorn.run(
        "daemon:app",
        host="127.0.0.1",  # NUNCA cambiar a 0.0.0.0 -> expondría el daemon a la red local
        port=5111,
        log_level="info",
    )
