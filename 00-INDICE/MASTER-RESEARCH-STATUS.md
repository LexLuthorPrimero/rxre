# MASTER-RESEARCH-STATUS.md — Estado Único del Proyecto

> **OVERLAY FINAL 2026-09-25:** la matriz vigente de problemas y el gate de
> publicación están en `../PATCH-REGISTRY-FINAL.md`,
> `../PROBLEM-STATUS-FINAL.md`, `../RELEASE-CANDIDATE.md` y
> `../FINAL-RELEASE-REPORT.md`. La instalación actual fue capturada en
> `../01-AUDITORIA/FINAL-VALIDATION/`. Este archivo conserva el historial
> R-4B/D6 y no debe usarse para declarar una resolución que no aparece en el
> overlay.

**ESTADO VIGENTE D6 (reconciliado 2026-09-24; Addenda D6 original 2026-09-23):** R-4B v2.3 = `S1 EJECUTADA/COMPLETADA` · `S2 INICIADA/PARADA D` antes de Phase 2 · `VEREDICT INCONCLUSO/INCONCLUSIVE`; nunca `SUPPORTED`; no se reintenta S2.

**ESTADO VIGENTE GATE P0 (2026-09-24):** **B. `CONTAMINATED_REQUIRES_ISOLATION`**; la atribución de ownership es `PARTIAL` y no se autoriza un nuevo A/B hasta aislar clientes y agentes automáticos. La fuente primaria es `01-AUDITORIA/FASE-P0-EXPERIMENTAL-VALIDITY-GATE/P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md`.

**SNAPSHOT HISTÓRICO PRE-D6 — NO DESCRIBE EL ESTADO ACTUAL:** 2026-09-23 — **FASE R-4B — EXP-F4-A GOVERNOR READ-ONLY — S1 v2.2 FINALIZADA; PHASE 2 CLASIFICADA `DIAGNOSTIC / THERMALLY CONFOUNDED — NOT FOR VERDICT`; PROPUESTA v2.3 PREPARADA (NO EJECUTADA); MINI-TEST 7.3-B (RAMP CON GOVERNOR) EJECUTADO N=2 (read-only) — RESULTADO: DIST no cabe íntegro desde ≤50 °C (ramp real 0.246–0.252 °C/s; entrada ≤35 °C era una opción histórica no verificada (no se declara viable))**: tras PARADA D de la S1 v2.1 (histéresis 58.3 % por throttling térmico 92 °C/SCLK 551), se caracterizó el problema térmico en investigación read-only (`FASE-R4B-THERMAL-TEST`: ramp 0.31 °C/s, recuperación ≤50 °C en 255–270 s, Kalm NO intervino) y se relanzó la S1 bajo **protocolo v2.2** (única variación documentada formalmente ANTES de ejecutar: cooldown pasivo entre passes p1→p2→p3, condición telemétrica `temp ≤50 °C s30s ∧ SCLK nv0 ∧ W_SMU<4 W`, tiempos reales 180 s/225 s). Resultado: **15/15 bloques con SCLK 1071 MHz sostenido en los 3 passes** (T_max 86 °C, sin degradación), histéresis **0.26 % → GATEs PASS**, **FREEZE T=9.168 ms, s\*=0.75 (sha256 `6b6d6952…`)**, Phase 2 8/8 trials ejecutados. **Clasificación formal Phase 2: `DIAGNOSTIC / THERMALLY CONFOUNDED — NOT FOR VERDICT`** — auditoría de timestamps: contaminación por **temperatura acumulada** (Phase 2 heredó 84 °C de Fase 1 y 91–92 °C entre trials; causa conocida ≥92 °C de N=2, no duración de trial); R1–R7 NO declarados (ni PASS ni FAIL); Fase 1/FREEZE conservados íntegros. **Propuesta v2.3 lista en `EXP-F4-A-PROTOCOL-v2.3-PROPUESTA.md`** (cooldown telemétrico entre cada trial de Phase 2; FIXED/GOV enteros; DIST con 3 opciones 7.3-A/B/C; sin segmentación). **S2 no iniciada en este snapshot pre-D6; la Addenda posterior registra S2 INICIADA/PARADA_D.** Datos en `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/results/session1-v22/` (S1-v2.1 original intacta en `results/session1/`). Antece: FASE R-4C COMPLETADA (jitter TAA, NIVEL A MAE=0.0px, NIVEL B MAE=3.66×10⁻¹⁰px desde matriz host-visible; 8/8 celdas PASS; ANV sin devices → NO EJECUTADO); FASE R-4A COMPLETADA (enlace Gen2×4 VERIFIED por techo del root port 00:01.0, PCIe teórico 2.0 GB/s/sentido DERIVED, VRAM teórica 96–112 GB/s ESTIMATED, ratio enlace/VRAM corregido ×48–80, real UNKNOWN); FASE R-3.1 COMPLETADA (7 fusiones, 0 PROVEN NOVEL, FUSION-04 READY, FUSION-02/05/06 REJECTED, FUSION-07 BLOCKED); FASE R-3 y R-2 COMPLETADAS; R-1/R-0 COMPLETADAS (catálogo GFX8 source-level; GRBM=2/SQ=4 no validan ASIC); programación de contadores y toda escritura SIGUEN NO AUTORIZADAS; este texto conserva el estado del maestro en el snapshot pre-D6 y no describe la reconciliación posterior.
**ESTADO VIGENTE — ADDENDA D6 (2026-09-23):** la corrida R-4B v2.3 posterior al snapshot
histórico de la línea anterior **S1 EJECUTADA/COMPLETADA** (15/15 bloques; 8/8 trials)
y **S2 INICIADA pero PARADA D** durante el cooldown p2→p3, antes de Phase 2. El veredicto
global es **INCONCLUSO / INCONCLUSIVE**, nunca `SUPPORTED`; la causa de interferencia
externa queda como probabilidad documentada, no verificada. La referencia canónica es
`03-EXPERIMENTOS/FASE-R4B-GOVERNOR/EXP-F4-A-RESULTADOS-v2.3.md`, que también lista
los 13 localizadores `/tmp` canónicos como perdidos/no verificables. Las frases
históricas «NO EJECUTADA» o «S2 NO iniciada» que quedan en secciones anteriores se
conservan únicamente como snapshots y no describen el estado posterior a esta addenda.

### Precedencia de estado R-4B

1. `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/EXP-F4-A-RESULTADOS-v2.3.md` y Addenda D6.
2. Esta addenda vigente.
3. Protocolos, propuestas y auditorías pre-run, únicamente como `SNAPSHOT HISTÓRICO`.
4. No se reinterpreta un resultado histórico como estado actual o capacidad actual.

**Umbrales vigentes:** 50 °C fue la condición de entrada/cooldown ejecutada en v2.3; 35 °C pertenece a una opción especial no verificada; 90 °C es un criterio de confound de ventana; 96 °C es un abort configurado, no un límite térmico validado de la placa.

**t90:** no existe un valor universal. Se registra por experimento, workload, cap, temperatura inicial y punto `t0/m0`. `t90≈221 s` es extrapolación lineal histórica, no evidencia operacional.

**Fecha última actualización:** 2026-09-25
**Versión:** 2.19 — reconciliación documental D6 + addenda H12-2 WSI/xdg-shell + addenda ASIC/counters + Gate P0 de validez + reconciliación documental F0/F1/A0/BD/C1/H12-4 + C1 isolation design preparado para review
**Punto único de entrada del proyecto** — No reconstruir el estado leyendo otros archivos.

### ADDENDA DOCUMENTARY RECONCILIATION (2026-09-25)

Fuente primaria: `01-AUDITORIA/DOCUMENTARY-RECONCILIATION-2026-09-25.md`.

- `P0=B__CONTAMINATED_REQUIRES_ISOLATION`; `OWNERSHIP=PARTIAL`; `C1=DEFERRED`; `C1_RUNTIME_VALIDATED=NO`; `C1_READY=NO`.
- F0/F1/A0/BD quedan `VOLATILE_EXTERNAL` con provenance registrada; no son autoritativos automáticamente.
- C1: `24/24=HISTORICAL`, `37/37=DERIVED/STALE`, `44/44=CURRENT_SIDECAR_RECORD`; `C1_TESTS=CONFLICT`; no reejecutado en esta auditoría.
- `H12-4=EXTERNAL_COMPLETED_RECORD_VS_DOC_NOT_EXECUTED`; `H12-4_PROVENANCE=CONFLICT`.
- `MESA_EXTERNAL=26.2.3`; `MESA_CANONICAL=26.2.2`; `MESA_PROVENANCE=CONFLICT`.
- `BTRFS=CONFLICT`; `BTRFS_CAUSE=UNKNOWN`; `REQUIRED=matched_identity_same_window`.
- `PM_EFFECT=UNKNOWN`; `ISOLATION_DESIGN_AT_RECON=DEFERRED`; no se ejecutó C1, tests, runtime, probes ni tuning.

### ADDENDA C1 ISOLATION DESIGN (2026-09-25)

Fuente primaria: `04-IMPLEMENTACION/C1-ISOLATION-DESIGN-v1.0.md`.

- `ISOLATION_DESIGN=PREPARED_FOR_REVIEW`; `DESIGN_ONLY=YES`; `EXECUTION=NONE`.
- Define `OWNERSHIP=FULL`, baseline de contaminantes, prechecks, guard `120s/5s`, GO/NO_GO/ABORT y restore plan.
- `OWNERSHIP_CURRENT=PARTIAL`; `C1=DEFERRED`; `C1_RUNTIME_VALIDATED=NO`; `C1_READY=NO`; `RESTORE_VALIDATED=NO`.
- Gaps conservados: inventario root/client completo, Btrfs, PM, governor, sda activity, agent coverage y restore de cambios no implementados.
- `GAP_REVIEW=COMPLETE`; `IMPLEMENTATION_GAPS_CLOSED=0`; ningún gap se cerró por documentación.
- No se autorizan runtime v2, sudo, systemctl, procesos, tuning, counters ni C1.
- `NEXT=REQUEST_SEPARATE_AUTHORIZATION_BEFORE_IMPLEMENTATION_OR_RUNTIME`.

### ADDENDA H12-2 — WAYLAND/XDG-SHELL/VULKAN WSI (2026-09-24)

Esta addenda es exclusivamente documental y no modifica el veredicto R-4B/D6.
La fuente primaria es
`01-AUDITORIA/FASE-H12-2-WSI-DOCUMENTATION/H12-2-XDG-SHELL-VULKAN-WSI-EVIDENCE.md`.

