from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any

import gradio as gr
import httpx

APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
DEMO_CASES_PATH = APP_DIR / "demo_cases.json"
CATEGORY_CATALOG_PATH = ROOT_DIR / "data" / "microcategories.enriched.json"
DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"
DEFAULT_SERVER_NAME = "127.0.0.1"
DEFAULT_SERVER_PORT = 7860
HTTP_TIMEOUT = 10.0
HEALTH_TIMEOUT = 2.0

APP_CSS = """
:root {
    --page-bg: #0b1220;
    --panel-bg: rgba(15, 23, 42, 0.84);
    --panel-border: rgba(148, 163, 184, 0.18);
    --text-main: #e2e8f0;
    --text-muted: #94a3b8;
    --accent: #38bdf8;
    --success: #10b981;
    --warning: #f59e0b;
    --danger: #ef4444;
}

body, .gradio-container {
    background:
        radial-gradient(circle at top left, rgba(56, 189, 248, 0.14), transparent 32%),
        radial-gradient(circle at top right, rgba(14, 165, 233, 0.12), transparent 28%),
        linear-gradient(180deg, #07101d 0%, #0b1220 100%);
    color: var(--text-main);
}

.app-shell {
    max-width: 1180px;
    margin: 0 auto;
}

.hero {
    padding: 24px 28px;
    border: 1px solid var(--panel-border);
    border-radius: 20px;
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.92), rgba(30, 41, 59, 0.72));
    box-shadow: 0 24px 48px rgba(2, 8, 23, 0.36);
}

.hero h1 {
    margin: 0 0 8px;
    color: #f8fafc;
    font-size: 2.15rem;
}

.hero p {
    margin: 0;
    color: var(--text-muted);
    line-height: 1.6;
}

.panel {
    border: 1px solid var(--panel-border);
    border-radius: 18px;
    background: var(--panel-bg);
    box-shadow: 0 18px 42px rgba(2, 8, 23, 0.24);
}

.section-title {
    margin: 0 0 10px;
    color: #f8fafc;
    font-size: 1.05rem;
}

.status-pill {
    margin: 0;
    padding: 10px 14px;
    border-radius: 999px;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 8px;
}

.status-pill.online {
    color: #d1fae5;
    background: rgba(16, 185, 129, 0.14);
    border: 1px solid rgba(16, 185, 129, 0.28);
}

.status-pill.offline {
    color: #fee2e2;
    background: rgba(239, 68, 68, 0.14);
    border: 1px solid rgba(239, 68, 68, 0.24);
}

.notice {
    margin: 0;
    padding: 14px 16px;
    border-radius: 14px;
    line-height: 1.55;
}

.notice.error {
    color: #fee2e2;
    background: rgba(127, 29, 29, 0.5);
    border: 1px solid rgba(239, 68, 68, 0.28);
}

.notice.info {
    color: #dbeafe;
    background: rgba(30, 64, 175, 0.32);
    border: 1px solid rgba(96, 165, 250, 0.2);
}

.notice.success {
    color: #d1fae5;
    background: rgba(6, 95, 70, 0.42);
    border: 1px solid rgba(16, 185, 129, 0.28);
}

.notice.warning {
    color: #fef3c7;
    background: rgba(120, 53, 15, 0.42);
    border: 1px solid rgba(245, 158, 11, 0.24);
}

.result-card {
    padding: 18px 20px;
    border-radius: 18px;
    border: 1px solid rgba(148, 163, 184, 0.14);
    background: rgba(15, 23, 42, 0.88);
}

.result-card.success {
    border-left: 4px solid var(--success);
}

.result-card.neutral {
    border-left: 4px solid var(--text-muted);
}

.result-card h2 {
    margin: 0 0 6px;
    color: #f8fafc;
}

.result-card p {
    margin: 0;
    color: var(--text-muted);
}

.draft-grid {
    display: grid;
    gap: 14px;
}

.draft-card {
    padding: 16px 18px;
    border-radius: 16px;
    border: 1px solid rgba(56, 189, 248, 0.14);
    background: rgba(15, 23, 42, 0.88);
}

.draft-card h3 {
    margin: 0 0 4px;
    color: var(--accent);
}

.draft-card .meta {
    margin: 0 0 10px;
    color: var(--text-muted);
    font-size: 0.95rem;
}

.draft-card pre {
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
    color: var(--text-main);
    font-family: inherit;
}

#submit-ad button, #apply-demo-case button {
    min-height: 46px;
    font-weight: 700;
}
"""


