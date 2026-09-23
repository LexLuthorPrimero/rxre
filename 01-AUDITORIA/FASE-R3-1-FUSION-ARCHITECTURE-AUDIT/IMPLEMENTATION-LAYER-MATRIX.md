# IMPLEMENTATION-LAYER-MATRIX — Capa de implementación por fusión

> **Archivo:** `IMPLEMENTATION-LAYER-MATRIX.md`
> **Fase:** FASE R-3.1 — FUSION ARCHITECTURE AUDIT
> **Fecha:** 2026-09-22 — READ-ONLY
> **Categorías:** LAYER-ONLY · APPLICATION-LEVEL · DRIVER-ASSISTED · KERNEL-ASSISTED · FIRMWARE-ASSISTED ·
> HARDWARE-LIMITED. ("Capa de implementación" ≠ permiso de implementación.)

---

| Fusión | LAYER-ONLY | APPLICATION-LEVEL | DRIVER-ASSISTED | KERNEL-ASSISTED | FIRMWARE-ASSISTED | HARDWARE-LIMITED | Principal |
|---|---|---|---|---|---|---|---|
| **F1** jitter dual | ✔ observación de jitter (layer con heurística) | ✔ re-proyección + predicción requieren cooperation del engine | — | — | — | La *unión* de señales es limitada por ingeniería (falta MV real) | APPLICATION-LEVEL (con layer para observar) |
| **F2** tile atómico | ✔ tile app-side (binning en aplicación) | ✔ partial-redraw / renderArea | ✔ hints DCC/HTILE (si driver lo expusiera) | — | — | ✔ residencia L2 (no controlable en GFX8) → tile lógico solo app | APPLICATION-LEVEL (tile lógico), HARDWARE-LIMITED (residencia) |
| **F3** memoria invertida | — | ✔ hot-set userland (VIS/GTT + pre-fetch) | ✔ (conocer/habilitar DCC on-GTT: requerido en GFX8) | ✔ (TTM/GTT/moverate/VM flags: requeridos si se gestiona) | — | ✔ (L2 como pool: no hay API) | KERNEL/DRIVER-ASSISTED (gestión real) |
| **F4** auto-observación | ✔ recorder/captura (api_dump/gfxreconstruct) | ✔ governor frametime-feedback read-only | — | ✔ contadores per-frame (requiere acceso programático — NO AUTORIZADO hoy) | — | SPM en GFX8 UNKNOWN | APPLICATION-LEVEL (read-only hoy) + KERNEL (counters a futuro) |
| **F5** bypass ROP | ✔ | ✔ (compute rendering en app) | — | — | — | ✔ premisa de paridad (32 SP/ROP; DCC) → HARDWARE-LIMITED | HARDWARE-LIMITED; la pieza async = APPLICATION (con BERRETA) |
| **F6** reconstrucción | ✔ (capa lsfg-style de frame generation) | ✔ (integración en app/engine) | — | — | — | ✔ presupuesto BW/power/8 CUs | LAYER/APPLICATION (calibración); HARDWARE-LIMITED (1080p) |
| **F7** mini-engine | ✔ (partes cortas) | ✔ (motor GPU-driven app) | ✔ (dependencias de DCC/tiling optativas) | ✔ (opciones de memoria) | — | ✔ sistémico (recursos de 35 W) | CONCEPTUAL — ninguna capa única |

## Lecturas
- Ninguna fusión requiere hacer-por-mover **firmware/VBIOS/BIOS** → ninguna FIRMWARE-ASSISTED.
- Las únicas capas que exigen **kernel** son F3 (TTM/GTT real) y F4 (contadores per-frame) — ambas fuera de
  la ventana autorizada actual.
- **F1, F4-readonly, F6-calibración** son las únicas implementables HOY en APPLICATION/LAYER sin tocar
  driver/kernel/HW.