- H12-2 r3 confirmó target `1002:699f`, Wayland nativo, RADV POLARIS12,
  `640×360`, 3 imágenes, FIFO, queue family 0/una queue, timestamp query
  `PRESENT` (64 bits, período 40 ns) y calibrated timestamps `PRESENT`.
- El XML local exacto es `wayland-protocols` 1.49
  `stable/xdg-shell/xdg-shell.xml`; coincide con el tag oficial y declara
  interfaces v7. El source H12-1 hace bind source-level de `xdg_wm_base` v1;
  la versión global del compositor no está registrada en r3.
- `xdg_toplevel.state=4` queda **CONFIRMED** como `activated` contra la
  versión exacta. No se infiere keyboard/pointer focus, resize, fullscreen,
  maximización ni error.
- El segundo `xdg_surface.configure` serial 12837, observado después del primer
  present, tuvo `640×360` y `states=[4]`. La regla absoluta «configure
  posterior al primer present = conflicto» queda **REFUTED** como regla de
  protocolo; la causa exacta y la continuación runtime siguen `UNKNOWN`.
- Vulkan Wayland WSI confirma que `vkQueuePresentKHR` emite
  `wl_surface.attach`/`damage`/`commit`; `VK_SUBOPTIMAL_KHR` permite decidir
  entre continuar o recrear y `VK_ERROR_OUT_OF_DATE_KHR` obliga a consultar
  capacidades y recrear si se continúa. H12-2 no llegó a probar el siguiente
  present, por lo que la compatibilidad posterior del swapchain es
  `UNKNOWN`.
- La capacidad WSI queda **PARTIALLY CONFIRMED**; la hipótesis causal H12
  (GPU completion vs VSync/WSI) permanece causalmente `UNKNOWN`. No se autoriza
  una nueva ejecución de H12/H12-1 desde esta addenda.
- El source working tree contiene un borrador no ejecutado de
  `POST_PRESENT_STATE_ONLY_CONFIGURE`; no se presenta como resultado de r3 ni
  como autorización de código.

### ADDENDA ASIC/COUNTERS — RECONCILIACIÓN DOCUMENTAL (2026-09-24)

La fuente focalizada y el ranking de valor informacional están en
[`02-ARQUITECTURA/COUNTERS-ASIC-TELEMETRY-KNOWLEDGE-ADDENDUM-2026-09-24.md`](../02-ARQUITECTURA/COUNTERS-ASIC-TELEMETRY-KNOWLEDGE-ADDENDUM-2026-09-24.md).
Esta addenda es documental y no autoriza probes, benchmarks, tuning, programación de
selectores ni escrituras de sistema.

- **Identidad:** `1002:699f`; `device_info` cataloga `GDT_GFX8_0_4`/`gfx804`; Mesa identifica
  `CHIP_POLARIS12`/GFX8. La equivalencia comercial Baffin permanece `UNKNOWN`.
- **Counters:** catálogo GFX8 `SUPPORTED` como referencia; selectores concretos y validación
  física `UNKNOWN`; programación prohibida. El PMU mainline `amdgpu` no registra GFX8/Polaris12
  en los tags inspeccionados: `NOT_AVAILABLE` como PMU confirmado.
- **API:** RADV no anuncia `VK_KHR_performance_query` para GFX8: `NOT_AVAILABLE` como feature
  pública comparada. radeonsi tiene un path GFX8 `SUPPORTED` sólo a nivel source; runtime local
  `UNKNOWN`.
- **Telemetría:** `gpu_busy_percent` y `mem_busy_percent` son proxies SMU `SUPPORTED`;
  `pcie_bw` es estimación/accounting `SUPPORTED`. Ninguno es PMU programable, bandwidth,
  vatímetro o prueba de WSI. UMR es database/debug; GPUPerfAPI/CodeXL son catálogo/histórico;
  RGP actual no demuestra GFX8; Perfetto no demuestra PMU.
- **Corrección trazable:** “UMR+radeontop funcionales” queda como observación/tooling histórico,
  no como validación ASIC; “GPUPerfAPI soporta GFX8” queda limitado a catálogo; GRBM=2/SQ=4
  quedan como entradas de catálogo, no como selectores verificados. Las afirmaciones
  históricas no se borran.

### ADDENDA GATE P0 — VALIDEZ EXPERIMENTAL (2026-09-24)

La fuente primaria del gate READ-ONLY es
[`01-AUDITORIA/FASE-P0-EXPERIMENTAL-VALIDITY-GATE/P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md`](../01-AUDITORIA/FASE-P0-EXPERIMENTAL-VALIDITY-GATE/P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md).
La auditoría se ejecutó entre 07:16:42 y 07:24:55 (-03) sobre kernel
`7.2.6-201.nobara.fc44.x86_64`. El gate no realizó escrituras al sistema, tuning, counters,
benchmark de campaña ni modificación de H12; las escrituras de automaticistas observadas
se registran como interferencia de servicios automáticos.

- **Resultado del gate:** **B. `CONTAMINATED_REQUIRES_ISOLATION`**.
- **Ownership:** `PARTIAL`. Se observaron `Xwayland` sobre `card1` y el proceso GPU de
  `ChatGPT` sobre `renderD129`; `fdinfo` prueba clientes/VRAM/GTT, no trabajo de motor.
  La enumeración de namespaces root fue incompleta.
- **Contaminación de entorno:** `OBSERVED`. `system-autopilot` ejecutó un ciclo cada
  2 min y escribió governor, IRQ39, scheduler/read-ahead y prioridad; `kalm` escribió
  la afinidad de IRQ 42 a CPU1; `irqbalance` y otros autores permanecen activos.
  El cambio a governor `performance` observado durante el gate queda `CONFLICT`
  para una línea base natural porque la propia auditoría pudo elevar `loadavg`.
- **Agentes GPU:** `kalm-gpu` está activo y su código leído tiene capacidad de escribir
  `power1_cap`/DPM; no se observó una escritura actual. `power1_cap=35 W` y
  `power1_input` es `W_SMU`, no vatímetro.
- **Identidad actual:** `0000:01:00.0`, `1002:699f`, revisión PCI `c7`, link observado
  `5.0 GT/s ×4`; el path hipotético `699F:CF` no se aplica a esta identidad. PPTable,
  VBIOS y containment permanecen sin validación física suficiente.
- **CPU/thermal/storage/PM:** no se observó throttling térmico actual; CPU governor y
  frecuencia no forman una línea base estable. El HDD es Samsung HM500JI con Btrfs
  comprimido y hubo presión IO transitoria, posiblemente amplificada por el gate.
  Runtime PM está `auto/active`, con `autosuspend=5000 ms`, `wakeup=disabled` y sin
  D3 explícito; la atribución workload-vs-cliente permanece `UNKNOWN`.
- **Histórico:** M1, FASE B, F2 y E-02/E-03 quedan `REQUIRES_REVIEW` sólo para su
  validez ambiental cuando falta snapshot de clientes/agentes; sus números no se borran
  ni se reinterpretan. R-4B conserva `INCONCLUSIVE`.
- **Siguiente decisión:** diseñar y, sólo con autorización, ejecutar un protocolo de
  aislamiento de clientes/autores antes de cualquier A/B. Counters GFX8 permanecen
  congelados en P3; no son el siguiente bloque.

### Relación vigente y siguiente decisión

`GPU/ASIC → source/catalog → API exposure → runtime capability → physical counter validation
→ telemetry → workload phase → bottleneck → optimization decision`

El gate P0 ya fue ejecutado, pero su resultado no autoriza Tuning. La siguiente rama es
la caracterización de aislamiento y reproducibilidad; sólo después de un entorno
verificado podrá decidirse entre CPU/GPU/WSI, cap/DPM, VRAM/GTT o PCI/containment.
Counters GFX8 quedan P3 y no son el siguiente bloque automático.

### Áreas temporalmente congelables

Mesa/ACO/DCC/FMASK, async compute/ACE, ReBAR/ASPM, MCLK forzado, cap/PM writes y la rama
GFX8 counters pueden permanecer congeladas hasta que el gate de atribución o una pregunta
de decisión concreta demuestre que su `UNKNOWN` puede cambiar una decisión material.
Esto no elimina los `UNKNOWN`; evita investigar ramas que todavía no pueden cambiar el
siguiente paso.

---

## 🟢 QUÉ SABEMOS (VERIFICADO / REPRODUCIBLE)

### Hardware / Sistema
- **RX 550** = Polaris12/GFX8, PCI `1002:699f`, amdgpu, card1. Display en Intel HD 4600 (card0).
- **power1_cap** = 35,000,000 µW (35 W) — valor actual, nunca escrito en sesión actual salvo restore EP-06.
- **DPM** = `auto`. SCLK nivel 7 = 1071 MHz (máximo DPM). MCLK nivel 2 = 1500 MHz (máximo DPM).
- **Mesa** = 26.2.2 (system). CUSTOM `/opt/mesa-26.2.2-rx550-haswell` existe pero NO usado salvo EP-05.
- **Kalm (snapshot histórico 2026-09-23):** se registró entonces `kalmd.py`/`kalm-lite.py`; el gate P0 actual observa `kalm.service`, `kalm-lite.service` y `kalm-gpu.service` activos. La afirmación histórica «kalm-gpu muerto» queda reemplazada sólo para el estado actual; la evidencia histórica se conserva.

