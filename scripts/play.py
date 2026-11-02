"""Botón Stream Deck: Play. Apunta la acción 'System: Open' a este script."""

import sys

import requests

from _config import DAEMON_URL, HEADERS

try:
    r = requests.post(f"{DAEMON_URL}/play", headers=HEADERS, timeout=3)
    r.raise_for_status()
except requests.RequestException as e:
    print(f"Error llamando al daemon: {e}", file=sys.stderr)
    sys.exit(1)
