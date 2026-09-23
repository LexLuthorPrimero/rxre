# PLAN MAESTRO — RX 550 al máximo rendimiento medible y reproducible

Fecha: 2026-09-20. Reconstruido a partir del estado real del proyecto y la documentación existente.

**Norte (PROJECT-ROADMAP.md):** no se optimiza el número de watts; se optimizan **FPS/frametime**. Potencia, clocks, MCLK, VRAM y utilización son variables explicativas. Cada etapa y herramienta (BERRETA, Ghost Cache, perfiles) es una **hipótesis sin valor hasta que una medición válida demuestre mejora**.

**Convención de clasificación (heredada de la investigación):**
`[VERIFICADO]` medido/confirmado repetible · `[REPRODUCIBLE]` comportamiento actual estable ·
`[OBSERVADO]` visto al menos una vez · `[NO REPRODUCIBLE]` histórico no reproducible, NO es hecho operacional ·
`[HIPÓTESIS]` candidata sin confirmar · `[DESCARTADO]` refutado con evidencia · `[DESCONOCIDO]` sin explicación.

---

## Arquitectura documental del proyecto

**ESTADO EXPERIMENTAL ACTUAL (fuente viva):**
Consultar **`MASTER-RESEARCH-STATUS.md`**.
Este archivo es la **única fuente de verdad del estado vivo** del proyecto. Este MASTER-PLAN **NO** duplica tablas de estado.

**Nomenclatura (convención):**

- `§A`, `§B`, `§C`, etc. → **secciones estructurales** de este MASTER-PLAN.
- `FASE A`, `FASE B`, `FASE C`, etc. → **fases experimentales/documentales** del proyecto (estado en `MASTER-RESEARCH-STATUS.md`).
- `FASE K`, `FASE L`, ..., `FASE Q` → **fases del roadmap futuro/post-FASE D** (ver §K de este documento).

No se renombran las fases históricas, no se modifican nombres de experimentos existentes y no se rompen referencias históricas. La ambigüedad se resuelve por **contexto explícito**.

**Relación entre ambos documentos:**

```
MASTER-PLAN                          MASTER-RESEARCH-STATUS
  ↓                                        ↓
¿Qué queremos investigar?              ¿Qué hicimos?
¿Por qué?                              ¿Qué observamos?
¿En qué orden?                         ¿Qué reproducimos?
¿Qué dependencias existen?             ¿Qué invalidamos?
¿Qué condiciones deben cumplirse?     ¿Qué está bloqueado?
                                       ¿Qué queda autorizado?
```

**Regla:** `MASTER-PLAN = FUTURO / ESTRUCTURA`. `MASTER-RESEARCH-STATUS = PRESENTE / EVIDENCIA`.

**Regla de actualización futura:**

Cuando se complete un experimento:
1. actualizar `MASTER-RESEARCH-STATUS`;
2. agregar/actualizar los artefactos del experimento;
3. actualizar `MASTER-PLAN` **solamente** si cambia el roadmap, una dependencia, un criterio o un diseño futuro;
4. **NO copiar automáticamente** el nuevo estado experimental a `MASTER-PLAN`.

Esto evita volver a crear dos fuentes de verdad.

---

## Capas del proyecto (independientes)

| Capa | Directorio/Área | Naturaleza |
|---|---|---|
| **rx550-torneo** (Modo Torneo/M1/M2) | `~/Escritorio/RX550_Iterative_Research/rx550-torneo/` + `experiments/` | Laboratorio de medición/control seguro. YA construido (Fases 1–3 + M1). |
| **Workload sintético GPU propio** (rama §J) | Diseño pendiente | Hipótesis: carga GPU representativa, reproducible, parametrizable, ≥27 W potencial. `[HIPÓTESIS]`/DISEÑO PENDIENTE. Separado de rx550-torneo hasta tener evidencia. |
| **BERRETA** | Sin diseño técnico | Hipótesis: aprovechar recursos ociosos con compute/VkLayer. Sin evidencia. |
| **Ghost Cache** | Sin diseño técnico | Hipótesis: caché/prefetch de texturas en VRAM/GTT. Sin evidencia. |
| **Orquestador Final** | `rx550-torneo` (perfiles)+ registro | Integra SOLO optimizaciones con evidencia. Aún sin aplicar. |

Estas capas se mantienen **independientes**: ninguna optimización se integra a otra hasta haber superado su propio gate.

---

> **⚠️ SNAPSHOT HISTÓRICO DEL ROADMAP / ESTADO AL 2026-09-20**
>
> Las secciones **§A–§J** de este documento contienen un **snapshot congelado** del estado/flujo documentado al **2026-09-20**.
> **NO constituyen el estado experimental vivo.** No se deben actualizar manualmente con resultados posteriores (p. ej. los del 21/09).
> Para el **estado actual** consultar **`MASTER-RESEARCH-STATUS.md`** (única fuente de verdad del estado vivo).
> El contenido histórico de §A–§J se conserva intacto; las fases experimentales posteriores a FASE D se describen en §K.

## A. Estado actual (verificado hoy, 2026-09-20)

Sistema vivo (`./rx550-torneo status --json`, read-only):
- RX 550 `1002:699f`, card1, bdf `0000:01:00.0`, amdgpu, hwmon2, renderD129. Display Intel HD 4600 `8086:0412` (card0). cap=`35000000` µW, DPM `auto` (idle `pp_dpm_sclk=0: 214Mhz *`), `power/control=on`, `runtime_status=active`, temp **35.0 °C**, `power1_input` idle 3.67 W, VRAM 5.4 MB / GTT 12.2 MB usados.
- kalm real activo (kalmd.py 4087, kalm-lite.py 4086); `kalm-gpu.service` inactive; Mesa CUSTOM `/opt/mesa-26.2.2-rx550-haswell` presente.
- rx550-torneo: Fase 1 **65/65**, Fase 2 **55/55**, Fase 3 **56/56**, M1 **112/112** checks OK (reejecutados). CLI: `status`, `state-save/show/load`, `verify`, `state-write-test`, `cap-write-test`, `m1-run`, `m1-schedule`.
- RX550_Benchmarks: **GravityMark 1.89**, **Superposition 1.1**, **Heaven 4.0**, **Valley 1.0** descargados (hash SHA-256 verificados) e **instalados exclusivamente en `~/Escritorio/berchmark/instalados/`** (extracción makeself `--noexec`, sin postinstalls). `BENCHMARK-INVENTORY.md` **creado y actualizado**.

M1 (COMPLETADO, **CERRADO / NO DISCRIMINATIVO**; artefactos `runs/20260919-235939` inmutables):
- 10/10 OK, 5×35 W + 5×30 W; `media(power1_input@35W)=12.27 W`; compuerta `<27 W` → **NO DISCRIMINATIVO**. ΔFPS=[0×5], ΔSCLK=[0×5]; ΔPwr IC95% (−0.103, +0.060) W. CV intra-brazo 1.828 %. Sin resets/hangs; stderr vacío (fix HOME/XDG).

Exploraciones previas cerradas (ver `experiments/EXPLORATORIO-GravityMark/runs/`):
- **GravityMark 1.89 (1080p Vulkan): CERRADO / NO DISCRIMINATIVO para M2.** `-asteroids 200k` → carga válida (busy 100 %) pero 12.4 W media / 14.8 W máx, con presión importante de VRAM (2.10/2.00 GB). `-asteroids 4m` → incidente de ejecución (device lost/OOM, 2.86 GB>2 GB), sin medición.
- **Superposition 1.1 (explorado): [VERIFICADO] como ejecución, pero NO DISCRIMINATIVO en la configuración probada.** Motor `superposition` con `-console_command world_load` → benchmark completado (score 804) sin reset/hang; potencia fase activa 18.8 W media / 23.7 W máx < 27 W. Config efectiva 1600x900/Medium/OpenGL (el `superposition_cli` traduce `-quality/-resolution` a XML pero exige `~/.Superposition/license`).

## B. Qué está terminado

1. **Infraestructura de medición/rollback del runner** (Fases 1–3 + M1):
   - gpu_finder por PCI `1002:699f` (nunca asume cardN); separación estricta display/RX550.
   - state_manager (snapshot + hash SHA-256 + persistencia atómica + flock).
   - failsafe/guard: restaura cap/DPM incluso tras SIGKILL; `restore_needed` + boot-service previsto.
   - write-test controlado (máx 2 escrituras, readback obligatorio, node autorizado por PCI).
   - detector reset/hang 7d vía `journalctl -k` (firma inequívoca; excluye PRT/VM-fault benignas).
   - telemetría CSV 10 Hz con ventana estable; detección STOCK/CUSTOM por `/proc/<pid>/maps`.
   - selección GPU: VK = ICD RADV + `MESA_VK_DEVICE_SELECT=1002:699f` + verificación de device `0x699F`; GL = `DRI_PRIME=1`/`1002:699f` + renderer.
   - identidad del workload: nunca corre como root; `HOME`/`XDG_RUNTIME_DIR` del usuario real.
2. **M1 cerrado** con informe, tabla de pares, estadística, anomalías y hashes sha256 de artefactos.
3. **Investigación documental** completa: `knowledge/hypotheses/decisions/open_questions/rejected_ideas/evidence/experiments_proposed/research_log` + `RX550_BUILD_SPECIFICATION.txt` (45 secciones) + backup 17/09.
4. **Descarga, hash e instalación controlada de 4 benchmarks** (GravityMark 1.89, Superposition 1.1, Heaven 4.0, Valley 1.0) en `~/Escritorio/berchmark/instalados/`, y **evaluación exploratoria de GravityMark (200k) y Superposition (motor)** — ambos quedan por debajo de 27 W en la configuración probada.
5. **M2 aún SIN workload discriminativo**: ningún benchmark externo explorado ha superado el umbral de potencia (≈27 W) con cap=35 W en la RX 550.

## C. Qué está en progreso

- **Inventario de benchmarks para M2** → `~/Escritorio/RX550_Benchmarks/BENCHMARK-INVENTORY.md` (creado y actualizado con instalación y resultados exploratorios).
- **Evaluación exploratoria de los 4 benchmarks descargados** (GravityMark, Superposition, Heaven, Valley) → instalación y, para GravityMark y Superposition, medición exploratoria completada; Heaven/Valley quedan pendientes (no autorizados para ejecución, solo instalados).
- Procedencia/descargas/exclusiones ya registradas en `RX550_Benchmarks/docs/` (`SOURCES-AND-EXECUTION.md`, `DOWNLOAD-MANIFEST.sha256`, `README.md`).

## D. Qué está pendiente

