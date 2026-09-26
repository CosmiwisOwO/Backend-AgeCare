"""
Configuración de acceso a datos: engine async de SQLAlchemy 2 + asyncpg y
la dependencia `get_db` que FastAPI inyecta en cada endpoint.

Todos los modelos (app/models/*.py) heredan de `Base`, definida aquí, para
que Alembic pueda descubrirlos a través de `Base.metadata` en env.py.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

# echo=db_echo permite ver el SQL generado en desarrollo sin tocar código.
# pool_pre_ping evita errores por conexiones cortadas por el firewall/idle
# timeout de Azure Database for PostgreSQL Flexible Server.
engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,
    pool_pre_ping=True,
    future=True,
)

# expire_on_commit=False: permite seguir leyendo atributos del objeto ORM
# después de hacer commit (útil para armar la respuesta del endpoint sin
# un round-trip extra a la base de datos).
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=AsyncSession,
)


class Base(DeclarativeBase):
    """Clase base declarativa. Todos los modelos ORM heredan de aquí."""

    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependencia de FastAPI: entrega una sesión async por request y garantiza
    su cierre (y rollback ante excepción) al terminar.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
