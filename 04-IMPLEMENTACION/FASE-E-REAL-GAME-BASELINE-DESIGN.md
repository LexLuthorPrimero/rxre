# FASE E — REAL-GAME BASELINE — Documento de Diseño

> **Archivo:** `FASE-E-REAL-GAME-BASELINE-DESIGN.md`
> **Fase:** FASE R-2 — COMPLETE PROJECT DOCUMENTATION & ECOSYSTEM ARCHITECTURE (R-2.3)
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL (DISEÑO; NO ejecutado)
> **Clasificación:** [DISEÑADO] — protocolo completo para que otro investigador ejecute SIN inventar pasos.
> **Estado global:** **PENDIENTE de ejecución** (bloqueado por ausencia de juego reproducible local, ver §3).

---

## 1. Objetivo

Establecer la **baseline de un juego real** (workload real reproducido, no sintético) para comparar sobre
la misma base el comportamiento de potencia/relojes/memoria que ya caracterizan los workloads sintéticos
(Vulcan) y Superposition (OpenGL). La motivación histórica: E-02/E2 (manifest) documentó que
**"no existe workload real reproducible local"** (juegos online = login; KOF XV = menú sin xdotool/wtype)
→ FASE E existe para **diseñar** cómo obtener esa baseline.

## 2. Alcance y límites

- **SÍ:** diseño del protocolo, criterios de selección del juego, criterios de válidez, telemetría.
- **NO (en esta fase):** instalar juegos, ejecutar benchmarks, tocar el sistema, escribir sysfs,
  programar contadores, modificar Mesa. Todo ello requiere autorización explícita posterior.
- **NO mezclar FASE E con:** E-03 (workload sintético Vulkan) ni Superposition (OpenGL estático). FASE E
  es una línea de evidencia propia. No fusionar métricas (Regla METRICS-DEFINITIONS: "NOT DIRECTLY COMPARABLE").

## 3. Estado actual documentado (contexto evidencial)

- **E2/E2-report:** candidatos descartados por no ser reproducibles localmente (Steam KOF XV = menú sin
  xdotool/wtype; resto online con login). → No existe aún ninguna corrida formal de FASE E.
- **R-15/Superposition** (`03-EXPERIMENTOS/R-14-SUPERPOSITION-DISSECTION/`) mostró que un load real-geometría
  **OpenGL** produce 22.31 W steady / 24.71 W pico (no VK). FASE E quiere ver lo mismo en un **motor real
  reiterable** (escena fija, mismo input, sin intervención manual).

## 4. Criterios de selección de juego (obligatorios, en orden)

