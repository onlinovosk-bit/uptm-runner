"""Enforcement evidence for the ENFORCED claims in capital-rules.json (UPTM-006).

Implements the criteria preregistered in
docs/specs/UPTM-006-enforcement-evidence.md, written before this module existed
(CC/P4).

What an ENFORCED claim asserts
------------------------------
    There is no route by which a gate can reach PASS while violating this
    principle.

That is a claim about routes, not about detectors. A correct detector nothing
calls enforces nothing — the lesson UPTM-002c is named after. So the evidence
here is organised by route: each one is a concrete piece of evidence a caller
could submit while violating the principle, and each names the guards that stop
it.

What this module does not establish
-----------------------------------
That the route list is complete. It shows that every enumerated route denies. A
route nobody thought of is not covered, and no test closes that. This is why
UPTM-006 advances no principle's status: it makes two existing claims checkable,
which is a different and smaller thing than making them true.
"""

from __future__ import annotations

import contextlib
import importlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from runner.gates import evaluate_gate
from runner.paths import CAPITAL_RULES, ROOT, PROMPT_STACKS
from runner.prompt_stacks import assemble_prompt
from runner.provenance import HeadProvenance
from runner.staleness import dependency_digests, determinism_declaration, digest_file

@dataclass(frozen=True)
class BypassRoute:
    """One way a caller could try to reach PASS while violating a principle.

    ``guards`` names attributes of ``runner.gates``. Neuter all of them and the
    route must reach PASS — that is what makes the denial load-bearing rather
    than incidental. A route that still denies without its guards is denied by
    something else, and names the wrong guard.

    ``expect`` is the check id whose denial is the point of the route. Asserting
    only the verdict would accept a route that denies for an unrelated reason,
    which is how a proof quietly stops proving anything.

    ``stubs`` are preconditions, not cheats. ``can_write`` reports writable for
    uid 0 whatever the file mode says, so a suite running as root would deny
    every kill-switch route on the deployment rather than on the property under
    test. Sealing it is what makes the route about its own subject.

    ``blocked_by`` names a condition that currently prevents the route from
    demonstrating anything, and is reported rather than hidden.

    ``around`` wraps evaluation only. Evidence is built before it starts, so a
    route can assemble a binding from the real stacks and then show the gate a
    drifted source. Applying that drift during ``build`` would bake the drifted
    digest into the binding and the route would pass.
    """

    route_id: str
    principle: str
    description: str
    build: Callable[[Path], dict[str, Any]]
    guards: tuple[str, ...]
    expect: str
    stubs: tuple[tuple[str, str, Any], ...] = ()
    blocked_by: str | None = None
    around: Callable[[Path], contextlib.AbstractContextManager[Any]] | None = None


#: A sealed deployment: the Runner cannot write its own stop state. Every
#: kill-switch route assumes this, because a route about drill freshness that
#: fails on the container's uid has demonstrated nothing about drill freshness.
SEALED = (("runner.detectors.kill_switch", "can_write", lambda _path: False),)


@contextlib.contextmanager
def apply_stubs(stubs: tuple[tuple[str, str, Any], ...]):
    """Install a route's preconditions, then put everything back."""
    saved: list[tuple[Any, str, Any]] = []
    try:
        for module_path, attribute, value in stubs:
            module = importlib.import_module(module_path)
            saved.append((module, attribute, getattr(module, attribute)))
            setattr(module, attribute, value)
        yield
    finally:
        for module, attribute, original in reversed(saved):
            setattr(module, attribute, original)


# --------------------------------------------------------------------------
# evidence builders
# --------------------------------------------------------------------------


