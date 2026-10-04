# MICROARCH-GFX8 — Qué se establece desde el corpus sobre la microarquitectura del shader de esta RX 550, y qué no

```
NODE_ID=MICROARCH-GFX8 · AGENT_ID=WORKER
CLASIFICACION=DOCUMENTATION+DERIVATION+MEASUREMENT · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS
MODIFICACIONES_CORPUS=0 · WRITE_EXECUTION=NONE · RUNTIME=NOT_RUN
GPU INTACTA · SIN MMIO · SIN DEBUGFS · SIN dmesg/journalctl · SIN RED
OBJETOS_ESCRITOS=1 (este fichero). Nada mas del arbol tocado.
```

Prefijo de cita: `K/` = `RESEARCH/working/linux-7.1.3/`. Ejemplo: `K/drivers/gpu/drm/amd/amdgpu/gfx_v8_0.c:7122`.
Todo lo de abajo está leído en esta ronda. No hay dato heredado sin cita.

---

## 0 · Resumen ejecutivo, en tres frases

1. **El número que el encargo daba por ausente —oleadas por SIMD— sí está, y está en cuatro sitios que coinciden**: `10` (`gfx_v8_0.c:7122`), `40 por CU` (`kfd_queue.c:459`), `simd_per_cu=4` (`gfx_8_0_enum.h:6832`), y el comentario de KFD (`kfd_priv.h:821`) — con la salvedad de que ese comentario dice **GFX9**, no GFX8 (§6.1).
2. **La matriz occupancy×ILP no se puede construir como fórmula, porque la regla que reparte recursos a las oleadas no está en el kernel: está en el firmware del SQ/RLC. Pero sí se puede construir como modelo de cinco dimensiones medibles**, porque el mapa de registros de GFX8 trae un contador de hardware por dimensión (§3).
3. **N-INT-04 y R-NEW-68 son la misma idea y además es la que no se puede ejecutar tal como está escrita**: el corpus sólo mide *recuento* de registros, nunca *vida* (§7).

Y un hallazgo lateral que cambia el estado de una frontera: **la observabilidad de ocupación en esta ASIC no es un muro de hardware, es un hueco de cableado del driver** (§5).

---

## 1 · Disculpa previa: `asic_reg/gc/` no contiene GFX8

El encargo señalaba `asic_reg/gc/` como candidato natural. **Refutado, por el nombre del directorio.**

Inventario de versiones presente en `K/drivers/gpu/drm/amd/include/asic_reg/`, leído con `os.walk`:

| subdir | versiones presentes |
|---|---|
| `gc/` | `9_0` (solo `_default.h`), `9_1`, `9_2_1`, `9_4_x`, `10_1`, `10_3`, `11_0`, `11_5`, `12_0`, `12_1` — **ningún `8_x`** |
| `gca/` | `6_0`, `7_0`, `7_2`, **`8_0`**, **`8_1`** |

**⇒ `PROVEN`.** El sitio correcto es **`asic_reg/gca/gfx_8_0_d.h` / `gfx_8_0_enum.h` / `gfx_8_0_sh_mask.h`**, y eso lo confirma el propio fichero que los usa:
`K/drivers/gpu/drm/amd/amdgpu/gfx_v8_0.c:49-51` incluye exactamente esas tres cabeceras, y ninguna otra de la GFX8.
Refutador: que apareciera un `gc/gc_8_0_offset.h` en el corpus. No aparece, y el inventario de 30 ficheros de `gc/` está cerrado.

Lo mismo vale para el "Packet Table" o definición de paquetes GFX8 que el encargo mencionaba: **`amdgpu_gfx.h` (697 líneas) no contiene ninguna tabla de paquetes GFX8** — ni `DISPATCH_PKT*`, ni `gfx8_pkt*`. `si_decodepacket.c` no está en el corpus. `⇒ PROVEN_ABSENT` dentro del corpus, alcance = `K/drivers/gpu/drm/amd/amdgpu/`.

---

## 2 · Los hechos que sí son recuperables, con cita

### 2.1 · Enlace ASIC → bloque de IP (para que ninguna cifra sea de otra generación)

| hecho | cita |
|---|---|
| `CHIP_POLARIS11`, `CHIP_POLARIS12`, `CHIP_VEGAM` ⇒ `gfx_target_version = 80003`, `f2g = &gfx_v8_kfd2kgd` | `K/drivers/gpu/drm/amd/amdkfd/kfd_device.c:293-296` |
| PCI `0x6980/0x6981/0x6985/0x6986/0x6987/0x6995/0x6997/0x699F` ⇒ `CHIP_POLARIS12` | `K/drivers/gpu/drm/amd/amdgpu/amdgpu_drv.c:2034-2041` |
| Polaris12 entra por `gfx_v8_0_gpu_early_init` | `K/drivers/gpu/drm/amd/amdgpu/gfx_v8_0.c:1681-1682` |
| Los *golden settings* de Polaris12 son los de Polaris11 | `K/drivers/gpu/drm/amd/amdgpu/gfx_v8_0.c:783-791` |

**⇒ `PROVEN`.** Todo lo que sigue, leído en ficheros `gfx_8_0_*` o en código de la rama `gfx_v8_*`, aplica a esta placa y no a Vega ni a Navi. Cuando cito un valor de GFX9 o de GFX10 lo marco como tal y no lo uso como cifra de esta ASIC.

### 2.2 · Las cinco cifras que N-INT-05 y R-NEW-64 necesitan

`K/drivers/gpu/drm/amd/amdgpu/gfx_v8_0.c:7119-7125`, literal:

```c
7119  cu_info->number = active_cu_number;
7120  cu_info->ao_cu_mask = ao_cu_mask;
7121  cu_info->simd_per_cu = NUM_SIMD_PER_CU;
7122  cu_info->max_waves_per_simd = 10;
7123  cu_info->max_scratch_slots_per_cu = 32;
7124  cu_info->wave_front_size = 64;
7125  cu_info->lds_size = 64;
```

Con `NUM_SIMD_PER_CU` resuelto en `K/drivers/gpu/drm/amd/include/asic_reg/gca/gfx_8_0_enum.h:6831-6833`:

```c
6831  * ENUM_NUM_SIMD_PER_CU enum
6832  typedef enum ENUM_NUM_SIMD_PER_CU {
6832  NUM_SIMD_PER_CU                                  = 0x4,
6833  } ENUM_NUM_SIMD_PER_CU;
```

| magnitud | valor | estado | cita |
|---|---|---|---|
| SIMD por CU | **4** | `PROVEN` | `gfx_8_0_enum.h:6832` · aplicado en `gfx_v8_0.c:7121` |
| **oleadas por SIMD** | **10** | `PROVEN` (constante de driver) | `gfx_v8_0.c:7122` |
| **líneas scratch por CU** | **32** | `PROVEN` (constante de driver) | `gfx_v8_0.c:7123` |
| **tamaño de oleada** | **64** (wave64) | `PROVEN` | `gfx_v8_0.c:7124` |
| **LDS por CU** | **64 KiB** | `PROVEN` (constante + unidad) | `gfx_v8_0.c:7125`; la unidad KiB la fija la asignación `cu->lds_size_in_kb = cu_info->lds_size` en `K/drivers/gpu/drm/amd/amdkfd/kfd_crat.c:2295` |
| contextos por hardware | **8** | `PROVEN` | `gfx_v8_0.c:1688` |
| GPR visibles al shader | **256** | `PROVEN` | `gfx_v8_0.c:1686` (`max_gprs = 256`) |

### 2.3 · Las mismas cifras, segunda y tercera fuente (corroboración)

KFD dimensiona el área de contexto de save/restore por CU con **constantes distintas, en otro fichero, escritas por otra función**:

| magnitud | constante KFD | cita |
|---|---|---|
| VGPR por CU | `0x40000` = 262 144 B | `K/drivers/gpu/drm/amd/amdkfd/kfd_queue.c:414` (sin override para `80003`) |
| SGPR por CU | `0x4000` = 16 384 B | `kfd_queue.c:403` |
| LDS por CU | `0x10000` = 65 536 B | `kfd_queue.c:446` |
| HWREG por CU | `0x1000` = 4 096 B | `kfd_queue.c:436` |
| oleadas por CU | `min(cu_num * 40, array_count / simd_arrays_per_engine * 512)` | `kfd_queue.c:459-460` |

