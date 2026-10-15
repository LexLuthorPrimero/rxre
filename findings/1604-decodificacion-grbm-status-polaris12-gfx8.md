# RXRE-008 FINDING 1604 — Decodificación mmGRBM_STATUS 0x00003028 en Polaris12/GFX8

## Provenance
- Fecha: 2026-10-14
- Autor: Sistema Autónomo RXRE (RXRE-008)
- Número de hallazgo: 1604
- Estado: PROVEN (layout) / HYPOTHESIS (semántica de snapshot)
- Hardware: AMD Radeon RX 550 (1002:699f, Polaris12, rev 0xc7), PCI 0000:01:00.0 — iGPU 0000:00:02.0 NO tocada (fingerprint verificado; fb0=i915drmfb 1366x768 de la Intel).
- Kernel/Software: Nobara/Fedora, umr 1.0.0 (build Jan 17 2026), regdb /usr/share/umr/database/ip/gfx_8_0_0.reg
- Tool provenance: `umr -dbp /usr/share/umr/database -O bits -g =0000:01:00.0 -r polaris12.gfx800.mmGRBM_STATUS`
- Suministro de evidencia: tools/rxre (op:run capability=gpu.register_read, decode=True) → result_id `res_gpu_register_1f1b38e5c6d4` (determinista), valor `0x00003028` (decimal 12328).
- RXRE finding (persistencia tool-level): finding_id `finding_17c893ed2affd34c`, epistemic graduado `PROVEN` (honesto: la evidencia op.status==ok sostiene PROVEN; ver §EPISTEMIC), DB durable `/tmp/rxre_decode_finding.sqlite3` (303 KB), idempotente/COLISION (mismo claim+evidence → mismo finding_id).

## Resumen
`mmGRBM_STATUS` (offset 0x3028, Gráficamente GRBM Status, Polaris12/GFX8) se descompone
en 24 bitfields mediante `umr -O bits` contra el regdb `ip/gfx_8_0_0.reg`, y el layout
coincide exactamente con el decode manual (oracle). El snapshot observado `0x00003028`
es consistente con GPU idle, pero la interpretación semántica de los campos (idle sostenido)
es **hipótesis** hasta validar con múltiples samples — la regla epistemica (§9) aplica: layout
PROVEN no implica estado PROVEN.

## Contexto
Enero 2026, el snapshot 0x3028 se obtuvo una sola vez (raw). La variante `raw-only` fue
insuficiente: el layout solo se obtiene con `umr -O bits` + regdb, y la semántica de "idle"
requiere validación cruzada (múltiples samples + discriminantes). Se implementó el flag
`decode: bool = False` (backward compatible) en `umr_read.py` `register_read(..., decode=False)`
con adapter literal `-O bits`, read-only; se ató a `op:run gpu.register_read` vía
`dispatch.py` ADAPTERS parametros `+= "decode"`. La capa de decisiones RXRE (AGUA) se
verificó: una lección de fallo (`reflect`) para `gpu.register_read` influye en `op:plan`
para esa capability (agrega `warning` + `reflexiones_previas` + estrategia), y no para
una capability sin lección (control).

### EPISTEMIC (graded, no declarado)
Regla aplicada (`_reclamar_estado_epistemico`): un claim `epistemic="PROVEN"` se gradúa
PROVEN sólo si la evidencia tiene `op.status==ok`. Evidencia: `res_gpu_register_1f1b38e5c6d4`,
`op.status=ok` → el claim PROVEN se mantiene (no es un label lie). Sin embargo, el **claim**
afirmaba el *layout*; la interpretación de *idle* del snapshot es HYPOTHESIS (1 sample).
Se separa explícitamente: layout = PROVEN (regdb oracle); semántica del snapshot = HYPOTHESIS.

### EVIDENCE → FINDING (cadena causal verificada)
EVIDENCE `res_gpu_register_1f1b38e5c6d4` (umr -O bits, 24 fields, 0x3028) → CLAIM (layout
Polaris12/GFX8 + campos oracle) → rz_findings.create_finding (evidence_ids, PROVEN,
target=operation.target, provenance, limitations) → finding_id `finding_17c893ed2affd34c`
(persistido=True) → op:explain reconstruye result→operation→backend → op:list_findings
(`hallazgos`) devuelve el finding, evidence-linked, con created_at.

## Evidencia técnica
### Lectura raw (umr -O bits, read-only)
- offset: 0x3028 (`mmGRBM_STATUS`).
- value_hex: `0x00003028` (decimal 12328). Tres runs consistentes (determinismo).
- decoded: True; bitfields: **24** (umr -O bits + regdb `ip/gfx_8_0_0.reg`), oracle-match=True.

### Bitfields decodificados (layout PROVEN — match regdb + decode manual)
| Campo | [bits] | 0x3028 | Significado (hipótesis, §9) |
|---|---|---|---|
| GUI_ACTIVE | [31:31] | 0 | GPU idle (no actividad GUI). |
| SRBM_RQ_PENDING | [5:5] | 1 | Lector MMIO activo (ESTA lectura). |
| DB_CLEAN | [12:12] | 1 | Depth Block limpio. |
| CB_CLEAN | [13:13] | 1 | Color Block limpio. |
| ME0PIPE0_CMDFIFO_AVAIL | [3:0] | 8 | Command FIFO 8/8 disponible. |
| (resto BUSY) | var | 0 | Sin bloques busy. |