def _base(**overrides: Any) -> dict[str, Any]:
    """Evidence that passes every gate check unrelated to the route under test.

    Kept deliberately close to the suite's own fixture: a route must fail
    because of the thing it is demonstrating, never because the surrounding
    evidence was sloppy.
    """
    evidence: dict[str, Any] = {
        "evidence_id": "uptm-006-route",
        "wave_id": 3,
        "commit_sha": "0" * 10,
        "branch": "enforcement-evidence",
        "pr": None,
        # UPTM-008: a real digest of a real file. Every route carried
        # "a" * 64 from the day this wall was built and passed structural
        # validation with it - the routes proved what they were built to prove
        # and none of them noticed the fabrication beside the proof.
        "files": [
            {
                "path": "runner/gates.py",
                "sha256": digest_file(ROOT / "runner" / "gates.py") or "",
            }
        ],
        "commands": [{"cmd": "pytest", "exit_code": 0}],
        "results": {"passed": 1, "failed": 0, "findings": []},
        "probes": [
            {"probe_id": "probe_live_trading", "outcome": "BLOCKED", "output_digest": "deadbeef"}
        ],
        "before": {"digest": "b" * 64, "summary": "before"},
        "after": {"digest": "c" * 64, "summary": "after"},
        "agent_claim": {"verdict": "PASS", "notes": "ok"},
        "live_trading": False,
        "prompt_stack": assemble_prompt(
            ["00"],
            "commander",
            {"wave_id": 3, "producer": "runner.enforcement._base"},
        ).cursor_metadata(),
        "scope": {"capital_bearing": False, "live_bearing": False},
        "signature": None,
    }
    evidence.update(overrides)
    return evidence


def _environment() -> dict[str, Any]:
    return {
        "deployment_ref": "dep-1",
        "credentials_ref": "cred-1",
        "gate_path_digest": "gate-1",
        "changed_at": "2026-09-01T00:00:00Z",
    }


def _stop_state(root: Path, state: str = "CLEAR", **overrides: Any) -> dict[str, Any]:
    path = root / f"stop.{state.lower()}.state"
    path.write_text(state, encoding="utf-8")
    stop = {
        "path": str(path),
        "owner": "ops@revolis",
        "runner_writable": False,
        "environment": _environment(),
        "independence_attestation": {"by": "ops@revolis", "at": "2026-09-10T00:00:00Z"},
    }
    stop.update(overrides)
    return stop


