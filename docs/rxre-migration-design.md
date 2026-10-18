# RXRE Migration Design: Current Architecture → Agentic Investigation Engine

## Status: DESIGN PHASE (Phase 1 of POPURRÍ FINAL)

---

## 1. Inventory: Current RXRE Architecture

### 1.1 Components

| Component | File | Lines | Role |
|---|---|---|---|
| `core/engine.py` | `tools/rxre/core/engine.py` | 336 | Pipeline dispatcher (deterministic stages) |
| `core/store.py` | `tools/rxre/core/store.py` | 740 | Data store: facts, observations, claims |
| `core/normalize.py` `core/__init__.py` | `tools/rxre/core/` | 274 | Artifact normalization → Result objects |
| `core/capabilities.py` | `tools/rxre/core/capabilities.py` | 274 | Capability catalog (what the agent can ask) |
| `core/dispatch.py` | `tools/rxre/core/dispatch.py` | 302 | Dispatch table (operation → handler) |
| `backends/registry.py` | `tools/rxre/backends/registry.py` | 280 | Tool registry (name → path, contract) |
| `backends/dispatch.py` | `tools/rxre/backends/dispatch.py` | 387 | Tool executor (subprocess, result capture) |
| `backends/contract.py` | `tools/rxre/backends/contract.py` | 326 | Tool contracts (preconditions, artifacts) |
| `backends/adapters/` | `tools/rxre/backends/adapters/` | — | Tool wrappers (rz_inspect.py) |
| `commands/query.py` | `tools/rxre/commands/query.py` | 526 | Query engine (search, trace pipelines) |
| `commands/handlers.py` | `tools/rxre/commands/handlers.py` | 405 | Operation handlers (register, search, etc.) |
| `api/envelope.py` | `tools/rxre/api/envelope.py` | 149 | Response envelope (status, results, evidence) |
| `api/request.py` | `tools/rxre/api/request.py` | 431 | Request parsing and validation |
| `api/machine.py` | `tools/rxre/api/machine.py` | 561 | Machine API (stdin/stdout JSON) |
| `cli.py` | `tools/rxre/cli.py` | 201 | CLI entry point |
| `storage/` | `tools/rxre/storage/` | 0 | Empty (placeholder) |

### 1.2 Tests

| Test File | Purpose |
|---|---|
| `test_p003.py` | P0.3: MMIO offset identity + conflict detection (PROVEN) |
| `test_rxre002.py` | Core capability tests |
| `test_rxre003.py` | Core capability tests |
| `test_backends004.py` | Backend contracts |
| `test_dispatch004.py` | Dispatch logic |
| `test_field005.py` | Register field resolution |
| `test_mutations003.py` | Mutation testing framework |
| `test_fixtures.py` / `test_fixture004.py` | Fixture-based tests |
| `freeze005.py` | Frozen oracle (golden output) |
| `ai_usability_test.py` | AI usability assessment |

---

## 2. Mapping: Current Components → POPURRÍ FINAL Roles

### 2.1 Investigation Engine (Fases B-D)

```
CURRENT: core/engine.py
├── ejecutar_operacion() → single capability execution
├── ejecutar_pipeline() → deterministic multi-stage pipeline
└── Pipelines dict → hardcoded pipeline definitions

MAPPING TO POPURRÍ:
├── hypotheses          → PARTIALLY (Pipeline stages = limited exploration)
├── uncertainty         → NO (statuses: ok/empty/blocked/error — not epistemic states)
├── information gain    → NO (no explicit gain calculation)
├── discriminants       → NO (no hypothesis separation)
├── next action         → NO (fixed pipelines, not agentic decisions)
└── decision            → PARTIALLY (propagates blocked/error, but no choice)

DECISION: REUSE + EXTRACT
- Keep deterministic pipelines as the "safe execution" layer
- Extract hypothesis/uncertainty/discriminant logic into new module
- Do NOT rewrite engine.py wholesale (preserve working pipeline logic)
```

### 2.2 RXRE Core (E-C)

