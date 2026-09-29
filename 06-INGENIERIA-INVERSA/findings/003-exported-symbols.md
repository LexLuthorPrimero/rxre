# 003 — Símbolos compute y API exportada de `amdgpu.ko`

**Clasificación**: `READ_ONLY/EVIDENCE`
**Fecha**: 2026-09-29
**Objeto**: `amdgpu-analysis/amdgpu.ko`, SHA256 `a1a44c2457d33c65149ef4f455173ca446564bfd19bcc9cb215fca10cf24c024`
**Volcados**: `symbols-all.txt` (65 596 líneas), `symbols-compute.txt` (4 456),
`exported-symbols.txt` (4)
**Clasificación de trabajo**: `READ_ONLY/EVIDENCE`. Sin sysfs, sin ejecución de código del
módulo, sin `SYSTEM_CHANGE`.

---

## 1. El comando indicado no funciona, y por qué

```bash
nm -D amdgpu-analysis/amdgpu.ko > symbols-all.txt
# nm: amdgpu-analysis/amdgpu.ko: no hay símbolos
```

**`nm -D` no devuelve nada en un `.ko`.** Un módulo de kernel es un objeto **relocatable**, no
un objeto enlazado: no tiene tabla `.dynsym` resuelta. Lo mismo aplica a
`readelf --dyn-syms`. El error de `nm` es explícito ("no hay símbolos"), no un resultado vacío
que se pueda malinterpretar.

La tabla correcta es **`.symtab`**, y la API que el módulo ofrece a otros módulos está en
`__ksymtab` (ver §2), que no es ninguna de las dos. Sustitutos used:

```bash
nm -S amdgpu-analysis/amdgpu.ko > symbols-all.txt            # 65 596 entradas
nm -S amdgpu-analysis/amdgpu.ko | grep -E "ring|_cs|job|gfx|compute" > symbols-compute.txt
readelf -SW amdgpu-analysis/amdgpu.ko | grep __ksymtab
readelf -p __ksymtab_strings amdgpu-analysis/amdgpu.ko
```

## 2. API exportada: 4 símbolos, ninguno de compute

| Símbolo | Tipo | Dirección | Subsistema |
|---|---|---|---|
| `isp_user_buffer_alloc` | `T` | `0x8d5040` | ISP (vídeo) |
| `isp_user_buffer_free` | `T` | `0x8d5180` | ISP (vídeo) |
| `isp_kernel_buffer_alloc` | `T` | `0x8d51a0` | ISP (vídeo) |
| `isp_kernel_buffer_free` | `T` | `0x8d51c0` | ISP (vídeo) |

`__ksymtab` = 30 B, `__ksymtab_strings` = 0x5e (94 B). Cero coincidencias con
`ring|gfx|compute|kfifo|sdma`.

**Lo que no es la API exportada:** las 311 entradas `alias=` de `.modinfo` son IDs de PCI
(`pci:v00001002d00001304sv*sd*bc*sc*i*`), no símbolos. Un filtro por `alias=` sobre `.modinfo`
devuelve una lista que parece de símbolos y no lo es. Verificado: 311 de 311 con prefijo `pci:`.

## 3. Los 10 símbolos más relevantes para compute submit

Ordenados por el camino que recorre un submit de compute desde el IOCTL hasta la cola KCQ.
Tamaños con `nm -S` (campo `Size`).

| # | Símbolo | Tipo | Tamaño | Papel en el camino |
|---|---|---|---|---|
| 1 | `amdgpu_cs_ioctl` | `T` | **8 107 B** | **Punto de entrada desde userspace.** `DRM_IOCTL_AMDGPU_CS`. El más grande del camino: parsea el IB, valida BOs, decide KCQ vs KGQ. Es donde vive la política de submit |
| 2 | `amdgpu_cs_wait_ioctl` | `T` | 504 B | Espera de fence por ioctl. `DRM_IOCTL_AMDGPU_CS_WAIT_QUERY` |
| 3 | `amdgpu_cs_wait_fences_ioctl` | `T` | 1 484 B | Espera por fences concretos. Complementario del anterior |
| 4 | `amdgpu_job_alloc_with_ib` | `T` | 558 B | Empaqueta IB + BOs en un objeto `amdgpu_job`. Frontera entre validación y envío |
| 5 | `amdgpu_sched_run_job` | `T` | — | **El despachador.** Decide qué ring recibe el job según el tipo de contexto |
| 6 | `amdgpu_ring_init` | `T` | 1 180 B | Inicialización del ring: tamaño, wptr, timestamps. Común a KCQ y KGQ |
| 7 | `amdgpu_fence_emit` | `T` | 472 B | Escribe la fence al final del ring. El punto de sincronización observable |
| 8 | `amdgpu_gfx_enable_kcq` | `T` | 833 B | **Setup de la cola de compute.** Casi el doble que `enable_kgq` |
| 9 | `amdgpu_gfx_enable_kgq` | `T` | 455 B | Setup de la cola de graphics. Referencia para comparar |
| 10 | `amdgpu_gfx_compute_queue_acquire` | `T` | 561 B | Adquisición de la cola. Debe preceder a los anteriores en un driver propio |

Todos son **`T` (enlace local)**. Ninguno exportable (ver §2).

### Lectura de las asimetrías

