from __future__ import annotations

import pytest
import streamlit_app


def test_streamlit_app_init() -> None:
    splitter, catalog = streamlit_app.get_splitter_and_catalog()
    assert splitter is not None
    assert len(catalog) > 0


def test_streamlit_demo_cases() -> None:
    cases = streamlit_app.get_demo_cases()
    assert isinstance(cases, list)
    assert len(cases) > 0
    assert "item" in cases[0]
