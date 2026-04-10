from __future__ import annotations

import importlib.util
import socket
from pathlib import Path


def load_module():
    script_path = Path(__file__).parent.parent / "run_project.py"
    spec = importlib.util.spec_from_file_location("run_project", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, script_path


def test_run_project_script_exists_and_compiles() -> None:
    module, script_path = load_module()
    assert module
    assert script_path.exists()
    compile(script_path.read_text(encoding="utf-8"), script_path.name, "exec")


def test_run_project_normalizes_demo_args() -> None:
    module, _ = load_module()

    assert module._normalize_cli_args([]) == ["demo"]
    assert module._normalize_cli_args(["--no-browser"]) == ["demo", "--no-browser"]
    assert module._normalize_cli_args(["report"]) == ["report"]
    assert module._normalize_cli_args(["public", "--no-browser"]) == ["public", "--no-browser"]


def test_run_project_parser_accepts_public_command() -> None:
    module, _ = load_module()

    args = module.build_parser().parse_args(["public", "--backend-port", "8100", "--frontend-port", "8600"])
    assert args.command == "public"
    assert args.backend_port == 8100
    assert args.frontend_port == 8600


def test_run_project_parser_accepts_frontend_backend_url() -> None:
    module, _ = load_module()

    args = module.build_parser().parse_args(["frontend", "--port", "8600", "--backend-url", "http://127.0.0.1:8999"])
    assert args.command == "frontend"
    assert args.port == 8600
    assert args.backend_url == "http://127.0.0.1:8999"


def test_run_project_picks_next_free_port() -> None:
    module, _ = load_module()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        busy_port = sock.getsockname()[1]
        next_port = module._find_available_port("127.0.0.1", busy_port, search_limit=5)
        assert next_port != busy_port


def test_run_project_extracts_gradio_public_link() -> None:
    module, _ = load_module()

    line = "Running on public URL: https://1234abcd.gradio.live"
    assert module.extract_gradio_public_url(line) == "https://1234abcd.gradio.live"


def test_run_project_builds_gradio_env() -> None:
    module, _ = load_module()

    env = module._build_frontend_env(
        backend_url="http://127.0.0.1:8123",
        frontend_port=7865,
        share=True,
    )

    assert env["AVITO_BACKEND_URL"] == "http://127.0.0.1:8123"
    assert env["AVITO_GRADIO_SHARE"] == "true"
    assert env["AVITO_GRADIO_SERVER_NAME"] == "127.0.0.1"
    assert env["AVITO_GRADIO_SERVER_PORT"] == "7865"