**Las cuatro aritméticas cierran exactamente.** Esto no es «dos números parecidos»:

```
VGPR:  0x40000 B/CU ÷ 4 SIMD = 0x10000 B/SIMD
       ÷ 64 líneas           = 0x400 B/línea = 256 dwords = 256 VGPR
       = max_gprs (gfx_v8_0.c:1686) = SQ_NUM_VGPR 0x100 (gfx_8_0_enum.h:2816)      ✔ 3 caminos

LDS:   0x10000 B/CU  = 64 KiB/CU
       = gfx_v8_0.c:7125 (=64, unidad KiB por kfd_crat.c:2295)                       ✔ 2 caminos

oleadas: 10 (gfx_v8_0.c:7122) × 4 SIMD = 40/CU
       = kfd_queue.c:459 (cu_num*40)                                                    ✔ 2 caminos

HWREG: 128 B por oleada (cwsr asm:737-739) → 0x1000/CU = 32 × 128                      ✔ coherente
```

**⇒ `CORROBORATED` (mismo autor, tres sitios independientes). No `PROVEN_DERIVED` de hardware.**
Limitación explícita: las tres fuentes son AMD. Coincidir no es verificación contra la pieza.
Refutador: que en la placa `0x40000 B/CU` no correspondiera a 256 VGPR × wave64 — se verificó leyendo los tres ficheros, no la placa; la refutación real es la lectura de `amdgpu_gca_config` (§5.3).

### 2.4 · Recuento arquitectónico de registros

`K/drivers/gpu/drm/amd/include/asic_reg/gca/gfx_8_0_enum.h`:

```c
2734  #define SQ_MAX_PGM_SGPRS     0x68     /* 104 */
2735  #define SQ_MAX_PGM_VGPRS     0x100    /* 256 */
2816  #define SQ_NUM_VGPR          0x100    /* 256 */
2822  #define SQ_NUM_SGPR          0x66     /* 102 */
```

**⇒ `PROVEN`: 256 VGPR y 102 SGPR en GFX8.** `SQ_MAX_PGM_*` es el tope direccionable en el ISA (104 incluye los dos de trampa); `SQ_NUM_*` es el recuento. No los mezclo.

### 2.5 · Granularidades de asignación — el punto que casi nadie cita y que decide la granularidad de N-INT-04

El manejador de traps CWSR de GFX8 es, dentro del corpus, **el único sitio donde alguien decodifica estos campos**. Citas literales:

`K/drivers/gpu/drm/amd/amdkfd/cwsr_trap_handler_gfx8.asm`

```asm
41  var SQ_WAVE_GPR_ALLOC_VGPR_SIZE_SHIFT   = 8
42  var SQ_WAVE_GPR_ALLOC_VGPR_SIZE_SIZE    = 6
43  var SQ_WAVE_GPR_ALLOC_SGPR_SIZE_SHIFT   = 24
44  var SQ_WAVE_GPR_ALLOC_SGPR_SIZE_SIZE    = 3   //FIXME  sq.blk still has 4 bits at this time while SQ programming guide has 3 bits

725 function get_vgpr_size_bytes(s_vgpr_size_byte)
726     s_getreg_b32   s_vgpr_size_byte, hwreg(HW_REG_GPR_ALLOC, 8, 6)  //vpgr_size
727     s_add_u32      s_vgpr_size_byte, s_vgpr_size_byte, 1
728     s_lshl_b32     s_vgpr_size_byte, s_vgpr_size_byte, (2+8) //Number of VGPRs = (vgpr_size + 1) * 4 * 64 * 4   (non-zero value)   //FIXME for GFX, zero is possible

304     s_getreg_b32    s_save_alloc_size, hwreg(HW_REG_GPR_ALLOC, 24, 3)   //spgr_size
305     s_add_u32       s_save_alloc_size, s_save_alloc_size, 1
306     s_lshl_b32      s_save_alloc_size, s_save_alloc_size, 4   //Number of SGPRs = (sgpr_size + 1) * 16   (non-zero value)
319     // SGPR is allocated in 16 SGPR granularity

719 function get_lds_size_bytes(s_lds_size_byte)
720     // SQ LDS granularity is 64DW, while PGM_RSRC2.lds_size is in granularity 128DW
722     s_lshl_b32     s_lds_size_byte, s_lds_size_byte, 8   //LDS size in dwords = lds_size * 64 *4Bytes

737 function get_hwreg_size_bytes
738     return 128 //HWREG size 128 bytes
```

| granularidad | valor | estado | cita |
|---|---|---|---|
| **VGPR por oleada** | múltiplo de **4** | `PROVEN` | `cwsr…asm:728` |
| **SGPR por oleada** | múltiplo de **16** | `PROVEN` | `cwsr…asm:306`, `:319`, `:734` |
| **LDS por oleada** | múltiplo de **64 DW = 256 B** | `PROVEN` | `cwsr…asm:720-722` |
| HWREG por oleada | 128 B | `PROVEN` | `cwsr…asm:737-739` |

**⇒ `CONFLICT`, y el conflicto es de AMD, no mío.** El campo `SGPR_SIZE` mide 4 bits en el mapa de registros (`SQ_WAVE_GPR_ALLOC__SGPR_SIZE_MASK 0xf000000`, `gfx_8_0_sh_mask.h:14461-14462`) y el ensamblador de AMD lee 3 bits, con el `FIXME` de la línea 44 declarando la discrepancia contra el SQ programming guide. Con 4 bits el máximo sería 256 SGPR, con 3 bits sería 128; **ninguno de los dos es 102**. Por tanto el campo **no es un contador lineal** y no se puede decodificar el máximo. Dejo el `CONFLICT` tal cual, sin resolverlo.

**⇒ `NOT_DETERMINED`, con el hueco exacto:** el mismo `FIXME` de `:728` dice *«zero is possible»* para GFX. Es decir, **el propio AMD no sabe decodificar el valor 0** de `VGPR_SIZE`. Cualquier modelo que asuma `(n+1)` en ese campo está asumiendo justo el caso que el fuente marca como no resuelto.

### 2.6 · Dónde el hardware *declara* la demanda por oleada

`gfx_8_0_sh_mask.h`, campos del paquete COMPUTE:

| campo | máscara / shift | ancho | cita |
|---|---|---|---|
| `COMPUTE_PGM_RSRC1.VGPRS` | `0x3f` / `0x0` | 6 b | `:8301-8302` |
| `COMPUTE_PGM_RSRC1.SGPRS` | `0x3c0` / `0x6` | 4 b | `:8303-8304` |
| `COMPUTE_PGM_RSRC1.PRIORITY` | `0xc00` / `0xa` | 2 b | `:8305-8306` |
| `COMPUTE_PGM_RSRC1.BULKY` | `0x1000000` / `0x18` | 1 b | `:8317-8318` |
| `COMPUTE_PGM_RSRC2.SCRATCH_EN` | `0x1` / `0x0` | 1 b | `:8321-8322` |
| `COMPUTE_PGM_RSRC2.USER_SGPR` | `0x3e` / `0x1` | 5 b | `:8323-8324` |
| `COMPUTE_PGM_RSRC2.LDS_SIZE` | `0xff8000` / `0xf` | 9 b | `:8339-8340` |
| `COMPUTE_RESOURCE_LIMITS.WAVES_PER_SH` | `0x3ff` / `0x0` | 10 b | `:8345-8346` |
| `COMPUTE_RESOURCE_LIMITS.TG_PER_CU` | `0xf000` / `0xc` | 4 b | `:8347-8348` |
| `COMPUTE_RESOURCE_LIMITS.LOCK_THRESHOLD` | `0x3f0000` / `0x10` | 6 b | `:8349-8350` |
| `COMPUTE_RESOURCE_LIMITS.SIMD_DEST_CNTL` | `0x400000` / `0x16` | 1 b | `:8351-8352` |
| `COMPUTE_RESOURCE_LIMITS.FORCE_SIMD_DIST` | `0x800000` / `0x17` | 1 b | `:8353-8354` |
| `COMPUTE_RESOURCE_LIMITS.CU_GROUP_COUNT` | `0x7000000` / `0x18` | 3 b | `:8355-8356` |
| `COMPUTE_TMPRING_SIZE.WAVES` | `0xfff` / `0x0` | 12 b | `:8365-8366` |
| `COMPUTE_TMPRING_SIZE.WAVESIZE` | `0x1fff000` / `0xc` | 13 b | `:8367-8368` |

