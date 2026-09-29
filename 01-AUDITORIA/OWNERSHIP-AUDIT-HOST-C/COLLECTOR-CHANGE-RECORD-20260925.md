# COLLECTOR-CHANGE-RECORD — R1 collector identity corrections

```
COLLECTOR_CHANGE=IMPLEMENTED_NOT_EXECUTED
COLLECTOR_HASH_BEFORE=41fee7943f2555d5870b5fbefe1ed3bc0abdd06894ad95636b18fc247689c5d9
COLLECTOR_HASH_AFTER=a2cf80c7cc28f27e48fc637df999a27a1d3ee2bbce1339d84f0cbf295f57f2f0
COLLECTOR_LINES=1158 -> 2268 (+1218 -108)
COLLECTOR_RUNTIME_EXECUTED=NO
PRIVILEGED_EXECUTION=NO
SUDO_INVOKED=0
R1_EXECUTED=NO
```

**Fecha:** 2026-09-25 · `HOST_SCOPE=HOST-C` (`DECLARED`) · `HEAD=c6146788e0d4fb12d9b0ec1209fa2840692de0c5`
**Fichero modificado (único):** `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/privileged_read_collector.py`
**Fichero creado (único):** `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/test_privileged_read_collector.py`

El collector **no se ejecutó** contra el sistema real. Rechaza ejecutarse sin argumentos
(`usage: …`, sin JSON). No produjo ningún artefacto. No invocó `sudo`.

---

## 1. Reconciliation with the R1 preflight

`R1-PREFLIGHT-drm-identity-and-command-audit.md` (hash `61f5d5f7…`) queda **intacto** como
histórico. Estas son las afirmaciones suyas que quedaron obsoletas al implementar el cambio, y
su estado actual. No se reescribió el documento.

| Afirmación en R1-PREFLIGHT | Fecha | Estado actual |
|---|---|---|
| `COLLECTOR_CHANGE_REQUIRED=YES` · `CHANGE_REASON=STATIC_DRM_NODE_MAPPING` | 23:40Z | **OBSOLETE** — implementado |
| "Nada de esto se ha escrito. El collector sigue byte-idéntico" (§Parte 3) | 23:40Z | **OBSOLETE** — los 9 cambios están escritos |
| `CAPABILITY_COVERAGE=5_OF_11_WITHOUT_CHANGE` (§Parte 5) | 23:40Z | **OBSOLETE** — 11/11 implementadas |
| "hash `41fee794…` byte-idéntico" | 23:40Z | **SUPERADO** — ahora `a2cf80c7…`; `41fee794…` queda como hash *before* |
| C07 = `findmnt -n -o SOURCE,FSTYPE /` (§Parte 2) | 23:40Z | **SUPERADO** — sustituido por `parse_mountinfo()` en Python puro |
| `R1_EXECUTABLE_WITH_CURRENT_COLLECTOR=NO` | 23:40Z | **SUPERADO** — ejecutable, pero sigue sin autorización |
| Gaps 1–5, 10 capabilities | 23:40Z | **CERRADOS** por código y por test |

**Sobre C07.** El preflight preveía `findmnt`. Se implementó `parse_mountinfo()` porque
`/proc/self/mountinfo` ya contiene mount point, fstype y source, y el encargo pedía no
introducir comandos shell resolubles en Python. El resultado es más robusto: no depende de que
`findmnt` exista ni de su locale. **Comandos que el collector puede emitir: `fuser`, `lsof`,
`ps`, `systemctl show`, `tty`. Ninguno muta.**

---

## 2. Gap-by-gap implementation

