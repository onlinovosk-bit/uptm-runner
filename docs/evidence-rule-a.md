# Evidence Rule A in `uptm-runner` — what was adopted, and what was not

**Decided:** 2026-09-24, by the Founder, on the fourth question of
`docs/architecture/governance-map.md`.

Rule A is written in `onlinovosk-bit/onlinovosk-bit-uptm`
(`docs/EVIDENCE_RULE_A.md`). This document records what it means here, because
adopting a rule from another repository without saying which parts of it survive
the move is how two systems end up agreeing in wording and disagreeing in fact —
which is the problem the governance map was written about in the first place.

## Rule A has two halves

**Half one — the artifact must not carry a field meaning "the commit that
contains me."** A commit hash covers the tree that holds the evidence file, so
editing the file to contain that hash changes the tree and changes the hash
again. The regress never terminates. Rule A bans the field names that attempt
it: `evidence_commit_sha`, `tested_head_sha`, `evaluated_head_sha`, `head_sha`,
and `tested_implementation_sha` used to mean "current HEAD".

**Half two — the evaluated head is supplied from outside the artifact**, read
from the checkout at verification time, and the artifact's claims are checked
against it.

## What applies here

**Half two: adopted.** It named a real hole. `enforcement-evidence` took
`--commit` and wrote whatever it was handed into the manifest. Nothing compared
that value to the checkout and nothing looked at the working tree, so a manifest
could name a commit whose code the routes had never run against, and no reader
downstream could tell the difference.

Since this change:

- The evaluated head is **read from the repository** (`git rev-parse HEAD`). It
  is no longer an argument.
- The working tree must be clean. Routes that ran against uncommitted edits ran
  against code that is at no commit, so the artifact evidences no commit and
  says so.
- `--expect-head` is a **cross-check, not a source.** The repository stays
  authoritative; a disagreement is recorded as a dispute in which neither value
  is adopted, and the run fails.
- A head that cannot be established is `null` with a stated reason. It is never
  a plausible default — the same three-valued discipline the gate uses.
- Every reason to doubt the head travels into the artifact under
  `head_provenance`, because doubt that stays in the generating process is doubt
  the auditor never sees.

CI passes no commit at all. It cannot tell the artifact what it evidences; the
artifact can only name the commit that is actually checked out.

**Half one: not applicable, for a reason that could expire.** This artifact is
never committed — `evidence/enforcement/` is in `.gitignore`, because an
artifact pinned to an older commit is stale the moment it lands (P12). The
self-SHA regress needs a *tracked* file to start from, and there is none.

`evaluated_head` is therefore not one of Rule A's banned fields in meaning
either. It names the commit the routes ran against, and the artifact is not part
of that commit.

**This is a conditional, not a permanent exemption.** If
`evidence/enforcement/` ever becomes tracked, the reasoning above collapses and
half one starts applying immediately.
`test_the_artifact_is_not_committed_which_is_why_the_other_half_cannot_apply`
fails on that day, and says what to do.

## A claim of mine that this corrects

`governance-map.md` said the UPTM-006 manifest "can attest to its own
freshness, the exact thing Rule A exists to forbid." The first half of that was
too strong: the manifest never lands in the repository, so it cannot attest to
its own containing commit and the regress Rule A forbids cannot occur here.

The defect was real but adjacent: the commit was **caller-asserted and
unchecked**. Finding a real hole and then naming it as the wrong hole is worth
recording rather than quietly restating — a map that overstates one gap is
harder to trust about the other four. The map has been corrected in place, with
the original claim left visible.

## What this does not do

- It does not change any principle's enforcement status. P8 and P10 are
  `ENFORCED` for the reasons UPTM-005 and UPTM-006 established, and neither
  depends on this.
- It does not set `evidence_expiry_days`. P12 stays `PARTIAL`; `expires_at` is
  still `null` and still says why.
- It does not answer the other four questions in the governance map.
- It grants no capability. `LIVE_TRADING` stays `false` and
  `CONSTITUTION-CAPITAL.md` v1.0 stays LOCKED.
