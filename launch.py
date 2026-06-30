# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "requests>=2.32.0",
#   "pydantic>=2.7.0",
#   "rich>=13.7.0", 
#   "python-dotenv>=1.2.2",
# ]
# ///

# THIS ENTIRE LAUNCH SCRIPT IS AI GENERATED, AND NO PLANS IT WILL CHANGE.
#
# --- DO NOT MARK ---

import os
import platform
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import urllib.request
import zipfile
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from importlib import import_module
from urllib.parse import quote_plus

try:
    Align = import_module("rich.align").Align
    box = import_module("rich.box")
    console_module = import_module("rich.console")
    Console = console_module.Console
    Group = console_module.Group
    Live = import_module("rich.live").Live
    Panel = import_module("rich.panel").Panel
    progress_module = import_module("rich.progress")
    Progress = progress_module.Progress
    SpinnerColumn = progress_module.SpinnerColumn
    TextColumn = progress_module.TextColumn
    TimeElapsedColumn = progress_module.TimeElapsedColumn
    Table = import_module("rich.table").Table
    Text = import_module("rich.text").Text
except ModuleNotFoundError:
    print(
        "Rich is required for the launcher TUI. Run with `uv run launch.py` or install `rich>=13.7.0`."
    )
    sys.exit(1)

ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.join(ROOT, "frontend")
BACKEND = os.path.join(ROOT, "backend")
PAPER_UTILS = os.path.join(ROOT, "tppr-paper-utils")
UV_CACHE_DIR = os.path.join(ROOT, ".uv-cache")
GCLOUD_CACHE_DIR = os.path.join(ROOT, ".gcloud-sdk")
GCLOUD_SDK_DIR = os.path.join(GCLOUD_CACHE_DIR, "google-cloud-sdk")
POSTGRES_CACHE_DIR = os.path.join(ROOT, ".postgresql")
POSTGRES_INSTALL_DIR = os.path.join(POSTGRES_CACHE_DIR, "pgsql")
POSTGRES_DATA_DIR = os.path.join(POSTGRES_CACHE_DIR, "data")
POSTGRES_LOG_FILE = os.path.join(POSTGRES_CACHE_DIR, "postgresql.log")
LOCAL_POSTGRES_USER = os.getenv("LOCAL_POSTGRES_USER", "tppr")
LOCAL_POSTGRES_DB = os.getenv("LOCAL_POSTGRES_DB", "tppr")
LOCAL_POSTGRES_HOST = "127.0.0.1"
LOCAL_POSTGRES_PORT = int(os.getenv("LOCAL_POSTGRES_PORT", "55432"))

console = Console()

# NOTE: this was made fully with AI


def rel(path):
    return os.path.relpath(path, ROOT)


def timestamp():
    return datetime.now().strftime("%H:%M:%S")


def log(message, style="cyan"):
    console.print(f"[dim]{timestamp()}[/dim] [{style}]*[/] {message}")


def success(message):
    log(message, "green")


def warn(message):
    log(message, "yellow")


def fatal(message, details=None, exit_code=1):
    renderable = Text(message)
    if details:
        renderable.append("\n\n")
        renderable.append(details)
    console.print(Panel(renderable, title="Launch failed", border_style="red"))
    sys.exit(exit_code)


def command_text(args):
    return " ".join(str(arg) for arg in args)


def render_header(split_mode):
    title = Text("TPPR Launcher", style="bold bright_white")
    title.append("\n")
    title.append(
        "Split mode: backend API + frontend dev server"
        if split_mode
        else "Combined mode: build frontend + serve from Flask",
        style="bright_cyan",
    )
    title.append("\n")
    title.append("Ctrl+C stops all managed services.", style="dim")

    console.print(
        Panel.fit(
            title,
            border_style="bright_blue",
            box=box.ROUNDED,
            padding=(1, 4),
        )
    )


def find_command(name):
    if platform.system().lower() == "windows":
        cmd_path = shutil.which(f"{name}.cmd")
        if cmd_path:
            return cmd_path
    return shutil.which(name)


def cached_gcloud_command():
    executable = "gcloud.cmd" if platform.system().lower() == "windows" else "gcloud"
    path = os.path.join(GCLOUD_SDK_DIR, "bin", executable)
    return path if os.path.exists(path) else None


def gcloud_archive_name():
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "windows" and machine in {"amd64", "x86_64"}:
        return "google-cloud-cli-windows-x86_64.zip"
    if system == "linux" and machine in {"amd64", "x86_64"}:
        return "google-cloud-cli-linux-x86_64.tar.gz"
    if system == "darwin" and machine in {"amd64", "x86_64"}:
        return "google-cloud-cli-darwin-x86_64.tar.gz"
    if system == "darwin" and machine in {"arm64", "aarch64"}:
        return "google-cloud-cli-darwin-arm.tar.gz"

    fatal(
        "Could not install Google Cloud CLI automatically",
        f"Unsupported platform for cached gcloud install: {system}/{machine}.",
    )


def download_file(url, target):
    tmp_target = f"{target}.tmp"
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            with open(tmp_target, "wb") as file:
                shutil.copyfileobj(response, file)
        os.replace(tmp_target, target)
    finally:
        if os.path.exists(tmp_target):
            os.unlink(tmp_target)


def install_cached_gcloud():
    cached = cached_gcloud_command()
    if cached:
        return cached

    archive_name = gcloud_archive_name()
    archive_url = (
        "https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/"
        f"{archive_name}"
    )
    archive_path = os.path.join(GCLOUD_CACHE_DIR, archive_name)
    os.makedirs(GCLOUD_CACHE_DIR, exist_ok=True)

    if not os.path.exists(archive_path):
        log("Downloading Google Cloud CLI for cached deploy tooling")
        try:
            download_file(archive_url, archive_path)
        except OSError as e:
            fatal(
                "Could not download Google Cloud CLI",
                f"{archive_url}\n\n{e}",
            )
    else:
        log("Using cached Google Cloud CLI archive")

    log("Installing cached Google Cloud CLI")
    with tempfile.TemporaryDirectory(prefix="gcloud-extract-", dir=GCLOUD_CACHE_DIR) as extract_dir:
        try:
            shutil.unpack_archive(archive_path, extract_dir)
        except (shutil.ReadError, tarfile.TarError, zipfile.BadZipFile) as e:
            fatal("Could not extract Google Cloud CLI archive", str(e))

        extracted_sdk = os.path.join(extract_dir, "google-cloud-sdk")
        if not os.path.isdir(extracted_sdk):
            fatal(
                "Could not install Google Cloud CLI",
                "The downloaded archive did not contain google-cloud-sdk.",
            )

        if os.path.exists(GCLOUD_SDK_DIR):
            shutil.rmtree(GCLOUD_SDK_DIR)
        shutil.move(extracted_sdk, GCLOUD_SDK_DIR)

    cached = cached_gcloud_command()
    if not cached:
        fatal(
            "Could not install Google Cloud CLI",
            "The cached SDK is missing the gcloud executable.",
        )
    return cached


