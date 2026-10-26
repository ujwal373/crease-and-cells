"""Tests for the offline mission generator.

All tests inject a fake Sonnet client so they run offline with no API key.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import pytest

# The generator lives in scripts/, which is on the Python path via pythonpath=["."]
from scripts.generate_missions import MissionGenerator, save_result


# ---------------------------------------------------------------------------
# Fake Anthropic client (Sonnet shape — same interface as Haiku fake)
# ---------------------------------------------------------------------------

@dataclass
class _FakeUsage:
    input_tokens: int = 200
    output_tokens: int = 400


@dataclass
class _FakeContentBlock:
    text: str


@dataclass
class _FakeMessage:
    content: list[_FakeContentBlock]
    usage: _FakeUsage


class _FakeMessages:
    def __init__(self, reply: str):
        self.reply = reply
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs) -> _FakeMessage:
        self.calls.append(kwargs)
        return _FakeMessage(
            content=[_FakeContentBlock(text=self.reply)],
            usage=_FakeUsage(),
        )


class FakeSonnet:
    def __init__(self, reply: str):
        self.messages = _FakeMessages(reply=reply)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_mission_json() -> str:
    """A mission that should pass all validation checks."""
    mission = {
        "title": "Economy Check",
        "story": (
            "Coach Rao taps the whiteboard. \"We've been leaking runs. "
            "Count every spell in this log where the economy went above six runs per over.\""
        ),
        "task": (
            "Economy is in column G, rows 2 to 61. "
            "Write a COUNTIF formula that counts spells with economy greater than 6."
        ),
        "npc": "Coach Rao",
        "reference_solution": '=COUNTIF(G2:G61,">6")',
        "answer_spec": {"kind": "count_gt", "field": "economy", "value": 6},
        "hints": [
            "You need a function that counts only the cells that meet a condition.",
            "COUNTIF takes two parts: the range to examine and the condition. Numeric conditions with operators go in quotes.",
            "Structure: =COUNTIF(range, condition). Point it at the economy column in G and state the threshold in quotes.",
        ],
        "required_any": ["COUNTIF"],
        "required_all": [],
    }
    return json.dumps(mission)


def _make_gen(reply: str) -> tuple[MissionGenerator, FakeSonnet]:
    fake = FakeSonnet(reply)
    gen = MissionGenerator(client=fake)
    return gen, fake


# ---------------------------------------------------------------------------
# Test 1: valid response produces a verified mission and the API is called once
# ---------------------------------------------------------------------------

def test_valid_generation_verified(tmp_path):
    gen, fake = _make_gen(_valid_mission_json())

    result = gen.generate(level=1, zone="The Nets", npc="Coach Rao", topic="economy")

    assert result.status == "verified", result.validation_errors
    assert result.mission is not None
    assert result.mission["title"] == "Economy Check"
    assert len(fake.messages.calls) == 1, "expected exactly one API call"


# ---------------------------------------------------------------------------
# Test 2: invalid JSON is rejected with status=invalid
# ---------------------------------------------------------------------------

def test_invalid_json_rejected():
    gen, _ = _make_gen("Sure! Here is your mission: {this is not JSON}")

    result = gen.generate()

    assert result.status == "invalid"
    assert any("json_parse" in e for e in result.validation_errors)
    assert result.mission is None


# ---------------------------------------------------------------------------
# Test 3: formula that raises FormulaError is marked invalid
# ---------------------------------------------------------------------------

def test_bad_formula_syntax_invalid():
    doc = json.loads(_valid_mission_json())
    doc["reference_solution"] = "=BADFUNCTION(G2:G61)"
    gen, _ = _make_gen(json.dumps(doc))

    result = gen.generate()

    assert result.status == "invalid"
    assert any("formula_error" in e for e in result.validation_errors)


# ---------------------------------------------------------------------------
# Test 4: answer_spec that doesn't match the formula result -> needs_review
# ---------------------------------------------------------------------------

def test_answer_spec_mismatch_needs_review():
    doc = json.loads(_valid_mission_json())
    # formula counts economy > 6 (result: 44)
    # but answer_spec says economy > 99 (result: 0)
    doc["answer_spec"] = {"kind": "count_gt", "field": "economy", "value": 99}
    gen, _ = _make_gen(json.dumps(doc))

    result = gen.generate()

    assert result.status == "needs_review"
    # validator returns "wrong_value" when the formula result doesn't match the spec
    assert any("validator" in e and "wrong_value" in e for e in result.validation_errors)


# ---------------------------------------------------------------------------
# Test 5: hint that leaks the expected answer -> needs_review
# ---------------------------------------------------------------------------

def test_hint_leaking_answer_needs_review():
    doc = json.loads(_valid_mission_json())
    # The expected value for count_gt economy > 6 with seed=101 is 44.
    # Injecting that number into a hint should trigger the guardrail.
    doc["hints"][1] = "There are 44 spells where the economy exceeds the threshold."
    gen, _ = _make_gen(json.dumps(doc))

    result = gen.generate()

    assert result.status == "needs_review"
    assert any("hint" in e and "leak" in e for e in result.validation_errors)


# ---------------------------------------------------------------------------
# Test 6: hint that contains the full formula -> needs_review
# ---------------------------------------------------------------------------

def test_hint_containing_formula_needs_review():
    doc = json.loads(_valid_mission_json())
    # The reference solution itself is in the secrets list.
    doc["hints"][2] = 'The formula is =COUNTIF(G2:G61,">6") and that is all you need.'
    gen, _ = _make_gen(json.dumps(doc))

    result = gen.generate()

    assert result.status == "needs_review"
    assert any("hint" in e and "leak" in e for e in result.validation_errors)


# ---------------------------------------------------------------------------
# Test 7: missing required field -> invalid
# ---------------------------------------------------------------------------

def test_missing_field_invalid():
    doc = json.loads(_valid_mission_json())
    del doc["answer_spec"]
    gen, _ = _make_gen(json.dumps(doc))

    result = gen.generate()

    assert result.status == "invalid"
    assert any("missing_fields" in e for e in result.validation_errors)


# ---------------------------------------------------------------------------
# Test 8: save_result writes to the output directory
# ---------------------------------------------------------------------------

def test_save_result_writes_file(tmp_path):
    gen, _ = _make_gen(_valid_mission_json())
    result = gen.generate()

    assert result.mission is not None
    path = save_result(result, out_dir=tmp_path)

    assert path is not None and path.exists()
    saved = json.loads(path.read_text())
    assert saved["title"] == "Economy Check"
    assert saved["status"] == "verified"


# ---------------------------------------------------------------------------
# Test 9: API exception -> invalid result, no file written
# ---------------------------------------------------------------------------

def test_api_error_returns_invalid():
    class _ErrorMessages:
        def create(self, **kwargs):
            raise RuntimeError("connection refused")

    class _ErrorClient:
        messages = _ErrorMessages()

    gen = MissionGenerator(client=_ErrorClient())
    result = gen.generate()

    assert result.status == "invalid"
    assert any("api_error" in e for e in result.validation_errors)


# ---------------------------------------------------------------------------
# Test 10: markdown fence stripping
# ---------------------------------------------------------------------------

def test_markdown_fence_stripped():
    fenced = "```json\n" + _valid_mission_json() + "\n```"
    gen, _ = _make_gen(fenced)

    result = gen.generate()

    assert result.status == "verified", result.validation_errors


# ---------------------------------------------------------------------------
# Test 11: hardcoded formula (no cell references) is rejected as invalid
# ---------------------------------------------------------------------------

def test_hardcoded_formula_invalid():
    doc = json.loads(_valid_mission_json())
    # =44 has no cell references; the validator returns "hardcoded_value"
    doc["reference_solution"] = "=44"
    gen, _ = _make_gen(json.dumps(doc))

    result = gen.generate()

    assert result.status == "invalid"
    assert any("hardcoded_value" in e for e in result.validation_errors)


# ---------------------------------------------------------------------------
# Test 12: validation_errors are saved inside the generated file
# ---------------------------------------------------------------------------

def test_validation_errors_in_saved_file(tmp_path):
    doc = json.loads(_valid_mission_json())
    # Mismatch so it becomes needs_review with a validation error
    doc["answer_spec"] = {"kind": "count_gt", "field": "economy", "value": 99}
    gen, _ = _make_gen(json.dumps(doc))

    result = gen.generate()
    assert result.status == "needs_review"

    path = save_result(result, out_dir=tmp_path)
    assert path is not None

    saved = json.loads(path.read_text())
    assert "validation_errors" in saved
    assert len(saved["validation_errors"]) > 0
    assert any("wrong_value" in e for e in saved["validation_errors"])


# ---------------------------------------------------------------------------
# Test 13: nothing under missions/generated/ is loaded by load_missions()
# ---------------------------------------------------------------------------

def test_generated_missions_not_loaded_by_service(tmp_path):
    from backend.service import load_missions
    from pathlib import Path

    missions = load_missions()
    for m in missions:
        # All ids loaded by the engine must follow the LN-NNN pattern,
        # not the GEN-XXXXXXXX pattern used for generated candidates.
        assert not m["id"].startswith("GEN-"), (
            f"load_missions() loaded a generated mission: {m['id']}. "
            "Generated missions must stay in missions/generated/ until merged."
        )
