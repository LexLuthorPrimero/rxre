# FUSION 03 — "INVERTIR LA JERARQUÍA DE MEMORIA"

> **Archivo:** `FUSION-03-INVERTED-MEMORY-HIERARCHY.md`
> **Fase:** FASE R-3.1 — FUSION ARCHITECTURE AUDIT
> **Fecha:** 2026-09-22 — READ-ONLY
> **Categoría de fusión:** RAM → hot set comprimido → VRAM → L2 → CU

---

## 1. Auditar los hechos del subsistema (VERIFICADO local)

| Parámetro | Valor | Estado |
|---|---|---|
| PCIe negociado | **5.0 GT/s (Gen2) ×4** — techo del **root port** (00:01.0, cap 5.0 GT/s); la tarjeta es capaz de 8.0 GT/s ×8 pero la plataforma no lo permite | VERIFICADO (sysfs) |
| Payload efectivo estimable | Gen2×4 ≈ **2.0 GB/s por dirección** (~500 MB/s/lane) | DERIVADO (20 GT/s ÷ 10 8b/10b); overhead TLP → ESTIMATED ≈1.4–1.9 GB/s |
| VIS-VRAM (CPU-visible) | **256 MB** (hard cap BAR) | VERIFICADO (sysfs) |
| VRAM total / GTT | 2 GB / **6.2 GB** (=5.77 GiB) | VERIFICADO (sysfs) |
| GTT | RAM del sistema mapeada vía GART | VERIFICADO (kernel docs) |
| Migration rate por defecto | `moverate=-1` → **8 MB/s** | VERIFICADO (module-params) |
| VRAM bus | 128-bit GDDR5; mclk 1500 MHz → **96–112 GB/s (ESTIMATED)** | VERIFICADO mclk (sysfs) + ESTIMATED re-derivación (ver adenda) |

**Lectura A — "PCIe es el cuello dominante":** VERIFIED como hipótesis para cualquier tráfico
host↔GPU que cruce PCIe (**factor ~×48–80 frente a VRAM**, corregido en R-4A; era ×24–32 con 48 GB/s). PERO
para workload GPU-puro (sin I/O host) el cuello sigue siendo VRAM side. No es "el" cuello universal, es "el
cuello del camino host".

> **ADENDA R-4A (EXP-F3-A, 2026-09-22):** la medición read-only confirmó Gen2×4 por techo del bridge,
> GTT=6.2 GB, VIS=256 MiB, cap 35 W. El modelo de *bandwidth* previo (48 GB/s, ratio ×24–32) se **corrige**:
> con mclk 1500 MHz y factor GDDR5 (cross-check R9 290/RX 480), la VRAM teórica es **96–112 GB/s** y el ratio
> enlace/VRAM sube a **×48+** (×50–80 con overhead PCIe). Las conclusiones de esta fusión **no cambian de
> dirección** (la brecha es aún mayor), solo de magnitud. Bandwidth REAL (medido) sigue UNKNOWN/REQUIRES
> FUTURE EXPERIMENT. Detalle en `experiments/FASE-R4A-BANDWIDTH-REAL/EXP-F3-A-BANDWIDTH-REAL.md`.

## 2. ¿Puede la compresión cerrar la brecha PCIe?

**CONTRADICTED como claim de paridad de bandwidth.** Evidencia GPUOpen (primaria):
- DCC es compresión **RGBA delta por bloque** en el **Color Block (ROPs)**; ahorra **ancho de banda interno
  GPU** (L2/VRAM), NO PCIe.
- El grosor por copy-engine/CDN **descomprime** ("no sabemos a dónde va"); UAV/shader writes **deshabilitan
  DCC**; partial writes → read-decompress-modify-write.
- PC-Delta (CUDARaster-style) comprime la **CPU side**, no el tráfico PCIe.

Incluso a 8:1 (mejor DCC), un GTT-path comprimido no alcanza a compensar el factor **×48–80** de PCIe Gen2×4
vs VRAM (corregido en R-4A; antes ×24–32). La afirmación "GTT comprimido puede competir con el camino VRAM" es
**CONTRADICTED como
bandwidth-equivalente**. La versión débil ("para datos que YA residen en RAM, el camino GTT es el único, y
L1/L2 amortiza re-lecturas") es **PARTIALLY VERIFIED** y defendible.

## 3. ¿Dónde está el ahorro real?

Contribuciones que SÍ son reales:
1. **Evitar materializar en VRAM**: si un tile/textura se re-lee N veces desde GTT y N es alto, L2 amortiza.
2. **Compresión delta en aplicación** (hot set → deltas): ahorro de *bytes sobre el cable* — trabajo de I-02/
   RX-Compression-Engine, pero NO es DCC ni "L2-residencia".
3. **Working-set pequeño en VIS-VRAM (256 MB)**: lo único CPU-visible; la lógica "render pequeño → VIS"
   es viable y es el sub-producto útil de esta fusión.

## 4. ¿"L2" es el destino correcto?

**NO (por topología).** L2 = 512 KB, CB/DB bypass L2, sin API de residencia/pinning (amdgpu no expone
L2-residency; control = hints VM, flush/streaming). L2 sirve a la ruta **shader** (texture reads, compute
UAV reads). Para una arquitectura de "hot set", el destino gestionable a nivel usuario es **VIS-VRAM/GTT +
prefetch/userland** (I-06), no L2.

## 5. Cómo verificar (read-only) en una fase futura — REQUIRES EXPERIMENT

- `debugfs:/amdgpu_benchmark` (GTT vs VRAM vs DMA bandwidth reales en esta máquina).
- Establecer la fracción de payload PCIe real (gpu-pcie-bench, run local futuro).
- Determinar si RADV/radeonsi habilitan DCC para imágenes GTT (HOST_VISIBLE no device-local) en GFX8
  (si_dcc — estado actual UNKNOWN).
- Medir el ratio de re-lecturas de un tile GTT-residente (ES-01/F2 hosts).

## 6. Falsabilidad

Hipótesis falsable: *"para un workload con fetch frecuente a datos residentes en RAM, la ruta GTT con
re-lectura por L2 produce mejor frametime que forzar la misma data a VRAM"* — falsable comparando
frametime/power en harness con data GTT vs VRAM, telemetría read-only. La versión "compresión cierra la
brecha PCIe" es **falsa por aritmética** (bandwidth).

## 7. Veredicto de fusión

- Alguno componente útil (hot set real, VIS 256 MB como buffer, delta compresión en app).
- La columna vertebral ("comprimir para que RAM compita con VRAM") **CONTRADICTED**.
- **Estado:** **NEEDS PRECONDITION** (faltan mediciones de bandwidth real de este sistema + estado DCC-GTT).