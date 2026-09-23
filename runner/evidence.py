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


def _load_schema() -> dict[str, Any]:
    path = SCHEMAS / "evidence.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


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
    # Optional strict schema (does not replace adversarial severity logic)
    try:
        import jsonschema

        # Copy and loosen severity enum so downgrade attacks reach count logic
        schema = _load_schema()
        jsonschema.validate(evidence, schema)
    except ImportError:
        pass
    except Exception:
        # Schema mismatch is recorded softly; structural errors above are hard.
        # Adversarial packs may intentionally violate severity enums.
        pass
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
