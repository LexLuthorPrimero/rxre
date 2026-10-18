# RXRE Autonomy Competency Matrix

## Comparison with External Autonomous Systems

| Dimension | LongHorizon-Harness | LangGraph Durable Execution | OpenHands | SWE-agent | AgentRewind | RXRE Current State |
|-----------|---------------------|----------------------------|-----------|-----------|-------------|-------------------|
| **Persistent mission representation** | JSONL ledger files (`rounds/round_NNN.jsonl`) | Checkpoint dicts, state snapshots | Conversation + event history JSON | Single-turn, no persistence | Checkpoint/rolling memory | SQLite DB with missions, criteria, tasks, findings |
| **Task dependency management** | Explicit dependency graph, blocked state | StateGraph edges | Task queue with dependencies | Linear action sequence | Rollback to checkpoint | Task dependencies in `dependencies` field |
| **Autonomous action selection** | Manager role + task queue | Node selection via StateGraph | Human-in-the-loop | Action sequence predetermined | Rewind to known good state | `seleccionar_siguiente_accion()` by priority |
| **Execution and observation** | Executor role, tool adapters | Node execution, side effects | Tool execution, event capture | Tool use, output parsing | Execute, observe state | `dispatch.ejecutar()`, results stored |
| **Independent acceptance verification** | Auditor role (independent file inspection) | Manual or external verification | Human review | Self-contained tests | Independent oracle | `verificar_criterios_mision()` + findings |
| **Evidence provenance and validity** | Full provenance in trajectory files | Limited | Event history | Code patches as evidence | Checkpoint validity | Finding table with `provenance` field |
| **Checkpointing and recovery** | Checkpoint after each round | Periodic checkpoint in DB | Conversation save/load | None (single turn) | Full state checkpoint | SQLite persistence survives restart |
| **Fresh-context operation** | Fresh context each round | Resume from checkpoint | Session save/resume | Single session | Resume from checkpoint | Process restart = fresh context |
| **Failure diagnosis and retry** | Auditor identifies, retry count | Built-in retry policies | Error events logged | Test failures | Rollback and retry | Task status tracking |
| **Loop and budget control** | `max_rounds`, per-role timeouts | Streamlit interface control | Conversation limits | Max tokens | Step limits | Available via tests |
| **Agent-oriented tool interface** | LLM-friendly JSON protocol | LangChain Runnable | Custom SDK | Action parsing | Checkpoint API | `dispatch.py` with capability registry |
| **End-to-end engineering success** | Independent auditor verifies completion | Human verification | Human review | PR merge | Success definition | Mission COMPLETED only with PROVEN evidence |

## Key Architectural Features of Each System

### LongHorizon-Harness
- **Three-role architecture**: Manager → Executor → Auditor
- **Fresh context each round**: Prevents context pollution
- **Independent auditor**: Never trusts executor's claims
- **Durable verified state**: Persisted to JSONL files
- **Budget controls**: `max_rounds`, per-role timeouts

### LangGraph Durable Execution
- **Checkpoint-based resumption**: Automatic state recovery
- **StateGraph**: Explicit state transitions
- **Idempotent nodes**: Safe resumption from any point
- **Separate memory from state**: Cached vs durable data

### OpenHands
- **Conversation persistence**: Full session save/restore
- **Event history**: All actions logged
- **Pause/resume semantics**: Human intervention points
- **Separate durable state**: Transient context vs persistent data

### SWE-agent
- **Agent-Computer Interface**: Clear action protocol
- **Repository exploration tools**: File reading, editing
- **Test output representation**: Parsed for LM consumption
- **Action limits**: Prevents unproductive loops

### AgentRewind (Paper)
- **Checkpointing**: Full state snapshots
- **Recovery**: Rollback to last good state
- **Distinction**: Recoverable vs corrupted state
- **Benchmarks**: Long-horizon engineering tasks

## RXRE Competency Assessment

### Strengths
- ✅ Persistent SQLite database with full mission state
- ✅ Evidence-based verification (findings table)
- ✅ Task priority-based selection
- ✅ Independent criterion verification
- ✅ Process-resilient persistence

### Gaps (High-Impact)
- ⚠️ **Missing independent auditor role**: No separate verification process
- ⚠️ **No fresh-context recovery**: Cannot rebuild state from goal + progress
- ⚠️ **No loop/budget controls**: Infinite task selection possible
- ⚠️ **No explicit dependency resolution**: Dependencies not checked before selection
- ⚠️ **No tool execution integration**: Dispatch system not connected to missions

### Resolved from External Models
- ✅ **Evidence-based verification** (adapted from LongHorizon-Harness auditor concept)
- ✅ **Persistent state** (adapted from LangGraph checkpointing)
- ✅ **Task prioritization** (adapted from OpenHands task queue)

## Recommendations for RXRE

1. **Add independent auditor capability**: Separate process to verify mission outcomes
2. **Implement checkpoint/recovery protocol**: Serialize mission state for process restart
3. **Add budget controls**: Max rounds, timeouts, task count limits
4. **Connect dispatch to missions**: `ejecutar()` should update mission state
5. **Add dependency resolution**: Check task dependencies before selection
6. **Implement loop detection**: Track repeated task patterns