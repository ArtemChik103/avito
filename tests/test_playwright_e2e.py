from __future__ import annotations

import os
import subprocess
import sys
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
    frontend_port = module._find_available_port("127.0.0.1", 7870)
    backend_url = f"http://127.0.0.1:{backend_port}"
    frontend_url = f"http://127.0.0.1:{frontend_port}"

    backend = subprocess.Popen(module._build_backend_command(backend_port), cwd=ROOT)
    frontend = None
    try:
        module._wait_for_url(f"{backend_url}/health", "backend")
        frontend = subprocess.Popen(
            module._build_frontend_command(),
            cwd=ROOT,
            env=module._build_frontend_env(
                backend_url=backend_url,
                frontend_port=frontend_port,
                share=False,
            ),
        )
        module._wait_for_url(f"{frontend_url}/", "gradio frontend")
        yield frontend_url, chrome_path
    finally:
        module._terminate(frontend)
        module._terminate(backend)


def test_playwright_smoke_for_demo_ui(live_demo_urls) -> None:
    frontend_url, chrome_path = live_demo_urls

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(chrome_path), headless=True)
        page = browser.new_page()
        page.goto(frontend_url, wait_until="domcontentloaded")
        expect(page.get_by_text("Avito Services Splitter")).to_be_visible()

        _select_gradio_dropdown(page, "demo-case-dropdown", "Отдельные услуги")
        page.locator("#apply-demo-case").click()

        description = page.locator("#description-input textarea")
        expect(description).to_have_value("Отдельно выполняем сантехнические и электромонтажные работы.")

        category_input = _dropdown_input(page, "microcategory-dropdown")
        expect(category_input).to_have_value("Ремонт квартир и домов под ключ")
        expect(_textbox_value_locator(page, "mcid-preview")).to_have_value("101")

        _select_gradio_dropdown(page, "microcategory-dropdown", "Сантехника")
        expect(_textbox_value_locator(page, "mcid-preview")).to_have_value("102")

        _select_gradio_dropdown(page, "microcategory-dropdown", "Ремонт квартир и домов под ключ")
        page.locator("#submit-ad").click()

        expect(page.locator("#verdict-card")).to_contain_text("shouldSplit = true")
        expect(page.locator("#drafts-list")).to_contain_text("Сантехника")
        expect(page.locator("#drafts-list")).to_contain_text("Электрика")
        expect(page.locator("#comparison-result")).to_contain_text("100% совпадение")

        browser.close()


def _dropdown_input(page, elem_id: str):
    return page.locator(f"#{elem_id} input").first


def _textbox_value_locator(page, elem_id: str):
    return page.locator(f"#{elem_id} textarea, #{elem_id} input").first


def _select_gradio_dropdown(page, elem_id: str, option_text: str) -> None:
    _dropdown_input(page, elem_id).click()
    page.get_by_role("option", name=option_text, exact=True).click()