### Experimentos y Resultados
| Experimento | Estado | Hallazgo Clave |
|---|---|---|
| **FASE B — cap-probe (histórica)** | **VERIFICADO** | Cap 25W NO liga SCLK (1071 MHz libre incluso a 71°C) |
| **EP-06 (soak + réplica)** | **VERIFICADO** | Régimen E1/E3 NO reproducible ni frío ni caliente; `W_SMU` máxima observada 13.6 W |
| **EP-05 (Mesa CUSTOM A/B)** | **VERIFICADO** | CUSTOM = STOCK para 3 escenas; no reproduce E5 |
| **EP-08 (auditoría E1/E3)** | **VERIFICADO** | E1/E3 midieron RX 550 real (amdgpu card1), NO iGPU |
| **M1 (vkmark 35/30W)** | **VERIFICADO** | `W_SMU` 12.27 W @35W → NO DISCRIMINATIVO; ΔFPS=0, ΔSCLK=0, IC95% ΔPwr (-0.103, +0.060) |
| **E-03 Corregida (Diseño B)** | **VERIFICADO** | `W_SMU` 13.4 W full / 15.75 W steady; MCLK 1500 activo (220/277); 0 faults |
| **ES-01 (Escalado A-D+E)** | **VERIFICADO** | A/B/C/D/E = SIN EFECTO `W_SMU`; auto-pacing fetch-bound |
| **F2 (8 fetches)** | **VERIFICADO** | 2× fetches = 2× frametime (112→222 ms), `W_SMU` invariante (15.76 vs 16.13 W) |
| **R-14 Superposition** | **OBSERVADO/CORRELACIONAL** | `W_SMU` 22.31 W steady / 24.71 W pico; score 804; OpenGL; diferencia correlacionada, no causalidad aislada |
| **FASE D etapa 1 (auditoría counters)** | **VERIFICADO** (procedimiento; no valida counters ASIC) | La operación/lectura histórica de UMR/radeontop no prueba selectores GFX8; el catálogo A/B/C/D permanece `SUPPORTED` sólo como referencia; SPM no es necesario para el diseño mínimo, pero aplicabilidad local sigue `UNKNOWN`; PMU mainline GFX8 no confirmado (`NOT_AVAILABLE` como PMU) |
| **FASE D etapa 2 (contraste A/B×3)** | **VERIFICADO + AUDITADO (v1.4)** | 6/6 runs válidos; A=`W_SMU` 22.25 W steady (score 804 replicado) vs B=15.78 W (fps 8.950 replicado); ratio 1.41; vgt/pa/sh y sx correlacionan; la diferencia orienta una hipótesis de geometría/vertex/export, sin causalidad aislada; `mem_busy` B>A (36 vs 25), sin inferir DRAM como causa; SPI_CSQ=0 en 8408 lecturas (no probatorio read-only); RLC ~25 MHz cte. Auditoría `FASE-D-ETAPA-2-AUDIT.md`: 2 errores objetivos en informe (tabla radeontop §4 mezcla métodos; conteo SPI 3306→8408) — conclusiones centrales intactas |

> **Nota de nomenclatura (FASE B):** la letra `FASE B` tiene **dos usos históricos distintos** en este proyecto, ambos conservados literalmente y sin renombrar sus documentos originales:
> 1. **FASE B — cap-probe (histórica)** → `03-EXPERIMENTOS/fase-b-cap-probe-20260919-122038/` (`RESULTADOS-FASE-B.md`): probe de power cap 25/28/32/35 W (19/09).
> 2. **FASE B — POLARIS12-MAP (histórica)** → `02-ARQUITECTURA/POLARIS12-MAP/` (`POLARIS12-MAP.md`): mapa de subsistemas A–AJ (09/20–21).
> Pertenecen a **líneas históricas distintas**; no constituyen una única secuencia lineal. La nomenclatura posterior (`FASE C` → R-14, `FASE D` → counters) NO debe interpretarse como continuación lineal de ninguna de las dos.

### Cuellos de Botella Identificados
- **Todos los workloads sintéticos Vulkan:** evidencia consistente con **fetch-latency bound**
  (auto-pacing). SCLK 1071 fijo, MCLK 1500, `mem_busy` 36% steady. Más fetches/frame
  → menos fps → `W_SMU` similar; no es causalidad física demostrada.
- **ALU (FMA) y CB (MSAA):** no cambiaron `W_SMU`/frametime en los runs probados; no
  prueba que no sean cuellos en todos los regimes.
- **Superposition (OpenGL, geometría):** muestra una asociación distinta:
  `W_SMU` 22.31 W steady / 24.71 W pico; `mem_busy` 24.6 % (vs 35.9 % sintéticos);
  VRAM 1.55 GB vs 0.23 GB; OpenGL/radeonsi vs Vulkan/RADV. La causa sigue abierta.
- **FASE D etapa 2 (2026-09-21):** la diferencia `W_SMU` **+6.5 W steady (A 22.25 vs
  B 15.78 W, ratio 1.41)** se correlaciona direccionalmente con señales de geometría/
  vertex/export; no identifica un subsistema causal. `mem_busy` no permite inferir tráfico
  DRAM como motor. SPI_CSQ_WF_ACTIVE_COUNT = 0 read-only → no informativo sin programación.

### Infraestructura rx550-torneo
- **Fase 1:** 65/65 checks OK (detección, separación Intel/RX550, state_manager, failsafe).
- **Fase 2:** 55/55 checks OK (write-test controlado power/control, rollback verificado).
- **Fase 3:** 56/56 checks OK (perfiles balanced/locked/25W/experimental con `--danger`).
- **M1:** 112/112 checks OK (10 runs pareados, hashes sha256 inmutables).
- **Benchmarks:** el inventario separa descargas dentro del repo, instalaciones externas
  observadas (no certificadas por el repo), ejecuciones históricas y elegibilidad M2.
  GravityMark y Superposition tienen resultados históricos; no se autoriza repetirlos.

---

## 🔴 QUÉ FUE INVALIDADO (con ERRATUM en `01-AUDITORIA/AUDIT-001/ERRATA.md`)

| Conclusión Anterior | ERRATUM | Nueva Clasificación |
|---|---|---|
| "Kalm limitó a 25W" | 001 | **INVALIDADO** — Régimen 25W ocurrió SIN kalm (17/09) |
| "Cap 25W liga SCLK" | 001 | **INVALIDADO** — Fase B + EP-06: cap 25W no liga SCLK |
| "25W = techo natural GPU" | 001 | **INVALIDADO** — power1_input era estimador SMU en estado regulatorio |
| "power1_input = potencia real" | 002 | **INVALIDADO** — Es estimador SMU; W_SMU máx 13.6 W (EP-06), 23.7 W pico (Superposition) |
| "Mesa CUSTOM causó E5" | 003 | **INVALIDADO** — EP-05 A/B: CUSTOM = STOCK; no reproduce E5 |
| "E1/E3 midieron iGPU" | 005 | **REFUTADO** — EP-08: telemetría = RX 550 (mem_info_* solo en amdgpu) |
| "13.40 W ≈ 15.75 W comparables" | 004 | **INVALIDADO** — Definiciones distintas (ventana completa vs régimen estable) |

---

## 🟡 NO REPRODUCIBLE (Histórico, NO es especificación operacional)

- **Régimen E1/E3/E5 completo (17/09/2026):** power1≈25W / SCLK 350-390 / MCLK 1250-1500 / 74-92°C / phong 1285 fps / desktop 443@1080 / jelly 691@35W.
  - Ningún parámetro autorizado (cap, calor, kalm, Mesa stock o CUSTOM) lo reprodujo.
  - Causa raíz = **DESCONOCIDA** sin autorización nueva.

---

## 🟠 HIPÓTESIS (Candidatas sin confirmar)

| Hipótesis | Evidencia Parcial | Estado |
|---|---|---|
| **Auto-pacing GPU / Fetch-latency bound** | ES-01 + F2: frametime ∝ fetches, power/mem_busy invariantes | **SUSTENTADA** por ES-01 + F2 |
| **Clock-gating anula trabajo extra** | Whitepaper Polaris "fine grained clock gating" + ES-01/F2 power invariante | **COHERENTE** |
| **MCLK 1500 requiere presión memoria real** | Superposition (MCLK 300-1500) vs sintético (MCLK 1500 solo con 4× tex 4096²) | **PARCIAL** |
| **Régimen 17/09 = estado térmico previo + MCLK push** | EP-06: soak 71°C + cap 25W no reproduce; `W_SMU` máxima observada hoy 13.6W | **CANDIDATA** |

---

## ⚫ DESCONOCIDO (Gaps Críticos)

| Gap | Descripción | Prioridad |
|---|---|---|
| **Causa raíz régimen 17/09** | Qué disparó SCLK 350 / MCLK 1250 / 25W en sesión 17/09 | **ALTA** |
| **MCLK sostenido 1250-1500** | Qué lo dispara (hoy solo 625 + picos transitorios) | **ALTA** |
| **W_SMU máximo observado** | Límite térmico/eléctrico real (>13.6 W medidos EP-06; 23.7 W pico Superposition) | **ALTA** |
| **Costo real DRAM / mem_busy** | `mem_busy` ≠ % bandwidth; necesidad contadores HW reales | **ALTA** |
| **Bottleneck GL 640p** | CPU submissions vs present vs VRAM/GTT | **MEDIA** |
| **DCC behavior real** | ¿Superposition usa DCC? ¿Nuestro CB lo deshabilita? | **MEDIA** |
| **PowerPlay internals** | ppfeaturemask, DPM niveles intermedios, voltage behavior | **MEDIA** |
| **Origen "phong 1285 fps"** | ¿Era otra ventana/superficie? | **BAJA** |
| **PCIe x8 vs x4** | Link width/speed negociado real | **BAJA** |
| **BIOS/fuses CUs** | Unidades deshabilitadas: fuse/BIOS/físico | **BAJA** |

---

## 🔵 EXPERIMENTOS AUTORIZADOS (Próximos Pasos)

