from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=False, pool_size=20, max_overflow=10)
engine_read = create_async_engine(settings.database_url_read, echo=False, pool_size=20, max_overflow=10)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
AsyncSessionLocalRead = async_sessionmaker(engine_read, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
            
async def get_read_db() -> AsyncSession:
    async with AsyncSessionLocalRead() as session:
        try:
            yield session
        finally:
            await session.close()
