import subprocess
import sys
import os
import shutil
import time
import threading

ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.join(ROOT, "frontend")
BACKEND = os.path.join(ROOT, "backend")

# NOTE: this was made fully with AI


def check_dependencies():
    missing = []

    if not shutil.which("uv"):
        missing.append("uv")

    npm = shutil.which("npm")
    bun = shutil.which("bun")
    if not npm and not bun:
        missing.append("npm or bun")

    if missing:
        print("Missing required tools: " + ", ".join(missing))
        sys.exit(1)

    return bun or npm  # prefer bun if available


def build_frontend(js_runtime):
    print("Building frontend...")
    runner = "bun" if "bun" in js_runtime else "npm"
    subprocess.run([runner, "run", "build"], cwd=FRONTEND, check=True)


def run_backend(api_only=False):
    args = ["uv", "run", "src/main.py"]
    if api_only:
        args.append("--api-only")
    return subprocess.Popen(args, cwd=BACKEND)


def run_frontend_dev(js_runtime):
    runner = "bun" if "bun" in js_runtime else "npm"
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
    js_runtime = check_dependencies()
    watchers = []

    if "--split" in sys.argv:
        # --- Split mode: backend API + frontend dev server ---
        print("Starting backend (API-only) with file watching...")
        backend_mgr = ProcessManager(lambda: run_backend(api_only=True))
        backend_mgr.start()

        print("Starting frontend dev server...")
        frontend_proc = run_frontend_dev(js_runtime)

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
            for w in watchers:
                w.stop()
    else:
        # --- Combined mode: build frontend + serve from backend ---
        build_frontend(js_runtime)
        print("Starting backend with file watching...")
        backend_mgr = ProcessManager(lambda: run_backend())
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
                build_frontend(js_runtime)
                backend_mgr.restart()
            except subprocess.CalledProcessError:
                print("Frontend build failed, skipping restart.")

        frontend_watcher = FileWatcher(
            watch_dirs=[frontend_src],
            extensions=[".ts", ".tsx", ".js", ".jsx",
                        ".vue", ".svelte", ".css", ".html"],
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
            for w in watchers:
                w.stop()
