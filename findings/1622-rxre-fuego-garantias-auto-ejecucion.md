# 1622 — FUEGO: garantías exigidas antes de auto-ejecución (documento, sin implementar)

- Fecha: 2026-10-15
- Clasificación: **REQUISITOS / NO VERIFICADA** — no existe auto-ejecución en
  RXRE; este documento fija qué debe cumplirse ANTES de encenderla. No se
  implementa nada de esto en este ciclo.

## Estado medido de las defensas actuales

| Defensa | Estado | Evidencia |
|---|---|---|
| allow-list de PCI | SÍ: `umr_read.ALLOWED_PCI`; `op:verify` reporta `intel_igp_blocked` | `machine.py:114-136` |
| allow-list de capabilities | SÍ: `dispatch.ejecutar` llama `esta_permitida` ANTES de invocar; denegada → `blocked` + motivo | `dispatch.py:759-770` |
| PRE_EXECUTION_CONTRACT_CHECK | SÍ por adaptador: existencia, firma, backend, entrypoint | medido en CUERPO hoy (PE, no-ELF, chmod 000) |
| timeouts | SÍ: `DISPATCH_TIMEOUT=600` (safety net) + adapter 900 default + parámetro `timeout` | `dispatch.py:69-74` |
| sin shell | SÍ: 0 usos de `shell=True` en `tools/rxre` | `grep -rn "shell=True"` → 0 |
| event-log durable | SÍ: `execution_events` (run=76, plan=0 en DB viva) | esquema + `registrar_evento` |
| reversibilidad de mutaciones | PARCIAL: `mutate` (CLI) opera en copias/scratch; backup/restore de `target.py` | `test_cli009`; `cmd_mutate` |
| auto-ejecución | **NO EXISTE**: ningún camino ejecuta capabilities sin `op` explícita; `scan`/`saturate` solo registran fronteras y sugieren `next_actions` | `HANDLERS` en `machine.py` |

## Requisitos (cada uno con su prueba de aceptación)

### R1. Permisos
- Quién autoriza una auto-ejecución; por capacidad Y por artefacto (path), no
  solo por nombre de capacidad.
- Prohibiciones duras: root NO; iGPU `0000:00:02.0` NO; escritura a hardware NO.
- Declarar en el registry qué capacidades son read-only y cuáles mutan estado.
- Prueba: capability no permitida jamás corre; con contexto de auto-ejecución
  nunca se invoca root.

### R2. Reversibilidad
- Toda escritura: backup previo + restore probado + hash de antes/después.
- DB: una transacción por auto-ciclo; rollback ante fallo a mitad.
- Prueba: ciclo que falla a mitad → estado idéntico al inicial (hash por
  archivo + filas DB contadas).

### R3. Costos (el caso REAL de hoy)
- Presupuesto por ciclo: N ejecuciones, segundos, MB de disco, tamaño de
  artefacto.
- MEDIDO hoy: `/tmp` estaba **100% lleno** (tmpfs 5.9G, 0 disponible) por una
  copia de trabajo de 5.2G de otro proceso; un auto-loop que escriba scratch
  sin presupuesto de disco se auto-bloquea o corrompe. El presupuesto de disco
  NO es teórico: es el estado del entorno ahora.
- Estimación ANTES de ejecutar (plan con costo) y aborto ANTES del límite.

### R4. Stop conditions
- Guard de bucle: misma capability+params+hash de input N veces → STOP.
- No-progreso: si un ciclo no agrega finding/result nuevo → STOP.
- Errores duros: disco lleno, permiso denegado, timeout → STOP limpio, sin
  reintento ciego.
- Kill externo: señal respetada a mitad de operación; salida con estado
  consistente (sin operaciones a medias).
- Prueba: simulacro de cada stop (loop repetido, no-progreso, disco lleno).

### R5. Observabilidad
- Cada auto-run → `execution_events` con quién/qué/por qué y gasto consumido.
- Contador legible: ciclos, ejecuciones, tiempo, disco.

## Discriminante

La auto-ejecución NO se enciende hasta que R1–R5 tengan prueba de aceptación
que pase en seco (sin hardware, sin root). Mientras eso no ocurra, cualquier
claim de "FUEGO autónomo" es NO VERIFICADA por definición.

## Lo que este documento NO afirma

- NO hay auto-ejecución implementada. Este documento son requisitos.
- Los timeouts y allow-lists citados son defensas ACTUALES medidas; no
  constituyen por sí mismos garantías de auto-ejecución.
