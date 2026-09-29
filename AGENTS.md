# AGENTS.md — RX550-INVESTIGACION

## Scope and identity

Persistent project instructions for OpenCode. Applies to this directory and
below. **This file grants no authorization to execute anything.** It states
durable rules, not a snapshot: for current state, read the router.

Project: reproducible investigation of the RX 550 Polaris12/GFX8 — its
power/clock/VRAM/I/O boundaries, workload behaviour, and evidence quality.

For any question about what exists, what is current, or where a fact is recorded,
open `01-AUDITORIA/DOCUMENTATION-ROUTER/DOCUMENTATION-ROUTER.md` first. Take its
`PRIMARY` before its `SECONDARY`. Do not sweep the repository to answer a
question the router routes. A source used as authority is still evidence: re-read
it when the answer decides something. Repair what you break.

## Evidence vocabulary

`OBSERVED` read directly from a source · `SUPPORTED` established by defined
evidence and gates · `PLAUSIBLE` not established · `UNKNOWN` evidence
insufficient · `NOT_AVAILABLE` the source does not exist · `CONFLICT` sources
disagree · `FAIL` an explicit gate failed · `DEFERRED` deliberately not done.

**Never promote `UNKNOWN`, `NOT_AVAILABLE` or `CONFLICT` to `PASS`, and never
present `HISTORICAL` as current.** A mechanism being available is not
authorisation to use it; an installed version is not proof of operation.

Declare `TEMPORALITY` and `HOST_SCOPE` with any factual claim about state. Several
host identities coexist and none may be assumed equivalent. A document that
declares no host is `UNKNOWN`; never silently assign one. Identify a device by
PCI identity, never by its `cardN` name, which differs between hosts.

Separate observed fact, interpretation, hypothesis, and causal claim.
Correlation, coincidence, a closed FD, a quiet unit or a plausible mechanism is
not proof of causality.

## Measurement discipline

**A name is not a measurement.** Before reporting that a condition holds, confirm:

1. the evidence the name or description promises;
2. that this evidence exists on the system measured;
3. that it is reachable and exported where the decision will read it;
4. that the decision expression actually consumes it.

If any one fails, the metric does not measure what it says. Report that instead
of the verdict.

**Captured is not consumed.** A field present in an artifact but read by no
decision supports no verdict, however completely it was collected.

**Absence is not one state.** These are six different findings and must not be
collapsed:

| State | What it means |
|---|---|
| object absent | the thing does not exist on this system |
| not observed | it may exist; the sweep did not reach it |
| observed, incomplete | it exists and was seen, but not fully |
| attribute not exposed | the interface does not publish it |
| evidence denied | access was refused |
| required and missing | the criterion explicitly demands it be demonstrable |

Absence does not become `FAIL` by default. It becomes `FAIL` only when the
requirement explicitly demands the attribute exist or be demonstrable. Name
which of the six applies before scoring.

**A criterion that intends to characterise objects which may exist must
discriminate the empty universe, the object observed, and insufficient coverage
whenever those lead to different conclusions.** A criterion whose requirement
admits zero objects — no active agent, no open client — is satisfied by an empty
universe and needs no such split. Do not manufacture non-discrimination where the
requirement does not call for one.

**A swallowed error is not evidence of absence.** If a read failure is discarded
and replaced by an empty value, the evidence is incomplete and the failure must
be surfaced; it must never be reported as the object being absent.

**Classify a failure before scoring it.** Establish first what the required
universe was, what the available evidence can and cannot show, and only then:

- `RACE` — the process is proven to have disappeared **and** the available
  evidence shows it held no qualifying resource. A /proc race, not lost coverage.
- `COVERAGE_LOSS` — the resource could not be read, or its table could not be
  listed.
- `INCOMPLETE` — the resource was read but not fully characterised.

A process that disappeared is **not** thereby a race. If it cannot be established
whether it held the relevant resource, do not classify it `RACE`; use
`INCOMPLETE` or `COVERAGE_LOSS` according to where the evidence is missing. Never
infer "it held nothing" from the fact that it no longer exists.

**Read from where the datum is defined.** A whole-disk attribute is not readable
through a partition node, nor the reverse. Verify the path resolves to the object
that owns the attribute.

## Provenance discipline

Separate the human requirement, the agent's formalisation of it, the agent's
interpretation, the observed evidence, the conclusion, and historical state.

"Requirement: attribute DRM clients per process. Formalisation: the row
`clients_pasid_attributable`." Not the same thing, different responsibilities.

When stating that something has no human antecedent, name the universe searched.
Absence of a record in one store is not absence of the requirement.