**Corroboración de la granularidad, y es fuerte:** `PGM_RSRC1.VGPRS` tiene **6 bits**, los mismos 6 bits que `SQ_WAVE_GPR_ALLOC.VGPR_SIZE` (`gfx_8_0_sh_mask.h:14457-14458`, máscara `0x3f00`, shift `0x8`). `PGM_RSRC2.LDS_SIZE` tiene **9 bits**, los mismos 9 que `SQ_WAVE_LDS_ALLOC.LDS_SIZE` (`:14465-14466`, `0x1ff000`, `0xc`). **El ancho de la demanda y el ancho de la concesión son idénticos, en los dos recursos.**
**⇒ `CORROBORATED`:** el hardware conserva en `SQ_WAVE_GPR_ALLOC` la misma codificación que el dispatch declaró en `PGM_RSRC1`. Refutador: que un shader de 64 VGPR declarase `VGPRS` distinto de 15 — no medido.

Y el driver da la decodificación por escrito, en un comentario:

`K/drivers/gpu/drm/amd/amdgpu/gfx_v8_0.c:1389`
```c
1389  mmCOMPUTE_PGM_RSRC1, 0x100004f, /* VGPRS=15 (64 logical VGPRs), SGPRS=1 (16 SGPRs), BULKY=1 */
```

**⇒ `PROVEN`, y es la cifra más útil de este turno: `VGPRS=15` ⇔ 64 VGPR lógicos; `SGPRS=1` ⇔ 16 SGPR.**
Comprobación: `0x4f` → bits 0-5 = `0x0f` = 15 ✔, bits 6-9 = 1 ✔, bit 24 = 1 = `BULKY` ✔ (`gfx_8_0_sh_mask.h:8317`). Y `VGPRS=15` → `(15+1)*4 = 64` ✔, **idéntico al `get_vgpr_size_bytes` de `:728`** (§2.5).

> ⚠ **No confundo los dos registros.** `PGM_RSRC1.SGPRS=1 → 16 SGPR` y `SQ_WAVE_GPR_ALLOC.SGPR_SIZE → (n+1)*16` **no usan la misma aritmética** (`1*16=16` vs `(1+1)*16=32`). AMD decodifica uno y no el otro. Trato `PGM_RSRC1` con la fórmula del comentario de `gfx_v8_0.c:1389` y `SQ_WAVE_GPR_ALLOC` con la de `cwsr…asm:728`, y no derivo una de la otra.

Este array es el microcódigo de arranque de VGPR: `vgpr_init_regs` (`gfx_v8_0.c:1382`), emitido como IB `SET_SH_REG` (`gfx_v8_0.c:1496`, `:1528-1531`). Y `mmCOMPUTE_RESOURCE_LIMITS = 0x1000000 /* CU_GROUP_COUNT=1 */` (`:1385`) deja **`WAVES_PER_SH = 0`**.

**⇒ `PROVEN`: el driver no impone ningún tope de oleadas por dispatch en Polaris12.** Las 10 oleadas/SIMD no vienen de un límite software: vienen del hardware o del firmware. Refutador: que `COMPUTE_RESOURCE_LIMITS` se reescriba en otro punto de la cadena para esta ASIC — no lo reescribe ningún `.c` del árbol, comprobado por nombre.

### 2.7 · El registro que decide la ocupación: `SPI_RESOURCE_RESERVE_CU_x`

`gfx_8_0_sh_mask.h:10521-10530` (CU_0; idéntico en CU_1..CU_15):

```c
10521  #define SPI_RESOURCE_RESERVE_CU_0__VGPR_MASK     0xf
10522  #define SPI_RESOURCE_RESERVE_CU_0__VGPR__SHIFT    0x0
10523  #define SPI_RESOURCE_RESERVE_CU_0__SGPR_MASK     0xf0
10524  #define SPI_RESOURCE_RESERVE_CU_0__SGPR__SHIFT    0x4
10525  #define SPI_RESOURCE_RESERVE_CU_0__LDS_MASK      0xf00
10526  #define SPI_RESOURCE_RESERVE_CU_0__LDS__SHIFT     0x8
10527  #define SPI_RESOURCE_RESERVE_CU_0__WAVES_MASK    0x7000
10528  #define SPI_RESOURCE_RESERVE_CU_0__WAVES__SHIFT   0xc
10529  #define SPI_RESOURCE_RESERVE_CU_0__BARRIERS_MASK 0x78000
10530  #define SPI_RESOURCE_RESERVE_CU_0__BARRIERS__SHIFT 0xf
```

offsets: `mmSPI_RESOURCE_RESERVE_CU_0..15` = `0x31dc..0x31f7` (`gfx_8_0_d.h:1627-1642`); `mmSPI_RESOURCE_RESERVE_EN_CU_0..15` = `0x31e6..0x31fb` (`:1643-1658`).
`_EN_` campos (`:10681-10688`): `EN` bit 0, `TYPE_MASK` `0xfffe`/1, `QUEUE_MASK` `0xff0000`/16, `RESERVE_SPACE_ONLY` bit 24.

**Y el driver lo programa para Polaris12**, `gfx_v8_0.c:360-368` (array `polaris11_golden_common_all`, aplicado en `:783-791`):

```c
364  mmSPI_RESOURCE_RESERVE_CU_0, 0xffffffff, 0x00000800,
365  mmSPI_RESOURCE_RESERVE_CU_1, 0xffffffff, 0x00000800,
366  mmSPI_RESOURCE_RESERVE_EN_CU_0, 0xffffffff, 0x00FF7FBF,
367  mmSPI_RESOURCE_RESERVE_EN_CU_1, 0xffffffff, 0x00FF7FAF,
```

**⇒ `PROVEN_DERIVED`:** decodificando `0x00000800` contra las máscaras de arriba, `VGPR=0`, `SGPR=0`, `LDS=8`, `WAVES=0`, `BARRIERS=0`. El único campo no nulo es **LDS**.

**⇒ `NOT_DETERMINED`, hueco exacto:** **el corpus no contiene la decodificación del campo `LDS` de este registro.** Con la granularidad documentada para `SQ_WAVE_LDS_ALLOC` (64 DW = 256 B) el valor 8 daría 2 KiB por CU, lo que contradice los 64 KiB de §2.3 — así que la codificación es otra (probablemente una potencia de dos, pero eso es conjetura mía y no lo afirmo). Lo que **sí** es `PROVEN`: el driver pone `VGPR=0` y `SGPR=0` en el registro de reserva de recursos, y el campo `LDS` vale 8. Refutador: una lectura de `SPI_RESOURCE_RESERVE_CU_0` con el significado de LDS contradicted — no realizada, no GPU.

### 2.8 · Lo que el corpus **no** contiene (y esa ausencia es el dato)

