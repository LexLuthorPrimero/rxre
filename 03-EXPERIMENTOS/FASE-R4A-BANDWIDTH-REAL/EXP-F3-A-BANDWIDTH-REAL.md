# EXP-F3-A — Bandwidth REAL: PCIe / VRAM / GTT (FASE R-4A)

> **Archivo:** `EXP-F3-A-BANDWIDTH-REAL.md`
> **Fase:** FASE R-4A — resuelve la precondición de FUSION-03 (R-3.1)
> **Fecha:** 2026-09-22 — **READ-ONLY estricto**
> **Regla fundamental:** NINGUNA cifra teórica se convierte en "bandwidth real". Toda cifra se etiqueta
> VERIFIED (leída) / DERIVED (aritmética sobre VERIFIED) / ESTIMATED (modelo con supuesto no medible
> localmente) / UNKNOWN.

---

## 0. Método y restricciones respetadas

Interfaces consultadas (todas de **solo lectura**; ninguna escritura):

| # | Interfaz | Resultado |
|---|---|---|
| P1 | `lspci -s 01:00.0 -vv` | identificó `Lexa PRO [Radeon 540/550/540X/550X]`, dev 0x699f ven 0x1002 |
| P2 | `/sys/bus/pci/devices/0000:01:00.0/{current,max}_link_{speed,width}` | **LEIDO** (VERIFIED) |
| P2b | `/sys/bus/pci/devices/0000:00:01.0/{current,max}_link_{speed,width}` (root port) | **LEIDO** (VERIFIED) |
| C1 | `/sys/class/drm/card1/device/mem_info_*` | **LEIDO** (VERIFIED) |
| C2 | `/sys/class/drm/card1/device/pp_dpm_{mclk,sclk}`, `power_profile` | **LEIDO** (VERIFIED) |
| C3 | `/sys/class/drm/card1/device/hwmon/hwmon2/{power1_cap,power1_input}` | **LEIDO** (VERIFIED; sin energy1_input) |
| D1 | `/sys/kernel/debug/dri/1/amdgpu_benchmark` | **DENEGADO** (sin sudo sin-password) — lectura que, por código del driver, devuelve solo "usage"; las transferencias corren exclusivamente en `.write`. No legible esta sesión. |
| D2 | `/sys/kernel/debug/dri/1/amdgpu_pm_info` | **DENEGADO** (sin sudo) |
| E1 | `dmesg` | **DENEGADO** (sin privilegios; /dev/kmsg root) |

- No se escribió registro alguno; no se tocó `power1_cap`, `pp_dpm_*`, runtime-PM, `ppfeaturemask`, clocks, GRUB, Mesa, kernel. No se creó workload ni se ejecutó benchmark. **D1 nunca se escribiría** (equivaldría a ejecutar benchmarks del driver).
- Lo no legible sin root → etiquetado `REQUIRES FUTURE EXPERIMENT` (lectura bajo sudo autorizado) o `UNKNOWN`.

## 1. Resultados VERIFIED (leídos del sistema)

| Dato | Valor | Fuente |
|---|---|---|
| Enlace PCIe negociado (device 01:00.0) | **5.0 GT/s (Gen2), ancho ×4** | sysfs `current_link_speed`/`current_link_width` |
| Capacidad del endpoint | **8.0 GT/s (Gen3) ×8** | sysfs `max_link_speed`/`max_link_width` |
| **Capacidad del root port (00:01.0) — techo real** | **5.0 GT/s (Gen2)**, current ×4, max ×16 | sysfs del bridge |
| VRAM total | 2147483648 B = **2 GiB** | `mem_info_vram_total` |
| VIS-VRAM (CPU-visible) | 268435456 B = **256 MiB** | `mem_info_vis_vram_total` |
| GTT total | 6195675136 B ≈ 5.77 GiB (**6.2 GB**) | `mem_info_gtt_total` |
| VRAM usada (ocio) | 5.5 MB | `mem_info_vram_used` |
| VIS/GTT usados (ocio) | 5.4 MB / 11.2 MB | `mem_info_*_used` |
| Power cap hwmon | 35000000 µW = **35 W** | `hwmon2/power1_cap` |
| Power instantáneo (ocio) | 3672000 µW ≈ **3.7 W** | `hwmon2/power1_input` |
| DPM MCLK (estados) | 300 / 625 / **1500 MHz** (ocio en 300) | `pp_dpm_mclk` |
| DPM SCLK (estados, 8) | hasta **1071 MHz** | `pp_dpm_sclk` |
| Perfil de potencia | `3D_FULL_SCREEN *`; readout local de MCLK `3/16/20`; el mapping de campo/perfil frente al valor upstream `5/16/20` queda `UNRESOLVED` | `pp_power_profile_mode` |

**Lectura clave del enlace:** el endpoint declara capacidad máxima Gen3×8, pero la
plataforma de este host tiene un techo negotiated Gen2; el enlace efectivo observado es
Gen2×4. Esto distingue capacidad del endpoint, negociación local y ancho efectivo.

## 2. Resultados DERIVED (aritmética sobre VERIFIED)

