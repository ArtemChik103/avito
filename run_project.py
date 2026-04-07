from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import webbrowser
from pathlib import Path
from shutil import which

from src.avito_splitter.case_report import build_case_report, format_case_report

ROOT = Path(__file__).resolve().parent
LOCAL_ENV_PATH = ROOT / ".avito.local.env"
DEFAULT_NGROK_PATHS = (
    Path.home() / "AppData/Local/Programs/ngrok/ngrok.exe",
    Path(os.environ.get("ProgramFiles", "")) / "ngrok/ngrok.exe",
)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args(_normalize_cli_args(sys.argv[1:]))

    if args.command == "demo":
        return run_demo(args)
    if args.command == "backend":
        return run_backend(args)
    if args.command == "frontend":
        return run_frontend(args)
    if args.command == "public":
        return run_public_demo(args)
    if args.command == "report":
        return run_report()
    if args.command == "test":
        return run_tests()

    parser.error(f"Unknown command: {args.command}")
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Simple launcher for Avito Services Splitter.",
    )
    subparsers = parser.add_subparsers(dest="command")

    demo_parser = subparsers.add_parser("demo", help="Run backend and Streamlit demo together.")
    demo_parser.add_argument("--backend-port", type=int, default=8000)
    demo_parser.add_argument("--frontend-port", type=int, default=8501)
    demo_parser.add_argument("--no-browser", action="store_true")

    backend_parser = subparsers.add_parser("backend", help="Run only FastAPI backend.")
    backend_parser.add_argument("--port", type=int, default=8000)

    frontend_parser = subparsers.add_parser("frontend", help="Run only Streamlit frontend.")
    frontend_parser.add_argument("--port", type=int, default=8501)

    public_parser = subparsers.add_parser("public", help="Run demo and expose it through ngrok.")
    public_parser.add_argument("--backend-port", type=int, default=8000)
    public_parser.add_argument("--frontend-port", type=int, default=8501)
    public_parser.add_argument("--ngrok-path", type=str, default=None)
    public_parser.add_argument("--ngrok-authtoken", type=str, default=None)
    public_parser.add_argument("--no-browser", action="store_true")

    subparsers.add_parser("report", help="Print report for all case files.")
    subparsers.add_parser("test", help="Run pytest.")

    parser.set_defaults(command="demo")
    return parser


def _normalize_cli_args(argv: list[str]) -> list[str]:
    if not argv:
        return ["demo"]

    known_commands = {"demo", "backend", "frontend", "public", "report", "test"}
    if argv[0] in known_commands:
        return argv

    if argv[0].startswith("-"):
        return ["demo", *argv]

    return argv


def run_demo(args: argparse.Namespace) -> int:
    backend_port = _find_available_port("127.0.0.1", args.backend_port)
    frontend_port = _find_available_port("127.0.0.1", args.frontend_port)
    backend_url = f"http://127.0.0.1:{backend_port}"

    if backend_port != args.backend_port:
        print(f"Port {args.backend_port} is busy, using backend port {backend_port}.")
    if frontend_port != args.frontend_port:
        print(f"Port {args.frontend_port} is busy, using frontend port {frontend_port}.")

    backend = None
    frontend = None
    try:
        backend, frontend = _start_demo_services(backend_port, frontend_port, backend_url=backend_url)

        frontend_url = f"http://127.0.0.1:{frontend_port}"
        docs_url = f"{backend_url}/docs"
        print(f"Backend docs: {docs_url}")
        print(f"Demo UI: {frontend_url}")
        print("Press Ctrl+C to stop both services.")

        if not args.no_browser:
            webbrowser.open(frontend_url)

        while True:
            if backend.poll() is not None:
                raise RuntimeError("Backend process exited unexpectedly.")
            if frontend.poll() is not None:
                raise RuntimeError("Streamlit process exited unexpectedly.")
            time.sleep(1)
    except KeyboardInterrupt:
        return 0
    finally:
        _terminate(frontend)
        _terminate(backend)


def run_public_demo(args: argparse.Namespace) -> int:
    backend_port = _find_available_port("127.0.0.1", args.backend_port)
    frontend_port = _find_available_port("127.0.0.1", args.frontend_port)
    backend_url = f"http://127.0.0.1:{backend_port}"
    ngrok_path = _find_ngrok_path(args.ngrok_path)
    ngrok_authtoken = _resolve_ngrok_authtoken(args.ngrok_authtoken)

    if backend_port != args.backend_port:
        print(f"Port {args.backend_port} is busy, using backend port {backend_port}.")
    if frontend_port != args.frontend_port:
        print(f"Port {args.frontend_port} is busy, using frontend port {frontend_port}.")

    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    ngrok_config: Path | None = None
    backend = None
    frontend = None
    ngrok_frontend = None
    try:
        if ngrok_authtoken:
            temp_dir = tempfile.TemporaryDirectory(prefix="avito-ngrok-")
            ngrok_config = _create_ngrok_config(ngrok_path, ngrok_authtoken, Path(temp_dir.name))

        backend, frontend = _start_demo_services(backend_port, frontend_port, backend_url=backend_url)

        ngrok_frontend = _start_ngrok_tunnel(
            ngrok_path=ngrok_path,
            local_port=frontend_port,
            label="frontend",
            config_path=ngrok_config,
        )
        public_frontend_url = _wait_for_ngrok_public_url(ngrok_frontend, "frontend tunnel")

        print(f"Local backend docs: {backend_url}/docs")
        print(f"Local demo UI: http://127.0.0.1:{frontend_port}")
        print(f"Public demo UI: {public_frontend_url}")
        print("Share the public demo URL with experts. Press Ctrl+C to stop everything.")

        if not args.no_browser:
            webbrowser.open(public_frontend_url)

        while True:
            if backend.poll() is not None:
                raise RuntimeError("Backend process exited unexpectedly.")
            if frontend.poll() is not None:
                raise RuntimeError("Streamlit process exited unexpectedly.")
            if ngrok_frontend.poll() is not None:
                raise RuntimeError("ngrok frontend tunnel exited unexpectedly.")
            time.sleep(1)
    except KeyboardInterrupt:
        return 0
    finally:
        _terminate(ngrok_frontend)
        _terminate(frontend)
        _terminate(backend)
        if temp_dir is not None:
            temp_dir.cleanup()


