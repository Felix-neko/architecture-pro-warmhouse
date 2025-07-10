import asyncio
from datetime import datetime, timezone
from typing import List, Any, Optional

from sqlalchemy import (
    DDL,
    event,
)
from sqlalchemy import create_engine

# from sqlalchemy.ext.asyncio import (
#     AsyncEngine,
#     AsyncSession,
#     create_async_engine,
# )
from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
)

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5433/telemetry"
# 1. Define your ORM model
Base = declarative_base()

from telemetry_service.orm_classes import FloatTelemetrySampleORM, JsonTelemetrySampleORM


# 2. Register DDL for TimescaleDB
# 2a. Create extension before any tables exist
event.listen(Base.metadata, "before_create", DDL("CREATE EXTENSION IF NOT EXISTS timescaledb;"))

# 2b. After this specific table is created, turn it into a hypertable
event.listen(
    FloatTelemetrySampleORM.__table__,
    "after_create",
    DDL(f"SELECT create_hypertable('{FloatTelemetrySampleORM.__tablename__}', 'timestamp', if_not_exists => TRUE);"),
)
sync_engine = create_engine(DATABASE_URL, echo=True)
# engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=True)
#
#
# async def init_models():
#     """Runs Base.metadata.create_all(), including our DDL listeners."""
#     async with engine.begin() as conn:
#         # run_sync will invoke the listeners around create_all()
#         await conn.run_sync(Base.metadata.create_all)
#
#
# async def insert_samples(samples: List[FloatTelemetrySampleORM]):
#     AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
#     async with AsyncSessionLocal() as session:
#         session.add_all(samples)
#         await session.commit()


# async def main():
#     pass
# AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
#
# # 1️⃣ Initialize DB (create extension, table, hypertable)
# await init_models()
#
# # 2️⃣ Prepare and insert some data
# now = datetime.now().astimezone()
# samples = [
#     FloatTelemetrySampleORM(timestamp=now, sensor_id=1, value=1.23),
#     FloatTelemetrySampleORM(timestamp=now, sensor_id=2, value=4.56),
# ]
# await insert_samples(samples)
#
# # 3️⃣ Query back
# async with AsyncSessionLocal() as session:
#     result = await session.query(FloatTelemetrySampleORM)
#     for row in result.fetchall():
#         print(row)


if __name__ == "__main__":
    Base.metadata.create_all(sync_engine)
    # asyncio.run(main())
