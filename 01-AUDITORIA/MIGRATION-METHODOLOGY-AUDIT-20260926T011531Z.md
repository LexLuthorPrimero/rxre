# MIGRATION-METHODOLOGY-AUDIT — RX550-INVESTIGACION

> **Registro histórico de auditoría. NO es el estado canónico del proyecto.**
> Persistido por decisión explícita del usuario. No sobrescribe ningún documento previo.

```
DOCUMENT_ID=MIGRATION-METHODOLOGY-AUDIT
CREATED_UTC=2026-09-26T01:15:31Z
TYPE=AUDIT_RECORD
CANONICAL_STATE=NO
IMPLEMENTATION=NOT_EXECUTED
SYSTEM_CHANGES=0  GPU_CHANGES=0  PRIVILEGED_WRITES=0  EXPERIMENTS_EXECUTED=0
COMMITS=0  PUSHES=0
```

**Host de la auditoría:** `kalm` · kernel `7.1.3-200.nobara.fc44.x86_64` · `HOST_SCOPE=HOST-C` (`DECLARED`)
**Git:** `HEAD=c6146788e0d4fb12d9b0ec1209fa2840692de0c5` · 0 commits · 0 push · 360 rutas staged

---

## CORRECCIÓN DE TERMINOLOGÍA OPENCODE (verificada, no de memoria)

Esta corrección se incorpora **antes** dePersistir, y fue verificada contra la documentación
oficial. La primera versión de este informe contenía terminología **V1** presentada como
vigente; eso era un error de provenance (§CORRECCIÓN-DEL-AUTOR).

### Lo verificado

| Afirmación | Estado | Evidencia |
|---|---|---|
| La acción correcta es `action: shell`, no `bash` | **CONFIRMADO** | aviso de migración explícito en la doc V2 |
| La clave correcta es `permissions`, no `permission` | **CONFIRMADO** | ídem; 17 vs 8 apariciones en la página V2 |
| La delegación es `action: subagent`, no `task` | **CONFIRMADO** | ídem |
| `websearch` es acción de primer nivel en V2 | **CONFIRMADO** | sección `Websearch` en la navegación V2 |
| Directorio `.opencode/agents/` (plural) | **CONFIRMADO** | 4 apariciones en la doc V2 de agentes |
| Las reglas son un **array ordenado** de `{action, resource, effect}` | **CONFIRMADO** | ejemplo literal de la doc V2 |
| Gana la última regla que coincide | **CONFIRMADO** | "The last matching rule wins" |
| Sin regla que coincida → `ask` | **CONFIRMADO** | "If no rule matches, OpenCode uses `ask`" |

### Fuentes

- `https://opencode.ai/v2/docs/agents` — HTTP 200
- `https://opencode.ai/v2/docs/permissions` — HTTP 200

Ambas recuperadas el `2026-09-26T01:15Z`. Contenido externo: **soporta afirmaciones sobre
OpenCode, nunca sobre nuestro host.**

### CORRECCIÓN-DEL-AUTOR — fallo de provenance propio

La primera versión de este informe propuso `.opencode/agent/` (singular) y un objeto de
configuración anidado con `permission.bash`. **Ambas cosas eran nomenclatura V1.** La causa:
consulté `https://opencode.ai/docs/…` (sin `/v2/`) y reporté su terminología como si fuera
vigente.

Esto es **RC-4** —sesgo de verificación del autor— operando sobre mí mismo: afirmé un
detalle técnico sin verificarlo, y un chequeo de 30 segundos lo habría detectado. Es la
evidencia más fuerte a favor de que el `EVIDENCE-AUDITOR` no puede ser el mismo agente que
escribe.

