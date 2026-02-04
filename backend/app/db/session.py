"""Database session management."""
import sqlalchemy
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy import create_engine
from app.core.config import get_settings
from typing import AsyncGenerator

settings = get_settings()

# SQLite connect args with WAL mode for better concurrency
sqlite_connect_args = {"check_same_thread": False}
pool_kwargs = {}
if "sqlite" in settings.database_url:
    # Enable WAL mode for better concurrency
    sqlite_connect_args.update({
        "timeout": 30,  # 30 second timeout for locked database
    })
else:
    # Pool settings only for non-SQLite databases
    pool_kwargs = {
        "pool_size": 5,
        "max_overflow": 10,
    }

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args=sqlite_connect_args if "sqlite" in settings.database_url else {},
    **pool_kwargs,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=True,  # Expire objects after commit to prevent stale data
)


# ============================================================================
# Sync Session Factory for Celery Workers
# ============================================================================
# Celery workers cannot use async database drivers (asyncpg/aiosqlite) due to
# event loop conflicts. This sync session factory uses psycopg2 for PostgreSQL
# or standard sqlite3 for SQLite, allowing Celery tasks to run without asyncio
# event loop issues.

# Get sync database URL (convert async URL to sync if needed)
sync_database_url = settings.get_sync_database_url()

# Pool settings for sync engine
sync_pool_kwargs = {}
if "sqlite" in sync_database_url:
    # SQLite settings
    sync_connect_args = {"check_same_thread": False}
else:
    # PostgreSQL/other pool settings
    sync_connect_args = {}
    sync_pool_kwargs = {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_pre_ping": True,  # Verify connections before using
    }

# Create sync engine for Celery workers
sync_engine = create_engine(
    sync_database_url,
    echo=settings.debug,
    connect_args=sync_connect_args,
    **sync_pool_kwargs,
)

# Create sync session factory
SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # Keep objects alive after commit for Celery workers
)


class Base(DeclarativeBase):
    """Base ORM model."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Database session dependency."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        # Enable WAL mode for better concurrency on SQLite
        if "sqlite" in str(engine.url):
            await conn.execute(sqlalchemy.text("PRAGMA journal_mode=WAL"))
            await conn.execute(sqlalchemy.text("PRAGMA synchronous=NORMAL"))
            await conn.execute(sqlalchemy.text("PRAGMA cache_size=-64000"))  # 64MB cache
            await conn.execute(sqlalchemy.text("PRAGMA temp_store=memory"))
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connection."""
    await engine.dispose()