| Fase | Objetivo | Estado |
|---|---|---|
| **FASE B — POLARIS12-MAP (histórica)** — `02-ARQUITECTURA/POLARIS12-MAP/` | Mapa completo subsistemas A–AJ (hardware/software/capacidades) | **COMPLETADA** |
| **FASE C** — `R-14-SUPERPOSITION-DISSECTION.md` | Dissección Superposition (22.31 W steady, 24.7 W pico, score 804) | **COMPLETADA** |
| **FASE D** — Performance Counters | Etapa 1 (auditoría read-only) **COMPLETADA**. Etapa 2 (contraste pareado A/B×3) **COMPLETADA** → informe `FASE-D-COUNTERS-AUDIT/FASE-D-ETAPA-2-RESULTADOS.md`; H1 APOYADA, H4 parcial, H8 gating descartado. Etapa 3 (contadores programados + SPM) **DISEÑADA** (`FASE-D-ETAPA-3-PLAN.md`), **PRECHECK completado** (`FASE-D-ETAPA-3-PRECHECK.md`), **etapa 3: eventos investigados** (`FASE-D-ETAPA-3-EVENTS.md`) y **Auditoría de Event IDs GFX8 completada** (`FASE-D-GFX8-EVENT-ID-AUDIT.md`); programación permanece NO autorizada. | **EN CURSO** |
| **FASE E** — Real-Game Baseline | Juego reproducible, offline, ≥30s, RX 550 explícita, misma telemetría | **PENDIENTE** |
| **FASE F** — Geometry Investigation | Documentar candidatos GEO-01..08, seleccionar mayor valor informativo | **PENDIENTE** |
| **FASE G** — Memory/VRAM/GTT | Modelo tráfico memoria + comparación contadores/sysfs | **PENDIENTE** |
| **FASE H** — RADV/Workarounds | Investigar individualmente (shrink_image_store, wait_for_vm_map, etc.) | **PENDIENTE** |
| **FASE I** — PowerPlay/DPM | pp_power_profile_mode, ppfeaturemask (0xfff7bfff), DPM intermedios | **PENDIENTE** |
| **FASE J** — Priority Matrix | `EXPERIMENT-PRIORITY-MATRIX.md` con justificación por evidencia | **PENDIENTE** |
| **FASE K** — POLARIS12 Performance Laboratory | Roadmap post-FASE D (PLANIFICADA): framework reproducible de caracterización/experimentación (estructura común, telemetría unificada, benchmarks A/B reproducibles, clasificación de bottlenecks con niveles de evidencia, experimentos SHD/FRAG/GEO/MEM, analizador K8 solo planificado). Ver `MASTER-PLAN.md` §K | **PLANIFICADA** |
| **FASE L** — RX550-Tuner | Búsqueda experimental (futura, dependiente de FASE K) de configuraciones PowerPlay/perfiles RX 550: perfiles, límites de potencia, clocks, benchmarks, búsqueda controlada, comparación estadística, validación, reversibilidad. Ver `MASTER-PLAN.md` §K | **PLANIFICADA** |
| **FASE M** — GFX8 Counter Research | Reconciliación de catálogo GFX8; `v3.17` referencia operativa, `v3.11.1` histórica; 2304 filas no equivalen a eventos validados; GRBM=2/SQ=4 son entradas de catálogo, no validación ASIC; programación NO autorizada. Ver `R0-1`, `R1-1` y `FASE-D-GFX8-EVENT-ID-AUDIT.md` | **PLANIFICADA** |
| **RE-02** — línea de investigación RX550 | Ingeniería inversa de la implementación amdgpu en `linux-7.1.3`. Alcance, artículos autorizados y no-autorizaciones: `02-ARQUITECTURA/RE02-DECISION-REGISTER.md` `RG-1` (`HUMAN_POLICY`, 2026-09-28). Autorizado: análisis estático de PDE/PT + instrumentación experimental mínima en C, reversible y aislada. **NO** autorizado: cambiar semántica funcional, optimizar, ni alterar políticas de scheduling / memoria / page tables / CGPG / MEC / power management. La autorización **no es retroactiva**: los `UNKNOWN`, `NOT_DETERMINED` e `INVALIDATED` previos conservan exactamente su estado | **AUTORIZADA** |

### FASE R-0 — EXTERNAL KNOWLEDGE RECOVERY (COMPLETADA 2026-09-22)

Línea documental SOLO READ-ONLY que **acota el gap de event IDs GFX8**; no demuestra runtime ni habilita programación:

- **R-0.1 PARCIALMENTE RECONCILIADO:** la fuente externa documenta catálogos GFX8 genéricos;
  `GPUOpen-Tools/gpu_performance_api` tag `v3.17` (referencia operativa; `v3.11.1` histórico). 2304 filas expuestas no equivalen a 2304 eventos únicos o validados para `1002:699f`.
  La aplicabilidad al ASIC, la equivalencia `gfx803/gfx804` y la semántica siguen `UNKNOWN`.
  GPUPerfAPI v4.0+ eliminó GCN; no se usa `main` como fuente GFX8.
- **R-0.2 [VERIFICADO source-level]:** política DPM MCLK smu7 para bus 128-bit =
  `mclk_up_hyst=5`, `mclk_down_hyst=16`, `mclk_activity=20` (upstream); no equivale a un trigger
  host `mem_busy_percent` ni a una causalidad local. R-4A registró `3/16/20`; el mapping
  de campo/perfil queda `UNRESOLVED` y ambos valores no son gate local.
- **R-0.3 [VERIFICADO source-level]:** radeonsi `has_msaa_sample_loc_bug` incluye
  **POLARIS12**; `LINE_FILTER_DISABLE(family<=POLARIS12)`; driconf
  `clear_db_cache_before_clear`. El efecto real en esta placa permanece sin medir.
- **R-0.4/R-0.5 [DOCUMENTADO]:** características de la familia; no cerrar la capacidad
  exacta de la unidad sin fuente ASIC específica.
- **R-0.6:** GPUPerfAPI, CodeXL, RGP y UMR tienen roles distintos; solo los catálogos
  source-level se pueden citar. UMR no aporta enums de eventos; RGP actual no es una ruta
  GFX8 confirmada.
- **Resultado B de FASE-D:** «IDs GFX8 no verificables con fuentes locales» permanece como
  resultado local; la fuente externa añade catálogo, no validación ASIC.
- **Blanco intacto:** programación de contadores y toda escritura siguen **NO AUTORIZADAS**;
  congelados intactos (KDE, BIOS/VBIOS); no se instaló ni escribió nada en el sistema.

### FASE R-1 — DOCUMENTATION RECONCILIATION & MASTER CONSOLIDATION (COMPLETADA 2026-09-22)

Fase SOLO DOCUMENTAL (read-only) que reconcilia la documentación acumulada (A–R-0) para dejar el
repositorio internamente coherente antes de M/J/L/E–J. Entregables en
`01-AUDITORIA/FASE-R1-DOCUMENTATION-RECONCILIATION/`:

- **R-1.1** `R1-1-GFX8-EVENT-RECONCILIATION.md` — reconciliación de catálogos GFX8:
  **19 coincidencias y 4 discrepancias sobre 23 comparaciones**; la formulación 20/22 queda
  corregida. Semántica/unidad de MC **UNRESOLVED**; no diseñar normalización MC.
- **R-1.2** `FASE-D-GFX8-EVENT-ID-AUDIT.md` §14 — Resultado B cruzado con R-0 (fuente local vs fuente AMD añadida).
- **R-1.3** `FASE-D-ETAPA-2-RESULTADOS.md` §12 — correcciones de la auditoría aplicadas (tabla radeontop método
  declarado, SPI 3306→8408) sin tocar conclusiones.
- **R-1.4** este documento → **v2.5** (historia preservada, contradicciones resueltas vía adenda, no borrado).
- **R-1.5** mapa documental A–R-1 · **R-1.6** modelo de estados de evidencia · **R-1.7** gaps críticos ·
  **R-1.8** capa transversal KERNEL/DRIVER read-only (L.0 Capability Audit ppfeaturemask, pp_od_clk_voltage,
  pp_dpm edge cases) · **R-1.9** readiness E–J · **R-1.10** acciones NO autorizadas;
  **R-1.15** informe final + checklist §14.
- **Constante:** la programación de contadores y toda escritura del sistema SIGUEN **NO AUTORIZADAS**.

### FASE R-2 — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE (COMPLETADA 2026-09-22, SOLO DOCUMENTAL/DISEÑO)

Fase SOLO DOCUMENTAL Y DE DISEÑO (sin ejecución) que documenta el **trabajo pendiente del ecosistema
completo** (no solo RX550/GFX8), con separación rigurosa de estados (DOCUMENTADO/DISEÑADO/PLANIFICADO/
HIPÓTESIS/UNVERIFIED/BLOCKED/NO AUTORIZADO…) y sin convertir nombres provisionales en tecnologías.
Entregables en `01-AUDITORIA/FASE-R2-PROJECT-DOCUMENTATION/`:

- **R-2.1** `R2-HISTORICAL-EXPERIMENT-INVENTORY.md` — E1/E2/E3/E4/E5/E5b EXISTEN en el backup Torneo
  (sesión 17/09); **E0 = NOT FOUND** como artefacto (solo 2 referencias textuales; datos plausibles sin
  etiquetar en `mesa-resolution-2026…113618|135118`); Familia 2 (E-01/E-02/E-03/ES-01/F2) VERIFICADA
  reproducible. Dos familias "E" distintas, no mezclables.
- **R-2.2** `R2-GLOBAL-DOCUMENTATION-MAP.md` + **R-2.24** `PROJECT-DOCUMENTATION-STATUS.md` (raíz):
  navegación completa del repositorio y estado por elemento del ecosistema.
- **R-2.3..R-2.7 + R-2.10..R-2.13 + R-2.18..R-2.20** — diseños formales `FASE-E…Q…-DESIGN.md`
  (baseline de juego real BLOQUEADA por falta de juego reproducible autorizado; GEO-01..08; modelo de
  memoria G-M1..G-M5; workarounds H-1..H-7; PowerPlay/DPM I-1..I-5; Lab K1..K10; Tuner L; contadores M;
  ecosistema N; gestores O; FG/upscaling P; Mesa Q).
- **R-2.8** `EXPERIMENT-PRIORITY-MATRIX.md` (matriz J, 10 criterios → ALTA/MEDIA/BAJA/BLOQUEADOS).
- **R-2.9** `SYNTHETIC-WORKLOAD-DESIGN.md` (8 modos sobre el prototipo CONGELADO).
- **R-2.14..R-2.17** `04-IMPLEMENTACION/projects/BERRETA|GHOST|RX-COMPRESSION-ENGINE|ORCHESTRATOR/*-DESIGN.md`
  (proyectos PROVISIONALES/IDEA, sin implementar; Ghost/RX-Comp dependen de FASE G).
- **R-2.21** `R2-DEPENDENCY-GRAPH.md` (grafo CONFIRMADA/PROBABLE/POTENCIAL).
- **R-2.22** MASTER-PLAN §S · **R-2.23** este documento (v2.6) · **R-2.25** `FASE-R2-FINAL-REPORT.md`.
- **Constante:** programación de contadores y toda escritura SIGUEN **NO AUTORIZADAS**; nada se ejecutó.

### FASE R-3 — ORIGINAL IDEAS, NOVELTY AUDIT & RESEARCH CANDIDATES (COMPLETADA 2026-09-22, SOLO DOCUMENTAL)

Fase SOLO DOCUMENTAL (investigación web; sin ejecución) que generó 10 ideas originales y las auditó contra
prior art. Entregables:

- **I-01..I-10** en `04-IMPLEMENTACION/projects/TBDR-IMR|TEMPORAL-TILE-REUSE|JITTER-REPROJECTION|ROP-COMPUTE-OFFLOAD|
  GFX8-FRAME-RECORDER|GHOST-PREDICTIVE-CACHE|ASYNC-OPTICAL-FLOW|CLOSED-LOOP-QUALITY-GOVERNOR|
  L2-RESIDENT-RENDERING|ASYNC-AUX-RENDERER/` (README + prior-art + diseño + riesgos por idea, 40+ docs).
