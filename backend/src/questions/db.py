from logging import Logger

from shared import DB_PATH
from sqlalchemy import event as sa_event
from sqlmodel import Session, SQLModel, create_engine

from questions.types import (
    AssetDB,
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
    _ensure_question_lineage_columns(log)
    log.info("All tables created / verified")


def get_session() -> Session:
    """Create a new database session."""
    return Session(engine)


def _ensure_question_lineage_columns(log: Logger) -> None:
    if engine.url.get_backend_name() != "sqlite":
        return

    with engine.begin() as conn:
        columns = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(questions)").fetchall()
        }
        for column in ("remixed_from", "source_question_id", "source_paper_id"):
            if column in columns:
                continue
            log.info(f"Adding questions.{column} column")
            conn.exec_driver_sql(f"ALTER TABLE questions ADD COLUMN {column} VARCHAR")
