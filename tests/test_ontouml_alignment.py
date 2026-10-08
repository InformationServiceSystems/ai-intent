"""Tests that the OntoUML model artefacts exist, verified clean, and agree with the export's gUFO typing.

Runnable without pytest:  python tests/test_ontouml_alignment.py
"""

import json
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if "openai" not in sys.modules:
    _openai = types.ModuleType("openai")

    class _StubOpenAI:
        def __init__(self, *args, **kwargs):
            pass

    _openai.OpenAI = _StubOpenAI
    sys.modules["openai"] = _openai

from evaluation.ontouml_alignment import compare  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent / "ontology" / "ontouml"


def test_model_artefacts_present_and_verified():
    """The committed model is schema-valid and free of OntoUML verification issues."""
    v = json.load(open(ROOT / "verification.json"))
    assert v["schema_valid"] is True
    assert v["issue_count"] == 0, v["issues"]
    assert v["gufo_transformation_issues"] == []
    model = json.load(open(ROOT / "ai-intent.ontouml.json"))
    assert model["type"] == "Project" and model["name"] == "AI-Intent"


def test_model_and_export_agree_on_gufo_typing():
    """Every construct is typed by the OntoUML transformation as the export declares it."""
    rows = compare()
    assert len(rows) == 13
    bad = [r for r in rows if r["agree"] != "yes"]
    assert not bad, bad


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
