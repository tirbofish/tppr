import os
from logging import Logger
from urllib.parse import quote_plus, urlencode

from sqlmodel import Session, SQLModel, create_engine
from settings import PRODUCTION, env_flag


def _configured_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        database_url = _database_url_from_parts()
    if not (
        database_url.startswith("postgresql://")
        or database_url.startswith("postgresql+psycopg2://")
    ):
        raise RuntimeError("DATABASE_URL must be a PostgreSQL connection URL")
    return database_url


def _database_url_from_parts() -> str:
    user = os.getenv("DB_USER", "").strip()
    password = os.getenv("DB_PASSWORD", "")
    host = os.getenv("DB_HOST", "").strip()
    port = os.getenv("DB_PORT", "5432").strip()
    name = os.getenv("DB_NAME", "").strip()

    missing = [
        key
        for key, value in {
            "DB_USER": user,
            "DB_PASSWORD": password,
            "DB_HOST": host,
            "DB_NAME": name,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(
            "Database not configured. Set DATABASE_URL or "
            f"{', '.join(missing)} in your .env"
        )

    auth = f"{quote_plus(user)}:{quote_plus(password)}"
    host_part = host if not port else f"{host}:{port}"
    query_options: dict[str, str] = {}

    sslmode = os.getenv("DB_SSLMODE", "").strip()
    if sslmode:
        query_options["sslmode"] = sslmode
    elif host.endswith(".supabase.com"):
        query_options["sslmode"] = "require"

    query = f"?{urlencode(query_options)}" if query_options else ""
    return f"postgresql+psycopg2://{auth}@{host_part}/{quote_plus(name)}{query}"


DATABASE_URL = _configured_database_url()
DATABASE_ECHO = False if PRODUCTION else env_flag("DATABASE_ECHO", False)

engine = create_engine(DATABASE_URL, echo=DATABASE_ECHO)

# Indexes that materially speed up the hot read paths (paper fetch, leaderboard,
# stats). Declared on the models too, but `create_all` won't add indexes to
# existing tables, so these idempotent statements ensure the remote DB gets them.
_INDEX_DDL = [
    "CREATE INDEX IF NOT EXISTS ix_papers_author_id ON papers (author_id)",
    "CREATE INDEX IF NOT EXISTS ix_papers_remixed ON papers (remixed)",
    "CREATE INDEX IF NOT EXISTS ix_questions_author_id ON questions (author_id)",
    "CREATE INDEX IF NOT EXISTS ix_question_syllabus_points_question_id "
    "ON question_syllabus_points (question_id)",
]


def prepare(log: Logger) -> None:
    log.info(
        "Connecting to database: "
        f"{engine.url.render_as_string(hide_password=True)}"
    )
    SQLModel.metadata.create_all(engine)
    with engine.begin() as conn:
        from sqlalchemy import text

        for statement in _INDEX_DDL:
            conn.execute(text(statement))
    log.info("All tables created / verified")


def get_session() -> Session:
    return Session(engine)