```
CURRENT: core/store.py + core/normalize.py
├── FactStore → evidence storage with provenance
├── FactType enum → FACT, OBSERVATION, MEASUREMENT
├── Result normalization → Result objects with tool, status, raw
├── Evidence objects → kind, value, tool, status, limitations

MAPPING TO POPURRÍ:
├── evidence          → YES (store.py FactEntry, normalize.py Result)
├── observations      → YES (OBSERVATION FactType)
├── claims            → PARTIAL (CLAIM FactType exists but limited)
├── provenance        → YES (every FactEntry tracks producer, input, tool)
├── artifacts         → PARTIAL (raw JSON captured in _raw_json)
├── lineage           → PARTIAL (evidence chain in provenance)
├── conflicts         → PARTIAL (conflict_note in reg_resolve.py results)
├── epistemic state   → PARTIAL (status enum: PROVEN/OBSERVED/NOT_DETERMINED)
└── investigation memory → PARTIAL (accumulates results but not questions)

DECISION: EXTEND + REFACTOR
- Augment epistemic states (add HYPOTHESIS, UNSETTLED, CONTRADICTION)
- Add claim lifecycle (CLAIM_ID, EVIDENCE, STATE_TRANSITION)
- Add investigation memory (questions, hypotheses, next actions)
- Preserve existing FactEntry structure (backward compatible)
```

### 2.3 Relation Engine (F)

```
CURRENT: core/normalize.py (partial)
├── de_busqueda() → search result normalization
├── de_registro() → register result normalization
├── de_arbol_trace() → callchain normalization
└── resultado() → generic Result constructor

RELATIONS currently:
- Implicit in pipeline output (results linked by stage)
- No explicit producer→consumer→effect chains
- No typed, traceable relations

MAPPING TO POPURRÍ:
├── producer → PARTIAL (tool field in Result)
├── transformation → NO (no explicit transform record)
├── representation → PARTIAL (normalized Result)
├── consumer → NO (no consumer tracking)
└── system/hardware effect → NO (no causal effect model)

DECISION: NEW MODULE
- Create core/relations.py
- Build on existing provenance infrastructure
- Start with small vertical: producer→representation→consumer
- Do NOT build universal graph initially
```

### 2.4 Tool Fabric (G)

```
CURRENT: backends/registry.py + backends/dispatch.py + backends/contract.py
├── ToolRegistry → name → (path, args, contract)
├── ToolExecutor → subprocess.run, capture stdout/stderr
├── ToolContract → preconditions, expected_artifacts, failure_modes

MAPPING TO POPURRÍ:
├── Rizin, radare2, LLVM, GDB, objdump → YES (rz_inspect.py adapter)
├── custom analyzers → YES (evidence_search.py, pm4ops.py, prov.py)
├── C/ASM probes → PARTIAL (some in tools/)
├── runtime observers → NO (not yet, no MMIO per safety rules)
└── tool validation → PARTIAL (contracts exist but not self-test suite)

DECISION: KEEP + EXTEND
- backends/registry.py → TOOL_FABRIC registry
- backends/adapters/ → domain adapters slot
- Extend contracts with self-test + cross-check requirements
- Do NOT reimplement existing tools (reuse, not replace)
```

### 2.5 Target (H)

```
CURRENT: core/capabilities.py
├── Capabilities → list of (name, description, inputs, outputs)
├── Capability → query, register, trace, etc.
├── Target identification → NOT present (no PCI/ASIC routing yet)

MAPPING TO POPURRÍ:
├── source          → NO (no source target adapter)
├── binary          → NO
├── firmware        → NO
├── kernel          → PARTIAL (kernel path passed as arg)
├── protocol        → NO
├── hardware        → NO (no hardware target adapter)

DECISION: BUILD P1 (Phase 1) as first vertical slice
- Create target identification module (core/target.py)
- PCI vendor/device → capabilities routing
- Polaris12 specific capability filter
```

### 2.6 Safe Execution Layer (H of POPURRÍ)

