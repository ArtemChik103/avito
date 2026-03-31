from __future__ import annotations

import argparse
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

from src.avito_splitter.case_report import build_case_report, format_case_report

ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = build_parser()
    args = parser.parse_args(_normalize_cli_args(sys.argv[1:]))

    if args.command == "demo":
        return run_demo(args)
    if args.command == "backend":
        return run_backend(args)
    if args.command == "frontend":
        return run_frontend(args)
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

    subparsers.add_parser("report", help="Print report for all case files.")
    subparsers.add_parser("test", help="Run pytest.")

    parser.set_defaults(command="demo")
    return parser


def _normalize_cli_args(argv: list[str]) -> list[str]:
    if not argv:
        return ["demo"]

    known_commands = {"demo", "backend", "frontend", "report", "test"}
    if argv[0] in known_commands:
        return argv

    if argv[0].startswith("-"):
        return ["demo", *argv]

    return argv


def run_demo(args: argparse.Namespace) -> int:
    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "src.avito_splitter.api:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(args.backend_port),
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
        str(args.frontend_port),
        "--server.headless",
        "true",
    ]

    backend = subprocess.Popen(backend_cmd, cwd=ROOT)
    frontend = None
    try:
        _wait_for_url(f"http://127.0.0.1:{args.backend_port}/health", "backend")
        frontend = subprocess.Popen(frontend_cmd, cwd=ROOT)
        _wait_for_url(f"http://127.0.0.1:{args.frontend_port}/_stcore/health", "streamlit")

        frontend_url = f"http://127.0.0.1:{args.frontend_port}"
        docs_url = f"http://127.0.0.1:{args.backend_port}/docs"
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
    return subprocess.call(command, cwd=ROOT)


def run_report() -> int:
    print(format_case_report(build_case_report()))
    return 0


def run_tests() -> int:
    return subprocess.call([sys.executable, "-m", "pytest"], cwd=ROOT)


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
