"""Resolve repository root and key paths."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONSTITUTION = ROOT / "constitution"
WAVES = ROOT / "waves"
EVIDENCE = ROOT / "evidence"
SCHEMAS = ROOT / "schemas"
AUDITS = ROOT / "audits"
BASELINE = AUDITS / "baseline" / "wave0_baseline.json"
RULES = CONSTITUTION / "rules.json"
CAPITAL_RULES = CONSTITUTION / "capital-rules.json"
CP_CONSTITUTION = CONSTITUTION / "CONSTITUTION.md"
CC_CONSTITUTION = CONSTITUTION / "CONSTITUTION-CAPITAL.md"
GOVERNANCE = CONSTITUTION / "GOVERNANCE.md"
PROMPT_STACKS = ROOT / "prompt-stacks"
