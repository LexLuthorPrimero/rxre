# MEMORIA-GFX8 — jerarquía de caché, compresión DCC y topología VRAM/GART en Polaris 12

```
NODE_ID=MEMORIA-GFX8
WORK_CLASS=READ_ONLY/EVIDENCE
WRITE_EXECUTION=1 fichero nuevo (este)
GPU=INTACTA · SIN_SUDO · SIN_COMMITS · SIN_GREP(dado por python3+open/os.walk)
ALCANCE=jerarquía de memoria, caché, compresión, topología VRAM/GART, y estado de la tabla GART del driver propio
FUERA_DE_ALCANCE=VGPR/SGPR/LDS/SIMD y modelo de occupancy -> ver nodo MICROARCH-GFX8
```

---

## 0. Verificación de entradas y ausencia de drift

**Universo de corpus.** Cuatro árboles del kernel presentes en el repo. Verificado que los tres
ficheros GFX8 que este nodo cita son **byte-idénticos en los cuatro**, y que
`gfx_8_0_enum.h` coincide con el hash fijado por el nodo `Q5-MEM-TABLES`
(`08-ARQUITECTURA/artifacts/Q5-MEM-TABLES/q5-mem-tables.md` §0). **No hubo `DRIFT_DETECTED`.**

```
299228e0bbd75d0f5879efbaea0234793fa77dece92646efe6adb6f5f9832a4a  include/asic_reg/gca/gfx_8_0_d.h
fa6b8ff974fccdd54aa0e1b6a6430508a558fd263ead90eaf70bef262e4d5d63  include/asic_reg/gca/gfx_8_0_enum.h
c2dd6e2f68a047114578ed48de852fcc02fae4c07dada7ef03fa89a6cde1cc85  include/asic_reg/gca/gfx_8_0_sh_mask.h
```
presentes en `RESEARCH/working/linux-7.1.3`, `RESEARCH/baseline/linux-7.1.3`,
`RESEARCH/kernelbuild/linux-7.1.3` y `rx550-upstream-7.2.8/linux-7.2.8`. Se cita
`RESEARCH/working/linux-7.1.3`; es inmaterial cuál.

**Negativo heredado, re-verificado.** El path de perfmon de GFX8 no existe: comprobado sobre
`gfx_v8_0.c` (247 678 B), `soc15.c`, `soc21.c`, `soc24.c`; los cuatro tienen
`sq_cmds=False`, `gfx8_=False`, `grnm=False`, `PERFCTLCNT=False`, `amdgpu_perf=False`.
Clase: **`PROVEN_ABSENT` dentro de esos cuatro ficheros** (scope completo de los cuatro, no un grep).

**Identidad de ASIC, medida y no heredada.** `POLARIS12` se maneja en
`amdgpu/amdgpu_drv.c:2034-2041` (8 IDs PCI, `0x6980…0x699F`); la cadena de nombre está en
`amdgpu/amdgpu_device.c:132` (`"POLARIS12"`); y los bloques IP que lo atienden son
`amdgpu/gmc_v8_0.c:141` y `amdgpu/gfx_v8_0.c:784`. Por tanto **POLARIS12 ⇒ gfx8.0 ⇒ cabeceras
`gfx_8_0_*`**, y su GMC es `gmc_v8_0.c`. Estado: `CORROBORATED` por dos rutas independientes
(tabla PCI → switch de IP).

---

## 1. Corrección previa que condiciona todo el nodo: `asic_reg/gc/` NO es esta ASIC

El enunciado de este nodo señalaba `drivers/gpu/drm/amd/include/asic_reg/gc/` como lugar natural
para los hechos de jerarquía de memoria. **Medido: ese directorio no contiene ninguna cabecera
GFX8.**

```
gc/ contiene exactamente: gc_9_0_*  gc_9_1_*  gc_9_2_1_*  gc_9_4_1_*  gc_9_4_2_*  gc_9_4_3_*
                            gc_10_1_0_*  gc_10_3_0_*  gc_11_0_0_*  gc_11_0_3_*
                            gc_11_5_0_*  gc_12_0_0_*  gc_12_1_0_*   (+ _default.h / _offset.h)
30 ficheros, 0 de ellos gc_8_*
```

Los registros de la familia VI (Tonga/Fiji/Carrizo/Polaris10/Polaris12/VegaM) viven en
`asic_reg/**gca**/gfx_8_0_d.h`, `gfx_8_0_enum.h`, `gfx_8_0_sh_mask.h` — 2 801 + 20 789 + 1 448
líneas. `gca` contiene también `gfx_7_0`, `gfx_7_2`, `gfx_8_1`, `gfx_6_0`.

**Consecuencia normativa, y es el punto más caro de este documento:** cualquier hecho de caché,
L2, textura o DCC sacado de `gc/` es un hecho de **Vega10 / Vega20 / Navi10 / Navi14 /
Arcturus / Alchemist**, no de Polaris 12. Las tres generaciones usan los mismos *nombres*
(`CB_COLOR0_DCC_CONTROL`, `TCC_CTRL__CACHE_SIZE`, `TCC_ADDR_CONFIG`…) con **codificaciones
distintas**. Citar `gc/` como si fuera esta ASIC es exactamente el error que este nodo tiene
prohibido cometer, y es el más fácil de cometer porque los nombres coinciden.

**Falsificador de esta corrección.** Si existiera un `gc_8_*` o una cadena `gfx_8_0` reexportada
desde `gc/`, la corrección sería falsa. Comprobado por listado completo del directorio: no existe.
Refutada la corrección no procede.

**Consecuencia sobre el recuento de 30 ficheros que el nodo principal ya tiene medido**
("30 ficheros de cabeceras de registro"): ese recuento es de `gc/` y por tanto **no describe esta
ASIC**. Se conserva como dato de la vía `gc/`, no como inventario de GFX8. No lo rederivo.

---

## 2. Hechos de jerarquía de memoria recuperables del corpus

Cada fila: qué lo prueba, y **hasta dónde**. Estados: `PROVEN` (el texto del corpus lo afirma y el
ámbigo está completo), `DERIVED` (calculado aquí con aritmética que el corpus hace explícita),
`NOT_DETERMINED` (el corpus no lo dice), `NOT_FOUND` (buscado en scope completo y no está).

### 2.1 Taxonomía de niveles — la da el propio kernel, con nombre propio

`amdkfd/kfd_crat.c:1425-1510`, `kfd_fill_gpu_cache_info_from_gfx_config()`. El kernel enumera la
jerarquía de GFX8 en seis entradas y **las nombra**. Los campos que las dimensionan están en
`amdgpu/amdgpu_gfx.h:288-304`.

| # | Nombre literal en el kernel | Campos que lo dimensionan | `cache_line_size` desde |
|---|---|---|---|
| L1 | `/* TCP L1 Cache per CU */` | `gc_tcp_l1_size`, `num_cu_shared = gc_num_tcp_per_wpg / 2` | `gc_tcp_cache_line_size` (`kfd_crat.c:1440`) |
| L1 | `/* Scalar L1 Instruction Cache per SQC */` | `gc_l1_instruction_cache_size_per_sqc`, `num_cu_shared = gc_num_sqc_per_wgp * 2` | `gc_instruction_cache_line_size` (`:1454`) |
| L1 | `/* Scalar L1 Data Cache per SQC */` | `gc_l1_data_cache_size_per_sqc` | `gc_scalar_data_cache_line_size` (`:1467`) |
| L1 | `/* GL1 Data Cache per SA */` | `gc_gl1c_per_sa * gc_gl1c_size_per_instance` | **constante `128` escrita a mano** (`:1483`), sin campo de discovery |
| L2 | `/* L2 Data Cache per GPU (Total Tex Cache) */` | `gc_gl2c_per_gpu` | `gc_tcc_cache_line_size` (`:1494`) |
| L3 | `/* L3 Data Cache per GPU */` | `adev->gmc.mall_size / 1024` | **constante `64`** (`:1507`) |

Esto es `PROVEN` como taxonomía: los comentarios son del driver, el scope es la función entera.

**Sobre el L3 de esta ASIC.** `mall_size` se asigna solo en `amdgpu/gmc_v10_0.c:780-792`; el
default de discovery es `mall_size = 0` (`amdgpu/amdgpu_discovery.c:1856`, `1868`). `gmc_v8_0.c`
no lo asigna. Consecuencia: **la entrada L3 no se emite para POLARIS12** → **no hay L3 en la vía
de discovery de GFX8**. Clase: `DERIVED` (dos ausencias de asignación, scope completo de
`gmc_v8_0.c` y de `gmc_v10_0.c`). Cuidado: esto prueba que *la ruta de discovery* no reporta L3, no
que el silicio no tenga ninguna estructura detrás de la L2. `NOT_DETERMINED` para eso.

### 2.2 Los tamaños y líneas de caché de POLARIS12 NO están en el corpus

Los seis campos de la tabla anterior salen de `gc_info`, la **tabla de IP discovery** que llega del
**firmware**, leída en `amdgpu/amdgpu_discovery.c:1767-1786`:

```
:1768  gc_num_tcp_per_wpg        = le32_to_cpu(gc_info->v1_2.gc_num_tcp_per_wpg)
:1769  gc_tcp_l1_size            = le32_to_cpu(gc_info->v1_2.gc_tcp_l1_size)
:1771  gc_l1_instruction_cache_size_per_sqc = ... v1_2 ...
:1772  gc_l1_data_cache_size_per_sqc         = ... v1_2 ...
:1773  gc_gl1c_per_sa            = ... v1_2 ...
:1774  gc_gl1c_size_per_instance = ... v1_2 ...
:1775  gc_gl2c_per_gpu           = ... v1_2 ...
:1779  gc_tcp_cache_line_size          = ... v1_3 ...
:1781  gc_instruction_cache_line_size  = ... v1_3 ...
:1783  gc_scalar_data_cache_line_size  = ... v1_3 ...
:1784  gc_tcc_size                    = ... v1_3 ...
:1785  gc_tcc_cache_line_size          = ... v1_3 ...
```

**El corpus tiene el lector y no tiene el valor.** Estado de cada uno de estos números para
POLARIS12: `NOT_DETERMINED`. No se pueden derivar del fuente; vienen del blob de firmware que
este nodo no abre.

**Y hay una segunda fuente, más fuerte, que además es un defecto del driver de referencia.**
`kfd_crat.c:1613-1616`:

```c
case CHIP_POLARIS12:
        *pcache_info = polaris12_cache_info;
        num_of_cache_types = ARRAY_SIZE(polaris12_cache_info);
```

y `kfd_crat.c:130`:

