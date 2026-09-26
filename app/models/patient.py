"""
Modelo del perfil del adulto mayor (tabla `patients`).

Todos los recursos clínicos futuros (vitals, medicamentos, alertas, bitácora,
etc. — fuera de alcance de este primer hito) cuelgan de `patient_id` y su
autorización se resuelve siempre contra `patient_members` (ver
patient_member.py), nunca contra el dueño de la sesión directamente.
"""
import uuid
from datetime import date

from sqlalchemy import Date, Enum, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import SexType
from app.models.mixins import TimestampMixin


class Patient(TimestampMixin, Base):
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Enum nativo de PostgreSQL. `name=` fija el nombre del tipo en la base
    # de datos (necesario para que Alembic lo gestione de forma predecible
    # en las migraciones). Es opcional porque el endpoint 4.1 de la
    # especificación lo marca como no obligatorio.
    # `values_callable`: por defecto SQLAlchemy usa el NOMBRE del miembro del
    # enum de Python (ej. "FEMALE") para el tipo nativo de PostgreSQL, no su
    # `.value` ("female"). Como la API (y el frontend) hablan en minúsculas
    # según la sección 2.6 de la especificación, se fuerza explícitamente a
    # persistir `.value` -- si no, la base de datos terminaría guardando
    # "FEMALE"/"MALE"/"OTHER", inconsistente con lo que viaja por HTTP y con
    # lo que vería cualquiera que consulte la tabla directamente (ej. la web
    # de administración).
    sex: Mapped[SexType | None] = mapped_column(
        Enum(SexType, name="sex_type", native_enum=True, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=True,
    )

    photo_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    # `conditions` (padecimientos) es una lista corta de strings libres
    # (ej. ["Hipertensión", "Artrosis"]). Se modela como ARRAY(String) de
    # Postgres -- más simple de consultar/mostrar que JSONB para una lista
    # plana de texto, y es el tipo nativo pensado para esto.
    conditions: Mapped[list[str]] = mapped_column(
        ARRAY(String(120)), nullable=False, default=list, server_default="{}"
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Zona horaria del paciente (IANA, ej. "America/Santiago"). No la pidió
    # explícitamente el enunciado de este hito, pero SÍ es parte del modelo
    # de datos de la Especificación de Endpoints (Anexo A, tabla `patients`)
    # y la usan, más adelante, los horarios de medicamentos y el semáforo de
    # bienestar. Se incluye ahora con un valor por defecto sensato para no
    # tener que hacer una migración adicional cuando llegue el módulo de
    # medicamentos.
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="America/Santiago", server_default="America/Santiago"
    )

    # Metadata opcional para futuras integraciones (OCR, wearable, etc.);
    # se deja libre como JSONB por si se necesita en sprints posteriores sin
    # otra migración. No se expone todavía en ningún schema de entrada/salida.
    extra: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    members: Mapped[list["PatientMember"]] = relationship(
        back_populates="patient", lazy="selectin", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Patient id={self.id} full_name={self.full_name!r}>"
