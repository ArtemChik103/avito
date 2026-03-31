from src.avito_splitter.case_report import build_case_report, format_case_report


def test_case_report_matches_all_known_case_files() -> None:
    sections = build_case_report()

    assert len(sections) == 4
    assert sum(section.total for section in sections) == 37
    assert sum(section.matched for section in sections) == 37
    assert all(outcome.ok for section in sections for outcome in section.outcomes)


def test_case_report_formatter_contains_totals_and_sources() -> None:
    rendered = format_case_report(build_case_report())

    assert "Avito Services Splitter Case Report" in rendered
    assert "Total matched: 37/37" in rendered
    assert "[data/gold_examples.json]" in rendered
    assert "[demo/demo_cases.json]" in rendered
