"""
Modelo de membresías (tabla `patient_members`).

Es la tabla de autorización central del sistema: TODO endpoint que opera
sobre un paciente valida el acceso consultando aquí si el usuario autenticado
tiene una fila para ese `patient_id`, y con qué rol (sección 2.2 y 2.7 de la
Especificación de Endpoints Backend v1: "la autorización por recurso se
valida contra la membresía del usuario en el paciente").

`UNIQUE(patient_id, user_id)`: una persona solo puede tener UN rol por
paciente (si en el futuro se necesitara que alguien tenga más de un rol
sobre el mismo paciente, se modelaría como una fila adicional con un
cambio de constraint, no reutilizando esta fila).
"""
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import RoleType
from app.models.mixins import TimestampMixin


class PatientMember(TimestampMixin, Base):
    __tablename__ = "patient_members"
    __table_args__ = (
        UniqueConstraint("patient_id", "user_id", name="uq_patient_members_patient_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Mismo cuidado que en Patient.sex: se fuerza `values_callable` para que
    # PostgreSQL almacene "family"/"caregiver"/"doctor"/"elder" (los valores
    # del contrato de API) y no "FAMILY"/"CAREGIVER"/"DOCTOR"/"ELDER" (los
    # nombres de los miembros de Python, que es el default de SQLAlchemy).
    role: Mapped[RoleType] = mapped_column(
        Enum(RoleType, name="role_type", native_enum=True, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )

    # El familiar administrador (quien crea el paciente) queda marcado como
    # owner: es el único que puede editar el perfil del paciente, invitar o
    # quitar miembros, y es a quien nunca se puede eliminar del círculo de
    # cuidado (endpoints 4.4, 4.5 y 4.8 de la especificación completa).
    is_owner: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    patient: Mapped["Patient"] = relationship(back_populates="members", lazy="joined")
    user: Mapped["User"] = relationship(back_populates="memberships")

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<PatientMember patient_id={self.patient_id} user_id={self.user_id} "
            f"role={self.role} is_owner={self.is_owner}>"
        )