```
CURRENT: core/engine.py, backends/dispatch.py
├── ejecutar_operacion() → wraps handler execution
├── ToolExecutor → subprocess with timeout
├── Envelope → status/blocked/error propagation

SAFETY MECHANISMS EXISTING:
├── Timeout on subprocess
├── Status propagation (blocked ≠ empty)
├── Evidence in envelope
└── Contract-based validation

MAPPING TO POPURRÍ:
├── READ_ONLY / REVERSIBLE / MUTATING / DESTRUCTIVE → PARTIAL
├── preconditions → PARTIAL (in contracts)
├── abort_condition → NO
├── recovery path → NO
└── validation → PARTIAL (selftests exist)

DECISION: EXTEND
- Add risk classification to tool contracts
- Add abort/recovery fields to operation schema
- Preserve existing timeout/propagation
```

### 2.7 Domain Adapters (Fase D)

```
CURRENT: backends/adapters/rz_inspect.py + backends/
├── rz_inspect.py → Rizin wrapper for binary inspection
├── evidence_search.py → code search engine
├── pm4ops.py → PM4 opcode census
├── prov.py → contract compliance checking
└── reg_resolve.py → register/field resolution

MAPPING TO POPURRÍ:
├── AMD GPU adapter → PARTIAL (reg_resolve.py, pm4ops.py)
├── x86 adapter → NO
├── ARM adapter → NO
├── Linux kernel adapter → PARTIAL (uses kernel source)
└── protocol adapter → NO

DECISION: EXTRACT
- Move backend-specific tools into domain adapter directories
- Preserve tool_fabric abstraction for composition
- Keep current tools working (no breaking changes yet)
```

### 2.8 Agent API (I)

```
CURRENT: api/machine.py + cli.py + api/envelope.py + api/request.py
├── machine.py → stdin/stdout JSON protocol (op: ..., inputs: ...)
├── envelope.py → consistent response schema
├── request.py → request parsing + validation
├── cli.py → CLI commands

AGENT CAPABILITIES:
├── ops → YES (list available operations)
├── capabilities → YES (list capabilities with contracts)
├── query → YES (search/trace pipelines)
├── register → YES (register resolution)
├── trace → YES (call chain)
├── case → YES (case management)
└── provenance → YES (contract compliance)

MAPPING TO POPURRÍ:
├── "What evidence do we have?" → YES (query results)
├── "What hypotheses exist?" → NO
├── "What contradictions?" → NO
├── "What's missing?" → NO
├── "Best next action?" → NO
└── "Why that action?" → NO (fixed pipelines)

DECISION: EXTEND
- Add epistemic query endpoints
- Add hypothesis/discriminant capability
- Preserve existing JSON protocol
```

### 2.9 Investigation Memory (E)

```
CURRENT: core/store.py (FactStore)
├── FactStore → SQLite-backed fact storage
├── FactEntry → (id, type, value, evidence, status, provenance)
├── FactType → FACT, OBSERVATION, MEASUREMENT, etc.
├── add/get/update → basic CRUD
├── by_question → query by question string

LIMITATIONS:
├── No hypothesis tracking
├── No decision history
├── No next_action queue
├── No state transition logging
└── No epistemic state machine

DECISION: EXTEND store.py
- Add Hypothesis table (hypothesis_id, statement, status, evidence)
- Add Decision table (decision_id, question, rationale, state_before, state_after)
- Add Question table (question_id, investigation_id, status)
- Preserve FactEntry/FactType (backward compatible)
```

---

## 3. Migration Plan: Phase by Phase

### FASE 1: P1 ASIC-AWARE ROUTING → Target Engine + Route Engine
```
WHAT: Create core/target.py — PCI-based capability routing
WHY: mmMC_CG_DATAPORT needs target identification before resolution
WHAT EXISTS:
  - backends/registry.py: tool catalog
  - core/capabilities.py: capability catalog
  - No target identification
WHAT TO BUILD:
  - core/target.py: PCI vendor/device → capabilities, ASIC-aware
  - Route engine: target + question → candidate capabilities → selection
  - Preserve current capability list
  - Add selection provenance
DEPENDENCIES: core/capabilities.py (existing), backends/registry.py (existing)
EVIDENCE NEEDED: PCI 1002:699f → Polaris12 mapping (from kernel source)
```

