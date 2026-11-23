"""conformance/cases.jsonl must match what the current rules produce, so the Java library is always
held to today's Python results. After a rule change: python conformance/make_cases.py."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_conformance_cases_are_up_to_date():
    spec = importlib.util.spec_from_file_location("make_cases", ROOT / "conformance" / "make_cases.py")
    make_cases = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(make_cases)
    current = (ROOT / "conformance" / "cases.jsonl").read_text(encoding="utf-8").splitlines()
    fresh = make_cases.cases()
    assert len(current) == len(fresh)
    stale = [k for k, (x, y) in enumerate(zip(current, fresh)) if x != y]
    assert not stale, f"{len(stale)} cases are stale (first line {stale[0] + 1}); run: python conformance/make_cases.py"
