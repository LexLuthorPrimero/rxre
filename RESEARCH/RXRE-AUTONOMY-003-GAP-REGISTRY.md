# RXRE Autonomy Gap Registry

## Principal Architectural Bottleneck

The primary bottleneck preventing autonomous mission completion in RXRE is:

**Missing observe-reason-act-verify control loop integration**

The mission system has:
- ✅ Mission creation and persistence
- ✅ Criteria definition with evidence references
- ✅ Task tracking and priority selection
- ✅ False-completion prevention (PROVEN requires evidence)

But lacks:
- ❌ **Execution integration**: Mission tasks not wired to dispatch `ejecutar()` 
- ❌ **Real evidence capture**: No automated evidence collection from executed actions
- ❌ **Verification feedback loop**: Verification results not fed back to update mission state
- ❌ **Fresh-context recovery**: No protocol to rebuild mission state from goal + verified progress
- ❌ **Loop and budget controls**: No limits on task selection attempts
- ❌ **Dependency resolution**: Task dependencies not enforced before selection

## Gap Registry

| Gap ID | Category | Description | Impact | Evidence |
|--------|----------|-------------|--------|----------|
| G-001 | Control loop | Missing observe-reason-act-verify integration | CRITICAL | Mission functions exist but not wired to dispatch |
| G-002 | Evidence capture | No automated evidence collection from task execution | CRITICAL | Results from `dispatch.ejecutar()` not stored as findings |
| G-003 | Dependency management | Task dependencies not checked before selection | HIGH | `seleccionar_siguiente_accion()` ignores dependencies |
| G-004 | Loop controls | No limits on repeated task selection | HIGH | Could loop infinitely without progress |
| G-005 | Fresh-context recovery | No protocol to rebuild state after process restart | MEDIUM | Partial persistence exists but recovery procedure unclear |
| G-006 | Integration gap | GAME-001 not connected to mission system | HIGH | Executable runs but no mission linkage |
| G-007 | Budget controls | No max rounds, timeouts, or attempt limits | MEDIUM | Automation could run without progress |

## Required Improvements

### 1. Execution Integration (Gap G-001)
- Wire `seleccionar_siguiente_accion()` to dispatch `ejecutar()` 
- After execution, capture results as findings with provenance
- Update task and criterion state based on verification

### 2. Evidence Capture (Gap G-002)
- After `ejecutar()`, automatically create findings entries
- Capture: exit code, output snippets, timestamps, tool version
- Link findings to criteria via `evidence_ids`

### 3. Dependency Resolution (Gap G-003)
- Store task dependencies as JSON (already in schema)
- `seleccionar_siguiente_accion()` must check dependencies before returning
- Skip tasks whose dependencies are unmet

### 4. Loop Controls (Gap G-004)
- Add `max_attempts` parameter to task selection
- Track task selection history to detect loops
- Time budget enforcement per mission

### 5. Fresh-Context Recovery (Gap G-005)
- Document recovery procedure: load mission + verified progress
- Rebuild task state from last completed task
- Re-evaluate criteria from evidence store

### 6. GAME-001 Integration (Gap G-006)
- Connect GAME-001 executable execution to mission tasks
- Capture player movement data as evidence
- Record shutdown behavior as acceptance criteria evidence

### 7. Budget Controls (Gap G-007)
- Add `max_criteria_attempts` to `marcar_mision_completada()`
- Track attempts per criterion
- Timeout enforcement

## Epistemic States Registry

Each mission component can be in one of these states:

| Component | Possible States | Transitions |
|-----------|----------------|-------------|
| Criteria | PROVEN, PARTIAL, NOT_DETERMINED, PROVEN_ABSENT | → PROVEN only with valid evidence_ids |
| Tasks | PENDING, IN_PROGRESS, COMPLETED, BLOCKED | → COMPLETED after execution + verification |
| Mission | PENDING, ACTIVE, BLOCKED, COMPLETED | → COMPLETED only when all required PROVEN criteria PASS |
| Evidence | EXISTING, STALE, CONTRADICTORY, MISSING | → Update when artifact hash changes |

## Verification Contract

The following patterns MUST be enforced:

1. **PROVEN without evidence_ids → FAIL** (already implemented)
2. **PROVEN with valid evidence_ids → PASS if evidence.evidence_ids all PROVEN** (already implemented)
3. **PARTIAL with at least one PROVEN evidence → PASS** (already implemented)
4. **NOT_DETERMINED → PENDING, requires manual verification** (already implemented)
5. **Mission completion → FAIL if any required PROVEN criterion not PASS** (already implemented in `marcar_mision_completada()`)
6. **Evidence staleness**: If referenced finding's epistemic changes, criterion reverts to NOT_DETERMINED

## Failure Pattern Matrix

| Scenario | Before Fix | After Fix |
|----------|-----------|-----------|
| PROVEN criterion, no evidence_ids | Mission marked complete (FALSE COMPLETION) | Verification FAILS, completion BLOCKED |
| PROVEN criterion, nonexistent evidence_ids | Mission marked complete (FALSE COMPLETION) | Verification FAILS (finding not found) |
| PARTIAL criterion, no evidence | Varies by implementation | PASS (not required for completion) |
| Task with unmet dependencies | Selected anyway, may fail | Skipped until dependencies met |
| Infinite task selection | Possible, no progress | BLOCKED by max_attempts or loop detection |

## Recovery Procedures

### Process Restart Recovery
1. Open database connection
2. Recover mission state via `resumir_mision()`
3. Re-evaluate all criteria via `verificar_criterios_mision()`
4. Select next eligible action via `seleccionar_siguiente_accion()`
5. Execute and continue from verified state

### Failed Task Recovery
1. Mark task as BLOCKED if execution fails
2. Check for dependency blockers
3. Select next eligible task
4. Do not mark mission complete until criteria verified

## Next Actions

1. Wire dispatch `ejecutar()` to mission task execution
2. Add automated evidence capture after execution
3. Implement dependency checking in task selection
4. Add loop detection and budget controls
5. Integrate GAME-001 executable execution
6. Document recovery procedures
7. Add regression tests for all failure patterns