1. `[HECHO]` `BENCHMARK-INVENTORY.md` escrito y actualizado (read-only, con registro de instalación autorizada y exploraciones).
2. `[HECHO]` Instalación controlada de 4 benchmarks (GravityMark, Superposition, Heaven, Valley) en `instalados/`.
3. `[SELECCIÓN]` Encontrar un workload (externo restante o **workload sintético propio**) capaz de subir el draw de ~12.3 W hacia **>27 W** con cap=35 W de forma reproducible. Hasta hoy ningún benchmark externo probado lo consigue.
4. `[PENDIENTE]` **Diseño del workload sintético GPU propio** (nueva rama, ver sección J) — HIPÓTESIS/DISEÑO PENDIENTE, sin código.
5. `[AUTORIZADO]` Prueba exploratoria del candidato final (draw real, FPS, temp, repetibilidad, resets).
6. `[AUTORIZADO]` **M2** con `m1-schedule` (5 bloques pareados 35/30) sobre el workload validado.
7. `[AUTORIZADO, opcional]` Perfil experimental (`--danger`): EP-03 (perf stat GL 640p), EP-09 (forcing MCLK/SCLK), EP-07 (re-medir phong).
8. `[PENDIENTE DISEÑO]` BERRETA y Ghost Cache: documento de diseño técnico antes de cualquier código; solo si la evidencia experimental los justifica.

## E. Dependencias entre etapas

```
INVENTARIO (BENCHMARK-INVENTORY.md, read-only) — HECHO
   → SELECCIÓN workload externo (criterio: draw ≥27 W @35 W, repetible) O
        ↓ (si ningún externo sirve) — HECHO: GravityMark/Superposition <27 W
   WORKLOAD SINTÉTICO PROPIO (rama §J: diseño → implementación → validación → selección)
   → PRUEBA EXPLORATORIA (medición autorizada del candidato elegido)
   → M2 (runner m1-schedule; gates = criterios M1)
      → si M2 DISCRIMINA → continuar investigación de potencia/clocks
      → si M2 NO discrimina → cerrar cap-power con los workloads disponibles (conclusión honesta)

BERRETA / GHOST CACHE: SOLO después de (a) caracterizar el cuello de botella real
   (perf stat, forcing MCLK, telemetría busy%) del workload elegido y
   (b) evidencia de recursos ociosos / límite VRAM-GTT. No dependen de M2 para
   existir, pero NINGUNA se adelanta a una medición de cuello de botella.

ORQUESTADOR: solo cuando ≥1 optimización (BERRETA/Ghost Cache/clocks/Mesa) supere
   el gate A/B. No antes.
```

## F. Secuencia exacta de ejecución (desde hoy hasta el sistema final)

1. **Inventario de benchmarks.** Hecho: `BENCHMARK-INVENTORY.md` creado y actualizado (4 benchmarks instalados, registro de instalación autorizada y exploraciones).
2. **Evaluación exploratoria de benchmarks externos.** En curso/parcial hecho: GravityMark 1.89 y Superposition 1.1 evaluados (ambos <27 W en la configuración probada); Heaven 4.0 y Valley 1.0 instalados pero sin ejecución autorizada.
3. **Diseño del workload sintético propio.** Ver rama §J. `[HIPÓTESIS]`/DISEÑO PENDIENTE — sin código.
4. **Implementación y validación del workload sintético.** Solo tras diseño aprobado y autorización; debe pasar los 10 gates de validación de §J.
5. **Selección del workload que pase el gate de potencia/reproducibilidad.** Criterio: draw ≥27 W @35 W, repetible (CV ≤2× intra-brazo), temp <90 °C, sin reset/hang. Puede ser un externo restante o el sintético propio.
6. **M2 formal 35 W vs 30 W.** `sudo ./rx550-torneo m1-schedule --confirm --blocks 5 --arms 35000000 30000000 --duration 25 --out DIR` sobre el workload validado; análisis con compuerta/criterios de M1 → cerrar M2 (informe + hashes) o re-seleccionar workload.
7. **Análisis de bottleneck.** Caracterizar el cuello de botella del workload ganador (perf stat read-only si se autoriza; forcing MCLK solo con `--danger`; telemetría busy%).
8. **BERRETA / Ghost Cache solo si la evidencia experimental los justifica.** Redactar diseño (capas Vulkan/ACE/compute; TTM/GTT/PCIe-SDMA/prefetch) → A/B aislado con gate. No se inician basándose solo en la existencia del workload sintético (§J).
9. **Orquestador final únicamente después de una optimización VERIFICADA.** Registrar las optimizaciones que hayan pasado el gate en perfiles activables/desactivables, con activación por perfil/run, rollback garantizado (state_manager+failsafe), verificación de GPU antes de cada corrida, bloqueo de cambios incompatibles (lista blanca BUILD_SPEC §17 vs prohibidos §18), y registro de resultados (`actions.log`, `runs/<id>`, `RESULTADOS-*.md`).

## G. Criterios de aceptación/rechazo por etapa

| Etapa | Aceptar | Rechazar |
|---|---|---|
| Inventario | 20 campos/candidato, categorías A–E, disponibilidad real, riesgos, reproducibilidad | Datos no verificados presentados como hechos; sin prioritarios útiles |
| Selección workload | draw ≥27 W @35 W; repetible (CV ≤2× intra-brazo); temp <90 °C; sin reset/hang | draw <27 W (como M1); no repetible; reset/hang |
| Prueba exploratoria | medición completa (draw, FPS, temp, busy%, resets), restauración verificada | cualquier write sin snapshot/readback/rollback; sin verificación de GPU |
| M2 | compuerta **abierta** (media draw @35 W ≥27 W) y, si liga, criterio M1 (Δ con IC95% excluyendo 0 y ≥2×CV, signo ≥4/5) | compuerta activada (<27 W) → NO DISCRIMINATIVO; no reproducible |
| BERRETA / Ghost Cache | ΔFPS ≥2×CV intra-brazo, IC95% excluye 0, A/B pareado, reversible, GPU verificada | falso positivo por ruido; no reversible; no se distingue GPU |
| Orquestador | solo optimizaciones con evidencia; rollback verificado; GPU verificada por corrida; registro completo | activar hipótesis sin gate; cambios globales no reversibles |

## H. Riesgos conocidos

- **El régimen histórico 25–31 W / MCLK 1250–1500 / 74–92 °C es [NO REPRODUCIBLE]** (17/09). Ningún benchmark explorado (GravityMark 200k: 12.4–14.8 W; Superposition motor: 18.8–23.7 W a 1600x900/Medium) ha alcanzado aún ≥27 W en la sesión actual → riesgo de no encontrar workload discriminativo sin el sintético propio.
- Perfil experimental (`--danger`): riesgo térmico (aborto ≥90 °C), reset/hang del kernel (detector 7d activo), artefacto "pinned at cap" del estimador SMU.
- BERRETA/Ghost Cache sin diseño técnico ni evidencia → riesgo de invertir tiempo en una idea no realizable (advertencia explícita en PROJECT-ROADMAP §10-11).
- kalm activo: no tocar; puede mediar el régimen sin que lo controlemos.
- Display en Intel: cualquier corrida debe re-verificar que la RX 550 no tome display (failsafe).
- Instaladores propietarios (GravityMark, UNIGINE) requieren revisión de licencia por una persona antes de ejecutarse.

## I. Qué NO debemos hacer todavía

- No escribir `power1_cap` ni DPM/SCLK/MCLK fuera de una corrida autorizada con snapshot+readback+restore.
- No instalar ni ejecutar benchmarks/instaladores (GravityMark `.run`, UNIGINE, RPM) sin autorización explícita y revisión de licencia.
- No modificar `rx550-torneo`, artefactos M1 (`runs/20260919-235939`), Mesa del sistema, `/opt/mesa-...`, kalm, GRUB/kernel/DRM.
- No diseñar ni implementar BERRETA ni Ghost Cache: falta (a) caracterizar cuello de botella y (b) documento de diseño.
- No escribir código del workload sintético en esta fase: es `[HIPÓTESIS]`/DISEÑO PENDIENTE (§J); la implementación solo tras diseño y autorización.
- No adoptar el régimen histórico 17/09 como especificación de rendimiento ([NO REPRODUCIBLE]).

---

## J. Workload sintético GPU propio (nueva rama de investigación)

**Estado inicial: `[HIPÓTESIS]` / DISEÑO PENDIENTE.** El workload NO existe aún y NO se afirma que será capaz de alcanzar 27–35 W. Esta sección formaliza la rama para desarrollarlo posteriormente, sin escribir código ni crear archivos de implementación en esta fase.

### Propósito
Desarrollar posteriormente un workload GPU controlado y reproducible específicamente para investigación de la RX 550, porque los benchmarks externos probados hasta ahora no han conseguido generar una carga suficientemente alta y estable para hacer discriminativo el cap de 30/35 W.

### Motivación experimental documentada
- **M1 con vkmark:** ~12.27 W → NO DISCRIMINATIVO.
- **GravityMark 1.89 a 1080p:** carga válida, pero ~12.4 W media / 14.8 W máxima; además mostró presión importante de VRAM.
- **Superposition 1.1 en la configuración explorada:** ~18.8 W durante fase activa / 23.7 W máximo; GPU busy 100 %, sin superar el umbral de ~27 W.
- Por lo tanto, **todavía no existe un workload reproducible que haya demostrado hacer intervenir el cap de 30/35 W**.

### Objetivo del nuevo workload
No debe diseñarse simplemente para "hacer consumir 35 W". Debe generar una carga GPU técnicamente representativa, reproducible y parametrizable, con VRAM controlada, para poder medir:
- potencia · rendimiento/throughput o FPS · frametime si corresponde · SCLK · MCLK · GPU busy · VRAM/GTT · temperatura · estabilidad.

### Hipótesis de diseño
Investigar primero qué API y patrón de carga son adecuados para Polaris12/RADV en esta RX 550. Evaluar, sin asumir de antemano:
- cómputo GPU · operaciones ALU/FLOP · presión de memoria · bandwidth · shaders/fragmentos · diferentes mezclas de carga · posibilidad de parametrizar intensidad y duración.
- **No asumir que un único tipo de carga será óptimo.**

### Arquitectura conceptual futura
```
workload sintético
  → selección explícita RX 550
  → intensidad configurable
  → duración configurable
  → telemetría
  → resultado reproducible
```
Debe permanecer **separado de rx550-torneo** hasta que exista evidencia experimental suficiente.