```c
#define polaris12_cache_info carrizo_cache_info
```

La tabla que el kernel asocia a **POLARIS12** es, literalmente, la de **Carrizo** (APU GCN3). Y esa
tabla (`kfd_crat.c:90-123`) contiene **tres entradas L1 y nada más**, con el comentario literal en
`kfd_crat.c:122`:

```c
	/* TODO: Add L2 Cache information */
```

- L1 `TCP L1 Cache per CU`: `.cache_size = 16`, `.cache_line_size = 64`, `.num_cu_shared = 1`
- L1 `Scalar L1 Instruction Cache`: `.cache_size = 32`, `.cache_line_size = 64`, `.num_cu_shared = 4`
- L1 `Scalar L1 Data Cache`: `.cache_size = 16`, `.cache_line_size = 64`, `.num_cu_shared = 4`
- **sin L2, sin L3**

La misma tabla la comparten `hawaii`(via kaveri), `tonga`, `fiji`, `polaris10`, `polaris11`,
**`polaris12`**, `vegam` (`kfd_crat.c:125-131`). Que un solo array sirva para un APU Carrizo y
para una RX 550 discreta de 2 GiB prueba que **no es una descripción por ASIC**: es un valor por
defecto. Implementación, no autoridad (`IMPLEMENTATION_IS_NOT_AUTHORITY`).

> **Consecuencia dura, y es la que manda sobre `M-01` y `N-INT-16/17/18`:** el corpus **no**
> contiene ni el tamaño de la L2 de esta tarjeta ni su línea de caché ni la línea de la L1 de
> textura. Un barrido de capacidad de caché (N-INT-16) necesita un punto de partida; **ese punto de
> partida no existe derivablemente**. No es una carencia del barrido: es una dependencia
> (`DEPENDENCY_UNSATISFIED`) cuya única fuente es el firmware en runtime.

**Falsificador.** Si existiera en el corpus una constante de L2 para POLARIS12 distinta de esta
tabla, la conclusión caería. Scope comprobado: `kfd_crat.c` completo (tabla estática + relleno
desde `gfx.config`); `kfd_crat.h:1-10` (struct, 5 campos, sin más). No la hay.
Refutación adicional posible: que el firmware de esta tarjeta no rellene `v1_2`/`v1_3` — eso
haría que los campos valieran 0 y la función de relleno no emitiera ninguna entrada; no se puede
descartar sin runtime. Queda `NOT_DETERMINED` en esa sub-capa.

### 2.3 Registros de caché de GFX8: qué existe, y qué code vale para esta ASIC

Aquí sí hay valores, porque la **secuencia golden** que el kernel aplica a `CHIP_POLARIS12`
programa algunos de ellos. `amdgpu/gfx_v8_0.c:783-791`:

```c
case CHIP_POLARIS11:
case CHIP_POLARIS12:
        amdgpu_device_program_register_sequence(adev,
                        golden_settings_polaris11_a11, ...);
        amdgpu_device_program_register_sequence(adev,
                        polaris11_golden_common_all, ...);
```

**POLARIS11 y POLARIS12 comparten secuencia golden.** Es decir: la evidencia de hardware más fuerte
que hay para esta ASIC es una tabla compartida con otro chip. Cualquier cosa que dependa de
"POLARIS12 tiene su propia calibración de caché" es `REFUTED`.

`golden_settings_polaris11_a11` (`gfx_v8_0.c:339-358`) tiene 16 entradas. Las dos que importan aquí:

```
gfx_v8_0.c:353   mmTCC_CTRL,        0x00100000, 0xf31fff7f
gfx_v8_0.c:354   mmTCP_ADDR_CONFIG, 0x000003ff, 0x000000f3
```

Decodificados contra los campos de `gfx_8_0_sh_mask.h` (MASK+SHIFT, sin suposiciones):

| Registro | Campo | Máscara | Shift | Valor | sh_mask |
|---|---|---|---|---|---|
| `TCC_CTRL` | `CACHE_SIZE` | `0x3` | 0 | **3** | `:15527-15528` |
| `TCC_CTRL` | `RATE` | `0xc` | 2 | 3 | `:15529-15530` |
| `TCC_CTRL` | `WRITEBACK_MARGIN` | `0xf0` | 4 | 7 | `:15531-15532` |
| `TCC_CTRL` | `METADATA_LATENCY_FIFO_SIZE` | `0xf00` | 8 | 15 | `:15533-15534` |
| `TCC_CTRL` | `SRC_FIFO_SIZE` | `0xf000` | 12 | 15 | `:15535-15536` |
| `TCC_CTRL` | `LATENCY_FIFO_SIZE` | `0xf0000` | 16 | 15 | `:15537-15538` |
| `TCC_CTRL` | `WB_OR_INV_ALL_VMIDS` | `0x100000` | 20 | 1 | `:15539-15540` |
| `TCC_CTRL` | **`MDC_SIZE`** | `0x3000000` | 24 | **3** | `:15541-15542` |
| `TCC_CTRL` | **`MDC_SECTOR_SIZE`** | `0xc000000` | 26 | **0** | `:15543-15544` |
| `TCC_CTRL` | `MDC_SIDEBAND_FIFO_SIZE` | `0xf0000000` | 28 | 15 | `:15545-15546` |
| `TCP_ADDR_CONFIG` | **`NUM_TCC_BANKS`** | `0xf` | 0 | **3** | `:15987-15988` |
| `TCP_ADDR_CONFIG` | `NUM_BANKS` | `0x30` | 4 | 3 | `:15989-15990` |
| `TCP_ADDR_CONFIG` | `COLHI_WIDTH` | `0x1c0` | 6 | 3 | `:15991-15992` |
| `TCP_ADDR_CONFIG` | `RB_SPLIT_COLHI` | `0x200` | 9 | 0 | `:15993-15994` |

**Refutación de una inferencia que iba a ser tentadora.** `TCC_CTRL = 0xf31fff7f` es
**idéntico, byte a byte, en las siete ASIC** de la tabla: Tonga (`gfx_v8_0.c:209`), VegaM
(`:322`), **Polaris11/12 (`:353`)**, Polaris10 (`:385`), Fiji (`:426`), Iceland (`:484`), Cz
(`:581`), Stoney (`:686`). O sea: `TCC_CTRL.CACHE_SIZE = 3` **no discrimina a esta tarjeta**; es
una constante de familia. **No se puede derivar "el tamaño de la L2 de la RX 550" de ahí.** Quien
lo intente está usando el nombre del campo como si fuera la semántica.

**Lo que sí discrimina es `TCP_ADDR_CONFIG`.** Medido, todos en `gfx_v8_0.c`:

| ASIC | `mmTCP_ADDR_CONFIG` | `NUM_TCC_BANKS` (decod.) | línea |
|---|---|---|---|
| Tonga | `0x000002fb` | 0xb = 11 | `:211` |
| Fiji | `0x000000ff` | 0xf = 15 | `:428` |
| Iceland | `0x000000f1` | 1 | `:486` |
| Stoney | `0x000000f1` | 1 | `:688` |
| Cz | `0x000000f3` | 3 | `:583` |
| **Polaris11/12** | **`0x000000f3`** | **3** | **`:354`** |
| Polaris10 (gfx8.1) | `0x000000f7` | 7 | `:386` |
| VegaM | `0x000000f7` | 7 | `:323` |

**Hecho duro y con fuerza de arquitectura:** el campo `NUM_TCC_BANKS` vale **3 para Polaris 12 y 7
para Polaris 10** — la mitad. Independencia deInterpretation: si el código fuera "número de bancos"
literal, Polaris 12 tendría 3 bancos de textura y Polaris 10, 7; si fuera `log2(n)` por el nombre
del campo y el comparador de `CB_ADDR_CONFIG` (`:6741-6759`, `NumBanks`/`BankWidth`/`BankHeight`
/`BankWidthHeight`), serían 4 contra 8. **La codificación código→bancos no está en el corpus.**
Lo que sí está es la **desigualdad**, y eso no depende de la convención: la granularidad de
direccionado de la L2 de Polaris 12 es **distinta** y **menor** que la de Polaris 10. Eso es
`PROVEN`; el número absoluto de bancos es `NOT_DETERMINED`.

**Falsificador de la desigualdad.** Si `TCP_ADDR_CONFIG` se re-programara en runtime con otro valor
para esta tarjeta, la tabla sería historia y no estado actual. Busqué la re-programación:
`gfx_v8_0.c:3728` reescribe `mmGB_ADDR_CONFIG` desde `adev->gfx.config.gb_addr_config` en la
routine de EDC, **pero no hay ninguna re-escritura de `mmTCP_ADDR_CONFIG` ni de `mmTCC_CTRL` en
todo `gfx_v8_0.c` fuera de las tablas golden** (scope: 7 207 líneas, filtrado completo). La
secuencia golden queda. Aun así: golden ≠ lectura; el valor *real en runtime* es `NOT_DETERMINED`
hasta que se lea el registro.

### 2.4 Registro de caché de textura (L1) — presente, sin valor para esta ASIC

- `mmTCP_CNTL = 0x2b02` (`gfx_8_0_d.h:2316`) con `TCP_CNTL__L1_SIZE` **máscara `0xc`, shift 2**
  (`gfx_8_0_sh_mask.h:15941-15942`): campo de **2 bits**.
- `mmSQC_CONFIG = 0x2301` (`gfx_8_0_d.h:2000`) con
  `INST_CACHE_SIZE` **2 bits** (`:13451-13452`) y `DATA_CACHE_SIZE` **2 bits** (`:13453-13454`).
- `mmSQC_CACHES = 0xc348` (`gfx_8_0_d.h:2001`) con `TARGET_INST`, `TARGET_DATA`, `INVALIDATE`,
  `WRITEBACK`, `VOL`, `COMPLETE` (`:13477-13488`): es el **registro de control de invalidación/escritura
  de las cachés de instrucción y de datos**, no de capacidad.

**Ni `mmTCP_CNTL` ni `mmSQC_CONFIG` aparecen en `golden_settings_polaris11_a11`.** Consecuencia
`PROVEN_ABSENT` dentro de `gfx_v8_0.c` (scope completo): **la secuencia golden que el kernel aplica
a esta tarjeta no programa el tamaño de la L1 de textura ni el de las cachés escalar.** Por tanto
**el valor de `TCP_CNTL.L1_SIZE` y de `SQC_CONFIG.*_CACHE_SIZE` para POLARIS12 es
`NOT_DETERMINED`** y no hay ni una línea del driver que lo escriba. Refutaría esta conclusión un
`WREG32(mmTCP_CNTL` o `mmSQC_CONFIG` en cualquier `.c`; no existe en `gfx_v8_0.c`.

