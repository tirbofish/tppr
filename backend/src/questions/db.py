import os
from logging import Logger

from sqlmodel import Session, SQLModel, create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://")

engine = create_engine(DATABASE_URL, echo=True)

with engine.connect() as conn:
    result = conn.execute(text("SELECT version();"))
    for row in result:
        print(row)


def prepare(log: Logger) -> None:
    log.info(f"Connecting to database: {engine.url}")
    SQLModel.metadata.create_all(engine)
    log.info("All tables created / verified")


def get_session() -> Session:
    """Create a new database session."""
    return Session(engine)