| magnitud | estado | alcance verificado | cómo se comprobó |
|---|---|---|---|
| nº de CU de esta placa | **`NOT_FOUND`** | `gfx_v8_0.c` + `amdgpu_atombios.c` | `gfx_v8_0.c:1683` llama `amdgpu_atombios_get_gfx_info(adev)`; `K/drivers/gpu/drm/amd/amdgpu/amdgpu_atombios.c:744-750` copia `max_shader_engines`, `max_cu_per_sh`, `max_sh_per_se`, `max_backends_per_se`, `max_texture_channel_caches` **desde la tabla `GFX_Info` del VBIOS**. No hay constante en el driver para Polaris12. |
| CU por SH / SH por SE / nº de SE | **`NOT_FOUND`** (idem) | ídem | ídem. `gfx_v8_0.c:1681-1695` **no asigna ninguno**; los hardcodea para Topaz/Fiji/Tonga/Carrizo/Stoney (`:1650-1668`, `:1713-1733`, `:1748-1750`) pero Polaris12 no está en esa lista. |
| **tamaño de un *slot* de scratch** | **`NOT_FOUND`** | `amdgpu/` + `amdkfd/` | `max_scratch_slots_per_cu = 32` es un *recuento* (`gfx_v8_0.c:7123`). Ningún `.c` del árbol nombra `scratch_size` ni `SCRATCH_SIZE` para esta ASIC. **⇒ el presupuesto de scratch en bytes por CU no es derivable.** |
| `amdgpu_perfctr*.c` (plumbing de contadores) | **`NOT_FOUND`** | `amdgpu/` — 632 ficheros, ninguno `amdgpu_perf*` | `os.listdir` completo |
| `include/uapi/drm/amdgpu_drm.h` | **`NOT_FOUND`** | `K/include` | no existe `uapi/` en el corpus ⇒ **no puedo citar el layout de `amdgpu_gpu_info`** |
| regla de reparto de recursos → nº de oleadas | **`NOT_FOUND`** | `gfx_v8_0.c`, `soc15.c`, `amdgpu_discovery.c` | ver §3.3 |
| fuente del compilador AMDGPU | **`PROVEN_ABSENT`** | `RESEARCH/` completo | Los 13 ficheros con «llvm» en el nombre son **internos del kernel**: `K/include/config/RUSTC_LLVM_{MAJOR_,}VERSION`, `K/scripts/rustc-llvm-version.sh`, `K/drivers/gpu/drm/ci/setup-llvm-links.sh`, `K/Documentation/bpf/llvm_reloc.rst`, `K/Documentation/kbuild/llvm.rst`, `K/Documentation/translations/zh_CN/kbuild/llvm.rst`, `K/tools/build/feature/test-llvm{,-perf}.cpp`, `K/tools/perf/util/llvm{,-c-helpers.h,.c,.h}`. Ninguno es LLVM/AMDGPU. **Confirma la medición del nodo principal.** |
| …y una **trampa de nombres** que hay que cerrar | **`PROVEN_ABSENT`** | `RESEARCH/` | 258 ficheros con `aco`/`llvm`/`mesa`/`radv`/`glsl`/`spirv`/`clang` en el nombre. Los `*_baco.c/h` (`polaris_baco.c`, `tonga_baco.c`, `vega10_baco.c`, …) son **Binary APO = blob de firmware**, no el compilador ACO. Y `llvm-mc` no está en el árbol: está **instalado en la máquina**, y eso ya está verificado en `08-ARQUITECTURA/designs/012-gcn8-assembler-and-isa-corpus.md` §2.2-2.4 (`llvm-mc` 22.1.8, target `amdgcn`, `rc=0` para `gfx803`, ensamblado determinista). |

**Refutación del último bloque:** que exista un `.c` que compile GLSL/HLSL a ISA GFX8 en el árbol. No existe; y el mismo `012` demuestra que el triple **no restringe la ISA** (`012` §3), así que un ensamblador no puede sustitizarse por un compilador.

---

## 3 · El modelo de ocupación: qué se puede construir y qué falta

### 3.1 · Lo que SÍ se puede construir (y no es un modelo a medias)

Un **modelo de cinco dimensiones con un contador de hardware por dimensión**, no una fórmula cerrada. La razón de que sea defendible: los cinco campos de `SPI_RESOURCE_RESERVE_CU_x` (§2.7) tienen correspondencia uno-a-uno con cinco familias de contadores en `gfx_8_0_enum.h:1975-2020`:

| dimensión | contador `SPI_PERF_RA_*` | IDs | cita |
|---|---|---|---|
| **sin hueco de oleada** | `WAVE_SIMD_FULL_{PS,VS,GS,ES,HS,LS,CSG,CSN}` | `0x7c..0x83` | `:1975-1982` |
| **VGPR** | `VGPR_SIMD_FULL_{PS,VS,GS,ES,HS,LS,CSG,CSN}` | `0x84..0x8b` | `:1983-1990` |
| **SGPR** | `SGPR_SIMD_FULL_{PS,VS,GS,ES,HS,LS,CSG,CSN}` | `0x8c..0x93` | `:1991-1998` |
| **LDS** | `LDS_CU_FULL_{PS,LS,ES,CSG,CSN}` | `0x94..0x98` | `:1999-2003` |
| **barriers** | `BAR_CU_FULL_{HS,CSG,CSN}` | `0x99..0x9b` | `:2004-2006` |
| `BULKY` | `BULKY_CU_FULL_{CSG,CSN}` | `0x9c..0x9d` | `:2007-2008` |
| tope de grupos | `TGLIM_CU_FULL_{CSG,CSN}` | `0x9e..0x9f` | `:2009-2010` |
| tope de oleadas | `WVLIM_STALL_{PS,VS,GS,ES,HS,LS,CSG,CSN}` | `0xa0..0xa7` | `:2011-2018` |
| bloqueo | `PS_LOCK_NA`, `VS_LOCK` | `0xa8`, `0xa9` | `:2019-2020` |

**Esto es exactamente lo que N-INT-05 llama «frontera de compensación explícita», y es medible sin conocer la fórmula.** Cuando se cambia el parámetro experimental de ILP, la frontera se ve como: `VGPR_SIMD_FULL_*` sube mientras `BAR_CU_FULL_*` / `LDS_CU_FULL_*` / `TGLIM_CU_FULL_*` aparecen. La frontera no se *calcula*: se *lee*.

**⇒ `PROVEN` que la distinción por recurso existe en el mapa de contadores de GFX8.** Refutador: que estos IDs no existieran o no fueran programables en esta placa. Lo primero está leído; lo segundo **no está verificado** — `amdgpu_perfctr*.c` no está en el corpus (§2.8), así que la forma de programarlos es `NOT_DETERMINED`.

### 3.2 · Lo que NO se puede construir, y el hueco exacto

**La regla que convierte un conjunto de valores de `PGM_RSRC1/PGM_RSRC2` en un número de oleadas concedidas no está en el kernel.**

Evidencia del hueco, no de su ausencia imaginada:
- No se escribe `COMPUTE_TMPRING_SIZE`, ni `COMPUTE_RESOURCE_LIMITS` fuera del microcódigo de init (`gfx_v8_0.c:1382-1400`); comprobado sobre los 632 ficheros de `amdgpu/` y los de `amdkfd/`.
- `COMPUTE_TMPRING_SIZE.WAVES` (12 bits, `gfx_8_0_sh_mask.h:8365-8366`) es el campo que *físicamente* dimensiona el anillo de oleadas de una SIMD, y nadie lo programa: es configuración de firmware.
- El hardware reporta wave slots **en vuelo por cola** con `SPI_CSQ_WF_ACTIVE_STATUS` + `SPI_CSQ_WF_ACTIVE_COUNT_0..7` (`gfx_8_0_d.h:1823-1831`; máscaras `ACTIVE 0xffffffff` y `COUNT 0x7ff` en `gfx_8_0_sh_mask.h:12809-12812`) — pero eso mide *cuántas hay*, no *cuántas caben*.

**⇒ `NOT_DETERMINED`.** El techo es conocido y cerrado (10 oleadas/SIMD, 4 SIMD/CU, 40/CU, y el límite global `min(cu_num*40, SE*512)` de `kfd_queue.c:459-460`). **La función de reparto no lo es.**

**Y hay un segundo hueco, dentro del techo, que es el que la revisión tenía razón en temerse:** el segundo término de ese `min` es `max_shader_engines * 512`, y **el corpus no dice de dónde sale el 512**.
*Observación, marcada como `HYPOTHESIS` y no afirmada:* `gfx_v8_0.c:1901` pone `num_mec = 2` para Polaris12 (junto a `:1899-1900`), `:1910-1911` pone `4` pipes × `8` queues, y `:1987-2003` itera ese producto ⇒ **64 colas de cómputo**; con `max_hw_contexts = 8` (`gfx_v8_0.c:1688`) el producto es `8 × 64 = 512`. Coincide. **No lo doy por bueno:** el corpus no lo declara, y una coincidencia aritmética con un número sin justificar es exactamente el tipo de cosa que `AGENTS.md` 11 obliga a marcar como hipótesis. Refutador: leer `ADEVRESID_MAX_COMPUTE_QUEUES` y ver que no es 64, o que el segundo término no es un tope de colas.

### 3.3 · El valor de 10 no está confirmado para GFX8 por ninguna fuente que lo diga

Esto hay que decirlo, porque es el número que sostiene todo lo demás.

`kfd_priv.h:818-824`, literal:

```c
818  *  The number of waves that a CU can launch is limited by couple of
819  *  parameters. These are encoded by struct amdgpu_cu_info instance
820  *  that is part of every device definition. For GFX9 devices this
821  *  translates to 40 waves (simd_per_cu * max_waves_per_simd) when waves
822  *  do not use scratch memory and 32 waves (max_scratch_slots_per_cu)
823  *  when they do use scratch memory. This could change for future
824  *  devices and therefore this example should be considered as a guide.
```

