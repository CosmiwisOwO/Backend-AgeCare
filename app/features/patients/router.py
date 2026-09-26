"""
Router del feature `patients`.

Corresponde a `lib/features/patients/` del frontend. Implementa lo que pide
este primer hito (crear paciente) más un extra necesario para que la
pantalla `create_patient_screen.dart` complete su flujo real:

    PatientsRepositoryHttp.createPatient()
        -> POST /patients                  (pedido explícitamente)
        -> GET  /patients/{patient_id}      (la pantalla lo llama enseguida
                                              para refrescar el objeto Patient
                                              completo; sin él, crear un
                                              paciente desde la app fallaría
                                              justo después de un 201 exitoso)

El resto de endpoints de pacientes (listar, actualizar, invitaciones,
wearable) pertenece al Sprint 2 completo (AGE-201 a AGE-211 del Plan de
Desarrollo) y queda fuera de este hito.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.features.patients.schemas import (
    PatientCreateRequest,
    PatientCreateResponse,
    PatientDetailResponse,
)
from app.features.patients.service import create_patient, get_patient_for_member
from app.models.user import User

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post(
    "",
    response_model=PatientCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear el perfil del adulto mayor",
)
async def create_patient_endpoint(
    payload: PatientCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PatientCreateResponse:
    """
    Crea el paciente y registra a `current_user` como familiar administrador
    (owner) en `patient_members`. Requiere estar autenticado (cualquier
    usuario registrado puede crear un paciente y así iniciar un círculo de
    cuidado nuevo).
    """
    patient = await create_patient(db, payload, owner=current_user)
    return PatientCreateResponse(
        patient_id=patient.id,
        full_name=patient.full_name,
        created_at=patient.created_at,
    )


@router.get(
    "/{patient_id}",
    response_model=PatientDetailResponse,
    summary="Detalle de paciente",
)
async def get_patient_endpoint(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PatientDetailResponse:
    """
    Devuelve el perfil completo del paciente si `current_user` pertenece a
    su círculo de cuidado (ver get_patient_for_member). `wearable` viaja en
    `null`: la vinculación de dispositivos es del módulo de Vitals
    (Sprint 3), no de este hito.
    """
    patient = await get_patient_for_member(db, patient_id, current_user)
    return PatientDetailResponse(
        patient_id=patient.id,
        full_name=patient.full_name,
        birth_date=patient.birth_date,
        sex=patient.sex,
        photo_url=patient.photo_url,
        conditions=patient.conditions,
        notes=patient.notes,
        wearable=None,
    )
