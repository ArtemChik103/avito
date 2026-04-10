from pathlib import Path


def test_run_project_bat_exists_and_points_to_python_launcher() -> None:
    script_path = Path(__file__).parent.parent / "run_project.bat"
    assert script_path.exists()

    content = script_path.read_text(encoding="utf-8").lower()
    assert "python run_project.py %*" in content


def test_start_demo_bat_exists_and_points_to_demo_launcher() -> None:
    script_path = Path(__file__).parent.parent / "start_demo.bat"
    assert script_path.exists()

    content = script_path.read_text(encoding="utf-8").lower()
    assert "python run_project.py demo" in content


def test_start_public_demo_bat_exists_and_points_to_public_launcher() -> None:
    script_path = Path(__file__).parent.parent / "start_public_demo.bat"
    assert script_path.exists()

    content = script_path.read_text(encoding="utf-8").lower()
    assert "python run_project.py public" in content