### Gates de validación
1. Compilación/ejecución limpia.
2. Selección inequívoca de RX 550 `0x699f`.
3. Sin modificación de configuración permanente del sistema.
4. Sin forzar SCLK/MCLK/DPM.
5. Sin tocar Kalm.
6. Sin crashes, GPU reset, hang o OOM.
7. Temperatura estable y dentro de límites seguros.
8. Consumo reproducible.
9. Idealmente alcanzar **≥27 W de manera sostenida con cap=35 W**.
10. Repetibilidad suficiente para poder usarlo posteriormente en A/B.

### Clasificación esperada
`HIPÓTESIS → DISEÑO → IMPLEMENTACIÓN → VALIDACIÓN → REPRODUCIBLE → CANDIDATO M2`
- Si no consigue superar ~27 W → **NO DISCRIMINATIVO para M2**.
- Si provoca OOM/crash/reset → **DESCARTADO o REDISEÑO**, según causa.

### Relación con M2
El workload sintético **NO reemplaza automáticamente M2**. Primero debe pasar la fase exploratoria. Solo si demuestra carga estable ≥27 W y reproducibilidad, se autoriza formalmente el protocolo M2 35 W vs 30 W.

### Relación con BERRETA y Ghost Cache
**No iniciar BERRETA ni Ghost Cache basándose solamente en la existencia del workload sintético.** El workload puede utilizarse posteriormente como herramienta de caracterización, pero las hipótesis de bottleneck deben demostrarse mediante mediciones.

---

## Contradicciones documentales detectadas (se usa la evidencia más reciente)

1. **`MESA_VK_DEVICE_SELECT=1002:699f`**: `knowledge.md`/BUILD_SPEC §29 lo marcaban "roto, elige iGPU"; `README-FASE1.md` (Fase 1.1) registra lo contrario ("deja la RX 550 primera, observado 09-19") y **M1 lo usó con éxito** (10/10, device correcto). Uso vigente: selector + `VK_ICD_FILENAMES` + **verificación de device `0x699F` en cada corrida** (el runner ya lo valida).
2. **Banner "no autorizado todavía" en `README-M1.md`**: desactualizado; M1 fue autorizado y ejecutado. Fuente de verdad = `RESULTADOS-M1.md` + artefactos (`audit.json`, `telemetry.csv`, `stdout.txt`).
3. **FPS históricos (1285 phong, 443 desktop@1080, jelly 691@35 W)**: [NO REPRODUCIBLE]; no usar como meta de rendimiento.

---

## Estado: hecho vs hipótesis vs pendiente

- **HECHOS medidos:** runner construido y probado (65/55/56/112); M1 cerrado (draw 12.27 W, NO DISCRIMINATIVO); estado del sistema verificado hoy; máximos draw 13.6 W (EP-06); cuello de botella no-SCLK en GL 640p; GravityMark 200k → 12.4/14.8 W (busy 100%, VRAM 2.10 GB, sin reset); Superposition motor → 18.8/23.7 W, score 804, sin reset.
- **HIPÓTESIS sin evidencia:** BERRETA (compute en recursos ociosos vía VkLayer/ACE); Ghost Cache (prefetch/caché texturas en VRAM/GTT, TTM/GTT/PCIe-SDMA); cualquier tuner de power/clocks; valor de la Mesa CUSTOM; **workload sintético propio capaz de ≥27 W en RX 550 (DISEÑO PENDIENTE)**.
- **PENDIENTE:** selección/validación de workload para M2 (externo restante o sintético); diseño e implementación del workload sintético (§J); M2; análisis de bottleneck; BERRETA/Ghost Cache solo si la evidencia los justifica; orquestador final.

---

## K. Roadmap post-FASE D — FASE K/L/M/N/O/P/Q + Ecosistema RX 550/Polaris (PLANIFICADAS, FUTURO)

Integrado el 2026-09-21 y ampliado el mismo día con la FASE N (nomenclatura), la arquitectura conceptual del ecosistema, el inventario inicial y el principio fundamental. Extendido el mismo 2026-09-21 con las FASE O (GPU Control & Orchestration Research), P (Frame Generation & Upscaling Research) y Q (Mesa Polaris12 Optimization Research), el Protocolo transversal de GPU Ownership y la ampliación de FASE L y FASE M. **Ninguna de estas fases está ejecutada; no se ha creado ningún experimento; ninguna hipótesis se presenta como resultado experimental.**

### Reglas de esta sección

- **Estado: PLANIFICADA / FUTURA** en las fases K/Q (K, L, M, N, O, P, Q). Requieren autorización explícita y diseño previo antes de crearse ninguno de sus experimentos. O, P y Q son líneas de investigación documental (RESEARCH).
- **Nomenclatura (mapeo):** la línea fue definida el 2026-09-21 como «FASE E/F/G». Al integrarse al plan maestro se renombra para no colisionar con las FASE E–J ya registradas y pendientes (Real-Game Baseline, Geometry Investigation, Memory/VRAM/GTT, RADV/Workarounds, PowerPlay/DPM, Priority Matrix), que permanecen intactas:

  | Propuesta original (2026-09-21) | Nombre definitivo en el plan |
  |---|---|
  | FASE E — POLARIS12 PERFORMANCE LABORATORY | **FASE K** |
  | FASE F — RX550-TUNER | **FASE L** |
  | FASE G — GFX8 COUNTER RESEARCH | **FASE M** |

- **FASE A, B, C y D permanecen intactas**, incluidas sus conclusiones y resultados numéricos. FASE D sigue figurando completada hasta su estado actual: **auditoría read-only completada; Event IDs GFX8 inicialmente no verificados con fuentes locales → RESUELTO documentalmente por FASE R-0 (GPUPerfAPI v3.11.1, R0-1) y reconciliado en FASE R-1 (R1-1)**; programación de contadores NO autorizada.
- Todo ejecución futura hereda las restricciones operacionales de FASE D: no tocar `rx550-torneo` congelado, Mesa sistema/`/opt/mesa-...`, kalm, kernel/GRUB/DRM, sysfs permanente; todos los escritos de registros/contadores/PowerPlay requieren autorización + snapshot/readback/restore + gates de reproducibilidad.
- La **Capa Transversal — KERNEL / DRIVER COMPATIBILITY & EDGE-CASE LAYER** (sección final de este documento) aplica a las fases K/Q (principalmente K, L, O y Q, y **parcialmente M**). **No es una FASE.**
- Cada fase §K–§Q expresa: **OBJETIVO · DEPENDENCIAS · PREGUNTAS · METODOLOGÍA · GATES · RIESGOS · CRITERIOS DE SALIDA**. NO repiten innecesariamente resultados experimentales ya contenidos en `MASTER-RESEARCH-STATUS.md`: para el estado de cada experimento/fase se consulta `MASTER-RESEARCH-STATUS.md`.

### FASE K — POLARIS12 PERFORMANCE LABORATORY (PLANIFICADA)

Propósito: transformar el trabajo acumulado de FASE A–D en un framework reproducible para caracterizar, experimentar y analizar el comportamiento de GPUs AMD Polaris/GFX8 bajo Linux.

- **K1 — Framework experimental:** estructura común para experimentos; identificación de GPU/API/driver/benchmark; parámetros y condiciones controladas; registro de configuración y estado previo/posterior.
- **K2 — Telemetría unificada:** integrar en una estructura común, **cuando estén disponibles**: SCLK, MCLK, GPU busy, memory busy, temperatura, `power1_input`, VRAM utilizada, radeontop, UMR, información de Mesa, FPS/score, duración, API utilizada y benchmark utilizado.
- **K3 — Benchmarks reproducibles:** ejecuciones A/B intercaladas; réplicas múltiples; ventanas *steady* claramente definidas; métricas normalizadas; **preservar los criterios de reproducibilidad utilizados en FASE D**.
- **K4 — Clasificación de bottlenecks:** investigar y clasificar experimentalmente escenarios como shader/ALU bound, geometry/vertex bound, raster/ROP bound, texture/fetch bound, memory/VRAM bound, latency bound y clock/power limited. La clasificación debe distinguir: **(1) observación directa → (2) correlación → (3) hipótesis → (4) evidencia causal**. **No presentar una correlación como causalidad.**
- **K5 — Experimentos de shader:** basados en los candidatos ya identificados en `experiments/POLARIS12-MAP/POLARIS12-MAP.md`: SHD-01, SHD-02, FRAG-01, FRAG-02.
- **K6 — Experimentos de geometría:** GEO-01, GEO-02, GEO-04.
- **K7 — Experimentos de memoria:** MEM-01, MEM-03.
- **K8 — Análisis automático (SOLO PLANIFICADO, no implementar):** diseñar posteriormente un analizador que reciba los resultados de los experimentos y produzca resumen de métricas, comparación A/B, diferencias porcentuales, detección de cambios de comportamiento, clasificación tentativa del bottleneck, nivel de evidencia e hipótesis pendientes de prueba. El plan actual no tiene una sección explícita para ese analizador, por lo que en esta revisión **únicamente se planifica; no se implementa nada.**
- **K9 — Telemetría unificada + Observability Perturbation + modos de telemetría:** integrar el concepto transversal de perturbación de la observación y los modos `TELEMETRY_MODE=MINIMAL / STANDARD / COUNTER / DIAGNOSTIC`; el benchmark principal debe usar el modo menos perturbador que permita medir las variables necesarias (ver Capa Transversal §9).
- **K10 — Capability Matrix:** aplicar a la caracterización experimental la matriz `CAPABILITY → DOCUMENTED → PRESENT → READABLE → WRITABLE → EFFECTIVE → REVERSIBLE → BENCHMARK-SAFE` (ver Capa Transversal §11).

### FASE L — RX550-TUNER (PLANIFICADA, dependiente de FASE K)

Propósito: construir sobre el laboratorio de FASE K un sistema de búsqueda experimental de configuraciones de PowerPlay/perfiles para la RX 550. Debe contemplar conceptualmente: perfiles de potencia, límites de potencia, clocks, benchmarks, búsqueda controlada, comparación estadística, validación y reversibilidad.

**NO implementar FASE L ahora.** Depende de FASE K (framework + telemetría + benchmark reproducible). Toda escritura de PowerPlay/sysfs seguirá sujeta a autorización explícita, snapshot/readback/restore y gates de FASE D.

Áreas futuras posibles (investigación/planificación, no autorizadas): PowerPlay; DPM; runtime-PM; perfiles; control de potencia; clocks; ownership; integración o interoperabilidad con herramientas externas (en el marco del Protocolo GPU Ownership, ver FASE O); y, eventualmente, investigación de BIOS/PowerPlay table.