**Dice GFX9. No dice GFX8.** Y el valor de GFX9 en el corpus **no está puesto**: `gfx_v9_0.c:7904` asigna sólo `simd_per_cu`; `max_waves_per_simd`, `wave_front_size`, `lds_size` y `max_scratch_slots_per_cu` no se asignan en ningún `.c` de `amdgpu/` salvo `gfx_v8_0.c:7122-7125`. Inventario completo de esas cuatro cabeceras en el árbol `amd/`: `K/drivers/gpu/drm/amd/include/atomfirmware.h:1864,1865,1869,1899,1900,1904` y `K/drivers/gpu/drm/amd/include/discovery.h:204-206,228-230,254-256,288-290,331-333,353-355` (todas structs), más `gfx_v8_0.c`. **No hay más escritores.**

**⇒ `CORROBORATED` para el 10, no `PROVEN`.** Dos hechos lo sostienen y ninguno lo declara:
1. `gfx_v8_0.c:7122` pone 10 **sin condición de ASIC**: es una constante del bloque `gfx_v8_0`, no de Polaris12.
2. `kfd_queue.c:459` aplica `cu_num * 40` a **todo** `gfxv < 100100`, GFX8 incluido, mientras que el único comentario que justifica el 40 es de GFX9.

**Y la segunda mitad del comentario —«32 oleadas si usan scratch»— es la que `gfx_v8_0.c:7123` (`= 32`) confirma como número, pero sin decir en bytes qué es un slot** (§2.8). Así que la regla de scratch **también** es `NOT_DETERMINED`.

### 3.4 · Por qué esta ASIC no tiene ip_discovery, y por qué eso importa aquí

Existe un camino *por hardware* para estos mismos campos: `K/drivers/gpu/drm/amd/amdgpu/amdgpu_discovery.c:1755-1758` y `:1799-1802` leen `gc_wave_size`, `gc_max_waves_per_simd`, `gc_max_scratch_slots_per_cu`, `gc_lds_size` de la tabla de descubrimiento IP, y `:1750`/`:1794` leen `gc_num_gprs`.

**Ese camino no corre para Polaris12**, por lo ya establecido en `06-INGENIERIA-INVERSA/findings/265-el-tamano-de-cache-de-gfx8-no-esta-en-ningun-sitio.md` (cinco tamaños de caché, cinco escrituras en el mismo bloque, `ip_discovery` inexistente ⇒ valen cero). Cito el finding; no lo re-derivo.

**⇒ `PROVEN_DERIVED`, y es la observación estructural de este turno:** para esta ASIC los valores de microarquitectura del shader **no vienen del firmware, vienen de constantes escritas a mano en `gfx_v8_0.c`**. No hay corroboración por hardware posible sin `ip_discovery.bin`. Por eso §2.3 es `CORROBORATED` y no `PROVEN`, y por eso el §5.3 (leer debugfs) es la única refutación real posible.

---

## 4 · `DERIVABLE_AQUI` / `NECESITA_FUENTE_EXTERNA`

| `DERIVABLE_AQUI` (con cita) | `NECESITA_FUENTE_EXTERNA` (motivo) |
|---|---|
| SIMD/CU = 4 — `gfx_8_0_enum.h:6832` | **Función de reparto recursos→oleadas.** Vive en el firmware SQ/RLC. No está en `amdgpu/`, ni en `amdkfd/`, ni en `asic_reg/`. Refutador: un `.c` que la implemente. No existe (búsqueda por nombre sobre los 632+ ficheros de `amdgpu/`). |
| Oleadas/SIMD = 10 — `gfx_v8_0.c:7122` | **Significado del campo `LDS` de `SPI_RESOURCE_RESERVE_CU_x`.** El corpus da el ancho (4 b) y el valor programado (8); no la decodificación. |
| Tamaño de oleada = 64 — `gfx_v8_0.c:7124` | **Tamaño de un slot de scratch.** `max_scratch_slots_per_cu = 32` es un recuento y el byte no aparece en ningún sitio (§2.8). |
| LDS/CU = 64 KiB — `gfx_v8_0.c:7125` + `kfd_crat.c:2295` | **Ancho real de `SGPR_SIZE`: 3 o 4 bits.** `CONFLICT` declarado por AMD en `cwsr…asm:44`; resolverlo exige el SQ programming guide. |
| Scratch/CU = 32 slots — `gfx_v8_0.c:7123` | **Decodificación de `VGPR_SIZE = 0` en GFX.** El propio AMD lo marca `FIXME` en `cwsr…asm:728`. |
| VGPR = 256, SGPR = 102 — `gfx_8_0_enum.h:2816,2822` | **Nº de CU, CU/SH, SH/SE, nº de SE.** Vienen del VBIOS `GFX_Info` (`amdgpu_atombios.c:744-750`), no del driver. |
| Granularidad VGPR = 4, SGPR = 16, LDS = 64 DW — `cwsr…asm:728,306,720-722` | **PGM_RSRC1 = 15 ⇔ 64 VGPR** se sabe por el comentario de `gfx_v8_0.c:1389`, no por tabla. Su extrapolación a otros valores es `HYPOTHESIS`. |
| `VGPRS`=6 b, `LDS_SIZE`=9 b — `gfx_8_0_sh_mask.h:8301,8339` | **Significado de `BULKY`** (`PGM_RSRC1.BULKY`, `gfx_v8_0_sh_mask.h:8317`) y del contador `SPI_PERF_RA_BULKY_CU_FULL_*` (`gfx_8_0_enum.h:2007`). Los dos nombres coinciden; el corpus no define ninguno. |
| Registro de reserva con 5 campos: VGPR/SGPR/LDS/WAVES/BARRIERS — `gfx_8_0_sh_mask.h:10521-10530` | **Cola de asignación (`SQ_RANDOM_WAVE_PRI`).** Existe en el mapa GFX8 (`gfx_8_0_d.h:2004`; campos `RET 0x7f`/`RUI 0x380`/`RNG 0x1ffc00`, `gfx_8_0_sh_mask.h:13533-13538`) y el driver lo programa **para Tonga** (`gfx_v8_0.c:207`) pero **no** en `golden_settings_polaris11_a11` (`:339-358`). ⇒ `PROVEN` la no-programación; `NOT_DETERMINED` qué valor por defecto trae la placa. Relevante directo para N-INT-06. |
| **Contadores que separan VGPR de SGPR**: `VGPR_SIMD_FULL_*` / `SGPR_SIMD_FULL_*` — `gfx_8_0_enum.h:1983-1998` | **Cómo se programan y leen esos contadores en esta ASIC.** `amdgpu_perfctr*.c` no está en el corpus (§2.8). |
| **Contadores que separan dependencia de inanición**: `VALU_DEP_STALL` = `0x67`, `VALU_STARVE` = `0x68` — `gfx_8_0_enum.h:2387-2388` | **Documento ISA GCN3 (AMD 70645).** Existe como identidad, según `06-INGENIERIA-INVERSA/findings/991-…`, y **no se ha leído**. Nada de la latencia, del ancho de la ruta ni de la latencia de `buffer_load` sale del corpus. |
| **Ocupación como contraste**: `WAVE_CYCLES`=`0x2e` / `WAVE_READY`=`0x2f` (`gfx_8_0_enum.h:2330-2331`); `WAVES`=`0x4`, `LEVEL_WAVES`=`0x5`, `WAVES_CU`=`0xb`, `LEVEL_WAVES_CU`=`0xc`, `CYCLES`=`0x2`, `BUSY_CYCLES`=`0x3` (`:2286-2297`) | **Regla de round-trip LLVM-ISA.** `SQ_PERF_SEL_*` es un enum de eventos; qué significan exactamente y cómo se leen es `NOT_DETERMINED` sin `amdgpu_perfctr*.c`. |
| **Distancia load→use**: `WAIT_CNT_LGKM`=`0x31` (`gfx_8_0_enum.h:2333`) frente a `INSTS_VMEM_RD`=`0x1c` (`:2312`) | **Lifetime de un VGPR.** **No hay ninguna fuente, interna ni externa.** Es la ausencia central de §7. |
| **Mezcla de instrucciones**: `INSTS_{VALU,VMEM_RD,VMEM_WR,VMEM,SALU,SMEM,FLAT,LDS,GDS,EXP,BRANCH,SENDMSG}` — `gfx_8_0_enum.h:2309-2323`; `VALU_SRC_C_CONFLICT`=`0x73` (`:2399`); `INST_CYCLES_SCA`=`0x54` (`:2368`) | **Distinción escalar/vector hardware.** El corpus da contadores separados (`SCA`, `SALU` vs `VALU`) pero **ninguna frase** que diga que un SGPR y un VGPR ocupen filas distintas del mismo asignador. El `SPI_RESOURCE_RESERVE_CU_0` los pone en campos adyacentes de 4 bits (`gfx_8_0_sh_mask.h:10521-10524`) ⇒ `HYPOTHESIS`, no afirmación. |
| **Divergencia**: `ITEMS`=`0xe`, `QUADS`=`0xf`, `WAVES_LT_64/48/32/16`=`0x9..0xa`, `CBRANCH_FORK_SPLIT`=`0x5e` — `gfx_8_0_enum.h:2298-2293`, `:2378` | **Aritmética del `512`** de `kfd_queue.c:460` (§3.2). |
| **Cuántas oleadas hay en vuelo, por cola**: `mmSPI_CSQ_WF_ACTIVE_STATUS` + `mmSPI_CSQ_WF_ACTIVE_COUNT_0..7`, `COUNT` = 11 b — `gfx_8_0_d.h:1823-1831`, `gfx_8_0_sh_mask.h:12811-12812` | **Si se pueden leer en esta placa.** `NOT_VERIFIED`: exige MMIO y GRBM, y este nodo no toca la GPU. |
| Geometría de colas: 2 MEC × 4 pipes × 8 queues = 64 — `gfx_v8_0.c:1901,1910-1911,1987-2003` | **Cualquier shader.** No hay compilador (§2.8). Hay *ensamblador* verificado (`012` §2.2), que es otra cosa. |
| **Todos los inputs del modelo, en runtime, por sysfs** — `kfd_topology.c:451,453,459,461,464,466,468,470,472` (§5.3) | **El `Shader Compiler Settings` de Mesa.** No está en el corpus. Es lo que produciría el VGPR *count* de un shader, y con él el lado "compiler" de R-NEW-68. |

