import os
import json
import platform
import shutil
import secrets
import socket
import subprocess
import sys
import tarfile
import threading
import time
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.join(ROOT, "frontend")
BACKEND = os.path.join(ROOT, "backend")
UV_CACHE_DIR = os.path.join(ROOT, ".uv-cache")
ENV_FILE = os.path.join(ROOT, ".env")
SEAWEEDFS_DIR = os.path.join(ROOT, ".seaweedfs")
SEAWEEDFS_BIN_DIR = os.path.join(SEAWEEDFS_DIR, "bin")
SEAWEEDFS_DATA_DIR = os.path.join(SEAWEEDFS_DIR, "data")
SEAWEEDFS_CONFIG_FILE = os.path.join(SEAWEEDFS_DIR, "s3.json")
SEAWEEDFS_MASTER_PORT = "9333"
SEAWEEDFS_VOLUME_PORT = "8081"
SEAWEEDFS_FILER_PORT = "8888"
SEAWEEDFS_S3_PORT = "8333"
SEAWEEDFS_BUCKET = "tppr"

# NOTE: this was made fully with AI


def check_dependencies():
    missing = []

    uv = shutil.which("uv")
    if not uv:
        missing.append("uv")

    npm = shutil.which("npm")
    bun = shutil.which("bun")
    if not npm and not bun:
        missing.append("npm or bun")

    if missing:
        print("Missing required tools: " + ", ".join(missing))
        sys.exit(1)

    return {
        "uv": uv,
        "js": bun or npm,  # prefer bun if available
    }


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


def seaweedfs_asset_name():
    system = platform.system().lower()
    machine = platform.machine().lower()

    os_map = {
        "linux": "linux",
        "darwin": "darwin",
        "freebsd": "freebsd",
        "windows": "windows",
    }
    arch_map = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }

    if system not in os_map or machine not in arch_map:
        raise RuntimeError(f"Unsupported SeaweedFS platform: {system}/{machine}")

    extension = "zip" if system == "windows" else "tar.gz"
    return f"{os_map[system]}_{arch_map[machine]}.{extension}"


def find_or_install_weed():
    binary = "weed.exe" if platform.system().lower() == "windows" else "weed"
    local_weed = os.path.join(SEAWEEDFS_BIN_DIR, binary)
    if os.path.exists(local_weed):
        return local_weed

    system_weed = shutil.which(binary) or shutil.which("weed")
    if system_weed:
        return system_weed

    print("Installing SeaweedFS locally...")
    os.makedirs(SEAWEEDFS_BIN_DIR, exist_ok=True)
    archive_name = seaweedfs_asset_name()
    archive_path = os.path.join(SEAWEEDFS_DIR, archive_name)
    url = f"https://github.com/seaweedfs/seaweedfs/releases/latest/download/{archive_name}"

    urllib.request.urlretrieve(url, archive_path)
    try:
        if archive_name.endswith(".zip"):
            with zipfile.ZipFile(archive_path) as archive:
                archive.extract(binary, SEAWEEDFS_BIN_DIR)
        else:
            with tarfile.open(archive_path, "r:gz") as archive:
                member = archive.getmember(binary)
                member.name = binary
                archive.extract(member, SEAWEEDFS_BIN_DIR)
    finally:
        if os.path.exists(archive_path):
            os.remove(archive_path)

    if platform.system().lower() != "windows":
        os.chmod(local_weed, 0o755)

    return local_weed


def setup_seaweedfs():
    env_values = load_env_file()
    access_key = env_values.get("SEAWEEDFS_S3_ACCESS_KEY") or "tppr-dev"
    secret_key = env_values.get("SEAWEEDFS_S3_SECRET_KEY") or secrets.token_urlsafe(32)

    os.makedirs(SEAWEEDFS_DATA_DIR, exist_ok=True)

    s3_config = {
        "identities": [
            {
                "name": "tppr_dev",
                "credentials": [
                    {
                        "accessKey": access_key,
                        "secretKey": secret_key,
                    }
                ],
                "actions": ["Admin", "Read", "List", "Tagging", "Write"],
            }
        ]
    }
    with open(SEAWEEDFS_CONFIG_FILE, "w", encoding="utf-8") as config:
        json.dump(s3_config, config, indent=2)
        config.write("\n")

    updates = {
        "SEAWEEDFS_MASTER_URL": f"localhost:{SEAWEEDFS_MASTER_PORT}",
        "SEAWEEDFS_FILER_URL": f"http://localhost:{SEAWEEDFS_FILER_PORT}",
        "SEAWEEDFS_S3_ENDPOINT": f"http://localhost:{SEAWEEDFS_S3_PORT}",
        "SEAWEEDFS_S3_ACCESS_KEY": access_key,
        "SEAWEEDFS_S3_SECRET_KEY": secret_key,
        "SEAWEEDFS_S3_BUCKET": env_values.get("SEAWEEDFS_S3_BUCKET") or SEAWEEDFS_BUCKET,
        "SEAWEEDFS_DATA_DIR": SEAWEEDFS_DATA_DIR,
        "SEAWEEDFS_CONFIG_FILE": SEAWEEDFS_CONFIG_FILE,
    }
    write_env_values(updates)

    if port_is_open("localhost", int(SEAWEEDFS_S3_PORT)):
        print("SeaweedFS S3 endpoint is already running.")
        return None

    weed = find_or_install_weed()
    args = [
        weed,
        "server",
        f"-dir={SEAWEEDFS_DATA_DIR}",
        "-ip=localhost",
        f"-master.port={SEAWEEDFS_MASTER_PORT}",
        f"-volume.port={SEAWEEDFS_VOLUME_PORT}",
        "-filer",
        f"-filer.port={SEAWEEDFS_FILER_PORT}",
        "-s3",
        f"-s3.port={SEAWEEDFS_S3_PORT}",
        "-s3.iam=false",
        f"-s3.config={SEAWEEDFS_CONFIG_FILE}",
    ]

    print("Starting SeaweedFS...")
    proc = subprocess.Popen(args, cwd=ROOT)
    try:
        wait_for_port("localhost", int(SEAWEEDFS_FILER_PORT), "SeaweedFS filer", proc=proc)
        wait_for_port(
            "localhost",
            int(SEAWEEDFS_S3_PORT),
            "SeaweedFS S3",
            timeout=90,
            proc=proc,
        )
    except Exception:
        terminate_process(proc)
        raise

    return proc


