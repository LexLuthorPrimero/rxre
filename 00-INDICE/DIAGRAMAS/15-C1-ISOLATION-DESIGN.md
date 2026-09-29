# 15 — C1 Isolation Design Flow

**STATUS:** `DOCUMENTARY DESIGN`
**ISOLATION_DESIGN:** `PREPARED_FOR_REVIEW`
**EXECUTION_EVIDENCE:** `NO`
**C1:** `DEFERRED`
**SOURCE:** `04-IMPLEMENTACION/C1-ISOLATION-DESIGN-v1.0.md`

Este diagrama es una vista derivada del diseño documental. No representa una ejecución, no autoriza acciones y no convierte `OWNERSHIP_PARTIAL` en `OWNERSHIP_FULL`.

```mermaid
flowchart TD
    B["BASELINE\nsnapshot/provenance"] --> P["PRECHECK\nidentity, namespace, D-state, procs_blocked, PSI, clients"]
    P --> Q{"CONTAMINATION?"}
    Q -- "YES" --> N["NO-GO\nISOLATION REQUIRED"]
    Q -- "UNKNOWN" --> N
    Q -- "NO" --> O["OWNERSHIP_REQUEST\nconceptual only"]
    O --> I["ISOLATION\nfuture authorized phase"]
    I --> V["VERIFY\nreadback + ownership evidence"]
    V --> G["GUARD WINDOW\n120s / 5s samples"]
    G --> S{"STABLE?"}
    S -- "NO / UNKNOWN" --> N
    S -- "YES" --> A["C1_AUTHORIZATION\nTTY + RUN-C1 + sudo"]
    A --> C["C1\nfuture execution only"]
    C --> R["RESTORE\nplanned inverse/readback"]
    R --> VR{"RESTORE_READBACK_OK?"}
    VR -- "NO" --> M["MANUAL / ABORT"]
    VR -- "YES" --> F["VERIFY_RESTORE\nfinal evidence"]
```

```text
FULL_OWNERSHIP=identity + client inventory + writer resolution + stable guard + restore plan
CURRENT_OWNERSHIP=PARTIAL
CURRENT_C1=DEFERRED
RESTORE_VALIDATED=NO
```

**Sources:** `P0`, `C1-DOC`, `C1-CODE`, `C1-SIDE`, `R5`, `OBS`, `DOC-REC`, `C1-ISOLATION-DESIGN-v1.0.md`.