### FASE 2: EPISTEMIC CORE → Epistemic State Extension
```
WHAT: Extend epistemic states, add Claim lifecycle to store.py
WHY: P0 conflict detection needs conflict tracking, not just "not found"
WHAT EXISTS:
  - core/store.py: FactStore with FACT, OBSERVATION, MEASUREMENT
  - core/normalize.py: Result with status
WHAT TO BUILD:
  - Add Claim state machine (PROVEN, REFUTED, NOT_DETERMINED, etc.)
  - Add conflict tracking module
  - Add contradiction detection
  - Preserve FactType enum (backward compatible)
DEPENDENCIES: FASE 1 (target identification enables claim scoping)
EVIDENCE NEEDED: Conflict between 0xA21 and 0xA32 values
```

### FASE 3: RELATION ENGINE → Relations Module
```
WHAT: Build core/relations.py — typed, traceable causal relations
WHY: reg_resolve.py conflict_note is informal; need formal producer→consumer chains
WHAT EXISTS:
  - core/normalize.py: Result has tool, raw, limitations
  - No formal relation model
WHAT TO BUILD:
  - Relation: (producer, transformation, representation, consumer, effect)
  - Start small: single vertical (reg_resolve conflict → query → agent)
  - Persist in FactStore
DEPENDENCIES: FASE 2 (claims provide semantic anchoring for relations)
EVIDENCE NEEDED: Current pipeline output linking (register step → query step)
```

### FASE 4: INVESTIGATION MEMORY → Memory Module
```
WHAT: Add Hypothesis, Decision, Question tracking to store.py
WHY: Agent needs to track "why we think what we think" across operations
WHAT EXISTS:
  - core/store.py: FactStore with by_question
WHAT TO BUILD:
  - Hypothesis: (id, statement, status, supporting_evidence, contradicting_evidence)
  - Decision: (id, question, chosen_action, rationale, before_state, after_state)
  - Question: (id, text, status, assigned_to_hypothesis)
  - Link to existing FactEntry
DEPENDENCIES: FASE 3 (relations provide causality for hypothesis support)
EVIDENCE NEEDED: Current pipeline stages (register.uses = search → register)
```

### FASE 5: HYPOTHESIS ENGINE → Hypotheses + Discriminants
```
WHAT: core/hypotheses.py — competitive hypothesis management
WHY: mmMC_CG_DATAPORT conflict needs explicit hypotheses (H1: writer=A, H2: writer=B)
WHAT EXISTS:
  - Nothing — no hypothesis tracking
WHAT TO BUILD:
  - create_hypothesis(statement) → Hypothesis
  - support/evidence methods
  - discriminate(h1, h2) → required observable
  - Link to FASE 4 memory
DEPENDENCIES: FASE 4 (memory needed for hypothesis persistence)
EVIDENCE NEEDED: Register conflict → divergent hypotheses about writer
```

### FASE 6: DISCRIMINANT ENGINE → Discriminant Selector
```
WHAT: core/discriminants.py — select best action to separate hypotheses
WHY: Need to decide "what experiment separates H1 from H2"
WHAT EXISTS:
  - core/engine.py: fixed pipelines
  - No discriminant calculation
WHAT TO BUILD:
  - information_gain(action, hypotheses) → float
  - select_next_action(question, context) → Action
  - risk assessment (reversibility, cost)
DEPENDENCIES: FASE 5 + FASE 1 (target routing needed for tool selection)
EVIDENCE NEEDED: Pipeline stages show "what next" — formalize as discriminant
```

