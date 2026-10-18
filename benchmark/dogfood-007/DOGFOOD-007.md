# DOGFOOD-007: FINDING ID PHASE A - Stable finding identity model

## Summary
Added FINDING_ID support to RXRE's runtime resolver while preserving legacy compatibility with display numbers.

## Objective
Implement Phase A of the stable finding identity model: add FINDING_ID support to RXRE's runtime resolver while preserving legacy compatibility with display numbers.

## Requirements Verification

### [DONE] Work in isolated worktree
- Worktree: `/tmp/rxre-finding-id-phase-a` (branch `repair/finding-id-phase-a`)
- Not modified the main worktree (112 modified + 101 untracked files preserved)

### [DONE] No global modifications
- Did NOT modify `347` existing findings globally
- Did NOT modify `evidence_search.py`, `trace_path.py`, P003, or `RX550-INVESTIGACION`

### [DONE] 5 pilot findings with FINDING_ID
- Added FINDING_ID to exactly 5 pilot findings:
  - `023-pm4-count-convencion-medida.md` -> `94929378a93a757f`
  - `023-pte-productor-sdma-gfx8.md` -> `59d2582fcffa70b8`
  - `043-asercion-struct-mqd-contra-offsets.md` -> `dab296d4eb72d972`
  - `043-pll-bsp-asi-pasi.md` -> `4a01ac343ec6ba56`
  - `043-vuelta-atras-035-y-036-leian-el-asic-equivocado.md` -> `9fd3d6252e986fcb`

### [DONE] Resolver supports both FINDING_ID and legacy display_number
- Resolver (`resuelve_a_finding_id`) tries FINDING_ID first (unique resolution)
- Falls back to legacy display_number (may be ambiguous)
- Returns: UUID if FINDING_ID was given, or number if legacy

### [DONE] Resolution types
- **FINDING_ID resolution**: UUID -> specific finding (unique even when numbers are ambiguous)
- **Legacy number resolution**: `023` -> number but may be ambiguous (multiple files share it)
- **Distinguishability**: Two findings with same number (`023-A` and `023-B`) can be distinguished via FINDING_ID

## Technical Decisions

### FINDING_ID format
- `FINDING_ID: <16-char-uuid>` line inserted after title line in frontmatter
- Persisted in finding frontmatter (not derived from path/content)
- UUID stored as raw 16 hex characters (not standard UUID dotted format)

### Resolver behavior
- `resuelve_a_finding_id(valor)` takes priority order:
  1. If valor is 16 hex chars and in `por_id` index -> return UUID
  2. Otherwise, fallback to `resuelve_a_finding(valor, por_num, nombres)` for legacy
- Legacy numbers may be ambiguous (marked with `!` flag in relation tuples)
- Never resolves ambiguous number to first match

### Backward compatibility
- Legacy `display_number` references still work (`023` resolves to `023`)
- Flag `AMBIGUA` set when legacy number has multiple candidates
- All 27 original selftests continue to pass

## Test Results

All deliverables tested and passing:

| Test Category | Result |
|---|---|
| Legacy lookup (backward compat) | PASS |
| FINDING_ID lookup (unique resolution) | PASS |
| Relation round-trip | PASS |
| Serialization (JSON) | PASS |
| Rename (ID preserved) | PASS |
| Move (ID preserved) | PASS |
| Content edit (ID preserved) | PASS |
| Provenance (1 file per ID) | PASS |
| Selftest regression (25 vectors) | PASS |

## Files Modified
- `tools/relations.py`:
  - Added `FINDING_ID_RX` regex pattern
  - Added `indice_findings_id()` function to index findings by FINDING_ID
  - Added `resuelve_a_finding_id()` resolver accepting both formats
  - Updated `escanear()` to read FINDING_ID from frontmatter
  - Modified `_add()` to carry finding_id in relation tuples
  - Updated JSON output to include `por_id`

## Deliverables Status
- All Phase A requirements met
- Ready for Phase B (full integration with claim system and benchmark suite)

## Next Steps (Phase B)
- Integrate FINDING_ID with claim registry
- Add FINDING_ID to benchmark contracts
- Extend automation to handle finding identity transitions
- Full performance validation with FINDING_ID-aware operations