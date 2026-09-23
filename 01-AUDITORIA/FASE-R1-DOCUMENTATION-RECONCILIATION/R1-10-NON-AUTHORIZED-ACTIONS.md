# R1-10 — ACCIONES NO AUTORIZADAS (marco de prohibición para el proyecto)

> **Tarea R-1.10** — FASE R-1 — 2026-09-22 — SOLO DOCUMENTAL
> Refuerza el bloqueo del proyecto: cada acción que NO puede realizarse, motivo, y qué se necesitaría para
> desbloquearla. Complementa «NO HACER» de MASTER-RESEARCH-STATUS.md y «congelado» del documento maestro.

---

## A. Escrituras hardware/driver (siempre NO AUTORIZADAS en esta fase)

| Acción | Motivo | Desbloqueo requerido |
|---|---|---|
| Programar contadores (`GRBM_PERFCOUNTER0_SELECT`, PERF_SEL, CP_PERFMON_CNTL, SPM, PKT3_EVENT_WRITE) | R-1 es read-only; ejecución D-3 requiere autorización nueva | Autorización explícita + PRE read-only + sanity idle + política de restauración |
| Escribir `power1_cap` | fuera de corrida autorizada con snapshot+readback+restore | FASE L con protocolo |
| Escribir `pp_dpm_sclk` / `pp_dpm_mclk` / pp_power_profile_mode | WRITE SUCCESS ≠ verificado; DPM puede elicitar estados inesperados | FASE I/L con readback + telemetría |
| Escribir `pp_od_clk_voltage` | OD no disponible (mask sin 0x4000) y es write | FASE L.0/L tras Capability Audit |
| Modificar `ppfeaturemask` | congelado explícitamente | nueva autorización |
| Extraer/alterar **VBIOS / SPPT / pp_table** | HIGH-RISK | investigación futura solo |
| Eliminar/actualizar **BIOS de la placa** | irreversible | NUNCA sin autorización de extremo riesgo |
| Escribir kernel/GRUB/DRM/KMS/amdgpu config | congelado | —

## B. Instalaciones / ejecuciones

| Acción | Motivo | Desbloqueo |
|---|---|---|
| Instalar benchmarks/instaladores | requiere revisión de licencia | revisión + autorización |
| Ejecutar juegos/benchmarks nuevos sin telemetría normalizada | resultados no comparables | FASE E/K framework |
| Diseñar/implementar BERRETA, Ghost Cache, GEO, memoria, RADV, PowerPlay | falta caracterizar bottleneck + documento de diseño | Fase de diseño autorizada |

## C. Reglas de lectura que SÍ están permitidas (read-only)

Lectura de sysfs (power1_input, gpu_busy, mem_busy, ppfeaturemask, od_*, clocks), telemetría pasiva (radeontop,
amdgpu_top monitoring), UMR snapshot (no programar), parsing/source-code research de documentación local o
repositorios (GPUPerfAPI v3.11.1, Mesa, kernel) — todo sin writes y sin PCMS.

## D. Recordatorios críticos

1. **WRITE SUCCESS ≠ STATE CHANGE VERIFIED** (R1-8 §3): un write que no dispara error no prueba nada por sí solo.
2. **Observability Perturbation**: medir puede alterar; documentar la perturbación esperada (R1-8 §7).
3. **CONGELADO** (no tocar): WORKLOAD-SINTETICO, BIOS/VBIOS/SPPT/pp_table, ppfeaturemask, Kalm writes, Mesa
   sistema, GRUB/kernel/DRM, configuraciones permanentes sysfs.
4. Todo experimento futuro debe ser **reversible** (snapshot → write → readback → restore → readback).

---

**Confirmación read-only:** este marco no ejecuta ninguna de las acciones; solo documenta su prohibición y vías
de desbloqueo futuro. No se escribió nada en el sistema durante R-1.