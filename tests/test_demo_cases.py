import json
from pathlib import Path

def test_demo_cases_schema():
    demo_file = Path(__file__).parent.parent / "demo" / "demo_cases.json"
    assert demo_file.exists(), "demo_cases.json must exist"
    
    with open(demo_file, "r", encoding="utf-8") as f:
        cases = json.load(f)
        
    assert isinstance(cases, list)
    assert len(cases) >= 6, "Must contain at least 6 demo cases"
    
    for case in cases:
        assert "label" in case
        assert "item" in case
        assert "expectedShouldSplit" in case
        assert "expectedDraftMcIds" in case
        
        item = case["item"]
        assert "itemId" in item
        assert "mcId" in item
        assert "mcTitle" in item
        assert "description" in item
