# 010 — `COMPUTE_PGM_RSRC1` decodificado: el bloqueo 1 resuelto

**Clasificación**: `READ_ONLY/EVIDENCE`
**Fecha**: 2026-09-29
**Estado**: `PGM_RSRC1_BITS = RESOLVED` (antes `NOT_DETERMINED`)
**Ámbito**: IA-1, `06-INGENIERIA-INVERSA/`
**Fuente primaria**:
`RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/gca/gfx_8_0_sh_mask.h`
(1 136 970 B)

---

## 1. El bloqueo estaba en mi búsqueda, no en los datos

En `009-blockers-status.md` §1 afirmé que los headers autogenerados de registros de IP **no
estaban en el repo**, y cerré la vía 1 con resultado negativo sobre esa base.

**Era falso, y el error fue dónde miré.** Los autogenerados **están** en el repo, en
`drivers/gpu/drm/amd/include/asic_reg/`. Busqué en `drivers/gpu/drm/amd/amdgpu/` y en
`include/`, y concluí que no existían. `amd/include/` es un subárbol hermano que no miré, y
contiene 1,1 MB de definiciones de registros de GFX8.

El razonamiento de `009` era correcto —los `__SHIFT` no podían estar en los ficheros `.c`— pero
la conclusión sobre dónde buscarlos no lo era. `kernel-devel` tampoco los trae: se instaló, y
`/usr/src/kernels/7.1.3-…/` no tiene ni un `.h` de registros de IP. **La instalación no era la
vía.**

> Lección, y es la segunda vez en este proyecto con el mismo cuerpo: `AGENTS.md` documenta tres
> casos de "se buscó donde no estaba y se concluyó que no existía". Uno fue mío en la Ronda 2
> (`vulkan.h`), este es el segundo. La diferencia es que aquí afirmé el resultado negativo
> **después de una búsqueda parcial**, y lo escribí con la misma seguridad que un hallazgo
> positivo.

## 2. `COMPUTE_PGM_RSRC1`: los 11 campos, con MASK y SHIFT

`gfx_8_0_sh_mask.h:8301-8320`, literal:

| Campo | MASK | SHIFT | Bits | Valor por defecto en el driver |
|---|---|---|---|---|
| `VGPRS` | `0x0000003f` | `0x0` | 5:0 | 0 |
| `SGPRS` | `0x000003c0` | `0x6` | 11:6 | **9** (`0x240`) |
| `PRIORITY` | `0x00000c00` | `0xa` | 11:10 | 0 |
| `FLOAT_MODE` | `0x000ff000` | `0xc` | 19:12 | 0 |
| `PRIV` | `0x00100000` | `0x14` | 20 | 0 |
| `DX10_CLAMP` | `0x00200000` | `0x15` | 21 | 0 |
| `DEBUG_MODE` | `0x00400000` | `0x16` | 22 | 0 |
| `IEEE_MODE` | `0x00800000` | `0x17` | 23 | 0 |
| `BULKY` | `0x01000000` | `0x18` | 24 | 0 / **1** |
| `CDBG_USER` | `0x02000000` | `0x19` | 25 | 0 |

**Once campos, los diez primeros con MASK+SHIFT.** Los bits 26-31 del registro no tienen campo
nombrado en este fichero. `OBSERVED`.

## 3. Validación cruzada: los 4 puntos que tenía encajan exactamente

En `009` registré cuatro valores observados sin poder explicar los bits. Se comprueban ahora
contra los MASK/SHIFT reales:

| Valor | Fuente | `VGPRS` | `SGPRS` | Residuo |
|---|---|---|---|---|
| `0x100004f` | `gfx_v8_0.c:1389` | **15** | **1** | `0x1000000` = `BULKY` |
| `0x240` | `gfx_v8_0.c:1410` | 0 | **9** | `0x0` |
| `0x3f` | `gfx_v9_0.c:4478` | **63** | 0 | `0x0` |
| `0xbf` | `gfx_v9_0.c:4495` | **63** | **2** | `0x0` |

**Los cuatro validad, sin residuo inesperado.** El comentario del driver
`VGPRS=15 (64 logical VGPRs), SGPRS=1 (16 SGPRs), BULKY=1` se reproduce exactamente.

**`BULKY` está en el bit 24, no en el 28.** En `009` escribí que el bit más alto era el 28
(`PLAUSIBLE` por posición). Es el 24. Un ensamblador que hubiera puesto el flag en el 28 habría
escrito fuera de todos los campos nombrados.