def find_or_install_gcloud():
    gcloud = find_command("gcloud")
    if gcloud:
        return gcloud

    cached = cached_gcloud_command()
    if cached:
        return cached

    warn("gcloud was not found on PATH; installing a cached Google Cloud CLI.")
    return install_cached_gcloud()


def postgres_executable(name):
    executable = f"{name}.exe" if platform.system().lower() == "windows" else name
    cached = os.path.join(POSTGRES_INSTALL_DIR, "bin", executable)
    if os.path.exists(cached):
        return cached

    if platform.system().lower() == "windows":
        path = shutil.which(f"{name}.exe") or shutil.which(name)
    else:
        path = shutil.which(name)
    return path


def cached_postgres_available():
    return all(
        os.path.exists(
            os.path.join(
                POSTGRES_INSTALL_DIR,
                "bin",
                f"{name}.exe" if platform.system().lower() == "windows" else name,
            )
        )
        for name in ("postgres", "initdb", "psql", "createdb")
    )


def postgres_archive_name():
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "windows" and machine in {"amd64", "x86_64"}:
        return "postgresql-17.5-1-windows-x64-binaries.zip"

    fatal(
        "Could not install PostgreSQL automatically",
        f"Unsupported platform for cached PostgreSQL install: {system}/{machine}.",
    )


def install_cached_postgres():
    if cached_postgres_available():
        return POSTGRES_INSTALL_DIR

    archive_name = postgres_archive_name()
    archive_url = f"https://get.enterprisedb.com/postgresql/{archive_name}"
    archive_path = os.path.join(POSTGRES_CACHE_DIR, archive_name)
    os.makedirs(POSTGRES_CACHE_DIR, exist_ok=True)

    if not os.path.exists(archive_path):
        log("Downloading PostgreSQL for local development")
        try:
            download_file(archive_url, archive_path)
        except OSError as e:
            fatal("Could not download PostgreSQL", f"{archive_url}\n\n{e}")
    else:
        log("Using cached PostgreSQL archive")

    log("Installing cached PostgreSQL")
    with tempfile.TemporaryDirectory(prefix="postgres-extract-", dir=POSTGRES_CACHE_DIR) as extract_dir:
        try:
            shutil.unpack_archive(archive_path, extract_dir)
        except (shutil.ReadError, tarfile.TarError, zipfile.BadZipFile) as e:
            fatal("Could not extract PostgreSQL archive", str(e))

        extracted = os.path.join(extract_dir, "pgsql")
        if not os.path.isdir(extracted):
            fatal(
                "Could not install PostgreSQL",
                "The downloaded archive did not contain pgsql.",
            )

        if os.path.exists(POSTGRES_INSTALL_DIR):
            shutil.rmtree(POSTGRES_INSTALL_DIR)
        shutil.move(extracted, POSTGRES_INSTALL_DIR)

    if not cached_postgres_available():
        fatal(
            "Could not install PostgreSQL",
            "The cached PostgreSQL install is missing required executables.",
        )
    return POSTGRES_INSTALL_DIR


def find_or_install_postgres():
    required = ("postgres", "initdb", "psql", "createdb")
    if all(postgres_executable(name) for name in required):
        return os.path.dirname(postgres_executable("postgres"))

    warn("PostgreSQL was not found on PATH; installing cached PostgreSQL.")
    install_cached_postgres()
    return os.path.join(POSTGRES_INSTALL_DIR, "bin")


def local_database_url(port=LOCAL_POSTGRES_PORT):
    return (
        f"postgresql+psycopg2://{LOCAL_POSTGRES_USER}@"
        f"{LOCAL_POSTGRES_HOST}:{port}/{LOCAL_POSTGRES_DB}"
    )