---

## 5 · Observabilidad: el hallazgo que cambia el estado de una frontera

### 5.1 · La ocupación **no** es observable en esta ASIC por KFD — y el motivo no es el hardware

Comprobado por nombre, en tres pasos:

1. `K/drivers/gpu/drm/amd/amdkfd/kfd_process.c:279-280`
   ```c
   279  if (dev->kfd2kgd->get_cu_occupancy == NULL)
   280      return -EINVAL;
   ```
2. `K/drivers/gpu/drm/amd/amdgpu/amdgpu_amdkfd_gfx_v8.c:592-609` — la tabla `gfx_v8_kfd2kgd` **completa** (13 entradas, `:593-609`) **no tiene `.get_cu_occupancy`**. Es la tabla que Polaris12 usa (`kfd_device.c:295-298`).
3. `.get_cu_occupancy` está definido **solo** en cuatro implementaciones, todas de GFX9 o posterior: `amdgpu_amdkfd_gfx_v9.c:1259`, `amdgpu_amdkfd_aldebaran.c:183`, `amdgpu_amdkfd_arcturus.c:419`, `amdgpu_amdkfd_gc_9_4_3.c:541`.

**⇒ `PROVEN_ABSENT`:** el atributo `cu_occupancy` de KFD devuelve `-EINVAL` en esta placa. Refutador: que `gfx_v8_kfd2kgd` tenga esa entrada más abajo de la línea 609 — leí el bloque entero, termina en 609 con `};`.

### 5.2 · Pero el hardware y la geometría que necesita **sí están**

La implementación que falta son ~40 líneas de `amdgpu_amdkfd_gfx_v9.c:1022-1065`, y todo lo que usa existe para GFX8:

| lo que esa función necesita | ¿existe para GFX8? | cita |
|---|---|---|
| `mmSPI_CSQ_WF_ACTIVE_STATUS` | **sí** | `gfx_8_0_d.h:1823` (`0x24db`), máscara `ACTIVE 0xffffffff` en `gfx_8_0_sh_mask.h:12809-12810` |
| `mmSPI_CSQ_WF_ACTIVE_COUNT_0..7` | **sí**, los 8 | `gfx_8_0_d.h:1824-1831` (`0x24dc..0x24e3`), `COUNT 0x7ff` (11 b) en `gfx_8_0_sh_mask.h:12811-12812` |
| esquema «4 pipes × 8 queues por micro-engine» | **el driver lo fija así para gfx8** | `gfx_v8_0.c:1910-1911` |
| ese esquema es el que AMD declara válido | dice «true for GFX9 devices» | `amdgpu_amdkfd_gfx_v9.c:1050-1054` |

El comentario de `amdgpu_amdkfd_gfx_v9.c:1050-1054` es explícito:

```c
1050  * Assumption: queue map encodes following schema: four
1051  * pipes per each micro-engine, with each pipe mapping
1052  * eight queues. This schema is true for GFX9 devices
1053  * and must be verified for newer device families
```

**⇒ `PROVEN`:** los dos registros y la geometría que la función necesita están presentes y coherentes para GFX8.
**⇒ `NOT_VERIFIED`:** que se lean como AMD espera en esta placa. Eso exige una lectura GRBM de `SPI_CSQ_WF_ACTIVE_STATUS`, que este nodo no hace. **Refutador:** que devuelva 0 con colas activas.

**Clasificación del hueco: `DEPENDENCY_UNSATISFIED` por ~40 líneas de driver, no `OBSERVABILITY_LIMITED`.** Y por eso el rótulo correcto es *hueco de cableado*, no *muro*: el hardware no dice que no, el driver no lo pregunta.

### 5.3 · Los tres caminos de lectura que sí existen, sin MMIO

1. **`/sys/class/kfd/kfd/topology/<node>/properties`** — `kfd_topology.c:861-863` crea `topology`, `:869-870` crea `nodes`, `:699` el atributo se llama `properties`. Y publica **literalmente todos los inputs del modelo**:
   `simd_count` (`:437`), `max_waves_per_simd` (`:451`), `lds_size_in_kb` (`:453`), `wave_front_size` (`:459`), `array_count` (`:461`), `simd_arrays_per_engine` (`:464`), `cu_per_simd_array` (`:466`), `simd_per_cu` (`:468`), `max_slots_scratch_cu` (`:470`), `gfx_target_version` (`:472`).
   Con esos diez valores, la fórmula de `kfd_queue.c:459-460` es evaluable a mano sobre esta placa.
2. **`amdgpu_gca_config`** en debugfs — `amdgpu_debugfs.c:1720` (nombre), `:972-1002` (lector), cabecera de versión `5` en `:988`, y campos `max_shader_engines`, `max_tile_pipes`, `max_cu_per_sh`, `max_sh_per_se`, `max_backends_per_se`, `max_texture_channel_caches`, `max_gprs`, `max_gs_threads`, `max_hw_contexts` en `:989-997`.
3. **`DRM_IOCTL_AMDGPU_INFO`** — `amdgpu_kms.c:1020-1022` publica `wave_front_size`, `num_shader_visible_vgprs` (= `max_gprs`), `num_cu_per_sh`. **No puedo citar los offsets**: `amdgpu_drm.h` no está en el corpus (§2.8).

**Esto convierte §2.3 en refutable.** Si `amdgpu_gca_config` muestra `max_gprs != 256`, o `properties` muestra `max_waves_per_simd != 10` / `lds_size_in_kb != 64`, la corroboración de §2.3 cae. **Es la primera medición que otro nodo debería hacer, y no toca la GPU**: dos lecturas de ficheros de texto.

---

## 6 · N-INT-04 y R-NEW-68: la distinción, y por qué también se rompen entre sí

### 6.1 · Enunciado de la distinción

