"""
Dependencias compartidas entre routers.

`get_current_user` es la dependencia que reemplaza, para endpoints
autenticados, al `Authorization: Bearer <access_token>` que exige la sección
2.2 de la Especificación de Endpoints Backend v1. Es la que usa
`POST /api/v1/patients` para saber quién está creando el paciente y
registrarlo como owner en `patient_members`.
"""
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import unauthorized
from app.core.security import TokenPayloadError, TokenType, decode_token
from app.models.user import User

# auto_error=False: si falta el header devolvemos NUESTRO formato de error
# (unauthorized()) en vez de que Starlette/FastAPI arme uno propio distinto
# al estándar de la sección 2.4.
_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Resuelve el usuario autenticado a partir del access_token.

    Lanza `AppError` 401 UNAUTHORIZED (formato estándar) si el header falta,
    el token es inválido/expiró, o el usuario ya no existe.
    """
    if credentials is None or not credentials.credentials:
        raise unauthorized("Debes iniciar sesión para realizar esta acción.")

    try:
        user_id: UUID = decode_token(credentials.credentials, expected_type=TokenType.ACCESS)
    except TokenPayloadError:
        raise unauthorized() from None

    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise unauthorized() from None

    return user
