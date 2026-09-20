from __future__ import annotations

import json

from runner.paths import ROOT


def test_hafez_candidate_remains_unverified_and_undefined():
    path = ROOT / "research" / "candidates" / "mechanical_break_retest_hafez.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["status"] == "UNVERIFIED"
    assert data["live_trading"] is False
    assert "P(outcome|state)" in data["no_prediction_principle"]["rule"]

    stages = {entry["stage"]: entry for entry in data["pipeline"]}
    assert stages["RESULT"]["status"] == "UNVERIFIED"
    assert stages["FORMAL_DEFINITION"]["status"] == "UNDEFINED"

    undefined = stages["FORMAL_DEFINITION"]["undefined_fields"]
    required_undefined = {
        "instrument_es_vs_mes",
        "level_definition",
        "break_definition",
        "retest_definition",
        "reaction_definition",
        "session_definition",
        "volume_profile_definition",
        "stop_definition",
        "slippage_definition",
    }
    assert required_undefined <= set(undefined)
    assert set(undefined.values()) == {"UNDEFINED"}