def run_backend(args: argparse.Namespace) -> int:
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "src.avito_splitter.api:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(args.port),
    ]
    return subprocess.call(command, cwd=ROOT)


def run_frontend(args: argparse.Namespace) -> int:
    env = os.environ.copy()
    env.setdefault("AVITO_BACKEND_URL", "http://127.0.0.1:8000")
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "demo/streamlit_app.py",
        "--server.address",
        "127.0.0.1",
        "--server.port",
        str(args.port),
    ]
    return subprocess.call(command, cwd=ROOT, env=env)


def run_report() -> int:
    print(format_case_report(build_case_report()))
    return 0


def run_tests() -> int:
    return subprocess.call([sys.executable, "-m", "pytest"], cwd=ROOT)


def _start_demo_services(
    backend_port: int,
    frontend_port: int,
    backend_url: str,
) -> tuple[subprocess.Popen, subprocess.Popen]:
    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "src.avito_splitter.api:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(backend_port),
    ]
    frontend_cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "demo/streamlit_app.py",
        "--server.address",
        "127.0.0.1",
        "--server.port",
        str(frontend_port),
        "--server.headless",
        "true",
    ]
    backend = subprocess.Popen(backend_cmd, cwd=ROOT)
    try:
        _wait_for_url(f"{backend_url}/health", "backend")
        frontend_env = os.environ.copy()
        frontend_env["AVITO_BACKEND_URL"] = backend_url
        frontend = subprocess.Popen(frontend_cmd, cwd=ROOT, env=frontend_env)
        try:
            _wait_for_url(f"http://127.0.0.1:{frontend_port}/_stcore/health", "streamlit")
        except Exception:
            _terminate(frontend)
            raise
        return backend, frontend
    except Exception:
        _terminate(backend)
        raise


def _wait_for_url(url: str, label: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status < 500:
                    return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for {label} at {url}")


def _wait_for_ngrok_public_url(process: subprocess.Popen, label: str, timeout: float = 30.0) -> str:
    deadline = time.time() + timeout
    if process.stdout is None:
        raise RuntimeError(f"Cannot read ngrok logs for {label}")

    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"ngrok exited before {label} became ready")
        line = process.stdout.readline()
        if not line:
            time.sleep(0.2)
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        public_url = str(payload.get("url", ""))
        if public_url.startswith("https://"):
            return public_url
        msg = str(payload.get("msg", ""))
        if msg == "started tunnel":
            nested_url = str(payload.get("obj", {}).get("url", ""))
            if nested_url.startswith("https://"):
                return nested_url
        if payload.get("lvl") == "eror":
            err = str(payload.get("err", "")).strip()
            if err:
                raise RuntimeError(f"{label} failed: {err}")
    raise RuntimeError(f"Timed out waiting for {label}")


def _find_available_port(host: str, preferred_port: int, search_limit: int = 20) -> int:
    for port in range(preferred_port, preferred_port + search_limit):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"Could not find available port starting from {preferred_port}")


def _find_ngrok_path(custom_path: str | None = None) -> str:
    if custom_path:
        path = Path(custom_path)
        if path.exists():
            return str(path)
        raise RuntimeError(f"ngrok executable not found at {custom_path}")

    resolved = which("ngrok")
    if resolved:
        return resolved

    for candidate in DEFAULT_NGROK_PATHS:
        if candidate.exists():
            return str(candidate)

    raise RuntimeError(
        "ngrok executable not found. Install ngrok or pass --ngrok-path / set it in PATH."
    )


def _resolve_ngrok_authtoken(explicit_token: str | None) -> str | None:
    if explicit_token:
        return explicit_token

    env_token = os.environ.get("NGROK_AUTHTOKEN")
    if env_token:
        return env_token

    local_env = _load_local_env_file(LOCAL_ENV_PATH)
    return local_env.get("NGROK_AUTHTOKEN")


def _load_local_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _create_ngrok_config(ngrok_path: str, authtoken: str, temp_dir: Path) -> Path:
    config_path = temp_dir / "ngrok.yml"
    command = [ngrok_path, "config", "add-authtoken", authtoken, "--config", str(config_path)]
    subprocess.run(command, check=True, cwd=ROOT, capture_output=True, text=True)
    return config_path


def _start_ngrok_tunnel(
    ngrok_path: str,
    local_port: int,
    label: str,
    config_path: Path | None,
) -> subprocess.Popen:
    command = [
        ngrok_path,
        "http",
        str(local_port),
        "--name",
        label,
        "--log",
        "stdout",
        "--log-format",
        "json",
    ]
    if config_path is not None:
        command.extend(["--config", str(config_path)])
    return subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _terminate(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
