from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from bot.config import settings

engine = create_async_engine(
    settings.DATABASE_URL_asyncpg,
    pool_recycle=3600,
)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
