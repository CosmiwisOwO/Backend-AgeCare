"""
Middleware de trazabilidad: asigna un `request_id` único a cada petición.

Se usa en dos lugares:
  1. Se agrega como header `X-Request-ID` en toda respuesta (facilita
     correlacionar logs del cliente Flutter con logs del backend).
  2. Los manejadores de excepciones (app/core/exceptions.py) lo incluyen en
     `error.request_id`, tal como exige el formato estándar de error
     (sección 2.4 de la Especificación de Endpoints Backend v1).
"""
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        # Se guarda en request.state para que cualquier handler/endpoint
        # pueda leerlo sin volver a generarlo.
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


def get_request_id(request: Request) -> str:
    """Devuelve el request_id de la petición actual, generando uno si faltara
    (por ejemplo, si la excepción ocurre antes de que el middleware corra)."""
    return getattr(request.state, "request_id", None) or str(uuid.uuid4())