- **`cs_ioctl` = 8 107 B.** El ioctl de compute es la mayor función del camino y triplica a
  `wait_ioctl`. Concentra la política: validación de BO, resolución de contexto, elección de
  cola. Es el punto de partida obligatorio para un driver propio, no un detalle periférico.
- **`enable_kcq` 833 B vs `enable_kgq` 455 B.** La cola de compute es casi el doble. `PLAUSIBLE`:
  KCQ lleva GTT, SQ y un despachador propio mientras KGQ hereda más camino. **El tamaño no
  identifica la causa**; establecerla requiere seguir las llamadas, y es trabajo de la ronda 2.
- `wait_fences_ioctl` (1 484 B) triplica a `wait_ioctl` (504 B). La espera por lista de fences
  es sustancialmente más compleja que la espera simple.

## 4. Los símbolos compute, filtrados

Volcado en `symbols-compute.txt`: **4 456 líneas** que casan con `ring|_cs|job|gfx|compute`.

Familias presentes, con el recuento de símbolos `T`/`t` en cada una:

| Familia | Recuento | Nota |
|---|---|---|
| `amdgpu_gfx_*` | ~190 incluye `gfx_v8` | IP block de gráficos, incluye setup de KCQ/KGQ |
| `amdgpu_cs_*` | 13 | Fachada de compute: ioctls y validación de BO |
| `amdgpu_job_*` | 8 | Gestión de jobs y IB |
| `amdgpu_fence_*` | 17 | Sincronización |
| `amdgpu_ring_*` | 30+ | Rings y colas |
| `amdgpu_sched_*` | 20+ | Planificador de contextos |
| `amdgpu_vm_*` | 40+ | Page tables |

## 5. Corrección de un supuesto de la ronda 1: el subsistema se llama LSDMA, no `amdgpu_sdma`

La ronda 1 buscó símbolos con nombres estándar de `amdgpu_sdma_ring0_kernel_dispatch` y `amdgpu_sdma_submit_ioctl`
—nombres estándar de ABL/RADV— **no existen con esas variantes**. Los 17 símbolos
`amdgpu_sdma_*` que sí existen son de la generación previa de packet open
(`amdgpu_sdma_init_microcode`, `amdgpu_sdma_reset_engine`).

El subsistema de envío PM4 en esta generación se llama **LSDMA** y sus símbolos llevan prefijo
`dmub_lsdma_*`:

| Símbolo | Tamaño | Qué es |
|---|---|---|
| `dmub_lsdma_init` | 445 B | Init del motor |
| `dmub_lsdma_send_tiled_to_tiled_copy_command` | 611 B | Copia tiled→tiled |
| `dmub_lsdma_send_linear_sub_window_copy_command` | 392 B | Copia con sub-ventana |
| `dmub_lsdma_send_pio_copy_command` | 383 B | Copia vía PIO |
| `dmub_lsdma_send_pio_constfill_command` | 373 B | Relleno de constante |
| `dmub_lsdma_send_linear_copy_command` | 371 B | Copia lineal |
| `dmub_lsdma_send_poll_reg_write_command` | 363 B | Poll de registro |

**Consecuencia:** la nomenclatura de ABL/RADV no es transferible. Un plan de driver escrito
contra `amdgpu_sdma_*` apuntaría a los ficheros equivocados. Esto es `OBSERVED`, y la
confirmación independiente es que la fuente contiene `lsdma_v6_0.c`, `lsdma_v6_0.h`,
`lsdma_v7_0.c`, `lsdma_v7_1.c` — junto a los `sdma_v2_4` … `sdma_v7_1` de las generaciones
antiguas, que coexisten porque el mismo driver sirve a varias familias ASIC.

## 6. Todos estos símbolos son de enlace local

De los 65 596 símbolos, 45 127 tienen tamaño conocido y **ninguno de los de compute es
exportable**. La API pública del módulo son 4 funciones de ISP (§2).

**Consecuencia operativa para IA-2:** no se puede construir un driver de compute encima de
`amdgpu` por enlace de símbolos. Las tres vías reales son:

1. **Reimplementar** la secuencia de setup de KCQ leyendo la fuente (la vía que este ámbito
   está habilitando).
2. **`kfd`/KFD**: el módulo incluye `kgd_arcturus_hqd_sdma_load` (713 B) y
   `kgd_arcturus_hqd_sdma_dump` (717 B), o sea que **el hardware de compute queue ya tiene
   soporte en KFD** y ahí sí hay una API de userspace. Es la vía menos costosa y la que
   conviene evaluar primero.
3. Sustituir el módulo completo, que es el objetivo declarado de Fase 4.

**Apunto 2 es una recomendación, no un hallazgo:** no se ha inspeccionado la interfaz KFD ni
verificado que estas dos funciones formen una API utilizable. Queda `NOT_DETERMINED`.

## Procedencia

Tamaños y direcciones de `nm -S` sobre el ELF de SHA256 `a1a44c24…`; tabla exportada de
`readelf -SW` + `readelf -p __ksymtab_strings`; conteos de `nm` filtrado. Todos ejecutados el
2026-09-29. La nomenclatura LSDMA se cross-checkea contra
`RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/`, donde existen `lsdma_v7_1.c` y
`lsdma_v6_0.c` junto a los `sdma_v*` heredados. Ningún valor transcrito.
