# Agentic Prompt Stacks

Source of truth is Git in this repository. There is no required Obsidian vault.

## Component order

1. **Constitution** - locked governance and capital rules. `live_trading=false`
   remains mandatory.
2. **Prompt STACKS** - versioned, role-scoped, digest-bound prompt contracts in
   `prompt-stacks/`.
3. **Wave contracts** - wave N+1 may not start until wave N gate PASS with
   complete evidence, `CRITICAL=0`, and `HIGH=0`.
4. **Runner FSM** - terminating loop:
   `DISCOVER -> BASELINE -> PLAN -> WAVE_READY -> PARALLEL_DISPATCH -> EXECUTION
   -> COLLECT -> VERIFY -> ADVERSARIAL_VERIFY -> EVIDENCE -> WAVE_GATE ->
   NEXT_WAVE | PATCH_LOOP(max 3) | HUMAN_REVIEW_REQUIRED | EXIT`.
5. **Ruflo Swarm** - optional orchestration bus for parallelism only. It never
   substitutes for gate evidence.
6. **Cursor executors** - isolated ownership per task through `CursorTask`
   metadata.
7. **Evidence + adversarial verify** - binds `assembled_prompt_digest` and stack
   ids/versions/digests when prompt stacks are used.
8. **Gate / stop conditions** - final authority. Agent self-PASS is never enough.

## Stack versioning and digests

`prompt-stacks/index.json` is the registry. Each stack declares:

- `id`
- `name`
- `version`
- canonical body `body_sha256`
- `depends_on`
- `required_roles`

The registry also carries `release_policy`. APS-002 deliberately does not
invent a wall-clock evidence lifetime: `evidence_expires_at` is `null` until a
Founder parameter exists. Evidence still goes stale when any bound prompt-stack
dependency changes.

Canonical body rules:

- JSON stacks: parse and dump sorted compact JSON.
- Markdown stacks: normalize line endings and keep one trailing newline.

The composer refuses to load a stack whose declared digest no longer matches its
body. A stack release id is derived as:

```text
<stack_id>@<version>+sha256:<body_sha256>
```

## Composition

`runner.prompt_stacks.assemble_prompt(stack_ids, role, wave_context)` returns an
`AssembledPrompt` artifact with:

- ordered stack ids
- per-stack versions
- per-stack body digests
- per-stack release ids
- full registry digest
- evidence expiry policy
- wave context
- assembled body
- assembled prompt digest

Composition fails closed on:

- unknown stack id
- duplicate stack id
- missing prior dependency
- unknown role
- role requesting a forbidden stack
- empty stack list
- missing wave context

## Role taxonomy

Current roles are:

- `commander`
- `planner`
- `executor`
- `verifier`
- `red_team`

The registry states which stacks each role may receive. `CursorTask` injects
`role`, `least_privilege`, `wave_id`, and `stack_id` into metadata, and composer
metadata adds stack ids, stack versions, stack digests, wave context, and
`assembled_prompt_digest`.

## Evidence binding

Gate evidence must bind to the prompt-stack source it was produced under. A gate
artifact without `prompt_stack` is invalid; silence does not mean "no prompt".

Every evidence artifact must include:

```json
{
  "prompt_stack": {
    "role": "executor",
    "stack_ids": ["00", "04"],
    "stack_versions": {"00": "0.1.0", "04": "0.1.0"},
    "stack_digests": {"00": "...", "04": "..."},
    "stack_releases": {"00": "00@0.1.0+sha256:...", "04": "04@0.1.0+sha256:..."},
    "registry_sha256": "...",
    "assembled_prompt_digest": "...",
    "evidence_expires_at": null,
    "stale_on": [
      "registry_sha256_change",
      "stack_version_change",
      "stack_body_sha256_change",
      "assembled_prompt_digest_change"
    ],
    "wave_context": {"wave_id": 4}
  }
}
```

The gate reassembles the prompt from Git source and rejects a PASS path when the
binding is absent, incomplete, or any version, stack digest, or assembled prompt
digest does not match. It also rejects stale bindings when the registry digest,
release id set, or expiry policy differs from the current registry.

## Wave and parallelism boundaries

Parallelism is allowed only inside a single wave and only when file ownership
does not overlap. The Ruflo `SwarmDispatch` contract requires:

- max 8 parallel agents
- all claims in the same wave
- unique `agent_id` and `lease_id`
- non-overlapping `owned_paths`, including parent/child overlaps
- work-claim lease fields with ISO-8601 expiry
- stack ids accepted for the claim role by the prompt-stack composer
- evidence skeleton path per claim, confined to `evidence/waveN/*.json`

Wave crossing is blocked by the FSM: wave N+1 cannot start until wave N is in
`passed_waves`, which is written only after a PASS gate result with
`CRITICAL=0` and `HIGH=0`.

## Ruflo and Cursor stub boundary

`NullRufloAdapter.available() == False`. `publish`, `subscribe`, and
`dispatch_swarm` raise `RufloUnavailableError`; they do not report fanout success.

Cursor remains a fail-closed executor contract. `NullCursorExecutor.dispatch`
raises when not configured. The documented fallback is a single-threaded Cursor
handoff skeleton, and that skeleton still must return schema-valid evidence
before any gate can pass.
