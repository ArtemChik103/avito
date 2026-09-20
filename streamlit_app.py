from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

# Ensure src directory is in sys.path for direct pipeline access
ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import streamlit as st
from avito_splitter.loaders import load_catalog_bundle
from avito_splitter.pipeline import ServicesSplitter
from avito_splitter.schemas import AdInput, EnrichedMicroCategory, SplitResponse

st.set_page_config(
    page_title="Avito Services Splitter",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def get_splitter_and_catalog() -> tuple[ServicesSplitter, list[EnrichedMicroCategory]]:
    """Load catalog bundle and instantiate ServicesSplitter once."""
    _, catalog = load_catalog_bundle()
    return ServicesSplitter(catalog), catalog


@st.cache_data
def get_demo_cases() -> list[dict[str, Any]]:
    """Load pre-configured demo cases from demo/demo_cases.json."""
    cases_path = ROOT_DIR / "demo" / "demo_cases.json"
    if cases_path.exists():
        with open(cases_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def main() -> None:
    splitter, catalog = get_splitter_and_catalog()
    demo_cases = get_demo_cases()

    st.title("Avito Services Splitter")
    st.caption("Анализ и разделение мультисервисных объявлений услуг на независимые черновики")

    # Sidebar: Mode selection and reference catalog
    with st.sidebar:
        st.subheader("Настройки входа")
        mode = st.radio(
            "Режим работы",
            options=["Готовые примеры", "Ручной ввод"],
            index=0,
        )

        selected_case_item: dict[str, Any] | None = None
        if mode == "Готовые примеры" and demo_cases:
            case_labels = [c.get("label", f"Кейс {idx + 1}") for idx, c in enumerate(demo_cases)]
            selected_case_index = st.selectbox(
                "Выберите тестовый сценарий",
                options=range(len(case_labels)),
                format_func=lambda i: case_labels[i],
            )
            selected_case_item = demo_cases[selected_case_index]["item"]

        st.divider()
        st.subheader("Справочник микрокатегорий")
        st.caption(f"Загружено микрокатегорий в каталоге: {len(catalog)}")
        with st.expander("Просмотреть доступные категории", expanded=False):
            for cat in catalog:
                st.write(f"**ID {cat.mcId}**: {cat.mcTitle}")

    # Build category lookup
    category_by_id = {cat.mcId: cat for cat in catalog}
    category_options = list(catalog)

    # Determine default field values
    if selected_case_item:
        default_item_id = int(selected_case_item.get("itemId", 1001))
        default_mc_id = int(selected_case_item.get("mcId", 101))
        default_description = str(selected_case_item.get("description", ""))
    else:
        default_item_id = 1001
        default_mc_id = 101
        default_description = "Выполняем электромонтаж, установку сантехники и монтаж натяжных потолков."

    # Find selectbox index for default category
    default_cat_index = 0
    for idx, cat in enumerate(category_options):
        if cat.mcId == default_mc_id:
            default_cat_index = idx
            break

    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.subheader("Параметры объявления")
        with st.form("split_form"):
            item_id = st.number_input(
                "ID объявления (itemId)",
                min_value=1,
                value=default_item_id,
                step=1,
            )

            selected_category = st.selectbox(
                "Текущая микрокатегория (mcId / mcTitle)",
                options=category_options,
                index=default_cat_index,
                format_func=lambda c: f"{c.mcTitle} (ID: {c.mcId})",
            )

            description = st.text_area(
                "Текст объявления (description)",
                value=default_description,
                height=180,
                help="Введите текст описания услуги для анализа независимых работ.",
            )

            submit_btn = st.form_submit_button("Разделить объявление", use_container_width=True)

    with col_right:
        st.subheader("Результат анализа")

        if submit_btn or selected_case_item is not None:
            if not description.strip():
                st.warning("Введите текст объявления для выполнения анализа.")
                return

            try:
                item = AdInput(
                    itemId=int(item_id),
                    mcId=int(selected_category.mcId),
                    mcTitle=str(selected_category.mcTitle),
                    description=description.strip(),
                )

                response: SplitResponse = splitter.process(item)

                # Summary metrics
                m1, m2 = st.columns(2)
                with m1:
                    st.metric(
                        label="Решение о разделении",
                        value="Разделено" if response.shouldSplit else "Не требует разделения",
                    )
                with m2:
                    st.metric(
                        label="Сформировано черновиков",
                        value=len(response.drafts),
                    )

                if response.shouldSplit and response.drafts:
                    st.success("Объявление содержит несколько независимых услуг. Сформированы следующие черновики:")
                    for idx, draft in enumerate(response.drafts, start=1):
                        with st.container(border=True):
                            st.markdown(f"**Черновик {idx}: {draft.mcTitle}** `(mcId: {draft.mcId})`")
                            st.write(draft.text)
                else:
                    st.info("Объявление представляет собой монолитную услугу или входит в рамки текущей комплексной категории. Разделение не требуется.")

                with st.expander("Сырой JSON ответ (согласно схеме SplitResponse)", expanded=False):
                    st.json(response.model_dump())

            except Exception as e:
                st.error(f"Ошибка при обработке объявления: {e}")
        else:
            st.info("Нажмите кнопку «Разделить объявление» для запуска анализа.")


if __name__ == "__main__":
    main()
