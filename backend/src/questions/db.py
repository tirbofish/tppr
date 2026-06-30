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

# Keep Supabase advisor hardening idempotent for databases this app prepares.
_SECURITY_DDL = [
    """
DO $$
DECLARE
    fn regprocedure;
    function_name text;
BEGIN
    FOREACH function_name IN ARRAY ARRAY[
        'public."deleteUser"()',
        'public.delete_own_account()'
    ] LOOP
        fn := to_regprocedure(function_name);
        IF fn IS NOT NULL THEN
            EXECUTE format(
                'ALTER FUNCTION %s SET search_path = public, auth, pg_temp',
                fn
            );
            EXECUTE format('REVOKE EXECUTE ON FUNCTION %s FROM PUBLIC', fn);

            IF to_regrole('anon') IS NOT NULL THEN
                EXECUTE format('REVOKE EXECUTE ON FUNCTION %s FROM anon', fn);
            END IF;

            IF to_regrole('authenticated') IS NOT NULL THEN
                EXECUTE format(
                    'REVOKE EXECUTE ON FUNCTION %s FROM authenticated',
                    fn
                );
            END IF;

            IF to_regrole('service_role') IS NOT NULL THEN
                EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO service_role', fn);
            END IF;
        END IF;
    END LOOP;
END $$;
""",
    """
DO $$
DECLARE
    table_name text;
    table_oid regclass;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'public.paper_takedown_states',
        'public.papers',
        'public.questions',
        'public.users'
    ] LOOP
        table_oid := to_regclass(table_name);
        IF table_oid IS NOT NULL THEN
            EXECUTE format(
                'DROP POLICY IF EXISTS %I ON %s',
                'Service role full access',
                table_oid
            );
        END IF;
    END LOOP;
END $$;
""",
    """
DO $$
BEGIN
    IF to_regclass('public.paper_stars') IS NOT NULL THEN
        CREATE INDEX IF NOT EXISTS ix_paper_stars_user_id
            ON public.paper_stars (user_id);
        CREATE INDEX IF NOT EXISTS ix_paper_stars_paper_id
            ON public.paper_stars (paper_id);
        ALTER TABLE public.paper_stars ENABLE ROW LEVEL SECURITY;

        DROP POLICY IF EXISTS "Users can read own stars" ON public.paper_stars;
        DROP POLICY IF EXISTS "Users can star own papers" ON public.paper_stars;
        DROP POLICY IF EXISTS "Users can unstar own papers" ON public.paper_stars;

        IF to_regrole('authenticated') IS NOT NULL THEN
            CREATE POLICY "Users can read own stars"
                ON public.paper_stars
                FOR SELECT
                TO authenticated
                USING ((select auth.uid())::text = user_id);

            CREATE POLICY "Users can star own papers"
                ON public.paper_stars
                FOR INSERT
                TO authenticated
                WITH CHECK ((select auth.uid())::text = user_id);

            CREATE POLICY "Users can unstar own papers"
                ON public.paper_stars
                FOR DELETE
                TO authenticated
                USING ((select auth.uid())::text = user_id);
        END IF;
    END IF;
END $$;
""",
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
        for statement in _SECURITY_DDL:
            conn.execute(text(statement))
    log.info("All tables created / verified")


def get_session() -> Session:
    return Session(engine)