**BIOS modification queda exclusivamente como investigación futura de alto riesgo.** No autoriza: flasheo; modificación de VBIOS; escritura de tablas; ni overdrive irreversible. Antes de cualquier operación de ese tipo deberá existir una fase independiente de auditoría, backup, validación y rollback. Herramientas históricas como Polaris BIOS Editor o MorePowerTool pueden investigarse documentalmente, pero **no asumir compatibilidad con el sistema actual hasta verificarla**.

Ampliaciones de robustez (relacionadas con la Capa Transversal, sección final de este documento):

- **L.0 — Capability Audit (ppfeaturemask):** antes de cualquier investigación de OverDrive se auditará el `ppfeaturemask` actual: leer el valor; identificar qué bits están activos; comprobar si `PP_OVERDRIVE_MASK = 0x4000` está habilitado; documentar el valor original; documentar qué cambiaría si se habilitara; y determinar si requiere modificación del parámetro de kernel + reinicio. **NO modificar todavía.** El paso 0 NO es «establecer 0x4000»: es **verificar si 0x4000 está disponible/habilitado y estudiar el mecanismo necesario para habilitarlo**. La modificación queda fuera del experimento documental hasta autorización explícita. `PP_OVERDRIVE_MASK=0x4000` es la definición del kernel, pero la disponibilidad efectiva de la interfaz debe comprobarse en la plataforma concreta (ver Capa Transversal §4).
- **pp_od_clk_voltage (objeto de investigación independiente):** investigar disponibilidad en Polaris12, formato, estados SCLK, estados MCLK, rangos, voltajes, modo manual, commit, reset, interacción con DPM, interacción con power cap, persistencia, restauración, comportamiento después de runtime-PM y después de suspensión/resume. La documentación genérica del kernel NO implica capacidad confirmada en RX 550 — **DOCUMENTACIÓN GENÉRICA ≠ CAPACIDAD CONFIRMADA EN RX550** (ver Capa Transversal §5).
- **Known/Reported Polaris DPM Edge Cases (CLAIM TO VERIFY):** investigar la afirmación de que en determinadas versiones/configuraciones de Polaris `pp_dpm_sclk` acepta una escritura a nivel de sysfs aunque el resultado efectivo en firmware/SMU no corresponda a lo solicitado. **NO registrar todavía como hecho universal; clasificar inicialmente como CLAIM TO VERIFY.** Buscar: versión del kernel, ASIC, driver, método de escritura, código del kernel, mensajes del kernel, readback, clock observado y casos reproducibles. Regla: **WRITE SUCCESS ≠ STATE CHANGE VERIFIED**; toda operación futura seguirá `write → readback de interfaz → observación efectiva del estado → validación temporal → conclusión` (ver Capa Transversal §6).
- **pp_table (distinción de mecanismos):** no afirmar prematuramente «pp_table runtime no funciona en Polaris». La disponibilidad y semántica efectiva dependen de la arquitectura/driver; para Polaris12 debe medirse y documentarse primero, clasificando: disponible / lectura disponible / escritura disponible / escritura rechazada / no expuesta / no verificada. NO confundir: (1) `pp_table` runtime del driver; (2) PowerPlay table almacenada/derivada del firmware/VBIOS; (3) modificación del VBIOS; (4) `pp_od_clk_voltage` (ver Capa Transversal §7).
- **VBIOS (frontera de alto riesgo): VBIOS MODIFICATION = HIGH RISK / OUTSIDE NORMAL EXPERIMENT LOOP.** No realizar flash, modificación, escritura, parcheo ni overdrive persistente sin una fase posterior específica de recuperación y validación (ver Capa Transversal §8).
- **Identificación por PCI (requisito de robustez):** no depender exclusivamente de `/sys/class/drm/card1`; preferir identificar la GPU por `vendor + device + PCI BDF` y resolver dinámicamente el nodo sysfs. Queda como requisito de robustez, no necesariamente como implementación inmediata (ver Capa Transversal §3).
- **Experimental Safety Gate:** antes de cualquier modificación futura de PowerPlay/OverDrive/Mesa/contadores, pasar el checklist completo con ABORT si algún ítem falla (ver Capa Transversal §12).

### FASE M — GFX8 COUNTER RESEARCH (PLANIFICADA, independiente)

Propósito: investigar fuentes históricas/primarias que permitan recuperar Event IDs auténticos para GFX8/Polaris12 y desbloquear potencialmente la instrumentación de contadores de rendimiento. El objetivo de M es obtener **evidencia primaria o equivalente** antes de cualquier programación.

Alcance de la investigación (todo documental): UMR; GPUPerfAPI histórico; CodeXL histórico; documentación de AMD; documentación histórica de GCN/GFX8; Radeon GPU Profiler y herramientas históricas equivalentes cuando sean relevantes; tablas históricas de Event IDs; mecanismos de selección de contadores; y diferencias de selección entre generaciones GFX8/GFX10/GFX11.

Queda explícitamente documentado:

- La auditoría local de Event IDs GFX8 concluyó que las fuentes locales disponibles **NO permiten verificar los IDs** (`experiments/FASE-D-COUNTERS-AUDIT/FASE-D-GFX8-EVENT-ID-AUDIT.md`) — **pero** la **FASE R-0 (R0-1, GPUPerfAPI v3.11.1) resolvió ese bloqueo documentalmente**: catálogo GFX8 completo con nombres+valores recuperado y verificado (GRBM GUI_ACTIVE=2, SQ WAVES=4). La **FASE R-1 (R1-1)** reconcilió los conteos CB/SQ/MC (396/405, 299/273, 33/22 → PARTIALLY_RECONCILED). Ver adenda §14 de la auditoría.
- **NO afirmar que UMR es «la única vía»** para obtener los Event IDs.
- **NO afirmar que una versión moderna de GPUPerfAPI/RGP soporta Polaris12.** **RESUELTO parcialmente:** la **versión histórica GPUPerfAPI v3.11.1 SÍ soporta GFX8** (incluida Polaris); **v4.0+ lo ELIMINÓ** (por eso debe usarse v3.11.1). Cualquier otra afirmación de soporte de versiones debe verificarse igualmente antes de afirmar.
- Los valores modernos de GFX10/GFX11 **NO deben portarse automáticamente a GFX8**.
- `GRBM_PERFCOUNTER0_SELECT=0x2` **ahora tiene evidencia documental válida para GFX8** (GUI_ACTIVE en catálogo AMD v3.11.1) → el bloqueo *científico* queda **eliminado documentalmente**; la **escritura sigue NO AUTORIZADA** (requiere nueva autorización explícita + PRE + sanity).
- `SQ PERF_SEL=0x4` **verificado para GFX8** (sub-bloques Sq/Cs/Es/Gs/Hs/Ls/Ps/Vs).
- **No realizar programación de contadores hasta disponer de IDs verificados** → **IDs YA disponibles documentalmente (R-0)**, la programación permanece NO AUTORIZADA.
- **Ampliación de robustez (parcial, Capa Transversal):** comparación histórica de herramientas (fuente de datos; ioctl/sysfs/debugfs utilizado; si requiere root; si modifica estado; si puede despertar la GPU; si puede impedir runtime-PM; resolución temporal; métricas disponibles; compatibilidad con Polaris12; coste de observación; reproducibilidad) y estudio del **overhead/perturbación de la medición de contadores** (Observability Perturbation, ver Capa Transversal §1 y §9): **OBSERVADOR ≠ PASIVO AUTOMÁTICAMENTE** (p. ej. leer GRBM/GRBM2 puede desactivar funciones de power saving).

Estado: **PLANIFICADA** (parcialmente resuelta por FASE R-0/R-1; queda transformar la investigación en opcional), independiente de FASE K/L/O/P/Q.

> **↳ nota FASE R-1 (2026-09-22):** dado que R-0 resolvió el propósito de FASE M a nivel documental, FASE M pasa a
> ser opcional/de consolidación (cruzada con R1-1 para CB/SQ/MC y sus diferencias de rango). Ver
> `experiments/FASE-R1-DOCUMENTATION-RECONCILIATION/R1-1-GFX8-EVENT-RECONCILIATION.md`.

### FASE N — TECHNOLOGY NAMING & ARCHITECTURE (PLANIFICADA / DOCUMENTAL)

Estado: **PLANIFICADA / DOCUMENTAL**. No se implementa ninguna tecnología como parte de esta fase.

Objetivo: crear una nomenclatura oficial para todo el ecosistema y resolver la arquitectura documental (proyectos, tecnologías, frameworks, herramientas, motores, perfiles, experimentos, investigaciones, benchmarks y documentación no deben mezclarse).

Proceso (en este orden):
1. **Inventario** de todos los elementos del ecosistema.
2. **Clasificación** de cada elemento como: `proyecto`, `tecnología`, `framework`, `herramienta`, `motor`, `perfil`, `experimento`, `investigación`, `benchmark` o `documentación`.
3. **Propuesta de nombres** y tabla final: `Nombre oficial | tipo | objetivo | estado | dependencia | alias/nombre anterior`.

Reglas:
- **No cambiar automáticamente** los nombres existentes con identidad propia (Ghost Cache, BERRETA, Modo Torneo, RX550-Tuner). Conservarlos salvo decisión explícita de renombrar.
- **No inventar nombres definitivos** para tecnologías todavía no suficientemente definidas (p. ej. RX Compression Engine permanece como nombre provisional).
- **Ghost vs BERRETA:** son entradas separadas en la documentación existente (tabla de capas del proyecto, líneas 18–22). El nombre histórico documentado de la línea de memoria es **Ghost Cache**; el nombre «Ghost Berreta» **no aparece** en la documentación existente y **no hay relación documentada** Ghost↔BERRETA. No se asume fusión ni relación hasta revisar documentación que lo respalde.

### FASE O — GPU CONTROL & ORCHESTRATION RESEARCH (PLANIFICADA / INVESTIGACIÓN)

Estado: **PLANIFICADA / FUTURA** (línea de investigación documental).

Objetivo: investigar las herramientas y mecanismos existentes para controlar GPUs AMD bajo Linux y determinar qué funciones conviene implementar nosotros mismos y cuáles es mejor reutilizar o tomar como referencia.

Ámbitos a investigar documentalmente: **LACT**; **CoreCtrl**; **amdgpu-clocks**; interfaces sysfs/amdgpu; PowerPlay; DPM; runtime-PM; perfiles de GPU; mecanismos de restauración; mecanismos de ownership/control exclusivo.

