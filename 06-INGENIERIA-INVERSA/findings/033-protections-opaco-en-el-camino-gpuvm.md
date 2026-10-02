# 033 · `PROTECTIONS`: el campo que el hardware rellena y el driver no descompone en el camino GPUVM

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=RESEARCH/working/linux-7.1.3`
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=SCOPED(findings)` · `HARDWARE_SCOPE=HOST-C/RX550`
`RUNTIME=NOT_RUN` · `GPU INTACTA`

## CUDA principal

`PROTECTIONS` es un campo de **8 bits** que el hardware rellena cuando una traducción
falla, y hay exactamente **un** punto en todo el driver donde se descompone en campos de
permiso. Ese punto está detrás de un gate de KFD, así que **no es alcanzable desde el
camino GPUVM de userspace normal**: para el camino que un driver propio implementa, el
valor es un entero opaco.

Esto **recorta F2b de forma cualitativa**. F2b no es "no sé qué significa el bit X del
PTE": es que *el driver de referencia nunca necesita esa información en el camino que
nos interesa*. Eso es una frontera de implementación, no una laguna de análisis.

## 1 · Layout del registro, y su lectura completa

`VM_CONTEXT1_PROTECTION_FAULT_STATUS`, según `gmc_8_2_sh_mask.h`:

| campo | MASK | SHIFT | bits | posición |
|---|---|---|---|---|
| `PROTECTIONS` | `0x000000ff` | `0x0` | 8 | [7:0] |
| `MEMORY_CLIENT_ID` | `0x001ff000` | `0xc` | 9 | [20:12] |
| `MEMORY_CLIENT_RW` | `0x01000000` | `0x18` | 1 | [24:24] |
| `VMID` | `0x1e000000` | `0x19` | 4 | [28:25] |
| `ATOMIC` | `0x020000000` | `0x1d` | 1 | [29:29] |

Los tres registros que lo surround, leídos juntos en `gmc_v8_0.c:1446-1448`:
`mmVM_CONTEXT1_PROTECTION_FAULT_ADDR`, `_STATUS`, `_MCCLIENT`.

`VMID` cabe en **4 bits** y `AMDGPU_NUM_VMID = 16` (`amdgpu_ids.h:34`). Coherente: no hay
hueco entre los VMIDs que el hardware puede reportar y los que el driver asigna.

## 2 · Los dos caminos de decodificación, y por qué sólo uno aplica

Hay **dos** lugares que consumen `PROTECTIONS`, con comportamientos distintos:

| | sitio | qué hace | ¿gate? |
|---|---|---|---|
| A | `gmc_v8_0.c:1478` → `gmc_v8_0_vm_decode_fault` | imprime `protections` como byte crudo `0x%02x` | **ninguno** |
| B | `gmc_v8_0.c:1482-1501` | lo descompone en 4 banderas | `if (is_kfd_vmid(vmid))` |

El camino B:

```c
info->prot_valid = protections & 0x7  ? true : false;   /* bits 2:0, agrupados */
info->prot_read  = protections & 0x8  ? true : false;   /* bit 3 */
info->prot_write = protections & 0x10 ? true : false;   /* bit 4 */
info->prot_exec  = protections & 0x20 ? true : false;   /* bit 5 */
```

**5 de los 8 bits se descomponen. Los bits 6 y 7 no los descompone nadie.**

Y el gate, textualmente:

```
amdgpu_amdkfd.c:751-757   is_kfd_vmid(vmid) := vmid >= vm_manager.first_kfd_vmid
gmc_v8_0.c:1168           first_kfd_vmid = 8
amdgpu_ids.h:34           AMDGPU_NUM_VMID  = 16
```

⇒ **VMID 0-7 = DRM · VMID 8-15 = KFD.** Un proceso DRM nunca obtiene un VMID ≥ 8.

## 3 · GFX6 y GFX7 tampoco lo descompongan

Se buscó el mismo campo en las otras dos generaciones con la misma máscara:

| ASIC | `PROTECTIONS` leído | descompuesto | cómo |
|---|---|---|---|
| `gmc_v6_0.c` | sí (L617) | **no** | `dev_err(..., 0x%02x, ...)` byte crudo, L623 |
| `gmc_v7_0.c` | sí (L773) | **no** | `dev_err(..., 0x%02x, ...)` byte crudo, L782 |
| `gmc_v8_0.c` | sí (L1006, L1482) | **sólo KFD** | crudo para todos, descompuesto tras el gate |

**GFX8 es la única generación que lo descompone, y sólo para KFD.** La idea de que un
comparativo entre generaciones podría distinguir si los bits 0-2 son Fault-ID o permiso
**queda refutada por los datos**: no hay variación de nomenclatura porque no hay
nomenclatura que varíe. Dos de tres no lo desarman.

## 4 · Lo que esto significa para el PTE, y lo que no

El PTE de GFX8 codifica permisos en **3 bits** — `EXECUTABLE` bit 4, `READABLE` bit 5,
`WRITEABLE` bit 6 — más `VALID` bit 0 (`gmc_v8_0.c:691-702`, fuente única, sin
corroboración en cabeceras ASIC).

El hardware reporta **8 bits**. **La correspondencia PTE → PROTECTIONS no existe en el
corpus.** Esto no es "está documentado como reservado": es que nadie la escribió.

