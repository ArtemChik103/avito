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
