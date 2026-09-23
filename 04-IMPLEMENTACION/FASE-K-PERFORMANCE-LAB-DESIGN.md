# FASE K — POLARIS12 PERFORMANCE LABORATORY — Documento de Diseño

> **Archivo:** `FASE-K-PERFORMANCE-LAB-DESIGN.md`
> **Fase:** FASE R-2 — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE (R-2.10)
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL (DISEÑO; NO implementado)
> **Clasificación:** [DISEÑADO] — estructura del laboratorio reproducible de caracterización.
> **Estado global:** **PLANIFICADA** (roadmap FASE K/Q). No se escribió ni ejecutó nada.

---

## 1. OBJETIVO

Diseñar el **LABORATORIO transversal** que estandariza cómo se ejecuta, mide, valida y almacena cada
experimento del ecosistema: estructura de corrida, telemetría unificada, validación, hashing, detección
de fallos y matriz de capacidades. Es la capa "runner" que usan FASE E/F/G/H/L y los proyectos.

## 2. Definición de los bloques K1..K10

| ID | Bloque | Contenido diseñado |
|---|---|---|
| **K1** | Telemetry Schema | Esquema CANÓNICO de telemetría: sysfs (gpu_busy, mem_busy, power1_average/input, temp, pp_dpm_state, pp_dpm_sclk/mclk, mem_info_*), frame-level (FPS, frametime p50/p99), metadata; formato CSV versionado; sync con `METRICS-DEFINITIONS` (AUDIT-001) |
| **K2** | Runner | Ejecutor de corridas: orquesta launcher + colección de telemetría + lifecycle (start→collect→stop→restore→validate); plantillas manifest/pre/post/journal; atomicidad por corrida |
| **K3** | Dataset Layout | Estructura canónica `runs/<experimento>/<celda>/` con `manifest/workspace/config/telemetry/stdout/stderr/result/validation/hash`; nomenclatura única (ID+timestamp) |
| **K4** | Metadata | Schema de metadata del experimento: ID único, fase, fecha, GPU (vendor/device), Mesa/driver/kernel, condiciones DPM/cap/temp/state-inicial, seeds, versión de workload, estado typeof experimento |
| **K5** | Repetitions & Warm-Up | Política N≥5 pareadas, A/B intercalado, warm-up 5s+registro de estabilidad térmica; outlier 3×MAD marcado no-eliminado |
| **K6** | Validation Engine | Validación de cada corrida: VALID/INVALID/OUTLIER/REPEATABLE (criterios FASE E §5.6); verificación de estado inicial/final (WRITE-SUCCESS ≠ STATE-CHANGE VERIFIED); presencia completa de artefactos |
| **K7** | Fault Detection | Detección de device lost / VK_ERROR_DEVICE_LOST / OOM / timeout fence / crash de telemetría; captura en journal + dmesg; abort limpio |
| **K8** | Observability Perturbation | Estimador de perturbación propia de la telemetría (costo de muestrear sysfs, mango hud, hilo dedicado) y su impacto en los limites de precisión de p99/steady (relación con R1-8 Observability Perturbation) |
| **K9** | Capability Matrix | Matriz HW/SW que declara qué puede medir este sistema y qué NO (amprehistoria de METRICS-DEFINITIONS): contadores → NO accesibles; mem_busy ≠ BW; power1_input = estimador SMU, etc. |
| **K10** | Artifact Hashing & Reproducibility | sha256 de artefactos (como M1), manifiesto determinista, Y del entorno, checksum de binarios/shaders; garantiza que "la misma corrida" es reproducible bit a bit en lo posible |

## 3. Estructura de RUN (diseñada)