def wait_for_tcp(host, port, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def run_postgres_command(args, *, env=None, check=True, capture_output=True):
    proc = subprocess.run(
        args,
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=capture_output,
    )
    if check and proc.returncode != 0:
        output = "\n".join(part for part in [proc.stdout, proc.stderr] if part).strip()
        fatal("PostgreSQL command failed", output or command_text(args))
    return proc


def postgres_env():
    env = os.environ.copy()
    env["PGCONNECT_TIMEOUT"] = "2"
    env["PGUSER"] = LOCAL_POSTGRES_USER
    return env


def ensure_postgres_cluster(postgres_bin):
    if os.path.exists(os.path.join(POSTGRES_DATA_DIR, "PG_VERSION")):
        return

    initdb = os.path.join(
        postgres_bin,
        "initdb.exe" if platform.system().lower() == "windows" else "initdb",
    )
    os.makedirs(POSTGRES_CACHE_DIR, exist_ok=True)
    run_postgres_command(
        [
            initdb,
            "-D",
            POSTGRES_DATA_DIR,
            "-U",
            LOCAL_POSTGRES_USER,
            "--auth=trust",
            "--encoding=UTF8",
        ],
        env=postgres_env(),
    )


def psql_command(postgres_bin, port, sql, database="postgres"):
    psql = os.path.join(
        postgres_bin,
        "psql.exe" if platform.system().lower() == "windows" else "psql",
    )
    return run_postgres_command(
        [
            psql,
            "-h",
            LOCAL_POSTGRES_HOST,
            "-p",
            str(port),
            "-U",
            LOCAL_POSTGRES_USER,
            "-d",
            database,
            "-tAc",
            sql,
        ],
        env=postgres_env(),
    )


def ensure_local_database(postgres_bin, port):
    exists = psql_command(
        postgres_bin,
        port,
        f"SELECT 1 FROM pg_database WHERE datname = '{LOCAL_POSTGRES_DB}'",
    ).stdout.strip()
    if exists == "1":
        return

    createdb = os.path.join(
        postgres_bin,
        "createdb.exe" if platform.system().lower() == "windows" else "createdb",
    )
    run_postgres_command(
        [
            createdb,
            "-h",
            LOCAL_POSTGRES_HOST,
            "-p",
            str(port),
            "-U",
            LOCAL_POSTGRES_USER,
            LOCAL_POSTGRES_DB,
        ],
        env=postgres_env(),
    )


@dataclass
class LocalPostgres:
    process: subprocess.Popen | None
    database_url: str
    port: int


def start_local_postgres(postgres_bin):
    ensure_postgres_cluster(postgres_bin)

    port = LOCAL_POSTGRES_PORT
    postgres = os.path.join(
        postgres_bin,
        "postgres.exe" if platform.system().lower() == "windows" else "postgres",
    )

    if wait_for_tcp(LOCAL_POSTGRES_HOST, port, timeout=0.5):
        ensure_local_database(postgres_bin, port)
        return LocalPostgres(None, local_database_url(port), port)

    os.makedirs(POSTGRES_CACHE_DIR, exist_ok=True)
    log(f"Starting local PostgreSQL on {LOCAL_POSTGRES_HOST}:{port}")
    log_file = open(POSTGRES_LOG_FILE, "a", encoding="utf-8")
    try:
        proc = subprocess.Popen(
            [
                postgres,
                "-D",
                POSTGRES_DATA_DIR,
                "-h",
                LOCAL_POSTGRES_HOST,
                "-p",
                str(port),
            ],
            cwd=ROOT,
            env=postgres_env(),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )
    finally:
        log_file.close()

    if not wait_for_tcp(LOCAL_POSTGRES_HOST, port, timeout=20):
        proc.terminate()
        fatal(
            "Local PostgreSQL did not start",
            f"See {POSTGRES_LOG_FILE} for details.",
        )

    if proc.poll() is not None:
        fatal(
            "Local PostgreSQL exited during startup",
            f"See {POSTGRES_LOG_FILE} for details.",
        )

    ensure_local_database(postgres_bin, port)
    return LocalPostgres(proc, local_database_url(port), port)


@dataclass
class DependencyStep:
    name: str
    detail: str
    status: str = "pending"


class DependencyTUI:
    """Small Rich dashboard for dependency setup."""

    STATUS_STYLES = {
        "pending": ("pending", "dim"),
        "running": ("running", "cyan"),
        "ready": ("ready", "green"),
        "skipped": ("skipped", "yellow"),
        "failed": ("failed", "red"),
    }

    def __init__(self, title):
        self.title = title
        self.steps = {}

    def add(self, key, name, detail):
        self.steps[key] = DependencyStep(name=name, detail=detail)

    def update(self, key, status=None, detail=None):
        step = self.steps[key]
        if status:
            step.status = status
        if detail:
            step.detail = detail

    def render(self):
        table = Table(
            box=box.SIMPLE,
            expand=True,
            show_edge=False,
            padding=(0, 1),
        )
        table.add_column("Dependency", style="bold")
        table.add_column("Status", no_wrap=True)
        table.add_column("Details", overflow="fold")

        for step in self.steps.values():
            label, style = self.STATUS_STYLES[step.status]
            table.add_row(step.name, f"[{style}]{label}[/]", step.detail)

        return Panel(
            Group(
                Align.center("[bold bright_white]Dependency setup[/]"),
                "",
                table,
            ),
            title=self.title,
            border_style="bright_blue",
            box=box.ROUNDED,
        )


def check_database_connection():
    """Report the PostgreSQL database that launch.py manages for local runs."""
    return (
        "Local PostgreSQL",
        True,
        f"{LOCAL_POSTGRES_HOST}:{LOCAL_POSTGRES_PORT}/{LOCAL_POSTGRES_DB}",
    )


def check_dependencies():
    missing = []

    uv = shutil.which("uv")
    if not uv:
        missing.append("uv")

    bun = find_command("bun")
    if not bun:
        missing.append("bun")

    postgres_bin = None
    if not missing:
        postgres_bin = find_or_install_postgres()

    runner = bun
    runner_name = "bun"
    runner_reason = "default JavaScript runner"

    table = Table(title="Toolchain", box=box.SIMPLE_HEAVY)
    table.add_column("Tool", style="bold")
    table.add_column("Status")
    table.add_column("Path", overflow="fold")
    table.add_row("uv", "[green]found[/]" if uv else "[red]missing[/]", uv or "-")
    table.add_row(
        "JavaScript runner",
        "[green]found[/]" if bun else "[red]missing[/]",
        f"{runner} ({runner_reason})" if runner else "-",
    )

    db_kind, db_reachable, db_detail = check_database_connection()
    table.add_row(
        db_kind,
        "[green]ready[/]" if db_reachable else "[red]invalid[/]",
        db_detail,
    )
    table.add_row(
        "PostgreSQL tools",
        "[green]found[/]" if postgres_bin else "[red]missing[/]",
        postgres_bin or "-",
    )

    console.print(table)

    if missing:
        fatal(
            "Missing required tools: " + ", ".join(missing),
            "Install uv and bun, then run launch.py again.",
        )

    if not db_reachable:
        fatal(
            "Database is not configured correctly",
            "launch.py should manage a local PostgreSQL database for development.",
        )

    return {
        "uv": uv,
        "js": runner,
        "js_name": runner_name,
        "postgres_bin": postgres_bin,
    }


def newest_existing_mtime(paths):
    existing = [path for path in paths if os.path.exists(path)]
    if not existing:
        return 0
    return max(os.path.getmtime(path) for path in existing)


def needs_refresh(target, sources):
    if not os.path.exists(target):
        return True
    return newest_existing_mtime(sources) > os.path.getmtime(target)


def missing_frontend_packages():
    required_packages = [
        ("vite", os.path.join(ROOT, "node_modules", "vite", "package.json")),
        (
            "typescript",
            os.path.join(ROOT, "node_modules", "typescript", "package.json"),
        ),
        ("react", os.path.join(ROOT, "node_modules", "react", "package.json")),
    ]
    missing = [name for name, path in required_packages if not os.path.exists(path)]

    vite_bins = [
        os.path.join(ROOT, "node_modules", ".bin", "vite"),
        os.path.join(ROOT, "node_modules", ".bin", "vite.cmd"),
    ]
    if not any(os.path.exists(path) for path in vite_bins):
        missing.append("vite CLI")

    return missing


def frontend_script_command(tools, script):
    return [tools["js"], "run", script], FRONTEND


def run_checked(args, cwd, label, env=None, show_status=True):
    display_cwd = rel(cwd)
    if show_status:
        with console.status(
            f"[bold cyan]{label}[/] [dim]({display_cwd})[/dim]", spinner="dots"
        ):
            proc = subprocess.run(
                args,
                cwd=cwd,
                env=env,
                text=True,
                capture_output=True,
            )
    else:
        proc = subprocess.run(
            args,
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
        )

    if proc.returncode != 0:
        output = "\n".join(part for part in [proc.stdout, proc.stderr] if part).strip()
        if len(output) > 6000:
            output = output[-6000:]
        console.print(
            Panel(
                Text(output or "No output captured."),
                title=f"{label} failed",
                subtitle=command_text(args),
                border_style="red",
            )
        )
        raise subprocess.CalledProcessError(
            proc.returncode, args, output=proc.stdout, stderr=proc.stderr
        )

    success(label)
    return proc


def run_streamed(args, cwd, label, env=None):
    log(label)
    proc = subprocess.run(args, cwd=cwd, env=env, text=True)
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, args)
    success(label)
    return proc