Preguntas de la investigación:
1. ¿Qué capacidades ya resuelven estas herramientas?
2. ¿Qué partes son reutilizables conceptualmente?
3. ¿Qué partes de rx550-torneo conviene mantener?
4. ¿Qué partes no conviene reinventar?
5. ¿Qué diferencias existen entre una herramienta generalista y una herramienta experimental específica para RX 550?
6. ¿Cómo garantizar reversibilidad?
7. ¿Cómo evitar carreras entre gestores de GPU?

IMPORTANTE: **no reemplazar rx550-torneo automáticamente** por LACT/CoreCtrl/amdgpu-clocks. Primero comparar capacidades. El objetivo es decidir posteriormente si: **reutilizamos**, **integramos**, **tomamos ideas** o **mantenemos nuestra implementación independiente**. Ninguna de esas herramientas es una solución adoptada; son **objetos de evaluación**.

Ampliaciones (Capa Transversal, sección final de este documento):

- **Comparación formal LACT vs rx550-torneo** (→ **DECISIÓN DOCUMENTAL**, no implementación automática): power cap; performance level; DPM; clocks; voltajes; overdrive; perfiles; persistencia; restauración; detección de hardware; multi-GPU; runtime-PM; seguridad; rollback; interfaz; automatización; dependencia de versiones del kernel; compatibilidad Polaris12. Pregunta correcta 1: **«¿Qué problema resuelve LACT que rx550-torneo no debería reinventar?»** Pregunta correcta 2: **«¿Qué requisitos experimentales de rx550-torneo hacen que una herramienta generalista no sea suficiente?»** (ver Capa Transversal §2).
- **amdgpu-clocks como referencia arquitectónica:** leer `ppfeaturemask`, comprobar OverDrive, `pp_od_clk_voltage`, FORCE_SCLK, FORCE_MCLK, FORCE_POWER_CAP, FORCE_PERF_LEVEL, FORCE_POWER_PROFILE, restauración, e **identificación por PCI frente a cardX** como patrón preferido (ver Capa Transversal §3).
- **Telemetría a evaluar (ampliada):** `radeontop`, `amdgpu_top`, `UMR`, `perf`, herramientas basadas en `fdinfo`, `gpu_metrics` y `sysfs/hwmon`, con registro por herramienta (fuente de datos, ioctl/sysfs/debugfs, root, modificación de estado, despertar GPU, bloqueo de runtime-PM, resolución temporal, métricas, compatibilidad Polaris12, coste de observación, reproducibilidad) y **clasificación A/B/C/D de perturbación** (ver Capa Transversal §1).
- **Detección de gestores externos y ownership:** integrar la detección de herramientas externas y la adquisición de ownership en el Protocolo GPU Ownership, con comparación de capacidades (ver Capa Transversal §11 y §12).

### PROTOCOLO TRANSVERSAL — GPU OWNERSHIP

Definir un protocolo general para cualquier herramienta externa que pueda modificar el estado de la GPU. Conceptualmente:

```
detectar gestor externo
→ verificar estado
→ adquirir ownership/control temporal
→ ejecutar experimento
→ restaurar estado original
→ liberar ownership
→ verificar restauración
```

Aplicarlo posteriormente a gestores como Kalm **si realmente están activos**.

IMPORTANTE:
- **No asumir que Kalm está actualmente activo.** El estado de Kalm debe verificarse en el momento de cada experimento.
- La auditoría histórica ya estableció que Kalm **NO fue la causa** del régimen histórico de 25 W (ver `MASTER-RESEARCH-STATUS.md` → QUÉ FUE INVALIDADO).

### FASE P — FRAME GENERATION & UPSCALING RESEARCH (PLANIFICADA / INVESTIGACIÓN)

Estado: **PLANIFICADA / FUTURA** (línea de investigación documental).

Objetivo: investigar tecnologías que puedan mejorar la **experiencia percibida** en GPUs de gama baja **sin confundirlas** con una mejora del rendimiento de renderizado real.

Ámbitos a investigar: **lsfg-vk**; **FSR**; upscaling; frame generation; Vulkan layers; técnicas de inyección/interposición; coste computacional; latencia; calidad visual; compatibilidad con Polaris12/RX 550.

Separación estricta de métricas (obligatoria): 
- **RENDIMIENTO REAL** → FPS producidos por el renderizado.
- **RENDIMIENTO PERCIBIDO** → FPS adicionales producidos mediante frame generation.
- **Nunca mezclar ambas métricas en los benchmarks principales del Polaris Performance Laboratory.**

Preguntas:
- ¿Puede ejecutarse en RX 550?
- ¿Cuál es el coste GPU/CPU?
- ¿Cuánta memoria utiliza?
- ¿Cuál es la latencia adicional?
- ¿Cuándo empeora realmente la experiencia?
- ¿Puede ser útil en determinados juegos?
- ¿Puede combinarse con upscaling?
- ¿Qué resolución interna resulta óptima?

**No asumir que frame generation mejora la experiencia.** Debe demostrarse mediante experimentos posteriores.

FASE P se mantiene sin cambios en su alcance: separación estricta de FPS reales vs FPS generados, y dimensiones de latencia, coste, calidad y compatibilidad (ver Capa Transversal §14).

### FASE Q — MESA POLARIS12 OPTIMIZATION RESEARCH (PLANIFICADA / INVESTIGACIÓN)

Estado: **PLANIFICADA / FUTURA** (línea de investigación documental).

Objetivo: investigar oportunidades de optimización específicas de Polaris12 dentro de Mesa/radeonsi/RADV **sin asumir que una modificación del driver producirá beneficios**.

Áreas: workarounds específicos de Polaris12; optimizaciones radeonsi; optimizaciones RADV; diferencias OpenGL/radeonsi vs Vulkan/RADV; compilación de shaders; scheduling; wave32/wave64 cuando corresponda; geometry; rasterización; memoria; cache; sincronización; posibles optimizaciones upstream; posibles optimizaciones experimentales locales.

Para cada oportunidad, el pipeline de evidencia es:

```
OBSERVACIÓN → HIPÓTESIS → CAMBIO AISLADO → A/B → RÉPLICAS → MEDICIÓN → VALIDACIÓN → ACEPTAR / RECHAZAR
```

- **Nunca introducir múltiples cambios simultáneamente** si el objetivo es determinar causalidad.
- Cualquier modificación de Mesa deberá realizarse **únicamente en una etapa experimental futura** y con **rollback claramente definido**.

Ampliaciones de robustez (Capa Transversal, sección final de este documento):

- **Matrices de versiones:** registrar en cada experimento la matriz kernel/driver y la matriz Mesa; toda afirmación dependiente de una versión concreta (kernel, Mesa, firmware o herramienta) debe registrar esa versión.
- **Detección de regresiones:** al cambiar de versión, comparar contra la línea base registrada para detectar regresiones.
- **Reproducibilidad y rollback:** mantener reproducibilidad y rollback definido para cualquier experimento de Mesa (ver Capa Transversal §11 y §15).

### Ecosistema RX 550 / Polaris — arquitectura conceptual

Estructura conceptual (no implica crear directorios ni implementaciones todavía):

```
RX 550 / POLARIS ECOSYSTEM
│
├── Polaris Performance Laboratory (FASE K)
│   ├── framework experimental
│   ├── telemetría
│   ├── benchmarks
│   ├── diagnóstico
│   └── análisis
│
├── RX550-Tuner (FASE L)
│   └── optimización experimental
│
├── Ghost Cache (investigación de memoria)
│   └── GTT/TTM, prefetch, VRAM
│
├── BERRETA
│   └── investigación Vulkan / compute / ACE
│
├── RX Compression Engine (nombre provisional)
│   └── compresión/descompresión especializada
│
├── GFX8 Counter Research (FASE M)
│   └── investigación de contadores
│
├── Technology Naming & Architecture (FASE N)
│   └── nomenclatura y arquitectura documental
│
├── GPU Control & Orchestration Research (FASE O)
│   └── herramientas de control AMD + Protocolo GPU Ownership
│
├── Frame Generation & Upscaling Research (FASE P)
│   └── lsfg-vk, FSR, frame generation, upscaling
│
└── Mesa Polaris12 Optimization Research (FASE Q)
    └── radeonsi/RADV, workarounds, shaders, scheduling
```

Nota: el árbol es conceptual. Ghost Cache y BERRETA se mantienen como ramas separadas (no se fusionan).

### Inventario inicial del ecosistema (clasificado)

El `Tipo` de cada elemento se respeta en las menciones futuras para no mezclar proyectos, tecnologías, frameworks, herramientas, perfiles, experimentos, investigaciones, benchmarks y documentación.

