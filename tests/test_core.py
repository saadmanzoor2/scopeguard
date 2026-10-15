"""Offline tests. They test OUR logic (validation, grounding, scoring, pipeline).
The pipeline test uses a fake model reply and is NOT evidence about model quality;
see live_smoke_test.py for the real-model test."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import scopeguard as sg

BRIEF = "I need a website ASAP. You can make small changes whenever I want. Budget is flexible, we discuss later."


def test_rejects_short_and_long_input():
    with pytest.raises(sg.ScopeGuardError):
        sg.validate_input("hi")
    with pytest.raises(sg.ScopeGuardError):
        sg.validate_input("x" * (sg.MAX_CHARS + 1))


def test_extract_json_handles_think_and_fences():
    raw = '<think>hmm</think>\n```json\n{"a": 1}\n```'
    assert sg.extract_json(raw) == {"a": 1}
    with pytest.raises(sg.ScopeGuardError):
        sg.extract_json("not json at all")


def test_normalize_rejects_bad_shape():
    with pytest.raises(sg.ScopeGuardError):
        sg.normalize([1, 2])
    with pytest.raises(sg.ScopeGuardError):
        sg.normalize({"project_summary": "x", "deliverables": "oops"})
    with pytest.raises(sg.ScopeGuardError):
        sg.normalize({})


def test_grounding_drops_invented_quotes():
    flags = [{"quote": "small changes whenever I want", "category": "unlimited_revisions", "severity": "high", "why": ""},
             {"quote": "unlimited free logo design", "category": "unpaid_extras", "severity": "high", "why": ""}]
    kept, dropped = sg.ground_flags(BRIEF, flags)
    assert len(kept) == 1 and dropped == 1


def test_risk_score_orders_levels():
    low, _ = sg.risk_score([], [])
    high, level = sg.risk_score([{"severity": "high"}] * 3, ["a", "b"])
    assert low < high and level == "High"


def test_highlight_escapes_html():
    out = sg.highlight_html("a <b>x</b> y", [{"span": (2, 5)}])
    assert "<mark>&lt;b&gt;</mark>" in out


def test_pipeline_with_fake_model(monkeypatch):
    fake = {"project_summary": "Website", "deliverables": ["Website"], "missing_info": ["Pages"],
            "risk_flags": [{"quote": "Budget is flexible", "category": "unclear_budget", "severity": "medium", "why": "No number"}],
            "clarifying_questions": ["How many pages?"], "draft_reply": "Hello"}
    monkeypatch.setattr(sg, "call_model", lambda brief: json.dumps(fake))
    res = sg.analyze(BRIEF)
    assert len(res["risk_flags"]) == 1 and res["level"] in ("Low", "Medium", "High")


def test_model_offline_error(monkeypatch):
    def boom(brief):
        raise sg.ScopeGuardError("Cannot reach Ollama. Start it with `ollama serve`.")
    monkeypatch.setattr(sg, "call_model", boom)
    with pytest.raises(sg.ScopeGuardError):
        sg.analyze(BRIEF)