def run_capture(args, cwd, label):
    proc = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
    if proc.returncode != 0:
        output = "\n".join(part for part in [proc.stdout, proc.stderr] if part).strip()
        fatal(label, output or f"Command failed: {command_text(args)}")
    return proc.stdout.strip()


def gcloud_process_env():
    env = os.environ.copy()
    env["CLOUDSDK_PYTHON"] = sys.executable
    return env


def gcloud_config_value(gcloud, key, env=None):
    proc = subprocess.run(
        [gcloud, "config", "get-value", key],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        return ""
    value = proc.stdout.strip()
    if value == "(unset)":
        return ""
    return value


def load_project_env():
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        return
    load_dotenv(os.path.join(ROOT, ".env"))


def existing_database_url_from_env():
    """Return a DATABASE_URL from .env (DB_* parts or DATABASE_URL), or None.

    Lets `uv run launch.py` target an existing remote Postgres (e.g. Supabase)
    declared in .env instead of starting the bundled local one. Never fatals:
    missing config simply means "fall back to local bundled Postgres".
    """
    db_user = (os.getenv("DB_USER") or "").strip()
    db_password = os.getenv("DB_PASSWORD") or ""
    db_host = (os.getenv("DB_HOST") or "").strip()
    db_port = (os.getenv("DB_PORT") or "5432").strip()
    db_name = (os.getenv("DB_NAME") or "").strip()

    if all([db_user, db_password, db_host, db_name]):
        sslmode = (os.getenv("DB_SSLMODE") or "require").strip()
        query = f"?sslmode={quote_plus(sslmode)}" if sslmode else ""
        return (
            "postgresql+psycopg2://"
            f"{quote_plus(db_user)}:{quote_plus(db_password)}@"
            f"{db_host}:{db_port}/{quote_plus(db_name)}{query}"
        )

    database_url = (os.getenv("DATABASE_URL") or "").strip()
    if database_url:
        return database_url

    return None


def build_supabase_database_url():
    db_user = (os.getenv("DB_USER") or "").strip()
    db_password = os.getenv("DB_PASSWORD") or ""
    db_host = (os.getenv("DB_HOST") or "").strip()
    db_port = (os.getenv("DB_PORT") or "5432").strip()
    db_name = (os.getenv("DB_NAME") or "").strip()
    if all([db_user, db_password, db_host, db_name]):
        sslmode = (os.getenv("DB_SSLMODE") or "require").strip()
        query = f"?sslmode={quote_plus(sslmode)}" if sslmode else ""
        return (
            "postgresql+psycopg2://"
            f"{quote_plus(db_user)}:{quote_plus(db_password)}@"
            f"{db_host}:{db_port}/{quote_plus(db_name)}{query}"
        )

    database_url = (os.getenv("DATABASE_URL") or "").strip()
    if database_url:
        return database_url

    missing = [
        key
        for key, value in {
            "DB_USER": db_user,
            "DB_PASSWORD": db_password,
            "DB_HOST": db_host,
            "DB_NAME": db_name,
        }.items()
        if not value
    ]
    if missing:
        fatal(
            "Supabase database settings are missing",
            "Set DATABASE_URL or "
            + ", ".join(missing)
            + " in .env before running `uv run launch.py --deploy gcp`.",
        )


def gcloud_env_vars_arg(env_vars):
    pairs = [f"{key}={value}" for key, value in env_vars.items()]
    if all("," not in pair for pair in pairs):
        return ",".join(pairs)

    # gcloud.cmd runs through cmd.exe on Windows, so delimiters must avoid
    # shell metacharacters such as |, &, <, >, %, and ^.
    delimiter_candidates = ("~", "#", ";", "!")
    delimiter = next(
        (
            candidate
            for candidate in delimiter_candidates
            if all(candidate not in value for value in env_vars.values())
        ),
        None,
    )
    if delimiter is None:
        fatal(
            "Could not encode Cloud Run environment variables",
            "One of the database environment values contains every supported gcloud delimiter.",
        )
    return f"^{delimiter}^" + delimiter.join(pairs)


def cloud_run_database_env():
    database_url = build_supabase_database_url()
    supabase_url = (
        os.getenv("SUPABASE_URL")
        or os.getenv("VITE_SUPABASE_URL")
        or ""
    ).strip().rstrip("/")
    if not supabase_url:
        fatal(
            "Supabase URL is missing",
            "Set SUPABASE_URL or VITE_SUPABASE_URL in .env before deploying.",
        )

    env_vars = {
        "DATABASE_URL": database_url,
        "SUPABASE_URL": supabase_url,
        "VITE_SUPABASE_URL": supabase_url,
    }
    anon_key = (os.getenv("VITE_SUPABASE_ANON_KEY") or "").strip()
    if anon_key:
        env_vars["VITE_SUPABASE_ANON_KEY"] = anon_key
    return env_vars


def remove_cloud_run_env_vars(gcloud, service, region, project, names, env):
    for flag in ("--remove-env-vars", "--remove-secrets"):
        args = [
            gcloud,
            "run",
            "services",
            "update",
            service,
            "--region",
            region,
            flag,
            ",".join(names),
            "--quiet",
        ]
        if project:
            args.extend(["--project", project])

        proc = subprocess.run(
            args,
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
        )
        if proc.returncode != 0:
            output = "\n".join(part for part in [proc.stdout, proc.stderr] if part).strip()
            if "does not exist" not in output and "not found" not in output.lower():
                raise subprocess.CalledProcessError(
                    proc.returncode,
                    args,
                    output=proc.stdout,
                    stderr=proc.stderr,
                )


def check_deploy_tools():
    git = find_command("git")
    gcloud = find_or_install_gcloud()
    bun = find_command("bun")
    missing = [
        name
        for name, cmd in [("git", git), ("bun", bun)]
        if not cmd
    ]
    if missing:
        fatal(
            "Missing deploy tools: " + ", ".join(missing),
            "Install the missing command(s), then run `uv run launch.py --deploy gcp` again.",
        )
    return {
        "git": git,
        "gcloud": gcloud,
        "gcloud_env": gcloud_process_env(),
        "js": bun,
        "js_name": "bun",
    }


def copy_latest_commit(git, target_dir):
    archive_file = tempfile.NamedTemporaryFile(
        prefix="tppr-source-", suffix=".zip", delete=False
    )
    archive_path = archive_file.name
    archive_file.close()
    try:
        proc = subprocess.run(
            [git, "archive", "--format=zip", "--output", archive_path, "HEAD"],
            cwd=ROOT,
            text=True,
        )
        if proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, proc.args)
        shutil.unpack_archive(archive_path, target_dir)
    finally:
        try:
            os.unlink(archive_path)
        except OSError:
            pass


