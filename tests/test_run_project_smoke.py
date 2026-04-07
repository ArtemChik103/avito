from pathlib import Path
import importlib.util
import socket


def test_run_project_script_exists_and_compiles() -> None:
    script_path = Path(__file__).parent.parent / "run_project.py"
    assert script_path.exists()
    compile(script_path.read_text(encoding="utf-8"), script_path.name, "exec")


def test_run_project_normalizes_demo_args() -> None:
    script_path = Path(__file__).parent.parent / "run_project.py"
    spec = importlib.util.spec_from_file_location("run_project", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module._normalize_cli_args([]) == ["demo"]
    assert module._normalize_cli_args(["--no-browser"]) == ["demo", "--no-browser"]
    assert module._normalize_cli_args(["report"]) == ["report"]
    assert module._normalize_cli_args(["public", "--no-browser"]) == ["public", "--no-browser"]


def test_run_project_parser_accepts_public_command() -> None:
    script_path = Path(__file__).parent.parent / "run_project.py"
    spec = importlib.util.spec_from_file_location("run_project", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    args = module.build_parser().parse_args(["public", "--backend-port", "8100", "--frontend-port", "8600"])
    assert args.command == "public"
    assert args.backend_port == 8100
    assert args.frontend_port == 8600


def test_run_project_picks_next_free_port() -> None:
    script_path = Path(__file__).parent.parent / "run_project.py"
    spec = importlib.util.spec_from_file_location("run_project", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        busy_port = sock.getsockname()[1]
        next_port = module._find_available_port("127.0.0.1", busy_port, search_limit=5)
        assert next_port != busy_port


def test_run_project_accepts_explicit_ngrok_path(tmp_path: Path) -> None:
    script_path = Path(__file__).parent.parent / "run_project.py"
    spec = importlib.util.spec_from_file_location("run_project", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    fake_ngrok = tmp_path / "ngrok.exe"
    fake_ngrok.write_text("", encoding="utf-8")

    assert module._find_ngrok_path(str(fake_ngrok)) == str(fake_ngrok)


def test_run_project_loads_local_ngrok_token(tmp_path: Path) -> None:
    script_path = Path(__file__).parent.parent / "run_project.py"
    spec = importlib.util.spec_from_file_location("run_project", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    env_path = tmp_path / ".avito.local.env"
    env_path.write_text("NGROK_AUTHTOKEN=test-token\nOTHER=value\n", encoding="utf-8")

    values = module._load_local_env_file(env_path)
    assert values["NGROK_AUTHTOKEN"] == "test-token"