@dataclass(frozen=True)
class CatalogIndex:
    titles: list[str]
    ids_by_title: dict[str, int]
    titles_by_id: dict[int, str]


@dataclass(frozen=True)
class PrefillViewModel:
    item_id: int
    mc_title: str
    mc_id_preview: str
    description: str
    selected_case_item: dict[str, Any] | None
    expected_result: dict[str, Any] | None
    current_form_item: dict[str, Any]
    error_markdown: str
    verdict_html: str
    drafts_html: str
    raw_response: dict[str, Any] | None
    comparison_markdown: str


@dataclass(frozen=True)
class SubmitViewModel:
    backend_status_markdown: str
    error_markdown: str
    verdict_html: str
    drafts_html: str
    raw_response: dict[str, Any] | None
    comparison_markdown: str
    current_form_item: dict[str, Any]


def load_demo_cases(path: Path = DEMO_CASES_PATH) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_microcategories(path: Path = CATEGORY_CATALOG_PATH) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_catalog_index(microcategories: list[dict[str, Any]]) -> CatalogIndex:
    titles = [entry["mcTitle"] for entry in microcategories]
    ids_by_title = {entry["mcTitle"]: int(entry["mcId"]) for entry in microcategories}
    titles_by_id = {int(entry["mcId"]): entry["mcTitle"] for entry in microcategories}
    return CatalogIndex(titles=titles, ids_by_title=ids_by_title, titles_by_id=titles_by_id)


DEMO_CASES = load_demo_cases()
DEMO_CASES_BY_LABEL = {case["label"]: case for case in DEMO_CASES}
DEFAULT_CASE_LABEL = DEMO_CASES[0]["label"] if DEMO_CASES else None
CATALOG_INDEX = build_catalog_index(load_microcategories())


def normalize_backend_url(raw_url: str | None) -> str:
    value = (raw_url or DEFAULT_BACKEND_URL).strip()
    return value.rstrip("/") or DEFAULT_BACKEND_URL


def render_backend_status(is_online: bool, detail: str | None = None) -> str:
    text = "Backend доступен" if is_online else "Backend недоступен"
    css_class = "online" if is_online else "offline"
    suffix = f" <span>{escape(detail)}</span>" if detail else ""
    return f'<p class="status-pill {css_class}"><span>{"●" if is_online else "○"}</span><span>{text}</span>{suffix}</p>'


def check_backend(backend_url: str, timeout: float = HEALTH_TIMEOUT) -> tuple[bool, str]:
    normalized = normalize_backend_url(backend_url)
    try:
        response = httpx.get(f"{normalized}/health", timeout=timeout)
    except httpx.ReadTimeout:
        return False, render_backend_status(False, "timeout")
    except httpx.RequestError:
        return False, render_backend_status(False, "ошибка сети")

    if response.status_code == 200:
        return True, render_backend_status(True)
    return False, render_backend_status(False, f"HTTP {response.status_code}")