### Sintaxis V2 verificada (literal de la documentación)

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "permissions": [
    { "action": "shell", "resource": "*",           "effect": "ask"   },
    { "action": "shell", "resource": "git status *","effect": "allow" },
    { "action": "shell", "resource": "git diff *",  "effect": "allow" },
    { "action": "shell", "resource": "git push *",  "effect": "deny"  }
  ]
}
```

Tres campos obligatorios: `action` (acción), `resource` (valor usado), `effect`
(`allow` | `deny` | `ask`). Wildcard de valor completo: `*` = cero o más, `?` = exactamente uno.

### Limitación conocida y declarada

La documentación de V1 indica que el usuario siempre puede invocar un subagente con `@`
aunque sus task-permissions lo nieguen. **No está verificado si V2 mantiene ese
comportamiento** → `REQUIRES_VERIFICATION`. Si se mantiene, `permissions` restringe al
modelo, no al usuario: es un guardián, no una frontera de seguridad.

---

## 1. ESTADO ACTUAL

**No existe arquitectura de agentes.** `AGENTS.md` (257 líneas) es el único mecanismo.
No hay `.opencode/`. `~/.config/opencode/` solo contiene `service.json`.

| Capa | Ubicación real | Problema |
|---|---|---|
| Estado canónico | `PROBLEM-STATUS-FINAL.md`, `README.md`, `FINAL-RELEASE-REPORT.md` | cita un host distinto al vivo (MIG-03) |
| Plan maestro | `00-INDICE/MASTER-PLAN.md` (857 líneas) | §J dice «sin código»; el código existe (MIG-11) |
| Gates | `P0-EXPERIMENTAL-VALIDITY-GATE`, `NEXT-BLOCKER-ANALYSIS.md` | gate P0 ejecutado en HOST-A (MIG-04) |
| Dependencias | `NEXT-BLOCKER-ANALYSIS.md`, `R2-DEPENDENCY-GRAPH.md`, `R3-1-DEPENDENCY-MATRIX.md` | ya existen — no reinventar |
| Evidencia | 1577 filas de censo, 1577 de routing, 24 eventos de log | sin provenance por entrada |
| Vocabulario | **4 en coexistencia** (MIG-07) | ver `MIG-07-VOCABULARY-MAPPING-20260926.md` |
| Herramientas | `tools/validate_rx550_final.py`, `privileged_read_collector.py` | ninguna ejecutable de extremo a extremo |
| Git | 8 commits, **0 tocan el collector**, 360 staged, 13 untracked | cadena R1 fuera de git (MIG-12) |

**R1: 2 ejecuciones intentadas, 0 con evidencia.** Run 1 abortó en identidad (DEFECT-01/02);
run 2 murió en el primer PID (DEFECT-03). **El barrido de `/proc` nunca se ejecutó con éxito.**

## 2. PROBLEMAS (20)

| ID | PROBLEMA | TIPO | SEV | BLOQUEA |
|---|---|---|---|---|
| MIG-01 | `UnboundLocalError` en `observe()` | TOOL_DEFECT | CRIT | R1 |
| MIG-02 | Ningún test ejecuta el barrido (154 tests, 0 tocan orquestación) | TEST_COVERAGE_DEFECT | CRIT | todo lo derivado |
| MIG-03 | `PROBLEM-STATUS-FINAL.md` cita captura HOST-B; host vivo es HOST-C | STATE_INCONSISTENCY | ALTO | current-state |
| MIG-04 | `P0=B__CONTAMINATED` procede de gate en HOST-A | STATE_INCONSISTENCY | ALTO | P0, C1 |
| MIG-05 | Censo dice «Cinco contradicciones» y lista C1–C6 | DOCUMENTATION_DEFECT | MEDIO | censo |
| MIG-06 | C1–C6 sin resolver | CONTRADICTION | MEDIO | interpretación |
| MIG-07 | **4 vocabularios de evidencia/estado coexistiendo** | CONFLICT | ALTO | toda clasificación |
| MIG-08 | Árbol huérfano `NOTEBOOKLM/` (106 ficheros) fuera del repo | PROVENANCE_DEFECT | MEDIO | trazabilidad |
| MIG-09 | `write_test.py` escribe `power/control` con root, sin gate formal | SAFETY_DEFECT | ALTO | seguridad |
| MIG-10 | `validate_rx550_final.py`: 2 defectos documentados no corregidos | TOOL_DEFECT | MEDIO | validación |
| MIG-11 | MASTER-PLAN §J «sin código»; existe `WORKLOAD-SINTETICO/src/*.cpp` | DOCUMENTATION_DEFECT | MEDIO | plan |
| MIG-12 | Git: 0 commits tocan el collector; R1 fuera de git | PROVENANCE_DEFECT | ALTO | reproducibilidad |
| MIG-13 | R1 sin evidencia (2 runs, 0 éxito) | MISSING_EVIDENCE | ALTO | OWNERSHIP |
| MIG-14 | `04-IMPLEMENTATION/tests/` inalcanzable | METHOD/ENVIRONMENT | MEDIO | verificación |
| MIG-15 | 140 referencias rotas (~70 reparables, no aplicadas) | DOCUMENTATION_DEFECT | MEDIO | navegación |
| MIG-16 | 59 documentos huérfanos | DOCUMENTATION_DEFECT | BAJO | navegación |
| MIG-17 | Camino de excepción de `__main__` omite el bloque `privilege` | TOOL_DEFECT | BAJO | provenance |
| MIG-18 | Btrfs: `CONFLICT`; actual ext4, histórico Btrfs | LIMITATION_CONFIRMED | MEDIO | G-08 |
| MIG-19 | `SECURITY_REVIEW=NOT_READY` (66 ficheros con rutas personales) | OPEN | MEDIO | publicación |
| MIG-20 | Causa de MIG-14 | UNKNOWN_CAUSE | MEDIO | verificación |

## 3. BLOCKERS

**Directos:** MIG-01, MIG-02, MIG-13. **Indirectos:** MIG-03, MIG-04, MIG-07, MIG-09, MIG-12.
`R1_SAFE_TO_AUTHORIZE` debe volver a **NO** por MIG-01.

## 4. CAUSAS RAÍZ

| ID | Causa | Estado | Explica |
|---|---|---|---|
| **RC-1** | Los tests solo alcanzan funciones hoja, nunca la orquestación | CONFIRMED | MIG-01 vivió 154 tests en verde; DEFECT-01 necesitó revisión independiente |
| **RC-2** | La identidad de host no se propaga al estado | CONFIRMED | MIG-03, MIG-04, DEFECT-02, y las contradicciones C2/C3/C4 |
| **RC-3** | No hay estado estructurado; la prosa es el estado | CONFIRMED | MIG-05, MIG-07, MIG-08, MIG-11, MIG-15, MIG-16 |
| **RC-4** | Sesgo de verificación del autor | CONFIRMED | DEFECT-01 (104 tests), DEFECT-03 (154 tests), y la corrección V1→V2 de este mismo informe |

**Desconocidas:** causa de MIG-14 (`ROOT_CAUSE=UNKNOWN`); causa Btrfs histórica
(`ROOT_CAUSE=UNKNOWN`, ya así documentada).

## 5. ÁRBOL DE DEPENDENCIAS

```
RC-1 tests-solo-hojas ──┬─→ MIG-01 UnboundLocalError ──→ MIG-13 R1 sin evidencia
                        │                                     ↓
RC-2 host-no-propagada ─┼─→ MIG-03 estado canónico contaminado  OWNERSHIP=PARTIAL
                        ├─→ MIG-04 P0 de HOST-A                 ↓
                        └─→ C2/C3/C4 contradicciones          BLK-01
                                                                  ↓
RC-3 sin-estado-estructurado ─→ MIG-05/07/08/11/15/16            C1=DEFERRED
                                                                  ↓
RC-4 sesgo-del-autor ────→ defectos sobreviven a revisión       A/B → R2 → R3
MIG-09 write_test.py sin gate ──→ superficie de escritura no bloqueada
MIG-12 R1 fuera de git ──────────→ reproducibilidad no garantizada
```

Raíz: RC-1..RC-4. Derivados: el resto. Independientes: MIG-09, MIG-10, MIG-11, MIG-14, MIG-18, MIG-19.

## 6. ARQUITECTURA PROPUESTA (NO IMPLEMENTADA)

| Agente | Función | Regla dura | Enforcement V2 |
|---|---|---|---|
| **EXPLORER** | buscar evidencia, código, historia | solo lectura | `permissions: [{action:"edit",resource:"*",effect:"deny"}]` |
| **EVIDENCE-AUDITOR** | provenance, host identity, contaminación | no puede cerrar un hallazgo | `edit`/`shell` acotados |
| **ROOT-CAUSE-ANALYST** | relaciones causales | `ROOT_CAUSE=CONFIRMED` requiere evidencia citada | `edit: deny` |
| **TECHNICAL-REVIEWER** | revisión independiente | no ve la razonación del autor, solo artefacto + tests | `edit: deny` |
| **SAFETY-REVIEWER** | toda operación privilegiada o de escritura | veto; clasifica cada cmd | `shell: {sudo:"deny", systemctl:"deny"}` |
| **DOCUMENTATION-REVIEWER** | consistencia, trazabilidad | detecta `HYPOTHESIS→FACT` | `edit` acotado a docs |
| **INVESTIGATOR** | coordina | no ejecuta sin SAFETY | delega vía `subagent` |

**Regla de independencia (respuesta a RC-4):** revisores reciben el artefacto y los tests, no
la conversación del autor.

## 7–11. MODELOS

Se develops por separado en `MIG-07-VOCABULARY-MAPPING-20260926.md` (§EVIDENCE_CLASSIFICATION,
FINDING_STATE, ROOT_CAUSE_STATE, GATE_STATE) y en la implementación futura de `STATE/`.

- **EVIDENCE:** `EVIDENCE_ID · RUN_ID · TIMESTAMP · HOST · KERNEL · HARDWARE · TOOL+VERSION · SHA256 · PARAMS · RESULT · CLASSIFICATION · LIMITATION`. Regla dura: dos evidencias de hosts distintos no se mezclan.
- **RCA:** qué ocurrió · dónde · cuándo · evidencia · impacto · causas posibles · causa raíz · evidencia que la confirma · corrección · **verificación por otro** · estado.
- **DOCUMENTACIÓN:** `EVIDENCE → ANALYSIS → STATE → DOCUMENTATION`, una sola dirección.
- **STATE:** YAML en `STATE/PROJECT-STATE.yaml` (propuesto, **no creado**), fuente única de verdad; los `.md` canónicos pasan a Derivados.
- **GATES:** `BLOCK` si hay blocker `OPEN`/`INVESTIGATING`, `ROOT_CAUSE=UNKNOWN` necesaria, evidencia contaminada, contradicción sin resolver, verificación pendiente o no independiente, dependencia abierta, identidad no demostrada o provenance insuficiente. **Gate por rama, con `SCOPE:` y `BLOCKS:` explícitos** — no bloquear todo el proyecto por una rama.

## 12–13. MIGRACIONES PROPUESTAS (NO EJECUTADAS)

**`AGENTS.md`:** conservar las 15 reglas de routing, la regla de no-asumir-host-equivalente,
`§Ownership`, `§HDD/Btrfs`, `§Recovery` y la prohibición de sudo/C1. Añadir: `§GATES`,
`§EVIDENCE-PROVENANCE`, la regla de **verificación independiente obligatoria**, y la regla de
no resolver contradicciones por conveniencia. Sustituir el bloque «Current project state» —
que hoy afirma valores derivados de otro host — por una referencia a `STATE/PROJECT-STATE.yaml`.

**`.opencode/agents/`:** no existe; hay que **crearlo**. 7 ficheros markdown con frontmatter.
Permisos reducidos como enforcement real (no como prosa).

## 14. PLAN DE IMPLEMENTACIÓN

1. **MIG-07** (vocabularios) — bloquea todo lo demás.
2. **MIG-14** — `ROOT_CAUSE=UNKNOWN`, solo investigación.
3. **MIG-01** + test que ejecute el barrido. Prerrequisito: RC-1.
4. **MIG-02** como gate permanente.
5. **MIG-03/04** — reconciliar contra HOST-C sin sobrescribir.
6. Crear `STATE/PROJECT-STATE.yaml`; migrar canónicos a Derivados.
7. **MIG-09** — gate sobre `write_test.py`.
8. **MIG-12** — commit de la cadena R1, con autorización explícita.
9. Solo entonces `.opencode/agents/` y R1.

## 15. RIESGOS

| Riesgo | Sev | Mitigación |
|---|---|---|
| El `STATE` se vuelve otro documento que nadie actualiza | ALTO | `DOCUMENTATION-REVIEWER` valida frescura |
| Gates fragmentados dejan pasar lo que debe bloquear | ALTO | cada gate declara `BLOCKS:`; SAFETY con veto |
| Verificación independiente más lenta | MEDIO | revisores sobre artefacto, no conversación |
| Renormalizar vocabulario rompe el router y 1577 filas | MEDIO | migración aditiva + mapa de equivalencia |
| Perder historial al consolidar | ALTO | nunca sobrescribir; canónicos se marcan Derivados |
| Construir agentes antes de resolver RC-1 | MEDIO | orden del plan |

## 16. VERIFICACIÓN

1. **MIG-01 reintroducido a propósito** → el gate bloquea y ningún test da verde sin ejecutar el barrido.
2. **MIG-03 reintroducido** → `EVIDENCE-AUDITOR` lo detecta sin que se le diga.
3. `ROOT_CAUSE=HYPOTHESIS` → `ROOT-CAUSE-ANALYST` no puede cerrarlo.
4. `sudo` en un plan → `SAFETY-REVIEWER` lo veta.
5. Contradicción de vocabulario → `DOCUMENTATION-REVIEWER` la marca `CONFLICT`.
6. **MIG-14** → reporta `REQUIRES_VERIFICATION`, no improvisa.

## 17. NO TOCAR

`R1-20260926T000649Z.json` · `R1-EXECUTION-RECORD-20260926T000649Z.md` ·
`R1-20260926T005434Z.json` · registros DEFECT-01/02 · `R1-COLLECTOR-INDEPENDENT-REVIEW*.md` ·
`DOCUMENTATION-INVENTORY.tsv` congelado · `ROUTING-LOG.jsonl` · `05-FUENTES-EXTERNAS/` ·
`03-EXPERIMENTOS/` · `AGENTS.md §Ownership` y `§Safety` · todo commit/índice/worktree ·
las 2 capturas FINAL-VALIDATION (HOST-B y HOST-C) · `RX550_Modo_Torneo_Backup_*/` y
`RX550-INVESTIGACION-NOTEBOOKLM/` (**fuera del repo**).

---

```
MIGRATION_AUDIT=COMPLETE
IMPLEMENTATION=NOT_EXECUTED
OPEN_BLOCKERS=20
ROOT_CAUSES_CONFIRMED=4
ROOT_CAUSES_UNKNOWN=2
PROPOSED_AGENTS=INVESTIGATOR,EXPLORER,EVIDENCE-AUDITOR,ROOT-CAUSE-ANALYST,TECHNICAL-REVIEWER,SAFETY-REVIEWER,DOCUMENTATION-REVIEWER
NEXT_ACTION=MIG-07
```
