"""
Punto de entrada para arrancar el daemon con el bind correcto y seguro.

Usa esto en vez de invocar uvicorn directamente a mano, para no arriesgarte
a olvidar el --host 127.0.0.1 y terminar exponiendo el daemon a tu red local.
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "daemon:app",
        host="127.0.0.1",  # NUNCA cambiar a 0.0.0.0 -> expondría el daemon a la red local
        port=5111,
        log_level="info",
    )
