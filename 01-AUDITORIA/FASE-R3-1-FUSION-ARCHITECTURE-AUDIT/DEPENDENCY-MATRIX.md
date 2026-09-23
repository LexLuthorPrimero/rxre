# DEPENDENCY-MATRIX — Dependencias por fusión

> **Archivo:** `DEPENDENCY-MATRIX.md`
> **Fase:** FASE R-3.1 — FUSION ARCHITECTURE AUDIT
> **Fecha:** 2026-09-22 — READ-ONLY
> **Estados:** REQUIRED · OPTIONAL · NOT REQUIRED · UNKNOWN

---

| Fusión | D-3 counters | Vulkan layer | Mesa | Kernel | RX Compression | Ghost Cache | BERRETA | Orquestador |
|---|---|---|---|---|---|---|---|---|
| **F1** jitter dual | NOT REQUIRED | **REQUIRED** (observación de jitter/push constants) | NOT REQUIRED | NOT REQUIRED | NOT REQUIRED | OPTIONAL (colabora para predicción) | OPTIONAL (temporalidad) | OPTIONAL (ruta de telemetría) |
| **F2** tile atómico | **REQUIRED** (si reclama residencia/L2, único modo de verificar) | OPTIONAL | OPTIONAL (control DCC/HTILE hints, si se toca) | NOT REQUIRED | OPTIONAL | OPTIONAL | OPTIONAL | OPTIONAL |
| **F3** memoria invertida | UNKNOWN (para tráfico MC) | OPTIONAL | **REQUIRED** (estado DCC-on-GTT GFX8 — conocimiento; no modificación) | **REQUIRED** (TTM/GTT/moverate/VM flags, si se gestiona) | **REQUIRED** (hot set comprimido = núcleo) | OPTIONAL | NOT REQUIRED | OPTIONAL |
| **F4** auto-observación | **REQUIRED** (feedback de contadores del sistema) | OPTIONAL (recorder) | OPTIONAL | REQUIRED (contadores per-frame; SPM UNKNOWN) | NOT REQUIRED | NOT REQUIRED | NOT REQUIRED | **REQUIRED** (integración del lazo) |
| **F5** bypass ROP | **REQUIRED** (para medir ROP-vs-CU y falsar) | OPTIONAL | OPTIONAL | NOT REQUIRED | NOT REQUIRED | NOT REQUIRED | OPTIONAL (async co-scheduling) | OPTIONAL |
| **F6** reconstrucción | OPTIONAL | OPTIONAL | NOT REQUIRED | NOT REQUIRED | NOT REQUIRED | NOT REQUIRED | **REQUIRED** (overlap async: pregunta compartida) | OPTIONAL |
| **F7** mini-engine | UNKNOWN | OPTIONAL | UNKNOWN (si toca DCC/tiling de imágenes) | UNKNOWN | OPTIONAL | OPTIONAL | OPTIONAL | **REQUIRED** (hub de integración) |

## Notas de lectura
1. **D-3 counters** aparece como REQUIRED justo en las fusiones que más dependen de ver *tráfico que la
   telemetría read-only no ve* (L2/MC: F2, F4, F5) — y que siguen bloqueadas por autorización. Las fusiones
   cuya medición se puede hacer con frametime/power (F1, F6, F3 parcial) no la necesitan.
2. **Mesa/Kernel** figuran como REQUIRED/UNKNOWN solo donde *se necesita conocimiento o control* del driver
   (DCC-GTT en F3) — nunca como modificación (prohibida).
3. **"UNKNOWN"** se reserva para: SPM/counters per-frame (F4), tráfico MC (F3), control de tiling de
   imágenes en F7.