- **`R3-NOVELTY-MATRIX.md`** — clasificación por prior art (escala KNOWN…NOVELTY UNKNOWN); la mitad
  "residencia" de I-01/I-09 **CONTRADICTED BY PRIOR ART** (CB/DB bypass L2 GFX8); premisa "CUs libres"
  **CONTRADICTED**; I-02+I-03 (temporal tile-lock) = slice PARTIALLY NOVEL; único gap de herramienta real =
  I-05 (viewer SQTT GFX8, NOVELTY UNKNOWN). **0 ideas PROVEN NOVEL**.
- **`R3-FEASIBILITY-MATRIX.md`**, **`R3-DEPENDENCIES.md`**, **`R3-MASTER-PLAN-INTEGRATION-PROPOSAL.md`**
  (MASTER-PLAN NO modificado), **`FASE-R3-FINAL-REPORT.md`** (10 preguntas + checklist + recomendaciones).
- **Recomendaciones:** A (integrar): ninguna; B (research candidate): I-05, piezas async de I-04;
  C (hypothesis): I-02, I-03, I-06, I-08, I-10; D (más investigación): I-07 y sub-reclamo de I-09
  (condicionados); E (discard): I-01, I-09 headline, I-04 full-ROP.
- **Constante:** programación de contadores y toda escritura SIGUEN **NO AUTORIZADAS**; nada se ejecutó.

### FASE R-3.1 — FUSION ARCHITECTURE AUDIT (COMPLETADA 2026-09-22, SOLO LECTURA)

Auditoría READ-ONLY de las **7 fusiones** formadas por agrupación de las ideas de R-3. Entregables en
`01-AUDITORIA/FASE-R3-1-FUSION-ARCHITECTURE-AUDIT/`:

- **FUSION-01..07** (`FUSION-01-JITTER-DUAL-CONSUMER.md` … `FUSION-07-MINI-ENGINE.md`) — auditorías por fusión.
- **`ASSUMPTION-AUDIT.md`** — **20 premisas** clasificadas VERIFIED(1)/CONTRADICTED(9)/PARTIALLY VERIFIED(5)/
  PLAUSIBLE(2)/UNKNOWN(5)/REQUIRES EXPERIMENT(2). Claves: ROP saturación REQUIRES EXPERIMENT; 32×32≠unidad HW
  CONTRADICTED; framebuffer-en-L2 CONTRADICTED (bypass CB/DB); jitter≠motion vector CONTRADICTED; compute≠free
  CONTRADICTED como regla; DCC no ahorra PCIe CONTRADICTED; RGP Polaris PARTIALLY (RGP 1.x-era SÍ cubría GCN).
- **Matrices:** `NOVELTY-MATRIX.md`, `FEASIBILITY-MATRIX.md`, `DEPENDENCY-MATRIX.md` (D-3/layer/Mesa/kernel/
  RX-Compression/Ghost/BERRETA/Orquestador), `IMPLEMENTATION-LAYER-MATRIX.md` (ninguna FIRMWARE; kernel solo
  en F3/F4; F1/F4readonly/F6calib = únicas implementables hoy en APPLICATION/LAYER).
- **`EXPERIMENT-ROADMAP.md`** — diseños EXP-F1-A (jitter observable), EXP-F2-A (tile 16/32/64), EXP-F3-A
  (bandwidth real), EXP-F4-A (governor read-only), **EXP-F5-A (mínimo obligatorio de fusión 5)**, EXP-F6-A
  (concurrencia 8 CU). **NINGUNO ejecutado.**
- **`PRIOR-ART-INDEX.md`** — índice consolidado R-3⇄R-3.1 (incluye refutación de fuente LinuxReviews/DCC-PCIe).
- **`R3-1-MASTER-REPORT.md`** — 10 respuestas ejecutivas + checklist de cierre 21/21.
- **Veredictos de prioridad:** FUSION-04 (governor read-only) READY FOR FUTURE EXPERIMENT · FUSION-01/03
  NEEDS PRECONDITION · FUSION-02/05/06 REJECTED/FALSIFIED (versiones fuertes) · FUSION-07 BLOCKED/RESEARCH
  ONLY · FUSION-05 sub-pieza async → BERRETA ASY-01.
- **Constante:** programación de contadores y toda escritura SIGUEN **NO AUTORIZADAS**; MASTER-PLAN NO fue
  modificado durante R-3/R-3.1; R-3.1 solo actualizó este documento (v2.7).

### FASE R-4A — EXP-F3-A BANDWIDTH REAL (COMPLETADA 2026-09-22, READ-ONLY)

Precondición R-3.1 de FUSION-03 resuelta en modo solo-lectura (ni una escritura). Informe:
`03-EXPERIMENTOS/FASE-R4A-BANDWIDTH-REAL/EXP-F3-A-BANDWIDTH-REAL.md`.

- **VERIFIED (sysfs):** enlace PCIe negociado **5.0 GT/s (Gen2) ×4** por techo del **root port 00:01.0**
  (max_link_speed 5.0 GT/s); tarjeta capaz de 8.0 GT/s ×8 pero la plataforma no lo permite. VRAM 2 GiB,
  VIS-VRAM **256 MiB**, GTT **6.2 GB** (=5.77 GiB). Cap 35 W, ~3.7 W ocio. mclk 300/625/1500 MHz, sclk hasta
  1071 MHz.
- **DERIVED:** Gen2×4 teórico = **2.0 GB/s por sentido** (20 GT/s ÷ 10, 8b/10b).
- **ESTIMATED:** payload PCIe efectivo ≈1.4–1.9 GB/s (overhead TLP); VRAM teórica **96–112 GB/s**
  (mclk 1500 × factor GDDR5 ×4 — cross-check R9 290/RX 480; módulo exacto UNKNOWN).
- **Corrección de modelo:** ratio enlace/VRAM pasa de ×24–32 (con 48 GB/s) a **×48–80**. Dirección de las
  conclusiones de FUSION-03 sin cambios; solo magnitud. Adenda escrita en FUSION-03.
- **UNKNOWN / REQUIRES FUTURE EXPERIMENT:** bandwidth REAL medido (amdgpu_benchmark bloqueado por permisos;
  su `.write` correría benchmarks → prohibido aquí); GTT no es constante (depende de DRAM del sistema); módulo
  GDDR5 6 vs 7 Gbps.
- **Constante:** programación de contadores y toda escritura SIGUEN **NO AUTORIZADAS**; no se creó workload,
  no se ejecutó benchmark; MASTER-PLAN intacto.

### FASE R-4C — EXP-F1-A JITTER OBSERVABILITY (COMPLETADA — harness ejecutado bajo autorización, 2026-09-22)

PRECHECK (diseño, verificado read-only) + **EJECUCIÓN COMPLETADA** tras autorización explícita. Todo local en
`03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/` (`harness/`, `results/`); capa vía `VK_LAYER_PATH` local; CERO
modificaciones al sistema; sin benchmarks de rendimiento. Entregables: `README.md`, `EXP-F1-A-JITTER-OBSERVABILITY.md`,
`PRECHECK-REPORT.md`, `PRIOR-ART.md`, y **`EXP-F1-A-RESULTADOS.md`** (resultados observados). Conclusión:

- **NIVEL A (canal directo vía `vkCmdPushConstants`): VERIFICADO por ejecución.** La capa intercepta el llamada
  y lee `pValues` en tiempo de recording → **MAE = 0.0 px (bit-idéntico a la GT)**, 320/320 frames medidos,
  Pearson 1.0, en RADV real (RX 550) y lavapipe.
- **NIVEL B (reconstrucción desde matriz de proyección FSR-consistente `M_jit=translate(jx_ndc,jy_ndc,0)·M_base`
  en UBO host-visible): VERIFICADO por ejecución.** La capa lee los dos slots, computa `T=projJit·inv(projBase)`
  y extrae `jx_px=T[12]·W/2`, `jy_px=−T[13]·H/2` → **MAE total = 3.66×10⁻¹⁰ px, máx error = 3.0×10⁻⁸ px**
  (piso FP32 de la ruta matriz), 320/320, Pearson 1.0.
- **MAE<0.01 px (PROVISIONAL TARGET): PASS con margen ~×10⁷** (0.01 px ÷ 3.66×10⁻¹⁰ px). El piso FP32 observado
  es incluso menor que la cota conservadora ~×50–500 del PRECHECK (matrices exactas, sin acumulación).
- **Matriz ejecutada:** NIVEL A/B × {RADV, lavapipe} × 2 réplicas = **8 corridas exitosas, deterministas**
  (ANV opcional NO EJECUTADO: sin devices físicos con `intel_icd.x86_64.json` — documentado, no como fallo).
- **Incidencias resueltas (documentadas en el informe):** `library_path` relativo→`dlopen` requiere
  `LD_LIBRARY_PATH` local; coexistencia con la implicit layer `VK_LAYER_MESA_device_select` (cadena `pNext`
  distingue link por `function==VK_LAYER_LINK_INFO`); `vkCreateDevice` se resuelve por instance-GPA, no por
  device-GPA con `VK_NULL_HANDLE`; PFN 1.4.341 sin `VkDevice` inicial en device/queue/cmd; gating de nivel con
  comparación a `"1"`.
- **Regla cumplida:** en ningún punto se concluye jitter = motion vector (el MV del harness es fijo e independiente).
- **Constante:** programación de contadores y toda escritura SIGUEN **NO AUTORIZADAS**; el plan maestro es documental y no autoriza acciones.

### SNAPSHOT HISTÓRICO PRE-D6 — FASE R-4B / EXP-F4-A GOVERNOR READ-ONLY (no vigente; Addenda D6 arriba prevalece)

> **ADDENDA D6 — estado posterior a la propuesta v2.3 (2026-09-23):** S1-v2.3
> **EJECUTADA/COMPLETADA** (15/15 bloques; 8/8 trials); S2-v2.3 **INICIADA y PARADA D**
> en el cooldown p2→p3, antes de Phase 2. El veredicto global es **INCONCLUSO /
> INCONCLUSIVE**, nunca `SUPPORTED`. La causa de interferencia externa no se declara
> verificada; los localizadores `/tmp/opencode/` canónicos T1–T13 están perdidos/no verificables
> y no se reconstruyen. Este addenda no reescribe los snapshots v2.1/v2.2 anteriores.

Precondición R-3.1 de FUSION-04 (governor **read-only**, único actuador = render-scale, sin contadores).
Documentación base: `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/` (`EXP-F4-A-PROTOCOL.md` v2.1, `PRE-FLIGHT-CALIBRACION-EXP-F4-A.md`,
`EXP-F4-A-RESULTADOS.md`).

