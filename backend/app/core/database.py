from collections.abc import AsyncIterator

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()


def _build_engine_url_and_args():
    """asyncpg doesn't understand libpq-style query params (sslmode, channel_binding)
    that Neon's connection string includes, so strip them and pass SSL via connect_args."""
    url = make_url(settings.database_url)
    query = dict(url.query)
    query.pop("sslmode", None)
    query.pop("channel_binding", None)
    return url.set(query=query), {"ssl": True}


_engine_url, _connect_args = _build_engine_url_and_args()
engine = create_async_engine(
    _engine_url, echo=settings.debug, pool_pre_ping=True, connect_args=_connect_args
)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session