def copy_deploy_source(target_dir):
    ignored_dirs = {
        ".git",
        ".venv",
        ".uv-cache",
        ".gcloud-sdk",
        ".postgresql",
        "node_modules",
        "__pycache__",
        "dist",
    }
    ignored_files = {".env", "database.db"}

    def ignore(_dir, names):
        ignored = set()
        for name in names:
            if name in ignored_dirs or name in ignored_files:
                ignored.add(name)
        return ignored

    shutil.copytree(ROOT, target_dir, dirs_exist_ok=True, ignore=ignore)


def run_gcp_deploy():
    load_project_env()
    tools = check_deploy_tools()
    git = tools["git"]
    gcloud = tools["gcloud"]
    gcloud_env = tools["gcloud_env"]
    js = tools["js"]
    database_env = cloud_run_database_env()

    commit = run_capture(
        [git, "rev-parse", "--short=12", "HEAD"],
        ROOT,
        "Could not resolve the latest git commit",
    )
    branch = run_capture(
        [git, "branch", "--show-current"],
        ROOT,
        "Could not resolve the current git branch",
    ) or "detached HEAD"
    status = run_capture(
        [tools["git"], "status", "--short"],
        ROOT,
        "Could not inspect git status",
    )
    if status:
        warn("Working tree has uncommitted changes; deploying the current files.")

    service = os.getenv("GCP_CLOUD_RUN_SERVICE", os.getenv("CLOUD_RUN_SERVICE", "tppr"))
    region = (
        os.getenv("GCP_REGION")
        or os.getenv("CLOUD_RUN_REGION")
        or gcloud_config_value(gcloud, "run/region", env=gcloud_env)
        or gcloud_config_value(gcloud, "compute/region", env=gcloud_env)
        or "australia-southeast1"
    )
    project = (
        os.getenv("GCP_PROJECT")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
        or os.getenv("GCLOUD_PROJECT")
        or gcloud_config_value(gcloud, "core/project", env=gcloud_env)
    )
    if not project:
        fatal(
            "GCP project is not configured",
            "Set GCP_PROJECT in .env or run "
            "`gcloud config set project YOUR_PROJECT_ID`, then deploy again.",
        )

    table = Table(title="GCP deploy", box=box.SIMPLE_HEAVY)
    table.add_column("Setting", style="bold")
    table.add_column("Value", overflow="fold")
    table.add_row("Service", service)
    table.add_row("Region", region)
    table.add_row("Project", project)
    table.add_row("Database", os.getenv("DB_HOST", "(DATABASE_URL)"))
    table.add_row("Branch", branch)
    table.add_row("Commit", commit)
    console.print(table)

    with tempfile.TemporaryDirectory(prefix=f"tppr-deploy-{commit}-") as source_dir:
        log("Preparing deploy source from the current working tree")
        copy_deploy_source(source_dir)

        deploy_frontend = os.path.join(source_dir, "frontend")
        deploy_backend_assets = os.path.join(source_dir, "backend", "assets", "site")
        deploy_frontend_dist = os.path.join(deploy_frontend, "dist")
        build_env = os.environ.copy()
        build_env["VITE_BASE_PATH"] = "/"

        run_streamed(
            [js, "install", "--frozen-lockfile"],
            source_dir,
            "Installing frontend dependencies for deploy",
        )
        run_streamed(
            [js, "run", "build"],
            deploy_frontend,
            "Building frontend for deploy",
            env=build_env,
        )
        if os.path.exists(deploy_backend_assets):
            shutil.rmtree(deploy_backend_assets)
        shutil.copytree(deploy_frontend_dist, deploy_backend_assets)

        deploy_source = os.path.join(source_dir, "backend")
        deploy_args = [
            gcloud,
            "run",
            "deploy",
            service,
            "--source",
            deploy_source,
            "--region",
            region,
            "--update-env-vars",
            gcloud_env_vars_arg(database_env),
            "--clear-cloudsql-instances",
            "--quiet",
        ]
        if project:
            deploy_args.extend(["--project", project])

        run_streamed(
            deploy_args,
            ROOT,
            f"Deploying {service} to Cloud Run",
            env=gcloud_env,
        )


def check_do_deploy_tools():
    git = find_command("git")
    doctl = find_command("doctl")
    bun = find_command("bun")
    missing = [
        name
        for name, cmd in [("git", git), ("doctl", doctl), ("bun", bun)]
        if not cmd
    ]
    if missing:
        fatal(
            "Missing deploy tools: " + ", ".join(missing),
            "Install the missing command(s); doctl from "
            "https://docs.digitalocean.com/reference/doctl/how-to/install/, "
            "then run `uv run launch.py --deploy do` again.",
        )
    return {"git": git, "doctl": doctl, "js": bun}


# ponytail: hand-emit the flat App Platform spec instead of adding a yaml dep
def do_app_spec(name, region, repo, branch, run_command, env_vars):
    def q(value):
        return "'" + str(value).replace("'", "''") + "'"
    lines = [
        f"name: {name}",
        f"region: {region}",
        "services:",
        "- name: web",
        "  environment_slug: python",
        "  github:",
        f"    branch: {branch}",
        "    deploy_on_push: true",
        f"    repo: {repo}",
        f"  run_command: {run_command}",
        "  health_check:",
        "    http_path: /ping",
        "  env_vars:",
    ]
    for key, value in env_vars.items():
        lines.append(f"  - key: {key}")
        lines.append(f"    value: {q(value)}")
    return "\n".join(lines) + "\n"


def github_owner_repo(git):
    raw = run_capture(
        [git, "config", "--get", "remote.origin.url"],
        ROOT,
        "Could not read the git remote origin URL",
    ).strip()
    for sep in ("github.com/", "github.com:"):
        if sep in raw:
            tail = raw.split(sep, 1)[1]
            if tail.endswith(".git"):
                tail = tail[:-4]
            parts = tail.split("/")
            if len(parts) == 2 and all(parts):
                return "/".join(parts)
    return None