| Cifra | Cálculo | Valor |
|---|---|---|
| Clocks Gen2 ×4 teórico, por dirección | 5.0 GT/s × 4 = 20 GT/s ÷ 10 (8b/10b) | **2.0 GB/s por sentido** |
| PCIe Gen2 ×4 agregado | 2 × 2.0 GB/s (duplex) | **4.0 GB/s ida+vuelta teórico-max** |
| VRAM teórica (SI: factor GDDR5 mclk×4, 128-bit) | 1500 MHz × 4 = 6.0 GT/s × 16 B | **96 GB/s** (ver ESTIMATED, §3) |
| Ratio enlace vs VRAM | 2.0 / 96 | **≈ ×48** el VRAM es más rápido que el enlace |

## 3. Resultados ESTIMATED (modelo, no medido localmente)

| Cifra | Supuesto | Valor |
|---|---|---|
| Payload efectivo PCIe ~Est | overhead TLP (headers 12–20 B / payload 128–256 B) + flow control | **≈1.4–1.9 GB/s por sentido** (no medido) |
| VRAM teórica ~Est | factor GDDR5 de `mclk×4` NO verificable localmente (sin info de módulo) ; rango nominal del SKU 112 GB/s | **96–112 GB/s** y dev/pendiente de identificación del módulo |
| Ratio enlace/VRAM corregido | con payload 1.4–1.9 vs 96–112 | **×50–80** (antes FUSION-03 decía ×24–32 con 48 GB/s — corregido) |

> **Justificación del factor ×4 de GDDR5 (no medible en esta máquina):** en amdgpu, R9 290 (Hawaii) reportaba
> mclk 1250 MHz ↔ 5.0 Gbps público → 5.0e9×64 B = 320 GB/s ✓; RX 480 reportaba 2000 MHz ↔ 8.0 Gbps público →
> 8.0e9×32 B = 256 GB/s ✓. Ambos cumplen `data_rate = mclk × 4`. Con Polaris12 (128-bit) y mclk 1500 MHz →
> 6.0 GT/s × 16 B = **96 GB/s** si los módulos son de 6 Gbps; el SKU nominal RX550 = 7 Gbps (112 GB/s). La
> distinción 96 vs 112 depende del módulo instalado → **UNKNOWN** hasta identificación del VBIOS/memtype.

## 4. Resultados UNKNOWN / REQUIRES FUTURE EXPERIMENT

| Pregunta | Estado | Por qué / cómo cerrarla |
|---|---|---|
| ¿Bandwidth REAL (medido) PCIe/GTT/VRAM de esta máquina? | **UNKNOWN** | No hay interfaz de lectura sin ejecutar pruebas. `amdgpu_benchmark` corre pruebas SOLO con `.write` (prohibido aquí). Cerrar con corrida autorizada (sudo read-only de debugfs para "usage", o benchmark aprobado explícitamente = **FUTURE**) |
| ¿GTT es constante? | **UNKNOWN / NO es constante** | GTT = páginas de RAM del CPU; su bandwidth efectivo lo domina el ancho de banda DRAM del sistema y la carga; NO es parámetro fijo de la GPU. Medirlo = harness dedicado (future) |
| ¿Factor ×4 GDDR5 de este módulo? | **UNKNOWN** | requeriría lectura de memtype/espejo VBIOS (sudo) |
| ¿Se negociaría ×8 (Gen2) si el slot lo permitiera? | **UNKNOWN** (irrelevante hoy) | el techo de velocidad del bridge = Gen2; ×8 Gen2 daría 4.0 GB/s teóricos por sentido, aun así ≪ VRAM |
| `amdgpu_benchmark` leer "usage" ahora | **REQUIRES FUTURE EXPERIMENT** (sudo) | permiso denegado esta sesión; la lectura es inocua por diseño del driver |

## 5. Incertidumbres de FUSION-03: resueltas vs restantes

**Resueltas (ahora con evidencia VERIFIED/DERIVED/ESTIMATED):**
- El enlace real observado es **Gen2×4**; la capacidad máxima declarada del endpoint
  (Gen3×8) no equivale al modo negociado de esta plataforma.
- El ratio PCIe-vs-VRAM nominal/estimado es aproximadamente ×48–80; no representa
  bandwidth VRAM real ni una atribución causal universal.
- GTT "6.2 GB" y VIS-VRAM 256 MiB son capacidades observadas, no bandwidth.
- La magnitud de brecha sigue siendo una estimación; el payload PCIe real permanece
  `UNKNOWN`.

**Restantes (no cerradas en R-4A):**
- Payload efectivo PCIe real (necesita medición) → ESTIMATED, no VERIFIED.
- Bandwidth GTT real (no es propiedad de la GPU; depende del sistema) → UNKNOWN.
- 96 vs 112 GB/s (módulo GDDR5) → UNKNOWN.
- DCC-on-GTT (si_dcc) → sigue UNKNOWN (ver R-3.1).

## 6. Checklist de cumplimiento (FASE R-4A)
- [x] Solo interfaces de lectura; sin escrituras de registros.
- [x] Sin cambios en power1_cap / DPM / clocks / runtime-PM / ppfeaturemask / GRUB / Mesa / kernel.
- [x] Sin workload nuevo; sin benchmark ejecutado.
- [x] `amdgpu_benchmark` MANEJADO como read-only; aun así bloqueado por permisos (documentado, no forzado).
- [x] Todo lo que requería cambiar estado → marcado REQUIRES FUTURE EXPERIMENT.
- [x] Separación VERIFIED / DERIVED / ESTIMATED / UNKNOWN en cada cifra.
- [x] Ninguna cifra teórica presentada como "bandwidth real".
- [x] Única documentación actualizada: este informe + notas FUSION-03 + MASTER-RESEARCH-STATUS (v2.8).
