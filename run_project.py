from __future__ import annotations

import argparse
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

from src.avito_splitter.case_report import build_case_report, format_case_report

ROOT = Path(__file__).resolve().parent
DEFAULT_BACKEND_HOST = "127.0.0.1"
DEFAULT_FRONTEND_HOST = "127.0.0.1"
DEFAULT_BACKEND_PORT = 8000
DEFAULT_FRONTEND_PORT = 7860


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

    demo_parser = subparsers.add_parser("demo", help="Run backend and local Gradio demo together.")
    demo_parser.add_argument("--backend-port", type=int, default=DEFAULT_BACKEND_PORT)
    demo_parser.add_argument("--frontend-port", type=int, default=DEFAULT_FRONTEND_PORT)
    demo_parser.add_argument("--no-browser", action="store_true")

    backend_parser = subparsers.add_parser("backend", help="Run only FastAPI backend.")
    backend_parser.add_argument("--port", type=int, default=DEFAULT_BACKEND_PORT)

    frontend_parser = subparsers.add_parser("frontend", help="Run only local Gradio frontend.")
    frontend_parser.add_argument("--port", type=int, default=DEFAULT_FRONTEND_PORT)
    frontend_parser.add_argument("--backend-url", type=str, default=f"http://{DEFAULT_BACKEND_HOST}:{DEFAULT_BACKEND_PORT}")

    public_parser = subparsers.add_parser("public", help="Run backend and Gradio demo with share=True.")
    public_parser.add_argument("--backend-port", type=int, default=DEFAULT_BACKEND_PORT)
    public_parser.add_argument("--frontend-port", type=int, default=DEFAULT_FRONTEND_PORT)
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
    backend_port = _find_available_port(DEFAULT_BACKEND_HOST, args.backend_port)
    frontend_port = _find_available_port(DEFAULT_FRONTEND_HOST, args.frontend_port)
    backend_url = f"http://{DEFAULT_BACKEND_HOST}:{backend_port}"
    frontend_url = f"http://{DEFAULT_FRONTEND_HOST}:{frontend_port}"

    if backend_port != args.backend_port:
        print(f"Port {args.backend_port} is busy, using backend port {backend_port}.")
    if frontend_port != args.frontend_port:
        print(f"Port {args.frontend_port} is busy, using frontend port {frontend_port}.")

    backend = None
    frontend = None
    try:
        backend, frontend = _start_demo_services(
            backend_port=backend_port,
            frontend_port=frontend_port,
            backend_url=backend_url,
            share=False,
        )

        print(f"Backend docs: {backend_url}/docs")
        print(f"Demo UI: {frontend_url}")
        print("Press Ctrl+C to stop both services.")

        if not args.no_browser:
            webbrowser.open(frontend_url)

        _wait_forever(backend=backend, frontend=frontend)
        return 0
    except KeyboardInterrupt:
        return 0
    finally:
        _terminate(frontend)
        _terminate(backend)


def run_public_demo(args: argparse.Namespace) -> int:
    backend_port = _find_available_port(DEFAULT_BACKEND_HOST, args.backend_port)
    frontend_port = _find_available_port(DEFAULT_FRONTEND_HOST, args.frontend_port)
    backend_url = f"http://{DEFAULT_BACKEND_HOST}:{backend_port}"
    frontend_url = f"http://{DEFAULT_FRONTEND_HOST}:{frontend_port}"

    if backend_port != args.backend_port:
        print(f"Port {args.backend_port} is busy, using backend port {backend_port}.")
    if frontend_port != args.frontend_port:
        print(f"Port {args.frontend_port} is busy, using frontend port {frontend_port}.")

    backend = None
    frontend = None
    try:
        backend, frontend = _start_demo_services(
            backend_port=backend_port,
            frontend_port=frontend_port,
            backend_url=backend_url,
            share=True,
            capture_frontend_output=True,
        )
        public_frontend_url = _wait_for_gradio_public_url(frontend, "gradio public URL")

        print(f"Local backend docs: {backend_url}/docs")
        print(f"Local demo UI: {frontend_url}")
        print(f"Public demo UI: {public_frontend_url}")
        print("Share the public demo URL while this process is running. Press Ctrl+C to stop everything.")

        if not args.no_browser:
            webbrowser.open(public_frontend_url)

        _wait_forever(backend=backend, frontend=frontend)
        return 0
    except KeyboardInterrupt:
        return 0
    finally:
        _terminate(frontend)
        _terminate(backend)


