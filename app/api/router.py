"""
Router raíz de la API v1.

Cuelga cada feature (auth, patients, ...) bajo el mismo prefijo, tal como
describe la sección 2.1 de la Especificación de Endpoints Backend v1:
todas las rutas REST viven bajo /api/v1. A medida que se implementen nuevos
módulos (health/vitals, medications, alerts, ...) su router se agrega aquí,
uno por línea, manteniendo la correspondencia 1:1 con `lib/features/` del
frontend.
"""
from fastapi import APIRouter

from app.features.auth.router import router as auth_router
from app.features.patients.router import router as patients_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router)
api_v1_router.include_router(patients_router)
