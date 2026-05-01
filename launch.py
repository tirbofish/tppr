import subprocess
import sys
import os
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.join(ROOT, "frontend")
BACKEND = os.path.join(ROOT, "backend")


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
    args = [sys.executable, "src/main.py"]
    if api_only:
        args.append("--api-only")
    return subprocess.Popen(args, cwd=BACKEND)


def run_frontend_dev(js_runtime):
    runner = "bun" if "bun" in js_runtime else "npm"
    return subprocess.Popen([runner, "run", "dev"], cwd=FRONTEND)


if __name__ == "__main__":
    js_runtime = check_dependencies()

    if "--split" in sys.argv:
        print("Starting backend (API-only)...")
        backend_proc = run_backend(api_only=True)
        print("Starting frontend dev server...")
        frontend_proc = run_frontend_dev(js_runtime)

        try:
            backend_proc.wait()
            frontend_proc.wait()
        except KeyboardInterrupt:
            backend_proc.terminate()
            frontend_proc.terminate()
    else:
        build_frontend(js_runtime)
        print("Starting backend...")
        run_backend().wait()