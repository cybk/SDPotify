"""
Configuración compartida por todos los scripts delgados de scripts/.

El token se lee de la variable de entorno DAEMON_TOKEN (debe ser el mismo
valor que configuraste en el .env del daemon). Configúralo como variable de
entorno del sistema, o edita DAEMON_TOKEN_FALLBACK aquí abajo si prefieres
no depender de variables de entorno del sistema al ejecutarse desde el
Stream Deck.
"""

import os
import sys

DAEMON_URL = "http://127.0.0.1:5111"

# Opción rápida: si no quieres configurar una variable de entorno de sistema,
# pega aquí el mismo token que pusiste en el .env del daemon.
DAEMON_TOKEN_FALLBACK = ""

DAEMON_TOKEN = os.getenv("DAEMON_TOKEN", DAEMON_TOKEN_FALLBACK)

if not DAEMON_TOKEN:
    print(
        "Falta configurar DAEMON_TOKEN (variable de entorno o "
        "DAEMON_TOKEN_FALLBACK en scripts/_config.py)",
        file=sys.stderr,
    )
    sys.exit(1)

HEADERS = {"X-Daemon-Token": DAEMON_TOKEN}