| Nombre (actual) | Tipo | Objetivo (documentado) | Estado | Dependencia | Alias / anterior |
|---|---|---|---|---|---|
| rx550-torneo / Modo Torneo | Herramienta/framework (runner de medición y control) | Laboratorio seguro: detección GPU por PCI, snapshot/hash/rollback, failsafe, telemetría 10 Hz, perfiles, M1/M2 | CONSTRUIDO (Fases 1–3: 65/55/56; M1: 112) | — | Modo Torneo; M1/M2 |
| Workload sintético GPU propio | Proyecto/experimento (rama §J) | Carga GPU representativa, reproducible, parametrizable; idealmente ≥27 W @35 W | HIPÓTESIS / DISEÑO PENDIENTE | para M2 | §J |
| Polaris Performance Laboratory | Framework (FASE K) | Caracterizar, experimentar y analizar Polaris/GFX8 de forma reproducible | PLANIFICADA / FUTURA | FASE A–D | E→K |
| RX550-Tuner | Proyecto/tecnología (FASE L) | Búsqueda experimental de perfiles de potencia, límites, clocks y DPM | PLANIFICADA / FUTURA | FASE K | F→L |
| GFX8 Counter Research | Investigación documental (FASE M) | Verificar Event IDs GFX8/Polaris12 en fuentes primarias | PLANIFICADA / FUTURA | Independiente | G→M |
| Ghost Cache | Proyecto/tecnología (memoria) | Reducir penalizaciones de movimiento/acceso de datos; GTT/TTM, prefetch, VRAM | HIPÓTESIS / sin diseño técnico / sin evidencia | post-caracterización de bottleneck | Ghost (genérico); «Ghost Berreta» NO documentado |
| BERRETA | Proyecto/tecnología (Vulkan/compute/ACE) | Capa/intervención Vulkan para experimentar renderizado y trabajo asíncrono; aprovechar recursos ociosos | HIPÓTESIS / sin diseño técnico / sin evidencia | post-caracterización de bottleneck | — |
| RX Compression Engine | Proyecto/tecnología (nombre PROVISIONAL) | Compresión/descompresión adaptada a workloads RX 550/Polaris12 | IDEA / propuesta — investigación pendiente | FASE K (prototipo controlado) | sin nombre definitivo |
| Orquestador Final | Framework (integración) | Aplicar solo optimizaciones con evidencia que hayan superado gates | DISEÑO PENDIENTE | ≥1 optimización VERIFICADA | — |
| Benchmarks externos | Herramientas/benchmarks | GravityMark 1.89, Superposition 1.1, Heaven 4.0, Valley 1.0 (instalados, SHA-256 verificados) | INSTALADOS (uso según autorización y licencia) | autorización | — |
| Technology Naming & Architecture | Línea documental (FASE N) | Inventario, clasificación y nomenclatura del ecosistema | PLANIFICADA / DOCUMENTAL | transversal | originales E/F/G → K/L/M; N nueva |
| GPU Control & Orchestration Research | Línea de investigación (FASE O) | Evaluar LACT, CoreCtrl, amdgpu-clocks, sysfs/amdgpu, PowerPlay, DPM, runtime-PM, perfiles, restauración y ownership; decidir reutilizar/integrar/tomar ideas/independiente; no reemplazar rx550-torneo sin comparar capacidades | PLANIFICADA / FUTURA (INVESTIGACIÓN) | transversal | — |
| Protocolo GPU Ownership | Protocolo transversal | detectar gestor externo → verificar estado → adquirir ownership temporal → experimento → restaurar original → liberar ownership → verificar restauración; aplicar a gestores como Kalm si realmente están activos | DISEÑO (en roadmap, no implementado) | aplica a K/L/O y a todo gestor externo | — |
| Frame Generation & Upscaling Research | Línea de investigación (FASE P) | lsfg-vk, FSR, upscaling, frame generation, Vulkan layers, inyección/interposición, coste/latencia/calidad, compatibilidad Polaris12; separar rendimiento REAL vs PERCIBIDO | PLANIFICADA / FUTURA (INVESTIGACIÓN) | métricas separadas de los benchmarks del Lab K | — |
| Mesa Polaris12 Optimization Research | Línea de investigación (FASE Q) | Oportunidades en Mesa/radeonsi/RADV para Polaris12 sin asumir beneficio; pipeline OBSERVACIÓN→HIPÓTESIS→CAMBIO AISLADO→A/B→RÉPLICAS→MEDICIÓN→VALIDACIÓN→ACEPTAR/RECHAZAR | PLANIFICADA / FUTURA (INVESTIGACIÓN) | etapa experimental futura con rollback definido | — |

### RX Compression Engine (NOMBRE PROVISIONAL)

Estado: propuesta de investigación; **no implementar**. El nombre es provisional, no definitivo.

Objetivo: investigar la posibilidad de un sistema de compresión/descompresión específicamente adaptado a workloads relevantes para RX 550/Polaris12. Candidatos a estudiar (sin asumir): texturas, buffers, datos intermedios, recursos Vulkan, datos RAM↔VRAM y datasets/workloads específicos.

La investigación debe determinar: qué datos son candidatos; coste de compresión; coste de descompresión; reducción de tráfico; latencia; consumo; impacto sobre CPU/GPU; y beneficio neto.

Direcciones a valorar posteriormente: compresión orientada a transferencia, a almacenamiento, a VRAM, a recursos Vulkan, o formatos específicos para determinados patrones de datos.

Orden: **investigación → prototipo controlado → validación → (solo entonces) tecnología estable**. No asumir que la compresión mejora el rendimiento.

### Orden de desarrollo (roadmap conceptual)

```
A–D (COMPLETADO — investigación y caracterización ya realizadas)
E–J (fases históricas/futuras existentes — se mantienen intactas)

K — Polaris12 Performance Laboratory
L — RX550-Tuner
M — GFX8 Counter Research
N — Technology Naming & Architecture (transversal)
O — GPU Control & Orchestration Research (transversal)
P — Frame Generation & Upscaling Research
Q — Mesa Polaris12 Optimization Research

Tecnologías del ecosistema (líneas de desarrollo que pueden depender de K/L/M/O/P/Q según corresponda):
Ghost / Ghost Berreta (memoria/GTT/TTM/prefetch), BERRETA (Vulkan/compute/ACE),
RX Compression Engine (provisional), futuras tecnologías específicas RX 550
```

- **No ejecutar todas las líneas simultáneamente.**
- **No asumir que todas terminarán siendo implementadas.** Cada tecnología pasa por su ciclo de vida:

```
IDEA → INVESTIGACIÓN → DISEÑO → PROTOTIPO → EXPERIMENTO → VALIDACIÓN → TECNOLOGÍA CONFIRMADA
IDEA → INVESTIGACIÓN → DESCARTADA
```

- **No llamar «tecnología confirmada» a algo que solo existe como hipótesis.**

### Principio fundamental de todo el ecosistema

El proyecto distingue estrictamente: `HECHO` · `HIPÓTESIS` · `EXPERIMENTO` · `RESULTADO` · `TECNOLOGÍA PROTOTIPO` · `TECNOLOGÍA VALIDADA`.

- No convertir ninguna hipótesis en hecho.
- Un experimento planificado no es un resultado; una correlación no es causalidad (§K4).
- Una tecnología solo se declara `TECNOLOGÍA VALIDADA` tras superar gates A/B con evidencia reproducible.

---

## Capa Transversal — KERNEL / DRIVER COMPATIBILITY & EDGE-CASE LAYER

**No es una FASE.** Capa transversal documental/planificación que afecta principalmente **K, L, O y Q**, y **parcialmente M**. Integrada el 2026-09-21.

Objetivo general: evitar que el proyecto asuma que una interfaz de amdgpu, una herramienta o un comportamiento documentado para otra generación de GPU funciona automáticamente en Polaris12/GFX8. **DOCUMENTACIÓN GENÉRICA ≠ CAPACIDAD CONFIRMADA EN RX550.**

### 1. Telemetría — FASE K / FASE O

Herramientas a evaluar explícitamente: `radeontop`, `amdgpu_top`, `UMR`, `perf`, herramientas basadas en `fdinfo`, `gpu_metrics` y `sysfs/hwmon`.

Para cada herramienta registrar: fuente de datos; ioctl/sysfs/debugfs utilizado; si requiere root; si modifica estado; si puede despertar la GPU; si puede impedir runtime-PM; resolución temporal; métricas disponibles; compatibilidad con Polaris12; coste de observación; reproducibilidad.

**IMPORTANTE:** `amdgpu_top` debe evaluarse no solo por la cantidad de métricas que proporciona, sino también por el efecto de leer contadores sobre los mecanismos de ahorro energético. La documentación de `amdgpu_top` advierte que leer GRBM/GRBM2 puede desactivar funciones de power saving.

**OBSERVADOR ≠ PASIVO AUTOMÁTICAMENTE.**

Toda herramienta de telemetría se clasificará como:
- **A — pasiva**;
- **B — potencialmente perturbadora**;
- **C — claramente perturbadora**;
- **D — desconocida**.

No utilizar una herramienta de categoría B/C dentro de un benchmark crítico sin una prueba previa de su overhead/perturbación.

### 2. LACT — FASE O (comparación formal LACT vs rx550-torneo)

No asumir que LACT debe reemplazar rx550-torneo. Comparar: power cap; performance level; DPM; clocks; voltajes; overdrive; perfiles; persistencia; restauración; detección de hardware; multi-GPU; runtime-PM; seguridad; rollback; interfaz; automatización; dependencia de versiones del kernel; compatibilidad Polaris12.

Pregunta correcta 1: **«¿Qué problema resuelve LACT que rx550-torneo no debería reinventar?»**
Pregunta correcta 2: **«¿Qué requisitos experimentales de rx550-torneo hacen que una herramienta generalista no sea suficiente?»**

Resultado esperado: **DECISIÓN DOCUMENTAL.** No implementación automática.

### 3. amdgpu-clocks — FASE L (referencia arquitectónica)

Analizar: lectura de `ppfeaturemask`; comprobación de OverDrive; `pp_od_clk_voltage`; FORCE_SCLK; FORCE_MCLK; FORCE_POWER_CAP; FORCE_PERF_LEVEL; FORCE_POWER_PROFILE; restauración; e **identificación por PCI frente a cardX**.

Estudiar especialmente la estrategia de identificación por PCI. Para rx550-torneo: **NO depender exclusivamente de `/sys/class/drm/card1`**; preferir identificar la GPU por `vendor + device + PCI BDF` y resolver posteriormente el nodo sysfs dinámicamente. Requisito de robustez, no necesariamente implementación inmediata.

### 4. L.0 — Capability Audit (ppfeaturemask) — FASE L

Antes de cualquier investigación de OverDrive: leer el `ppfeaturemask` actual; identificar qué bits están activos; comprobar si `PP_OVERDRIVE_MASK = 0x4000` está habilitado; documentar el valor original; documentar qué cambiaría si se habilitara; determinar si requiere modificación del parámetro de kernel y reinicio. **NO modificar todavía.**

IMPORTANTE: **Paso 0 ≠ «establecer 0x4000».** Paso 0 = verificar si 0x4000 está disponible/habilitado y estudiar el mecanismo necesario para habilitarlo. La modificación queda fuera del experimento documental hasta autorización explícita. El kernel define `PP_OVERDRIVE_MASK` como 0x4000, pero la disponibilidad efectiva de la interfaz debe comprobarse en la plataforma concreta.

### 5. pp_od_clk_voltage — FASE L (objeto de investigación independiente)

Investigar: disponibilidad en Polaris12; formato; estados SCLK; estados MCLK; rangos; voltajes; modo manual; commit; reset; interacción con DPM; interacción con power cap; persistencia; restauración; comportamiento después de runtime-PM; comportamiento después de suspensión/resume.

**DOCUMENTACIÓN GENÉRICA ≠ CAPACIDAD CONFIRMADA EN RX550.** El kernel documenta esta interfaz como mecanismo para ajustar clocks/voltajes de los power levels, pero eso NO implica que todas las operaciones estén disponibles o se comporten igual en todas las generaciones.

### 6. pp_dpm_sclk — Known/Reported Polaris DPM Edge Cases — FASE L

Investigar específicamente la afirmación: «en determinadas versiones/configuraciones de Polaris, `pp_dpm_sclk` puede aceptar una escritura a nivel de sysfs aunque el resultado efectivo en firmware/SMU no corresponda con lo solicitado».

- **NO registrar todavía como hecho universal; clasificar inicialmente: CLAIM TO VERIFY.**
- Buscar: versión del kernel; ASIC; driver; método de escritura; código del kernel; mensajes del kernel; readback; clock observado; casos reproducibles.

