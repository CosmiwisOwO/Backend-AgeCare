"""
Modelo de usuarios (tabla `users`).

Cubre a los cuatro roles de la plataforma (familiar, cuidadora, médico,
adulto mayor): el rol específico de cada usuario no vive en esta tabla sino
en `patient_members`, porque una misma persona puede tener distinto rol
según el paciente (ej. es familiar de su madre y, en teoría, podría ser
invitada como algo distinto en otro círculo de cuidado). Ver Anexo A de la
Especificación de Endpoints Backend v1.
"""
import uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    # UUID generado en Python (uuid4) en vez de server_default=gen_random_uuid():
    # así no se depende de tener la extensión `pgcrypto` habilitada en la
    # instancia de Azure Database for PostgreSQL, lo que simplifica el
    # primer despliegue. Es funcionalmente equivalente para el resto del
    # sistema (el cliente nunca genera IDs, siempre los recibe del backend).
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    full_name: Mapped[str] = mapped_column(String(120), nullable=False)

    # Correo único: es el identificador de acceso (login). El índice único
    # también actúa como constraint de integridad a nivel de base de datos,
    # no solo de aplicación (evita condiciones de carrera en registros
    # concurrentes con el mismo correo).
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # Hash Argon2 de la contraseña (ver app/core/security.py). Nunca se
    # almacena ni se loguea la contraseña en texto plano.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    # Idioma preferido (es | en). Por defecto español, acorde al público
    # objetivo de la plataforma.
    locale: Mapped[str] = mapped_column(String(8), nullable=False, default="es", server_default="es")

    # Relación inversa hacia las membresías del usuario (un usuario puede
    # pertenecer al círculo de cuidado de varios pacientes: soporte
    # multi-paciente). `lazy="selectin"` evita el problema N+1 al listar
    # pacientes de un usuario sin tener que acordarse de hacer joinedload
    # en cada consulta.
    memberships: Mapped[list["PatientMember"]] = relationship(
        back_populates="user", lazy="selectin"
    )

    def __repr__(self) -> str:  # pragma: no cover - solo utilidad de debug
        return f"<User id={self.id} email={self.email!r}>"


# Nota sobre el forward-reference "PatientMember": no se importa aquí para
# evitar un import circular (patient_member.py importa User). SQLAlchemy
# resuelve el string contra su registro de clases mapeadas la primera vez
# que se usa el mapper, siempre que ambos módulos hayan sido importados
# antes de ese punto — lo que app/models/__init__.py garantiza.