def _drill(stop: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    drill = {
        "last_drill_at": "2026-09-22T12:00:00Z",
        "drill_commit": "c9ae2aa",
        "drill_stop_path": stop["path"],
        "before": {"state": "RUNNING", "artifact_digest": "a" * 64},
        "after": {"state": "STOPPED", "artifact_digest": "b" * 64},
        "environment": dict(stop.get("environment") or {}),
    }
    drill.update(overrides)
    return drill


def _live_bearing(root: Path, *, stop_overrides: Any = None, drill_overrides: Any = None,
                  state: str = "CLEAR") -> dict[str, Any]:
    stop = _stop_state(root, state, **(stop_overrides or {}))
    return _base(
        scope={"capital_bearing": False, "live_bearing": True},
        kill_switch={"stop_state": stop},
        kill_switch_drill=_drill(stop, **(drill_overrides or {})),
    )


def _capital_pack(**overrides):
    """A capital declaration well inside the tranche.

    The field names are the detector's, not a guess: `at_risk` is the single
    number VC-I2 compares against the ceiling. An earlier version of this
    builder invented `aggregate_open_exposure` and `per_position_at_risk` as
    pack fields and nothing noticed, because VC-P1 denied every capital route
    on the unset tranche before any of them was read. Setting the tranche is
    what exposed it.
    """
    pack = {"currency": "EUR", "at_risk": 100.0, "cumulative_realised_loss": 50.0}
    pack.update(overrides)
    return pack


def _capital_gate(pack=None, **overrides):
    return _base(
        scope={"capital_bearing": True, "live_bearing": False},
        capital=pack if pack is not None else _capital_pack(),
        capital_gate=True,
        **overrides,
    )


#: A tranche cleared after having been set. VC-P1 must still deny: a ceiling
#: that can be removed by editing a file is not a ceiling.
CLEARED_TRANCHE = (
    ("runner.gates", "load_capital_rules", lambda: {"validation_capital": {}}),
)


# --------------------------------------------------------------------------
# the routes
# --------------------------------------------------------------------------

#: Route groups whose id is not a principle. UPTM-006's claim gate only demands
#: routes for principles reading ENFORCED, so a guard that protects no such
#: principle would otherwise go unrouted: remove it and nothing notices. These
#: exist to close that, and are listed separately so the claim gate stays exact.
NON_PRINCIPLE_GUARDS = {
    "APS-001": (
        "The mandatory prompt-stack evidence binding. It protects evidence "
        "integrity rather than P8 or P10 directly - removing it does not let a "
        "kill-switch or capital violation through - so no ENFORCED principle "
        "requires these routes. They are here because a guard nobody routes is "
        "a guard whose removal is silent."
    ),
    "EVIDENCE-STRUCTURE": (
        "The required-field list inside validate_evidence_structure. Like APS-001 "
        "it protects evidence integrity rather than P8 or P10 directly, so no "
        "ENFORCED principle demands routes for it. "
        "It is routed here because it was measured unrouted: disabling all "
        "fourteen required fields failed two tests, and both were PS-R1 "
        "bookkeeping about prompt_stack. The ten routes naming "
        "validate_evidence_structure are all prompt-stack routes and every one is "
        "about the binding arm, so nothing asked whether evidence with no "
        "commit_sha could reach PASS. "
        "Which fields these routes use is not arbitrary. commit_sha, agent_claim "
        "and branch are held by this arm alone - neuter the guard and each route "
        "opens - so each denies for its own reason with nothing covering for it. "
        "probes and results are deliberately not routed here: measured, their "
        "absence is also caught by the fabrication detector and by the claim gate, "
        "so a route on them would name this guard while another mechanism did the "
        "work."
    ),
}

SCOPE = ("run_scope_detector",)
STRUCTURE = ("validate_evidence_structure",)
KILL_SWITCH = ("run_kill_switch_detectors",)
CAPITAL = ("run_validation_capital_detectors",)
BINDING = ("binding_errors",)


def _composer_binding(**overrides: Any) -> dict[str, Any]:
    """A shaped binding. Overrides are what the route is about.

    Built from a real assembled binding rather than a literal, so every field
    the contract requires is present without this fixture having to know the
    list. When APS-001 gained stack_releases, registry_sha256,
    evidence_expires_at and stale_on, a hardcoded shape silently started
    denying these routes on the missing fields instead of on the thing each one
    is about - the proofs stayed green-looking while proving nothing.

    Only the keys a route overrides are shaped; the rest stay true.
    """
    binding = dict(
        assemble_prompt(["00"], "commander", {"wave_id": 3}).cursor_metadata()
    )
    binding.update(
        {
            "role": "commander",
            "stack_ids": ["00"],
            "stack_versions": {"00": "0.1.0"},
            "stack_digests": {"00": "a" * 64},
            "assembled_prompt_digest": "b" * 64,
            "wave_context": {"wave_id": 3},
        }
    )
    binding.update(overrides)
    return binding


def _without_wave_context(_root: Path) -> dict[str, Any]:
    """Drop wave_context from a binding assembled as {"wave_id": 3}.

    evidence.wave_id is also 3. Substituting that id back would reproduce the
    assembled prompt and the gate would PASS.
    """
    binding = assemble_prompt(["00"], "commander", {"wave_id": 3}).cursor_metadata()
    del binding["wave_context"]
    return _base(prompt_stack=binding)


def _drift_prompt_stack_source(root: Path) -> contextlib.AbstractContextManager[Any]:
    """Show the gate a stack 00 body the registry digest does not name.

    The copy is per route root. The repository source is left untouched.
    """

    @contextlib.contextmanager
    def _ctx():
        import runner.prompt_stacks as prompt_stacks

        dest = root / "drifted-prompt-stacks"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(PROMPT_STACKS, dest)
        constitution = dest / "00_constitution.json"
        payload = json.loads(constitution.read_text(encoding="utf-8"))
        payload["drift"] = "PS-R3"
        constitution.write_text(json.dumps(payload), encoding="utf-8")
        saved = prompt_stacks.PROMPT_STACKS
        prompt_stacks.PROMPT_STACKS = dest
        try:
            yield
        finally:
            prompt_stacks.PROMPT_STACKS = saved

    return _ctx()


ROUTES: tuple[BypassRoute, ...] = (
    # ---- P8 -------------------------------------------------------------
    BypassRoute(
        "P8-R1", "P8",
        "no scope declaration and no kill-switch pack — the pre-UPTM-005 omission",
        lambda root: {k: v for k, v in _base().items() if k != "scope"},
        SCOPE, "SC-P1",
    ),
    BypassRoute(
        "P8-R2", "P8",
        "declares live_bearing false while carrying a kill-switch pack",
        lambda root: _base(
            scope={"capital_bearing": False, "live_bearing": False},
            kill_switch={"stop_state": _stop_state(root)},
        ),
        SCOPE + KILL_SWITCH, "SC-I3", SEALED,
    ),
    BypassRoute(
        "P8-R3", "P8",
        "declares live_bearing true and brings no packs",
        lambda root: _base(scope={"capital_bearing": False, "live_bearing": True}),
        SCOPE, "SC-I2",
    ),
    BypassRoute(
        "P8-R4", "P8",
        "a complete valid pack whose stop state reads ENGAGED",
        lambda root: _live_bearing(root, state="ENGAGED"),
        ("run_kill_switch_detectors", "stop_is_engaged"), "KS-I3", SEALED,
    ),
    BypassRoute(
        "P8-R5", "P8",
        "declares the stop state writable by the Runner",
        lambda root: _live_bearing(root, stop_overrides={"runner_writable": True}),
        KILL_SWITCH, "KS-P2", SEALED,
    ),
    BypassRoute(
        "P8-R6", "P8",
        "a drill older than the cadence",
        lambda root: _live_bearing(root, drill_overrides={"last_drill_at": "2026-06-25T12:00:00Z"}),
        KILL_SWITCH, "KS-D2", SEALED,
    ),
    BypassRoute(
        "P8-R7", "P8",
        "a fresh drill run against a deployment that has since changed",
        lambda root: _live_bearing(
            root, drill_overrides={"environment": {**_environment(), "credentials_ref": "rotated"}}
        ),
        KILL_SWITCH, "KS-D5", SEALED,
    ),
    BypassRoute(
        "P8-R8", "P8",
        "no independence attestation",
        lambda root: _live_bearing(root, stop_overrides={"independence_attestation": None}),
        KILL_SWITCH, "KS-D6", SEALED,
    ),
    # ---- P10 ------------------------------------------------------------
    BypassRoute(
        "P10-R1", "P10",
        "no scope declaration and no capital pack",
        lambda root: {k: v for k, v in _base().items() if k != "scope"},
        SCOPE, "SC-P1",
    ),
    BypassRoute(
        "P10-R2", "P10",
        "declares capital_bearing false while carrying a capital pack",
        lambda root: _base(
            scope={"capital_bearing": False, "live_bearing": False}, capital=_capital_pack()
        ),
        SCOPE + CAPITAL, "SC-I3",
    ),
    BypassRoute(
        "P10-R3", "P10",
        "declares capital_bearing true and brings no pack",
        lambda root: _base(scope={"capital_bearing": True, "live_bearing": False}),
        SCOPE, "SC-I1",
    ),
    BypassRoute(
        "P10-R4", "P10",
        "capital at risk above the validation tranche",
        lambda root: _capital_gate(_capital_pack(at_risk=900.0)),
        CAPITAL, "VC-I2",
    ),
    BypassRoute(
        "P10-R5", "P10",
        "return used as an acceptance criterion of the validation experiment",
        lambda root: _capital_gate(gate_criteria=["cumulative_pnl > 0"]),
        CAPITAL, "VC-R1",
    ),
    BypassRoute(
        "P10-R6", "P10",
        "cumulative realised loss above the validation tranche",
        lambda root: _capital_gate(_capital_pack(cumulative_realised_loss=900.0)),
        CAPITAL, "VC-I3",
    ),
    BypassRoute(
        "P10-R7", "P10",
        "exposure reported in a currency the ceiling is not denominated in",
        lambda root: _capital_gate(_capital_pack(currency="USD", at_risk=650.0)),
        CAPITAL, "VC-I4",
    ),
    BypassRoute(
        "P10-R8", "P10",
        "the tranche cleared after having been set",
        lambda root: _capital_gate(),
        CAPITAL, "VC-P1", CLEARED_TRANCHE,
    ),
    BypassRoute(
        "P10-R9", "P10",
        "a PASS claim resting on what the run earned",
        lambda root: _capital_gate(
            agent_claim={"verdict": "PASS", "notes": "ok", "basis": ["net profit"]}
        ),
        CAPITAL, "VC-R2",
    ),
    # ---- APS-001, a guard rather than a principle -----------------------
    BypassRoute(
        "PS-R1", "APS-001",
        "gate evidence submitted with no prompt-stack binding at all",
        lambda root: {k: v for k, v in _base().items() if k != "prompt_stack"},
        STRUCTURE, "prompt_stack",
    ),
    BypassRoute(
        "PS-R2", "APS-001",
        "a prompt-stack binding whose assembled digest does not match the stacks it names",
        lambda root: _base(
            prompt_stack={**_base()["prompt_stack"], "assembled_prompt_digest": "0" * 64}
        ),
        STRUCTURE, "assembled_prompt_digest mismatch",
    ),
    BypassRoute(
        "PS-R3", "APS-001",
        "a stack body changed after its evidence binding was assembled, without a registry digest update",
        lambda root: _base(),
        STRUCTURE, "prompt stack 00 digest mismatch",
        around=_drift_prompt_stack_source,
    ),
    BypassRoute(
        "PS-R4", "APS-001",
        "wave_context omitted where evidence.wave_id would reconstruct the same context",
        _without_wave_context,
        STRUCTURE, "prompt_stack wave_context is required",
    ),
    BypassRoute(
        "PS-R5", "APS-001",
        "executor binding names stack 06, which that role may not receive",
        lambda root: _base(prompt_stack=_composer_binding(
            role="executor",
            stack_ids=["00", "06"],
            stack_versions={"00": "0.1.0", "06": "0.1.0"},
            stack_digests={"00": "a" * 64, "06": "b" * 64},
            wave_context={"wave_id": 6},
        )),
        STRUCTURE, "may not receive stack 06",
    ),
    BypassRoute(
        "PS-R6", "APS-001",
        "binding names a stack id that is not in the registry",
        lambda root: _base(prompt_stack=_composer_binding(stack_ids=["00", "99"])),
        STRUCTURE, "unknown prompt stack",
    ),
    BypassRoute(
        "PS-R7", "APS-001",
        "the same stack id is requested twice",
        lambda root: _base(prompt_stack=_composer_binding(stack_ids=["00", "00"])),
        STRUCTURE, "duplicate prompt stack",
    ),
    BypassRoute(
        "PS-R8", "APS-001",
        "stack 06 is requested without its prior dependencies",
        lambda root: _base(prompt_stack=_composer_binding(stack_ids=["06"])),
        STRUCTURE, "missing prior dependencies",
    ),
    BypassRoute(
        "PS-R9", "APS-001",
        "binding role is outside the role taxonomy",
        lambda root: _base(prompt_stack=_composer_binding(role="auditor")),
        STRUCTURE, "unknown role",
    ),
    BypassRoute(
        "PS-R10", "APS-001",
        "binding names no stacks",
        lambda root: _base(prompt_stack=_composer_binding(stack_ids=[])),
        STRUCTURE, "no prompt stacks",
    ),
    # ---- P12, UPTM-008: the binding the evidence declares ----------------
    BypassRoute(
        "P12-R1", "P12",
        "evidence declaring a file whose content has changed since it was produced",
        lambda root: _base(files=[{"path": "runner/gates.py", "sha256": "a" * 64}]),
        BINDING, "binding STALE",
    ),
    BypassRoute(
        "P12-R2", "P12",
        "evidence declaring a file that is not in the tree at all",
        lambda root: _base(files=[{"path": "runner/no_such_module.py", "sha256": "b" * 64}]),
        BINDING, "binding UNKNOWN",
    ),
    BypassRoute(
        "P12-R3", "P12",
        "evidence bound to nothing - an empty files list",
        lambda root: _base(files=[]),
        BINDING, "binding UNKNOWN",
    ),
    BypassRoute(
        "P12-R4", "P12",
        "a digest that is not a digest, which a lenient check would skip rather than refuse",
        lambda root: _base(files=[{"path": "runner/gates.py", "sha256": "not-a-digest"}]),
        BINDING, "binding UNKNOWN",
    ),
    BypassRoute(
        "P12-R5", "P12",
        "a files entry that is not an object at all",
        lambda root: _base(files=["runner/gates.py"]),
        BINDING, "binding UNKNOWN",
    ),
    # ---- the required-field list, the other arm of the same guard ---------
    # Each of these drops one field that the required-field list is the sole
    # mechanism enforcing. Measured before they were written: neuter
    # validate_evidence_structure and each route reaches PASS, so the denial is
    # this arm's rather than a neighbour's.
    BypassRoute(
        "ES-R1", "EVIDENCE-STRUCTURE",
        "gate evidence submitted with no commit_sha, so no PASS could be pinned to a commit",
        lambda root: {k: v for k, v in _base().items() if k != "commit_sha"},
        STRUCTURE, "missing field: commit_sha",
    ),
    BypassRoute(
        "ES-R2", "EVIDENCE-STRUCTURE",
        "gate evidence submitted with no agent_claim, so nothing states what is being claimed",
        lambda root: {k: v for k, v in _base().items() if k != "agent_claim"},
        STRUCTURE, "missing field: agent_claim",
    ),
    BypassRoute(
        "ES-R3", "EVIDENCE-STRUCTURE",
        "gate evidence submitted with no branch, so the claim names no line of work",
        lambda root: {k: v for k, v in _base().items() if k != "branch"},
        STRUCTURE, "missing field: branch",
    ),
)


#: Routes whose second guard is a circumstance rather than a mechanism, and so
#: would fall away when the circumstance changes. Empty: the one entry this held
#: was a prediction, and the prediction was wrong. See CORRECTED_PREDICTIONS.
CONDITIONAL_GUARDS: dict[str, str] = {}

#: Routes held by more than one mechanism inside the same named guard, with the
#: measurement that established it.
#:
#: A second mechanism is not a defect and is not removed. It is recorded so that
#: a test which neuters one of them and finds the route still denying reads as
#: the measured result rather than as a route naming the wrong guard.
REDUNDANT_GUARDS: dict[str, str] = {
    "PS-R1": (
        "Measured 2026-09-24: validate_evidence_structure holds PS-R1 twice over. "
        "Dropping the key entirely trips the required-field list ('missing field: "
        "prompt_stack') and validate_prompt_stack_binding ('prompt_stack binding "
        "required'), and each denies on its own. PS-R2, which keeps the key and "
        "tampers with the digest, is held by the binding validator alone. This entry "
        "exists because the prediction written first - that neutering the binding "
        "validator would open both routes - was refuted by the run, and the test was "
        "corrected to the measurement rather than the measurement to the test."
    ),
}

#: Predictions this module made and the measurements that refuted them.
#:
#: Kept in code rather than quietly deleted. A wall whose whole purpose is that
#: claims must be checked does not get to drop its own failed claim out of the
#: record — that is the fabrication it exists to catch, applied to itself.
CORRECTED_PREDICTIONS = {
    "P10-R2-conditional-guard": (
        "Predicted 2026-09-23, before the tranche was set: P10-R2 is guarded twice only "
        "because validation_capital is unset, so setting it would drop the route from two "
        "guards to one and leave SC-I3 holding it alone. This was stated in the spec, in "
        "capital-rules.json, in PR #13 and to the Founder. "
        "MEASURED AFTER SETTING IT: false. Neutering either guard alone still leaves the "
        "route denying. The capital detector's hold on it was never VC-P1 (the unset "
        "tranche) but VC-P2 — the pack is carried by evidence that does not declare "
        "capital_gate — which is structural and does not depend on the tranche at all. "
        "The reasoning was plausible and untested; the number of guards did not change."
    ),
}


def routes_for(principle: str) -> tuple[BypassRoute, ...]:
    return tuple(r for r in ROUTES if r.principle == principle)


@contextlib.contextmanager
def route_guard(route: BypassRoute, root: Path):
    """Apply a route's source drift and stubs around evaluation, not construction."""
    ctx = contextlib.nullcontext() if route.around is None else route.around(root)
    with ctx:
        with apply_stubs(route.stubs):
            yield


def evaluate_route(route: BypassRoute, root: Path):
    """Build the evidence first, then evaluate it under the route's guard."""
    evidence = route.build(root)
    with route_guard(route, root):
        return evaluate_gate(evidence)


# --------------------------------------------------------------------------
# the claim gate
# --------------------------------------------------------------------------


def enforced_principles(rules: dict[str, Any] | None = None) -> list[str]:
    """Principle ids currently claiming ENFORCED in the governance artifact."""
    if rules is None:
        rules = json.loads(CAPITAL_RULES.read_text(encoding="utf-8"))
    return [p["id"] for p in rules["principles"] if p.get("enforcement") == "ENFORCED"]


def unproven_claims(rules: dict[str, Any] | None = None) -> list[str]:
    """ENFORCED principles with no registered routes.

    This is the inversion the wall exists for: ENFORCED stops being a word
    typed into a file and becomes a status that has to be earned.
    """
    covered = {r.principle for r in ROUTES}
    return sorted(p for p in enforced_principles(rules) if p not in covered)


def evidence_expiry_days(rules: dict[str, Any] | None = None) -> int | None:
    """The preregistered evidence lifetime, or None when none is set.

    A missing, non-integer or non-positive value is None rather than a default.
    Returning a computed default here would be the sourceless number UPTM-002
    exists to catch: the lifetime is a Founder parameter or it is nothing.
    """
    if rules is None:
        rules = json.loads(CAPITAL_RULES.read_text(encoding="utf-8"))
    days = rules.get("evidence_expiry_days")
    if not isinstance(days, int) or isinstance(days, bool) or days <= 0:
        return None
    return days


def evidence_expiry(
    rules: dict[str, Any] | None = None, *, generated_at: datetime | None = None
) -> str | None:
    """P12 expiry as a timestamp, or None when no lifetime is preregistered.

    A timestamp rather than a phrase. The earlier version returned
    "N days from generated_at", which reads like an expiry and cannot be
    compared to anything - an expiry nothing can evaluate is decorative, which
    is the same defect as a status word nobody earned.
    """
    days = evidence_expiry_days(rules)
    if days is None:
        return None
    stamp = generated_at or datetime.now(timezone.utc)
    return (stamp + timedelta(days=days)).isoformat()


def expiry_status(manifest_payload: dict[str, Any], *, now: datetime | None = None) -> str:
    """``VALID``, ``EXPIRED`` or ``UNKNOWN`` for an artifact already generated.

    Three-valued on purpose, and ``UNKNOWN`` is not a soft ``VALID``: an
    artifact carrying no expiry, or one this cannot parse, has not been shown to
    be current. Under runner.verdict that dominates PASS and denies.
    """
    expires_at = manifest_payload.get("expires_at")
    if not isinstance(expires_at, str) or not expires_at:
        return "UNKNOWN"
    try:
        deadline = datetime.fromisoformat(expires_at)
    except ValueError:
        return "UNKNOWN"
    if deadline.tzinfo is None:
        return "UNKNOWN"
    return "VALID" if (now or datetime.now(timezone.utc)) < deadline else "EXPIRED"


def run_routes(root: Path) -> list[dict[str, Any]]:
    """Drive the real gate down every route and record what came back."""
    results: list[dict[str, Any]] = []
    for route in ROUTES:
        outcome = evaluate_route(route, root)
        results.append(
            {
                "route_id": route.route_id,
                "principle": route.principle,
                "description": route.description,
                "verdict": outcome.verdict.value,
                "decision": outcome.decision.value,
                "expected_check": route.expect,
                "denied_by_its_own_check": any(
                    route.expect in reason for reason in outcome.reasons
                ),
                "guards": list(route.guards),
                "guard_count": len(route.guards),
                "conditional_guard": CONDITIONAL_GUARDS.get(route.route_id),
                "redundant_guard": REDUNDANT_GUARDS.get(route.route_id),
                "blocked_by": route.blocked_by,
            }
        )
    return results


def manifest(
    results: list[dict[str, Any]],
    *,
    provenance: HeadProvenance,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """The evidence artifact. Names the commit the repository was at, not one it
    was told to name; carries no expiry, and says why.

    ``provenance`` is not an argument the caller can answer freely. It is read
    from the repository by ``runner.provenance.read_head``, and every reason to
    doubt it travels with it into the artifact.
    """
    rules = json.loads(CAPITAL_RULES.read_text(encoding="utf-8"))
    stamp_dt = generated_at or datetime.now(timezone.utc)
    stamp = stamp_dt.isoformat()
    return {
        "spec": "docs/specs/UPTM-006-enforcement-evidence.md",
        "generated_at": stamp,
        "evaluated_head": provenance.evaluated_head,
        "head_provenance": {
            "source": provenance.source,
            "tree_clean": provenance.tree_clean,
            "dirty_paths": list(provenance.dirty_paths),
            "disputed_head": provenance.disputed_head,
            "problems": list(provenance.problems),
        },
        "rule_a": (
            "Evidence Rule A (onlinovosk-bit/onlinovosk-bit-uptm, docs/EVIDENCE_RULE_A.md) "
            "has two halves. Adopted: the evaluated head is read from the repository, never "
            "asserted by the caller. Not applicable: the ban on a field meaning 'the commit "
            "that contains me' — this artifact is never committed (evidence/enforcement/ is "
            "ignored), so the self-SHA regress it forbids cannot arise here. "
            "See docs/evidence-rule-a.md."
        ),
        "expires_at": evidence_expiry(rules, generated_at=stamp_dt),
        "expiry_days": evidence_expiry_days(rules),
        "dependencies": dependency_digests(),
        "determinism": determinism_declaration(),
        "staleness_note": (
            "expires_at answers how old this is; dependencies answers whether it still "
            "describes the system. An artifact can sit well inside its seven days and "
            "describe a gate that has since been rewritten, so both are carried. The "
            "dependency set is derived by walking the repository, never listed in "
            "source: a list someone must remember to update is the same failure as a "
            "status word someone types. See runner.staleness and "
            "docs/specs/UPTM-007-stale-invalidation.md."
        ),
        "expiry_note": (
            "P12 requires a commit and an expiry. The commit is evaluated_head above, read "
            "from the repository. The expiry is a timestamp computed from generated_at plus "
            "evidence_expiry_days, set by the Founder to 7 on 2026-09-24 to match the "
            "kill-switch drill cadence, so evidence never outlives the drill it rests on. "
            "An artifact with no expires_at is UNKNOWN under expiry_status, not valid. "
            "P12 stays PARTIAL: expiry is satisfied, STALE invalidation on dependency "
            "change is not - evidence can be inside its seven days and still describe code "
            "that has moved."
        ),
        "claims_checked": enforced_principles(rules),
        "unproven_claims": unproven_claims(rules),
        "routes": results,
        "does_not_establish": (
            "That the route list is complete. Every enumerated route denies; a route nobody "
            "thought of is not covered. This manifest advances no principle's status."
        ),
    }
