"""
Utilidades de seguridad.

- Hash de contraseñas con Argon2 (ganador del Password Hashing Competition;
  es la opción recomendada en la Documentación de Seguridad junto a bcrypt).
- Emisión y validación de JSON Web Tokens firmados con HS256, siguiendo la
  sección 2.2 de la Especificación de Endpoints Backend v1:
    * access_token  -> vigencia 30 min, incluye user_id.
    * refresh_token -> vigencia 30 días.

Nota de alcance (MVP): en la especificación completa el refresh_token es
rotatorio y se persiste en la tabla `refresh_tokens` para poder revocarlo
del lado del servidor (POST /auth/refresh, POST /auth/logout). Esa tabla
no forma parte de este primer hito (que pidió explícitamente solo Usuarios,
Pacientes y Membresías), así que aquí el refresh_token es un JWT autocontenido
sin persistencia ni revocación todavía. Queda documentado como pendiente en
el README para el próximo sprint (AGE-104 del Plan de Desarrollo).
"""
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from uuid import UUID

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# schemes=["argon2"]: un solo esquema activo. deprecated="auto" permite migrar
# de esquema en el futuro (ej. si se decidiera sumar bcrypt) sin romper hashes
# ya emitidos.
_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


def hash_password(plain_password: str) -> str:
    """Genera el hash Argon2 de una contraseña en texto plano."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verifica una contraseña en texto plano contra su hash almacenado."""
    return _pwd_context.verify(plain_password, password_hash)


def _create_token(user_id: UUID, token_type: TokenType, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": token_type.value,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: UUID) -> str:
    return _create_token(
        user_id, TokenType.ACCESS, timedelta(minutes=settings.access_token_expire_minutes)
    )


def create_refresh_token(user_id: UUID) -> str:
    return _create_token(
        user_id, TokenType.REFRESH, timedelta(days=settings.refresh_token_expire_days)
    )


class TokenPayloadError(Exception):
    """El token es inválido, expiró o no corresponde al tipo esperado."""


def decode_token(token: str, expected_type: TokenType) -> UUID:
    """
    Decodifica y valida un JWT. Devuelve el user_id (UUID) contenido en `sub`.
    Lanza TokenPayloadError ante cualquier problema (firma, expiración, tipo).
    El llamador (dependencia de FastAPI) traduce esto al error HTTP 401
    estándar de la API.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise TokenPayloadError(str(exc)) from exc

    if payload.get("type") != expected_type.value:
        raise TokenPayloadError("Tipo de token inesperado")

    try:
        return UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise TokenPayloadError("Payload de token inválido") from exc
