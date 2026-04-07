from pathlib import Path

import httpx
from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).parent.parent / "demo" / "streamlit_app.py"


def make_app() -> AppTest:
    return AppTest.from_file(str(APP_PATH), default_timeout=20)


def find_by_label(elements, label: str):
    for element in elements:
        if getattr(element, "label", None) == label:
            return element
    raise AssertionError(f"Element with label {label!r} not found")


def test_streamlit_demo_file_exists_and_compiles() -> None:
    assert APP_PATH.exists()
    compile(APP_PATH.read_text("utf-8"), APP_PATH.name, "exec")


def test_streamlit_shows_backend_error_when_api_is_offline() -> None:
    app = make_app()
    app.run()

    assert find_by_label(app.text_input, "URL backend")
    assert find_by_label(app.button, "Обработать объявление")

    find_by_label(app.text_input, "URL backend").set_value("http://127.0.0.1:65530")
    app.run()
    app.text_area[0].set_value("Отдельно выполняем сантехнические работы.")
    app.run()
    find_by_label(app.button, "Обработать объявление").click()
    app.run()

    assert not app.exception
    assert app.error
    assert "Backend недоступен" in app.error[0].value


def test_streamlit_loads_demo_case_and_renders_happy_path(monkeypatch) -> None:
    def fake_get(url: str, timeout: float) -> httpx.Response:
        assert url.endswith("/health")
        return httpx.Response(200, request=httpx.Request("GET", url), json={"status": "ok"})

    def fake_post(url: str, json: dict, timeout: float) -> httpx.Response:
        assert url.endswith("/split")
        assert json["description"] == "Отдельно выполняем сантехнические и электромонтажные работы."
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

    app = make_app()
    app.run()

    assert find_by_label(app.selectbox, "Сценарий")
    assert find_by_label(app.button, "Подставить кейс")
    assert find_by_label(app.selectbox, "Микрокатегория")

    find_by_label(app.selectbox, "Сценарий").select("Отдельные услуги")
    app.run()
    find_by_label(app.button, "Подставить кейс").click()
    app.run()

    assert app.text_area[0].value == "Отдельно выполняем сантехнические и электромонтажные работы."

    find_by_label(app.button, "Обработать объявление").click()
    app.run()

    assert not app.exception
    assert app.success
    assert "100% совпадение" in app.success[0].value
    assert len(app.json) == 1