### FASE 7: INFORMATION-GAIN ENGINE → Action Priority
```
WHAT: core/priority.py — rank actions by information gain
WHY: Multiple possible actions; need explicit ranking
WHAT EXISTS:
  - Nothing — agent chooses (no internal ranking)
WHAT TO BUILD:
  - value(hypothesis_separation, path_unlock, validation, ...)
  - explainability: "why action X over Y"
  - Deterministic but not fixed
DEPENDENCIES: FASE 6 (need discriminants before ranking)
EVIDENCE NEEDED: Current capability ordering (query → register)
```

### FASE 8: SAFE EXECUTION LAYER → Risk Classification
```
WHAT: core/safety.py — risk classification + abort/recovery
WHY: P0 used reg_resolve.py (readonly); future phases need writes
WHAT EXISTS:
  - core/engine.py: timeout + status propagation
  - backends/contract.py: preconditions (basic)
WHAT TO BUILD:
  - READ_ONLY / REVERSIBLE / MUTATING / DESTRUCTIVE classification
  - abort_condition schema
  - recovery path registry
  - NO MMIO WRITES (RX550 hardware protection rule)
DEPENDENCIES: FASE 6 + FASE 7 (need discriminant + priority for safe action)
EVIDENCE NEEDED: Current timeout + status propagation in engine.py
```

### FASE 9: DOMAIN ADAPTERS → AMD GPU Adapter
```
WHAT: tools/rxre/domains/amd_gpu/ — Polaris12-specific adapters
WHY: reg_resolve.py is AMD GPU specific; extract into domain module
WHAT EXISTS:
  - tools/reg_resolve.py (AMD GPU)
  - tools/evidence_search.py (generic code search)
  - tools/pm4ops.py (PM4 opcodes)
WHAT TO BUILD:
  - domains/amd_gpu/__init__.py → registers, traces, capabilities
  - Register adapter (wrap reg_resolve.py)
  - PM4 adapter (wrap pm4ops.py)
  - Trace adapter (wrap evidence_search.py)
  - Keep current tools working (no breaking changes)
DEPENDENCIES: All previous phases (need full pipeline for AMD GPU queries)
EVIDENCE NEEDED: Current reg_resolve.py output
```

### FASE 10: AGENT-FACING API → Extended Query
```
WHAT: Extend api/machine.py with epistemic queries
WHY: Agent needs to ask "what hypotheses exist?" not just "search this symbol"
WHAT EXISTS:
  - api/machine.py: ops, capabilities, query, register, trace
  - api/envelope.py: consistent response schema
WHAT TO BUILD:
  - New ops: hypotheses.list, hypotheses.create, action.next, evidence.show
  - Extend envelope with epistemic fields (uncertainty, discriminant, etc.)
  - Preserve backward compatibility (existing ops unchanged)
DEPENDENCIES: FASE 4 + FASE 5 + FASE 9 (need hypotheses + domain adapters)
EVIDENCE NEEDED: Current machine.py op responses
```

### FASE 11: BENCHMARK → Agent Investigation Benchmark
```
WHAT: tools/rxre/tests/benchmark/ — black-box agent benchmark
WHY: Prove RXRE enables better investigation than raw tools
WHAT EXISTS:
  - test_p003.py (P0.3 verification)
  - test_mutations003.py (mutation testing)
  - ai_usability_test.py (basic usability)
WHAT TO BUILD:
  - Benchmark scenarios: register conflict, missing evidence, ambiguous definition
  - Metrics: time_to_hypothesis, false_claim_rate, evidence_coverage
  - Comparison: agent + RXRE vs agent without RXRE
DEPENDENCIES: FASE 10 (need agent API for comparison)
EVIDENCE NEEDED: Current test_p003.py as baseline scenario
```

---

## 4. Vertical Slice: First Implemented Path

