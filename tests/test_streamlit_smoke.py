from pathlib import Path

import httpx
from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).parent.parent / "demo" / "streamlit_app.py"


def make_app() -> AppTest:
    return AppTest.from_file(str(APP_PATH), default_timeout=20)


def test_streamlit_demo_file_exists_and_compiles() -> None:
    assert APP_PATH.exists()
    compile(APP_PATH.read_text("utf-8"), APP_PATH.name, "exec")


def test_streamlit_shows_backend_error_when_api_is_offline() -> None:
    app = make_app()
    app.run()

    assert app.text_input[1].label == "Backend URL"
    assert app.button[0].label == "Обработать объявление"

    app.text_input[1].set_value("http://127.0.0.1:65530")
    app.run()
    app.text_area[0].set_value("Отдельно выполняем сантехнические работы.")
    app.run()
    app.button[0].click()
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
                    {"mcId": 101, "mcTitle": "Сантехника", "text": "Draft A"},
                    {"mcId": 102, "mcTitle": "Электрика", "text": "Draft B"},
                ],
            },
        )

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(httpx, "post", fake_post)

    app = make_app()
    app.run()

    assert app.selectbox[0].label == "Select a scenario:"
    assert app.button[1].label == "Подставить кейс"

    app.selectbox[0].select("Отдельные услуги (со split на 2 категории)")
    app.run()
    app.button[1].click()
    app.run()

    assert app.text_area[0].value == "Отдельно выполняем сантехнические и электромонтажные работы."

    app.button[0].click()
    app.run()

    assert not app.exception
    assert app.success
    assert "100% совпадение" in app.success[0].value
    assert len(app.json) == 1
