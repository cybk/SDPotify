"""
Punto de entrada para arrancar el daemon con el bind correcto y seguro.

Usa esto en vez de invocar uvicorn directamente a mano, para no arriesgarte
a olvidar el --host 127.0.0.1 y terminar exponiendo el daemon a tu red local.

    python run.py --login   # primera vez: abre el navegador para autorizar
    python run.py           # uso normal / tarea programada: nunca abre navegador
"""

import argparse
import copy
import logging
import logging.config
import sys
from pathlib import Path

import uvicorn
from uvicorn.config import LOGGING_CONFIG

from spotify_auth import AuthError, ensure_authenticated

LOG_PATH = Path(__file__).resolve().parent / "daemon.log"


def build_log_config() -> dict:
    """Config de logging de uvicorn + un archivo rotativo (daemon.log) donde
    también escribe el logger 'daemon'. Útil cuando el daemon corre desde el
    Programador de tareas y la consola no se ve."""
    config = copy.deepcopy(LOGGING_CONFIG)
    config["formatters"]["file"] = {
        "format": "%(asctime)s %(levelname)s %(name)s: %(message)s"
    }
    config["handlers"]["file"] = {
        "class": "logging.handlers.RotatingFileHandler",
        "formatter": "file",
        "filename": str(LOG_PATH),
        "maxBytes": 1_000_000,
        "backupCount": 3,
        "encoding": "utf-8",
    }
    # uvicorn.error propaga a 'uvicorn', así que basta con estos dos.
    for name in ("uvicorn", "uvicorn.access"):
        config["loggers"][name]["handlers"].append("file")
    config["loggers"]["daemon"] = {
        "handlers": ["default", "file"],
        "level": "INFO",
        "propagate": False,
    }
    return config


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Daemon Spotify para Stream Deck")
    parser.add_argument(
        "--login",
        action="store_true",
        help="si no hay token válido, abre el navegador para autorizar con Spotify",
    )
    args = parser.parse_args()

    log_config = build_log_config()
    logging.config.dictConfig(log_config)
    log = logging.getLogger("daemon")

    try:
        ensure_authenticated(login=args.login)
    except AuthError as e:
        log.error("Error de autenticación al arrancar: %s", e)
        sys.exit(1)

    uvicorn.run(
        "daemon:app",
        host="127.0.0.1",  # NUNCA cambiar a 0.0.0.0 -> expondría el daemon a la red local
        port=5111,
        log_config=log_config,
        log_level="info",
    )
