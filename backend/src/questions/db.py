import os
from logging import Logger

from sqlmodel import Session, SQLModel, create_engine, text
from settings import DATABASE_PATH, PRODUCTION, env_flag

DATABASE_URL = os.getenv("DATABASE_URL")
if PRODUCTION and not DATABASE_URL:
    raise RuntimeError("DATABASE_URL must be set when PRODUCTION=1")

DATABASE_URL = DATABASE_URL or f"sqlite:///{DATABASE_PATH}"
DATABASE_ECHO = False if PRODUCTION else env_flag("DATABASE_ECHO", False)

engine = create_engine(DATABASE_URL, echo=DATABASE_ECHO)

if env_flag("DATABASE_PRINT_VERSION", False) and not PRODUCTION:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();"))
        for row in result:
            print(row)


def prepare(log: Logger) -> None:
    log.info(
        "Connecting to database: "
        f"{engine.url.render_as_string(hide_password=True)}"
    )
    SQLModel.metadata.create_all(engine)
    log.info("All tables created / verified")


def get_session() -> Session:
    """Create a new database session."""
    return Session(engine)