def run_do_deploy():
    load_project_env()
    tools = check_do_deploy_tools()
    git = tools["git"]
    doctl = tools["doctl"]

    auth_check = subprocess.run(
        [doctl, "account", "get"], capture_output=True, text=True
    )
    if auth_check.returncode != 0:
        fatal(
            "doctl is not authenticated",
            "Run `doctl auth init` with an API token, then deploy again.",
        )

    commit = run_capture(
        [git, "rev-parse", "--short=12", "HEAD"],
        ROOT,
        "Could not resolve the latest git commit",
    )
    branch = (
        run_capture(
            [git, "branch", "--show-current"],
            ROOT,
            "Could not resolve the current git branch",
        )
        or "main"
    )
    status = run_capture(
        [git, "status", "--short"], ROOT, "Could not inspect git status"
    )
    if status:
        warn(
            "Working tree has uncommitted changes; App Platform builds from the pushed HEAD."
        )

    repo = os.getenv("DO_APP_REPO") or github_owner_repo(git)
    if not repo:
        fatal(
            "GitHub repository could not be resolved",
            "Set DO_APP_REPO=owner/repo in .env, or add a GitHub remote to this repo.",
        )

    app_name = os.getenv("DO_APP_NAME", "tppr")
    region = os.getenv("DO_REGION", "syd")
    run_command = os.getenv("DO_RUN_COMMAND", "python src/main.py")
    env_vars = cloud_run_database_env()
    env_vars["PRODUCTION"] = "true"

    if not os.path.isfile(os.path.join(BACKEND, "assets", "site", "index.html")):
        warn(
            "backend/assets/site has no built frontend; App Platform won't build it. "
            "Build it locally and commit, or switch the spec to a Dockerfile component."
        )

    table = Table(title="DigitalOcean App Platform deploy", box=box.SIMPLE_HEAVY)
    table.add_column("Setting", style="bold")
    table.add_column("Value", overflow="fold")
    table.add_row("App", app_name)
    table.add_row("Region", region)
    table.add_row("Repo", repo)
    table.add_row("Branch", branch)
    table.add_row("Run", run_command)
    table.add_row("Database", os.getenv("DB_HOST", "(DATABASE_URL)"))
    table.add_row("Commit", commit)
    console.print(table)

    with tempfile.TemporaryDirectory(prefix=f"tppr-do-deploy-{commit}-") as spec_dir:
        spec_path = os.path.join(spec_dir, "app.yaml")
        with open(spec_path, "w", encoding="utf-8") as fh:
            fh.write(
                do_app_spec(app_name, region, repo, branch, run_command, env_vars)
            )
        run_streamed(
            [doctl, "apps", "create", "--upsert", "--spec", spec_path, "--wait"],
            ROOT,
            f"Deploying {app_name} to DigitalOcean App Platform",
        )


def ensure_python_dependencies(tools, skip_install=False, tui=None, live=None):
    step_key = "python"
    if skip_install:
        if tui and live:
            tui.update(step_key, "skipped", "Install step bypassed by --skip-install")
            live.update(tui.render())
        warn("Skipping Python dependency sync (--skip-install).")
        return

    venv_dir = os.path.join(ROOT, ".venv")
    dependency_files = [
        os.path.join(ROOT, "pyproject.toml"),
        os.path.join(ROOT, "uv.lock"),
        os.path.join(BACKEND, "pyproject.toml"),
        os.path.join(BACKEND, "uv.lock"),
        os.path.join(PAPER_UTILS, "pyproject.toml"),
        os.path.join(PAPER_UTILS, "uv.lock"),
    ]

    if tui and live:
        tui.update(step_key, "running", "Checking .venv against workspace manifests")
        live.update(tui.render())

    if not needs_refresh(venv_dir, dependency_files):
        if tui and live:
            tui.update(step_key, "ready", ".venv is newer than dependency files")
            live.update(tui.render())
        success("Python dependencies are up to date")
        return

    env = os.environ.copy()
    env["UV_CACHE_DIR"] = UV_CACHE_DIR
    os.makedirs(UV_CACHE_DIR, exist_ok=True)
    if tui and live:
        tui.update(step_key, "running", "Running uv sync --all-packages")
        live.update(tui.render())
    try:
        run_checked(
            [tools["uv"], "sync", "--all-packages"],
            cwd=ROOT,
            env=env,
            label="Syncing Python workspace dependencies",
            show_status=not live,
        )
    except subprocess.CalledProcessError:
        if tui and live:
            tui.update(step_key, "failed", "uv sync --all-packages failed")
            live.update(tui.render())
        raise
    if tui and live:
        tui.update(step_key, "ready", "Workspace dependencies synced")
        live.update(tui.render())


def ensure_frontend_dependencies(tools, skip_install=False, tui=None, live=None):
    step_key = "frontend"
    if skip_install:
        if tui and live:
            tui.update(step_key, "skipped", "Install step bypassed by --skip-install")
            live.update(tui.render())
        warn("Skipping frontend dependency install (--skip-install).")
        return

    node_modules = os.path.join(ROOT, "node_modules")
    dependency_files = [
        os.path.join(ROOT, "package.json"),
        os.path.join(ROOT, "bun.lock"),
        os.path.join(FRONTEND, "package.json"),
        os.path.join(FRONTEND, "bun.lock"),
    ]

    if tui and live:
        tui.update(
            step_key, "running", "Checking node_modules against package manifests"
        )
        live.update(tui.render())

    missing_packages = missing_frontend_packages()
    if not needs_refresh(node_modules, dependency_files) and not missing_packages:
        if tui and live:
            tui.update(
                step_key,
                "ready",
                "node_modules has required frontend packages and is up to date",
            )
            live.update(tui.render())
        success("Frontend dependencies are up to date")
        return

    command = [tools["js"], "install"]
    install_reason = (
        "missing " + ", ".join(missing_packages)
        if missing_packages
        else "package manifests changed"
    )
    if tui and live:
        tui.update(
            step_key,
            "running",
            f"Running {tools['js_name']} install ({install_reason})",
        )
        live.update(tui.render())
    try:
        run_checked(
            command,
            cwd=ROOT,
            label=f"Installing frontend dependencies with {tools['js_name']}",
            show_status=not live,
        )
    except subprocess.CalledProcessError:
        if tui and live:
            tui.update(step_key, "failed", f"{tools['js_name']} install failed")
            live.update(tui.render())
        raise
    if tui and live:
        tui.update(step_key, "ready", "Frontend packages installed")
        live.update(tui.render())


def prepare_dependencies(tools, skip_install=False):
    tui = DependencyTUI("Project dependencies")
    tui.add("python", "Python workspace", ".venv, pyproject.toml, uv.lock")
    tui.add("frontend", "Frontend workspace", "node_modules, package.json, lockfiles")

    with Live(tui.render(), console=console, refresh_per_second=8) as live:
        ensure_python_dependencies(tools, skip_install=skip_install, tui=tui, live=live)
        ensure_frontend_dependencies(
            tools, skip_install=skip_install, tui=tui, live=live
        )
        live.update(tui.render())