Regla: **WRITE SUCCESS ≠ STATE CHANGE VERIFIED.** Toda operación futura seguirá:
`write → readback de interfaz → observación efectiva del estado → validación temporal → conclusión`.

### 7. pp_table — FASE L (clasificación por GPU)

No afirmar prematuramente «pp_table runtime no funciona en Polaris». El kernel define `pp_table` como interfaz sysfs para leer la tabla PowerPlay e intentar cargar una nueva; la disponibilidad y semántica efectiva dependen de la arquitectura/driver.

Clasificar por GPU: disponible / lectura disponible / escritura disponible / escritura rechazada / no expuesta / no verificada. Para Polaris12 hay que medir y documentar primero.

NO confundir (son cuatro mecanismos conceptualmente distintos):
1. `pp_table` runtime del driver;
2. PowerPlay table almacenada/derivada del firmware/VBIOS;
3. modificación del VBIOS;
4. `pp_od_clk_voltage`.

### 8. VBIOS — alto riesgo — FASE L

Mantener la investigación de: PolarisBiosEditor; herramientas históricas de VBIOS; PowerPlay tables; modificación de clocks/voltajes/power limits. Establecer formalmente:

**VBIOS MODIFICATION = HIGH RISK / OUTSIDE NORMAL EXPERIMENT LOOP.**

NO realizar: flash; modificación; escritura; parcheo; overdrive persistente — sin una fase posterior específica de recuperación y validación.

### 9. Observability Perturbation (transversal)

Antes de utilizar una herramienta para medir una variable, estudiar si la propia medición altera: clocks; power gating; runtime-PM; GPU busy; memory busy; temperatura; power; scheduling; latencia; frecuencia efectiva.

Especialmente relevante para: `radeontop`; `amdgpu_top`; `UMR`; lecturas de contadores; polling frecuente; GPU metrics.

En cada benchmark crítico registrar el **TELEMETRY MODE**:
- `TELEMETRY_MODE=MINIMAL`
- `TELEMETRY_MODE=STANDARD`
- `TELEMETRY_MODE=COUNTER`
- `TELEMETRY_MODE=DIAGNOSTIC`

El benchmark principal debe utilizar el modo menos perturbador que permita medir las variables necesarias.

### 10. Hardware Identity (transversal)

La identidad física de la GPU es requisito transversal de todo experimento. No utilizar solamente card0/card1. Registrar: PCI BDF; vendor; device; subsystem; ASIC/GFX generation; driver; kernel; Mesa; firmware; VRAM; power cap limits.

Para nuestra RX 550: **la identidad PCI es la referencia primaria**; `cardX` debe considerarse un identificador dinámico.

### 11. Capability Matrix (K/L/O)

Aplicar a cada interfaz la matriz:

`CAPABILITY → DOCUMENTED → PRESENT → READABLE → WRITABLE → EFFECTIVE → REVERSIBLE → BENCHMARK-SAFE`

Una interfaz puede existir, aceptar escritura y devolver éxito, y aun así no producir el efecto esperado. **«Writable» no significa «Effective».**

### 12. Experimental Safety Gate

Antes de cualquier modificación futura de PowerPlay/OverDrive/Mesa/contadores, comprobar todo el checklist; si alguno falla → **ABORT**:

```
[ ] GPU correcta
[ ] PCI BDF correcto
[ ] driver correcto
[ ] kernel registrado
[ ] estado original capturado
[ ] método de restauración probado
[ ] runtime-PM conocido
[ ] herramienta externa detectada
[ ] ownership adquirido
[ ] telemetría seleccionada
[ ] rollback definido
[ ] criterio de abort definido
```

### 13. Regla metodológica transversal

**NO CONFIAR EN EL RETORNO DE LA INTERFAZ COMO PRUEBA DEL ESTADO FÍSICO.**

Ejemplo: `sysfs write = SUCCESS` no demuestra: clock aplicado; power state aplicado; firmware aceptó; hardware operó en ese estado. La validación debe observar el estado efectivo mediante una ruta independiente cuando sea posible.

### 14. Actualización de K–Q (resumen de la integración)

- **K:** unified telemetry; observability perturbation; telemetry modes; capability matrix (ver §1, §9, §11).
- **L:** capability audit; ppfeaturemask; pp_od_clk_voltage; pp_dpm edge cases; pp_table distinction; VBIOS high-risk boundary; PCI-based identification; experimental safety gate (ver §3–§8, §12).
- **M:** observability perturbation; historical tool comparison; counter measurement overhead (ver §1, §9).
- **O:** LACT; CoreCtrl; amdgpu-clocks; amdgpu_top; ownership; capability comparison; external-manager detection (ver §1, §2, §3, §11, §12).
- **P:** mantiene: separación FPS reales / FPS generados; latencia; coste; calidad; compatibilidad (sin cambios).
- **Q:** kernel/driver version matrix; Mesa version matrix; regression detection; reproducibility; rollback (ver §11, §15).

### 15. Clasificación de afirmaciones externas (regla final)

No convertir ninguna afirmación encontrada en Internet en un «hecho del proyecto» automáticamente. Toda afirmación externa se clasificará como:

`DOCUMENTED · OBSERVED · REPRODUCED · INFERRED · HYPOTHESIS · UNVERIFIED · CONTRADICTED`

Y cuando una afirmación dependa de una versión concreta del kernel, Mesa, firmware o herramienta, **se registrará la versión**.

El objetivo es que el MASTER-PLAN no sea solamente un listado de tecnologías, sino una **especificación experimental reproducible para una GPU GFX8 real**.

---

## R. FASE R-1 — DOCUMENTATION RECONCILIATION & MASTER CONSOLIDATION (COMPLETADA 2026-09-22)

> **Objetivo:** fase SOLO DOCUMENTAL (read-only) que reconcilia la documentación acumulada A–R-0 para que el
> repositorio sea internamente coherente antes de M/J/L y E–J; cierre de deudas documentales y consolidación
> del estado. Entregables en `experiments/FASE-R1-DOCUMENTATION-RECONCILIATION/`.

### Entregables (tracer a su archivo)

| Ítem | Archivo | Contenido clave | Estado |
|---|---|---|---|
| R-1.1 | `R1-1-GFX8-EVENT-RECONCILIATION.md` | Reconciliación GPUPerfAPI v3.11.1 (CB 396/SQ 299/MC 33) vs Mesa groups_VI (CB 405/SQ 273/MC 22) → **PARTIALLY_RECONCILED**; 20/22 bloques con coincidencia exacta; semántica/unidad MC **UNRESOLVED**. Rango seguro: CB 0..395, SQ 0..272, MC 0..21 | COMPLETADA |
| R-1.2 | `FASE-D-GFX8-EVENT-ID-AUDIT.md` §14 | Resultado B cruzado con R-0 (fuentes locales vs AMD v3.11.1 añadida); GRBM=2 y SQ=4 pasan a VERIFICADO documental | COMPLETADA |
| R-1.3 | `FASE-D-ETAPA-2-RESULTADOS.md` §12 | Correcciones de la auditoría aplicadas (tabla radeontop con método declarado; SPI 3306→8408) sin alterar conclusiones (potencia 1.41 intacta) | COMPLETADA |
| R-1.4 | `MASTER-RESEARCH-STATUS.md` (v2.5) | Conclusión B → adenda (no borrado); versión, artefactos, noticia GRBM=2 actualizada | COMPLETADA |
| R-1.5 | `R1-5-DOCUMENTATION-STATUS.md` | Mapa documental A–R-1 con versiones/estado/dependencias/contradicciones | COMPLETADA |
| R-1.6 | `R1-6-EVIDENCE-STATE-MODEL.md` | Modelo de estados: VERIFICADO/REPRODUCIBLE/OBSERVADO/HIPÓTESIS/DOCUMENTADO/PARTIALLY_RECONCILED/UNRESOLVED/CONTRADICTED/NO REPRODUCIBLE/NO VERIFICADO | COMPLETADA |
| R-1.7 | `R1-7-CRITICAL-GAPS.md` | 8+ gaps con plantilla y prioridad (GAP-01 cap/SCLK, GAP-04 mem_busy, GAP-07 PCIe x8/x4, GAP-08 CUs/BIOS, GAP-09 MC semántica = alta) | COMPLETADA |
| R-1.8 | `R1-8-CROSS-CUTTING-AUDIT.md` | Capa Transversal read-only: L.0 Capability Audit ppfeaturemask (0xfff7bfff, sin 0x4000 → OD no activo); pp_od_clk_voltage/pp_dpm como objetos independientes; WRITE SUCCESS ≠ STATE CHANGED; VBIOS high-risk; Observability Perturbation; Hardware Identity por PCI | COMPLETADA |
| R-1.9 | `R1-9-E-J-READINESS.md` | E-J: diseño posible ya; ejecución NO hasta autorización + Laboratorio K + resolución de gaps ALTA | COMPLETADA |
| R-1.10 | `R1-10-NON-AUTHORIZED-ACTIONS.md` | Marco: qué sigue NO autorizado y vías de desbloqueo (programación contadores, sysfs, pp*, VBIOS, instalaciones) | COMPLETADA |
| R-1.13 | este documento (sección R) + MASTER-RESEARCH-STATUS v2.5 | Integración de FASE R-1 | COMPLETADA |
| R-1.15 | `FASE-R1-FINAL-REPORT.md` | Informe final apartados A–K + verificación de checklist §14 | COMPLETADA |

### Constantes de la fase

1. **Solo documental:** ninguna escritura de sistema (no sysfs, no contadores, no PowerPlay, no VBIOS). Sin
   benchmarks, sin instalaciones.
2. **Historial intacto:** las conclusiones previas NO se borran; las contradicciones se resuelven mediante
   adendas/cross-refs (modelo R1-6).
3. **Nada se inventa:** cada número trazable a su fuente (GPUPerfAPI v3.11.1 `gpa_hw_counter_gfx8.cc`;
   Mesa local `ac_perfcounter.c`; referencias R-0).
4. **Programación de contadores y toda escritura SIGUEN NO AUTORIZADAS.**

### Efecto neto de la fase

- **Bloqueo documental de Event IDs GFX8 eliminado** (mapa recuperado en R-0, reconciliado en R-1).
- Se define el rango seguro de PERF_SEL para futuro diseño (intersección de catálogos).
- La semántica/unidad del bloque **MC queda declarada UNRESOLVED**: no diseñar normalización de ancho de banda
  MC sin catálogo con nombres/unidad.
- Las fases E–J/E–Q quedan con su readiness documentado y sus gates de autorización intactos.

