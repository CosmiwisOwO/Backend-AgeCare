"""
Schemas de entrada/salida del feature `patients`.

Los campos replican `NewPatient.toJson()` y `Patient.fromJson()` de
`lib/features/patients/domain/models.dart`, y las secciones 4.1 y 4.3 de la
Especificación de Endpoints Backend v1.
"""
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import SexType


class PatientCreateRequest(BaseModel):
    """Body de POST /api/v1/patients."""

    full_name: str = Field(min_length=2, max_length=120)
    birth_date: date
    sex: SexType | None = None
    photo_url: str | None = Field(default=None, max_length=2048)
    conditions: list[str] = Field(default_factory=list)
    notes: str | None = None


class PatientCreateResponse(BaseModel):
    """Respuesta 201 de POST /api/v1/patients."""

    patient_id: UUID
    full_name: str
    created_at: datetime


class WearableStatusOut(BaseModel):
    """
    Sub-objeto `wearable` dentro del detalle de paciente.

    Se deja definido desde ya porque `Patient.fromJson` en el frontend ya lo
    espera (aunque sea `null`), pero el modelo `wearables` en sí es parte del
    módulo de Vitals (Sprint 3), fuera del alcance de este hito.
    """

    wearable_id: UUID | None = None
    last_sync_at: datetime | None = None
    battery_pct: int | None = None
    is_stale: bool = False


class PatientDetailResponse(BaseModel):
    """
    Respuesta de GET /api/v1/patients/{patient_id}.

    Nota de alcance: este endpoint no fue pedido explícitamente en la lista
    de requerimientos del MVP, pero `create_patient_screen.dart` lo invoca
    inmediatamente después de crear el paciente
    (`PatientsRepositoryHttp.createPatient` hace `POST /patients` seguido de
    `GET /patients/{id}`). Se incluye para que esa pantalla funcione de punta
    a punta, protegido por la misma verificación de membresía que usarán el
    resto de los endpoints clínicos.
    """

    patient_id: UUID
    full_name: str
    birth_date: date
    sex: SexType | None
    photo_url: str | None
    conditions: list[str]
    notes: str | None
    wearable: WearableStatusOut | None = None