| | recuento | vida (*lifetime*) |
|---|---|---|
| **de quién es la propiedad** | del **hardware**: cuántos registros hay y de qué anchura | del **programa**: cuántas instrucciones pasa un registro vivo |
| **dónde se observa en GFX8** | `SQ_WAVE_GPR_ALLOC.{VGPR_BASE,VGPR_SIZE}` (`gfx_8_0_sh_mask.h:14455-14458`) y `SPI_RESOURCE_RESERVE_CU_x.VGPR` (`:10521-10522`) | **en ningún sitio** |
| **granularidad** | 4 VGPR (`cwsr…asm:728`) | — |
| **quién lo escribe** | el hardware, al conceder la oleada | el *shader scheduler* al asignar |

**El recuento es observable. La vida no.** Y no es una limitación del corpus: **es una limitación del hardware**, y se puede demostrar:

**⇒ `PROVEN_ABSENT` (alcance: el mapa de registros GFX8 completo, `asic_reg/gca/gfx_8_0_{d,enum,sh_mask}.h`):** no existe ningún registro, campo ni evento de rendimiento que reporte duración de vida de un VGPR. Se comprobó por búsqueda de nombre sobre los tres ficheros completos: los identificadores que existen en torno a la asignación son `*GPR_ALLOC*`, `*SPI_PERF_RA*` (1975-2020), `*SPI_RESOURCE_RESERVE*` y `COMPUTE_PGM_RSRC1/2`; **todos son de recuento**. Refutador: un campo con `LIFE`, `LIFETIME`, `DEAD`, `STALL_VGPR_LIVE` o similar en esos tres ficheros. No hay ninguno.

**Y el recuento ni siquiera se puede leer desde la CPU.** `SQ_WAVE_GPR_ALLOC` es un *hardware register* por oleada, no un registro MMIO. La aritmética lo demuestra: `SQ_HW_REG_GPR_ALLOC = 0x5` (`gfx_8_0_enum.h:4051`) y `ixSQ_WAVE_GPR_ALLOC = 0x15` (`gfx_8_0_d.h:2137`); `SQ_HW_REG_LDS_ALLOC = 0x6` (`:4052`) y `ixSQ_WAVE_LDS_ALLOC = 0x16` (`:2138`); `SQ_HW_REG_MODE = 0x1` (`:4047`) y `ixSQ_WAVE_MODE = 0x11` (`:2134`). **Base = `0x10` en los tres casos.** Frente a `mmSQ_RANDOM_WAVE_PRI 0x2303` (`gfx_8_0_d.h:2004`), que sí es MMIO.

**⇒ `PROVEN_ABSENT` (alcance: los 632 `.c` de `amdgpu/` y los de `amdkfd/`):** ningún fichero C del árbol usa `ixSQ_WAVE_*`. Búsqueda por nombre sobre `K/drivers/gpu/drm/amd/`: los únicos aciertos son las definiciones de `gfx_6_0_d.h:76-95`. El **único** consumidor de `SQ_WAVE_GPR_ALLOC` en todo el repositorio es el manejador de traps, **que corre en la GPU**: `cwsr_trap_handler_gfx8.asm:726` y `:732`, con `hwreg(HW_REG_GPR_ALLOC, …)`.

Consecuencia operativa, y es la que hay que escribir: **para medir el recuento de una oleada hay que detener esa oleada y ejecutar código dentro de ella** (el único lector de `GPR_ALLOC` en el repositorio es el manejador de traps, que corre en la GPU). No hay atajo desde el host. Y sin GPU, no hay nada.

### 6.2 · La reespecificación que exigen las once ideas

| idea | qué necesita | ¿existe en el corpus? |
|---|---|---|
| N-INT-01 latencia oculta vs throughput | `WAVE_READY` / `WAVE_CYCLES` (`gfx_8_0_enum.h:2330-2331`), `WAVES` / `LEVEL_WAVES` (`:2288-2289`) | contadores ✔; **cómo se programan** ✘ (`amdgpu_perfctr*.c` ausente) |
| N-INT-02 distancia load→use | `WAIT_CNT_LGKM` (`:2333`) ÷ `INSTS_VMEM_RD` (`:2312`) | idem |
| N-INT-03 dependencia artificial vs natural | **`VALU_DEP_STALL` (`:2387`) vs `VALU_STARVE` (`:2388`)** | idem — **es el par discriminante más limpio de los once** |
| **N-INT-04 lifetime de VGPR** | un observable de *vida* | **no existe, ni interno ni externo** |
| N-INT-05 frontera ILP↔occupancy | `SPI_PERF_RA_VGPR_SIMD_FULL_*` (`:1983-1990`) vs `WAVE_SIMD_FULL_*` (`:1975-1982`) vs `BAR_CU_FULL_*` (`:2004-2006`) | idem — **medible sin la fórmula** (§3.1) |
| N-INT-06 scheduler-sensitive | que `SQ_RANDOM_WAVE_PRI` **no** se programa para Polaris12 (`gfx_v8_0.c:339-358` vs `:207`) | **el hecho es `PROVEN`**; el valor por defecto, `NOT_DETERMINED` |
| N-INT-07 instruction-mix | `INSTS_*` (`:2309-2323`), `VALU_SRC_C_CONFLICT` (`:2399`) | idem |
| N-INT-08 escalar/vector | `SGPR_SIMD_FULL_*` vs `VGPR_SIMD_FULL_*` (`:1983-1998`) | idem |
| R-NEW-63 barrido de ILP | variante de shader por punto del barrido | requiere emitir shaders |
| R-NEW-64 matriz occupancy×ILP | los dos ejes | requiere medir occupancy por shader ⇒ ver §6.3 |
| R-NEW-66 barrido de ancho | operaciones de precisión (medio / float / doble) | **no depende de la microarquitectura**: depende de la semántica de las operaciones |
| R-NEW-68 complejidad vs presión de registros | ver §6.3 | **ver §6.3** |

### 6.3 · Las dos ideas que son la misma, con el argumento

**`R-NEW-68` (complejidad del shader vs presión de registros) y `N-INT-04` (lifetime de VGPR como variable independiente) son la misma idea, y la forma que tiene R-NEW-68 escrita es la forma que N-INT-04 declara inválida.**

El argumento, sin apelar a nada externo:

1. R-NEW-68 tiene dos variables: «complejidad del shader» y «presión de registros». La segunda es la independiente para la primera.
2. Lo único que el proyecto puede llamar «presión de registros» en GFX8 es `SQ_WAVE_GPR_ALLOC.VGPR_SIZE` (§6.1), que es un **recuento** con granularidad de 4 (`cwsr…asm:728`).
3. El lado de la comparanda, «complejidad del shader», en un driver propio es la longitud y la mezcla del ISA emitido (`gfx_8_0_enum.h:2309-2323` da contadores para medirla una vez emitida).
4. Por tanto, tal como está redactada, **R-NEW-68 mide: complejidad → recuento de VGPR.** Y eso es exactamente la mitad de N-INT-04 que la propia definición de N-INT-04 rechaza (*«register count ≠ register lifetime»*, `ideas.md:388`).
5. La otra mitad —*lifetime*— no tiene observable (§6.1). No es que sea difícil: es que el mapa de registros de GFX8 no tiene ningún campo que la represente, y eso se comprobó sobre los tres ficheros completos.

**Consecuencia, y es una strengthening, no una buried:**
- **R-NEW-68 necesita reespecificarse** a «complejidad del shader → **recuento** de VGPR/SGPR concedidos», que sí es ejecutable con `llvm-mc` (`012`) + una lectura de `GPR_ALLOC` desde la propia oleada. Y entonces **deja de ser una idea de microarquitectura** y pasa a ser una del compilador.
- **N-INT-04 pasa de «idea» a «requiere cadena de compilación y visibilidad».** Concretamente, dos eslabones que hoy no existen: (a) un emisor de shaders GFX8, y (b) un mecanismo de lectura de `SQ_WAVE_GPR_ALLOC` desde la GPU. El corpus no aporta ninguno de los dos, y el primero no lo puede aportar nadie sin fuente externa.

**⇒ `DECIDIDO`:** fusionar R-NEW-68 dentro de N-INT-04 bajo el rótulo «presión de registros **declarada** vs **concedida**», y registrar por separado que la dimensión *lifetime* queda `NOT_DETERMINED` con el hueco de §6.1. Esto satisface la regla de no crear una idea nueva cuando sólo cambia el parámetro experimental: aquí no cambia un parámetro, cambia **qué magnitud se mide**, y eso es una reespecificación con su hueco declarado.

---

## 7 · Estado de salida

