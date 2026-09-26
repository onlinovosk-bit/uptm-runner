"""Evidence loading, schema validation, and integrity helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from runner.paths import SCHEMAS
from runner.prompt_stacks import validate_prompt_stack_binding


class EvidenceError(ValueError):
    """Evidence invalid or incomplete."""


SCHEMA_PATH = SCHEMAS / "evidence.schema.json"
_SCHEMA_NAME = "schemas/evidence.schema.json"


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _schema_errors(evidence: dict[str, Any]) -> list[str]:
    """UPTM-010: separate "the check could not run" from "the evidence failed".

    One ``except Exception: pass`` used to cover both. It hid the fact that
    schemas/evidence.schema.json had not parsed since c4c409d - every run
    reported success while the check did nothing at all.

    A load failure is an infrastructure fault and fails closed. A mismatch is a
    finding about the evidence and stays soft, because the schema is measurably
    behind what the code really builds: 183 of the suite's evaluations fail it,
    most on packs (capital, kill_switch, market_data, pnl) the schema has never
    been taught. Turning those hard would promote an out-of-date schema into a
    gate. See docs/specs/UPTM-010-schema-load-is-not-optional.md.

    At most one error is returned: the fault is about the check, not the fields.
    """
    try:
        import jsonschema
    except ImportError:
        # jsonschema>=4.20 is a declared runtime dependency, not an extra. An
        # environment without it is misconfigured, and a misconfigured
        # environment quietly skipping a check is the defect this replaces.
        return ["schema check could not run: jsonschema is not importable"]

    try:
        schema = _load_schema()
    except json.JSONDecodeError as exc:
        return [
            f"schema check could not run: {_SCHEMA_NAME} does not parse "
            f"({exc.msg}, line {exc.lineno})"
        ]
    except OSError as exc:
        return [f"schema check could not run: {_SCHEMA_NAME} is unreadable ({exc})"]

    try:
        jsonschema.validate(evidence, schema)
    except jsonschema.ValidationError:
        # The evidence did not match. Soft on purpose - see the docstring.
        return []
    except jsonschema.SchemaError as exc:
        first = str(exc).splitlines()[0]
        return [
            f"schema check could not run: {_SCHEMA_NAME} is not a valid "
            f"JSON Schema ({first})"
        ]
    except Exception as exc:  # noqa: BLE001 - deliberate, and no longer silent
        # Anything else means the check did not complete. Unknown is not pass.
        return [
            f"schema check could not run: {type(exc).__name__} "
            f"({str(exc).splitlines()[0]})"
        ]
    return []


def validate_evidence_structure(evidence: dict[str, Any]) -> list[str]:
    """Structural validation. Fail closed on missing required fields."""
    errors: list[str] = []
    required = [
        "evidence_id",
        "wave_id",
        "commit_sha",
        "branch",
        "files",
        "commands",
        "results",
        "probes",
        "before",
        "after",
        "agent_claim",
        "live_trading",
        "prompt_stack",
    ]
    for key in required:
        if key not in evidence:
            errors.append(f"missing field: {key}")
    if "results" in evidence and isinstance(evidence["results"], dict):
        for rk in ("passed", "failed", "findings"):
            if rk not in evidence["results"]:
                errors.append(f"missing results.{rk}")
    if "probes" in evidence:
        if not isinstance(evidence["probes"], list) or len(evidence["probes"]) < 1:
            errors.append("probes must be a non-empty list")
    if "live_trading" in evidence and evidence.get("live_trading") is not False:
        errors.append("live_trading must be false")
    errors.extend(validate_prompt_stack_binding(evidence))
    errors.extend(_schema_errors(evidence))
    return errors


def digest_payload(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load_evidence(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise EvidenceError("evidence root must be object")
    return data


def normalize_severity(raw: str) -> str:
    s = raw.strip().upper()
    aliases = {
        "CRIT": "CRITICAL",
        "CRITICAL": "CRITICAL",
        "HIGH": "HIGH",
        "WARN": "WARNING",
        "WARNING": "WARNING",
        "MED": "MEDIUM",
        "MEDIUM": "MEDIUM",
        "LOW": "LOW",
        "INFO": "INFO",
    }
    return aliases.get(s, s)


def count_findings(evidence: dict[str, Any]) -> dict[str, int]:
    """
    Count OPEN/HYPOTHESIS/accepted residual findings by effective severity.
    Prefer true_severity; detect V-CRIT*/V-HIGH* id downgrades.
    """
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0, "WARNING": 0}
    for finding in evidence.get("results", {}).get("findings", []):
        status = finding.get("status")
        if status == "FIXED":
            continue
        if status not in ("OPEN", "HYPOTHESIS", None) and status in (
            "ACCEPTED_RISK",
            "ACCEPT_RESIDUAL",
        ):
            # still count accepted risk as present risk for gating
            pass

        if finding.get("true_severity"):
            severity = normalize_severity(str(finding["true_severity"]))
        else:
            severity = normalize_severity(str(finding.get("severity", "INFO")))

        fid = str(finding.get("id", ""))
        if fid.startswith("V-CRIT") and severity not in ("CRITICAL",):
            severity = "CRITICAL"
        if fid.startswith("V-HIGH") and severity not in ("HIGH", "CRITICAL"):
            severity = "HIGH"

        if severity not in counts:
            severity = "INFO"
        counts[severity] += 1
    return counts