- **S1 v2.1 (parada D, datos intactos en `results/session1/`):** 15/15 bloques open-loop → GATE de
  histéresis **FALLADO (58.3 %)** por throttling térmico (SCLK 1071→551 MHz a ~92 °C en p2/p3). El GATE §14-D
  protegió la corrida (sin FREEZE). Registro completo en `EXP-F4-A-RESULTADOS.md` §1B.
- **Investigación térmica read-only (`FASE-R4B-THERMAL-TEST/`):** caracterización A–J con N=2 réplicas —
  ramp 0.315/0.310 °C/s (±1.6 %), recuperación a ≤50 °C en 255–270 s, `W_SMU` 23.5 W < cap 35 W →
  asociación térmica observada; no se afirma causalidad "puramente térmica". Kalm audito
  (VERIFIED: NO interviene — kalmd 4087 solo afinidad IRQ,
  kalm-lite 4086 solo vm.*/proc, kalm-gpu.service muerto desde 18/09). Curvas, análisis y propuesta de
  cooldown en `RESULTADOS-TEST-TERMICO.md` + `analyze_thermal.py`.
- **Variación v2.2 (autorizada, documentada formalmente ANTES de ejecutar en `EXP-F4-A-PROTOCOL-v2.2.md`):**
  único cambio = cooldown pasivo entre passes de Fase 1 (p1→p2→p3), condición de retorno **telemétrica**
  `temp ≤50 °C sostenido ≥30 s ∧ SCLK nivel 0 ∧ W_SMU<4 W` (expectativa ~270 s NO asumida como tope; tiempos
  reales registrados). Workload, T, s*, escalas, thresholds, R1–R7, F1–F6, bloques y duraciones **sin
  cambios**.
- **S1 v2.2 ejecutada (`results/session1-v22/`):** **15/15 bloques con SCLK 1071 MHz sostenido en los 3
  passes** (sub-1071 1.2–1.5 % transitorios; T_max p2/p3 = 86 °C, nunca ~92 °C); **GATEs Fase 1 TODOS PASS
  (histéresis 0.26 %)**; **FREEZE T=9.168 ms, s*=0.75, sha256 `6b6d6952…`** (`fase1/manifest.json` +
  `frozen.sha256`); cooldowns reales **180 s** y **225 s**; **Phase 2 completa 8/8 trials** (orden
  `fixed gov fixed gov fixed gov dist dist`); integridad 15/15 + 8/8, DPM/kalm/cap pre↔post idénticos
  (hash `ff9e8280bd…`), journal sin eventos de subsistema → **sin writes**.
- **Diagnóstico formal de Phase 2 — clasificación `DIAGNOSTIC / THERMALLY CONFOUNDED — NOT FOR
  VERDICT`:** auditoría de timestamps (telemetría 10 Hz + governor_trace) demuestra que la causa es
  **temperatura acumulada**, no duración de trial: Phase 2 heredó 84 °C de Fase 1 (sin cooldown
  FREEZE→fixed1) y cada trial heredó 91–92 °C del anterior (sin cooldown entre trials) → SCLK
  551 MHz desde ~v0. Solo fixed1 conserva v0–v1 limpias; 0 de 8 trials íntegros. R1–R7 **NO**
  declarados con estos datos (ni PASS ni FAIL); Fase 1/FREEZE conservados íntegros. Detalle:
  `EXP-F4-A-RESULTADOS.md` §1C.5.
- **Propuesta v2.3 preparada (`EXP-F4-A-PROTOCOL-v2.3-PROPUESTA.md`), NO EJECUTADA:** cooldown
  telemétrico entre CADA trial de Phase 2 (condición DN-07 ≤50 °C s30s ∧ SCLK nv0 ∧ P<4 W);
  FIXED (60 s→≈69 °C) y GOV (120 s→≈87 °C) enteros desde ≤50 °C (margen bajo 90 °C verificado);
  DIST (200 s) con 3 opciones (entrada ≤40 °C / mini-test read-only de ramp con governor activo /
  marcación por ventana); regla por ventana `THERMALLY CONFOUNDED` (T>90 °C o SCLK<1071 → ventana
  excluida); segmentación RECHAZADA (invalida ventanas ancladas a t0 y steps internos +60/+120);
  auditoría de invariantes (T/s*/escalas/banda/R1–R7/F1–F6/workload/réplicas/governor/harness/
  analyze) sin cambios; duración estimada ~65–72 min/sesión. Respuestas A–I y evaluación de los 5
  esquemas de cooldown dentro.
- **Mini-test 7.3-B EJECUTADO (N=2 read-only, autorizado por el usuario 2026-09-23; NO forma
  parte de S2; datos en `FASE-R4B-THERMAL-TEST/runs/minitest-ramp-gov/rep{1,2}/`; plan
  `EXP-F4-A-MINITEST-RAMP-GOV-PLAN.md`, resultados `RESULTADOS-MINITEST-7.3-B.md`):** ramp con
  governor activo (governor.py sin tocar, T=9.168 ms) partiendo de DN-07 (≤50 °C). Respuestas
  A–I: governor responde correctamente a 1071 (LOWER/RAISE alineadas, latencias dentro de
  especificación, p99 trace == p99 frames en todas las ventanas → semántica temporal íntegra);
  **ramp efectiva 0.252 vs 0.246 °C/s (Δ=2.1 %, reproducible)**; **T_max=92 °C en ambas
  réplicas ANTES de completar los 200 s** (REP1 v9 degradada T≥90 a t≈172 s; REP2 v7–v9 T≥90 a
  t≈135 s, entrada 45 °C); SCLK 1071 sostenido solo en las ventanas limpias (REP1 v0–v7,
  REP2 v0–v5); 0 aborts, ±0 writes verificado (DPM/kalm/cap idénticos `ff9e8280bd`). **Conclusión
  per criterio: DIST NO puede ejecutarse íntegro desde ≤50 °C (opción 1 NO demostrada);
  la entrada ≤35 °C queda como opción histórica no verificada y `t90≈221 s` es
  extrapolación, no viabilidad. ≤40 °C también es extrapolación; 7.3-C era la red de
  seguridad propuesta.
  NO se preparó v2.3-final; la elección 7.3-A/C y la autorización de S2 son texto pre-D6;
  el estado posterior es S2 INICIADA/PARADA_D.
- **Snapshot histórico previo a v2.3:** la sesión 2 figuraba como **NO iniciada** en este
  bloque v2.2; la corrida posterior está registrada en la addenda D6 superior: S1-v2.3
  EJECUTADA/COMPLETADA, S2-v2.3 **PARADA D** antes de Phase 2 y veredicto **INCONCLUSO /
  INCONCLUSIVE**. La programación de contadores y toda escritura SIGUEN **NO AUTORIZADAS**.

### Índice de auditorías background y readiness (N7)

Las siguientes auditorías son documentos read-only de 2026-09-23. No autorizan por sí
mismas ninguna acción sobre servicios, timers, Kalm, sysfs o el sistema:

| Documento | Alcance | Estado |
|---|---|---|
| `00-INDICE/AUDITORIA-ACTUALIZACIONES-AUTOMATICAS.md` | Mecanismos automáticos de actualización | READ-ONLY; no se modificaron servicios |
| `00-INDICE/AUDITORIA-CANDIDATOS-BACKGROUND-v2.md` | Candidatos de procesos/unidades en segundo plano | READ-ONLY; `system-autopilot.timer` no se desactiva |
| `00-INDICE/AUDITORIA-CONSUMO-SEGUNDO-PLANO.md` | Consumo de CPU/RAM/HDD y I/O en segundo plano | READ-ONLY; evidencia conservada |
| `00-INDICE/PROTOCOLO-AB-LIMPIEZA-BACKGROUND.md` | Protocolo A/B propuesto, pendiente de decisión | NO EJECUTADO; no se realizó ninguna desactivación |
| `01-AUDITORIA/IMPLEMENTATION-READINESS/IMPLEMENTATION-READINESS-AUDIT.md` | Madurez de implementación y frontera de seguridad | READ-ONLY; no implementa ni modifica el sistema |

Los documentos canónicos auxiliares de readiness están en
`04-IMPLEMENTACION/IMPLEMENTATION-ROADMAP.md` y
`04-IMPLEMENTACION/IMPLEMENTATION-SAFETY-RULES.md`.

| **FASE N** — Technology Naming & Architecture | Línea DOCUMENTAL (PLANIFICADA): inventario y nomenclatura oficial del ecosistema; clasificar proyectos/tecnologías/frameworks/herramientas/motores/perfiles/experimentos/investigaciones/benchmarks/documentación; tabla `Nombre oficial|tipo|objetivo|estado|dependencia|alias`; no implementar tecnologías. Ver `MASTER-PLAN.md` §K | **PLANIFICADA (DOCUMENTAL)** — diseño completo en FASE R-2.13 (`FASE-N-ECOSYSTEM-ARCHITECTURE.md`) |
| **FASE O** — GPU Control & Orchestration Research | Línea de INVESTIGACIÓN (PLANIFICADA): evaluar LACT, CoreCtrl, amdgpu-clocks, interfaces sysfs/amdgpu, PowerPlay, DPM, runtime-PM, perfiles, restauración y ownership; no reemplazar rx550-torneo sin comparar capacidades; Protocolo GPU Ownership (detectar→verificar→adquirir→experimentar→restaurar→liberar→verificar) y aplicarlo a gestores como Kalm solo si realmente están activos. Herramientas externas = objetos de evaluación, no soluciones adoptadas. Ver `MASTER-PLAN.md` §K | **PLANIFICADA** |
| **FASE P** — Frame Generation & Upscaling Research | Línea de INVESTIGACIÓN (PLANIFICADA): lsfg-vk, FSR, upscaling, frame generation, Vulkan layers, inyección/interposición, coste/latencia/calidad, compatibilidad Polaris12; separar estrictamente RENDIMIENTO REAL vs PERCIBIDO; nunca mezclar en los benchmarks del Lab K. No asumir mejora sin experimentos. Ver `MASTER-PLAN.md` §K | **PLANIFICADA** |
| **FASE Q** — Mesa Polaris12 Optimization Research | Línea de INVESTIGACIÓN (PLANIFICADA): oportunidades en Mesa/radeonsi/RADV específicas de Polaris12 sin asumir beneficio; pipeline OBSERVACIÓN→HIPÓTESIS→CAMBIO AISLADO→A/B→RÉPLICAS→MEDICIÓN→VALIDACIÓN→ACEPTAR/RECHAZAR; cambios aislados para causalidad; modificación solo en etapa experimental futura con rollback definido. Ver `MASTER-PLAN.md` §K | **PLANIFICADA** |