def terminate_process(proc):
    if not proc or proc.poll() is not None:
        return

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def build_frontend(tools):
    command, cwd = frontend_script_command(tools, "build")
    run_checked(command, cwd=cwd, label="Building frontend")


def run_backend(tools, api_only=False, capture_output=False, log_start=True):
    os.makedirs(UV_CACHE_DIR, exist_ok=True)
    env = os.environ.copy()
    env["UV_CACHE_DIR"] = UV_CACHE_DIR
    if tools.get("database_url"):
        env["DATABASE_URL"] = tools["database_url"]

    args = [tools["uv"], "run", "src/main.py"]
    if api_only:
        args.append("--api-only")

    if log_start:
        log("Starting backend" + (" in API-only mode" if api_only else ""))
    return subprocess.Popen(
        args,
        cwd=BACKEND,
        env=env,
        stdout=subprocess.PIPE if capture_output else None,
        stderr=subprocess.STDOUT if capture_output else None,
        text=capture_output,
        encoding="utf-8" if capture_output else None,
        errors="replace" if capture_output else None,
        bufsize=1 if capture_output else -1,
    )


def run_frontend_dev(tools, capture_output=False, log_start=True):
    command, cwd = frontend_script_command(tools, "dev")
    if log_start:
        log("Starting frontend dev server")
    return subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE if capture_output else None,
        stderr=subprocess.STDOUT if capture_output else None,
        text=capture_output,
        encoding="utf-8" if capture_output else None,
        errors="replace" if capture_output else None,
        bufsize=1 if capture_output else -1,
    )


class FileWatcher:
    """Watches directories for file changes and triggers callbacks."""

    def __init__(
        self, watch_dirs, extensions, callback, debounce=1.0, label="files", quiet=False
    ):
        self.watch_dirs = watch_dirs
        self.extensions = extensions
        self.callback = callback
        self.debounce = debounce
        self.label = label
        self.quiet = quiet
        self._stop = threading.Event()
        self._file_mtimes = {}
        self._thread = None

    def _snapshot(self):
        mtimes = {}
        for watch_dir in self.watch_dirs:
            for dirpath, _, filenames in os.walk(watch_dir):
                basename = os.path.basename(dirpath)
                if basename in (
                    "node_modules",
                    "__pycache__",
                    ".git",
                    "dist",
                    ".venv",
                    ".postgresql",
                ):
                    continue
                for f in filenames:
                    if any(f.endswith(ext) for ext in self.extensions):
                        full = os.path.join(dirpath, f)
                        try:
                            mtimes[full] = os.path.getmtime(full)
                        except OSError:
                            pass
        return mtimes

    def _poll(self):
        self._file_mtimes = self._snapshot()
        while not self._stop.is_set():
            time.sleep(self.debounce)
            new_mtimes = self._snapshot()
            changed = []
            for path, mtime in new_mtimes.items():
                if path not in self._file_mtimes or self._file_mtimes[path] != mtime:
                    changed.append(path)
            for path in self._file_mtimes:
                if path not in new_mtimes:
                    changed.append(path)
            if changed:
                if not self.quiet:
                    changed_text = ", ".join(rel(p) for p in changed[:3])
                    if len(changed) > 3:
                        changed_text += f", +{len(changed) - 3} more"
                    warn(f"Detected {self.label} change: {changed_text}")
                self._file_mtimes = new_mtimes
                self.callback(changed)

    def start(self):
        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()
        if not self.quiet:
            success(f"Watching {self.label}")

    def stop(self):
        self._stop.set()


class ProcessManager:
    """Manages restarting a subprocess."""

    def __init__(self, start_fn, label, quiet=False):
        self._start_fn = start_fn
        self._label = label
        self._quiet = quiet
        self._proc = None
        self._lock = threading.Lock()

    def start(self):
        with self._lock:
            self._proc = self._start_fn()
        return self._proc

    def restart(self):
        with self._lock:
            if self._proc and self._proc.poll() is None:
                if not self._quiet:
                    warn(f"Stopping {self._label}...")
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
            if not self._quiet:
                log(f"Restarting {self._label}...")
            self._proc = self._start_fn()
        return self._proc

    def terminate(self):
        with self._lock:
            if self._proc and self._proc.poll() is None:
                if not self._quiet:
                    warn(f"Stopping {self._label}...")
                self._proc.terminate()

    @property
    def process(self):
        with self._lock:
            return self._proc

    def wait(self):
        if self._proc:
            self._proc.wait()


class OutputPane:
    """Captures a subprocess stream for live Rich rendering."""

    def __init__(self, title, border_style, max_lines=300):
        self.title = title
        self.border_style = border_style
        self._lines = deque(maxlen=max_lines)
        self._lock = threading.Lock()

    def append(self, line):
        line = line.rstrip()
        if not line:
            return
        with self._lock:
            self._lines.append(line)

    def attach(self, proc):
        if not proc.stdout:
            self.append("No output stream attached.")
            return

        def reader():
            for line in proc.stdout:
                self.append(line)

        threading.Thread(target=reader, daemon=True).start()

    def render(self, visible_lines):
        with self._lock:
            lines = list(self._lines)[-visible_lines:]

        if lines:
            top_padding = max(0, visible_lines - len(lines))
            padded_output = "\n" * top_padding + "\n".join(lines)
            body = Text.from_ansi(padded_output)
        else:
            body = Text("\n" * (visible_lines - 1), style="dim")
            body.append("Waiting for output...", style="dim")

        return Panel(
            body,
            title=self.title,
            border_style=self.border_style,
            box=box.ROUNDED,
            height=visible_lines + 2,
        )


class SplitOutputView:
    def __init__(self, backend_pane, frontend_pane):
        self.backend_pane = backend_pane
        self.frontend_pane = frontend_pane

    def render(self):
        visible_lines = max(8, console.height - 11)
        links = Table.grid(padding=(0, 2))
        links.add_column(style="bold")
        links.add_column()
        links.add_column(style="bold")
        links.add_column()
        links.add_row(
            "Backend",
            "[link=http://localhost:5000]http://localhost:5000[/link]",
            "Frontend",
            "[link=http://localhost:5173]http://localhost:5173[/link]",
        )
        links.add_row(
            "API docs",
            "[link=http://localhost:5000/api/docs/]http://localhost:5000/api/docs/[/link]",
            "",
            "",
        )

        table = Table.grid(expand=True)
        table.add_column(ratio=1)
        table.add_column(ratio=1)
        table.add_row(
            self.backend_pane.render(visible_lines),
            self.frontend_pane.render(visible_lines),
        )
        return Group(
            Panel(
                links, title="Split mode ready", border_style="green", box=box.ROUNDED
            ),
            table,
        )