def port_is_open(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex((host, port)) == 0


def wait_for_port(host, port, label, timeout=60, proc=None):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if port_is_open(host, port):
            return
        if proc and proc.poll() is not None:
            raise RuntimeError(f"{label} exited before starting on {host}:{port}")
        time.sleep(0.25)

    raise RuntimeError(f"{label} did not start on {host}:{port}")


def terminate_process(proc):
    if not proc or proc.poll() is not None:
        return

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def build_frontend(tools):
    print("Building frontend...")
    runner = tools["js"]
    subprocess.run([runner, "run", "build"], cwd=FRONTEND, check=True)


def run_backend(tools, api_only=False):
    os.makedirs(UV_CACHE_DIR, exist_ok=True)
    env = os.environ.copy()
    env["UV_CACHE_DIR"] = UV_CACHE_DIR

    args = [tools["uv"], "run", "src/main.py"]
    if api_only:
        args.append("--api-only")
    return subprocess.Popen(args, cwd=BACKEND, env=env)


def run_frontend_dev(tools):
    runner = tools["js"]
    return subprocess.Popen([runner, "run", "dev"], cwd=FRONTEND)


class FileWatcher:
    """Watches directories for file changes and triggers callbacks."""

    def __init__(self, watch_dirs, extensions, callback, debounce=1.0):
        self.watch_dirs = watch_dirs
        self.extensions = extensions
        self.callback = callback
        self.debounce = debounce
        self._stop = threading.Event()
        self._file_mtimes = {}
        self._thread = None

    def _snapshot(self):
        mtimes = {}
        for watch_dir in self.watch_dirs:
            for dirpath, _, filenames in os.walk(watch_dir):
                # skip node_modules, __pycache__, .git, dist
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
                for p in changed:
                    print(f"  Changed: {os.path.relpath(p, ROOT)}")
                self._file_mtimes = new_mtimes
                self.callback(changed)

    def start(self):
        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()


class ProcessManager:
    """Manages restarting a subprocess."""

    def __init__(self, start_fn):
        self._start_fn = start_fn
        self._proc = None
        self._lock = threading.Lock()

    def start(self):
        with self._lock:
            self._proc = self._start_fn()
        return self._proc

    def restart(self):
        with self._lock:
            if self._proc and self._proc.poll() is None:
                print("Stopping process...")
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
            print("Restarting process...")
            self._proc = self._start_fn()
        return self._proc

    def terminate(self):
        with self._lock:
            if self._proc and self._proc.poll() is None:
                self._proc.terminate()

    def wait(self):
        if self._proc:
            self._proc.wait()


if __name__ == "__main__":
    tools = check_dependencies()
    watchers = []
    seaweedfs_proc = setup_seaweedfs()

    if "--split" in sys.argv:
        # --- Split mode: backend API + frontend dev server ---
        print("Starting backend (API-only) with file watching...")
        backend_mgr = ProcessManager(lambda: run_backend(tools, api_only=True))
        backend_mgr.start()

        print("Starting frontend dev server...")
        frontend_proc = run_frontend_dev(tools)

        # Watch backend Python files for changes
        backend_src = os.path.join(BACKEND, "src")
        backend_watcher = FileWatcher(
            watch_dirs=[backend_src],
            extensions=[".py"],
            callback=lambda changed: backend_mgr.restart(),
            debounce=1.0,
        )
        backend_watcher.start()
        watchers.append(backend_watcher)

        print("Watching backend for changes...")

        try:
            backend_mgr.wait()
            frontend_proc.wait()
        except KeyboardInterrupt:
            print("\nShutting down...")
            backend_mgr.terminate()
            frontend_proc.terminate()
        finally:
            terminate_process(seaweedfs_proc)
            for w in watchers:
                w.stop()
    else:
        # --- Combined mode: build frontend + serve from backend ---
        build_frontend(tools)
        print("Starting backend with file watching...")
        backend_mgr = ProcessManager(lambda: run_backend(tools))
        backend_mgr.start()

        # Watch backend Python files
        backend_src = os.path.join(BACKEND, "src")
        backend_watcher = FileWatcher(
            watch_dirs=[backend_src],
            extensions=[".py"],
            callback=lambda changed: backend_mgr.restart(),
            debounce=1.0,
        )
        backend_watcher.start()
        watchers.append(backend_watcher)

        # Watch frontend source files — rebuild + restart backend
        frontend_src = os.path.join(FRONTEND, "src")

        def on_frontend_change(changed):
            print("Frontend source changed, rebuilding...")
            try:
                build_frontend(tools)
                backend_mgr.restart()
            except subprocess.CalledProcessError:
                print("Frontend build failed, skipping restart.")

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
        )
        frontend_watcher.start()
        watchers.append(frontend_watcher)

        print("Watching backend and frontend for changes...")

        try:
            backend_mgr.wait()
        except KeyboardInterrupt:
            print("\nShutting down...")
            backend_mgr.terminate()
        finally:
            terminate_process(seaweedfs_proc)
            for w in watchers:
                w.stop()