Tamaño en bytes: `NOT_DETERMINED` en todos los casos. **La tabla de encodings 2-bit → bytes no
existe en el corpus.** Eso no es un detalle: es lo que impide cerrar `M-01` sin runtime.

### 2.5 Caché de metadatos de DCC (`MDC`) — el enlace DCC↔L2, y existe en GFX8

`TCC_CTRL` tiene tres campos `MDC_*` (`gfx_8_0_sh_mask.h:15541-15546`) y el valor que la golden
programa para esta ASIC es `MDC_SIZE = 3`, `MDC_SECTOR_SIZE = 0`, `MDC_SIDEBAND_FIFO_SIZE = 15`.

Nombre literal: `MDC` aparece como `MDC_SIZE`, `MDC_SECTOR_SIZE`, `MDC_SIDEBAND_FIFO_SIZE`, y en
los contadores como `TCC_PERF_SEL_MDC_*` (`gfx_8_0_enum.h:4621-4627`):

```
TCC_PERF_SEL_MDC_TAG_HIT                            = 0x63
TCC_PERF_SEL_MDC_SECTOR_HIT                         = 0x64
TCC_PERF_SEL_MDC_SECTOR_MISS                        = 0x65
TCC_PERF_SEL_MDC_TAG_STALL                          = 0x66
TCC_PERF_SEL_MDC_TAG_REPLACEMENT_LINE_IN_USE_STALL  = 0x67
TCC_PERF_SEL_MDC_TAG_DESECTORIZATION_FIFO_FULL_STALL= 0x68
TCC_PERF_SEL_MDC_TAG_WAITING_FOR_INVALIDATE_COMPLETION_STALL = 0x69
```

**Lo que esto prueba y lo que no.** Prueba que hay hardware de caché de metadatos **dentro del
TCC/L2**, con sectorización propia, con contadores de hit/miss propios, y que el kernel lo llama
`MDC`. **No prueba** que `MDC` sea la caché de metadatos de DCC: el corpus **no contiene ninguna
frase que ligue `MDC` con DCC**. La unión `MDC ↔ DCC` es una **hipótesis**, con fuerza de
hipótesis (los campos de DCC viven en CB y los de MDC en TCC; una caché de metadatos que se
invalida por `WB_OR_INV_ALL_VMIDS` y tiene sectorización encaja con metadatos de superficie, pero
encajar no es identificar). Estado: `HYPOTHESIS`, no `PROVEN`. Falsificador: un documento de
programación del ASIC o una lectura que distinga `MDC_SECTOR_SIZE` con y sin `CB_COLORn_DCC_ENABLE`.

### 2.6 Políticas de reemplazo: el knob de N-INT-18 está en el ASIC

Conjunto completo, y este es de los pocos sitios donde GFX8 está **bien servido**:

| Enum | Valores | sh_mask/enum línea |
|---|---|---|
| `TCC_CACHE_POLICIES` | `LRU = 0x0`, `STREAM = 0x1` | `gfx_8_0_enum.h:6776-6779` |
| `TCP_CACHE_POLICIES` | `MISS_LRU=0`, `MISS_EVICT=1`, `HIT_LRU=2`, `HIT_EVICT=3` | `:5168-5173` |
| `TCP_CACHE_STORE_POLICIES` | `WT_LRU=0`, `WT_EVICT=1` | `:5174-5177` |
| `GATCL1RequestType` | `NORMAL=0`, `SHOOTDOWN=1`, `BYPASS=2` | `:6771-6775` |

Los registros que las consumen existen: `mmTC_CFG_L1_LOAD_POLICY0/1`,
`mmTC_CFG_L1_STORE_POLICY`, `mmTC_CFG_L2_LOAD_POLICY0/1`, `mmTC_CFG_L2_STORE_POLICY0/1`,
`mmTC_CFG_L2_ATOMIC_POLICY`, `mmTC_CFG_L1_VOLATILE`, `mmTC_CFG_L2_VOLATILE`
(`gfx_8_0_d.h:2337-2346`), y `mmTCP_BUFFER_ADDR_HASH_CNTL = 0x2b16` (`:2335`).

**Por qué esto importa para N-INT-18 (reuse distance).** `LRU` y `STREAM` son **políticas
seleccionables en el hardware**, y `STREAM` existe como valor propio. Reuse distance como barrido de
*workload* (cambiar el patrón) y como barrido de *política* (cambiar LRU↔STREAM) son **experimentos
distintos con distinto mecanismo**: el primero varía la carga, el segundo vary el estado del
hardware. Eso es el criterio de la regla del usuario (§6): el segundo sí introduce mecanismo causal
distinto, el primero no. Y programar `STREAM` es un **write de semántica no trivial** — no es un
 parámetro de workload, es un modo de caché.

### 2.7 Contadores de caché que existen como nombre

Recuento medido sobre `gfx_8_0_enum.h` (entradas `= 0x..,`): **4 891 valores de enum**. Subconjuntos
relevantes:

| Enum | nº valores | rango líneas | qué nombra |
|---|---|---|---|
| `CBPerfSel` | **396** | `125-522` | CB, **DCC**, y cachés `CM_CACHE`/`FC_CACHE`/`CC_CACHE` |
| `PerfCounter_Vals` (el enum de DB) | **257** | `779-1037` | depth buffer |
| `TCC_PERF_SEL` | 236 | `4521-4758` | **L2 (TCC)**: MC read/write, TAG, MDC |
| `SPI_PERFCNT_SEL` | 197 | `1850-2048` | shader SPI |
| `SQ_PERF_SEL` | **292** | `2283-2576` | SQ (de los cuales 105 tienen prefijo `SQC_PERF_`, líneas 2451-2555) |
| `TCP_PERFCOUNT_SELECT` | 183 | `4983-5167` | **L1 textura (TCP)** |
| `TA_PERFCOUNT_SEL` | 119 | `4805-4925` | direcciones de textura |
| `TCA_PERF_SEL` | 35 | `4759-4795` | texture channel address |
| `VGT_PERFCOUNT_SELECT` | **146** | `5457-5604` | vertex fetch |

Ejemplos exactos del lado L1 y L2:

```
gfx_8_0_enum.h:4549   TCC_PERF_SEL_MC_WRREQ_UNCACHED = 0x1b
gfx_8_0_enum.h:4558   TCC_PERF_SEL_MC_RDREQ_UNCACHED = 0x24
gfx_8_0_enum.h:4564   TCC_PERF_SEL_TAG_STALL          = 0x2a
gfx_8_0_enum.h:4991   TCP_PERF_SEL_READ_TAGCONFLICT_STALL_CYCLES  = 0x7
gfx_8_0_enum.h:5097   TCP_PERF_SEL_TCC_MISS_EVICT_READ_REQ       = 0x71
gfx_8_0_enum.h:5114   TCP_PERF_SEL_TOTAL_MISS_LRU_READ           = 0x82
gfx_8_0_enum.h:5115   TCP_PERF_SEL_TOTAL_MISS_EVICT_READ         = 0x83
gfx_8_0_enum.h:5157   TCP_PERF_SEL_GATCL1_TRANSLATION_MISS        = 0xad
gfx_8_0_enum.h:5158   TCP_PERF_SEL_GATCL1_PERMISSION_MISS         = 0xae
```

**Y lo que NO existe.** Comprobado sobre el árbol `amdgpu/` completo (excluyendo los tres ficheros
`*_enum.h` de gca/gfx): **`TCC_PERF_SEL`, `TCP_PERF_SEL`, `CB_PERF_SEL`, `DB_PERF_SEL`,
`SQC_PERF_SEL`, `TA_PERF_SEL` no tienen ni una referencia fuera de sus cabeceras de enum.** Los
nombres existen; la ruta de software que los enumere no. Eso es lo que convierte toda esta tabla en
**vocabulario, no instrumentación** (§5).

### 2.8 Cosas que se searched y NO están — la parte útil de la tabla

Estas ausencias son tan informativas como los números, porque separan `DERIVABLE` de
`NECESITA_FUENTE_EXTERNA`:

| Se buscó | Dónde, scope completo | Resultado |
|---|---|---|
| tamaño de L2 en bytes | `gca/gfx_8_0_{d,sh_mask,enum}.h` (30 523 líneas: 2 829 + 20 836 + 6 858) | `NOT_FOUND` |
| líneas de caché | ídem | `NOT_FOUND` (solo campos de 2 bits, sin valor) |
| tabla de encodings código→bytes para tamaños de caché | ídem + `gfx_v8_0.c` (7 207) | `NOT_FOUND` |
| número de bancos de L2 en unidades absolutas | ídem | `NOT_FOUND` (solo el código 3/7) |
| caché de vértices con campo de tamaño | `gfx_8_0_d.h` (2 801) | `NOT_FOUND`. Hay `mmVGT_CACHE_INVALIDATION` (`:2606`), `mmVGT_VERTEX_REUSE_BLOCK_CNTL` (`:2579`) — control, **no capacidad** |
| `VGT_CACHE_SIZE` | ídem | `NOT_FOUND` |
| L3 / MALL en GFX8 | `gmc_v8_0.c` (1 783) | `PROVEN_ABSENT`: `mall_size` no se asigna (§2.1) |
| `CACHE_LINE_SIZE` de GFX8 en `asic_reg/gc/` | `gc/` (30 ficheros) | irrelevante por §1 |
| registro de «pérdida de datos comprimidos» | `gfx_8_0_sh_mask.h` (20 789), token `LOSS\|LOST` | **38 coincidencias y ninguna es eso**: 32 son `CB_COLORn_DCC_CONTROL__LOSSY_{RGB,ALPHA}_PRECISION`, 4 son `SQ_IMG_RSRC_WORD6__LOST_{COLOR,ALPHA}_BITS`, 2 `TA_CNTL_AUX__SCOAL_DSWIZZLE_N` (falso positivo por subcadena). **Un contador de «compressed data lost» como tal: `NOT_FOUND`.** Lo que hay es el control de **precisión con la que se tira la información** (§3.2), que es la inversa: DCC aquí es **lossy por diseño** |
| control de *coalescing* de accesos | `gfx_8_0_d.h` (2 829), `gfx_8_0_sh_mask.h` (20 836), token `COALESCE\|COAL_` | `NOT_FOUND`. Los únicos aciertos son `TA_CNTL_AUX__SCOAL_DSWIZZLE_N` (`:15813-15814`), `DB_DEPTH_INFO__ADDR5_SWIZZLE_MASK` (`:4177-4178`) y `SH_STATIC_MEM_CONFIG__SWIZZLE_ENABLE` (`:15909-15910`), y los tres son **subcadena** (`SCOAL`, `SWIZZLE`), no un control de coalescing. **Un control de coalescing como tal: `NOT_FOUND`** en GFX8. Lo que sí hay es **swizzle de buffer** (`TCP_CNTL__FLAT_BUF_CACHE_SWIZZLE` `:15945-15946`, `TCP_CNTL__FLAT_BUF_HASH_ENABLE` `:15943-15944`, `SQ_BUF_RSRC_WORD1__CACHE_SWIZZLE` `:14093-14094`, `SQ_BUF_RSRC_WORD1__SWIZZLE_ENABLE` `:14095-14096`) y **tamaño de bloque** en DCC (`CB_COLORn_DCC_CONTROL__{MIN,MAX}_COMPRESSED_BLOCK_SIZE`) |
| `MMH_VM_GTT` / tipos de dirección de PTE | `drivers/gpu/drm/amd/` completo | `NOT_FOUND`. No existe el símbolo en esta versión (§4.3) |