class ManagedProcessExited(RuntimeError):
    def __init__(self, service, returncode):
        self.service = service
        self.returncode = returncode
        super().__init__(f"{service} exited with code {returncode}")


def render_ready(split_mode):
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()

    if split_mode:
        table.add_row(
            "Backend", "[link=http://localhost:5000]http://localhost:5000[/link]"
        )
        table.add_row(
            "Frontend", "[link=http://localhost:5173]http://localhost:5173[/link]"
        )
    else:
        table.add_row("App", "[link=http://localhost:5000]http://localhost:5000[/link]")
    table.add_row(
        "API docs",
        "[link=http://localhost:5000/api/docs/]http://localhost:5000/api/docs/[/link]",
    )

    console.print(Panel(table, title="Ready", border_style="green", box=box.ROUNDED))


def run_split_mode(tools, watchers):
    backend_pane = OutputPane("Backend API", "bright_cyan")
    frontend_pane = OutputPane("Frontend Dev Server", "bright_magenta")

    def start_backend():
        backend_pane.append("Starting backend in API-only mode...")
        proc = run_backend(tools, api_only=True, capture_output=True, log_start=False)
        backend_pane.attach(proc)
        return proc

    backend_mgr = ProcessManager(start_backend, "backend", quiet=True)
    backend_mgr.start()

    frontend_pane.append("Starting frontend dev server...")
    frontend_proc = run_frontend_dev(tools, capture_output=True, log_start=False)
    frontend_pane.attach(frontend_proc)

    backend_src = os.path.join(BACKEND, "src")

    def on_backend_change(changed):
        backend_pane.append("Backend source changed; restarting...")
        backend_mgr.restart()

    backend_watcher = FileWatcher(
        watch_dirs=[backend_src],
        extensions=[".py"],
        callback=on_backend_change,
        debounce=1.0,
        label="backend files",
        quiet=True,
    )
    backend_watcher.start()
    watchers.append(backend_watcher)

    split_view = SplitOutputView(backend_pane, frontend_pane)

    try:
        with Live(
            split_view.render(),
            console=console,
            refresh_per_second=8,
            screen=False,
        ) as live:
            while True:
                backend_proc = backend_mgr.process
                backend_code = backend_proc.poll() if backend_proc else None
                frontend_code = frontend_proc.poll()

                if backend_code is not None:
                    backend_pane.append(f"Backend exited with code {backend_code}.")
                    time.sleep(0.5)
                    live.update(split_view.render())
                    raise ManagedProcessExited("Backend", backend_code)
                if frontend_code is not None:
                    frontend_pane.append(f"Frontend exited with code {frontend_code}.")
                    time.sleep(0.5)
                    live.update(split_view.render())
                    raise ManagedProcessExited("Frontend", frontend_code)

                live.update(split_view.render())
                time.sleep(0.125)
    except KeyboardInterrupt:
        warn("Shutting down...")
        backend_mgr.terminate()
        frontend_proc.terminate()


def run_combined_mode(tools, watchers):
    build_frontend(tools)
    backend_mgr = ProcessManager(lambda: run_backend(tools), "backend")
    backend_mgr.start()

    backend_src = os.path.join(BACKEND, "src")
    backend_watcher = FileWatcher(
        watch_dirs=[backend_src],
        extensions=[".py"],
        callback=lambda changed: backend_mgr.restart(),
        debounce=1.0,
        label="backend files",
    )
    backend_watcher.start()
    watchers.append(backend_watcher)

    frontend_src = os.path.join(FRONTEND, "src")

    def on_frontend_change(changed):
        warn("Frontend source changed; rebuilding...")
        try:
            build_frontend(tools)
            backend_mgr.restart()
        except subprocess.CalledProcessError:
            warn("Frontend build failed; backend restart skipped.")

    frontend_watcher = FileWatcher(
        watch_dirs=[frontend_src],
        extensions=[
            ".ts",
            ".tsx",
            ".js",
            ".jsx",
            ".vue",
            ".svelte",
            ".css",
            ".html",
        ],
        callback=on_frontend_change,
        debounce=2.0,
        label="frontend files",
    )
    frontend_watcher.start()
    watchers.append(frontend_watcher)

    render_ready(split_mode=False)

    try:
        backend_mgr.wait()
    except KeyboardInterrupt:
        warn("Shutting down...")
        backend_mgr.terminate()


def main():
    if "--deploy" in sys.argv:
        deploy_index = sys.argv.index("--deploy")
        provider = sys.argv[deploy_index + 1] if deploy_index + 1 < len(sys.argv) else ""
        if provider in ("do", "do-app", "do-app-platform", "digitalocean"):
            deploy_fn = run_do_deploy
        elif provider == "gcp":
            deploy_fn = run_gcp_deploy
        else:
            fatal(
                "Unsupported deploy target",
                "Use `uv run launch.py --deploy gcp` or `uv run launch.py --deploy do`.",
            )
        try:
            deploy_fn()
        except KeyboardInterrupt:
            warn("Deployment interrupted.")
        except subprocess.CalledProcessError as exc:
            fatal(
                f"Command failed with exit code {exc.returncode}: {command_text(exc.cmd)}"
            )
        except Exception as exc:
            fatal(str(exc))
        return

    split_mode = "--build" not in sys.argv
    skip_install = "--skip-install" in sys.argv
    watchers = []
    local_postgres = None

    render_header(split_mode)

    try:
        tools = check_dependencies()
        prepare_dependencies(tools, skip_install=skip_install)
        load_project_env()
        remote_db_url = existing_database_url_from_env()
        if remote_db_url:
            tools["database_url"] = remote_db_url
            success("Using existing database from .env (remote Postgres)")
        else:
            local_postgres = start_local_postgres(tools["postgres_bin"])
            tools["database_url"] = local_postgres.database_url
            success(
                "Local PostgreSQL ready at "
                f"{LOCAL_POSTGRES_HOST}:{local_postgres.port}/{LOCAL_POSTGRES_DB}"
            )

        if split_mode:
            run_split_mode(tools, watchers)
        else:
            run_combined_mode(tools, watchers)
    except KeyboardInterrupt:
        warn("Interrupted.")
    except subprocess.CalledProcessError as exc:
        fatal(
            f"Command failed with exit code {exc.returncode}: {command_text(exc.cmd)}"
        )
    except Exception as exc:
        fatal(str(exc))
    finally:
        if local_postgres and local_postgres.process:
            terminate_process(local_postgres.process)
        for watcher in watchers:
            watcher.stop()
        success("Launcher cleanup complete")


if __name__ == "__main__":
    main()