---

## S. FASE R-2 — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE (COMPLETADA 2026-09-22)

> **Objetivo:** fase SOLO DOCUMENTAL Y DE DISEÑO (read-only) que documenta **todo el trabajo pendiente del
> ecosistema completo** (no limitado a RX550/GFX8), con rigurosa separación de estados
> (DOCUMENTADO/DISEÑADO/PLANIFICADO/INVESTIGADO/OBSERVADO/MEDIDO/REPRODUCIDO/VALIDADO/HIPÓTESIS/UNVERIFIED/
> BLOCKED/DEFERRED/NOT STARTED/NO AUTORIZADO). Un futuro investigador debe poder ejecutar una fase leyendo su
> diseño sin inventar el protocolo, y **ningún nombre provisional se convierte en tecnología consolidada**.
> Entregables en `experiments/FASE-R2-PROJECT-DOCUMENTATION/` + `projects/`.

### Entregables (tracer a su archivo)

| Ítem | Archivo | Contenido clave | Estado |
|---|---|---|---|
| R-2.1 | `R2-HISTORICAL-EXPERIMENT-INVENTORY.md` | Inventario E0–E5: E1/E2/E3/E4/E5/E5b EXISTEN en backup Torneo; **E0 NOT FOUND** como artefacto (solo 2 refs textuales; datos plausibles en `mesa-resolution-…113618|135118`); Familia 2 (E-01/E-02/E-03/ES-01/F2) VERIFICADA reproducible; dos familias "E" no mezclables | COMPLETADA |
| R-2.2 | `R2-GLOBAL-DOCUMENTATION-MAP.md` | Mapa documental completo del repositorio (raíz, experiments/ A–D/R-0/R-1/sintético, rx550-torneo, backup, R-2) + rutas de navegación para investigador nuevo | COMPLETADA |
| R-2.3 | `FASE-E-REAL-GAME-BASELINE-DESIGN.md` | Diseño completo de baseline de juego real: criterios de selección, protocolo NS≥30s, telemetría unificada, criterios VALID/INVALID/OUTLIER/REPEATABLE; **DISEÑADA pero BLOQUEADA** (sin juego reproducible autorizado) | COMPLETADA (DISEÑO) |
| R-2.4 | `FASE-F-GEOMETRY-INVESTIGATION-DESIGN.md` | Fichas GEO-01..08 (hipótesis, mecanismo, contador potencial, workload, variables, controles, riesgos, confounders, éxito/negativo, dependencias); correlación ≠ causalidad; priorización en J | COMPLETADA (DISEÑO) |
| R-2.5 | `FASE-G-MEMORY-VRAM-GTT-DESIGN.md` | Modelo request→caches→VRAM/GTT→PCIe→system RAM→stall; separación DOCUMENTED/OBSERVED/INFERRED/HYPOTHESIS; experimentos G-M1..G-M5; base conceptual para Ghost y RX-Compression-Engine | COMPLETADA (DISEÑO) |
| R-2.6 | `FASE-H-RADV-WORKAROUNDS-DESIGN.md` | H-1..H-7 (msaa_sample_loc_bug, LINE_FILTER_DISABLE, clear_db_cache, z_fights/blend, shrink_image_store, wait_for_vm_map, partial_vs_wave); explica cocientes MSAA E3/E5 | COMPLETADA (DISEÑO) |
| R-2.7 | `FASE-I-POWERPLAY-DPM-DESIGN.md` | Separación A–F (doc externa/evidencia local/capacidad kernel/verificada/reversible/alto riesgo); política MCLK 5/16/20 (R0-2); experimentos I-1..I-5 | COMPLETADA (DISEÑO) |
| R-2.8 | `EXPERIMENT-PRIORITY-MATRIX.md` | Matriz J con 10 criterios (valor/dependencias/riesgo/reversibilidad/reproducibilidad/coste/métricas/evidencia/discriminación/confounders) → ALTA/MEDIA/BAJA/BLOQUEADOS; sin "mejor experimento" sin justificación | COMPLETADA (DISEÑO) |
| R-2.9 | `SYNTHETIC-WORKLOAD-DESIGN.md` | Framework modular de 8 modos (geometry/shading/memory/fetch/vram/compute/async/power) sobre el prototipo CONGELADO; validación/hashing/determinismo | COMPLETADA (DISEÑO) |
| R-2.10 | `FASE-K-PERFORMANCE-LAB-DESIGN.md` | K1..K10: telemetry/runner/dataset/metadata/repeticiones/warmup/validación/fault detection/perturbación de observabilidad/capability matrix/hashing; estructura RUN canónica | COMPLETADA (DISEÑO) |
| R-2.11 | `FASE-L-RX550-TUNER-DESIGN.md` | State machine + ownership + lock + verificación de estado + failsafe; perfil balanced/locked/25W/experimental; WRITE SUCCESS ≠ STATE CHANGE VERIFIED; no reemplaza rx550-torneo | COMPLETADA (DISEÑO) |
| R-2.12 | `FASE-M-GFX8-COUNTER-RESEARCH-DESIGN.md` | Estado catálogo (R-0.1/R1-1) → rutas M-A..M-E; "Event ID documentado ≠ autorización"; programación NO autorizada; D-3 vía de ejecución separada | COMPLETADA (DISEÑO) |
| R-2.13 | `FASE-N-ECOSYSTEM-ARCHITECTURE.md` | 14 nombres oficiales del ecosistema con PROPÓSITO/TIPO/DEPENDENCIAS/ESTADO/RELACIÓN/PROVISIONAL/IMPLEMENTADO; principio fundamental + ciclo de vida + SAFETY BOUNDARY | COMPLETADA (DISEÑO) |
| R-2.14 | `projects/BERRETA/BERRETA-DESIGN.md` | Investigación de overlap async/ACE (H-B1..B3) dependiente de ASY-01/evidencia; PROVISIONAL; criterios éxito/abandono | COMPLETADA (DISEÑO/IDEA) |
| R-2.15 | `projects/GHOST/GHOST-CACHE-DESIGN.md` | Prefetch/localidad/working set; separación GHOST vs GHOST CACHE vs RX550-Tuner vs FASE G; escalones IDEA→HIPÓTESIS→OBSERVADO→VALIDADO; PROVISIONAL | COMPLETADA (IDEA) |
| R-2.16 | `projects/RX-COMPRESSION-ENGINE/RX-COMPRESSION-ENGINE-DESIGN.md` | Compresión de memoria (texturas/buffers/intermedios/GTT/PCIe); casos ayuda/no-ayuda, métodos de medición, confounders; PROVISIONAL | COMPLETADA (IDEA) |
| R-2.17 | `projects/ORCHESTRATOR/FINAL-ORCHESTRATOR-DESIGN.md` | Orquestador: integra runner/telemetría/benchmark/tuner/contadores/validación/rollback/artefactos/resultados/decisión; SAFETY BOUNDARY Observación/Experimentación/Modificación; sin autoridad de HW | COMPLETADA (DISEÑO) |
| R-2.18 | `FASE-O-GPU-CONTROL-ORCHESTRATION-DESIGN.md` | Comparación LACT/CoreCtrl/amdgpu-clocks vs rx550-torneo (capacidades/ownership/perfiles/telemetría/runtime-PM/PowerPlay/rollback/GUI-CLI/risco/compatibilidad); sin instalación; externas = objetos de evaluación | COMPLETADA (DISEÑO) |
| R-2.19 | `FASE-P-FRAME-GENERATION-UPSCALING-DESIGN.md` | lsfg-vk/FSR/upscaling/frame generation/Vulkan layers; separación estricta REAL FPS vs GENERATED vs PERCEIVED; nunca mezcladas en Lab K | COMPLETADA (DISEÑO) |
| R-2.20 | `FASE-Q-MESA-POLARIS12-OPTIMIZATION-DESIGN.md` | Inventario por dominio (radeonsi/RADV/ACO/LLVM/memoria/scheduling/barriers/cache/MSAA/primitivas); ficha por oportunidad con 10 campos; pipeline OBSERVACIÓN→…→DECISIÓN; sin tocar Mesa | COMPLETADA (DISEÑO) |
| R-2.21 | `R2-DEPENDENCY-GRAPH.md` | Grafo R-0→R-1→R-2; E→F/G/H/I; J; K→L/M; Ghost depende G (POTENCIAL); RX-Comp depend G; BERRETA ASY; Orquestador coordina; fuerza CONFIRMADA/PROBABLE/POTENCIAL | COMPLETADA |
| R-2.22 | este documento (sección S) | Integración de FASE R-2 en el MASTER-PLAN (mapa del proyecto, no duplica estado) | COMPLETADA |
| R-2.23 | `MASTER-RESEARCH-STATUS.md` (v2.6) | FASE R-2 registrada; sin marcar como ejecutado lo que solo tiene diseño | COMPLETADA |
| R-2.24 | `PROJECT-DOCUMENTATION-STATUS.md` (raíz) | ÍNDICE CENTRAL: qué existe/falta/diseñado/ejecutado/validado/planteado/autorización por elemento del ecosistema | COMPLETADA |
| R-2.25 | `FASE-R2-FINAL-REPORT.md` | Informe final apartados A–O + checklist de finalización + resumen de 11 ítems | COMPLETADA |

### Constantes de la fase

1. **Solo documental/diseño:** ninguna escritura de sistema, ni hardware, ni Mesa/kernel/PowerPlay/VBIOS/BIOS;
   sin contadores, sin benchmarks nuevos, sin implementar BERRETA/Ghost/RX-Compression/Orquestador.
2. **Rigor de estados:** nunca "completo" solo porque exista un párrafo en MASTER-PLAN; una fase está con diseño
   suficiente solo si otro investigador puede ejecutarla sin inventar el protocolo.
3. **Nada se inventa:** E0 NOT FOUND registrado con dónde se buscó; proyectos provisionales marcados
   PROVISIONAL/IDEA; sin promover hipótesis a tecnología.
4. **Programación de contadores y toda escritura SIGUEN NO AUTORIZADAS.**

### Efecto neto de la fase

- Repositorio navegable por cualquier investigador nuevo (`PROJECT-DOCUMENTATION-STATUS.md` + mapa R-2.2).
- 24 documentos de diseño/inventario producidos cubriendo E–Q y los 4 proyectos propios (BERRETA, GHOST,
  RX-Compression-Engine, Orquestador).
- Histórico E0–E5 inventariado (dos familias), con E0 registrado como NOT FOUND.
- Roadmap E–Q con diseño completo pendiente de autorización de ejecución (K/L/M requieren el Lab).