---

## 3. La tabla DCC: no existe como tabla, y por qué eso no es una carencia

### 3.1 Búsqueda exhaustiva del «sitio natural»

El enunciado pedía buscarla en `gc/`, `mmhub/`, `dpcs/`, `athub/` y el driver. Medido, contando
ocurrencias de `DCC` **mayúsculas** (para no contar `vddc` ni `EDCC`):

| Directorio | Ocurrencias `DCC` | Ficheros | Veredicto |
|---|---|---|---|
| `asic_reg/gca/` | 834 | `gfx_8_0_d.h`(18), `gfx_8_0_sh_mask.h`(204), `gfx_8_0_enum.h`(160), `gfx_8_1_*` | **este es el sitio, y son campos de registro, no tabla** |
| `asic_reg/gc/` | 4 580 | solo `gc_9_*`…`gc_12_*` | **otra generación** (§1) |
| `asic_reg/dpcs/` | 27 400 | `dpcs_3_1_4`, `dpcs_4_2_0`, `dpcs_4_2_2`, `dpcs_4_2_3` | **colisión de nombre**: DCN Display Compression Controller, pipeline de display |
| `asic_reg/dcn/` | (mismo familia) | `dcn_1_0`…`dcn_4_2_1` | ídem, display |
| `asic_reg/gmc/` | 58 | `gmc_6_0`, `gmc_7_0`, `gmc_7_1`, `gmc_8_1`, `gmc_8_2` | **todos `EDCCDR`** (ECC-DRAM) o el literal `0xdcc` (§3.4) |
| `asic_reg/mmhub/` | **2** | `mmhub_4_1_0_sh_mask.h` | DCC de gfx9+, irrelevante para GFX8 (que no tiene MMHU) |
| `asic_reg/athub/` | **0** | — | nada |
| `asic_reg/{umc,pcie,mp,clk,rsmu,wafl}` | **0** | — | nada |
| `amdgpu/` (driver, sin display) | `compressed_block` solo en `amdgpu_display.c` (3) | — | ver abajo |
| `display/` | 191 000+ | — | pipeline de display, excluido por diseño |

**Conclusión de la búsqueda: no hay ninguna tabla de formatos comprimibles en el kernel, en ningún
directorio.** Se comprobó además, sobre el `amdgpu/` no-display, que los únicos sitios con
`compressed_block` fuera de cabeceras de registro son `amdgpu_display.c` (que es el **modifier de
tiling** DCC de `amdgpu_display.c:581` `static const struct drm_format_info dcc_formats[]`, con
`AMD_FMT_MOD_SET(DCC, …)` en `:881` — caminos de GFX9+/GFX10+/GFX12, y `gfx12_dcc` en `:1187`)
y `process_pptables_v1_0.c:278` `pVddcCACTable`, que es **Vddc** (voltaje) y no DCC.

### 3.2 Lo que GFX8 tiene: el **espacio de formatos** como producto de campos

No hay tabla. Hay un **conjunto de campos** cuya combinación *es* el formato DCC. Register-level,
en `gfx_8_0_d.h`:

```
:89-96    mmCB_COLOR0..7_DCC_CONTROL   0xa31e, 0xa32d, 0xa33c, 0xa34b, 0xa35a, 0xa369, 0xa378, 0xa387   (paso 0xf)
:145-152  mmCB_COLOR0..7_DCC_BASE      0xa325, 0xa334, 0xa343, 0xa352, 0xa361, 0xa370, 0xa37f, 0xa38e
:159      mmCB_DCC_CONFIG              0x2687
:31       mmCB_DCC_CONTROL             0xa109
:73-80    mmCB_COLOR0..7_INFO          0xa31c, 0xa32b, 0xa33a, 0xa349, 0xa358, 0xa367, 0xa376, 0xa385
```

Recuento medido: **18 registros con `DCC` en el nombre** en `gfx_8_0_d.h`; **72 campos
`CB_COLORn_DCC_CONTROL__*` = 9 nombres distintos × 8 MRT**, exactamente iguales en los ocho
(gfx_8_0_sh_mask.h:671-688 para MRT0; repetido idéntico por los otros siete). Los nueve:

| Campo | Máscara | Shift | sh_mask (MRT0) | Lectura del nombre |
|---|---|---|---|---|
| `OVERWRITE_COMBINER_DISABLE` | `0x1` | 0 | `:671-672` | bit |
| `KEY_CLEAR_ENABLE` | `0x2` | 1 | `:673-674` | bit |
| `MAX_UNCOMPRESSED_BLOCK_SIZE` | `0xc` | 2 | `:675-676` | **2 bits** |
| `MIN_COMPRESSED_BLOCK_SIZE` | `0x10` | 4 | `:677-678` | **1 bit** |
| `MAX_COMPRESSED_BLOCK_SIZE` | `0x60` | 5 | `:679-680` | **2 bits** |
| `COLOR_TRANSFORM` | `0x180` | 7 | `:681-682` | **2 bits** |
| `INDEPENDENT_64B_BLOCKS` | `0x200` | 9 | `:683-684` | bit |
| `LOSSY_RGB_PRECISION` | `0x3c00` | 10 | `:685-686` | **4 bits** |
| `LOSSY_ALPHA_PRECISION` | `0x3c00`→`0x3c000` | 14 | `:687-688` | **4 bits** |

`COLOR_TRANSFORM` tiene enumeración explícita y **el enum se llama `ColorTransform` con valores
`DCC_*`** (`gfx_8_0_enum.h:6411-6416`):

```
DCC_CT_AUTO              = 0x0
DCC_CT_NONE              = 0x1
ABGR_TO_A_BG_G_RB        = 0x2
BGRA_TO_BG_G_RB_A        = 0x3
```

Y el formato de superficie vive en `CB_COLORn_INFO__FORMAT`, **5 bits** (`sh_mask:289-290`), alimentado
por el enum `SurfaceFormat` (64 valores, `enum.h:6513-6578`) y `ColorFormat` (24 valores, `enum.h:6487-6512`) — no por el `SurfaceFormat` de 5 bits
que usa CB, sino por el código de 5 bits que selecciona dentro de él. Junto a él,
`CB_COLORn_INFO__DCC_ENABLE` es **1 bit** (`sh_mask:319-320`) y `CB_COLORn_INFO__COMPRESSION` es
**1 bit** distinto (`sh_mask:299-300`), junto a `FMASK_COMPRESSION_DISABLE` / `FMASK_COMPRESS_1FRAG_ONLY`
(`:315-318`) que son de FMASK, no de DCC.

`CB_DCC_CONFIG` (`sh_mask:1033-1046`) añade los dos campos que gobiernan **cuánta caché de DCC hay**:
`DCC_CACHE_EVICT_POINT` (4 bits) y `DCC_CACHE_NUM_TAGS` (4 bits). `CB_DCC_CONTROL`
(`sh_mask:35-40`) tiene `OVERWRITE_COMBINER_WATERMARK` (3 bits).

**El tamaño del espacio.** Naivo: 32 códigos de formato × 4 transforms × 16 precisiones RGB × 16
precisiones alpha × 4 min × 4 max × 4 max-unc × 2 (64B) = **millones**. La tabla que la colapsaría
—qué combinaciones son válidas y con qué `MIN/MAX_COMPRESSED_BLOCK_SIZE`— es precisamente lo que
no está. Y **esa es la razón por la que no puede estar**: la tabla no es un dato, es el resultado
de **preguntarle al silicio**. Un formato no comprimido no es una fila ausente de una tabla: es un
**resultado** — el hardware acepta la combinación y stores `UNCOMPRESSED` en la clave (ver §3.3).
Una tabla «de qué formatos son comprimibles» destruiría justamente la información que la idea del
usuario pide medir.

**Falsificador.** Si amdgpu tuviera (o hubiera tenido) una DCC table para GFX8, aparecería como un
array de constantes con literales de formato. Scope comprobado: `amdgpu/` no-display completo, token
`dcc.*(table|format)|(table|format).*dcc` y `compressed_block` — nada. No la hay.

### 3.3 El dato que respalda la revisión adversarial del usuario: DCC no es ON/OFF

Aquí el nodo tiene el resultado más fuerte, y **no es una intuición: es la taxonomía del propio
hardware**, en `gfx_8_0_enum.h`, en el enum `CBPerfSel`.

**(a) Un cubo `UNCOMPRESSED` que es un valor de clave, no un estado del sistema.**
`gfx_8_0_enum.h:505-521`:

```
CB_PERF_SEL_CC_DCC_KEY_VALUE__UNCOMPRESSED = 0x17b
CB_PERF_SEL_CC_DCC_COMPRESS_RATIO_2TO1      = 0x17c
CB_PERF_SEL_CC_DCC_COMPRESS_RATIO_4TO1      = 0x17d
CB_PERF_SEL_CC_DCC_COMPRESS_RATIO_4TO2      = 0x17e
CB_PERF_SEL_CC_DCC_COMPRESS_RATIO_4TO3      = 0x17f
CB_PERF_SEL_CC_DCC_COMPRESS_RATIO_6TO1      = 0x180
…
CB_PERF_SEL_CC_DCC_COMPRESS_RATIO_8TO7      = 0x18b
```

Son **17 cubos contiguos**: `UNCOMPRESSED` y 16 razones de compresión (`2TO1`…`8TO7`). Los 113
valores previos (`0x10a`–`0x17a`) son `CB_PERF_SEL_CC_DCC_KEY_VALUE__*`, es decir **la clave de
bloque** — combinaciones de `1BLOCK_2TO1`, `1BLOCK_2TO2`, `2BLOCKS_4TO1`…, que es la codificación
`INDEPENDENT_64B_BLOCKS` + `MIN/MAX_COMPRESSED_BLOCK_SIZE` de §3.2 hecha enum.

