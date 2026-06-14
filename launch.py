# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "requests>=2.32.0",
#   "pydantic>=2.7.0",
#   "rich>=13.7.0",
# ]
# ///

# THIS ENTIRE LAUNCH SCRIPT IS AI GENERATED, AND NO PLANS IT WILL CHANGE.
#
# --- DO NOT MARK ---

import os
import platform
import shutil
import subprocess
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from importlib import import_module

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
ENV_FILE = os.path.join(ROOT, ".env")

DEFAULT_DATABASE_URL = "postgresql://localhost:5432/tppr"

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


def check_dependencies():
    missing = []

    uv = shutil.which("uv")
    if not uv:
        missing.append("uv")

    bun = find_command("bun")
    if not bun:
        missing.append("bun")

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
    console.print(table)

    if missing:
        fatal(
            "Missing required tools: " + ", ".join(missing),
            "Install uv and bun, then run launch.py again.",
        )

    return {
        "uv": uv,
        "js": runner,
        "js_name": runner_name,
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


def load_env_file():
    values = {}
    if not os.path.exists(ENV_FILE):
        return values

    with open(ENV_FILE, "r", encoding="utf-8") as env:
        for line in env:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            values[key] = value

    return values


def write_env_values(updates):
    existing_lines = []
    seen = set()

    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as env:
            existing_lines = env.readlines()

    next_lines = []
    for line in existing_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0]
            if key in updates:
                next_lines.append(f"{key}={updates[key]}\n")
                seen.add(key)
                continue
        next_lines.append(line)

    if next_lines and not next_lines[-1].endswith("\n"):
        next_lines[-1] += "\n"

    for key, value in updates.items():
        if key not in seen:
            next_lines.append(f"{key}={value}\n")

    with open(ENV_FILE, "w", encoding="utf-8") as env:
        env.writelines(next_lines)


def setup_database_env():
    env_values = load_env_file()
    if "DATABASE_URL" not in env_values:
        write_env_values({"DATABASE_URL": DEFAULT_DATABASE_URL})
        success(f"Added DATABASE_URL to .env (default: {DEFAULT_DATABASE_URL})")
    else:
        success(f"DATABASE_URL already configured: {env_values['DATABASE_URL']}")


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
                if basename in ("node_modules", "__pycache__", ".git", "dist", ".venv"):
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
    split_mode = "--build" not in sys.argv
    skip_install = "--skip-install" in sys.argv
    watchers = []

    render_header(split_mode)

    try:
        tools = check_dependencies()
        prepare_dependencies(tools, skip_install=skip_install)
        setup_database_env()

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
        for watcher in watchers:
            watcher.stop()
        success("Launcher cleanup complete")


if __name__ == "__main__":
    main()