1. **Reproducible** (requisito #1): escena/benchmark integrado que se repite idéntico sin intervención
   manual (timelapse, replay, benchmark integrado, fixed camera track).
2. **Native Linux O Vulkan/OpenGL**: no depende de wrappers que introduzcan confounders de capa.
3. **Offline**: no requiere servidor online ni login ni red.
4. **CPU razonable**: el sistema es i7-4790 (4C/8T); el juego no debe quedar CPU-bound a la resolución de
   trabajo (si lo queda, marcar como confounder observado, no descartar).
5. **≥ 30 s de régimen estable** por repetición (mínimo para estadística de régimen).
6. **RX 550 explícita**: para Vulkan usar ICD RADV y verificar el device `0x699f`;
   `MESA_VK_DEVICE_SELECT=1002:699f` es opcional y no se acepta sin verificación. Para GL,
   verificar con `glxinfo` que el contexto usa `DRI_PRIME=1` o la RX 550.
7. **Sin DRM/licencias**: trabajo local, sin microtransacciones, sin DRM online.
8. **Coste cero / de catálogo open source** preferido (ej. `supertuxkart` tiene demo con track fijo);
   cualquier instalación estará sujeta a autorización y a revisión de licencia.

Ejemplos DIRECCIONALES (no seleccionados aún; solo ilustran el perfil): juegos con benchmark de escena
fija (Xonotic con `+timedemo`, SuperTuxKart, GNU Rocket/0 A.D. con escena determinista), o demos de
motor (Unvanquished). **Ninguno ha sido validado en esta máquina todavía.**

## 5. Protocolo de ejecución (diseñado, por otro investigador con autorización)

### 5.1 Pre-condiciones del sistema (verificar y registrar en `state_initial.txt`)
- Identidad GPU: `lspci -nn | grep 1002:699f`; display en Intel HD 4600 (card0), RX550 en card1.
- DPM actual (`power_dpm_force_performance_level`), power1_cap (µW), pp_dpm_sclk/mclk, pp_power_profile_mode.
- Estado Kalm (verificar `pgrep`; NO asumir activo/inactivo), sesión Wayland/XWayland.
- Temperatura ambiente + temp inicial de la GPU.

### 5.2 Workload
- Usar la escena integrada del juego seleccionado (benchmark/timedemo/replay) que garantice **la misma
  escena cada repetición**.
- Resolución fija: derivada del FPS objetivo — comenzar en 1920×1080; si la CPU queda bound (FPS plano
  y busy_busy<95% con más carga GPU), documentar y usar la resolución de trabajo elegida explicitamente.
- VSync **OFF** (frame pacing medido por MangoHud/log propio, no por sincronización).
- Preset de calidad: el del juego, fixture fijo; documentar **exactamente** el preset usado.

### 5.3 Duración/repetisiones
- **Warm-up:** 20 s antes de la telemetría del régimen (o el marcador del juego si lo define).
- **Régimen:** ≥ 30 s por repetición.
- **Repeticiones:** N ≥ 5 pareadas por celda (mismo bloque que FASE D utiliza: intercalado A/B).

### 5.4 Telemetría (la MISMA taxonomía que el Lab K y FASE D)
- **sysfs amdgpu** (hilo dedicado 4-10 Hz): `gpu_busy_percent`, `mem_busy_percent`,
  `power1_average`/`power1_input` (µW), `pwm`/temp1, `pp_dpm_state`/`pp_dpm_sclk`/`pp_dpm_mclk`
  (niveles activos), vram/gtt (mem_info_*).
- **Frame-level:** MangoHud log CSV (FPS, frametime p50/p99) o contador propio si el juego expone.
- **CPU (secundaria):** `perf stat :u` breve por repetición (IPC/inst) SOLO si se sospecha CPU-bound.

### 5.5 Condiciones fijas (no variar entre repeticiones)
Escena, resolución, preset, duración, DPM (registro de `auto` o del perfil autorizado), VSync,
ventana/modo ventana-fullscreen (DDC; display es Intel, la RX550 headless — confirmar que el juego
renderice en RX550 y preséntese por la Intel sin sincronizar).

### 5.6 Criterios de validez de una corrida
| Clasificación | Criterio |
|---|---|
| **VALID** | telemetría completa (todas las muestras), sin faults del juego, escena idéntica, estado inicial/final registrado, sin crash del driver |
| **INVALID** | telemetría incompleta, juego crasheó, stdin no reproducido, cap jugado/no registrado |
| **OUTLIER** | estadístico: señal > 3×MAD frente al resto de la celda; se marca pero NO se elimina silenciosamente |
| **REPEATABLE** | la célula se ha reproducido en ≥2 bloques independientes con Δpower dentro del IC95% |

### 5.7 Restauración
Al terminar el bloque: restaurar TODA condición sysfs tocada (libretos en el manejador del runner) y
verificar con `state_final.txt` + readback. Regla: **WRITE-SUCCESS ≠ STATE-CHANGE VERIFIED**.

## 6. Hipótesis que FASE E puede discriminar (no afirmar sin ejecutar)

- H-E1: un juego real reproducible supera la `W_SMU` de los VK sintéticos (¿> 22.3 W?); una
  correlación posterior podría contrastar el **tipo de carga**, pero no confirmaría causalidad
  ni aislaría la API.
- H-E2: el régimen estable de MCLK 1500 se sostiene en un motor real que presiona memoria/texturas.
- H-E3: la relación SCLK:MCLK (documentada en E5b) se manifiesta en un motor real (costes de
  muestreo/geometría visibles a 1080 en lugar de enmascarados).

## 7. Dependencias
- Lab de telemetría de FASE K (si está lista: usarla; si no, el arnés de FASE D/generic runner).
- Autorización para instalar/descargar el juego candidato y su licencia.
- No depende de contadores HW (read-only).

## 8. Entregables de la fase (cuando se ejecute)
`runs/<juego>/<celda>/` con manifest/state_initial/tele-*.csv/res-*.csv/stdout + `RESULTADOS-FASE-E.md`
(tabla por juego/celda, clasificación VALID/INVALID/OUTLIER, IC95%, restauración verificada).

## 9. Conclusión del diseño
FASE E queda **DISEÑADA pero BLOQUEADA** por la ausencia de un juego reproducible local autorizado.
El protocolo anterior define exactamente qué seleccionar, cómo correr y cómo validar. Sin la selección e
instalación del candidato (autorización externa), la fase no puede ejecutarse. **No hay ningún resultado de
FASE E reportable hoy.**
