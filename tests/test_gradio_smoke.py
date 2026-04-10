from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import httpx

APP_PATH = Path(__file__).parent.parent / "demo" / "gradio_app.py"


def load_module():
    spec = importlib.util.spec_from_file_location("gradio_app", APP_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_gradio_demo_file_exists_and_compiles() -> None:
    assert APP_PATH.exists()
    compile(APP_PATH.read_text("utf-8"), APP_PATH.name, "exec")


def test_gradio_loads_demo_cases_and_microcategories() -> None:
    module = load_module()

    cases = module.load_demo_cases()
    categories = module.load_microcategories()

    assert cases
    assert cases[0]["label"]
    assert categories
    assert categories[0]["mcTitle"]


def test_gradio_prepare_demo_case_prefills_expected_state() -> None:
    module = load_module()

    result = module.prepare_demo_case("Отдельные услуги")

    assert result.item_id == 1002
    assert result.mc_title == "Ремонт квартир и домов под ключ"
    assert result.mc_id_preview == "101"
    assert "электромонтажные работы" in result.description
    assert result.expected_result == {"shouldSplit": True, "draftMcIds": [102, 103]}


def test_gradio_submit_builds_correct_http_payload(monkeypatch) -> None:
    module = load_module()
    captured: dict[str, object] = {}

    def fake_get(url: str, timeout: float) -> httpx.Response:
        assert url.endswith("/health")
        return httpx.Response(200, request=httpx.Request("GET", url), json={"status": "ok"})

    def fake_post(url: str, json: dict, timeout: float) -> httpx.Response:
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={"shouldSplit": False, "drafts": []},
        )

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(httpx, "post", fake_post)

    result = module.submit_split_request(
        backend_url="http://127.0.0.1:8000",
        item_id=1002,
        mc_title="Ремонт квартир и домов под ключ",
        description="Отдельно выполняем сантехнические и электромонтажные работы.",
        selected_case_item=None,
        expected_result=None,
    )

    assert captured["url"] == "http://127.0.0.1:8000/split"
    assert captured["json"] == {
        "itemId": 1002,
        "mcId": 101,
        "mcTitle": "Ремонт квартир и домов под ключ",
        "description": "Отдельно выполняем сантехнические и электромонтажные работы.",
    }
    assert result.raw_response == {"shouldSplit": False, "drafts": []}


def test_gradio_submit_handles_offline_backend(monkeypatch) -> None:
    module = load_module()

    def fake_get(url: str, timeout: float) -> httpx.Response:
        raise httpx.RequestError("offline", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)

    result = module.submit_split_request(
        backend_url="http://127.0.0.1:65530",
        item_id=1002,
        mc_title="Ремонт квартир и домов под ключ",
        description="Отдельно выполняем сантехнические работы.",
        selected_case_item=None,
        expected_result=None,
    )

    assert "Backend недоступен" in result.error_markdown
    assert result.raw_response is None


def test_gradio_submit_renders_success_and_raw_json(monkeypatch) -> None:
    module = load_module()

    def fake_get(url: str, timeout: float) -> httpx.Response:
        return httpx.Response(200, request=httpx.Request("GET", url), json={"status": "ok"})

    def fake_post(url: str, json: dict, timeout: float) -> httpx.Response:
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "shouldSplit": True,
                "drafts": [
                    {"mcId": 102, "mcTitle": "Сантехника", "text": "Draft A"},
                    {"mcId": 103, "mcTitle": "Электрика", "text": "Draft B"},
                ],
            },
        )

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(httpx, "post", fake_post)

    result = module.submit_split_request(
        backend_url="http://127.0.0.1:8000",
        item_id=1002,
        mc_title="Ремонт квартир и домов под ключ",
        description="Отдельно выполняем сантехнические и электромонтажные работы.",
        selected_case_item={
            "itemId": 1002,
            "mcId": 101,
            "mcTitle": "Ремонт квартир и домов под ключ",
            "description": "Отдельно выполняем сантехнические и электромонтажные работы.",
        },
        expected_result={"shouldSplit": True, "draftMcIds": [102, 103]},
    )

    assert "shouldSplit = true" in result.verdict_html
    assert "Сантехника" in result.drafts_html
    assert "100% совпадение" in result.comparison_markdown
    assert result.raw_response == {
        "shouldSplit": True,
        "drafts": [
            {"mcId": 102, "mcTitle": "Сантехника", "text": "Draft A"},
            {"mcId": 103, "mcTitle": "Электрика", "text": "Draft B"},
        ],
    }
