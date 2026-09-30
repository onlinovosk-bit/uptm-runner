"""Proof that the guard tests are load-bearing — run in CI, not on request.

CLAUDE.md states the rule this module enforces: *deklarované ≠ vynútené*, and a
new gate is proven by mutation — break it and show the suite catches it. The
suite already carries spy and disconnection tests for that. What nothing carried
until now is a check that those tests **still** catch anything.

A green suite cannot tell the difference between a guard that works and a guard
whose test was deleted, renamed, skipped, or quietly weakened. Both read as
green. The only way to tell them apart is to break the guard on purpose and
require the named tests to go red.

So each case below breaks one mechanism in the source and names the tests whose
job is to notice. The gate fails when:

- the anchor no longer matches — the code was refactored and the mutation no
  longer bites, so the case is stale and a human has to re-aim it. Silently
  skipping it is the failure mode this module exists to prevent;
- the suite stays green under mutation — the mechanism is not load-bearing;
- a named sentinel does not fail — something else caught the mutation, and the
  test that was supposed to has stopped doing its job.

Extra failures beyond the sentinels are fine and expected: a disconnected guard
tends to trip several proofs at once. Only their *absence* is a finding.

The source is restored in a ``finally`` and the restoration is verified byte for
byte before the next case runs, so a crash mid-case cannot leave a mutated tree
behind.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

from contextlib import contextmanager

from runner.paths import ROOT

FAILED_LINE = re.compile(r"^FAILED\s+(\S+)", re.MULTILINE)


class MutationAnchorError(RuntimeError):
    """The text a mutation rewrites is no longer present, or is ambiguous.

    Raised rather than skipped: a mutation that cannot be applied proves
    nothing, and a gate that shrugs at it is worse than no gate, because it
    reports success.
    """


@dataclass(frozen=True)
class Mutation:
    """One deliberate break, and the tests required to notice it."""

    mutation_id: str
    claim: str
    path: str
    anchor: str
    replacement: str
    sentinels: tuple[str, ...]


@dataclass
class MutationResult:
    mutation_id: str
    claim: str
    applied: bool
    suite_failed: bool
    missing_sentinels: tuple[str, ...] = ()
    caught_by: tuple[str, ...] = ()
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.applied and self.suite_failed and not self.missing_sentinels

    def as_dict(self) -> dict:
        return {
            "mutation_id": self.mutation_id,
            "claim": self.claim,
            "ok": self.ok,
            "applied": self.applied,
            "suite_failed": self.suite_failed,
            "missing_sentinels": list(self.missing_sentinels),
            "caught_by": list(self.caught_by),
            "error": self.error,
        }


MUTATIONS: tuple[Mutation, ...] = (
    Mutation(
        mutation_id="evidence-binding-unverified",
        claim=(
            "UPTM-008's check is what makes the gate read the files[] binding every "
            "artifact declares. Remove the call and the gate returns to accepting a "
            "digest computed from nothing - which is what it did until 2026-09-24."
        ),
        path="runner/gates.py",
        anchor="    binding = binding_errors(evidence)\n",
        replacement="    binding = []  # mutation-gate: binding left unverified\n",
        sentinels=(
            "tests/test_binding.py::test_g4_the_fabricated_digest_that_passed_before_this_wall_now_denies",
            "tests/test_binding.py::test_g2_a_changed_declared_file_denies_and_names_the_path",
            "tests/test_binding.py::test_g7_neutering_the_binding_check_opens_a_denying_gate",
            "tests/test_binding.py::test_r1_p12_has_a_route_per_violation_shape_each_denying_by_its_own_check",
        ),
    ),
    Mutation(
        mutation_id="capital-detectors-disconnected",
        claim=(
            "The validation-capital detectors are what deny the P8/P10 routes. "
            "Disconnect them and the routes must stop denying for their own reason."
        ),
        path="runner/gates.py",
        anchor=(
            '    pack = evidence.get("capital")\n'
            '    if pack is None and evidence.get("capital_gate") is not True:\n'
            "        return Verdict.PASS, []\n"
        ),
        replacement=(
            "    return Verdict.PASS, []  # mutation-gate: detectors disconnected\n"
            '    pack = evidence.get("capital")\n'
            '    if pack is None and evidence.get("capital_gate") is not True:\n'
            "        return Verdict.PASS, []\n"
        ),
        sentinels=(
            "tests/test_detector_invocation.py::test_gate_actually_calls_the_validation_capital_detector",
            "tests/test_detector_invocation.py::test_gate_verdict_depends_on_what_the_capital_detector_returns",
            "tests/test_enforcement_evidence.py::test_every_route_denies_for_its_own_reason",
            "tests/test_enforcement_evidence.py::test_neutering_the_named_guards_opens_the_route",
        ),
    ),
    Mutation(
        mutation_id="prompt-stack-binding-disconnected",
        claim=(
            "APS-001's binding check is what holds the prompt-stack routes. Drop the "
            "call and the binding proofs must fail rather than the structural checks "
            "quietly covering for it."
        ),
        path="runner/evidence.py",
        anchor="    errors.extend(validate_prompt_stack_binding(evidence))\n",
        replacement="    pass  # mutation-gate: binding check disconnected\n",
        sentinels=(
            "tests/test_enforcement_evidence.py::test_the_binding_check_itself_is_what_holds_the_prompt_stack_routes",
            "tests/test_prompt_stacks.py::test_pass_without_prompt_stack_binding_rejected",
            "tests/test_prompt_stacks.py::test_evidence_binding_rejects_tampered_digest",
            "tests/test_prompt_stacks.py::test_stack_body_change_without_manifest_update_invalidates_evidence",
        ),
    ),
    Mutation(
        mutation_id="kill-switch-detectors-disconnected",
        claim=(
            "The UPTM-003 detectors are what deny the kill-switch routes, and the "
            "drill check folds in through the same call. Disconnect them and both "
            "the spy proofs and the routes that name them must go red."
        ),
        path="runner/gates.py",
        anchor=(
            '    pack = evidence.get("kill_switch")\n'
            "    if pack is None:\n"
            "        return Verdict.PASS, []\n"
        ),
        replacement=(
            "    return Verdict.PASS, []  # mutation-gate: detectors disconnected\n"
            '    pack = evidence.get("kill_switch")\n'
            "    if pack is None:\n"
            "        return Verdict.PASS, []\n"
        ),
        sentinels=(
            "tests/test_detector_invocation.py::test_gate_actually_calls_the_kill_switch_detector",
            "tests/test_detector_invocation.py::test_gate_verdict_depends_on_what_the_kill_switch_detector_returns",
            "tests/test_detector_invocation.py::test_gate_actually_calls_the_drill_detector",
            "tests/test_enforcement_evidence.py::test_every_route_denies_for_its_own_reason",
            "tests/test_enforcement_evidence.py::test_neutering_the_named_guards_opens_the_route",
        ),
    ),
    Mutation(
        mutation_id="scope-detector-disconnected",
        claim=(
            "The UPTM-005 scope detector runs on every gate, unconditionally — that "
            "is the point, since the walls it serves were steppable around while it "
            "ran only when handed something. Disconnect it and both the spy proofs "
            "and the six routes that name it must go red."
        ),
        path="runner/gates.py",
        anchor="    outcomes = detect_scope(evidence)\n",
        replacement=(
            "    return Verdict.PASS, []  # mutation-gate: detector disconnected\n"
            "    outcomes = detect_scope(evidence)\n"
        ),
        sentinels=(
            "tests/test_scope_declaration.py::test_gate_actually_calls_the_scope_detector",
            "tests/test_scope_declaration.py::test_gate_verdict_depends_on_what_the_scope_detector_returns",
            "tests/test_enforcement_evidence.py::test_every_route_denies_for_its_own_reason",
            "tests/test_enforcement_evidence.py::test_neutering_the_named_guards_opens_the_route",
        ),
    ),
    Mutation(
        mutation_id="ks-i3b-invariant-disconnected",
        claim=(
            "KS-I3b is the invariant rather than the mechanism: it refuses to emit "
            "PASS while the stop reads ENGAGED, and by design it can only fire on a "
            "governance bug. That makes it the thinnest-held guard in the file — "
            "measured, three tests catch its removal where the others are caught by "
            "twenty-odd. Exactly the shape a silent regression survives."
        ),
        path="runner/gates.py",
        anchor=(
            '    if verdict is Verdict.PASS and stop_is_engaged(evidence.get("kill_switch") or {}):\n'
            "        verdict = Verdict.FAIL\n"
            "        reasons.append(\n"
            '            "gate_bypass_attempt: a PASS verdict was produced while the kill switch reads ENGAGED"\n'
            "        )\n"
        ),
        replacement="    pass  # mutation-gate: KS-I3b invariant disconnected\n",
        sentinels=(
            "tests/test_detector_invocation.py::test_ks_i3b_refuses_a_pass_produced_while_the_stop_is_engaged",
            "tests/test_enforcement_evidence.py::test_neither_guard_alone_opens_a_doubly_guarded_route",
            "tests/test_enforcement_evidence.py::test_one_guard_alone_does_not_open_the_doubly_guarded_route",
        ),
    ),
    Mutation(
        mutation_id="required-fields-check-disconnected",
        claim=(
            "The required-field list is the structural arm of validate_evidence_structure "
            "— the other mechanism holding PS-R1, and the only thing standing between a "
            "gate and evidence with no commit_sha, no agent_claim and no branch. Those "
            "three, measured: neuter the guard and each is let through. Not probes or "
            "results — their absence is also caught by the fabrication detector and the "
            "claim gate, so this arm is not what holds them.\n\n"
            "This case was added while the arm was unrouted, and the measurement said "
            "so: disabling all fourteen required fields was caught by two tests, both "
            "PS-R1 redundancy bookkeeping about prompt_stack, with no route proof "
            "failing at all. The sentinels then were what existed rather than what "
            "ought to.\n\n"
            "ES-R1 to ES-R3 and the per-field assertions closed that, and the same "
            "mutation now fails 25 tests rather than 2. The sentinels below are "
            "re-aimed accordingly: the route proofs and the field assertions, which "
            "are about this arm, in place of the binding-arm proof that only failed "
            "here incidentally. test_each_mechanism_holding_ps_r1_denies_on_its_own "
            "stays because it asserts this mechanism denies on its own, which is the "
            "same property from the other side."
        ),
        path="runner/evidence.py",
        anchor=(
            "    for key in required:\n"
            "        if key not in evidence:\n"
            '            errors.append(f"missing field: {key}")\n'
        ),
        replacement=(
            "    for key in []:  # mutation-gate: required-field check disconnected\n"
            "        if key not in evidence:\n"
            '            errors.append(f"missing field: {key}")\n'
        ),
        sentinels=(
            "tests/test_enforcement_evidence.py::test_every_route_denies",
            "tests/test_enforcement_evidence.py::test_every_route_denies_for_its_own_reason",
            "tests/test_enforcement_evidence.py::test_neutering_the_named_guards_opens_the_route",
            "tests/test_enforcement_evidence.py::test_every_required_field_is_actually_required",
            "tests/test_enforcement_evidence.py::test_each_mechanism_holding_ps_r1_denies_on_its_own",
        ),
    ),
    Mutation(
        mutation_id="swarm-collect-disconnected",
        claim=(
            "APS-007 records a swarm wave in passed_waves only after "
            "collect_and_verify passes. Replace that call with a forced pass and "
            "a missing claim ledger records the wave."
        ),
        path="runner/fsm.py",
        anchor="        return dispatch.collect_and_verify(dict(artifacts or {}))\n",
        replacement=(
            "        return SwarmCollectResult(\n"
            "            wave_id=wave_id, passed=True, reasons=()\n"
            "        )  # mutation-gate: collect disconnected\n"
        ),
        sentinels=(
            "tests/test_fsm.py::test_fsm_actually_calls_collect_and_verify",
            "tests/test_fsm.py::test_failing_collect_does_not_record_passed_wave",
            "tests/test_fsm.py::test_passed_wave_depends_on_collect_result",
        ),
    ),
    Mutation(
        mutation_id="listed-agents-dispatch-disconnected",
        claim=(
            "APS-008 refuses to record a wave whose yaml lists agents when no "
            "SwarmDispatch is bound. Disconnect that check and a PASS gate records "
            "the wave with no ledger."
        ),
        path="runner/fsm.py",
        anchor="        elif _wave_lists_agents(self.current_wave):\n",
        replacement=(
            "        elif False and _wave_lists_agents(self.current_wave):"
            "  # mutation-gate: listed agents disconnected\n"
        ),
        sentinels=(
            "tests/test_fsm.py::test_fsm_actually_checks_listed_agents",
            "tests/test_fsm.py::test_listed_agents_without_dispatch_does_not_record",
            "tests/test_fsm.py::test_passed_wave_depends_on_listed_agent_check",
        ),
    ),
    Mutation(
        mutation_id="agent-id-match-disconnected",
        claim=(
            "APS-009 records a listed-agent wave only when claim agent_ids equal "
            "ownership.agents. Disconnect that comparison and a ledger under "
            "another name records the wave."
        ),
        path="runner/fsm.py",
        anchor="            mismatch = _agent_ledger_mismatch(self.current_wave, dispatch)\n",
        replacement=(
            "            mismatch = None  # mutation-gate: agent id match disconnected\n"
        ),
        sentinels=(
            "tests/test_fsm.py::test_fsm_actually_compares_claim_agent_ids",
            "tests/test_fsm.py::test_claim_agent_id_must_match_listed_agents",
            "tests/test_fsm.py::test_passed_wave_depends_on_agent_id_match",
        ),
    ),
    Mutation(
        mutation_id="empty-agents-require-dispatch",
        claim=(
            "DEC-UPTM-APS-010 keeps an empty ownership.agents list on the gate. "
            "Treat that empty list as a required swarm and a wave that named "
            "nobody stops recording."
        ),
        path="runner/fsm.py",
        anchor="    return len(declared) > 0\n",
        replacement="    return True  # mutation-gate: empty agents treated as a swarm\n",
        sentinels=(
            "tests/test_fsm.py::test_empty_agent_list_still_records_without_dispatch",
            "tests/test_fsm.py::test_terminating_fsm_reaches_exit_after_all_waves_pass",
        ),
    ),
    Mutation(
        mutation_id="map-q1-reopened",
        claim=(
            "Re-aimed by UPTM-015 after the Founder closed the question. It used "
            "to guard that nobody adopted an answer; it now guards that nobody "
            "reverts the one that was adopted.\n\n"
            "DEC-UPTM-MAP-Q1 is YES: a trading-system wave gate must satisfy the "
            "capital constitution. Reverting it to open would quietly restore the "
            "reading in which P8 and P10 - two of the three principles that are "
            "actually ENFORCED - are enforced against something that never runs."
        ),
        path="docs/architecture/governance-map.md",
        anchor="   **DECIDED (DEC-UPTM-MAP-Q1, 2026-09-28): YES.** Founder GO to close it.\n",
        replacement=(
            "   **OPEN (DEC-UPTM-MAP-Q1, 2026-09-25):** neither answer is adopted.\n"
        ),
        sentinels=(
            "tests/test_governance.py::test_map_q1_is_decided_yes_and_claims_no_mechanism",
            "tests/test_cross_repository.py::test_g1_q1_is_adopted_yes_with_the_reason_that_no_empties_the_runner",
            "tests/test_cross_repository.py::test_g8_the_map_does_not_still_call_q1_or_q2_open",
        ),
    ),
    Mutation(
        mutation_id="map-q5-given-a-canonical-numbering",
        claim=(
            "Re-aimed by UPTM-016 after the Founder closed the question. The "
            "closure keeps 'neither numbering is canonical' - picking one was "
            "always the wrong fix, not merely an unmade choice - so the "
            "dangerous edit is unchanged in substance: naming a canonical "
            "numbering.\n\n"
            "Marking 0-7 canonical names the other repository's waves, over a "
            "repository this one cannot read, and it would not remove the "
            "ambiguity from a single status line already written."
        ),
        path="docs/architecture/governance-map.md",
        anchor="   AT SOURCE.** Founder GO to close it. **Neither numbering is canonical** —\n",
        replacement=(
            "   AT SOURCE.** Founder GO to close it. **Waves 0-7 are canonical** —\n"
        ),
        sentinels=(
            "tests/test_governance.py::test_map_q5_is_decided_without_a_canonical_numbering",
            "tests/test_wave_names.py::test_n8_q5_is_recorded_decided_in_both_places",
        ),
    ),
    Mutation(
        mutation_id="map-q3-turned-into-a-ceiling",
        claim=(
            "Re-aimed by UPTM-017 after the Founder closed the question with "
            "option C. The relation adopted is a FLOOR - the declared account "
            "must be at least the tranche - and the dangerous edit is the option "
            "that was not chosen: making EUR 700 a ceiling on the other "
            "repository's account.\n\n"
            "That would impose a change on a repository this one cannot read and "
            "has no authority over, which is exactly what MAP-Q1 and MAP-Q2 "
            "settled against. The floor needs no authority there: it refuses a "
            "configuration rather than commanding anyone."
        ),
        path="docs/architecture/governance-map.md",
        anchor="   **DECIDED (DEC-UPTM-MAP-Q3, 2026-09-29): THE ACCOUNT IS A FLOOR UNDER THE\n",
        replacement="   **DECIDED (2026-09-29): €700 IS A CEILING ON THE ACCOUNT, AND THE\n",
        sentinels=(
            "tests/test_governance.py::test_map_q3_is_decided_as_a_floor_and_copies_no_number",
        ),
    ),
    Mutation(
        mutation_id="map-q3-relation-reads-unadopted-again",
        claim=(
            "UPTM-018a. The map's numbers paragraph said DEC-UPTM-MAP-Q3 'leaves "
            "that relation unadopted' after the same label had been decided as a "
            "floor two screens below - true on 2026-09-25, false from UPTM-017. "
            "This puts the original sentence back.\n\n"
            "It is a different mutation from map-q3-turned-into-a-ceiling and "
            "the difference is the point: that case edits the decision inside "
            "question 3's block, which the older one-sided test slices and "
            "reads. This one edits outside the slice, which that test cannot "
            "see. Measured by hand under this exact mutation: the older test "
            "stays green, the two-sided guard goes red."
        ),
        path="docs/architecture/governance-map.md",
        anchor=(
            "**DEC-UPTM-MAP-Q3 relates them as a floor:** a declared account must be at\n"
            "least the tranche, or the configuration is refused (VC-I6). The account in that\n"
        ),
        replacement=(
            "**DEC-UPTM-MAP-Q3 leaves that relation unadopted.** Whether the tranche is a\n"
            "ceiling on the envelope, a subset of it, or an independent limit is not decided\n"
            "here. The account in that\n"
        ),
        sentinels=(
            "tests/test_governance_map_consistency.py::test_g1_no_label_in_the_map_is_asserted_both_decided_and_open",
            "tests/test_governance_map_consistency.py::test_r1_the_numbers_paragraph_states_the_relation_that_was_adopted",
            "tests/test_governance_map_consistency.py::test_r2_the_numbers_paragraph_carries_no_openness_wording",
        ),
    ),
    Mutation(
        mutation_id="capital-note-claims-unset-again",
        claim=(
            "UPTM-018. The note beside the validation-capital detector said the "
            "tranche parameters were 'unset. Every capital gate denies until all "
            "three are set' for the week after the Founder set them, and a handover "
            "later believed the 700 EUR tranche was still open because of it. This "
            "puts the original sentence back.\n\n"
            "The suite was green with that sentence in place - measured before the "
            "guard existed - so nothing looked at the record. The guard makes the "
            "note's status word equal the state of the three parameters it "
            "describes, in both directions, so a stale note cannot pass and a "
            "correct one cannot be broken by tidying."
        ),
        path="constitution/capital-rules.json",
        anchor='"founder_parameter_required": "SATISFIED 2026-09-23 (DEC-UPTM-004): the Founder set',
        replacement=(
            '"founder_parameter_required": "validation_capital.amount, .currency and '
            '.applies_to are unset. Every capital gate denies until all three are '
            'set. (DEC-UPTM-004): the Founder set'
        ),
        sentinels=(
            "tests/test_capital_parameter_status.py::test_g1_the_note_in_the_real_file_agrees_with_the_real_parameters",
            "tests/test_capital_parameter_status.py::test_a1_the_note_is_dated_and_names_the_decision_that_satisfied_it",
        ),
    ),
    Mutation(
        mutation_id="map-q2-given-a-winner",
        claim=(
            "Re-aimed by UPTM-015 after the Founder closed the question. The "
            "answer adopted is NEITHER WINS, so the dangerous edit is no longer "
            "'decide it' but 'decide it the other way'.\n\n"
            "A disagreement between two verdicts is not a tie to be broken, it is "
            "uncertainty, and P11 halts on uncertainty. Naming a winner would let "
            "one repository's PASS overrule the other's DENY - which is the one "
            "reading the closure exists to forbid."
        ),
        path="docs/architecture/governance-map.md",
        anchor="   **DECIDED (DEC-UPTM-MAP-Q2, 2026-09-28): NEITHER WINS.** Founder GO to\n",
        replacement=(
            "   **DECIDED (2026-09-28):** the uptm-runner `PASS` wins the "
            "disagreement. Founder GO to\n"
        ),
        sentinels=(
            "tests/test_governance.py::test_map_q2_is_decided_neither_wins",
            "tests/test_cross_repository.py::test_g2_q2_is_adopted_neither_wins_and_derived_rather_than_chosen",
        ),
    ),
    Mutation(
        mutation_id="syntax-gate-stops-parsing",
        claim=(
            "UPTM-009's parse of every .py is what stops an unreadable file from "
            "reaching pytest. Remove it and the gate goes back to reporting success "
            "on a tree it never read - which is worse than having no gate, because a "
            "green step now says the files were checked.\n\n"
            "This guard enforces no constitution principle, so it has no route "
            "through evaluate_gate and is deliberately not in NON_PRINCIPLE_GUARDS: "
            "it decides nothing about evidence, only whether CI can run at all. "
            "DEC-UPTM-APS's rule still applies - a guard nobody can break on purpose "
            "is a guard whose removal is silent - and this case is how it is met."
        ),
        path="runner/syntax_gate.py",
        anchor="            ast.parse(source, filename=str(path))\n",
        replacement="            pass  # mutation-gate: python files no longer parsed\n",
        sentinels=(
            "tests/test_syntax_gate.py::test_g1_a_python_file_that_does_not_parse_is_named_with_its_line",
            "tests/test_syntax_gate.py::test_r1_the_shape_that_swallowed_482_tests_is_reported",
            "tests/test_syntax_gate.py::test_g5_every_problem_is_reported_not_only_the_first",
        ),
    ),
    Mutation(
        mutation_id="schema-faults-swallowed",
        claim=(
            "UPTM-010 is what makes a schema the gate cannot load deny instead of "
            "pass. Remove the call and the blanket `except Exception: pass` is back "
            "in effect: schemas/evidence.schema.json did not parse for a day and "
            "every run still reported success.\n\n"
            "Only the fault path is load-bearing. Evidence that merely fails to "
            "match a loadable schema stays soft on purpose - measured, 183 of the "
            "suite's evaluations do, most on packs the schema has never been "
            "taught - so no sentinel here asserts anything about mismatch."
        ),
        path="runner/evidence.py",
        anchor="    errors.extend(_schema_errors(evidence))\n",
        replacement="    pass  # mutation-gate: schema faults swallowed again\n",
        sentinels=(
            "tests/test_schema_load.py::test_s1_a_schema_that_does_not_parse_is_reported_with_its_line",
            "tests/test_schema_load.py::test_s4_jsonschema_not_importable_is_a_fault_not_a_pass",
            "tests/test_schema_load.py::test_s6_the_fault_denies_the_gate",
            "tests/test_schema_load.py::test_s7_a_fault_is_reported_once_not_once_per_field",
        ),
    ),
    Mutation(
        mutation_id="pattern-ladder-ordering-dropped",
        claim=(
            "UPTM-011's ladder is ordered on purpose: an axis may rise above its "
            "floor only when every earlier axis stands at its top. Drop the "
            "ordering and the six axes become six independent labels, which is the "
            "single flat `status: UNVERIFIED` again in a longer costume - a "
            "candidate could carry MEASURED_AFTER_COSTS while no_leakage still "
            "read NOT_TESTED, i.e. a return measured with information the strategy "
            "could not have had at decision time."
        ),
        path="runner/pattern_contract.py",
        anchor="            if status[earlier] != top(earlier):\n",
        replacement="            if False:  # mutation-gate: ladder ordering dropped\n",
        sentinels=(
            "tests/test_pattern_contract.py::test_c5_no_axis_rises_while_any_earlier_axis_is_at_its_floor",
            "tests/test_pattern_contract.py::test_c5_performance_needs_the_whole_ladder_beneath_it",
        ),
    ),
    Mutation(
        mutation_id="pattern-undefined-root-ignored",
        claim=(
            "The root UPTM-011 exists to expose: every one of the seven reversal "
            "formations is written in swing highs and lows, and none can be "
            "evaluated until *swing* is mechanically defined. This check is what "
            "stops `rules` reading MECHANICAL over terms nobody has pinned down. "
            "Remove it and a contract can declare itself evaluable while the "
            "sequence it declares rests on UNDEFINED."
        ),
        path="runner/pattern_contract.py",
        anchor='    if still_undefined and status["rules"] != UNDEFINED:\n',
        replacement="    if False:  # mutation-gate: undefined terms no longer block rules\n",
        sentinels=(
            "tests/test_pattern_contract.py::test_c2_deleting_a_term_does_not_define_it",
            "tests/test_pattern_contract.py::test_c3_rules_cannot_leave_undefined_while_the_root_is_undefined",
            "tests/test_pattern_contract.py::test_c4_an_unseen_contract_is_held_to_the_same_root",
        ),
    ),
    Mutation(
        mutation_id="swing-confirmation-lag-removed",
        claim=(
            "UPTM-012's `confirmed_at` is the whole reason the module exists. A "
            "swing high at bar i is not knowable at bar i - the bars to its right "
            "have not happened. Collapse the lag to the bar the extreme sits on "
            "and every downstream decision reads `pivot_bars` bars of future "
            "information, silently, and reports an edge nobody could have traded.\n\n"
            "The candidate's own no_prediction_principle forbids exactly this: "
            "'swing points confirmed by bars later than the decision timestamp'. "
            "This case is what keeps that sentence from becoming decoration."
        ),
        path="runner/swing.py",
        anchor="                confirmed_at=index + reach,\n",
        replacement="                confirmed_at=index,  # mutation-gate: lag removed\n",
        sentinels=(
            "tests/test_swing.py::test_s3_confirmation_is_the_extreme_plus_the_right_hand_window",
            "tests/test_swing.py::test_s4_what_is_knowable_at_t_is_what_a_detector_at_t_could_have_found",
            "tests/test_swing.py::test_s4_the_invariant_also_holds_with_an_amplitude_filter_in_play",
            "tests/test_swing.py::test_s4_a_swing_is_not_knowable_on_the_bar_it_sits_on",
            "tests/test_swing.py::test_s8_the_confirmation_lag_is_a_consequence_of_the_parameter_not_a_constant",
        ),
    ),
    Mutation(
        mutation_id="swing-plateau-accepted",
        claim=(
            "UPTM-012 chose that a plateau yields no swing: a tie is not an "
            "extreme, and picking one of two equal bars is a rule a later reader "
            "cannot reconstruct from the data. The choice is one character wide - "
            "`<` against `<=` - so a refactor can flip it without anything else "
            "in CI noticing. One test stands between the definition and a "
            "different definition wearing its name."
        ),
        path="runner/swing.py",
        anchor="            bars[other].high < pivot\n",
        replacement="            bars[other].high <= pivot  # mutation-gate: ties accepted\n",
        sentinels=("tests/test_swing.py::test_s2_a_plateau_yields_no_swing",),
    ),
    Mutation(
        mutation_id="unconnected-source-may-produce-numbers",
        claim=(
            "Directive 4's rule, mechanically: a source that is not CONNECTED may "
            "not produce a number. UPTM-013 wrote ES/MES into a map, and writing a "
            "source down is exactly when it starts to read like a source we have - "
            "four vendors named, four questions open, nothing contracted, no data. "
            "Remove this refusal and MAPPED_UNVERIFIED buys a detector."
        ),
        path="runner/data_sources.py",
        anchor=(
            '    return source.get("connection_state") == CONNECTED and not '
            "state_errors(source, root)\n"
        ),
        replacement="    return True  # mutation-gate: unconnected source now runs\n",
        sentinels=(
            "tests/test_data_sources.py::test_d3_every_rung_below_connected_refuses_the_detector",
            "tests/test_data_sources.py::test_d3_the_real_record_refuses_today",
            "tests/test_data_sources.py::test_d3_a_malformed_record_cannot_read_as_connected",
            "tests/test_data_sources.py::test_d7_the_contract_and_the_source_cannot_disagree",
        ),
    ),
    Mutation(
        mutation_id="connected-no-longer-costs-evidence",
        claim=(
            "CONNECTED is the rung that says data actually reaches this runner. It "
            "costs an artifact and a commit for UPTM-010's reason: a state anyone "
            "can type is one that will eventually be typed optimistically, usually "
            "by someone in a hurry who is not lying. Drop the requirement and the "
            "top rung becomes a word again.\n\n"
            "Preregistered L1 named one case, for the refusal above. This second "
            "mechanism is independent of it - the refusal still holds when the "
            "evidence rule is gone - so one mutation cannot cover both."
        ),
        path="runner/data_sources.py",
        anchor='        for field in ("artifact", "commit"):\n',
        replacement="        for field in ():  # mutation-gate: evidence no longer required\n",
        sentinels=(
            "tests/test_data_sources.py::test_d2_connected_without_evidence_is_an_error_not_a_pass",
            "tests/test_data_sources.py::test_d2_half_the_evidence_is_not_evidence",
        ),
    ),
    Mutation(
        mutation_id="roll-admissibility-always-true",
        claim=(
            "UPTM-014's L1a. `may_use` is what a future detector would ask before "
            "reading a continuous series, and the answer is measured rather than "
            "looked up: build the series at two moments and see whether the "
            "earlier bars survived. Make it always true and a back-adjusted file "
            "- which is what most vendors ship - becomes readable, and with it "
            "every confirmed swing gets repriced by rolls that had not happened "
            "when it was confirmed. That is precisely UPTM-012's S5 undone."
        ),
        path="runner/roll.py",
        anchor="    return not rewrites_history(series, schedule, adjustment)\n",
        replacement="    return True  # mutation-gate: every join is admissible now\n",
        sentinels=(
            "tests/test_roll.py::test_r7_every_member_of_the_family_is_classified_by_measurement",
        ),
    ),
    Mutation(
        mutation_id="roll-as-of-ignored",
        claim=(
            "UPTM-014's L1b, and an independent mechanism from L1a: the refusal "
            "still holds when this one is gone. `build_continuous` takes as_of as "
            "a cut, not a trim - bars after it are never built. Ignore it and the "
            "series handed to a detector contains bars from after the decision "
            "point, which is the leak UPTM-012 spent a whole spec closing, "
            "reopened one layer further down where the swing code cannot see it."
        ),
        path="runner/roll.py",
        anchor="    for index in range(as_of + 1):\n",
        replacement=(
            "    for index in range(len(series[schedule[0].contract])):"
            "  # mutation-gate: as_of ignored\n"
        ),
        sentinels=(
            "tests/test_roll.py::test_r3_no_bar_after_as_of_is_returned",
            "tests/test_roll.py::test_r4_an_admissible_join_never_moves_a_bar_it_has_already_emitted",
        ),
    ),
    Mutation(
        mutation_id="cross-repo-absence-allows",
        claim=(
            "UPTM-015's L1a. MAP-Q2 adopted that an absent counterpart verdict "
            "is not an ALLOW - GOVERNANCE.md C3, silence is not permission. "
            "Remove the check and the resolution reads a missing trading-system "
            "verdict as agreement, which is exactly the state the control plane "
            "is in today: it reaches ALLOW without ever asking."
        ),
        path="runner/cross_repository.py",
        anchor="    if missing:\n",
        replacement="    if False:  # mutation-gate: absence no longer denies\n",
        sentinels=(
            "tests/test_cross_repository.py::test_g4_an_unreadable_verdict_on_either_side_denies",
            "tests/test_cross_repository.py::test_g4_the_missing_side_is_named_not_merely_counted",
            "tests/test_cross_repository.py::test_g4_an_absent_counterpart_is_not_a_dispute",
            "tests/test_cross_repository.py::test_g6_no_trading_system_verdict_is_reachable_from_here",
        ),
    ),
    Mutation(
        mutation_id="cross-repo-allow-overrides-deny",
        claim=(
            "UPTM-015's L1b, independent of L1a: absence still denies when this "
            "one is gone. MAP-Q2 adopted NEITHER WINS, so one side's ALLOW must "
            "never clear the other's DENY. A disagreement is not a tie to be "
            "broken; it is uncertainty, and P11 halts on uncertainty. Let either "
            "ALLOW carry the pair and the control plane can permit what the "
            "trading system just refused."
        ),
        path="runner/cross_repository.py",
        anchor="    if ours is theirs is Decision.ALLOW:\n",
        replacement=(
            "    if Decision.ALLOW in (ours, theirs):"
            "  # mutation-gate: one ALLOW now wins\n"
        ),
        sentinels=(
            "tests/test_cross_repository.py::test_g3_allow_only_when_both_sides_allow",
            "tests/test_cross_repository.py::test_g5_a_disagreement_keeps_both_sides_and_names_neither_a_winner",
        ),
    ),
    Mutation(
        mutation_id="wave-artifact-loses-its-repository",
        claim=(
            "UPTM-016's L1a. MAP-Q5 was closed by putting the qualification in "
            "the data rather than in whoever writes the status line - because "
            "the line is where it failed the first time, when this map's own "
            "author conflated this repository's wave 7 with the trading "
            "repository's W7. Stop requiring a wave file to say which repository "
            "it belongs to and a single field lifted out of it is bare again."
        ),
        path="runner/wave_names.py",
        anchor='        if document.get("repository") != CONTROL_PLANE:\n',
        replacement="        if False:  # mutation-gate: repository no longer required\n",
        sentinels=(
            "tests/test_wave_names.py::test_n2_a_wave_file_that_drops_its_repository_is_a_finding",
        ),
    ),
    Mutation(
        mutation_id="wave-ambiguity-set-hardcoded",
        claim=(
            "UPTM-016's L1b, independent of L1a: the artifacts still declare "
            "their repository when this one is gone. Which numbers are ambiguous "
            "is the intersection of a measured range and a recorded one, so "
            "adding wave8.yaml makes W8 ambiguous with nobody editing a list. "
            "Freeze it to a literal and the set is correct until the day the "
            "tree changes - which is the same rot as a hand-kept dependency set, "
            "silent and in the reassuring direction."
        ),
        path="runner/wave_names.py",
        anchor="    return our_waves(root) & THEIR_WAVES\n",
        replacement=(
            "    return frozenset({0, 1, 2, 3, 4, 5, 6, 7})"
            "  # mutation-gate: set frozen\n"
        ),
        sentinels=(
            "tests/test_wave_names.py::test_n4_adding_a_wave_changes_the_set_without_anyone_editing_a_list",
        ),
    ),
    Mutation(
        mutation_id="drill-freshness-loses-the-wall-clock",
        claim=(
            "P8 is one of the three principles that are actually ENFORCED, and "
            "KS-D2 is what makes an untested kill switch fail rather than pass. "
            "Its reference has to be the wall clock: that is the only clock an "
            "operator can be judged against.\n\n"
            "Added after a repair, not a build. The suite mixed a frozen drill "
            "fixture with the wall clock and stayed green for five days, then "
            "went red at the minute the fixture aged past the cadence - fifteen "
            "minutes after a PR's CI had passed on it. The fix threads an "
            "explicit reference through for tests; this case guards the thing "
            "the fix could have broken, by freezing the default."
        ),
        path="runner/detectors/kill_switch.py",
        anchor=(
            '        return _unknown("KS-D2", ["last_drill_at as an ISO-8601 timestamp"])\n'
            "    reference = now or datetime.now(timezone.utc)\n"
        ),
        replacement=(
            '        return _unknown("KS-D2", ["last_drill_at as an ISO-8601 timestamp"])\n'
            "    reference = now or datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)"
            "  # mutation-gate: default clock frozen\n"
        ),
        sentinels=(
            "tests/test_kill_switch_detector.py::test_without_an_injected_now_a_stale_drill_fails_against_the_wall_clock",
        ),
    ),
    Mutation(
        mutation_id="at-risk-basis-unchecked",
        claim=(
            "UPTM-017's L1a. `aggregate_open_exposure` in applies_to is a switch, "
            "not a definition: it turns on a comparison of at_risk against the "
            "amount and says nothing about the unit. For ES/MES, notional, margin "
            "and risk-to-stop differ by orders of magnitude - EUR 700 means no "
            "trade at all, one contract, or fourteen trades depending which. "
            "Accept any declared basis and P10's exposure half is a number with "
            "no unit again, which is where this started."
        ),
        path="runner/detectors/validation_capital.py",
        anchor="    if basis != AT_RISK_BASIS:\n",
        replacement="    if False:  # mutation-gate: any basis accepted\n",
        sentinels=(
            "tests/test_at_risk_unit_and_floor.py::test_u2_the_two_rejected_bases_are_told_why_not_merely_that",
            "tests/test_at_risk_unit_and_floor.py::test_u2_an_unrecognised_basis_fails_without_inventing_a_reason",
        ),
    ),
    Mutation(
        mutation_id="account-floor-unchecked",
        claim=(
            "UPTM-017's L1b, independent of L1a: the basis is still checked when "
            "this one is gone. Option C, adopted by the Founder - a loss ceiling "
            "halts the test only while the account can reach it. Against the "
            "range recorded in the governance map, an account of 500 can never "
            "reach a 700 ceiling, so what halts the test is the account emptying, "
            "which is not a decision anybody made. Remove the comparison and the "
            "ceiling goes back to being decoration in exactly that case."
        ),
        path="runner/detectors/validation_capital.py",
        anchor="    if equity < amount:\n",
        replacement="    if False:  # mutation-gate: the floor no longer binds\n",
        sentinels=(
            "tests/test_at_risk_unit_and_floor.py::test_u5_an_account_below_the_tranche_fails_and_says_why",
            "tests/test_at_risk_unit_and_floor.py::test_u7_an_account_below_the_tranche_denies_at_the_gate",
        ),
    ),
    Mutation(
        mutation_id="drill-fixture-pinned-to-a-date",
        claim=(
            "Added after a repair, not a build - the second one on the same "
            "cause. The kill-switch drill fixture states its drill as an age "
            "(two days). Pin it to a calendar date and it is fresh on the day "
            "it is written and stale a cadence later: main went red on "
            "2026-09-29 at 12:00Z with no commit landing, after passing CI "
            "hours earlier, and a second pinned date would have done the same "
            "the next morning.\n\n"
            "P8 is one of the three principles that are actually ENFORCED and "
            "these tests are what show the detector is what decides. A fixture "
            "that rots takes that proof with it. Re-pin the date and the guard "
            "must go red on its own, not only through the eight tests that "
            "notice after the fact."
        ),
        path="tests/test_detector_invocation.py",
        anchor='            "last_drill_at": _ago(days=2),\n',
        replacement='            "last_drill_at": "2026-09-22T12:00:00Z",\n',
        sentinels=(
            "tests/test_detector_invocation.py::test_the_drill_fixture_ages_with_the_wall_clock_not_the_calendar",
            "tests/test_detector_invocation.py::test_clear_stop_with_a_recent_drill_passes_the_gate",
        ),
    ),
)


@contextmanager
def applied(mutation: Mutation, root: Path | None = None) -> Iterator[None]:
    """Apply one mutation, then restore the file and verify the restoration.

    The anchor must appear exactly once. Zero means the code moved; more than
    one means the mutation is not aimed at a single place and the result would
    be ambiguous. Both raise.
    """
    target = (root or ROOT) / mutation.path
    original = target.read_bytes()
    text = original.decode("utf-8")
    found = text.count(mutation.anchor)
    if found != 1:
        raise MutationAnchorError(
            f"{mutation.mutation_id}: anchor found {found}x in {mutation.path}, expected 1. "
            "The code changed and this mutation no longer bites — re-aim it."
        )
    try:
        target.write_text(text.replace(mutation.anchor, mutation.replacement), encoding="utf-8")
        yield
    finally:
        target.write_bytes(original)
        if target.read_bytes() != original:  # pragma: no cover - filesystem failure
            raise RuntimeError(f"failed to restore {mutation.path} after {mutation.mutation_id}")


def failed_nodes(pytest_output: str) -> set[str]:
    """Node ids from a pytest run, with parametrisation stripped.

    Sentinels name a test, not a parameter set: a route id that appears or
    disappears should not silently retarget the gate.
    """
    return {FAILED_LINE.match(line).group(1).split("[")[0]  # type: ignore[union-attr]
            for line in pytest_output.splitlines()
            if FAILED_LINE.match(line)}


def _run_pytest(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=no", "-p", "no:cacheprovider"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def run_mutation_gate(
    mutations: tuple[Mutation, ...] = MUTATIONS,
    root: Path | None = None,
    runner: Callable[[Path], subprocess.CompletedProcess[str]] = _run_pytest,
) -> tuple[bool, list[MutationResult], str | None]:
    """Run every mutation. Returns (ok, results, baseline_error).

    The unmutated suite is run first. If it is already red the mutation results
    mean nothing — a test that was failing anyway is not a test that caught the
    mutation — so the gate refuses rather than reporting on noise.
    """
    work = root or ROOT
    baseline = runner(work)
    if baseline.returncode != 0:
        return False, [], "the suite is red before any mutation; fix that first"

    results: list[MutationResult] = []
    for mutation in mutations:
        try:
            with applied(mutation, work):
                proc = runner(work)
        except MutationAnchorError as exc:
            results.append(
                MutationResult(
                    mutation_id=mutation.mutation_id,
                    claim=mutation.claim,
                    applied=False,
                    suite_failed=False,
                    error=str(exc),
                )
            )
            continue

        nodes = failed_nodes(proc.stdout + proc.stderr)
        missing = tuple(s for s in mutation.sentinels if s not in nodes)
        results.append(
            MutationResult(
                mutation_id=mutation.mutation_id,
                claim=mutation.claim,
                applied=True,
                suite_failed=proc.returncode != 0,
                missing_sentinels=missing,
                caught_by=tuple(sorted(n for n in nodes if n in mutation.sentinels)),
            )
        )

    return all(r.ok for r in results) and bool(results), results, None