**La interpolación que me negué a hacer habría sido incorrecta.** `SGPRS=9 ↔ 0x240` y
`SGPRS=1 ↔ 0x4f` son compatibles con el campo en bits 6-9 (SGPRS = `(v >> 6) & 0x3F`, ancho 6),
con bits 6-8… no, con bits 6-11 (ancho 6) y también con bits 6-12 o cualquier otro
desplazamiento que encajase ambos puntos. Habría acertado por casualidad y no por método.

## 4. Corrección sobre dónde vive el grid: `PGM_RSRC1` NO lleva workgroups

En `007` y en la respuesta a IA-2 dije que el número de workgroups iba en `COMPUTE_PGM_RSRC1`.
**Es incorrecto.** `PGM_RSRC1` es el registro de **límites de recursos** (cuántos VGPR y SGPR
tiene el shader), y su propio comentario lo dice: `SGPRS=9 (80 GPRS)`.

Dos comprobaciones:

- **`WORKGROUP` no aparece ni una vez** en los 1,1 MB de `gfx_8_0_sh_mask.h`.
- GFX8 usa el término **threadgroup**: el registro es `COMPUTE_THREADGROUP_ID`, y
  `COMPUTE_RESOURCE_LIMITS` tiene un campo `TG_PER_CU` (*threadgroups per CU*).

El grid del dispatch va en **`COMPUTE_DIM_X/Y/Z`**, y ese es el que despacha
`PACKET3_DISPATCH_DIRECT`:

| Registro | Campo | MASK | SHIFT | Ancho |
|---|---|---|---|---|
| `COMPUTE_DIM_X` | `SIZE` | `0xffffffff` | `0x0` | 32 bits |
| `COMPUTE_DIM_Y` | `SIZE` | `0xffffffff` | `0x0` | 32 bits |
| `COMPUTE_DIM_Z` | `SIZE` | `0xffffffff` | `0x0` | 32 bits |

**Los tres payloads `8/1/1` de `DISPATCH_DIRECT` en `gfx_v8_0.c:1542-1544` son `COMPUTE_DIM_X/Y/Z`.**
Es decir: `DISPATCH_DIRECT` **sí** lleva las dimensiones del grid, en el packet, y no en un
registro aparte. Mi afirmación de la Ronda 3 de que "no lleva el número de workgroups" era
correcta **por el motivo equivocado**: las dimensiones del dispatch y el número de threadgroups
**son lo mismo**, y sí van en el packet.

Lo que **no** va en el packet es `COMPUTE_NUM_THREAD_X/Y/Z`, que están en `sgpr1_init_regs`
(`256*5` = 1280) y describen el **tamaño de cada threadgroup**, no el número de ellos:

| Registro | Campo | MASK | SHIFT |
|---|---|---|---|
| `COMPUTE_NUM_THREAD_X` | `NUM_THREAD_FULL` | `0x0000ffff` | `0x0` |
| `COMPUTE_NUM_THREAD_X` | `NUM_THREAD_PARTIAL` | `0xffff0000` | `0x10` |
| `COMPUTE_NUM_THREAD_Y` | `NUM_THREAD_FULL` | `0x0000ffff` | `0x0` |
| `COMPUTE_NUM_THREAD_Z` | `NUM_THREAD_FULL` | `0x0000ffff` | `0x0` |

**Relación que queda establecida:** el dispatch reparte `DIM_X/Y/Z` threadgroups sobre una
CU, y cada threadgroup tiene `NUM_THREAD_X/Y/Z` hilos. `sgpr1_init_regs` pone
`NUM_THREAD_X=1280` (5 workgroups × 256) y `DIM_X=8`, que es un subconjunto de ese total.

**`COMPUTE_NUM_THREAD_X` no lleva el número de workgroups**: es un par de 16+16 bits
(`FULL`/`PARTIAL`). Un ensamblador que lo tratara como un contador único escribiría un valor
en el campo equivocado.

## 5. `COMPUTE_RESOURCE_LIMITS`: validación del valor `0x1000000`

`sgpr1_init_regs` escribe este registro con `0x1000000` y el comentario `CU_GROUP_COUNT=1`.
Campos reales (`gfx_8_0_sh_mask.h`):

