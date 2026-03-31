from pathlib import Path


def test_run_project_bat_exists_and_points_to_python_launcher() -> None:
    script_path = Path(__file__).parent.parent / "run_project.bat"
    assert script_path.exists()

    content = script_path.read_text(encoding="utf-8").lower()
    assert "python run_project.py %*" in content
