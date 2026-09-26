"""
Entorno de ejecución de Alembic.

Dos decisiones clave respecto al `env.py` que genera `alembic init` por
defecto:

1. La URL de conexión se toma de `app.core.config.get_settings()` (es decir,
   de la variable de entorno DATABASE_URL / archivo .env), NO de
   `alembic.ini`. Así el mismo archivo versionado sirve para cualquier
   entorno sin tocar código ni exponer credenciales.

2. Como el proyecto usa el driver async `asyncpg` (SQLAlchemy 2 async),
   las migraciones también corren en modo async: se crea un
   `AsyncEngine` y se delega el trabajo síncrono real de Alembic a
   `connection.run_sync(...)`, que es el patrón oficial recomendado por
   SQLAlchemy/Alembic para este caso.
"""
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# --- Import de la app -------------------------------------------------
# Se importa la configuración y TODOS los modelos (a través de app.models,
# que ya centraliza sus propios imports) para que `Base.metadata` quede
# completo antes de que Alembic compare el esquema contra la base de datos.
from app.core.config import get_settings
from app.core.database import Base
import app.models  # noqa: F401  (registra User, Patient, PatientMember)

# Objeto de configuración de Alembic (lee alembic.ini).
config = context.config

# Configura logging según alembic.ini (si el archivo está presente).
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata objetivo para el autogenerate: aquí es donde Alembic descubre
# qué tablas/columnas deberían existir, para compararlas con la base real.
target_metadata = Base.metadata

# Inyecta la URL real (desde variables de entorno) en la configuración de
# Alembic, sobrescribiendo el `sqlalchemy.url` vacío de alembic.ini.
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    """
    Modo 'offline': genera el SQL de la migración sin abrir una conexión
    real (útil para revisar el DDL antes de aplicarlo, o para pipelines que
    aplican el .sql generado por separado).
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Configura el contexto de Alembic sobre una conexión ya abierta y
    ejecuta las migraciones. Se llama vía `connection.run_sync(...)` porque
    la API de Alembic en sí es síncrona."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Modo 'online' (el que se usa en el día a día): abre un AsyncEngine real
    contra PostgreSQL y aplica las migraciones.

    `poolclass=pool.NullPool`: Alembic abre una única conexión de corta vida
    para migrar; no tiene sentido mantener un pool de conexiones para eso.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
