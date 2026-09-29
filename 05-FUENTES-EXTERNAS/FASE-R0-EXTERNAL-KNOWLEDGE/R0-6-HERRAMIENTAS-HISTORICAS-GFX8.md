# R0-6 — Herramientas históricas con tablas de Event IDs GFX8 (GPUPerfAPI/CodeXL/UMR/etc.)

> **Archivo:** `R0-6-HERRAMIENTAS-HISTORICAS-GFX8.md`
> **Fase:** FASE R-0 — EXTERNAL KNOWLEDGE RECOVERY
> **Fecha:** 2026-09-22 — Modo SOLO DOCUMENTAL
> **Clasificación:** [VERIFICADO source-level] (presencia/características de herramientas
> verificadas por repos/README/release notes; no prueba runtime del ASIC)
>
> **RECONCILIACIÓN 2026-09-24:** `v3.17` es la referencia operativa recomendada para
> tablas GFX8; `v3.11.1` queda como extracción histórica. La presencia de tablas no prueba
> aplicabilidad al ASIC Polaris12 ni seguridad de programación.

---

## 1. Propósito

Catalogar qué herramientas/proyectos históricos (AMD y comunidad) **contienen** o **alguna vez
contuvieron** tablas de contadores GFX8. `v3.17` es la referencia operativa recomendada
para tablas GFX8; `v3.11.1` queda como extracción histórica. Ninguna presencia de catálogo
prueba aplicabilidad al ASIC Polaris12 o seguridad de programación. El resto de herramientas
citadas son conocimiento con estado de disponibilidad variado.

## 2. Herramientas y estado

| Herramienta | Repo/Tipo | Estado | ¿Tablas GFX8? | Notas |
|---|---|---|---|---|
| **GPUPerfAPI** (v3.17; v3.11.1 histórico) | GitHub AMD `GPUOpen-Tools/gpu_performance_api` | Abierto; catálogo GFX8 genérico | **CATÁLOGO** (no validación ASIC) | v4.0+ eliminó GCN; v3.17 es referencia de tablas y v3.11.1 extracción histórica |
| **CodeXL** | AMD, antiguo (SUPONTO software, Artes "GPUOpen") | EOL/archivado | Sí (en versiones antiguas con GPUPerfAPI integrado) | Se usó para perf counters en VI; código semi-histórico; no accesible hoy como tabla simple |
| **RGP (Radeon GPU Profiler)** | AMD | Moderno | **NO** para GFX8 en versiones modernas; compatibilidad GCN-era histórica no implica runtime local | RGP 2.x es RDNA; soporte GCN histórico y viewer GFX8 siguen `UNKNOWN` |
| **UMR (User Mode Register)** | `GPUOpen-Tools/umr` | Abierto | Solo DB de REGISTROS (`gfx_8_0_0.reg`), **NO event IDs** | Ya auditado localmente (FASE D): CERO enums con valores de evento |
| **radeontop** | Libre | Activo | Solo carga vía `gpu_busy`/reg, no tabla eventos | Herramienta operacional (FASE D), sin valores PERF_SEL |
| **si_perfcounter.c** (Mesa radeonsi) | Mesa | Actual | **NO** (solo passthrough de selectores; tabla VI eliminada hace años) | Confirmado por Fossies (versión actual) — la tabla VI entró/salió; ramas antiguas la tienen (ver "MAEMO-LESTE fork") |
| `r600_perfcounter.c` (Mesa) | Mesa | Actual | Solo GFX6 (SI) | No GFX8 |
| **amdgfxregs.h** (Mesa) | Mesa | Actual | Sin enums PERF_SEL completos | Auditar local |
| **llvm** (AMDGPU backend) | LLVM | Activo | No (sin tablas eventos) | — |

## 3. Acciones posibles (Documental) en base a esta FASE

- **D1** (hecha): extraer tabla `exposed_gfx8_reference.txt` (2304 filas) desde GPUPerfAPI
  v3.11.1 → ver R0-1. Es una referencia histórica de catálogo, no una tabla de eventos
  validados para Polaris12.
- **D2** (opcional futura, SOLO documental): si se desea citar nombres de catálogo por
  bloque (ej. `SPI0_PERF_VS_BUSY`, `SQ0_PERF_SEL_WAVES`), la referencia R0-1 ya los
  incluye; no se necesitan para autorizar programación.
- **D3**: constatar que GPUPerfAPI v4.x/master ya no sirve para GFX8 (validado: en v4.0 release
  notes "Removed support for GCN"; los builds modernos usan PMU RDNA). Para tablas GFX8
  usar `v3.17` como referencia; `v3.11.1` queda histórico.

## 4. Fuentes

1. Repo GPUPerfAPI (GitHub AMD):
   https://github.com/GPUOpen-Tools/gpu_performance_api
   - Tag v3.11.1 → README y RELEASE_NOTES (GRÁFICA: "Supports … IP version 8 and newer"; v4.0:
     "Removed support for GCN (ie: GFX8 and GFX9)")
2. Fossies si_perfcounter.c (Mesa actual, sin tablas VI):
   https://fossies.org/linux/mesa/src/gallium/drivers/radeonsi/si_perfcounter.c
3. UMR (local) — `gfx_8_0_0.reg`: ya verificado en FASE D (solo regs, sin eventos).
4. Radeon Top (active) — https://github.com/clbr/radeontop (conocimiento general).

## 5. Confianza y límites

- [VERIFICADO source-level] presencia de tablas GFX8 en GPUPerfAPI v3.17/v3.11.1;
  la aplicabilidad al ASIC y la seguridad de programación siguen `UNKNOWN`.
- [VERIFICADO] ausencia de GCN en v4.0+ (release notes del mismo repo).
- Para CodeXL/RGP la verificación es indirecta (fecha EOL y notas de soporte AMD);
  no se afirma su estado interno sin repositorio consultado.
- **No aplicar**: nada de lo anterior habilita escritura de contadores. Sigue prohibido programar
  y escribir MMIO/sysfs.
