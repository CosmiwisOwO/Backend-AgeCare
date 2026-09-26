"""
Limitador de tasa (rate limiting) mínimo, en memoria, por IP.

Objetivo de este MVP: demostrar que el error 429 responde con el formato
estándar (requerimiento 4), aplicado a un endpoint público sensible a abuso
(`POST /auth/register`).

*** Importante — NO usar tal cual en producción ***
Esta implementación guarda contadores en un diccionario del proceso, por lo
que:
  * No sirve con más de una instancia/réplica del backend (cada una tendría
    su propio contador).
  * Se reinicia si el proceso se reinicia.
Para producción, la Especificación de Endpoints (2.5, error RATE_LIMITED)
asume un limitador real: Azure API Management, o `slowapi`/`fastapi-limiter`
respaldado por Redis, compartido entre instancias.
"""
import time
from collections import defaultdict

from fastapi import Request

from app.core.exceptions import rate_limited

# ip -> lista de timestamps (epoch, segundos) de peticiones recientes.
_hits: dict[str, list[float]] = defaultdict(list)


def simple_rate_limit(max_requests: int = 5, window_seconds: int = 60):
    """
    Devuelve una dependencia de FastAPI que permite como máximo
    `max_requests` peticiones cada `window_seconds` por IP de origen.
    """

    async def _dependency(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window_start = now - window_seconds

        # Descarta timestamps fuera de la ventana deslizante.
        recent = [t for t in _hits[client_ip] if t > window_start]
        if len(recent) >= max_requests:
            raise rate_limited()

        recent.append(now)
        _hits[client_ip] = recent

    return _dependency