| GAP | Requirement | Implementation | Verified by |
|---|---|---|---|
| 1 | dynamic card/render | `resolve_gpu_identity()` → `GPU_CARD_NODE` / `GPU_RENDER_NODE` from BDF | `test_04`, `test_05`, `test_06` |
| 2 | dynamic debugfs minor | `debugfs_client_attribution()` derives minor from the render node, never `dri/1` | `test_12`, `test_12b`, `test_12c`, `test_12d`, `test_14`, `test_14b` |
| 3 | PCI identity gate | `pci_identity()` verifies vendor/device/class/driver before any node is used | `test_10`, `test_10b`, `test_11`, `test_11b` |
| 4 | BDF → node discovery | `discover_drm_nodes()`, forward + reverse must agree | `test_09`, `test_09b`, `test_04` |
| 5 | storage identity | `resolve_storage_identity()` mountinfo → source → `/sys/class/block` → parent disk | `test_07`, `test_08`, `test_08b`, `test_08c` |
| 6 | `/proc/<pid>/maps` | `scan_maps()` with `MAPS_READABLE` / `MAPS_PERMISSION_DENIED` / `ABSENT` / `ERROR` | `test_13`, `test_13b`, `test_13c`, `test_13d` |
| 7 | kwin coverage | `compositor_gpu_relation()`: OBSERVED / UNKNOWN only, never inferred | `test_compositor_relation_never_infers_gpu_usage` |
| 8 | root coverage | `TOTAL_PIDS`, `ROOT_PIDS`, `ROOT_FD_COVERAGE`, `ROOT_MAPS_COVERAGE`, `ROOT_NAMESPACE_COVERAGE` | emitted in `ownership.root_coverage` |
| 9 | ownership boolean | kept, labelled `NON_AUTHORITATIVE`; 11-condition matrix is the verdict | `test_15`, `test_15b`, `test_15c`, `test_15d` |
| 10 | capability matrix | `CAPABILITY_MATRIX`, 11 rows, each naming real code | `test_capability_matrix_names_real_code` |
| 11 | read-only safety | AST proof, not regex | `ReadOnlyProofTests`, 12 tests |

## 3. Discovery chain, as implemented

```
/sys/bus/pci/devices/0000:01:00.0/{vendor,device,class,driver}
        │  must equal 0x1002 / 0x699f / 0x030000 / amdgpu
        ▼
forward : /sys/bus/pci/devices/<BDF>/drm/{card*,renderD*}
        ▼  must AGREE
reverse : /sys/class/drm/<node>/device -> realpath -> BDF
        ▼
exactly one card* + one renderD*  ── else AMBIGUOUS_CANDIDATE / ROLE_MISSING
        ▼
GPU_CARD_MINOR, GPU_RENDER_MINOR  ── integers read off the node names
        ▼
/sys/kernel/debug/dri/<RENDER_MINOR>/clients
        accepted only if the directory exists AND holds amdgpu_* markers
        AND exactly one amdgpu DRM device was discovered
        otherwise DEBUGFS_CLIENT_ATTRIBUTION=NOT_AVAILABLE
```

Node numbers are outputs of the resolution, never inputs to it. Every node rejected during
discovery is recorded with its resolved BDF and driver, so an exclusion is auditable.

**Observed on HOST-C during design (read-only, 23:30–23:55Z):** `card0`→`0000:00:02.0`
(driver `i915`), `card1`→`0000:01:00.0` (driver `amdgpu`), `renderD128`→`0000:00:02.0`,
`renderD129`→`0000:01:00.0`. The Intel is excluded by BDF, not by index.

## 4. Ordering and abort

`main()` now runs: HOST → PCI → DRM → storage → namespaces/processes → fd/fdinfo → maps →
debugfs → aggregated GPU → ownership → output matrix, and the order is recorded in the payload
as `identity.resolution_order`.

If `GPU_IDENTITY_STATUS != PROVEN`, the collector prints `abort_payload()` and **stops**. That
payload has no `ownership` key at all: an empty ownership document would be indistinguishable
from an observation of "no clients". If only storage identity fails, the storage metrics are
skipped (`STORAGE_METRICS=SKIPPED_IDENTITY_NOT_PROVEN`) and the rest continues, because the GPU
evidence does not depend on it.

## 5. The ownership boolean is not the verdict

`ownership_full` is computed exactly as before — `root_visibility_complete and active_gpu==0 and
active_storage==0 and active_agents==0` — and is **not** modified to produce a desired outcome.
It is emitted as:

```
COLLECTOR_OWNERSHIP_BOOLEAN = { AUTHORITATIVE: false,
                               CLASSIFICATION: "NON_AUTHORITATIVE",
                               value: <the same boolean> }
```

