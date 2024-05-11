import databases
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool.impl import AsyncAdaptedQueuePool
from config import settings


# database = databases.Database(settings.postgres_conn_string)

Base = declarative_base()

engine = create_async_engine(
    settings.postgres_conn_string,
    pool_size=250,
    echo=False,
    pool_pre_ping=True,
    poolclass=AsyncAdaptedQueuePool,
    pool_recycle=7200,
    isolation_level="READ COMMITTED"
)

SessionFactory = sessionmaker(autocommit=False,
                              autoflush=False,
                              bind=engine,
                              expire_on_commit=False,
                              class_=AsyncSession)
