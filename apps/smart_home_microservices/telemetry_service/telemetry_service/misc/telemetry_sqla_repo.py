from sqlalchemy import create_engine


DATABASE_URL_SYNC = "postgresql://postgres:postgres@localhost:5433/telemetry"
DATABASE_URL_ASSYNC = "postgresql|asyncpg://postgres:postgres@localhost:5433/telemetry"


from telemetry_service.orm_classes import FloatTelemetrySampleORM, JsonTelemetrySampleORM, Base


sync_engine = create_engine(DATABASE_URL_SYNC, echo=True)


if __name__ == "__main__":
    Base.metadata.create_all(sync_engine)