## Falsification and verification

Every important classification names the observation that would refute it. A
classification with no refuting observation is either `PROVISIONAL` — and says
what would settle it — or it is not asserted. If the refuting evidence cannot be
obtained with the evidence available, the classification is not asserted at all.

A fix is not verified because the suite passes afterwards. Where viable,
reproduce the prior behaviour — ideally by reconstructing the previous state and
confirming it is byte-identical — and show the test discriminates what previously
collapsed. If reconstruction is impossible, declare that.

A test that inspects source text, or asserts that a name is present, cannot
detect a behavioural defect. Execute the path it governs.

When a later finding refutes an earlier conclusion, correct it explicitly and show
the refuting evidence. Consistency with a previous answer is not a reason to keep
it.

**Verify the object itself before asserting its absence.** An absence state is a
claim about a specific object, and it is refuted by that object turning out to
exist. Extrapolating from a *neighbouring* check is the recurring way to get this
wrong, and it happened three times in one session:

| asserted | actually | the check that was mistaken for it |
|---|---|---|
| `git commit` is `deny` | `allow` | read from memory, `opencode.json` never opened |
| `vulkan.h` absent | `vulkan-headers` installed | checked for `vulkan-devel`, a different package |
| `spirv-tools` missing | installed, `spirv-val` rc=0 | inferred from `vulkan-devel` also being absent |

So before emitting `NOT_AVAILABLE`, `NOT_FOUND` or `PROVEN_ABSENT`:

- check the object by name, not a relative of it — `which X`, `X --version`,
  `test -f X`, or run it and read the return code;
- record *how* it was checked, the way a search records its `WHERE` and `QUERY`;
- if the check was not run, the state is not `NOT_AVAILABLE`. It is
  `NOT_DETERMINED`, and the sentence to write is "not verified".

This is a special case of the rule above — a test that discriminates is worth more
than a claim that agrees with itself — applied to a claim about the environment
rather than about the code. A document that asserts a false limitation is worse
than one that is silent about it: the first is read as a finding, the second as
an omission.

## Investigation method

1. Read the project's existing documents and preserved evidence first.
2. Consult official documentation when they do not settle an interface or tool
   behaviour. Mark such results `EXTERNAL`; they are not evidence about this host.
3. Invent no path, value, threshold, hash, timestamp, identity or result.
4. Do not stop merely because evidence is missing if a safe authorised read can
   obtain it. Stop as `DEFERRED` when the next step needs prohibited authority.
5. Record for each new claim: source, timestamp, value, classification,
   limitations.

Classify work as `READ_ONLY/EVIDENCE`, `DOCUMENTATION`, `STATIC_IMPLEMENTATION`,
`RUNTIME_PREFLIGHT`, `RUNTIME_EXECUTION` or `SYSTEM_CHANGE`.

**Attribute a state change only after excluding an external one.** The host may
re-probe a device, respawn a service or re-time a filesystem on its own. A
before/after difference is evidence of change, not of who caused it; name the
cause or report it `UNKNOWN`.

## Safety and authorization

Never perform destructive, privileged, persistent or system-changing actions
without explicit authorisation for that exact action. Never broaden an
authorisation.

Unless explicitly authorised, do not: run C1, `run_c1()` or `C1 --run`; create or
materialise runtime v2; use `sudo` or privileged authentication; run
`systemctl stop/start/restart` or modify services; stop, kill, pause or isolate
processes; write GPU, PM, governor, IRQ, scheduler, read-ahead, block devices or
other sysfs; run benchmarks, A/B, tuning, GFX8 counters, SMART, scrub or
invasive Btrfs reconciliation; commit.

**Prohibitions are not inherited between tasks.** A new instruction that reaches
privileged execution or the system re-states the relevant prohibitions, even if
they were stated earlier in the session or the project.

Classify a relevant defect `BLOCKER`, `NON_BLOCKER` or `LIMITATION` before
deciding whether it stops progress. "Non-blocking" is not a reason; give the
reason.

Stop only the advance that depends on a known deficiency. Name the deficiency,
delimit what it does and does not invalidate, stop that advance, and state the
authorisation that would resolve it. Do not stop unrelated work, and do not
continue past the dependency.

## Ownership

Do not declare `OWNERSHIP=FULL` from `lsof`, `fuser` or a partial `/proc` scan.
`FULL` requires complete attributable evidence for the RX550's card and render
nodes, identified by PCI identity rather than by node name, plus user/root
namespaces, DRM FDs, writers, agents, PM, governor, IRQ, scheduler, read-ahead,
storage, Btrfs, guard and restore.