`final.OWNERSHIP` now comes from `AGENTS_OWNERSHIP_MATRIX.OWNERSHIP_CRITERION_STATE`, and
`final.OWNERSHIP_LEGACY_BOOLEAN_NON_AUTHORITATIVE` carries the old boolean separately.

`writers_resolved` (R2) and `guard_and_restore` (R3) are hardcoded `NOT_EVALUATED` with their
route, so the aggregate **cannot** reach `FULL` from this collector. `test_15` proves it by
feeding a context where the legacy boolean would be `True`.

## 6. Payload schema changes

Renamed, because the old names asserted something the new code no longer guarantees:

| Old key | New key | Reason |
|---|---|---|
| `ownership.sda_clients` | `ownership.storage_clients` | the device is not `sda` |
| `sda_identity` | `storage_identity_evidence` | same |
| `queue.initial.<attr>` | `queue.initial.queue.<attr>` | `read_queue()` now returns a status envelope |

Added: `identity.{HOST,GPU,STORAGE,DEBUGFS,resolution_order}`,
`AGENTS_OWNERSHIP_MATRIX`, `COLLECTOR_OWNERSHIP_BOOLEAN`, `CAPABILITY_MATRIX`,
`ownership.root_coverage`, `ownership.compositor_gpu_relations`.

No capability was lost: 6 pre-existing ones are preserved and 5 were added
(PCI identity, BDF→node discovery, storage identity, `maps`, capability register). The
preflight's count of 11 is confirmed correct.

## 7. Test results

```
TESTS=43 + existing 54 (1 skipped)
TESTS_PASS=97
TESTS_FAIL=0
```

| Suite | Result |
|---|---|
| `test_privileged_read_collector.py` (new, 43) | **OK** |
| `test_c1_isolation_automator.py` (existing, 54) | **OK, skipped=1** — no regression |

Every test builds a synthetic sysfs/procfs/debugfs tree in a temp directory. **No test touches
the live host, invokes `sudo`, `systemctl`, C1, or the collector itself.**

Four defects in the new test suite were found and fixed during this phase, all in the tests and
not in the collector: a stray `]`; a synthetic tree missing the `<pci>/drm/<node>/device`
symlink (which had made the driver lookup resolve through the path text instead of a real
link); partitions created as sibling block devices instead of children of their parent disk; and
an incomplete attribute allowlist that flagged `re.compile` and `str.splitlines` as mutations.

**Not run:** the `64/64` and `110/110` figures. They belong to the capture host and
`DOCUMENTATION-GAPS.md` item 5 already records that no suite has been re-executed since the host
change. They are **not** claimed here.

## 8. Residual risk

The one failure mode that survived the preflight review is **not** fixed, only mitigated:
`scan_fds()` still matches DRM nodes by path prefix for the *contrast* list, and the FD scan can
only see what the kernel lets the observer see. If privilege is insufficient, R1 will report
`PermissionError` per PID — which is the honest result, and the reason `OWNERSHIP` stays
`PARTIAL`. R1 remains **unexecuted and unauthorized**.

## 9. Guarantees

```
SYSTEM_CHANGES=0        GPU_CHANGES=0         SERVICE_CHANGES=0
SYSFS_WRITES=0          PROCESS_TERMINATED=0  PROCESS_SUSPENDED=0
PATCHES_APPLIED=0       PACKAGE_INSTALLS=0     BENCHMARKS_EXECUTED=NO
C1_EXECUTED=NO          SUDO_INVOKED=0        R1_EXECUTED=NO
MODIFIES_AGENTS_MD=NO   MODIFIES_ROUTER=NO    MODIFIES_CENSUS=NO
MODIFIES_ROUTING_LOG=NO MODIFIES_HISTORICAL_CAPTURES=NO
```

Unchanged and re-verified: `AGENTS.md` `d5fa85a4…`, `README.md` `4524f6f6…`,
`DOCUMENTATION-INVENTORY.tsv` `a4ccacbc…`, `DOCUMENTATION-ROUTER.md` `9ef58048…`,
`ROUTING-LOG.jsonl` `ff9110e9…` (24 events), the BLK-02 capture `6c6e0353…`, the ownership
audit `3bd1c05c…`, the closure attempt `9f7f8378…`, the reconciliation `06f337c7…`, and both
R1 documents `5832a468…` / `61f5d5f7…`.
