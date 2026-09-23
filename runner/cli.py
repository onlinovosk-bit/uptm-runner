"""CLI: uptm-runner baseline | wave-status | evaluate-gate | smoke | enforcement-evidence"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import tempfile

from runner.enforcement import manifest, run_routes, unproven_claims
from runner.fsm import RunnerFSM, load_baseline, run_baseline_ack, wave_status
from runner.gates import evaluate_gate
from runner.paths import ROOT
from runner.stops import StopConditionError


def cmd_baseline(_: argparse.Namespace) -> int:
    try:
        result = run_baseline_ack()
    except StopConditionError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps({"ok": True, **result}, indent=2))
    return 0


def cmd_wave_status(_: argparse.Namespace) -> int:
    print(json.dumps(wave_status(RunnerFSM()), indent=2))
    return 0


def cmd_evaluate_gate(args: argparse.Namespace) -> int:
    path = Path(args.evidence) if args.evidence else None
    if path is None or not path.exists():
        result = evaluate_gate(None, evidence_path=path)
    else:
        result = evaluate_gate(None, evidence_path=path)
    payload = {
        "passed": result.passed,
        "reasons": result.reasons,
        "critical": result.critical,
        "high": result.high,
        "evidence_path": result.evidence_path,
    }
    print(json.dumps(payload, indent=2))
    return 0 if result.passed else 1


def cmd_enforcement_evidence(args: argparse.Namespace) -> int:
    """Emit UPTM-006 evidence for the ENFORCED claims, and fail if one is unearned.

    Exits non-zero when a claim has no routes, when any route reaches PASS, or
    when a route denies for a reason other than its own. Silence is not
    permission: an artifact that cannot be produced is not a passing run.
    """
    with tempfile.TemporaryDirectory() as scratch:
        results = run_routes(Path(scratch))

    payload = manifest(results, commit=args.commit)
    passing = [r["route_id"] for r in results if r["verdict"] == "PASS"]
    misattributed = [
        r["route_id"]
        for r in results
        if not r["denied_by_its_own_check"] and r["blocked_by"] is None
    ]
    payload["ok"] = not (passing or misattributed or payload["unproven_claims"])
    payload["routes_reaching_pass"] = passing
    payload["routes_denied_for_another_reason"] = misattributed

    out = Path(args.out) if args.out else ROOT / "evidence" / "enforcement" / f"{args.commit}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("ok", "commit", "expires_at", "unproven_claims",
                                              "routes_reaching_pass",
                                              "routes_denied_for_another_reason")}, indent=2))
    print(f"written: {out}", file=sys.stderr)
    return 0 if payload["ok"] else 1


def cmd_smoke(_: argparse.Namespace) -> int:
    report: dict = {"live_trading": False, "checks": []}

    def add(name: str, ok: bool, detail: str = "") -> None:
        report["checks"].append({"name": name, "ok": ok, "detail": detail})

    # Baseline
    try:
        b = load_baseline()
        add("baseline_loads", True, b.get("baseline_id", ""))
        add("live_trading_false", b.get("live_trading") is False)
        add("pr4_merge_forbidden", b.get("pr4_merge_allowed") is False)
    except Exception as exc:
        add("baseline_loads", False, str(exc))

    # FSM happy path skeleton
    try:
        fsm = RunnerFSM()
        for st in [
            __import__("runner.fsm", fromlist=["State"]).State.BASELINE,
            __import__("runner.fsm", fromlist=["State"]).State.PLAN,
            __import__("runner.fsm", fromlist=["State"]).State.WAVE_READY,
        ]:
            fsm.transition(st)
        add("fsm_discover_to_wave_ready", True, "→".join(fsm.history))
    except Exception as exc:
        add("fsm_discover_to_wave_ready", False, str(exc))

    # Cursor fail closed
    from cursor.contract import CursorNotConfiguredError, CursorTask, get_executor

    cur = get_executor()
    try:
        cur.dispatch(CursorTask(0, "00", "prompt-stacks/00_constitution.json"))
        add("cursor_fail_closed", False, "dispatch unexpectedly succeeded")
    except CursorNotConfiguredError as exc:
        add("cursor_fail_closed", True, str(exc)[:80])

    # Ruflo unavailable
    from ruflo.adapter import OrchestrationEvent, RufloUnavailableError, get_adapter

    ruflo = get_adapter()
    try:
        ruflo.publish(OrchestrationEvent("ping", {}))
        add("ruflo_unavailable", False, "publish unexpectedly succeeded")
    except RufloUnavailableError:
        add("ruflo_unavailable", True, "publish raised as expected")

    # Gate fail closed missing evidence
    g = evaluate_gate(None)
    add("gate_fail_closed_missing", g.passed is False)

    # Waves present
    waves_ok = all((ROOT / "waves" / f"wave{i}.yaml").exists() for i in range(8))
    add("waves_0_7_present", waves_ok)

    ok = all(c["ok"] for c in report["checks"])
    report["ok"] = ok
    print(json.dumps(report, indent=2))
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="uptm-runner", description="UPTM Runner control-plane")
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("baseline", help="Lock/load Wave 0 baseline acknowledgment")
    b.set_defaults(func=cmd_baseline)

    w = sub.add_parser("wave-status", help="Show FSM/wave unlock status")
    w.set_defaults(func=cmd_wave_status)

    g = sub.add_parser("evaluate-gate", help="Evaluate gate from evidence artifact")
    g.add_argument("--evidence", type=str, required=False, help="Path to evidence JSON")
    g.set_defaults(func=cmd_evaluate_gate)

    e = sub.add_parser(
        "enforcement-evidence", help="Emit UPTM-006 evidence for the ENFORCED claims"
    )
    e.add_argument("--commit", required=True, help="Commit the evidence is pinned to (P12)")
    e.add_argument("--out", default=None, help="Output path (default evidence/enforcement/)")
    e.set_defaults(func=cmd_enforcement_evidence)

    s = sub.add_parser("smoke", help="Smoke checks (no live trading)")
    s.set_defaults(func=cmd_smoke)
    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    code = args.func(args)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