*Nota: las FASE K/Q (K, L, M, N, O, P, Q) son roadmap **PLANIFICADO/FUTURO** — no autorizadas para ejecución; ninguna hipótesis presentada como resultado experimental; N/O/P/Q son líneas de investigación documental; GRBM_PERFCOUNTER0_SELECT=0x2 (GUI_ACTIVE) y SQ PERF_SEL=0x4 (WAVES) son **entradas de catálogo GFX8**, no verificaciones ASIC; la ejecución/escritura sigue NO autorizada (no se afirma que UMR sea la única vía). No se asume que Kalm está activo: su estado debe verificarse en el momento de cada experimento. LACT/CoreCtrl/amdgpu-clocks = objetos de evaluación, no soluciones adoptadas. BIOS/VBIOS = solo investigación futura de alto riesgo. Las FASE E–J existentes permanecen intactas. Inventario del ecosistema, arquitectura conceptual, Protocolo GPU Ownership, ciclo de vida de tecnologías, principio fundamental y FASE L/M ampliadas en `MASTER-PLAN.md` §K. Añadida la **Capa Transversal — KERNEL / DRIVER COMPATIBILITY & EDGE-CASE LAYER** (sección final de `MASTER-PLAN.md`, no es una FASE): telemetría (clasificación A/B/C/D), LACT vs rx550-torneo, amdgpu-clocks (identificación por PCI), L.0 ppfeaturemask, pp_od_clk_voltage, pp_dpm edge cases (WRITE SUCCESS ≠ STATE CHANGE VERIFIED), pp_table, VBIOS high-risk, Observability Perturbation, Hardware Identity, Capability Matrix, Experimental Safety Gate y clasificación de afirmaciones externas.*

---

## 🔒 CONGELADO (NO TOCAR sin autorización explícita nueva)

- **WORKLOAD-SINTETICO:** código, shaders, Makefile, configuración Mesa, drirc, Kalm, kernel, GRUB
- **BIOS / VBIOS / SPPT / pp_table**
- **ppfeaturemask** (valor actual `0xfff7bfff` — no escribir)
- **Kalm writes** (kalmd.py, kalm-lite.py, kalm-gpu.service, config `/etc/kalm/`)
- **Mesa del sistema** (`/usr/lib64/`, `/usr/share/vulkan/icd.d/`)
- **GRUB / kernel / DRM / KMS / amdgpu config**
- **Cambios permanentes de sysfs** (power1_cap, DPM, pp_dpm_sclk/mclk, pp_power_profile_mode)
- **Configuraciones permanentes del sistema**

---

## 📁 ARTEFACTOS CLAVE (Rutas)

| Artefacto | Ruta |
|---|---|
| Auditoría completa | `01-AUDITORIA/AUDIT-001/` (AUDIT-001.md, ERRATA.md, METRICS-DEFINITIONS.md, EVIDENCE-MATRIX.md) |
| FASE A — discriminación (histórica) | `03-EXPERIMENTOS/fase-a-discriminacion-20260919-114241/` (RESULTADOS-FASE-A.md, INVALIDACION-corridas-04-09.md) |
| FASE B — cap-probe (histórica) | `03-EXPERIMENTOS/fase-b-cap-probe-20260919-122038/` (RESULTADOS-FASE-B.md, EP08-auditoria-telemetria-E1E3.md) |
| FASE B — POLARIS12-MAP (histórica) | `02-ARQUITECTURA/POLARIS12-MAP/` (POLARIS12-MAP.md, HARDWARE-ROUTES.md, SOFTWARE-CAPABILITIES.md, EXPERIMENT-CANDIDATES.md, UNVERIFIED-CLAIMS.md) |
| EP-05 (Mesa CUSTOM A/B) | `03-EXPERIMENTOS/ep05-mesa-custom-20260919-212249/RESULTADOS-EP05.md` |
| EP-06 (soak + réplica) | `03-EXPERIMENTOS/ep06-soak-cap-20260919-205645/RESULTADOS-EP06.md` |
| rx550-torneo | `04-IMPLEMENTACION/rx550-torneo/` (Fases 1–3 + M1, 65/55/56/112 checks OK) |
| M1 (vkmark 35/30W) | `03-EXPERIMENTOS/M1-cap-35-30/` (RESULTADOS-M1.md, TELEMETRY-SCHEMA.md, runs/20260919-235939/) |
| E-03 corregida | `03-EXPERIMENTOS/WORKLOAD-SINTETICO/runs/exploratorio-03-corrected/` |
| ES-01 (Escalado) | `03-EXPERIMENTOS/WORKLOAD-SINTETICO/runs/escalado-01/` |
| F2 (8 fetches) | `03-EXPERIMENTOS/WORKLOAD-SINTETICO/runs/escalado-01/F2-*/` |
| GravityMark | `03-EXPERIMENTOS/EXPLORATORIO-GravityMark/runs/` |
| Superposition (exploratorio) | `03-EXPERIMENTOS/EXPLORATORIO-GravityMark/runs/Superposition/` |
| **FASE C — R-14 Superposition Dissection** | `03-EXPERIMENTOS/R-14-SUPERPOSITION-DISSECTION/` (R-14-SUPERPOSITION-DISSECTION.md, runs/superposition_dissection_1/) |
| **FASE D — Performance Counters** | `03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT/` — Etapa 1: `FASE-D-COUNTERS-AUDIT.md` · Etapa 2: `FASE-D-ETAPA-2-PLAN.md`, `FASE-D-ETAPA-2-RESULTADOS.md` (+§12 correcciones R-1.3), `FASE-D-ETAPA-2-AUDIT.md` + `runs/etapa2/A{1,2,3}/B{1,2,3}/` · Etapa 3 (DISEÑADA, NO EJECUTADA): `FASE-D-ETAPA-3-PLAN.md`, `FASE-D-ETAPA-3-PRECHECK.md`, `FASE-D-ETAPA-3-EVENTS.md` · **Auditoría IDs**: `FASE-D-GFX8-EVENT-ID-AUDIT.md` (COMPLETADA, Conclusión B + adenda §14 R-1.2) |
| **FASE R-0 — External Knowledge Recovery** | `05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/` (R0-1..R0-6 + REFERENCE.txt + informe final) — COMPLETADA |
| **FASE R-1 — Documentation Reconciliation** | `01-AUDITORIA/FASE-R1-DOCUMENTATION-RECONCILIATION/` (R1-1..R1-15) — COMPLETADA |
| **FASE R-2 — Project Documentation** | `01-AUDITORIA/FASE-R2-PROJECT-DOCUMENTATION/` (R-2.1..R-2.25, FASE-R2-FINAL-REPORT.md) + raíz `PROJECT-DOCUMENTATION-STATUS.md` — COMPLETADA |
| **FASE R-3 — Original Ideas / Novelty Audit** | `01-AUDITORIA/FASE-R3-NOVELTY-AUDIT/` (R3-NOVELTY-MATRIX, R3-FEASIBILITY-MATRIX, R3-DEPENDENCIES, R3-MASTER-PLAN-INTEGRATION-PROPOSAL, FASE-R3-FINAL-REPORT) + `04-IMPLEMENTACION/projects/` I-01..I-10 (40+ docs) — COMPLETADA |
| **FASE R-3.1 — Fusion Architecture Audit** | `01-AUDITORIA/FASE-R3-1-FUSION-ARCHITECTURE-AUDIT/` (FUSION-01..07, ASSUMPTION-AUDIT, NOVELTY/FEASIBILITY/DEPENDENCY/IMPLEMENTATION-LAYER matrices, EXPERIMENT-ROADMAP, PRIOR-ART-INDEX, README, R3-1-MASTER-REPORT) — COMPLETADA (READ-ONLY) |
| **FASE R-4A — EXP-F3-A Bandwidth Real** | `03-EXPERIMENTOS/FASE-R4A-BANDWIDTH-REAL/EXP-F3-A-BANDWIDTH-REAL.md` — COMPLETADA (READ-ONLY): enlace Gen2×4 (techo bridge), PCIe teórico 2.0 GB/s/sentido DERIVED, VRAM 96–112 GB/s ESTIMATED, GTT 6.2 GB VERIFIED; real UNKNOWN; adenda en FUSION-03 |
| **FASE R-4C — EXP-F1-A Jitter Observability** | `03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/` (README.md, EXP-F1-A-JITTER-OBSERVABILITY.md, PRECHECK-REPORT.md, PRIOR-ART.md, EXP-F1-A-RESULTADOS.md, harness/, results/) — **COMPLETADA**: NIVEL A MAE=0.0px y NIVEL B MAE=3.66×10⁻¹⁰px/máx 3×10⁻⁸px reconstruyendo desde matriz host-visible; 8/8 corridas PASS deterministas (RADV RX550 real + lavapipe ×2 réplicas ×2 niveles); MAE<0.01px PROVISIONAL TARGET superado ~×10⁷; ANV NO EJECUTADO (sin devices); jitter≠MV |
| **FASE R-4B — EXP-F4-A Governor Read-Only (fila histórica; D6 vigente)** | `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/` (EXP-F4-A-PROTOCOL.md v2.1, EXP-F4-A-PROTOCOL-v2.2.md, **EXP-F4-A-PROTOCOL-v2.3-PROPUESTA.md**, PRE-FLIGHT-CALIBRACION-EXP-F4-A.md, EXP-F4-A-RESULTADOS.md, harness/, controller/, telemetry/, results/session1) + `03-EXPERIMENTOS/FASE-R4B-THERMAL-TEST/` (investigación térmica A–J, N=2, **mini-test 7.3-B ramp con governor N=2**) — **S1 v2.2 COMPLETADA 2026-09-23**: GATEs TOTALES PASS (histéresis 0.26 % tras cooldown entre passes), FREEZE T=9.168 ms/s\*=0.75/sha256 `6b6d6952…`, Phase 2 8/8 ejecutados y **clasificada `DIAGNOSTIC / THERMALLY CONFOUNDED — NOT FOR VERDICT`** (R1–R7 sin declarar, causa = temperatura acumulada, N=2); sin writes; S1 v2.1 = parada D (registro §1B); **propuesta v2.3 preparada (cooldown entre trials de Phase 2; DIST opciones 7.3-A/B/C)**; **mini-test 7.3-B ejecutado (N=2): DIST 200 s NO cabe desde ≤50 °C (ramp 0.252/0.246 °C/s, T_max 92 °C pre-final) → entrada ≤35 °C (7.3-A) o 7.3-C como opciones; la corrida v2.3 posterior quedó **S1 EJECUTADA/COMPLETADA + S2 PARADA D**, veredicto **INCONCLUSO** |
| Benchmarks (inventario) | `05-FUENTES-EXTERNAS/RX550_Benchmarks/BENCHMARK-INVENTORY.md` — cuatro ejes; instalaciones externas observadas, ejecuciones históricas y elegibilidad separadas |
| Ecosistema / inventario (FASE N–Q) + Capa Transversal | `MASTER-PLAN.md` §K (FASE K/Q, arquitectura conceptual, inventario del ecosistema, Protocolo GPU Ownership, RX Compression Engine provisional, FASE L/M ampliadas, ciclo de vida y principio fundamental) + sección final **Capa Transversal — KERNEL / DRIVER COMPATIBILITY & EDGE-CASE LAYER** (telemetría y clasificación A/B/C/D, LACT/amdgpu-clocks, ppfeaturemask L.0, pp_od_clk_voltage, pp_dpm edge cases, pp_table, VBIOS high-risk, Observability Perturbation, Hardware Identity, Capability Matrix, Experimental Safety Gate, clasificación de afirmaciones externas) |

