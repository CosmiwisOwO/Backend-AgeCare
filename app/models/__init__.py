"""
Importa todos los modelos ORM en un solo lugar.

Esto cumple dos propósitos:
  1. Registra las tres clases mapeadas contra `Base.metadata` para que
     `alembic/env.py` (que importa `app.models`) vea el esquema completo al
     autogenerar migraciones.
  2. Resuelve los forward-references en string (ej. `Mapped["PatientMember"]`
     dentro de user.py) que usan las relaciones bidireccionales, ya que
     SQLAlchemy solo puede resolverlos si ambas clases fueron importadas
     antes de que se configuren los mappers.

Cualquier modelo nuevo (vitals, medications, alerts, etc. en próximos
sprints) debe agregar aquí su import.
"""
from app.models.patient import Patient  # noqa: F401
from app.models.patient_member import PatientMember  # noqa: F401
from app.models.user import User  # noqa: F401

__all__ = ["User", "Patient", "PatientMember"]
