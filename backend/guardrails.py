"""Guardrails: input filtering, prompt injection defence, output validation.

Three layers, each with a different job:
  1. Formulas are never interpreted by a model. They go to the deterministic
     engine, which has its own allowlist and limits. The guard here only
     enforces length and character set.
  2. Free text aimed at the coach (an LLM in later phases) is screened for
     injection and answer-extraction attempts before it gets near a prompt.
  3. Anything the coach says is checked so it cannot contain the answer key.

This is a baseline. Pattern matching will miss novel attacks; the real defence
is architectural: the model never holds the answer key at all, so there is
nothing to leak. The tests in tests/test_guardrails.py are the regression set.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

MAX_FORMULA_LEN = 300
MAX_CHAT_LEN = 500

_FORMULA_CHARS = re.compile(r"""^=[A-Za-z0-9_$.,:()+\-*/^&<>=%"'?\[\] ]*$""")

_INJECTION = [
    r"ignore\s+(all\s+|any\s+|the\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?)",
    r"disregard\s+.{0,40}(instructions?|rules?|prompt)",
    r"(reveal|show|print|repeat|tell me|give me|leak|dump).{0,50}(system prompt|instructions|answer key|answer_spec|expected answer|solution|reference)",
    r"what('?s| is) the (answer|solution)",
    r"\byou are now\b",
    r"\bpretend (to be|you)\b",
    r"\bdeveloper mode\b",
    r"\bjailbreak\b",
    r"</?\s*(system|assistant|instructions?)\s*>",
    r"\boverride\b.{0,30}(rules?|safety|policy)",
]
_INJECTION_RE = [re.compile(p, re.I | re.S) for p in _INJECTION]


@dataclass
class GuardResult:
    allowed: bool
    reason: str = "ok"


def check_formula_input(formula: str) -> GuardResult:
    if not isinstance(formula, str):
        return GuardResult(False, "formula must be text")
    if len(formula) > MAX_FORMULA_LEN:
        return GuardResult(False, "formula too long")
    if not _FORMULA_CHARS.match(formula):
        return GuardResult(False, "formula contains characters that are not allowed")
    return GuardResult(True)


def check_chat_input(text: str) -> GuardResult:
    if not isinstance(text, str) or not text.strip():
        return GuardResult(False, "empty message")
    if len(text) > MAX_CHAT_LEN:
        return GuardResult(False, "message too long")
    for pattern in _INJECTION_RE:
        if pattern.search(text):
            return GuardResult(False, "message looks like an attempt to extract the answer or change the coach's rules")
    return GuardResult(True)


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", s).upper()


def check_output(text: str, secrets: list[str]) -> GuardResult:
    """Block coach output that contains the answer value or the reference formula."""
    for secret in secrets:
        if not secret:
            continue
        if re.fullmatch(r"-?\d+(\.\d+)?", secret):
            if re.search(r"(?<![\d.])" + re.escape(secret) + r"(?!\d|\.\d)", text):
                return GuardResult(False, "output contains the answer value")
        elif _norm(secret) in _norm(text):
            return GuardResult(False, "output contains the reference solution")
    return GuardResult(True)


_FORMULA_PATTERN = re.compile(r"=\s*[A-Za-z][A-Za-z0-9_.]*\s*\(")

# Lazy import at call time to avoid a circular dependency at module load.
def _fn_name_pattern() -> re.Pattern[str]:
    """Return a compiled regex that matches any FUNCTIONS name followed by '('."""
    from .formula_engine import FUNCTIONS  # noqa: PLC0415
    names = "|".join(re.escape(name) for name in sorted(FUNCTIONS, key=len, reverse=True))
    # Match the function name preceded by a word boundary or a backtick,
    # optionally wrapped in backticks, and followed by optional whitespace + '('.
    return re.compile(rf"(?i)(?:^|[^A-Za-z0-9_])({names})\s*\(")


def check_tutor_output(text: str, secrets: list[str]) -> GuardResult:
    """check_output plus a block on formula-shaped patterns.

    Blocks any of:
      * =FUNC( (the leading-equals form)
      * FUNC( with no equals sign, e.g. COUNTIF(G2:G61,">8")
      * `FUNC(` wrapped in backticks

    Used for live tutor replies only. Static hints are exempt and go through
    check_output so they can contain structural examples without a function call.
    """
    base = check_output(text, secrets)
    if not base.allowed:
        return base
    if _FORMULA_PATTERN.search(text):
        return GuardResult(False, "output contains a formula pattern")
    if _fn_name_pattern().search(text):
        return GuardResult(False, "output contains a formula pattern")
    return GuardResult(True)
