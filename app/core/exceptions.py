"""
Manejo estándar de errores de la API.

Todo error de la API — sin excepción — responde con el mismo cuerpo JSON,
listo para mostrarse en la app (sección 2.4 de la Especificación de
Endpoints Backend v1):

    {
      "error": {
        "code": "EMAIL_ALREADY_EXISTS",
        "message": "Ya existe una cuenta con este correo electrónico.",
        "details": null,
        "request_id": "a1b2c3d4-..."
      }
    }

Esto es exactamente lo que `ApiException.fromDio` espera del lado de Flutter
(lib/core/network/api_client.dart): lee `data['error']['code']` y
`data['error']['message']`.

Este módulo define:
  * `AppError`      -> excepción de negocio que los endpoints/servicios
                        lanzan explícitamente (ej. EMAIL_ALREADY_EXISTS).
  * `register_exception_handlers(app)` -> conecta AppError, los errores de
    validación de Pydantic/FastAPI, los HTTPException de Starlette y
    cualquier excepción no controlada a ese mismo formato, cubriendo
    401, 403, 404, 422, 429 y 500 tal como pide el requerimiento 4 del MVP.
"""
import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.middleware import get_request_id

logger = logging.getLogger("agecare.errors")


class AppError(Exception):
    """
    Excepción de negocio estándar de la API.

    Los servicios/routers la lanzan con un código HTTP, un código interno
    en MAYÚSCULAS (estable, pensado para lógica en el cliente) y un mensaje
    en español listo para mostrar al usuario final.

    Ejemplo:
        raise AppError(
            status_code=409,
            code="EMAIL_ALREADY_EXISTS",
            message="Ya existe una cuenta con este correo electrónico.",
        )
    """

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: list | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


# ---------------------------------------------------------------------------
# Errores comunes reutilizables (sección 2.5 de la Especificación de
# Endpoints): se exponen como funciones factory para lanzarlos con
# `raise unauthorized()` desde cualquier dependencia o endpoint.
# ---------------------------------------------------------------------------
def unauthorized(message: str = "Tu sesión expiró. Vuelve a iniciar sesión.") -> AppError:
    return AppError(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", message)


def forbidden(
    message: str = "No tienes permisos para realizar esta acción sobre este paciente.",
) -> AppError:
    return AppError(status.HTTP_403_FORBIDDEN, "FORBIDDEN", message)


def not_found(
    message: str = "El recurso solicitado no existe o no está disponible.",
) -> AppError:
    return AppError(status.HTTP_404_NOT_FOUND, "NOT_FOUND", message)


def rate_limited(
    message: str = "Demasiadas solicitudes. Intenta de nuevo en unos segundos.",
) -> AppError:
    return AppError(status.HTTP_429_TOO_MANY_REQUESTS, "RATE_LIMITED", message)


def _error_body(code: str, message: str, request_id: str, details: list | None = None) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": request_id,
        }
    }


def register_exception_handlers(app: FastAPI) -> None:
    """Registra todos los manejadores de excepción globales en la app FastAPI."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message, get_request_id(request), exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # exc.errors() trae la lista de errores de Pydantic v2. Se traduce a
        # un formato liviano {field, message} apto para resaltar campos en
        # el formulario de la app (ej. register_screen.dart).
        details = [
            {
                "field": ".".join(str(p) for p in err["loc"] if p != "body"),
                "message": err["msg"],
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body(
                "VALIDATION_ERROR",
                "Hay datos inválidos en la solicitud. Revisa los campos marcados.",
                get_request_id(request),
                details,
            ),
        )

    # Mensajes por defecto para HTTPException "crudas" (ej. 404 de ruta no
    # encontrada, o cualquier `raise HTTPException(401)` suelto que no pase
    # por AppError). Cubre exactamente los códigos pedidos en el MVP.
    _default_messages = {
        status.HTTP_401_UNAUTHORIZED: ("UNAUTHORIZED", "Tu sesión expiró. Vuelve a iniciar sesión."),
        status.HTTP_403_FORBIDDEN: (
            "FORBIDDEN",
            "No tienes permisos para realizar esta acción sobre este paciente.",
        ),
        status.HTTP_404_NOT_FOUND: (
            "NOT_FOUND",
            "El recurso solicitado no existe o no está disponible.",
        ),
        status.HTTP_429_TOO_MANY_REQUESTS: (
            "RATE_LIMITED",
            "Demasiadas solicitudes. Intenta de nuevo en unos segundos.",
        ),
    }

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code, default_message = _default_messages.get(
            exc.status_code, ("HTTP_ERROR", "Ocurrió un error al procesar la solicitud.")
        )
        # Si el endpoint pasó un `detail` explícito y legible, se respeta;
        # si no, se usa el mensaje en español por defecto de la tabla.
        message = exc.detail if isinstance(exc.detail, str) and exc.detail else default_message
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(code, message, get_request_id(request)),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = get_request_id(request)
        # Se loguea el stack trace completo del lado del servidor (con el
        # request_id como llave de correlación) pero NUNCA se expone el
        # detalle interno al cliente: solo el mensaje genérico de la sección
        # 2.5 de la especificación.
        logger.exception("Error no controlado [request_id=%s]", request_id)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body(
                "INTERNAL_ERROR",
                "Algo salió mal de nuestro lado. Intenta más tarde.",
                request_id,
            ),
        )