Dos hipótesis, sin fuente que las distinga:

- `HYPOTHESIS` A: `PROTECTIONS[3:5]` espeja R/W/X, y `[2:0]` son subtipos de fallo de
  validez (PDE0 no válido, PTE no válido, entrada silenciosa…).
- `HYPOTHESIS` B: `[7:0]` es un Fault-ID opaco y el mapeo desde el PTE no es directo.

La existencia de `VM_L2_CNTL__PDE_FAULT_CLASSIFICATION` (`MASK 0x40000`, presente en
`gmc_6_0` a `gmc_8_2`) sugiere que **el hardware sí distingue tipos de fallo a nivel
PDE**, lo que inclinaría hacia A — pero un indicio no es evidencia, y ese campo tampoco
lo descompone el driver.

## 5 · Consecuencia para el driver propio

El único sitio de todo el driver donde `PROTECTIONS` se convierte en banderas de permiso
**no es alcanzable** en el camino GPUVM que un driver propio implementa. Un driver propio
que quiera diagnosticar faults de traducción tendrá que **inventar su propia decodificación**
de un campo de 8 bits dehardware que el driver de referencia nunca descompone en ese
camino.

Por `NO_HISTORICAL_INHERITANCE` y `IMPLEMENTATION GATE`: **no se hereda la decodificación
de KFD como semántica de hardware.** Es software de KFD sobre un campo opaco, no una
verdad del silicio.

Esto marca `F2b` con una causa nombrada nueva: no bloquea por falta de spec del PTE, sino
porque **el observador de referencia no produjo el dato en el camino relevante**.

## 6 · Ausencia acotada

Lo que **no** se encontró, tras buscar:

- `PROTECTIONS` en `findings/` o `docs/`: **0 ficheros** antes de este.
- `first_kfd_vmid`: **0 ficheros**. `prot_valid`: **0 ficheros**.
- Una enumeración o comentario del campo: **no existe** en `gmc_8_2_sh_mask.h` ni en
  ninguna otra cabecera aplicable a GFX8.
- Definición de la entrada de page table en cabeceras ASIC: **inexistente** para todo
  GFX8 (`gmc` 6_0/7_0/7_1/8_1/8_2 y bloque GFX). Los únicos campos con PDE/PTE en el
  nombre son enables de fault, endianess de la L2 cache, y falsos positivos
  (`MC_IO_TXCNTL_*__PTERM_*` es terminación PHY, sin relación).

## 7 · Hallazgo colateral: la L2 puede byte-swappear PTE y PDE por separado

`VM_L2_CNTL__L2_CACHE_PDE_ENDIAN_SWAP_MODE` (`MASK 0x30`) y
`VM_L2_CNTL__L2_CACHE_PTE_ENDIAN_SWAP_MODE` (`MASK 0x0c`) existen de `gmc_6_0` a
`gmc_8_2`, idénticos. El driver **no los programa** en `gfxhub`/`gmc_v8_0` init.

Es decir: esta GPU puede leer la caché L2 de PDE y de PTE con endianess distinto, y el
driver de referencia lo deja en el valor de reset. No está en ningún hallazgo del proyecto.
Relevante para un driver propio que placement de page tables en VRAM.

## Clasificación final

| afirmación | clase | estado |
|---|---|---|
| layout de `PROTECTION_FAULT_STATUS`, 5 campos | FACT | **PROVEN** |
| el decode estructurado está tras gate KFD | FACT | **PROVEN** |
| VMID 0-7 DRM / 8-15 KFD en esta GPU | DERIVATION | **PROVEN_DERIVED** |
| GFX6/GFX7 no lo descomponen | NEGATIVE_RESULT | **PROVEN_ABSENT** (2 ficheros, 2 generaciones) |
| bits 6-7 sin decodificar por nadie | NEGATIVE_RESULT | **PROVEN_ABSENT** |
| PTE → PROTECTIONS | — | **NOT_IN_CORPUS**, con las dos hipótesis A/B sin separador |
| layout de la entrada de page table en hardware | — | **NOT_IN_CORPUS**, fuente única = un comentario |

## Lo que este hallazgo NO cierra

**No cierra F2b.** `F2b` sigue `BLOCKED_BY_CORPUS` + `BLOCKED_BY_AUTHORIZATION`. Lo que
hace es **renombrar el bloqueo**: de "falta la spec del PTE" a "el observador de
referencia no decodifica el campo en el camino que nos interesa". Es un dato que
`IMPLEMENTATION_GATE` necesita para marcar la frontera, no para romperla.

## Nota de honestidad

Hipótesis de partida de esta iteración: el page walker de GFX8 sería `gfxhub_v1_0`. **Es
falsa.** El control negativo —0 menciones de `gfxhub|vmhub` en las 97 líneas del init log
— la refutó antes de leer el fichero. Los ip_blocks reales, contados del log, son **9** y
ninguno es VMHUB: `vi_common`, `gmc_v8_0`, `tonga_ih`, `gfx_v8_0`, `sdma_v3_0`,
`powerplay`, `dm`, `uvd`, `vce`. Para GFX8 la ruta es `gmc_v8_0` con un registro de PTBA
de 32 bits, no el par `LO32/HI32` de SOC15.

Ejecutar el control negativo **antes** de la lectura fue lo que ahorró la iteración.