from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")
sync_playwright = playwright.sync_playwright
expect = playwright.expect

ROOT = Path(__file__).resolve().parents[1]


def _load_run_project_module():
    import importlib.util

    script_path = ROOT / "run_project.py"
    spec = importlib.util.spec_from_file_location("run_project", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _find_chrome_executable() -> Path | None:
    candidates = [
        os.getenv("PLAYWRIGHT_CHROME_PATH"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        Path.home() / "AppData/Local/Google/Chrome/Application/chrome.exe",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if path.exists():
            return path
    return None


@pytest.fixture(scope="module")
def live_demo_urls():
    chrome_path = _find_chrome_executable()
    if chrome_path is None:
        pytest.skip("Google Chrome is not installed")

    module = _load_run_project_module()
    backend_port = module._find_available_port("127.0.0.1", 8010)
    frontend_port = module._find_available_port("127.0.0.1", 8510)
    backend_url = f"http://127.0.0.1:{backend_port}"
    frontend_url = f"http://127.0.0.1:{frontend_port}"

    backend = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "src.avito_splitter.api:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(backend_port),
        ],
        cwd=ROOT,
    )

    frontend = None
    try:
        module._wait_for_url(f"{backend_url}/health", "backend")
        env = os.environ.copy()
        env["AVITO_BACKEND_URL"] = backend_url
        frontend = subprocess.Popen(
            [
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
            ],
            cwd=ROOT,
            env=env,
        )
        module._wait_for_url(f"{frontend_url}/_stcore/health", "streamlit")
        yield frontend_url, chrome_path
    finally:
        module._terminate(frontend)
        module._terminate(backend)


def test_playwright_smoke_for_demo_ui(live_demo_urls) -> None:
    frontend_url, chrome_path = live_demo_urls

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(chrome_path), headless=True)
        page = browser.new_page()
        page.goto(frontend_url, wait_until="networkidle")

        _select_streamlit_option(page, "Сценарий", "Отдельные услуги")
        page.get_by_role("button", name="Подставить кейс").click()

        description = page.get_by_label("Описание")
        expect(description).to_have_value("Отдельно выполняем сантехнические и электромонтажные работы.")
        expect_category = page.get_by_label("Микрокатегория")
        expect(expect_category).to_have_attribute(
            "aria-label",
            "Selected Ремонт квартир и домов под ключ. Микрокатегория",
        )
        expect(page.get_by_text("ID выбранной микрокатегории: 101")).to_be_visible()

        _select_streamlit_option(page, "Микрокатегория", "Сантехника")
        expect(page.get_by_text("ID выбранной микрокатегории: 102")).to_be_visible()

        _select_streamlit_option(page, "Микрокатегория", "Ремонт квартир и домов под ключ")
        page.get_by_role("button", name="Обработать объявление").click()
        expect(page.get_by_text("shouldSplit = true")).to_be_visible()
        expect(page.get_by_text("Сантехника", exact=True).first).to_be_visible()
        expect(page.get_by_text("Электрика", exact=True).first).to_be_visible()
        expect(page.get_by_text("100% совпадение")).to_be_visible()

        browser.close()


def _select_streamlit_option(page, label: str, option_text: str) -> None:
    page.get_by_label(label).click()
    page.get_by_role("option", name=option_text, exact=True).click()
