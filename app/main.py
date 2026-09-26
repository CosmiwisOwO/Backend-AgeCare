"""
Punto de entrada de la aplicación FastAPI.

Ejecutar en desarrollo local con:
    uvicorn app.main:app --reload --port 8000

Ver README.md para la guía completa de instalación (Postgres local, entorno
virtual, variables de entorno y migraciones).
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_v1_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.middleware import RequestIDMiddleware

logging.basicConfig(level=logging.INFO)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description=(
        "API REST de AgeCare — Suite de cuidado de adultos mayores. "
        "Hito 1 (MVP): fundaciones, autenticación y pacientes."
    ),
    version="0.1.0",
    # Se ocultan /docs y /redoc en producción por defecto (no conviene
    # exponer el esquema completo de la API públicamente); en desarrollo
    # quedan disponibles para probar los endpoints desde el navegador.
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
)

# El orden importa: el middleware agregado ÚLTIMO es el que se ejecuta
# PRIMERO sobre el request entrante. Se quiere que el request_id exista
# antes que cualquier otra cosa (incluido CORS), para poder correlacionar
# logs de cualquier error, incluidos los de CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIDMiddleware)

# Manejo estándar de errores (requerimiento 4 del MVP): cubre AppError,
# validación de Pydantic/FastAPI, HTTPException de Starlette y cualquier
# excepción no controlada, todas con el mismo formato { error: {...} }.
register_exception_handlers(app)

# Todas las rutas de negocio cuelgan de /api/v1 (sección 2.1 de la
# Especificación de Endpoints).
app.include_router(api_v1_router, prefix=settings.api_v1_prefix)


def _health_payload() -> dict:
    return {"status": "ok", "service": settings.app_name, "environment": settings.environment}


# Se expone el healthcheck en dos rutas:
#   * "/health"           -> convención estándar de infraestructura (probes
#                             de liveness/readiness de Azure Container Apps,
#                             ticket AGE-102 del Plan de Desarrollo).
#   * "/api/v1/health"     -> la ruta que efectivamente pediría el cliente
#                             Flutter, ya que `ApiClient` arma sus requests
#                             sobre `baseUrl = apiBaseUrl + apiVersion` y
#                             trata "/health" como ruta pública
#                             (ver lib/core/network/api_client.dart).
@app.get("/health", tags=["health"], summary="Healthcheck de infraestructura")
async def health_root() -> dict:
    return _health_payload()


@app.get(f"{settings.api_v1_prefix}/health", tags=["health"], summary="Healthcheck de la API v1")
async def health_v1() -> dict:
    return _health_payload()