| Campo | MASK | SHIFT | Bits | En `0x1000000` |
|---|---|---|---|---|
| `WAVES_PER_SH` | `0x000003ff` | `0x0` | 9:0 | 0 |
| **`TG_PER_CU`** | `0x0000f000` | `0xc` | 15:12 | **0** |
| `LOCK_THRESHOLD` | `0x003f0000` | `0x10` | 21:16 | 0 |
| `SIMD_DEST_CNTL` | `0x00400000` | `0x16` | 22 | 0 |
| `FORCE_SIMD_DIST` | `0x00800000` | `0x17` | 23 | 0 |
| **`CU_GROUP_COUNT`** | `0x07000000` | `0x18` | 26:24 | **1** |

**El comentario del driver se confirma**: `CU_GROUP_COUNT = 1`. Y aparece algo que el driver
**no documenta**: `TG_PER_CU` queda a **0** en ese valor, y ese campo sí es el número de
threadgroups por CU. El driver lo deja sin inicializar. Qué significa un `TG_PER_CU` de 0
—default del hardware o valor que hay que fijar— **no se ha establecido**: `NOT_DETERMINED`,
y es un candidato a diferencia entre el comportamiento de referencia y el de un driver propio.

## 6. Dónde están los demás registros que un ensamblador necesita

`gfx_8_0_sh_mask.h` contiene 50 registros `COMPUTE_*` con sus campos. Los de la secuencia de
dispatch (`gfx_v8_0.c:1535-1564`):

| Registro en el código | Available | Campos |
|---|---|---|
| `mmCOMPUTE_PGM_LO` / `_HI` | sí | `PGM_LO`, `PGM_HI` |
| `mmCOMPUTE_PGM_RSRC1` | sí | 10 campos, §2 |
| `mmCOMPUTE_PGM_RSRC2` | sí | — |
| `mmCOMPUTE_USER_DATA_0..15` | sí | 16 registros |
| `mmCOMPUTE_STATIC_THREAD_MGMT_SE0` | sí | — |
| `mmCOMPUTE_NUM_THREAD_X/Y/Z` | sí | §4 |
| `mmCOMPUTE_RESOURCE_LIMITS` | sí | §5 |
| `mmCOMPUTE_DISPATCH_INITIATOR` | sí | `COMPUTE_SHADER_EN` entre otros |

**Los 50 registros `COMPUTE_*` de GFX8, con MASK y SHIFT de cada campo, están en ese fichero.**
Es el mapa de registers que `register-maps/gfx-v8-compute.md` esperaba y que no tenía.

## 7. Corrección pendiente en `register-maps/`

La plantilla de `register-maps/gfx-v8-compute.md` §3 lista `CP_RB_BASE`, `CP_RB_RPTR` y compañía
como **nomenclatura supuesta**, y lo dice. Siguen sin verificar: son registros del command
processor, no de `COMPUTE_*`, y están en otro fichero de la misma familia. **`DEFERRED`**, no
corregido en esta ronda.

## 8. Límites

- Los MASK/SHIFT son **`OBSERVED` de la fuente**, no validados contra hardware. La validación
  cruzada contra los cuatro valores del driver es consistente, y eso es un control real: si un
  shift fuese erróneo, alguno de los cuatro valores no encajaría.
- **`COMPUTE_RESOURCE_LIMITS.TG_PER_CU = 0`** y su efecto: `NOT_DETERMINED`.
- Los bits 26-31 de `PGM_RSRC1` sin campo nombrado: `NOT_DETERMINED`, y no se rellenan.
- `REG_FIELD_SHIFT(mmCOMPUTE_PGM_RSRC1, SGPRS)` sigue sin poder compilarse: los macros existen
  en `gfx_8_0_sh_mask.h` pero el `#include` que los expone no está en el árbol parcial. Se han
  leído directamente, que es lo que hace falta.
- El CRC32 del firmware y `GFX_HWIP` **siguen bloqueados** y sin cambio: `amdgpu_smc.c` no
  aparece en ningún árbol del repo, y `GFX_HWIP` requiere UMR.

## Procedencia

`gfx_8_0_sh_mask.h` líneas 8259-8320, leídas el 2026-09-29. Validación cruzada por aritmética de
máscara y desplazamiento contra los cuatro valores de `gfx_v8_0.c:1389,1410,1431` y
`gfx_v9_0.c:4478,4495`. Búsqueda de `WORKGROUP` en el fichero completo: 0 ocurrencias.
