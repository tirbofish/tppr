from logging import Logger

from shared import DB_PATH
from sqlalchemy import event as sa_event
from sqlmodel import Session, SQLModel, create_engine

from questions.types import (
    PaperDB,
    PaperOutcome,
    QuestionDB,
    QuestionOutcome,
    QuestionSyllabusPointDB,
)


def _enable_foreign_keys(dbapi_conn, connection_record):
    """Enable FK enforcement for every new SQLite connection."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
sa_event.listen(engine, "connect", _enable_foreign_keys)


def prepare(log: Logger) -> None:
    """Create all tables defined by SQLModel metadata."""
    log.info(f"Connecting to database at {DB_PATH}")
    SQLModel.metadata.create_all(engine)
    log.info("All tables created / verified")


def get_session() -> Session:
    """Create a new database session."""
    return Session(engine)
