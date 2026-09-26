"""
Enumeraciones de dominio compartidas entre modelos.

Los valores (`.value`) son exactamente los strings que define la sección 2.6
("Enumeraciones globales") de la Especificación de Endpoints Backend v1, y
por lo tanto los mismos que ya consume el frontend Flutter en
`lib/features/auth/domain/models.dart` (`RoleType.apiValue`). No cambiar
estos valores sin coordinar con el frontend: viajan tal cual en el JSON.
"""
from enum import StrEnum


class RoleType(StrEnum):
    """Rol de un usuario respecto a un paciente (patient_members.role)."""

    FAMILY = "family"
    CAREGIVER = "caregiver"
    DOCTOR = "doctor"
    ELDER = "elder"


class SexType(StrEnum):
    """Sexo del paciente (patients.sex). Opcional en el modelo."""

    FEMALE = "female"
    MALE = "male"
    OTHER = "other"
