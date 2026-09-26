"""Mixins reutilizables para los modelos ORM."""
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """
    Agrega `created_at` / `updated_at` con zona horaria (timestamptz), tal
    como especifica el Anexo A de la Especificación de Endpoints Backend v1
    ("todas usan columnas created_at / updated_at con timestamptz").

    `server_default=func.now()` deja que sea PostgreSQL quien fije el valor
    al insertar (consistente aunque se inserte por fuera de esta app), y
    `onupdate=func.now()` actualiza `updated_at` en cada UPDATE emitido por
    SQLAlchemy.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