**Lo que esto prueba:** la instrumentación del propio ASIC **clasifica cada bloque comprimido por su
ratio conseguido**, y `UNCOMPRESSED` es uno más de esos cubos. DCC, en GFX8, es una
**magnitud con valores discretos**, y el caso «no comprimido» es un valor de esa magnitud. La revisión
adversarial del usuario —*«DCC como reducción de tráfico, no ON/OFF»*— está **corroborada por la
estructura de nombres del hardware**, no sólo por intuición.

**(b) El contador que mide el tráfico ahorrado existe con ese nombre.**
`gfx_8_0_enum.h:237`:

```
CB_PERF_SEL_CC_CACHE_READS_SAVED_DUE_TO_DCC = 0x6f
```

**(c) La caché de DCC tiene hit/miss propios y peticiones a MC propias.**
`gfx_8_0_enum.h:367-391`: `FC_DCC_CACHE_HIT`(0xf1), `FC_DCC_CACHE_TAG_MISS`(0xf2),
`FC_DCC_CACHE_SECTOR_MISS`(0xf3), 10× `_STALL`, `FC_DCC_CACHE_FLUSH`(0xfc), `TAGS_FLUSHED`,
`SECTORS_FLUSHED`, `DIRTY_SECTORS_FLUSHED`; más `CC_DCC_BEYOND_TILE_SPLIT`(0x100),
`FC_MC_DCC_WRITE_REQUEST`(0x101), `FC_MC_DCC_READ_REQUEST`(0x103),
`CC_DCC_RDREQ_STALL`(0x105), `CC_DCC_DECOMPRESS_TIDS_IN/OUT`(0x106/0x107),
`CC_DCC_COMPRESS_TIDS_IN/OUT`(0x108/0x109).

**Y los contadores de tráfico hacia memoria que son la otra mitad de N-INT-19**:
`TCC_PERF_SEL_MC_RDREQ`/`MC_WRREQ` y sus variantes `…_UNCACHED` (`enum.h:4549`, `:4558`) — el
numerador y el denominador de «tráfico reducido».

**Advertencia de honestidad epistémica, y es importante:** todo lo anterior prueba que **los
nombres existen**. No prueba que los contadores **cuenten** lo que su nombre dice, ni que se puedan
leer. §5 lo separa. Lo que sí es `PROVEN` es que la taxonomía de ratios está en el enumerado del
ASIC — que es una representación, no una medición.

### 3.4 Colisiones de nombre — tres, medidas, y por qué hay que registrarlas

Un buscador de `dcc` sin distinguir mayúsculas produce **falsos positivos sin cualificar**:

| Falso positivo | Dónde | Qué es de verdad |
|---|---|---|
| `MC_TRAIN_EDCCDR_R_D0/D1` | `asic_reg/gmc/gmc_8_1_d.h:772-773` | **ECC-DRAM** (training de memoria con ECC) |
| `0xdcc` | `asic_reg/gmc/gmc_8_1_d.h:1555` `mmMC_ARB_HARSH_BWPERIOD1_RD` | el **literal hexadecimal** |
| `pVddcCACTable` | `pm/powerplay/hwmgr/process_pptables_v1_0.c:278` | **Vddc** = voltaje |
| `dccg` (38 ficheros) | `display/dc/dccg/` | **Display Core Clock Generator** |
| DCC de `dpcs`/`dcn` (27 400) | `asic_reg/dpcs/`, `asic_reg/dcn/` | Display Compression Controller |
| `AMDGPU_GEM_CREATE_GFX12_DCC` | `amdgpu/amdgpu_vram_mgr.c:453-579` | **solo GFX12** |
| DCC de modifier de tiling | `amdgpu/amdgpu_display.c:581-1258` | rutas de display, ≥GFX9 |

Medido: en `asic_reg/gmc/gmc_8_1_sh_mask.h` hay **16 ocurrencias de `dcc` sin distinguir
mayúsculas y las 16 son `EDCC`** (contiguas con la `E` de ECC-DRAM). **Cero son Delta Color
Compression.** Quien cuente "DCC en gmc_8_1" está contando ECC-DRAM.

### 3.5 DCC después de un clear state

`amdgpu/clearstate_vi.h` pone a cero `CB_DCC_CONTROL` (`:292`) y, para los ocho MRT,
`CB_COLORn_DCC_CONTROL` y `CB_COLORn_DCC_BASE` (`:817`, `:824`, `:832`, `:839`, `:847`, `:854`,
`:862`, `:869`, `:877`, `:884`, `:892`, `:899`, `:907`, `:914`, `:922`). Es decir: **un clear state
deja DCC apagado y sin base.** Estado `PROVEN`.

Observación con discriminante: `clearstate_vi.h` (945 líneas) **no contiene** `TCC_CTRL`,
`TCP_CNTL`, `SQC_CONFIG`, `GB_ADDR_CONFIG` ni ningún otro campo de capacidad de caché. Comprobado
con filtered scan de las 945 líneas. Es decir: **la geometría de caché de esta ASIC no se sabe por el
clear state**, solo por la golden sequence (§2.3) y por el firmware (§2.2).

---

## 4. Topología VRAM/GART y el spill

### 4.1 Números de esta tarjeta, y de dónde sale cada uno

| Dato | Valor | Procedencia | Clase |
|---|---|---|---|
| `mc_mask` | `0xffffffffffULL` (40 bits) | `amdgpu/gmc_v8_0.c:1133` literal por ASIC | `PROVEN` (que el valor es ese) |
| `AMDGPU_GMC_HOLE_START` | bit 47 | `amdgpu/amdgpu_gmc.h:36`, invocado desde `gmc_v8_0.c:1127` | `PROVEN` |
| `amdgpu_vm_adjust_size` | `(adev, 64, 9, 1, 40)` | `gmc_v8_0.c:1127` — el 4.º argumento (1) es el `max_level` que decide LOW/HIGH | `PROVEN` |
| `gart_size` | **256 MiB** | `gmc_v8_0.c:592-595` (`case CHIP_POLARIS12:` → `256ULL << 20`), + `smu_prv_buffer_size` en `:608` | `PROVEN` |
| `table_size` | `num_gpu_pages * 8` = 524 288 B = **512 KiB** | `gmc_v8_0.c:960`; `num_gpu_pages = gart_size / 4096` en `amdgpu_gart.c:533`; `AMDGPU_GPU_PAGE_SIZE 4096` en `amdgpu_gart.h:35` | `DERIVED` |
| la tabla vive en **VRAM** | `AMDGPU_GEM_DOMAIN_VRAM` | `amdgpu_gart.c:270-272` | `PROVEN` |
| tipo de GART | **"PCIE GART"** | la cadena literal del log: `gmc_v8_0.c:942` `"PCIE GART of %uM enabled (table at 0x%016llX)."` | `PROVEN` |
| AGP aperture | **deshabilitada** | `gmc_v8_0.c:420` llama `amdgpu_gmc_set_agp_default`, que fija `agp_start=0xffffffffffff`, `agp_end=0`, `agp_size=0` (`amdgpu_gmc.c:392-394`). **No hay ninguna llamada a `amdgpu_gmc_agp_location()` en `gmc_v8_0.c`** (scope 1 783 líneas) | `PROVEN` |
| colocación del GART | `AMDGPU_GART_PLACEMENT_BEST_FIT` | `gmc_v8_0.c:422` | `PROVEN` |
| `fb_base` | `RREG32(mmMC_VM_FB_LOCATION) & 0xFFFF`, luego `<<= 24` | `gmc_v8_0.c:416-418` → múltiplo de 16 MiB siempre | `PROVEN` |
| `gtt_size` del driver | `ttm_tt_pages_limit() << PAGE_SHIFT` | `amdgpu/amdgpu_ttm.c:2140` | `PROVEN` (que sale de ahí, no el valor) |

### 4.2 La frontera, calculada con la aritmética del propio corpus

`amdgpu_gmc_gart_location()` (`amdgpu_gmc.c:294-336`) es aritmética pura con nueve pasos. Aplicada
con los datos de esta tarjeta (`fb_base = 0x000000F400000000` y `vram = 2048 MiB`, ambos ya
declarados en `04-IMPLEMENTACION/rx550-driver/rx550_gart_geom.h:180-181`):

```
mc_mask                     = 0x000000FFFFFFFFFF            (gmc_v8_0.c:1133)
max_mc_address = min(mc_mask, HOLE_START-1) = 0xFFFFFFFFFF    (amdgpu_gmc.c:299)
fb_start       = 0x000000F400000000                          (gmc_v8_0.c:416-418)
fb_end         = 0x000000F47FFFFFFF   = fb_start + 2 GiB - 1
ALIGN(fb_end+1, 4GiB) = 0x000000F480000000                    (amdgpu_gmc.c:305)
size_bf = fb_start                       = 976.00 GiB
size_af = 0x10000000000 - 0xF480000000   = 0xB00000000 = 44.00 GiB
gart_size = 0x10000000 = 256 MiB                              (gmc_v8_0.c:595)

BEST_FIT (amdgpu_gmc.c:322-329):
   ¿(size_bf >= gart_size && size_bf < size_af)?  976 GiB < 44 GiB  -> NO
   ¿size_af < gart_size?                                            -> NO
   -> else: gart_start = max_mc_address - gart_size + 1 = 0x000000FFF0000000
   -> &~4GiB (línea :332)  = 0x000000FF00000000
gart_end = 0x000000FF0FFFFFFF
```

Resultado:

| Ventana | Rango GPU | Tamaño |
|---|---|---|
| **VRAM (FB)** | `0x000000F400000000` … `0x000000F47FFFFFFF` | **2 GiB** |
| hueco | `0x000000F480000000` … `0x000000FEFFFFFFFF` | 42 GiB |
| **GART (GTT)** | `0x000000FF00000000` … `0x000000FF0FFFFFFF` | **256 MiB** |

**Corroboración independiente:** el nodo principal tiene medido en el log del kernel de esta máquina
`"GART: 256M 0x000000FF00000000"` (registrado en `rx550_gart_table.h:30`). Mi aritmética produce
exactamente `0x000000FF00000000`. `CORROBORATED` por dos vías (aritmética del corpus + log de
runtime), y la segunda es una cita de otro nodo, así que se marca como tal.

**Consecuencia de topología, y es la que importa para `R-NEW-45`:**
VRAM y GTT están **separados por 42 GiB de hueco**, no adyacentes. La frontera es **un solo
umbral de dirección** (`gart_start`), porque — ver §4.3 — el PTE de GFX8 no lleva campo de tipo.