```
QUESTION
  ↓
"¿Dónde está definido mmMC_CG_DATAPORT y cuál valor es correcto?"
  ↓
RXRE CORE
  ↓
EVIDENCE (reg_resolve.py: 5 definitions, 2 values 0xA21/0xA32)
  ↓
CLAIM: "valor correcto es 0xA21" (H1) vs "valor correcto es 0xA32" (H2)
  ↓
CONFLICT noted, CHOSEN=null, CANDIDATES=[0xA21, 0xA32]
  ↓
DISCRIMINANT: "¿cuál header define a qué ASIC?" (need ASIC identification)
  ↓
NEXT ACTION: route to target (1002:699f → Polaris12 → gfx_8_0 → header)
  ↓
TOOL: reg_resolve.py --gfx gfx_8_0
  ↓
OBSERVATION: definicion en gfx_8_0_d.h = 0xA21
  ↓
RXRE UPDATE: H1 supported, H2 refuted (NOT for target), CLAIM state → PROVEN
  ↓
NEXT QUESTION
  ↓
"¿Qué driver usa este offset en runtime?"
```

This vertical slice requires FASE 1 (target routing) + existing P0.3 infrastructure.

---

## 5. Dependencies and Constraints

### 5.1 Build Order Constraints

```
FASE 1 → FASE 2 → FASE 3 → FASE 4 → FASE 5 → FASE 6 → FASE 7 → FASE 8 → FASE 9 → FASE 10 → FASE 11
```

Each phase depends on:
- Preceding phases for epistemic infrastructure
- Existing RXRE components (preserved, not replaced)

### 5.2 Hard Constraints

1. **NO Intel iGPU access** — any action touching 0000:00:02.0 → REFUSE
2. **NO MMIO writes** — only readonly observation of RX550 hardware
3. **NO firmware/VBIOS modification** — read-only investigation
4. **P0 = PROVEN** — no re-audit of P0.3
5. **Backward compatibility** — existing APIs preserved where possible

### 5.3 What NOT to Build

Per §5 (no over-research / no feature creep):

- Generic graph database (FASE 3 builds minimal, targeted relations)
- Universal parser framework (FASE 7 builds action ranking only)
- Internal LLM (FASE 10 preserves API boundary)
- Reimplementation of Rizin/GDB/LLVM (FASE 4 wraps, doesn't replace)

---

## 6. Evidence Summary

### 6.1 Current Evidence Sources

| Evidence | Source File | Used By |
|---|---|---|
| MMIO offset identity | kernel `amdgpu_device_rreg` docstring | P0.3 (PROVEN) |
| Register definitions | `asic_reg/gca/gfx_8_0_d.h` | reg_resolve.py |
| PM4 opcodes | `amdgpu_pm4.h` | pm4ops.py |
| Contract compliance | kernel source tree | prov.py |
| Search results | kernel source tree | evidence_search.py |

### 6.2 Evidence Needed Per Phase

| Phase | Needed Evidence | Current Status |
|---|---|---|
| FASE 1 | PCI 1002:699f → Polaris12 mapping | EXISTING (kernel source) |
| FASE 2 | Conflict resolution pattern | EXISTING (P0.3) |
| FASE 3 | Producer→consumer causality | PARTIAL (pipeline stages) |
| FASE 4 | Investigation state tracking | NONE |
| FASE 5 | Register conflict → hypotheses | EXISTING (P0.3) |
| FASE 6 | Action value calculus | NONE |
| FASE 7 | Action ranking rationale | NONE |
| FASE 8 | Risk classification | NONE |
| FASE 9 | AMD GPU tool wrappers | EXISTING (tools/) |
| FASE 10 | Epistemic query responses | NONE |
| FASE 11 | Agent benchmark scenarios | PARTIAL (test_p003.py) |

---

## 7. Next Action

**Primary**: Implement FASE 1 — `core/target.py` (target identification + ASIC routing).

**Secondary**: Create evidence for target identification:
- PCI vendor/device for RX550 → Polaris12
- ASIC → gfx_8_0 mapping
- gfx → capabilities filter

**Rationale**: This is the smallest vertical slice that enables the agent to ask "where is this register defined for MY target?" — which is the fundamental question that drives all AMD GPU investigation. Without target routing, every tool operates without context.
