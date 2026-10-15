# RXRE-008 FINDING 1605 — Time-series mmGRBM_STATUS 0x00003028 (idle sostenido)

## Provenance
- Fecha: 2026-10-14
- Autor: Sistema Autónomo RXRE (RXRE-008)
- Número de hallazgo: 1605
- Estado: PROVEN (layout, §1604) / OBSERVED (estabilidad, 10 samples)
- Hardware: AMD Radeon RX 550 (1002:699f, Polaris12), PCI 0000:01:00.0. iGPU 0000:00:02.0 NO tocada.
- Kernel/Software: Nobara/Fedora, umr 1.0.0 (build Jan 17 2026), regdb /usr/share/umr/database/ip/gfx_8_0_0.reg
- Tool provenance: 10× `op:run gpu.register_read decode=True` (internamente `umr -O bits -r`), 1 s de separación, RXRE_DB=/tmp/rxre_ts.sqlite3 (durable, root, aislada).
- Relación: extiende §1604 (snapshot único) → estabilidad sobre 10 samples (idle).

## Resumen
Diez lecturas read-only consecutivas de `mmGRBM_STATUS` (0x3028) bajo idle producen
**10/10 = `0x00003028`**, con los campos estables (`GUI_ACTIVE=0`, `DB/CB_CLEAN=1`,
`ME0PIPE0_CMDFIFO_AVAIL=8`, `SRBM_RQ_PENDING=1` en cada lectura). La limitación de §1604
("snapshot único") se relaja: **el snapshot 0x3028 es estable (no efímero) bajo idle**.
La estabilidad es OBSERVED (10 muestras, idle); el layout sigue PROVEN (§1604, regdb oracle).
NO se probó el estado bajo carga (frontera de workload pendiente — requiere submit; display
prohibido → compute no-display solo si se autoriza).

## Contexto
§1604 declaró HYPOTHESIS la semántica del snapshot (1 sample). Este finding lo promueve a
OBSERVED sobre 10 samples (idle), pero NO a PROVEN de "estado bajo carga". La regla §9 se
mantiene: estabilidad observada ≠ comportamiento bajo carga probado.

## Evidencia técnica
### Serie temporal (10 samples, 1 s apart, idle, read-only)
| sample | value | SRBM_RQ_PENDING[5] | GUI_ACTIVE[31] | DB_CLEAN[12] | CB_CLEAN[13] | CMD_AVAIL[0:3] | n_fields |
|---|---|---|---|---|---|---|---|
| 1 | 0x00003028 | 1 | 0 | 1 | 1 | 8 | 24 |
| 2 | 0x00003028 | 1 | 0 | 1 | 1 | 8 | 24 |
| 3 | 0x00003028 | 1 | 0 | 1 | 1 | 8 | 24 |
| 4 | 0x00003028 | 1 | 0 | 1 | 1 | 8 | 24 |
| 5 | 0x00003028 | 1 | 0 | 1 | 1 | 8 | 24 |
| 6 | 0x00003028 | 1 | 0 | 1 | 1 | 8 | 24 |
| 7 | 0x00003028 | 1 | 0 | 1 | 1 | 8 | 24 |
| 8 | 0x00003028 | 1 | 0 | 1 | 1 | 8 | 24 |
| 9 | 0x00003028 | 1 | 0 | 1 | 1 | 8 | 24 |
| 10| 0x00003028 | 1 | 0 | 1 | 1 | 8 | 24 |

- `distinct_values: ['0x00003028']` → 10/10 idéntico (idle sostenido).
- `SRBM_RQ_PENDING[5]=1` en cada sample → refleja el lector MMIO activo POR cada `-r` (no busy GPU real; es el propio reader).
- `GUI_ACTIVE[31]=0` en los 10 → sin actividad GUI/CP.
- `DB/CB_CLEAN=1` en los 10 → bloques limpios.
- `CMD_AVAIL=8` en los 10 → CMDFIFO 8/8 disponible (idle).
- `n_fields=24` determinista → layout estable (§1604 PROVEN).

### Nota de interpretación (§46 ORACLE / §9 EPISTEMIC KERNEL)
Un script de análisis adicional reportó `srqm ... 0/10`, `gui ... False`, etc. — **bug de
comparación string-vs-int** (los valores vienen como int 1/0; la comparación `== "1"` falló).
La tabla de arriba es la evidencia autoritativa (impresa directamente del bitfield). La
regla §46 aplica: el efecto observable (tabla) sobrevalora la salida de análisis con bug.

## Decisiones
- D5 (RXRE-008): el snapshot 0x3028 es estable bajo idle (10/10) → la limitación de §1604
  ("snapshot único") se relaja a "10 samples, idle". La semántica de idle está OBSERVED.
- D6 (RXRE-008): el tool RXRE persiste results con result_id DETERMINISTA
  (hash del input) y sin timestamp → lecturas idénticas COLISION (1 result_id
  `res_gpu_register_1f1b38e5c6d4`, deduplicado). El time-series se captura a nivel de
  SCRIPT (no como rows distintos en results). Esto LIMITA la observabilidad temporal
  del tool-level store.
- D7 (RXRE-008): NO se programa salida de display de la RX550 (frontera dura; fb0/i915 = Intel).

## Verificación
- 10/10 samples = 0x00003028 (idle sostenido). ✓ (discrimina H1: snapshot efímero → REFUTADA; idle es estable).
- Campos coherentes y estables en los 10 samples. ✓
- n_fields=24 (layout PROVEN §1604). ✓
- DB tool: /tmp/rxre_ts.sqlite3 (303 KB), result_id deduplicado `res_gpu_register_1f1b38e5c6d4`. ✓
- iGPU 0000:00:02.0 intacta (read-only sobre 0000:01:00.0). ✓

## Limitaciones
- Idle only: NO se probó el estado bajo carga (GPU_BUSY, actividad de shader/CP/SDMA).
  La estabilidad bajo idle no implica estabilidad bajo carga.
- D6 (tool no timestampa / result_id determinista) → el time-series es captura externa de
  script, no rows queryables con timestamp en results. La observabilidad temporal del
  tool-level store es LIMITADA.
- Layout válido para Polaris12/GFX8 (§1604); no generalizado.

## Próximos pasos (§58 GLOBAL WORK SCAN)
- 1606 (frontera): estudiar mmGRBM_STATUS BAJO CARGA (compute workload no-display sobre la
  RX550 vía amdgpu, SOLO si se autoriza explícitamente; iGPU nunca). Discrimina
  H1(estado carga coherente) vs H2(no se refleja en GRBM_STATUS). → gating: display prohibido.
- Escalar time-series a mmGRBM_STATUS2, mmGRBM_STATUS_SE[0..3] (más campos de idle/carga).
- (Fase E) Revisar herramienta de time-series formal: timestamp + result_ids distintos por
  sample (feature gap en rxre store: §1605-D6).

<signed> Sistema Autónomo RXRE — RXRE-008 (single active agent; iGPU 0000:00:02.0 untouched; GPU 0000:01:00.0 read-only probes only)