### AGUA (influencia demostrable, 5/5) — op:reflect → op:plan
- `op:reflect gpu.register_read` (outcome=failure, strategy="usar decode=True; 0x3028 snapshot idle; no confiar en un solo sample", check=tools/rxre/tests/test_umr_decode003.py) registra la lección.
- `op:plan gpu.register_read` → `warning`="Revisar antes de ejecutar" + `reflexiones_previas`[0].strategy="usar decode=True..." (INFLUIR ✓).
- `op:plan binary.inspect` (control) → sin `warning`, sin `reflexiones_previas` (CONTROL ✓).
- Veredicto AGUA: la lección viaja hasta el plan y modifica la decisión (no solo se expone). test_agua_plan008.py lo formaliza (lock-in repo, stagiado).

### ETER (ciclo causal integrado, 12/12)
1. OBSERVAR: decode → 24 bitfields; value=0x00003028; result_id determinista; campos oracle.
2. APRENDER: op:reflect registra la lección.
3. INFLUIR: op:plan gpu.register_read agrega warning.
4. CONTROL: op:plan binary.inspect no agrega warning.
5. PERSIST: create_finding → finding_17c893ed2affd34c, PROVEN, persistido=True (target corregido =operation.target).
6. EPISTEMIC: PROVEN reclamado → grado honesto PROVEN (evidencia op.status=ok).
7. VERIFICAR: op:explain reconstruye provenance (result+operation+backend+raw).
8. INTEGRAR: op:list_findings (`hallazgos`) → 1 finding, evidence-linked, created_at.

## Decisiones
- D1 (RXRE-008): agregar `decode: bool = False` a `umr_read.register_read` + adapter literal `-O bits` (read-only). Rationale: el layout (24 fields incl. GUI_ACTIVE/SRBM_RQ_PENDING/DB/CB_CLEAN/CMD_AVAIL) es autoridad regdb; sin decode se mantiene backward-compat. Verificado 9/9 (`test_umr_decode003.py`: decode=True→24 fields, decode=False→`{}`, iGPU 0000:00:02.0 rechazado).
- D2 (RXRE-008): el `findings` de RXRE persiste en rxre.sqlite3 (`rz_findings.create_finding`), NO en el árbol `findings/` del directorio madre → se usa la capa tool (`op:run rxre.create_finding` / `op:explain` / `op:list_findings`).
- D3 (RXRE-008): epistemic se GRADUA (no se declara) — PROVEN requiere evidencia op.status=ok; layout PROVEN, semántica de snapshot HYPOTHESIS.
- D4 (RXRE-008): `target` del finding == `target` de la operación de evidencia (`gpu:0000:01:00.0:polaris12.gfx800.mmGRBM_STATUS`); el primer intento falló por target-mismatch (payload truncado) → corregido.

## Verificación
- Oracle layout: `umr -O bits` (24 fields) ≡ regdb `ip/gfx_8_0_0.reg` ≡ decode manual. ✓
- Regresión: run_baseline 13/13 green (test_dispatch004 132 checks) — sin regresión de D1. ✓
- AGUA: reflect→plan gpu agrega warning + strategy; control no (5/5). ✓
- ETER: 12/12 (OBSERVAR/APRENDER/INFLUIR/CONTROL/PERSIST/EPISTEMIC/VERIFICAR/INTEGRAR). ✓
- Reproducibilidad: create_finding idempotiente/COLISION (mismo claim+evidence → finding_17c893ed2affd34c). ✓
- DB tool: `/tmp/rxre_decode_finding.sqlite3` (303 KB, root, aislada, no live rxre.sqlite3). ✓

## Limitaciones
- Snapshot único (0x30228) → NO prueba estado sostenido; SRBM_RQ_PENDING[5]=1 refleja ESTA lectura (no busy real).
- Layout válido para Polaris12/GFX8 (`ip/gfx_8_0_0.reg`); no generalizado a otros ASIC (§5 NO PORTABILITY BY DEFAULT).
- nextnum.py del directorio madre NO está presente en tools/rxre/ → la numeración de findings/ tool-level es manual (colisión con sesión concurrente monitoreada); rxre.sqlite3 es la fuente de verdad del finding.
- No se programó salida de display de la RX550 (frontera dura: prohibido hasta permiso explícito; fb0/i915/intel DRM exclusivamente Intel).

## Próximos pasos (§58 GLOBAL WORK SCAN)
- 1605: time-series read-only de mmGRBM_STATUS (umr -O bits -r, N muestras bajo idle) para validar estabilidad del snapshot 0x30028 → discriminar H1(idle sostenido) vs H2(snapshot efímero). (Contraind: read-only; no display; no GPU write.)
- Escalar el ETER cycle a más registros (mmGRBM_STATUS2, mmGRBM_STATUS_SEx) + SDMA/CP state para reconstruir más transiciones (§17).
- (Fase E) consolidar test_umr_decode003.py + test_agua_plan008.py; revisar README L139 staleness + machine.py docstring L12 (dice 5 ops, reales 10).

<signed> Sistema Autónomo RXRE — RXRE-008 (single active agent; iGPU 0000:00:02.0 untouched; GPU 0000:01:00.0 read-only probes only)