```
PROVEN            geometría del bloque GFX8 para Polaris12; 4 SIMD/CU; 10 oleadas/SIMD;
                  32 slots scratch/CU; wave64; 64 KiB LDS/CU; 256 VGPR; 102 SGPR; 8 contextos;
                  granularidades 4 VGPR / 16 SGPR / 64 DW LDS; PGM_RSRC1.VGPRS=15 ⇔ 64 VGPR;
                  64 colas de cómputo; SPI_RESOURCE_RESERVE_CU_x = 0x00000800 con LDS=8;
                  WAVES_PER_SH sin tope por software; VGPR/SGPR/LDS/BARRIER tienen contador propio;
                  VALU_DEP_STALL y VALU_STARVE existen; cu_occupancy ausente en gfx_v8;
                  SPI_CSQ_WF_ACTIVE_* presentes en GFX8; SQ_WAVE_* no legibles desde CPU;
                  no hay compilador AMDGPU en el corpus; *baco* es firmware.
CORROBORATED     256 VGPR y 64 KiB LDS/CU y 40 oleadas/CU, por tres sitios independientes (§2.3).
                  El valor 10 (misma constante que GFX9, sin fuente que lo declare para GFX8, §3.3).
CONFLICT          ancho de SQ_WAVE_GPR_ALLOC.SGPR_SIZE: 4 bits en el registro vs 3 en el
                  ensamblador de AMD — `FIXME` en cwsr_trap_handler_gfx8.asm:44.
NOT_DETERMINED   función de reparto recursos→oleadas (firmware);
                  decodificación del campo LDS de SPI_RESOURCE_RESERVE_CU_x;
                  tamaño en bytes de un slot de scratch;
                  valor por defecto de SQ_RANDOM_WAVE_PRI en esta placa;
                  lectura real de SPI_CSQ_WF_ACTIVE_* en esta placa;
                  contenido del documento ISA GCN3 (identificado, no leído — finding 991).
NOT_FOUND        nº de CU / CU-por-SH / SH-por-SE / nº de SE (vienen del VBIOS, amdgpu_atombios.c:744-750);
                  amdgpu_perfctr*.c; include/uapi/drm/amdgpu_drm.h;
                  si_decodepacket.c y tabla de paquetes GFX8;
                  asic_reg/gc/ sin ningún 8_x (la premisa del encargo, §1).
PROVEN_ABSENT   (revisados por nombre, alcance acotado y escrito)
                  todo lifetime de registro en el mapa GFX8 (§6.1);
                  todo lector CPU de ixSQ_WAVE_* (§6.1);
                  toda fuente de compilador AMDGPU (§2.8).
HYPOTHESIS      512 = max_hw_contexts(8) × 64 colas de cómputo (§3.2);
                  BULKY = "carga voluminosa" cobrable en el asignador de recursos;
                  PGM_RSRC1 y SQ_WAVE_GPR_ALLOC comparten decodificación (la comparten en VGPR,
                  no en SGPR — §2.6).
```

### Lo que queda abierto, y quién lo cierra

| hueco | el que lo cierra | coste |
|---|---|---|
| corroborar §2.3 contra la placa | leer `amdgpu_gca_config` y `/sys/class/kfd/kfd/topology/*/properties` | **dos lecturas de fichero de texto, sin MMIO, sin root** |
| ¿10 oleadas/SIMD es correcto en GFX8? | la lectura anterior; si `max_waves_per_simd` ≠ 10, §2.3 y §3.3 caen | misma lectura |
| decodificar `LDS=8` en `SPI_RESOURCE_RESERVE_CU_0` | experimento de barrido del campo, con lectura del mismo registro | MMIO |
| la función de reparto | barrido de `PGM_RSRC1.VGPRS` leyendo `SPI_PERF_RA_VGPR_SIMD_FULL_*` — **no hace falta la fórmula** | driver propio + contadores |
| `cu_occupancy` en GFX8 | portar `kgd_gfx_v9_get_cu_occupancy` a `gfx_v8_kfd2kgd`; la geometría ya está (§5.2) | ~40 líneas |
| lifetime de VGPR | **nadie, hoy.** Requiere emisor de shaders **y** lectura de `GPR_ALLOC` desde la GPU | cadena nueva |
| nº de CU de esta placa | VBIOS, o `amdgpu_gca_config` | una lectura |

**Lo único que este turno ha hecho cambiar de estado, en una línea:** la frontera «observabilidad de ocupación en GFX8» pasa de *muro de hardware* a *hueco de cableado de ~40 líneas en `gfx_v8_kfd2kgd`*, con los dos registros (`gfx_8_0_d.h:1823-1831`) y la geometría (4×8, `gfx_v8_0.c:1910-1911`) ya verificados como presentes.

---

## 8 · Citas de este turno

- `K/drivers/gpu/drm/amd/amdkfd/kfd_device.c:293-296`
- `K/drivers/gpu/drm/amd/amdkfd/kfd_queue.c:403,414,436,446,459-460,492`
- `K/drivers/gpu/drm/amd/amdkfd/kfd_priv.h:818-824`
- `K/drivers/gpu/drm/amd/amdkfd/kfd_crat.c:2282-2295`
- `K/drivers/gpu/drm/amd/amdkfd/kfd_topology.c:437-473,699,861-870,2090-2091`
- `K/drivers/gpu/drm/amd/amdkfd/kfd_process.c:265-280`
- `K/drivers/gpu/drm/amd/amdkfd/cwsr_trap_handler_gfx8.asm:39-44,304-306,319,719-722,725-728,731-734,737-739`
- `K/drivers/gpu/drm/amd/amdgpu/gfx_v8_0.c:49-51,60,207,339-358,360-368,783-791,1382-1400,1496,1528-1531,1681-1695,1901,1910-1911,1987-2003,7119-7125`
- `K/drivers/gpu/drm/amd/amdgpu/gfx_v8_0.h:592-609` *(tabla `gfx_v8_kfd2kgd`, vía `amdgpu_amdkfd_gfx_v8.c`)*
- `K/drivers/gpu/drm/amd/amdgpu/amdgpu_amdkfd_gfx_v8.c:592-609`
- `K/drivers/gpu/drm/amd/amdgpu/amdgpu_amdkfd_gfx_v9.c:978-1065,1259`
- `K/drivers/gpu/drm/amd/amdgpu/amdgpu_amdkfd_aldebaran.c:183`, `…arcturus.c:419`, `…gc_9_4_3.c:541`
- `K/drivers/gpu/drm/amd/amdgpu/amdgpu_drv.c:2034-2041`
- `K/drivers/gpu/drm/amd/amdgpu/amdgpu_atombios.c:731-755`
- `K/drivers/gpu/drm/amd/amdgpu/amdgpu_discovery.c:1742-1802`
- `K/drivers/gpu/drm/amd/amdgpu/amdgpu_debugfs.c:972-1002,1720`
- `K/drivers/gpu/drm/amd/amdgpu/amdgpu_kms.c:1020-1022`
- `K/drivers/gpu/drm/amd/amdgpu/amdgpu_gfx.h:231-250,307-319`
- `K/drivers/gpu/drm/amd/amdgpu/gfx_v9_0.c:7902-7907`
- `K/drivers/gpu/drm/amd/include/asic_reg/gca/gfx_8_0_d.h:1627-1658,1823-1831,2133-2139`
- `K/drivers/gpu/drm/amd/include/asic_reg/gca/gfx_8_0_enum.h:1975-2020,2284-2420,2734-2735,2816,2822,4047-4052,6831-6833`
- `K/drivers/gpu/drm/amd/include/asic_reg/gca/gfx_8_0_sh_mask.h:8301-8356,8365-8368,10521-10530,10681-10688,12809-12812,13533-13538,14455-14466`
- `08-ARQUITECTURA/designs/012-gcn8-assembler-and-isa-corpus.md` §2.2-2.4, §3
- `06-INGENIERIA-INVERSA/findings/265-el-tamano-de-cache-de-gfx8-no-esta-en-ningun-sitio.md`
- `06-INGENIERIA-INVERSA/findings/991-el-isa-de-gfx8-si-tiene-fuente-primaria-publicada.md`
- `ideas.md:388,389,392,91-97,276-282`

**Renumeración: ninguna.** No he creado ID nuevo. No he editado ningún fichero del árbol salvo éste.