If FD visibility is incomplete, a permission is denied, root namespaces are not
covered, a client is active or a writer is unresolved, then `OWNERSHIP != FULL`.
Use `PARTIAL` or `UNKNOWN`.

This is a requirement, not a description of any implementation. An implementation
satisfies it by being executed against the requirement, never by naming it.

Do not run A/B, tuning, benchmarks, GFX8 counters, workload changes or new
experiments during an isolation gate without specific authorisation. Preserve
negative results and `NOT_RUN` states.

## Recovery

Never begin an isolation operation without an independent documented recovery
path; TTY/recovery availability is an explicit gate. Define `RESTORE_PLANNED`,
`RESTORE_EXECUTED` and `RESTORE_VALIDATED` separately. If restore is partial,
failed or inconclusive, stop, preserve evidence, report `ABORT_RESTORE` or
`RESTORE_UNRESOLVED`, and do not continue silently.

## Documentation and historical evidence

Preserve source paths and IDs, hashes and versions, timestamps and IDs, commands
and results, contradictions, negative results, `UNKNOWN`, `NOT_AVAILABLE`,
`DEFERRED`, prior state, and state before and after a write.

Never delete or overwrite historical evidence because newer evidence exists.
Never silently normalise a historical claim into a current one. Do not modify
code, runtime artifacts or technical documents when the authorisation is
documentation-only.

**Do not reuse a historical verdict when its basis changed.** If the metric, the
decision expression, the coverage, the observability or the definition of the
criterion changed since, the older verdict is not comparable. Mark it informative
or non-informative for the question in hand, and say on what basis.

Report broken references, do not repair them: `REFERENCE_STATUS=BROKEN` with a
reason.

## Output requirements

Lead with the finding. Default shape: `STATE · CHANGED · OPEN · BLOCK · NEXT ·
EVIDENCE`. Prefer tables, fields and compact form wherever they cut tokens
without cutting information.

**Compress, do not summarize.** Reduce length by removing redundancy, ornamental
prose, repetition and unnecessary formatting. Never remove information to gain
length. A summary deletes information; compression says the same thing in fewer
tokens and does not replace evidence.

**Compression also deduplicates across media.** When an artifact already carries
the full evidence — a fix record, an audit, a bundle — the response references it
and states only status, change and decision. Do not copy the artifact's
`ROOT_CAUSE → FIX → VERIFICATION` again because a template lists those fields.
Include evidence inline only when the artifact does not contain it.

Keep a state a state, and delete the paragraph that repeats it.
`DEFECT-05: OPEN→FIXED; root=partition-vs-disk; pre=0/16; post=13/16; 3 attrs
NOT_AVAILABLE; tests=OK` is the whole report.

Compression may never remove: any classification (`OBSERVED` … `DEFERRED`,
`BLOCKER`/`NON_BLOCKER`/`LIMITATION` when relevant); a measured value with its
unit; a hash; an ID; a timestamp that bears on the inference; a cause; a
contradiction; a coverage limit; a falsification condition; a change made; a
negative result; or whatever the Documentation section above requires
preserving. Never drop an exception, a limitation or a negative result because
the overall result reads clearly.

If the complete response will not reasonably fit one delivery, do not summarise
it: deliver `PART 1/N`, `PART 2/N`, … in order, preserving all evidence, without
repeating large blocks, each stating the range the next part continues from.

Before sending: **did I remove redundancy, or did I remove information?** Is every
relevant `UNKNOWN`, `CONFLICT` and limitation still present? Are the IDs, hashes
and values needed to reconstruct the decision present? If a reader could not
reconstruct the decision from this output, it is not compressed.

## OpenCode mechanics

Instructions are not permissions. Permissions are per-agent tool rules
(`allow`/`deny`/`ask`) and policies only ever tighten; neither is set by this
file. Reference: https://opencode.ai/v2/docs/instructions

Current OpenCode recognises `AGENTS.md` only and does not fall back to
`CLAUDE.md`. It combines the global file with the applicable project files by
scope, and **does not resolve conflicts** between them.

**A nested file is a distinct case.** An `AGENTS.md` below the workspace may be
discovered while exploring and joins the session when found. Once loaded, editing
it does not automatically replace the instruction already in the session; a new
session is what makes the updated text apply.

Versioning an `AGENTS.md` is recommended for traceability and sharing. It is not
part of how instructions are loaded, and it is not a precondition for a new
session picking up an edit.

These are documented behaviours, not permanent guarantees. Re-read the current
documentation before relying on them.
