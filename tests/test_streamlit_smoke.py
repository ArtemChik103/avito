import sys
from pathlib import Path

def test_streamlit_demo_imports():
    """
    Very basic smoke test to ensure there are no syntax errors 
    and the file is present.
    """
    demo_file = Path(__file__).parent.parent / "demo" / "streamlit_app.py"
    assert demo_file.exists()
    
    # Check that we can read it and compile it
    code = demo_file.read_text("utf-8")
    compile(code, demo_file.name, "exec")