def resolve_item(item: dict[str, Any]) -> dict[str, Any]:
    fallback_title = CATALOG_INDEX.titles[0] if CATALOG_INDEX.titles else ""
    mc_id = int(item["mcId"])
    mc_title = str(item["mcTitle"]).strip()
    if mc_title in CATALOG_INDEX.ids_by_title:
        mc_id = CATALOG_INDEX.ids_by_title[mc_title]
    else:
        mc_title = CATALOG_INDEX.titles_by_id.get(mc_id, fallback_title)
        mc_id = CATALOG_INDEX.ids_by_title.get(mc_title, mc_id)

    return {
        "itemId": int(item["itemId"]),
        "mcId": mc_id,
        "mcTitle": mc_title,
        "description": str(item["description"]),
    }


DEFAULT_FORM_ITEM = resolve_item(
    {
        "itemId": 1000,
        "mcId": 101,
        "mcTitle": "Ремонт квартир и домов под ключ",
        "description": "",
    }
)


def build_payload(item_id: int | float | None, mc_title: str, description: str) -> dict[str, Any]:
    normalized_title = str(mc_title).strip()
    if normalized_title not in CATALOG_INDEX.ids_by_title:
        raise ValueError("Выберите микрокатегорию из каталога.")

    normalized_description = str(description or "").strip()
    if not normalized_description:
        raise ValueError("Описание не может быть пустым.")

    try:
        normalized_item_id = int(item_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("Item ID должен быть целым числом.") from exc

    return {
        "itemId": normalized_item_id,
        "mcId": CATALOG_INDEX.ids_by_title[normalized_title],
        "mcTitle": normalized_title,
        "description": normalized_description,
    }


def get_mc_id_preview(mc_title: str) -> str:
    mc_id = CATALOG_INDEX.ids_by_title.get(str(mc_title).strip())
    return "" if mc_id is None else str(mc_id)


def format_expected_note(expected_result: dict[str, Any]) -> str:
    return (
        '<div class="notice info">'
        f"Эталон загружен: shouldSplit = {str(bool(expected_result['shouldSplit'])).lower()}, "
        f"draftMcIds = {expected_result['draftMcIds']}"
        "</div>"
    )


def render_error(message: str) -> str:
    return f'<div class="notice error">{escape(message)}</div>'


def render_comparison(
    payload: dict[str, Any],
    selected_case_item: dict[str, Any] | None,
    expected_result: dict[str, Any] | None,
    result: dict[str, Any] | None,
) -> str:
    if not selected_case_item or not expected_result:
        return ""

    if payload != selected_case_item:
        return '<div class="notice info">Эталон выбран, но текущая форма отличается от подставленного demo-case.</div>'

    if result is None:
        return format_expected_note(expected_result)

    actual_should_split = bool(result.get("shouldSplit"))
    actual_draft_ids = [int(draft["mcId"]) for draft in result.get("drafts", [])]
    expected_draft_ids = [int(value) for value in expected_result["draftMcIds"]]
    if actual_should_split == bool(expected_result["shouldSplit"]) and set(actual_draft_ids) == set(expected_draft_ids):
        return '<div class="notice success">Сверка с эталоном demo-case: 100% совпадение.</div>'

    return (
        '<div class="notice warning">'
        f"Несовпадение с эталоном. Ожидали shouldSplit = {str(bool(expected_result['shouldSplit'])).lower()}, "
        f"получили = {str(actual_should_split).lower()}. Ожидали draftMcIds = {expected_draft_ids}, "
        f"получили = {actual_draft_ids}."
        "</div>"
    )


def render_verdict(result: dict[str, Any]) -> str:
    should_split = bool(result.get("shouldSplit"))
    verdict_text = "Обнаружено несколько самостоятельных услуг." if should_split else "Объявление не нужно split-ить."
    css_class = "success" if should_split else "neutral"
    return (
        f'<div class="result-card {css_class}">'
        f"<h2>shouldSplit = {str(should_split).lower()}</h2>"
        f"<p>{escape(verdict_text)}</p>"
        "</div>"
    )


def render_drafts(result: dict[str, Any]) -> str:
    drafts = result.get("drafts", [])
    if not drafts:
        return '<div class="notice info">Черновики не созданы.</div>'

    cards = []
    for draft in drafts:
        cards.append(
            "<article class=\"draft-card\">"
            f"<h3>{escape(str(draft.get('mcTitle', 'Unknown')))}</h3>"
            f"<p class=\"meta\">mcId: {escape(str(draft.get('mcId', '')))}</p>"
            f"<pre>{escape(str(draft.get('text', '')))}</pre>"
            "</article>"
        )
    return f'<div class="draft-grid">{"".join(cards)}</div>'


def _extract_backend_error(response: httpx.Response) -> str:
    prefix = f"Backend вернул HTTP {response.status_code}."
    try:
        payload = response.json()
    except json.JSONDecodeError:
        return prefix

    if response.status_code == 422:
        return f"{prefix} Запрос не прошел валидацию."
    detail = payload.get("detail")
    if isinstance(detail, str) and detail.strip():
        return f"{prefix} {detail.strip()}"
    return prefix


def prepare_demo_case(case_label: str | None) -> PrefillViewModel:
    if not case_label or case_label not in DEMO_CASES_BY_LABEL:
        item = DEFAULT_FORM_ITEM
        return PrefillViewModel(
            item_id=item["itemId"],
            mc_title=item["mcTitle"],
            mc_id_preview=str(item["mcId"]),
            description=item["description"],
            selected_case_item=None,
            expected_result=None,
            current_form_item=item,
            error_markdown="",
            verdict_html="",
            drafts_html="",
            raw_response=None,
            comparison_markdown="",
        )

    case = DEMO_CASES_BY_LABEL[case_label]
    item = resolve_item(case["item"])
    expected_result = {
        "shouldSplit": bool(case["expectedShouldSplit"]),
        "draftMcIds": [int(value) for value in case["expectedDraftMcIds"]],
    }
    return PrefillViewModel(
        item_id=item["itemId"],
        mc_title=item["mcTitle"],
        mc_id_preview=str(item["mcId"]),
        description=item["description"],
        selected_case_item=item,
        expected_result=expected_result,
        current_form_item=item,
        error_markdown="",
        verdict_html="",
        drafts_html="",
        raw_response=None,
        comparison_markdown=format_expected_note(expected_result),
    )


def submit_split_request(
    backend_url: str,
    item_id: int | float | None,
    mc_title: str,
    description: str,
    selected_case_item: dict[str, Any] | None,
    expected_result: dict[str, Any] | None,
) -> SubmitViewModel:
    normalized_backend_url = normalize_backend_url(backend_url)
    is_online, backend_status_markdown = check_backend(normalized_backend_url)

    try:
        payload = build_payload(item_id=item_id, mc_title=mc_title, description=description)
    except ValueError as exc:
        return SubmitViewModel(
            backend_status_markdown=backend_status_markdown,
            error_markdown=render_error(str(exc)),
            verdict_html="",
            drafts_html="",
            raw_response=None,
            comparison_markdown="",
            current_form_item=DEFAULT_FORM_ITEM,
        )

    if not is_online:
        return SubmitViewModel(
            backend_status_markdown=backend_status_markdown,
            error_markdown=render_error(f"Backend недоступен по адресу {normalized_backend_url}."),
            verdict_html="",
            drafts_html="",
            raw_response=None,
            comparison_markdown=render_comparison(payload, selected_case_item, expected_result, None),
            current_form_item=payload,
        )

    try:
        response = httpx.post(
            f"{normalized_backend_url}/split",
            json=payload,
            timeout=HTTP_TIMEOUT,
        )
    except httpx.ReadTimeout:
        return SubmitViewModel(
            backend_status_markdown=backend_status_markdown,
            error_markdown=render_error("Backend не ответил вовремя: timeout."),
            verdict_html="",
            drafts_html="",
            raw_response=None,
            comparison_markdown=render_comparison(payload, selected_case_item, expected_result, None),
            current_form_item=payload,
        )
    except httpx.RequestError:
        return SubmitViewModel(
            backend_status_markdown=backend_status_markdown,
            error_markdown=render_error(f"Не удалось подключиться к backend по адресу {normalized_backend_url}."),
            verdict_html="",
            drafts_html="",
            raw_response=None,
            comparison_markdown=render_comparison(payload, selected_case_item, expected_result, None),
            current_form_item=payload,
        )

    if response.status_code != 200:
        return SubmitViewModel(
            backend_status_markdown=backend_status_markdown,
            error_markdown=render_error(_extract_backend_error(response)),
            verdict_html="",
            drafts_html="",
            raw_response=None,
            comparison_markdown=render_comparison(payload, selected_case_item, expected_result, None),
            current_form_item=payload,
        )

    try:
        result = response.json()
    except json.JSONDecodeError:
        return SubmitViewModel(
            backend_status_markdown=backend_status_markdown,
            error_markdown=render_error("Backend вернул невалидный JSON."),
            verdict_html="",
            drafts_html="",
            raw_response=None,
            comparison_markdown=render_comparison(payload, selected_case_item, expected_result, None),
            current_form_item=payload,
        )

    return SubmitViewModel(
        backend_status_markdown=backend_status_markdown,
        error_markdown="",
        verdict_html=render_verdict(result),
        drafts_html=render_drafts(result),
        raw_response=result,
        comparison_markdown=render_comparison(payload, selected_case_item, expected_result, result),
        current_form_item=payload,
    )


def as_prefill_outputs(view_model: PrefillViewModel) -> tuple[Any, ...]:
    return (
        view_model.item_id,
        view_model.mc_title,
        view_model.mc_id_preview,
        view_model.description,
        view_model.selected_case_item,
        view_model.expected_result,
        view_model.current_form_item,
        view_model.error_markdown,
        view_model.verdict_html,
        view_model.drafts_html,
        view_model.raw_response,
        view_model.comparison_markdown,
    )


def as_submit_outputs(view_model: SubmitViewModel) -> tuple[Any, ...]:
    return (
        view_model.backend_status_markdown,
        view_model.error_markdown,
        view_model.verdict_html,
        view_model.drafts_html,
        view_model.raw_response,
        view_model.comparison_markdown,
        view_model.current_form_item,
    )


def build_app() -> gr.Blocks:
    with gr.Blocks(title="Avito Services Splitter", css=APP_CSS) as app:
        selected_case_state = gr.State(None)
        expected_result_state = gr.State(None)
        current_form_state = gr.State(DEFAULT_FORM_ITEM)

        gr.Markdown(
            """
            <div class="app-shell hero">
              <h1>Avito Services Splitter</h1>
              <p>Анализ объявления и выделение самостоятельных услуг через существующий backend `POST /split`.</p>
            </div>
            """
        )

        with gr.Row(elem_classes=["app-shell"]):
            with gr.Column(scale=1, min_width=320, elem_classes=["panel"]):
                gr.Markdown("### Настройки demo")
                backend_url = gr.Textbox(
                    label="Backend URL",
                    value=os.getenv("AVITO_BACKEND_URL", DEFAULT_BACKEND_URL),
                    elem_id="backend-url",
                )
                backend_status = gr.Markdown(elem_id="backend-status")
                demo_case = gr.Dropdown(
                    label="Demo-кейс",
                    choices=list(DEMO_CASES_BY_LABEL.keys()),
                    value=DEFAULT_CASE_LABEL,
                    elem_id="demo-case-dropdown",
                )
                apply_demo_case = gr.Button("Подставить кейс", variant="primary", elem_id="apply-demo-case")

            with gr.Column(scale=2, min_width=480, elem_classes=["panel"]):
                gr.Markdown("### Исходное объявление")
                item_id = gr.Number(
                    label="Item ID",
                    value=DEFAULT_FORM_ITEM["itemId"],
                    precision=0,
                    elem_id="item-id",
                )
                microcategory = gr.Dropdown(
                    label="Микрокатегория",
                    choices=CATALOG_INDEX.titles,
                    value=DEFAULT_FORM_ITEM["mcTitle"],
                    elem_id="microcategory-dropdown",
                )
                mc_id_preview = gr.Textbox(
                    label="mcId",
                    value=str(DEFAULT_FORM_ITEM["mcId"]),
                    interactive=False,
                    elem_id="mcid-preview",
                )
                description = gr.Textbox(
                    label="Описание",
                    lines=8,
                    value=DEFAULT_FORM_ITEM["description"],
                    elem_id="description-input",
                )
                submit = gr.Button("Обработать объявление", variant="primary", elem_id="submit-ad")

        with gr.Column(elem_classes=["app-shell", "panel"]):
            gr.Markdown("### Результат")
            error_markdown = gr.Markdown(elem_id="error-message")
            verdict_html = gr.HTML(elem_id="verdict-card")
            drafts_html = gr.HTML(elem_id="drafts-list")
            comparison_markdown = gr.Markdown(elem_id="comparison-result")
            raw_response = gr.JSON(label="Raw JSON", elem_id="raw-json")

        app.load(
            fn=lambda backend_url_value: check_backend(backend_url_value)[1],
            inputs=[backend_url],
            outputs=[backend_status],
        )
        backend_url.change(
            fn=lambda backend_url_value: check_backend(backend_url_value)[1],
            inputs=[backend_url],
            outputs=[backend_status],
        )
        backend_url.submit(
            fn=lambda backend_url_value: check_backend(backend_url_value)[1],
            inputs=[backend_url],
            outputs=[backend_status],
        )
        microcategory.change(
            fn=get_mc_id_preview,
            inputs=[microcategory],
            outputs=[mc_id_preview],
        )
        apply_demo_case.click(
            fn=lambda case_label: as_prefill_outputs(prepare_demo_case(case_label)),
            inputs=[demo_case],
            outputs=[
                item_id,
                microcategory,
                mc_id_preview,
                description,
                selected_case_state,
                expected_result_state,
                current_form_state,
                error_markdown,
                verdict_html,
                drafts_html,
                raw_response,
                comparison_markdown,
            ],
        )
        submit.click(
            fn=lambda backend_url_value, item_id_value, mc_title_value, description_value, selected_case_item_value, expected_result_value: as_submit_outputs(
                submit_split_request(
                    backend_url=backend_url_value,
                    item_id=item_id_value,
                    mc_title=mc_title_value,
                    description=description_value,
                    selected_case_item=selected_case_item_value,
                    expected_result=expected_result_value,
                )
            ),
            inputs=[
                backend_url,
                item_id,
                microcategory,
                description,
                selected_case_state,
                expected_result_state,
            ],
            outputs=[
                backend_status,
                error_markdown,
                verdict_html,
                drafts_html,
                raw_response,
                comparison_markdown,
                current_form_state,
            ],
        )

    return app


def parse_bool_env(raw_value: str | None) -> bool:
    return str(raw_value or "").strip().lower() in {"1", "true", "yes", "on"}


def launch_from_env() -> None:
    server_name = os.getenv("AVITO_GRADIO_SERVER_NAME", DEFAULT_SERVER_NAME)
    server_port = int(os.getenv("AVITO_GRADIO_SERVER_PORT", str(DEFAULT_SERVER_PORT)))
    share = parse_bool_env(os.getenv("AVITO_GRADIO_SHARE", "false"))
    build_app().launch(server_name=server_name, server_port=server_port, share=share)


def extract_public_url_from_text(text: str) -> str | None:
    match = re.search(r"https://[a-zA-Z0-9.-]+\.gradio\.live(?:/\S*)?", text)
    if match:
        return match.group(0)
    return None


if __name__ == "__main__":
    launch_from_env()
