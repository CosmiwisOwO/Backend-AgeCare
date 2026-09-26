"""
Lógica de negocio del feature `patients`.
"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import forbidden, not_found
from app.features.patients.schemas import PatientCreateRequest
from app.models.enums import RoleType
from app.models.patient import Patient
from app.models.patient_member import PatientMember
from app.models.user import User


async def create_patient(db: AsyncSession, data: PatientCreateRequest, owner: User) -> Patient:
    """
    Crea el perfil del adulto mayor y registra automáticamente a `owner`
    (quien hace la petición) como familiar administrador del paciente,
    exactamente como exige el endpoint 4.1: "Quien lo crea queda registrado
    automáticamente como familiar administrador (owner) del paciente".

    Ambas escrituras (patient + patient_member) se hacen en la misma
    transacción: o se crean las dos, o no se crea ninguna. Un paciente sin
    ningún miembro sería un recurso huérfano e inaccesible para siempre.
    """
    patient = Patient(
        full_name=data.full_name,
        birth_date=data.birth_date,
        sex=data.sex,
        photo_url=data.photo_url,
        conditions=data.conditions,
        notes=data.notes,
    )
    db.add(patient)
    await db.flush()  # asigna patient.id sin cerrar la transacción todavía

    membership = PatientMember(
        patient_id=patient.id,
        user_id=owner.id,
        role=RoleType.FAMILY,
        is_owner=True,
    )
    db.add(membership)

    await db.commit()
    await db.refresh(patient)
    return patient


async def get_patient_for_member(db: AsyncSession, patient_id: UUID, user: User) -> Patient:
    """
    Devuelve el paciente si `user` pertenece a su círculo de cuidado.

    * 404 NOT_FOUND si el paciente no existe en absoluto.
    * 403 FORBIDDEN si existe pero `user` no tiene membresía (no observa,
      no opera y no prescribe sobre él) -- misma semántica que el resto de
      los endpoints clínicos descritos en la sección 2.7 (matriz de
      permisos por rol).
    """
    patient = await db.scalar(select(Patient).where(Patient.id == patient_id))
    if patient is None:
        raise not_found()

    is_member = any(m.user_id == user.id for m in patient.members)
    if not is_member:
        raise forbidden()

    return patient
