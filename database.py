import databases
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from config import settings


# database = databases.Database(settings.postgres_conn_string)

Base = declarative_base()

engine = create_async_engine(
    settings.postgres_conn_string,
    pool_size=100,
    echo=False
)

SessionFactory = sessionmaker(autocommit=False,
                              autoflush=False,
                              bind=engine,
                              expire_on_commit=False,
                              class_=AsyncSession)