### 4.3 Cómo distingue esta ASIC VRAM de GTT: por **rango**, no por **campo**

Medido sobre `amdgpu/amdgpu_vm.h:57-133`. Los flags de PTE de GFX8 son:

```
AMDGPU_PTE_VALID     (1ULL<<0)     :57
AMDGPU_PTE_SYSTEM    (1ULL<<1)     :58     <-- el discriminador
AMDGPU_PTE_SNOOPED   (1ULL<<2)     :59
AMDGPU_PTE_TMZ       (1ULL<<3)     :62
AMDGPU_PTE_EXECUTABLE(1ULL<<4)     :65
AMDGPU_PTE_READABLE  (1ULL<<5)     :67
AMDGPU_PTE_WRITEABLE (1ULL<<6)     :68
AMDGPU_PTE_FRAG(x)   ((x&0x1f)<<7) :70
AMDGPU_PTE_PRT       (1ULL<<51)    :73
AMDGPU_PTE_LOG       (1ULL<<55)    :78
AMDGPU_PTE_TF        (1ULL<<56)    :81
AMDGPU_PTE_NOALLOC   (1ULL<<58)    :84
AMDGPU_PTE_IS_PTE    (1ULL<<63)    :133
```

**Y el campo de tipo de memoria: existe para VG10, NV10 y GFX12, y NO para GFX8.**

```
AMDGPU_PTE_MTYPE_VG10_SHIFT(mtype)  (mtype << 57)   amdgpu_vm.h:97
AMDGPU_PTE_MTYPE_NV10_SHIFT(mtype)  (mtype << 48)   amdgpu_vm.h:114
AMDGPU_PTE_MTYPE_GFX12_SHIFT(mtype) (mtype << 54)   amdgpu_vm.h:125
AMDGPU_PTE_MTYPE_NC / _CC           0 / 2           amdgpu_vm.h:103-104
```

El enum `MTYPE` (`gfx_8_0_enum.h:6780-6785`: `MTYPE_NC_NV=0, MTYPE_NC=1, MTYPE_CC=2, MTYPE_UC=3`)
está en la cabecera de GFX8 pero **nadie lo escribe en un PTE de GFX8**: los tres `AMDGPU_PTE_MTYPE_*`
están condicionados a versión por ASIC, y GFX8 no tiene ninguno.

**Por tanto, en esta ASIC la distinción VRAM/GTT es:**
1. **el valor de la dirección GPU** (por debajo de `gart_start` → VRAM; dentro de
   `[gart_start, gart_end]` → GART), y
2. **el bit 1 del PTE** (`AMDGPU_PTE_SYSTEM`), que es una *pista*, no un tipo.

La cadena causal, con cita en cada eslabón:

```
bo->tbo.resource->mem_type == TTM_PL_TT
  -> pages_addr = bo->tbo.ttm->dma_address          amdgpu_vm.c:1330-1332
  -> flags = amdgpu_ttm_tt_pte_flags(...)            amdgpu_vm.c:1344
       -> | adev->gart.gart_pte_flags               amdgpu_ttm.c:1449
          (= AMDGPU_PTE_EXECUTABLE = 1<<4; gmc_v8_0.c:961)   <-- NO lleva SYSTEM
       -> | AMDGPU_PTE_READABLE, y WRITEABLE si no es RO       amdgpu_ttm.c:1450-1453
  -> amdgpu_vm_update_range(..., pages_addr, ...)    amdgpu_vm.c:1388-1392
```

**Falsificador.** Si el PTE de GFX8 tuviera un campo de tipo en otro bit no listado aquí, el
razonamiento de §4.3 caería. Scope: `amdgpu_vm.h` completo (2 000+ líneas) más `gfx_8_0_sh_mask.h`.
`AMDGPU_PTE_MTYPE_GFX8` no existe. Confirmado.

### 4.4 El **spill**: dónde hay discontinuidad y dónde no

Aquí es donde el nodo puede **refutar** la predicción del usuario, y lo hace con el argumento.

Hay **dos** mecanismos distintos, y se comportan de forma distinta:

**(A) La escalera de working set (VRAM → GTT por presión).** Mecanismo: TTM ADM, no la GPU.
`amdgpu_ttm.c:1467-1480` `amdgpu_ttm_bo_eviction_valuable()` decide qué desalojar; TTM desaloja y
reintenta. Es **gradual por construcción**: la fracción de datos en GTT crece con el working set,
y el tiempo crece con ella. El corpus **no contiene ninguna rama que falle** en esta ruta.

> **Refutación parcial de `R-NEW-46`.** La revisión del usuario ya dice *«cliff es predicción
> fuerte; reformular a discontinuidades por spilling»* (`IDEA-REGISTER.md:148`). El análisis
> estático **va un paso más allá y dice cuál de las dos cosas es**: para la escalera de working set
> (VRAM↔GTT por presión de TTM), el código sugiere **degradación gradual**, no acantilado. La
> discontinuidad de `R-NEW-46`, si existe, **no está en el spill**. **Falsificador:** un barrido de
> working set que muestre un salto de segundo orden en el punto en que `gtt_size` supera el
> `vm_size` útil. Eso sería un confounder de TTM (eviction, no migrate-in-place), no del hardware de
> memoria, y se distinguiría por un observable indirecto: los contadores de
> `vram_pin_size`/`gart_pin_size` (que sí existen, §4.5) y el page-fault (que **no** se puede leer).

**(B) La ventana GART.** Mecanismo: asignación de páginas del GART, **con fallo duro**.
`amdgpu_ttm.c:988-998` (`amdgpu_ttm_alloc_gart`):

```c
placement.num_placement = 1;
placements.fpfn = 0;
placements.lpfn = adev->gmc.gart_size >> PAGE_SHIFT;   /* :992  = 65536 */
placements.mem_type = TTM_PL_TT;
r = ttm_bo_mem_space(bo, &placement, &tmp, &ctx);       /* :996 */
if (unlikely(r))
        return r;                                       /* :997-998  -> FALLO, no degradación */
```

Cuando la ventana de 256 MiB (65 536 páginas) se agota, `ttm_bo_mem_space` devuelve error y
**el pin falla**. No hay ruta de «más lento»: hay ruta de «no». Y el llamador propaga:
`amdgpu_object.c:279-285` `amdgpu_bo_pin(bo, AMDGPU_GEM_DOMAIN_GTT)` → `amdgpu_ttm_alloc_gart`.

**Éste sí es un acantilado, y es discreto.** El sitio exacto de la discontinuidad es
**`gtt_size` residencial > 256 MiB** (más lo que el resto del sistema tenga ya residencial en GTT),
no «el working set supera la VRAM».

> **Corroboración parcial de `R-NEW-46`, en otro sitio.** El acantilado que el usuario predice
> **existe**, pero la variable que lo dispara no es el working set: es **la ocupación de la ventana
> GART de 256 MiB**. `R-NEW-46` debe reformularse a: *«discontinuidad por agotamiento de la ventana
> GART (256 MiB), no por spill gradual de VRAM a GTT»*. Eso es `R-NEW-46` con el mecanismo
> correcto, y la distinción es la diferencia entre un experimento que midió presión de VRAM y uno
> que habría medido una condición de fallo.

**Las dos ideas quedan separadas por tener mecanismo causal distinto**, que es el criterio de la
regla del usuario (§6). `R-NEW-41` (escalera de working set) y `R-NEW-46` reformulado (agotamiento
de GART) **no son la misma idea**, contra lo que sugiere `IDEA-REGISTER.md:148` (`R-NEW-46` =
`VARIANT_OF(H6)`).

### 4.5 Qué se puede observar de la residencia (para `R-NEW-43`)

`R-NEW-43` («churn de residencia») está marcada `BUENA — requiere observar residency`
(`IDEA-REGISTER.md:145`). Medido: **la observabilidad de residencia es mejor de lo que el registro
supone, y es de nivel 1 (lectura de ioctl), no de nivel 4.**

| Cuantidad | Dónde se mantiene | Cómo se lee |
|---|---|---|
| `gtt_size` **menos** lo que la GART ya tiene pinneado | `amdgpu_kms.c:833-834`: `vram_gtt.gtt_size = ttm_manager_type(...,TTM_PL_TT)->size; vram_gtt.gtt_size -= atomic64_read(&adev->gart_pin_size);` | ioctl `AMDGPU_INFO_VRAM_GTT` |
| `vram_size` menos pinneado | `amdgpu_kms.c:826-828` (idem ioctl) | idem |
| `vram_cpu_accessible_size` | `amdgpu_kms.c:829-832` | idem |
| **`gart_pin_size`** | `atomic64_add(amdgpu_bo_size(bo), &adev->gart_pin_size)` en `amdgpu_object.c:993`; `_sub` en `:1026` |derivado del ioctl anterior |
| `vram_pin_size`, `visible_pin_size` | `amdgpu_object.c:989-991`, `:1022-1024` | idem |
| uso real de VRAM | `amdgpu_kms.c:802-805` `AMDGPU_INFO_VRAM_USAGE` | ioctl |
| uso real de GTT | `amdgpu_kms.c:809-811` `AMDGPU_INFO_GTT_USAGE` | ioctl |
| pages faults a VRAM desde CPU | `amdgpu_kms.c:800` `num_vram_cpu_page_faults` | ioctl |

**Consecuencia:** `R-NEW-43` y `R-NEW-45` dejan de estar bloqueadas por «observar residencia». Hay
**siete** campos de residencia legibles por ioctl, incluido `gart_pin_size`, que es exactamente la
magnitud que se acerca al acantilado de §4.4(B). Esto **no** mide bytes/s (el padre H6 lo prohíbe:
`HYPOTHESIS-REGISTER.md:138`) ni residency por objeto, pero sí da la serie de presión que un
working-set ladder necesita para no ser una regresión ciega.

### 4.6 El estado de la tabla GART del driver propio (recibido, no rederivado)

Recibido del nodo principal, registrado como `MEDIDO`, **no modificado**:

| Elemento | Valor | Dónde |
|---|---|---|
| entradas de la tabla | 8 bytes (`uint64_t`), **no** 4 | `rx550_gart_table.h:96` `RX550_GART_TABLA_ENTRADA_BYTES 8u`, justificado con `gmc_v8_0.c:960` |
| nº de entradas | `gart_size / 4096` = 65 536 | `rx550_gart_table.h:109`; cadena en `:22-23` |
| tamaño | 65 536 × 8 = 512 KiB | `rx550_gart_table.h:110` |
| valor de arranque | `RX550_GART_PTE_EXECUTABLE = 0x10` por **palabra** | `rx550_gart_table.h:106`, con la discrepancia frente a `memset_io` documentada en `:139-183` |
| geometría de PTE/PDE | `root_entries = ceil(max_pfn / (1<<block_size))`; `coverage = root_entries * (1<<block_size) << 12` | refutada y corregida en `e417d64`. Consistente con lo medido aquí: `coverage >> 12` cuenta **páginas de GPU**, y 65 536 páginas × 4 KiB = **256 MiB**, que es exactamente `gart_size`. O sea que el `<< 12` final es una **conversión de unidades**, no un redondeo. El valor concreto de `block_size` en el driver propio queda `NOT_DETERMINED` (no he leído `rx550_vmid1_pgt.h`, fuera del alcance de este nodo) |
| `RX550_GART_START` | `0` | `rx550_spaces.h:56`, bajo el epígrafe **`DESIGN_CHOICE`** (`:55`) |
| por qué es decisión y no hecho | el corpus usa `BEST_FIT` (`gmc_v8_0.c:422`) y en esta tarjeta elige **la rama alta** ⇒ `0xFF00000000`, no 0 | `rx550_gart_geom.h:103-108` lo dice; mi §4.2 lo reproduce |

**Dos observaciones de este nodo sobre ese estado, que son nuevas y no tocan los ficheros:**

1. **`RX550_GART_START = 0` es incompatible con la topología medida en §4.2.** La geometría real
   coloca el GART en `0xFF00000000`, con la VRAM en `0xF400000000`–`0xF47FFFFFFF` y **42 GiB de hueco
   entre medias**. Con `GART_START = 0` el GART se solapa con… nada que exista, porque la VRAM no
   está en 0 — pero entonces `GART_ADDRESS` pasa a ser **una dirección de sistema** por identidad
   (`rx550_spaces.h:95-100`, `:116-120`), y la identidad `GART == PA` **sólo es cierta con esa
   elección** (el propio fichero lo dice en `:70-71`). El diseño es coherente consigo mismo; lo que
   no es es una descripción de la máquina. Sigue siendo `DESIGN_CHOICE` y el nodo no lo modifica.
2. **La corrección de `e417d64` y la §4.2 encajan**, pero por un motivo que conviene tener explícito:
   `coverage >> 12 = root_entries * (1<<block_size)` cuenta **páginas de GPU**; 65 536 páginas son
   256 MiB de *cobertura de PTE*, no 2 GiB. Si el `block_size` elegido produce
   `root_entries * 2^block_size = 65 536`, la cobertura es exactamente la de la GART y el
   `<< 12` es una conversión de unidades, no un problema de exponente. `NOT_DETERMINED` el valor concreto
   de `block_size` en el driver propio: no he leído `rx550_vmid1_pgt.h` y queda fuera del alcance
   declarado de este nodo.

---

## 5. Qué es medible aquí y qué no, con números

### 5.1 Contable estáticamente en el fuente — **sin GPU, sin riesgo**

| Cantidad | Valor medido |
|---|---|
| `#define` en `gfx_8_0_d.h` | **2 801** (de ellos `mm*` de offset: **2 633**) |
| `#define` en `gfx_8_0_sh_mask.h` | **20 789** = **10 394** `_MASK` + **10 394** `__SHIFT` |
| valores de enum en `gfx_8_0_enum.h` | **4 891** en 125 `typedef enum` |
| registros con `DCC` en el nombre (`gfx_8_0_d.h`) | **18** |
| campos `CB_COLORn_DCC_CONTROL__*` | **72** = **9** nombres × **8** MRT, idénticos en los 8 |
| valores del enum `CBPerfSel` | **396** (líneas 125-522) |
| cubos de ratio de DCC | **17** (`UNCOMPRESSED` + 16) |
| valores `TCC_PERF_SEL` / `TCP_PERFCOUNT_SELECT` | **236** / **183** |
| entradas de la golden sequence de POLARIS12 | **16** en `golden_settings_polaris11_a11`, **6** en `polaris11_golden_common_all` |
| valores decodificados de `TCC_CTRL` y `TCP_ADDR_CONFIG` para esta ASIC | **10** y **4** campos (§2.3) |
| aritmética de colocación del GART | **9 pasos**, resultado `0xFF00000000`, corroborado con el log |
| ventanas de memoria y sus tamaños | 3 (VRAM 2 GiB, hueco 42 GiB, GART 256 MiB) |
| campos de PTE de GFX8 | **13** (`amdgpu_vm.h:57-133`), de los cuales `MTYPE` **0** |
| campos de residencia legibles por ioctl | **7** (§4.5) |
| tablas de caché por ASIC para POLARIS12 | **1**, y es la de Carrizo, con `TODO: Add L2` |
| tablas DCC de formatos comprimibles | **0** |

### 5.2 Necesita un contador de hardware que **no existe en esta vía**

Los cuatro que harían falta para cerrar `M-01` y `F-02`/`N-INT-19`, y su estado exacto:

| Lo que se necesita | El nombre existe | La ruta de software existe |
|---|---|---|
| L2 hit/miss/sector-miss | sí: `TCC_PERF_SEL_MDC_*` (7, `enum.h:4621-4627`), `TCP_PERF_SEL_TOTAL_MISS_{LRU,EVICT}_{READ,WRITE}` (`:5114-5119`) | **NO** |
| tráfico a MC (numerador/denominador de DCC) | sí: `TCC_PERF_SEL_MC_RDREQ/WRREQ` + `…_UNCACHED` (`:4549`,`:4558`) | **NO** |
| **lecturas ahorradas por DCC** | sí: `CB_PERF_SEL_CC_CACHE_READS_SAVED_DUE_TO_DCC = 0x6f` (`:237`) | **NO** |
| **histograma de ratio de compresión** | sí: **17** cubos `CC_DCC_KEY_VALUE__UNCOMPRESSED`…`CC_DCC_COMPRESS_RATIO_8TO7` (`:505-521`) | **NO** |
| caché de DCC hit/miss | sí: `FC_DCC_CACHE_HIT`…`DIRTY_SECTORS_FLUSHED` (`:367-381`) | **NO** |
| bytes/s reales de PCIe | — | **NO**. Y `HYPOTHESIS-REGISTER.md:136` lo marca `UNKNOWN`, `:138` prohíbe afirmarlo |

Comprobación del «NO», y su scope: sobre `amdgpu/` completo (excluyendo `gfx_8_0_enum.h`,
`gfx_8_1_enum.h`, `gfx_7_2_enum.h`), los tokens `TCC_PERF_SEL`, `TCP_PERF_SEL`, `CB_PERF_SEL`,
`DB_PERF_SEL`, `SQC_PERF_SEL`, `TA_PERF_SEL` tienen **cero** referencias; y sobre `gfx_v8_0.c`,
`soc15.c`, `soc21.c`, `soc24.c` los tokens `sq_cmds`, `gfx8_`, `grnm`, `PERFCTLCNT`,
`amdgpu_perf` dan `False` en los cuatro. **Los nombres existen; la enumeración por software no.**

> **Consecuencia sobre `N-INT-19` y `F-02`, y es la más dura del nodo.** La forma del experimento que
> el usuario quiere —DCC como reducción de tráfico— **es exactamente la forma de los contadores que
> el ASIC declara y que nadie puede leer**. Hay 17 cubos de ratio y un contador de lecturas
> ahorradas, y **ninguno** tiene camino desde el kernel de esta máquina. Eso no hace la idea mala:
> hace que su **observable named** esté bloqueado, y el bloqueo es de la vía de lectura, no del
> experimento. Lo que SÍ es ejecutable sin contadores es el par `(formato, `DCC_ENABLE`)` →
> **tiempo de frame medido**, que es un observable de nivel 1 y no necesita instrumentación — pero
> mezcla «tráfico» con «capacidad» y no separa los dos. La separación necesita el contador.

### 5.3 Necesita autorización de hardware (nivel 4) — bloqueada en este nodo

Ninguna de estas se ha hecho ni se propone hacer aquí. Se listan para que la frontera sea visible.

| Operación | Registros | Por qué es nivel ≥4 |
|---|---|---|
| cambiar `TCC_CTRL.MDC_SIZE` / `MDC_SECTOR_SIZE` | `sh_mask:15541-15544` | semántica de hardware no verificada; escribe en la L2 mientras el motor corre |
| cambiar la política de caché LRU↔STREAM | `TC_CFG_L2_*_POLICY` (`gfx_8_0_d.h:2340-2344`) | modo de caché, no parámetro de workload |
| `FORCE_HIT` / `FORCE_MISS` de la L1 de textura | `TCP_CNTL__FORCE_HIT` (`:15937`), `__FORCE_MISS` (`:15939`) | nombres que describen sin ambigüedad lo peligroso que suenan |
| `SQC_CONFIG__FORCE_ALWAYS_MISS` / `FORCE_IN_ORDER` | `:13459-13462` | el nombre literal del campo no deja margen de interpretación |
| `GATCL1_TYPE_SHOOTDOWN` manual | `enum.h:6772` | invalidación global de TLB |
| `CB_COLORn_DCC_CONTROL` / `_DCC_BASE` desde CPU | `d.h:89-96`, `:145-152` | superficie + metadatos; tocarlo sin driver de render es `WRITE_SEMANTICS_UNKNOWN` |
| Anything en `mmTCC_*` con el motor activo | `d.h:2245-2265` | es la L2 |

Ninguna se ha ejecutado. `GPU=INTACTA`.

---

## 6. La regla del usuario aplicada: qué ideas se funden y cuál no

La regla: *«no crear una IDEA nueva cuando solo cambia el parámetro experimental, salvo que
introduzca mecanismo causal distinto»*.

### 6.1 Se funden: **cinco** IDs que sólo cambian el parámetro

| ID | Own wording | Mecanismo | Por qué se funde |
|---|---|---|---|
| `R-NEW-07` | barrido de patrón de acceso | L2/L1 hit-rate | padre |
| `N-INT-09` | localidad temporal vs espacial | **idéntico**: el barrido de patrón ya barre temporal vs espacial, porque el patrón *es* la localidad | no introduce nada |
| `R-NEW-41` | escalera de working set | **idéntico**: el eje es la cantidad, el mecanismo es el mismo barrido de L2 hit-rate a capacidad creciente | ya marcado `VARIANT_OF(H6)` (`IDEA-REGISTER.md:143`) |
| `N-INT-11` | working-set × localidad | producto de los dos anteriores | producto, no mecanismo |
| `N-INT-12` | working-set × wave occupancy | producto, y el segundo factor es **microarquitectura** | → nodo `MICROARCH-GFX8` |

