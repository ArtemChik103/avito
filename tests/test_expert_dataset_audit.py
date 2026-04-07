from src.avito_splitter.expert_dataset_audit import audit_expert_dataset, evaluate_expert_dataset


def test_expert_dataset_json_and_csv_are_consistent() -> None:
    audit = audit_expert_dataset()

    assert audit.json_rows == 2480
    assert audit.csv_rows == 2480
    assert audit.json_non_numeric_item_ids == [318]
    assert audit.json_non_numeric_source_mc_ids == []
    assert audit.json_conflicting_duplicates == 0
    assert audit.csv_conflicting_duplicates == 0
    assert audit.only_in_json == 0
    assert audit.only_in_csv == 0
    assert audit.json_csv_value_mismatches == 0
    assert audit.case_type_counts == {
        "no_other_microcategories_detected": 728,
        "other_microcategories_detected_but_not_split": 1281,
        "split": 471,
    }


def test_pipeline_matches_expert_dataset_markup() -> None:
    regression = evaluate_expert_dataset()

    assert regression.examples == 2480
    assert regression.matched == 2480
    assert regression.accuracy == 1.0