```
runs/<ID-celda>/
├── metadata.yaml        # K4: identidad del experimento y condiciones
├── configuration.json   # K4: parámetros exactos (workload + runner)
├── workload/            # binario/shaders/versión (o referencia a hash fijo)  <- K10
├── telemetry/           # raw sysfs + frame-level CSVs                       <- K1
├── stdout.txt           # salida del workload
├── stderr.txt           # errores
├── result.json          # métricas calculadas (REP)                          <- K5/K10
├── validation.json      # VALID/INVALID/OUTLIER + reason                     <- K6
├── hash.sha256          # checksums de todos los artefactos                  <- K10
└── journal.md           # log del runner (eventos, abortos, faults)          <- K7
```

Convenciones: ID = `<FASE>-<CANDIDATO>-<rep>` (ej. `GEO-01-r1`), timestamps en metadata (no en el nombre
para no romper inmutabilidad del hash).

## 4. Telemetría (K1) — bloques canónicos

1. **sysfs (hilo dedicado, configuración por runner):** `gpu_busy_percent`, `mem_busy_percent`,
   `power1_average` (µW), `power1_input` (µW, solo diagnóstico), `temp1_input`, `pwm`,
   `pp_dpm_state`, `pp_dpm_sclk`, `pp_dpm_mclk`, `mem_info_vram_used`, `mem_info_gtt_used`.
2. **Frame-level:** log de frames (timestamp, duration) → FPS/Frametime p50/p99/p95; lectura desde
   MangoHud o timing propio del runner.
3. **Timestamp queries Vulkan** para caminos específicos (upload latencia etc.) cuando el workload lo
   exponga.
4. **PC estándar (secundaria):** `perf stat :u` opcional por celda para aislar CPU-Bound.

Regla: **toda métrica reportada debe citar su definición exacta** (ventana/filtro) y si no es comparable
con otra se etiqueta `NOT DIRECTLY COMPARABLE`.

## 5. Validación (K6) — reglas

- R1: todos los artefactos presentes con hash válido.
- R2: `state_final` == `state_initial` (o == valor esperado del diseño) → si alto-riesgo (write), exigir
  readback + estado verificado.
- R3: sin faults (journal vacío de errors), sin device lost.
- R4: datos de calibración del entorno (temp prompt, DPM) registrados.
- R5: outlier detectado se marca (no se borra).

## 6. Perturbación de observabilidad (K8)

- Medir el costo de muestrear sysfs a 4/10 Hz (time delta por lectura) y el delta de frames de mango-hud
  en un run controlado (2 run de un mismo workload: con/sin telemetría). Reportar el sesgo máximo
  introducido en p50/p99; si supera el alpha del experimento, marcar el experimento como no-verificable
  dentro de su diseño.
- Relación con R1-8 (Observability Perturbation) ya existente: K8 la instrumenta.

## 7. Capacidad y límites (K9)

Declarar cosas verdaderas, no re-ejecutar:
- Podemos medir: FPS/frametime, power1_average/input (estimador SMU), busy%, relojes por DPM, temp,
  VRAM/GTT uso, faults de Vulkan.
- NO podemos (sin autorización/Herramienta): contadores HW GFX8 (programación NO autorizada), DCC state
  exacto, % real de bandwidth, per-block activity.
→ K9 es la guía para interpretar: nada de lo que diga el Lab contradice METRICS-DEFINITIONS.

## 8. Integración
- El Lab es **runner neutral**: no reemplaza rx550-torneo (perfiles); lo captura como entorno.
- El launcher del workload sintético (R-2.9) le servirá de runner por defecto; los proyectos (GHOST,
  BERRETA) ejecutan AÚN solo como diseños (no ejecutan en K sin autorización).
- FASE L es el consumidor de K (hará A/B con el runner); FASE M (counter research) requerirá el Lab
  para sus mediciones cuando se autorice el modo contadores.

## 9. Conclusión del diseño
FASE K queda **DISEÑADA** (K1..K10 + estructura RUN + telemetría + validación + fault + perturbación +
capacidad + hashing). El Lab no existe como código aún: su implementación es **futura** (requiere
autorización de codificación), y mientras tanto se usa el arnés de FASE D/M1 (que ya implementa
prácticamente K3-K6-K10 en su formato). No se ejecutó ni se declaró ningún resultado de K.