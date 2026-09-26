"""
Router del feature `auth`.

Corresponde a `lib/features/auth/` del frontend: por ahora solo implementa
el registro (sección 3.1 de la Especificación de Endpoints), que es lo que
necesita `register_screen.dart` para funcionar contra un backend real.

Login, refresh, logout y recuperación de contraseña (3.2 a 3.6) quedan
fuera de este primer hito y se agregan cuando se aborde ese ticket
(equivalente a AGE-104 del Plan de Desarrollo).
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import simple_rate_limit
from app.features.auth.schemas import RegisterRequest, RegisterResponse
from app.features.auth.service import register_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar cuenta de familiar",
    # Dependencia de rate limiting ilustrativa: máx. 5 intentos de registro
    # por IP cada 60 segundos (ver docstring de simple_rate_limit sobre por
    # qué esto es solo un punto de partida, no una solución de producción).
    dependencies=[Depends(simple_rate_limit(max_requests=5, window_seconds=60))],
)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    """
    Crea la cuenta del usuario. En este MVP el familiar es quien se registra
    directamente (sin invitación); cuidadora, médico y adulto mayor se
    incorporarán vía invitación en un hito posterior.
    """
    user, access_token, refresh_token = await register_user(db, payload)
    return RegisterResponse(
        user_id=user.id,
        email=user.email,
        role=None,  # ver docstring de RegisterResponse
        access_token=access_token,
        refresh_token=refresh_token,
    )