---

## 🚫 NO HACER (Reglas de Seguridad)

1. No escribir `power1_cap`, DPM, SCLK, MCLK, ppfeaturemask fuera de corrida autorizada con snapshot+readback+restore.
2. No instalar/ejecutar benchmarks/instaladores sin autorización y revisión de licencia.
3. No modificar rx550-torneo, artefactos M1, Mesa system, `/opt/mesa-...`, kalm, GRUB/kernel/DRM.
4. No diseñar/implementar BERRETA, Ghost Cache, GEO, memoria, RADV, PowerPlay — falta caracterizar cuello de botella y documento de diseño.
5. No adoptar régimen histórico 17/09 como especificación de rendimiento ([NO REPRODUCIBLE]).
5. No comparar métricas de potencia sin etiquetar `NOT DIRECTLY COMPARABLE` (ver `METRICS-DEFINITIONS.md`).

---

## 📋 PRÓXIMA ACCIÓN INMEDIATA

> **ADDENDA D6 — acción vigente (2026-09-23):** no se reintenta S2. S1-v2.3 está
> EJECUTADA/COMPLETADA; S2-v2.3 está PARADA D antes de Phase 2; el veredicto es
> **INCONCLUSO / INCONCLUSIVE**, nunca `SUPPORTED`. La fuente canónica es
> `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/EXP-F4-A-RESULTADOS-v2.3.md`, que contiene el
> inventario de los 13 localizadores `/tmp` perdidos/no verificables. Las frases
> siguientes que hablan de «autorización para ejecutar S2» son un snapshot histórico de
> la propuesta y no reactivan esa ejecución.

**ACCIÓN VIGENTE (reconciliación 2026-09-24):** no reintentar S2-v2.3. La S1-v2.3 queda `EXECUTADA/COMPLETADA`; la S2-v2.3 queda `INICIADA/PARADA_D`; el veredicto global es `INCONCLUSO/INCONCLUSIVE`, nunca `SUPPORTED`. Cualquier réplica futura es un protocolo/hipótesis nuevo y requiere autorización nueva. La capability/semántica WSI de H12-2 quedó documentada en `01-AUDITORIA/FASE-H12-2-WSI-DOCUMENTATION/H12-2-XDG-SHELL-VULKAN-WSI-EVIDENCE.md`; la capa causal H12 sigue `UNKNOWN`. Cualquier continuación de H12 es un protocolo/hipótesis nuevo y requiere autorización nueva; esta addenda no autoriza ejecución.

### SNAPSHOT HISTÓRICO — PROPUESTA v2.3 / MINI-TEST (no reinterpreta el estado D6)
`03-EXPERIMENTOS/FASE-R4B-GOVERNOR/EXP-F4-A-RESULTADOS.md` §1C + `EXP-F4-A-PROTOCOL-v2.2.md` +
`EXP-F4-A-PROTOCOL-v2.3-PROPUESTA.md` + `FASE-R4B-THERMAL-TEST/RESULTADOS-MINITEST-7.3-B.md`:
GATEs Fase 1 **TODOS PASS** (histéresis 0.26 % tras cooldown v2.2 entre passes), **FREEZE
T=9.168 ms, s*=0.75** (sha256 `6b6d6952…`), Phase 2 8/8 trials ejecutada y **clasificada
`DIAGNOSTIC / THERMALLY CONFOUNDED — NOT FOR VERDICT`** (auditoría de timestamps: contaminación por
**temperatura acumulada** — Phase 2 heredó 84 °C de Fase 1 y 91–92 °C entre trials; 0 de 8 trials
íntegros; R1–R7 NO declarados). Verificaciones integridad/read-only OK. **Mini-test 7.3-B
EJECUTADO (N=2 read-only, autorizado por el usuario, NO parte de S2):** governor responde
correctamente a 1071 y semántica íntegra, pero **DIST de 200 s NO cabe desde ≤50 °C**
(ramp real 0.246–0.252 °C/s, T_max 92 °C antes del final en ambas réplicas; REP1 v9 degradada,
REP2 v7–v9). **Decisión pendiente del usuario:** (a) opción DIST — **7.3-A con entrada ≤35 °C**
(recomendada por la ramp medida; ≤40 °C queda sin margen) o **7.3-C** marcación por ventana
(R7 → DIAGNOSTIC NOT FOR VERDICT); (b) autorización explícita para
ejecutar S2 bajo v2.3 (reproducible extendiendo `run_all_v22.sh`). Constante: programación de
contadores y toda escritura SIGUEN NO AUTORIZADAS; S1-v2.1 original intacta como diagnóstico.
Tras R-4B siguen candidatos NO INICIADOS: EXP-F5-A (fusión 5 mínimo obligatorio), EXP-F6-A
(concurrencia 8 CU). Recordatorio permanente de FASE D:
**PROGRAMACIÓN PERMANECE NO AUTORIZADA.** Etapa 3: eventos investigados (`03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT/FASE-D-ETAPA-3-EVENTS.md`, offline/read-only): mecanismo CP/eventos VERIFICADO en código Mesa local (CP_PERFMON_CNTL 0/1/2; eventos V_028A90 START=23/STOP=24/SAMPLE=27; campos SQ_CTRL; COMPUTE_PERFCOUNT_ENABLE); CONCORDANCIA Mesa↔UMR de offsets (dword = byte/4). **Auditoría de Event IDs GFX8 completada** (`03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT/FASE-D-GFX8-EVENT-ID-AUDIT.md`): se investigaron Mesa local (+ historial git completo 222 644 commits), kernel amdgpu (recortado: solo Kconfig/Makefile), amdgfxregs.h (sin enums PERF_SEL), UMR db (2633 regs, CERO enums de evento), /opt, backups, /usr/share/doc y $HOME. **Conclusión B: «Los IDs de eventos GFX8 no pueden verificarse mediante las fuentes locales disponibles.»** radeonsi (sí soporta GFX8 y AMD_performance_monitor) reenvía el selector del usuario sin definir eventos; los únicos IDs numéricos (GRBM=2 «GPU active», SQ WAVES=4, GL1C/GL2C/TCP/SQ_*, CPF=0x18) son de RADV y **solo se ejecutan/probaron en GFX10.3 (o GFX11, con valores distintos p.ej. SQ WAVES=0x14)** — el comentario del commit de enablement (f905edb1991) dice literalmente «the code has only been tested on GFX10.3»; GFX8 nunca se habilitó. **GRBM PERF_SEL=2 y SQ PERF_SEL=4 → NO VERIFICADO para GFX8** (GUI_ACTIVE solo existe como bit 31 de GRBM_STATUS, no como selector). **La primera escritura `GRBM_PERFCOUNTER0_SELECT=0x2` (propuesta §H del EVENTS) queda BLOQUEADA** — científicamente no válida sin el mapa de eventos VI. Fuente primaria faltante: tabla PERF_SEL de VI/gfx803 de material AMD (GPUPerfAPI/CodeXL/RGP o documentación oficial Polaris). **No ejecutar hasta nueva autorización explícita + mapa de eventos GFX8 verificado + PRE read-only superado + sanity idle OK.** El plan `03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT/FASE-D-ETAPA-3-PLAN.md` (v1.5, 2026-09-21) define 11 secciones: preguntas Q1–Q8, inventario priorizado A/B/C, semántica por contador (GRBM/GRBMSE/SX/TCC/TCA/CB/DB/MC_ARB directos; SQ/SPI/TCP/TA/TD windowed; SPM EXCLUIDO), mecanismo conceptual de programación+restauración, diseño mínimo (6 corridas intercaladas A/B×3 idénticas a Etapa 2), protocolo PRE/DURANTE/POST, criterios de éxito (H1, H3, H5, geometría-vs-shader, caché-vs-VRAM), criterios de aborto y matriz final. **No ejecutar hasta nueva autorización explícita + PRE read-only superado + sanity idle OK.** Para cuantificar trabajo real de unidades (SQ/CB/DB/MC_ARB/MC_CITF/ATC/CHUB_ATC/GMCON/CP) y caches L1/L2 (TCC directo; TCP/TA/TD solo vía ventana de shader) se requiere programación de contadores (escrituras MMIO) → requiere nueva autorización y política de restauración.

> **↳ RECONCILIACIÓN FASE R-1 (2026-09-23; limita la adenda histórica sin borrarla).**
> La fuente local no verificaba IDs GFX8. GPUPerfAPI aporta un catálogo externo, pero:
> - `v3.11.1` es extracción histórica; `v3.17` es la referencia operativa de tablas.
> - 2304 son filas expuestas, no 2304 eventos únicos/validados.
> - GRBM=2 y SQ=4 son entradas de catálogo, no validación para `1002:699f`.
> - La aritmética vigente es 19/23: 19 coincidencias y 4 discrepancias (CB, SQ, MC, PA_SU).
> - Los rangos son índices de catálogo, no rangos semánticamente seguros.
> - La equivalencia gfx803/gfx804 y la aplicabilidad de instancias por ASIC siguen `UNKNOWN`.
> - La programación de counters permanece **NO AUTORIZADA**.

Investigar subsistemas A–AJ (ver `02-ARQUITECTURA/POLARIS12-MAP/POLARIS12-MAP.md` — tabla maestra de subsistemas) usando fuentes primarias: whitepaper Polaris, GCN whitepaper, GPUOpen, Mesa upstream, kernel amdgpu, Chip and Cheese, RasterGrid, Phoronix, Igor'sLab.

**WORKLOAD-SINTETICO permanece CONGELADO durante toda la auditoría y mapeo.**
