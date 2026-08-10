"""
Botón Stream Deck: Volumen a 40%. Ejemplo de cómo mandar un parámetro.

Duplica este archivo y cambia VOLUME_LEVEL para crear botones de "volumen
bajo", "volumen alto", etc.
"""

import sys

import requests

from _config import DAEMON_URL, HEADERS

VOLUME_LEVEL = 40

try:
    r = requests.post(
        f"{DAEMON_URL}/volume",
        headers=HEADERS,
        params={"level": VOLUME_LEVEL},
        timeout=3,
    )
    r.raise_for_status()
except requests.RequestException as e:
    print(f"Error llamando al daemon: {e}", file=sys.stderr)
    sys.exit(1)