def run_backend(args: argparse.Namespace) -> int:
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "src.avito_splitter.api:app",
        "--host",
        DEFAULT_BACKEND_HOST,
        "--port",
        str(args.port),
    ]
    return subprocess.call(command, cwd=ROOT)


def run_frontend(args: argparse.Namespace) -> int:
    env = _build_frontend_env(
        backend_url=args.backend_url,
        frontend_port=args.port,
        share=False,
    )
    return subprocess.call(_build_frontend_command(), cwd=ROOT, env=env)


def run_report() -> int:
    print(format_case_report(build_case_report()))
    return 0


def run_tests() -> int:
    return subprocess.call([sys.executable, "-m", "pytest"], cwd=ROOT)


def _start_demo_services(
    backend_port: int,
    frontend_port: int,
    backend_url: str,
    share: bool,
    capture_frontend_output: bool = False,
) -> tuple[subprocess.Popen[str], subprocess.Popen[str]]:
    backend = subprocess.Popen(_build_backend_command(backend_port), cwd=ROOT, text=True)
    try:
        _wait_for_url(f"{backend_url}/health", "backend")
        frontend = _start_frontend_process(
            backend_url=backend_url,
            frontend_port=frontend_port,
            share=share,
            capture_output=capture_frontend_output,
        )
        try:
            _wait_for_url(f"http://{DEFAULT_FRONTEND_HOST}:{frontend_port}/", "gradio frontend")
        except Exception:
            _terminate(frontend)
            raise
        return backend, frontend
    except Exception:
        _terminate(backend)
        raise


def _build_backend_command(port: int) -> list[str]:
    return [
        sys.executable,
        "-m",
        "uvicorn",
        "src.avito_splitter.api:app",
        "--host",
        DEFAULT_BACKEND_HOST,
        "--port",
        str(port),
    ]


def _build_frontend_command() -> list[str]:
    return [
        sys.executable,
        "-u",
        "demo/gradio_app.py",
    ]


def _build_frontend_env(backend_url: str, frontend_port: int, share: bool) -> dict[str, str]:
    env = os.environ.copy()
    env["AVITO_BACKEND_URL"] = backend_url
    env["AVITO_GRADIO_SHARE"] = "true" if share else "false"
    env["AVITO_GRADIO_SERVER_NAME"] = DEFAULT_FRONTEND_HOST
    env["AVITO_GRADIO_SERVER_PORT"] = str(frontend_port)
    env["PYTHONUNBUFFERED"] = "1"
    return env


def _start_frontend_process(
    backend_url: str,
    frontend_port: int,
    share: bool,
    capture_output: bool,
) -> subprocess.Popen[str]:
    kwargs: dict[str, object] = {
        "cwd": ROOT,
        "env": _build_frontend_env(backend_url=backend_url, frontend_port=frontend_port, share=share),
        "text": True,
    }
    if capture_output:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.STDOUT
        kwargs["bufsize"] = 1
    return subprocess.Popen(_build_frontend_command(), **kwargs)  # type: ignore[arg-type]


def _wait_forever(backend: subprocess.Popen[str], frontend: subprocess.Popen[str]) -> None:
    while True:
        if backend.poll() is not None:
            raise RuntimeError("Backend process exited unexpectedly.")
        if frontend.poll() is not None:
            raise RuntimeError("Gradio process exited unexpectedly.")
        time.sleep(1)


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


def extract_gradio_public_url(text: str) -> str | None:
    match = re.search(r"https://[a-zA-Z0-9.-]+\.gradio\.live(?:/\S*)?", text)
    if match:
        return match.group(0)
    return None


def _wait_for_gradio_public_url(
    process: subprocess.Popen[str],
    label: str,
    timeout: float = 60.0,
) -> str:
    if process.stdout is None:
        raise RuntimeError(f"Cannot read stdout for {label}")

    deadline = time.time() + timeout
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Frontend exited before {label} became ready")

        line = process.stdout.readline()
        if not line:
            time.sleep(0.2)
            continue

        public_url = extract_gradio_public_url(line)
        if public_url:
            return public_url

        lowered = line.lower()
        if "could not create share link" in lowered:
            raise RuntimeError(line.strip())

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


def _terminate(process: subprocess.Popen[str] | None) -> None:
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