**El argumento, en una frase:** los cuatro son el par `(cantidad de datos, patrón de acceso)`
barrido en una rejilla. `N-INT-09` cambia el valor del eje de patrones; `R-NEW-41` y `N-INT-11`
cambian el valor del eje de cantidad. Ninguno añade una variable física nueva. **Una sola idea:
«curva de hit-rate L2 contra (working set × patrón)»**, con los dos ejes como parámetros. Eso es
`REFACTORIZAR`, no descartar: el contenido no se pierde, se declara.

**Y hay un cuarto miembro que el registro ya marked `NUEVA` sin razón:** `R-NEW-09` «umbral de
tamaño de textura» y `R-NEW-10` «umbral de cantidad de texturas» están ya marcados
`DUPLICATE`/`REDUNDANTE` (`:81-82`) y `CTD-05` los declara duplicados de `H6`/`M-01`
(`RESEARCH-LINES.md:335`). Correcto, y por el mismo argumento.

### 6.2 Se funden: `N-INT-16` y `N-INT-17`, y `N-INT-18` **NO**

| ID | Mecanismo | Estado |
|---|---|---|
| `N-INT-16` cache-capacity sweep | barrido del hit-rate L2 al cruzar la capacidad | **el mismo** que §6.1: es `R-NEW-41` con el eje rename «capacidad de caché» en vez de «working set». La capacidad de caché **es** el working set, visto desde el otro lado |
| `N-INT-17` cache-thrashing controlado | forzar el despliegue de la capacidad | **mismo mecanismo**, es el extremo del barrido de `N-INT-16` |
| **`N-INT-18` cache reuse distance** | **otro** | **NO se funde.** El barrido de capacidad sólo produce un *punto* de codo. La reuse distance es un **segundo observable**: qué separación working-set↔LRU produce el miss. Y el ASIC **tiene el knob** (`TCC_CACHE_POLICY_LRU`/`STREAM`, `enum.h:6776-6779`), así que hay **dos** variables con dos mecanismos: la carga y la política. Eso es lo que la regla llama «mecanismo causal distinto» |

**Pero `N-INT-18` tiene una dependencia que este nodo acaba de encontrar y que laidea no declaraba.**
Para barrer reuse distance hace falta conocer la **capacidad y la línea de la L2**, y §2.2
demuestra que **ninguna de las dos está en el corpus**. Estado: `NOT_DETERMINED` → la idea es
válida y **no ejecutable estáticamente**. Eso es una `DEPENDENCY_UNSATISFIED` con fuente única
(el firmware), y **no es culpa de la idea**.

### 6.3 `N-INT-19`: el registro la marca `REFORMULA(F-02)` y este nodo la **corrobora con una cita**

`IDEA-REGISTER.md:333` marca `N-INT-19` como `REFORMULA(F-02)`, con el texto *«DCC como reducción de
tráfico, no ON/OFF»*. **Ese juicio tiene ahora un artefacto detrás**, y no es una opinión:
`gfx_8_0_enum.h:505-521` — 17 cubos, con `UNCOMPRESSED` como valor de la misma magnitud, más
`CB_PERF_SEL_CC_CACHE_READS_SAVED_DUE_TO_DCC` en `:237`. La reformulación deja de ser una
sugestencia de redacción y pasa a ser **una descripción de la taxonomía del hardware**. Clase del
nuevo soporte: `CORROBORATED` (el artefacto existe y contiene exactamente lo que la reformulación
afirma); clase de «DCC ahorra tráfico en esta workload concreta»: `NOT_DETERMINED` (§5.2).

**Y el formato (N-INT-20) queda por debajo de DCC en capacidad de evidencia**: `N-INT-20` («compresión
× formato de render target») depende de la tabla de formatos de §3.2, que **no existe**. Los dos
sitios donde `F-04` toca formatos están `RESEARCH-LINES.md:808` («sus ramas son `VARIANT_OF` de un
corpus ya cerrado») y `IDEA-REGISTER.md:199` `R-NEW-72` `DUPLICATE` de `F-02`. Coherente.

### 6.4 Lo que queda como decisión de este nodo

- **Una** idea de barrido de caché: `(working set × patrón)`, con `R-NEW-07`, `N-INT-09`,
  `R-NEW-41`, `N-INT-11`, `N-INT-16`, `N-INT-17` como **ejes**, no como ideas.
- **`N-INT-12`** se transfiere a `MICROARCH-GFX8` (el segundo factor es ocupación).
- **`N-INT-18`** sobrevive, con dependencia declarada de un dato de firmware.
- **`N-INT-19`** sobrevige reformulada, con la reformulación corroborada por cita.
- **`N-INT-10`** (divergencia dentro de la wave) y **`N-INT-13`** (reutilización inter-wave) no se
  tocan: son microarquitectura, no jerarquía de memoria. Fuera del alcance declarado.

---

## 7. Falsificadores y estado residual

Cada clasificación importante de este documento, con la observación que la tumbaría.

| Afirmación | Refutador |
|---|---|
| §1 — `gc/` no es GFX8 | un fichero `gc_8_*`, o `gfx_8_0` reexportado desde `gc/`. No existe (listado completo de 30 ficheros) |
| §2.3 — `NUM_TCC_BANKS` 3 en Polaris12 y 7 en Polaris10, desigualdad real | una re-programación de `mmTCP_ADDR_CONFIG` en runtime. Buscada en las 7 207 líneas de `gfx_v8_0.c`: **no hay ninguna** fuera de las tablas golden |
| §2.3 — `TCC_CTRL.CACHE_SIZE=3` **no** dice el tamaño de L2 de esta tarjeta | una ASIC de la lista de §2.3 con `TCC_CTRL` distinto. **Las ocho tienen `0xf31fff7f`** |
| §2.2 — el corpus no tiene L2 ni línea de caché de POLARIS12 | una constante de L2 en `kfd_crat.c` o un `gc.config` con default. Scope completo de `kfd_crat.c`: la tabla es `carrizo_cache_info` con `TODO: Add L2` en `:122` |
| §2.4 — la golden no programa L1/`SQC` | un `WREG32(mmTCP_CNTL` o `mmSQC_CONFIG` en `gfx_v8_0.c`. No existe |
| §3.1 — no hay tabla DCC | un array de constantes con formato + block sizes en `amdgpu/` no-display. No existe |
| §3.3 — DCC es una magnitud con 17 valores, no un bit | lectura de hardware que muestre el cubo `UNCOMPRESSED` inaccesible o contadores distintos. `NOT_DETERMINED`: el enum **declara** los cubos; que el contador los cuente es lo que no se ha probado |
| §3.4 — las 16 `dcc` de `gmc_8_1_sh_mask.h` son `EDCC` | una de ellas no precedida de `E`. Las 16 son contiguas a `E` |
| §4.3 — el PTE de GFX8 no tiene campo de tipo | un `AMDGPU_PTE_MTYPE_GFX8` o un bit de tipo reutilizado. No existe en `amdgpu_vm.h` |
| §4.4(A) — el spill VRAM→GTT es gradual | un salto de segundo orden en la escalera de working set. **No probado**: es una predicción sobre TTM, y TTM no está en el corpus para esta pregunta. Clase real: `DERIVED` de una lectura de código, y por tanto más débil que el resto |
| §4.4(B) — el acantilado real está en la ventana GART de 256 MiB | un camino de recuperación en `amdgpu_ttm_alloc_gart` cuando `ttm_bo_mem_space` falla. No lo hay: `if (unlikely(r)) return r;` en `amdgpu_ttm.c:997-998` |
| §5.2 — los contadores no son legibles | una ruta de lectura GFX8 en `soc15.c`/`soc21.c`/`soc24.c`. Los cuatro dan `False` en los cinco tokens |

**Estado residual, explícito:**

- **Codificación → bytes de los tamaños de caché:** `NOT_DETERMINED`. Falta la tabla de encodings.
- **L2 / L1-texture / línea de caché de POLARIS12:** `NOT_DETERMINED`, fuente única = firmware
  (`gc_info.v1_2`, `gc_info.v1_3`).
- **Bancos de L2 en unidades absolutas:** `NOT_DETERMINED`. Conocida la desigualdad 3-vs-7.
- **`MDC` = caché de metadatos de DCC:** `HYPOTHESIS`. No hay ninguna frase que lo ligue.
- **Valores de los contadores:** `NOT_DETERMINED`. Los nombres existen; la lectura no.
- **Continuidad vs acantilado en el spill:** `DERIVED` de código, no medido. La única afirmación
  fuerte que hago es que **el sitio de la discontinuidad está identificado** (`gart_size >> PAGE_SHIFT`),
  no que laladder lo vaya a mostrar.
- **`MDC` / nivel L3:** `NOT_DETERMINED` para la existencia de estructura fuera de la L2; lo que
  es `PROVEN_ABSENT` es que la vía de discovery de GFX8 no reporta L3.

**No he tocado la GPU. No he usado `dmesg`/`journalctl`. No he hecho `grep` (todos los barridos son
`python3` con `open()` y `os.walk`). No he modificado ningún fichero del árbol salvo este. No he
renumerado nada. No he descargado nada.**

---

## 8. Citas heredadas de otros nodos, con su procedencia

| Dato | Procedencia | Verificado por mí |
|---|---|---|
| `gmc.gart_size = 256 MiB` y `GART: 256M 0x000000FF00000000` de esta máquina | nodo principal, registrado en `rx550_gart_table.h:30` | el 256 MiB **sí**, contra `gmc_v8_0.c:592-595`. El `0xFF00000000` lo **reprodujo** mi aritmética (§4.2) desde `amdgpu_gmc.c:294-336` |
| fórmula de cobertura `root_entries = ceil(max_pfn / (1<<block_size))` | nodo principal, commit `e417d64` | **no** rederivada (§4.6 pt. 2 la marca `NOT_DETERMINED` sin haber leído `rx550_vmid1_pgt.h`) |
| los 4 PRT golden writes no implementados | nodo principal | fuera del alcance de este nodo |
| el path de perfmon GFX8 no existe | nodo principal | **sí**, re-verificado (§0) |
| el recuento de 30 ficheros en `gc/` | nodo principal | **reinterpretado**: son de `gc/`, no de esta ASIC (§1). No lo rederivé |
| taxonomy `N-INT-*`, `R-NEW-*`, `M-0*`, `F-0*`, `H6` | `02-ARQUITECTURA/IDEA-REGISTER.md`, `00-INDICE/HYPOTHESIS-REGISTER.md` | citados por línea |