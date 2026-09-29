# 10 — Navegación documental

**DIAGRAM_ID:** V-11
**STATUS:** DRAFT/CONFLICT
**LAST AUDITED:** 2026-09-24
**SOURCE_OF_TRUTH:**
- `README.md`
- `00-INDICE/README.md`
- `00-INDICE/MASTER-RESEARCH-STATUS.md`
- `00-INDICE/MASTER-PLAN.md`
- `00-INDICE/R2-GLOBAL-DOCUMENTATION-MAP.md`
- `00-INDICE/PROJECT-DOCUMENTATION-STATUS.md`
- `04-IMPLEMENTACION/IMPLEMENTATION-ROADMAP.md`
- `04-IMPLEMENTACION/IMPLEMENTATION-SAFETY-RULES.md`

**CONFLICTS:**
- El mapa global ahora se marca `DRAFT/CONFLICT` y se está reindexando; no es una vista `LIVE`.
- `FINAL-RESEARCH-STATUS.md` es histórico aunque aparece como entrada de navegación.
- El roadmap F/G/K ya no declara un ciclo en su diseño; esta vista sigue requiriendo reauditoría.
- README/decisiones ya tienen una reconciliación documental, pero las auditorías repair/Set I
  permanecen como snapshots y no fuente de estado actual.
- H12/WSI y capabilities runtime siguen sin confirmar.

**NOTE:** este diagrama muestra navegación; no convierte ningún documento histórico en LIVE.

## Flujo de navegación

```mermaid
flowchart TD
    R["[DOC] README.md"] --> MRS["[DOC] MASTER-RESEARCH-STATUS.md (D6)"]
    MRS --> D["[DRAFT] DIAGRAMAS/README.md"]

    D --> M["[DRAFT] Maestro del proyecto"]
    D --> S["[DRAFT] Estados científicos"]
    D --> N["[DRAFT] Navegación documental"]
    D --> H["[DRAFT] Claims C1 + H1–H12 (V-03)"]
    D --> P["[DRAFT] Roadmap visual (V-02)"]
    D --> C1V["[DRAFT] Pipeline/state C1 (V-04/V-12)"]
    D --> AG["[DRAFT] Agentes y seguridad (V-09)"]
    D --> TR["[DRAFT] Matriz de trazabilidad (V-13)"]

    MRS --> MP["[PLAN] MASTER-PLAN.md"]
    MRS --> RD["[DRAFT] IMPLEMENTATION-ROADMAP.md"]
    MRS --> SAFE["[AUTH] IMPLEMENTATION-SAFETY-RULES.md"]
    MRS --> HYP["[DRAFT] HYPOTHESIS-REGISTER.md"]

    MP --> EXP["[DESIGN] Experimentos FASE E–Q"]
    MP --> K["[DESIGN] FASE K Performance Lab"]
    K --> L["[DESIGN] FASE L/Tuning"]
    K --> Q["[DESIGN] FASE Q/Mesa"]
    K --> MCNT["[DESIGN] FASE M/Counters"]

    EXP --> RES["[RESULT] Resultados y artefactos"]
    RES --> EV["[EVIDENCE] Evidence matrix / audit"]
    EV --> V["[VERDICT] Veredictos"]

    SNAP["[SNAPSHOT] FINAL-RESEARCH-STATUS"] -.-> R
    REP["[SNAPSHOT] REPARATION/POST-REPAIR"] -.-> R
    PRE["[SNAPSHOT] PRE-RUN protocols"] -.-> RES
    OLD["[HISTORICAL] Backup / RX550_Iterative_Research"] -.-> R

    C1["[REAUDIT] R-4B D6 vs snapshots"] -.-> MRS
    C2["[DRAFT] Map DRAFT/CONFLICT"] -.-> N
    C3["[RECONCILED] D1–D4 documental"] -.-> REP
    C4["[REAUDIT] F/G/K acyclic source"] -.-> RD

    classDef doc fill:#e8f1ff,stroke:#2563eb,color:#111827
    classDef draft fill:#fff4cc,stroke:#b7791f,color:#111827
    classDef snapshot fill:#eeeeee,stroke:#6b7280,color:#111827
    classDef conflict fill:#ffd6d6,stroke:#b91c1c,color:#111827
    classDef auth fill:#ffe0e0,stroke:#991b1b,color:#111827
    classDef result fill:#e6ffed,stroke:#15803d,color:#111827

    class MRS doc
    class R conflict
    class D,M,S,N,H,P,C1V,AG,TR,MP,EXP,K,L,Q,MCNT,HYP draft
    class SAFE auth
    class RES,EV,V result
    class SNAP,REP,PRE,OLD snapshot
    class RD,C1,C2,C3,C4 conflict
```

## REFERENCIA CANÓNICA (no equivale a vista `LIVE`)

| Documento/área | Uso |
|---|---|
| `MASTER-RESEARCH-STATUS.md` | Fuente de estado; Addenda D6 prevalece; la vista derivada requiere reauditoría |
| `MASTER-PLAN.md` | Estructura y diseño futuro; no es autorización |
| `IMPLEMENTATION-SAFETY-RULES.md` | Límite de autorización y congelación; no concede permisos |
| R-4A/R-4B v2.3/R-4C/FASE D results | Resultados canónicos dentro de alcance; R-4B se representa solo con la terna D6 |

## DRAFT / PROVISIONAL

| Documento/área | Uso |
|---|---|
| `HYPOTHESIS-REGISTER.md` | Registro textual provisional; no es un veredicto ni una vista `LIVE` |

## HISTORICAL / SNAPSHOT

| Documento/área | Regla |
|---|---|
| `FINAL-RESEARCH-STATUS.md` | No usar como estado vivo |
| `REPARATION-PLAN.md` | Plan/checkpoint histórico |
| `POST-REPARACION-DOCUMENTAL-AUDIT.md` | Auditoría histórica |
| Set I y auditorías de reorganización | Trazabilidad, no estado actual |
| PRE-RUN R-4B/R-4C | Protocolos previos, no ejecución actual |
| Backup y raíz antigua | Historia preservada, no operación |
| `/tmp` | Localizadores perdidos/no verificables |

## CONFLICT

- La vista sigue en `DRAFT/CONFLICT` hasta reauditar el mapa y las capability claims.
- `FINAL-RESEARCH-STATUS` y auditorías repair/Set I son snapshots, no estado vivo.
- H12/WSI y capacidades runtime no confirmadas; r1–r3, r4/H12-3 y H12-4 tienen alcopes distintos.
- C1 sidecar 37/37 vs provenance R5 24/24: `CONFLICT`; no runtime v2 creado.
- `R2-GLOBAL-DOCUMENTATION-MAP` es ahora una vista `DRAFT/CONFLICT`, no un mapa vivo.
- `ESTADOS-ES-EN.md` es una taxonomía ampliada pero todavía provisional.

## Regla de navegación

Un nuevo documento debe enlazarse desde una sola capa:

- estado: `00-INDICE/MASTER-RESEARCH-STATUS.md`;
- plan: `00-INDICE/MASTER-PLAN.md` o `IMPLEMENTATION-ROADMAP.md`;
- seguridad: `IMPLEMENTATION-SAFETY-RULES.md`;
- resultados: carpeta del experimento;
- auditorías: `01-AUDITORIA/`;
- fuentes: `05-FUENTES-EXTERNAS/`.

Los diagramas no sustituyen esos enlaces.
