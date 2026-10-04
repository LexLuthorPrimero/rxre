# CONTADORES-GFX8-MAPA

```text
NODE_ID          = CONTADORES-GFX8-MAPA
CLASSIFICATION   = MAPA + MEDICIÓN + CORRECCIÓN DE ESTADO
TRACK            = STATIC (corpus). CERO acceso a la GPU.
WORK_CLASS       = READ_ONLY / EVIDENCE
WRITE_EXECUTION  = NONE. No se tocó GPU, no se usó dmesg ni journalctl.
TARGET           = 0000:01:00.0 · 1002:699F · CHIP_POLARIS12 · GFX8
CORPUS           = RESEARCH/baseline/linux-7.1.3/drivers/gpu/drm/amd
GIT_HEAD         = 85ca0c59ff45ac693e506893d2dea8ceb665f876
GIT_DIRTY        = 20 entradas (medido antes de escribir; este fichero es la única adición)
MODIFICATIONS    = 1 fichero nuevo. Nada más editado. Sin git add, sin commit.
```

**POR QUÉ ESTE NODO EXISTE.** Las líneas R-NEW-94..98 y N-INT-100..103 asumen que se
pueden leer contadores y que cada uno dice algo falsable. Este nodo mide si eso es cierto
**antes** de que se diseñe un experimento. La respuesta corta: **parcialmente cierto, y
por un motivo que invalida la premisa de trabajo tal como está redactada.**

---

## 0 · RESULTADO EN UNA TABLA

| pregunta | veredicto |
|---|---|
| ¿existe enumeración de eventos perfmon en el corpus? | **PROVEN_ABSENT** — y no sólo para GFX8 (§0.3) |
| ¿existen los *registros* de contador en el archivo de GFX8? | **PROVEN_PRESENT** — 349 regs, 94 contadores independientes (§4) |
| ¿cuántos registros independientes hay para este ASIC? | **2555** (no 16 703) (§1) |
| ¿cuántos son alcanzables sin root por ioctl? | **21 MMIO-vivo + 54 caché** (§2) |
| ¿cuántos de los 94 contadores de rendimiento son alcanzables por ioctl? | **0** (§2.4) |
| ¿cuál es la única vía que alcanza todo el espacio de registros? | debugfs `amdgpu_regs`, modo `0400`, **root** (§2.3) |

---

## 1 · ESTADO ENTRANTE: LO QUE SE VERIFICÓ Y LO QUE NO

El encargo traía tres afirmaciones medidas. Las reproduje una por una. **Dos se
confirmaron; una era erroneous en su parte decisiva, y una tercera tenía el número
equivocado.** No las heredo: las mido.

### 1.1 · CORRECCIÓN 1 — las cabeceras de GFX8 NO están en `gc/`

El encargo dice: *«Los nombres de registro SÍ están, en cabeceras:
`include/asic_reg/gc/` — 30 ficheros»*.

```text
MEDIDO  include/asic_reg/gc/  →  30 entradas
        ninguna es gfx8 ni gc_8_*:  el más antiguo es gc_9_0_*
        MEDIDO  os.walk sobre gc/ y sobre el árbol completo:
                artefactos "gfx8" o "gc_8*": 0
MEDIDO  include/asic_reg/gca/ →  12 entradas:
        gfx_6_0_{d,sh_mask}.h  gfx_7_0_d.h  gfx_7_2_{enum,sh_mask}.h
        gfx_8_0_{d,enum,sh_mask}.h  gfx_8_1_{d,enum,sh_mask}.h
```

GFX8 se describe en **`gca/`**, no en `gc/`. `gc/` es GFX9 (Vega) en adelante.
Prueba directa: `GRBM_STATUS__CP_BUSY_MASK` está definido en
`include/asic_reg/gca/gfx_8_0_sh_mask.h:5537`, y `mmGRBM_STATUS` en
`include/asic_reg/gca/gfx_8_0_d.h:862`; los dos primeros hits de `GRBM_STATUS` en
`gc/` sólo existen en `gc_9_0`, `gc_9_1`, `gc_9_2_1`, `gc_9_4_2`, `gc_9_4_3`,
`gc_10_*`, `gc_11_*`, `gc_12_*` — arquitecturas **distintas de la nuestra**.

Y el consumidor real lo confirma: `amdgpu/gfx_v8_0.c:49-51` incluye
`gca/gfx_8_0_d.h`, `gca/gfx_8_0_enum.h`, `gca/gfx_8_0_sh_mask.h`.

> **Consecuencia:** cualquier trabajo que se apoye en la ruta `gc/` para esta tarjeta
> está leyendo la tabla de registros de otra generación. Esto no es un detalle
> cosmetics; es exactamente el error que §1.3 cuantifica.

### 1.2 · CONFIRMADO — la ruta perfmon no está, pero es un hecho DEL CORPUS, no de GFX8

```text
MEDIDO  occurrences en soc21.c / soc15.c / gfx_v8_0.c / vi.c:
        sq_cmds 0 0 0 0      gfx8_ 0 0 0 0      grnm 0 0 0 0
        xx_mask 0 0 0 0      YY_MASK 0 0 0 0     perf_cnt 0 0 0 0
MEDIDO  os.walk TODO drivers/gpu/drm/amd, todo .h/.c:
        'sq_cmds' → 0 ficheros        'grnm' → 0 ficheros
        'BUMP_SET_' → 0 ficheros
ÚNICO   'perfmon' en soc21.c → soc21.c:562-563, y es una LLAMADA a
        adev->gfx.funcs->update_perfmon_mgcz, no una tabla
```

**Matiz que cambia el sentido del hallazgo.** El encargo dice «el path de perfmon de
GFX8 no está en el kernel». Lo medido es más fuerte y distinto: **no hay tablas de
enumeración de eventos perfmon para NINGÚN ASIC en este corpus.** No es una
característica de GFX8; es una característica de la foto del corpus.

> **Lo que esto NO permite concluir.** No permite concluir que el hardware GFX8 de esta
> placa carezca de contadores. De hecho §4 demuestra que el archivo de registros de
> GFX8 los declara. Lo que falta es el *mapa valor→evento*, no el *registro*.

### 1.3 · CONFIRMADO Y CORREGIDO — 16 703 es real, y es casi todo otra generación

```text
MEDIDO  regex \b(?:GRBM_|SQ_|TA_|CB_|DB_|VGT_|SH_|BC_)[A-Z0-9_]*\b
        sobre drivers/gpu/drm/amd completo:
        nombres distintos      = 16703      ← REPRODUCE el número del encargo
        ficheros con ≥1        = 136        ← el encargo decía 135 (off-by-one)

DESCOMPOSICIÓN (suma con solapamientos):
  desde gca/gfx_8_0_* + gfx_8_1_*  =  5410
  desde OTROS asic_reg (9/10/11/12)= 13842
  desde .c/.h de código            =  5125

  nombres que sólo existen FUERA de las cabeceras GFX8  =  9104
  nombres sólo en cabeceras GFX8                        =   672
```

El encargo tiene razón en el número y razón en que es una lista, no un mapa. La
conclusión Adds: **9 104 de los 16 703 nombres no describen esta placa.**

### 1.4 · CORRECCIÓN 2 — la lista blanca citada no es la de esta tarjeta

El encargo dice: *«`amdgpu_kms.c` `AMDGPU_INFO_READ_MMR_REG` es la única vía MMIO
desde userspace sin root, y su lista blanca para soc21 es `soc21.c:287-307` →
`soc21_allowed_read_registers[]`, 19 entradas, todas `SOC15_REG_ENTRY(GC,0,…)`;
`soc21_read_register` (`soc21.c:338`) devuelve `-EINVAL` para cualquier otro offset»*.

Hay tres errores y uno de ellos anula la premisa.

```text
a) soc21 NO es el camino de esta GPU.
MEDIDO  amdgpu/amdgpu_drv.c:2041   {0x1002, 0x699F, …, CHIP_POLARIS12}
MEDIDO  amdgpu/amdgpu_discovery.c:2056-2110  amdgpu_discovery_set_common_ip_blocks()
        switch sobre amdgpu_ip_version(adev, GC_HWIP, 0)
        casos presentes: 9.0.1 … 9.5.0, 10.x, 11.x, 12.0.x, 12.1.0
        caso 8.x:            >>> NO EXISTE <<<
        default:             amdgpu_discovery.c:2107-2110 → dev_err "Failed to add
                             common ip block" y NO se añade bloque common
MEDIDO  la tabla que sí contiene a Polaris12 está en amdgpu/vi.c:
        vi.c:2105  case CHIP_POLARIS10:
        vi.c:2106  case CHIP_POLARIS11:
        vi.c:2107  case CHIP_POLARIS12:
        vi.c:2108  case CHIP_VEGAM:
        vi.c:2109      amdgpu_device_ip_block_add(adev, &vi_common_ip_block);
        vi.c:2112      amdgpu_device_ip_block_add(adev, &gfx_v8_0_ip_block);
MEDIDO  soc15.c NO menciona soc21 en ninguna línea (0 ocurrencias)
        ni al revés. Son ramas disjuntas de amdgpu_discovery.

b) Por tanto la ruta efectiva es:
        vi.c:1452  vi_common_early_init()
        vi.c:1472      adev->asic_funcs = &vi_asic_funcs;
        vi.c:1431      .read_register  = &vi_read_register,
        amdgpu/amdgpu.h:1390
            #define amdgpu_asic_read_register(adev,se,sh,offset,v) \
                ((adev)->asic_funcs->read_register(...))
        amdgpu/amdgpu_kms.c:912  amdgpu_asic_read_register(adev, se, sh,
                                        info->read_mmr_reg.dword_offset + i, &regs[i])
        ⇒ vi_read_register, no soc15_read_register ni soc21_read_register.

c) Números:
        soc21.c:287-307  soc21_allowed_read_registers[] = 19 entradas  ✓ coincide
        soc15.c:381-402  soc15_allowed_read_registers[] = 20 entradas  (no 19)
        vi.c:665-742     vi_allowed_read_registers[]    = 76 entradas  ← LA QUE IMPORTA
   y «todas SOC15_REG_ENTRY(GC,0,…)» es falso incluso para soc21: soc21.c:294-295
   son SOC15_REG_ENTRY(SDMA0/SDMA1, 0, …). Las macros son reg* en soc21 y mm* en soc15/vi.

d) Consecuencia fuerte: como no hay bloque common para 8.x, adev->soc.funcs nunca se
   asigna para esta GPU, y por tanto soc15_read_register y soc21_read_register NO SON
   ALCANZABLES. No es que la lista blanca de soc21 sea restrictive: es que no se ejecuta.
```

> **Ésta es la corrección que decide el diseño de cualquier experimento.** La premisa
> «19 registros alcanzables» era pesimista por un lado y falsa por otro: la lista
> verdadera tiene 76 entradas, y 21 de ellas leen hardware de verdad.

### 1.5 · Lo que sí queda igual

`AMDGPU_INFO_READ_MMR_REG` está en `amdgpu/amdgpu_kms.c:875`, y `count > 128` →
`-EINVAL` en `amdgpu/amdgpu_kms.c:899-900`. Confirmado. Sobre el límite de 128 dwords:
`for` en `amdgpu_kms.c:911` llama con `dword_offset + i`, así que una petición de
128 dwords contiguos que cruza un registro no permitido aborta con `-EFAULT`
(`amdgpu_kms.c:917`) y **descarta el lote entero**; `regs[]` no se copia a userspace
porque `if (!ret)` en `amdgpu_kms.c:924` falla. Detalle operativo, no semántico.

---

## 2 · REDUNDANCIA (N-INT-101): el número real de registros

El encargo pide el número de **registros realmente distintos**, no de nombres. Se mide
por offset, que es la identidad física del registro.

### 2.1 · `gca/gfx_8_0_d.h` — offsets

```text
MEDIDO  include/asic_reg/gca/gfx_8_0_d.h = 2830 líneas
        #define mm<NAME> <hex>  parseados con ^\s*#\s*define\s+(mm…)\s+(0x…)\s*$

  nombres  mm* distintos ...................... 2633
  OFFSETS  distintos ......................... 2555   ← registro real
  offsets con >1 nombre (grupos alias) ....... 32
  nombres que son alias de otro ............... 78
  nombres únicos de su offset ................. 2523
```

**Respuesta a la pregunta del encargo: 2 555 registros, no 16 703.** Factor 6,5.

### 2.2 · Grupos de alias — no son errores, son hardware real

Los alias más grandes son coherentes con registros que.Documenta la realidad del
hardware. **Esto prueba que la deduplicación por offset es necesaria, y que los
"contrapuntos" de una lista de nombres no son puntos de medida independientes.**

| offset | #alias | nombres |
|---|---|---|
| `0x0237F` | **29** | `mmSQ_SOP2`, `mmSQ_VOP1`, `mmSQ_MTBUF_1`, `mmSQ_EXP_1`, `mmSQ_MUBUF_1`, `mmSQ_SMEM_1`, `mmSQ_INST`, `mmSQ_EXP_0`, `mmSQ_MUBUF_0`, `mmSQ_VOP_SDWA`, `mmSQ_VOP3_0`, `mmSQ_VOP2`, `mmSQ_MTBUF_0`, `mmSQ_SOPP`, `mmSQ_FLAT_0`, `mmSQ_VOP3_0_SDST_ENC`, `mmSQ_MIMG_1`, `mmSQ_SOP1`, `mmSQ_SOPC`, `mmSQ_FLAT_1`, `mmSQ_DS_1`, `mmSQ_VOP3_1`, `mmSQ_SMEM_0`, `mmSQ_MIMG_0`, `mmSQ_SOPK`, `mmSQ_DS_0`, `mmSQ_VOP_DPP`, `mmSQ_VOPC`, `mmSQ_VINTRP` |
| `0x023B0` | 15 | `mmSQ_THREAD_TRACE_WORD_*` (`CMN`,`INST`,`INST_PC_1_OF_2`,`INST_USERDATA_1_OF_2`,`TIMESTAMP_1_OF_2`,`WAVE`,`MISC`,`WAVE_START`,`REG_1_OF_2`,`REG_2_OF_2`,`REG_CS_1_OF_2`,`REG_CS_2_OF_2`,`EVENT`,`ISSUE`,`PERF_1_OF_2`) |
| `0x023B1` | 6 | `…_INST_PC_2_OF_2`, `…_INST_USERDATA_2_OF_2`, `…_TIMESTAMP_2_OF_2`, `…_PERF_2_OF_2`, `mmSQ_WREXEC_EXEC_LO`, `mmSQ_WREXEC_EXEC_HI` |
| `0x0001E` | 4 | `mmCSPRIV_THREAD_TRACE_TG0..TG3` |
| `0x021C0` | 2 | `mmCP_RB0_RPTR`, `mmCP_RB_RPTR` |
| `0x03040` | 2 | `mmCP_RB0_BASE`, `mmCP_RB_BASE` |
| `0x0304C` | 2 | `mmCP_RING_PRIORITY_CNTS`, `mmCP_ME0_PIPE_PRIORITY_CNTS` |
| `0x0EC05` | 2 | `mmRLC_SAFE_MODE`, `mmRLC_SOFT_RESET_GPU` |

Interpretación honesta: el hardware tiene **un** SQ_THREAD_TRACE_WORD en `0x23b0` y
`0x23b1`, con campos distintos dentro de la palabra. Los "29 nombres" de `0x0237F` son
el mismo一处 de取指. **Cuidado: esto es DERIVADO del layout, no semántica de hardware;
no hay fuente en el corpus que lo diga.**

### 2.3 · `gca/gfx_8_0_sh_mask.h` — campos

```text
MEDIDO  include/asic_reg/gca/gfx_8_0_sh_mask.h = 20837 líneas
        #define <REG>__<FIELD>_MASK    = 10366
        #define <REG>__<FIELD>__SHIFT  = 10394
        (con sufijo 'L', p.ej. DIDT_*: 28 líneas; no son de GFX8 GC)
        registros distintos con ≥1 campo = 2773
        pares (registro,campo)            = 10394
        media campos/registro             = 3.75
CRUCE   registros en sh_mask SIN offset en gfx_8_0_d.h = 176
        (CLIPPER_DEBUG_REG00.., etc.)
        offsets mm* SIN campos en sh_mask = 36  (CB_DEBUG_BUS_1..16, etc.)
```

El desfase 10 366 vs 10 394 y los 176/36 son **NOT_DETERMINED** en cuanto a su causa;
requieren revisar el parseo contra el fichero completo. No se afirma más.

### 2.4 · El número que decide

```text
REGISTROS INDEPENDIENTES PARA ESTE ASIC .................... 2555
de los cuales, NOMBRES con semántica de campo documentada .... 2773  (sh_mask)
de los cuales, ALCANZABLES por ioctl sin root (MMIO vivo) ..... 21
de los cuales, ALCANZABLES por ioctl (incl. caché software) .. 76
de los cuales, CONTADORES DE RENDIMIENTO independientes ....... 94   (§4)
```

---

## 3 · ALCANZABILIDAD: lo que decide si el mapa sirve de algo

### 3.1 · Vía 1 — `AMDGPU_INFO_READ_MMR_REG` (ioctl, sin root)

```text
MEDIDO  amdgpu_kms.c:875   case AMDGPU_INFO_READ_MMR_REG
MEDIDO  amdgpu_kms.c:912   amdgpu_asic_read_register(...)
MEDIDO  amdgpu_kms.c:917   ante fallo: ret = -EFAULT; break
MEDIDO  amdgpu.h:1390      → adev->asic_funcs->read_register
MEDIDO  vi.c:1431          → vi_read_register
MEDIDO  vi.c:665-742       vi_allowed_read_registers[]  = 76 entradas (vi.c:666..741)
MEDIDO  vi.c:849           if (reg_offset != …reg_offset) continue;
MEDIDO  vi.c:856           return -EINVAL;   ← todo lo no listado
```

### 3.2 · LA DISTINCIÓN QUE FALTA EN EL ENCARGO: 76 ≠ 76 lecturas

`vi_get_register_value` (vi.c:744) tiene dos ramas. En la **rama no-indexada**,
53 de las 76 entradas caen en `case` que devuelven **`adev->gfx.config.*`**, es decir
un valor cacheado en software en el momento del init — **no leen MMIO**:

```text
MEDIDO  vi.c:778-779   mmGB_ADDR_CONFIG      → adev->gfx.config.gb_addr_config
MEDIDO  vi.c:780-781   mmMC_ARB_RAMCFG       → adev->gfx.config.mc_arb_ramcfg
MEDIDO  vi.c:782-815   mmGB_TILE_MODE0..31   → adev->gfx.config.tile_mode_array[idx]
MEDIDO  vi.c:816-833   mmGB_MACROTILE_MODE0..15 → …macrotile_mode_array[idx]
   = 1 + 1 + 32 + 16 = 50 entradas, todas de caché
MEDIDO  vi.c:737-738,740-741  (grbm_indexed=true)
        mmCC_RB_BACKEND_DISABLE, mmGC_USER_RB_BACKEND_DISABLE,
        mmPA_SC_RASTER_CONFIG, mmPA_SC_RASTER_CONFIG_1
        → vi.c:753-762  devuelven adev->gfx.config.rb_config[se][sh].*
   = 4 entradas, todas de caché
MEDIDO  vi.c:835       default: return RREG32(reg_offset);   ← ÚNICA lectura real
```

```text
RESULTADO DE LA VIA 1 (ioctl, sin root, 76 entradas):
  23 entradas → lectura MMIO real
  53 entradas → lectura de caché software (NO son una medida del hardware actual)
  22 entradas → -EINVAL
```

Y de esas 23, el desglose por bloque es:

| # | vi.c | registro | offset GFX8 | campos con nombre |
|---|---|---|---|---|
| 1 | 666 | `mmGRBM_STATUS` | `0x02004` (`gfx_8_0_d.h:862`) | 24 |
| 2 | 667 | `mmGRBM_STATUS2` | `0x02002` (`:863`) | 18 |
| 3 | 668 | `mmGRBM_STATUS_SE0` | `0x02005` (`:864`) | 11 |
| 4 | 669 | `mmGRBM_STATUS_SE1` | `0x02006` (`:865`) | 11 |
| 5 | 670 | `mmGRBM_STATUS_SE2` | `0x0200E` (`:866`) | 11 |
| 6 | 671 | `mmGRBM_STATUS_SE3` | `0x0200F` (`:867`) | 11 |
| 7 | 672 | `mmSRBM_STATUS` | `0x00394` (`oss_3_0_d.h:91`) | 20 |
| 8 | 673 | `mmSRBM_STATUS2` | `0x00393` (`oss_3_0_d.h:90`) | 21 |
| 9 | 674 | `mmSRBM_STATUS3` | `0x00395` (`oss_3_0_d.h:92`) | 16 |
| 10 | 675 | `mmSDMA0_STATUS_REG` + `SDMA0_REGISTER_OFFSET` | `0x0` (`vid.h:26`) | 58 |
| 11 | 676 | `mmSDMA0_STATUS_REG` + `SDMA1_REGISTER_OFFSET` | `+0x200` (`vid.h:27`) | 58 |
| 12 | 677 | `mmCP_STAT` | `0x021A0` (`:564`) | 23 |
| 13 | 678 | `mmCP_STALLED_STAT1` | `0x0219D` (`:560`) | 16 |
| 14 | 679 | `mmCP_STALLED_STAT2` | `0x0219E` (`:561`) | 29 |
| 15 | 680 | `mmCP_STALLED_STAT3` | `0x0219C` (`:562`) | 19 |
| 16 | 681 | `mmCP_CPF_BUSY_STAT` | `0x02088` (`:354`) | 31 |
| 17 | 682 | `mmCP_CPF_STALLED_STAT1` | `0x02089` (`:355`) | 9 |
| 18 | 683 | `mmCP_CPF_STATUS` | `0x02087` (`:353`) | 21 |
| 19 | 684 | `mmCP_CPC_BUSY_STAT` | `0x02085` (`:351`) | 28 |
| 20 | 685 | `mmCP_CPC_STALLED_STAT1` | `0x02086` (`:352`) | 14 |
| 21 | 686 | `mmCP_CPC_STATUS` | `0x02084` (`:350`) | 15 |
| 22 | 739 | `mmGB_BACKEND_MAP` (indexed=false) | `0x0263F` (`:774`) | 1 |

*(22 filas: las 10 y 11 son el mismo registro en dos instancias, por eso «23 entradas»
y 22 filas.)*

### 3.3 · Vía 2 — debugfs `amdgpu_regs` (root): **alcanza todo**

```text
MEDIDO  amdgpu_debugfs.c:1694-1710  debugfs_regs[]  = 15 fops
MEDIDO  amdgpu_debugfs.c:1712-1728  debugfs_regs_names[] = "amdgpu_regs",
        "amdgpu_regs2", "amdgpu_gprwave", "amdgpu_regs_didt", "amdgpu_regs_pcie",
        "amdgpu_regs_pcie64", "amdgpu_regs_smc", "amdgpu_gca_config",
        "amdgpu_sensors", "amdgpu_wave", "amdgpu_gpr", "amdgpu_gfxoff",
        "amdgpu_gfxoff_status", "amdgpu_gfxoff_count", "amdgpu_gfxoff_residency"
MEDIDO  amdgpu_debugfs.c:1742-1745  bucle SIN gate por ASIC:
            debugfs_create_file(debugfs_regs_names[i], S_IFREG | 0400, root, …)
        ⇒ modo 0400 = sólo lectura por root. NO hay función .funcs de gfx que lo deshabilite.
MEDIDO  amdgpu_debugfs.c:1746-1747  i_size_write(ent->d_inode, adev->rmmio_size)
        ⇒ el nodo cubre [0, rmmio_size)
MEDIDO  amdgpu_debugfs.c:2152        llamada desde amdgpu_debugfs_init() (:2117)
        sin condición de ASIC
MEDIDO  amdgpu_debugfs.c:152         value = RREG32(*pos >> 2);   ← SIN lista blanca
MEDIDO  amdgpu_debugfs.c:279         value = RREG32(offset >> 2);  ← amdgpu_regs2, idem
MEDIDO  amdgpu_device.c:3814/3817    adev->rmmio_size = pci_resource_len(5 | 2)
MEDIDO  amdgpu_debugfs.c:200-204     existe .write → amdgpu_debugfs_regs_write
```

**Consecuencia.** El mapa de 2 555 registros **es alcanzable entero**, pero por una vía
privilegiada y con dos condiciones que hay que decir:

1. `0400` no concede escritura en el nodo. Existe un handler `.write`, pero si el modo
   del inodo es `0400` la escritura depende de `CAP_DAC_OVERRIDE` en el VFS.
   → **`NOT_VERIFIED` en este nodo**: no se ha tocado la GPU ni se ha probado una
   escritura. Se escribe como `NOT_VERIFIED`, no como «no se puede».
2. Leer un contador de rendimiento sin haber seleccionado un evento no mide nada.
   Seleccionar exige escribir el `SELECT`. §4.

### 3.4 · Vía 3 — `/sys/kernel/debug/dri` y debugfs de amdgpu: répondida

`/sys/kernel/debug/dri/0/amdgpu_regs` es exactamente el nodo de §3.3: la raíz es
`minor->debugfs_root` (amdgpu_debugfs.c:1739). No hay una vía distinta.
`amdgpu_gca_config` (amdgpu_debugfs.c:1720) expone la caché que §3.2 identifica como
*no-MMIO* — o sea, es la fuente de los 53 valores cacheados, y **no** es una medida.

### 3.5 · RESUMEN DE ALCANZABILIDAD

| clase | nº | vía | condición |
|---|---|---|---|
| registros MMIO-vivo | **21** | `AMDGPU_INFO_READ_MMR_REG` | sin root |
| caché software (falso positivo) | **53** | ídem | sin root, pero **no es hardware** |
| registros de GFX8 totales | 2555 | debugfs `amdgpu_regs` | **root** |
| contadores de rendimiento (94) | **0** por ioctl | debugfs `amdgpu_regs` | **root + write para SELECT** |
| enumeración valor→evento | **0** | — | **`PROVEN_ABSENT` en este corpus** |

---

## 4 · LOS CONTADORES DE RENDIMIENTO QUE SÍ EXISTEN

Éste es el hallazgo positivo, y es el que reencuadra todo lo anterior.

```text
MEDIDO  sobre gca/gfx_8_0_d.h, regex PERF|COUNTER en el nombre mm*:
  total de registros PERF/COUNTER ......... 349
  ..._LO  (mitad baja de contador) ........  94
  ..._HI  (mitad alta de contador) .........  92
  contadores independientes de 64 bits ....  94
  registros _SELECT (selector de evento) .. 119
  registros de control PERFMON/CPERF .......  44
  de los 349, presentes en
  vi_allowed_read_registers[] .............    0
```

Contadores por bloque (`_LO`):

```text
SQ 16 · PA_SC 8 · SPI 6 · CB 4 · DB 4 · PA_SU 4 · SX 4 · TCC 4 · TCA 4 · TCP 4 ·
GDS 4 · VGT 4 · IA 4 · WD 4 · CPG 2 · CPC 2 · CPF 2 · GRBM 2 · RLC 2 · TD 2 · TA 2 ·
GRBM_SE0..SE3 1 c/u · RLC_GPM_PERF_COUNT_0/1 1 c/u
```

Citas de ejemplo:

```text
gfx_8_0_d.h:886   mmGRBM_PERFCOUNTER0_SELECT    0xd840
gfx_8_0_d.h:892   mmGRBM_PERFCOUNTER0_LO        0xd040
gfx_8_0_d.h:893   mmGRBM_PERFCOUNTER0_HI        0xd041
gfx_8_0_d.h:2049  mmSQ_PERFCOUNTER0_SELECT      0xd9c0
gfx_8_0_d.h:2017  mmSQ_PERFCOUNTER0_LO          0xd1c0
gfx_8_0_d.h:2304  mmTA_PERFCOUNTER0_SELECT      0xdac0
gfx_8_0_d.h:2307  mmTA_PERFCOUNTER0_LO          0xd2c0
gfx_8_0_d.h:1668  mmSPI_PERFCOUNTER0_SELECT     0xd980
gfx_8_0_d.h:1679  mmSPI_PERFCOUNTER0_HI         0xd180
```

**Lo que esto prueba y lo que no.**

- **PROVEN:** el archivo de registros de GFX8 declara 94 contadores de 64 bits con
  nombre y offset, y 119 selectores de evento.
- **PROVEN_ABSENT:** el mapping `valor de SELECT → evento con nombre`. Sin él, un
  `SELECT` es un entero sin nombre. Leer `SQ_PERFCOUNTER0_LO` da un número que no
  significa nada por sí solo.
- **NO SE AFIRMA:** que estos contadores funcionen en esta placa. Que estén en la tabla
  de registros no prueba que el silicio los implemente, ni que el firmware los deje
  accesibles. Eso requiere lectura real, que este nodo no hizo.

---

## 5 · EL MAPA CONTADOR → HIPÓTESIS, Y SU FALSADOR

Regla aplicada (METH-NEW-02): *¿qué observación distinguiría H de ¬H?* Cada fila nombra
el **observado que falsaría** la hipótesis. Sin falsador, la fila no entra.

### 5.0 · La distinción NOMBRE / SEMÁNTICA, antes de todo

> Que un bit se llame `CP_BUSY` **no prueba qué hace CP ahí**. Prueba que se llama así.
> El corpus contiene un ejemplo donde esa distinción es literalmente el objeto del
> argumento: ver §5.1 fila 0 y la hipótesis H0.

Sólo hay **una** fuente de semántica en el corpus que no sea el nombre, y es
comportamental: cómo el driver **usa** el registro.

### 5.1 · `GRBM_STATUS` (`0x02004`, 24 campos con nombre)

Campos, en orden de bit. Cita de máscara y de shift alternando en
`gca/gfx_8_0_sh_mask.h`:

| bit | campo | máscara | línea mask |
|---|---|---|---|
| 0 | `ME0PIPE0_CMDFIFO_AVAIL` | `0x0000000F` | 5495 |
| 5 | `SRBM_RQ_PENDING` | `0x00000020` | 5497 |
| 7 | `ME0PIPE0_CF_RQ_PENDING` | `0x00000080` | 5499 |
| 8 | `ME0PIPE0_PF_RQ_PENDING` | `0x00000100` | 5501 |
| 9 | `GDS_DMA_RQ_PENDING` | `0x00000200` | 5503 |
| 12 | `DB_CLEAN` | `0x00001000` | 5505 |
| 13 | `CB_CLEAN` | `0x00002000` | 5507 |
| 14 | `TA_BUSY` | `0x00004000` | 5509 |
| 15 | `GDS_BUSY` | `0x00008000` | 5511 |
| 16 | `WD_BUSY_NO_DMA` | `0x00010000` | 5513 |
| 17 | `VGT_BUSY` | `0x00020000` | 5515 |
| 18 | `IA_BUSY_NO_DMA` | `0x00040000` | 5517 |
| 19 | `IA_BUSY` | `0x00080000` | 5519 |
| 20 | `SX_BUSY` | `0x00100000` | 5521 |
| 21 | `WD_BUSY` | `0x00200000` | 5523 |
| 22 | `SPI_BUSY` | `0x00400000` | 5525 |
| 23 | `BCI_BUSY` | `0x00800000` | 5527 |
| 24 | `SC_BUSY` | `0x01000000` | 5529 |
| 25 | `PA_BUSY` | `0x02000000` | 5531 |
| 26 | `DB_BUSY` | `0x04000000` | 5533 |
| — | **bit 27 SIN NOMBRE** | `0x08000000` | — |
| 28 | `CP_COHERENCY_BUSY` | `0x10000000` | 5535 |
| 29 | `CP_BUSY` | `0x20000000` | 5537 |
| 30 | `CB_BUSY` | `0x40000000` | 5539 |
| 31 | `GUI_ACTIVE` | `0x80000000` | 5541 |

**MEDIDO — el encargo dice «diez máscaras de busy». Son 24 campos, de los cuales 17
son `*_BUSY` o `GUI_ACTIVE`, 2 son `*_BUSY_NO_DMA`, 5 son `*_PENDING`/`*_CLEAN`/
`CMDFIFO_AVAIL`.** No hay grupo canónico de diez.

#### Semántica comportamental (la única del corpus)

```text
MEDIDO  gfx_v8_0.c:4798-4807  gfx_v8_0_is_idle():
          if (REG_GET_FIELD(RREG32(mmGRBM_STATUS), GRBM_STATUS, GUI_ACTIVE)
              || RREG32(mmGRBM_STATUS2) != 0x8)
                  return false;          /* NO idle */
          else return true;               /* idle */
MEDIDO  gfx_v8_0.c:4809-4817  gfx_v8_0_rlc_is_idle():
          RREG32(mmGRBM_STATUS2) != 0x8  →  no idle
```

De aquí sale una **definición** (no un nombre):

> `GFX idle  ⟺  GRBM_STATUS.GUI_ACTIVE == 0  ∧  GRBM_STATUS2 == 0x8`

`0x8` es el bit 3 de `GRBM_STATUS2`. En `gfx_8_0_sh_mask.h:5543` el campo
`ME0PIPE1_CMDFIFO_AVAIL` tiene máscara `0x0000000F`, es decir **los bits 0–3**. El bit 3
no tiene nombre propio.

> **H0 — `GRBM_STATUS2 == 0x8` significa «RLC_rq_pending=0 y ME0PIPE1_CMDFIFO_AVAIL=1».**
> **ESTADO: HYPOTHESIS / NOT_PROVEN.**
> *Falsador:* leer `GRBM_STATUS2` con la GPU ociosa y ver si vale `0x8`. Si vale `0x0`, o
> si vale `0x8` con `CMDFIFO_AVAIL` distinto de 1 en un estado他知道 ocioso, H0 cae.
> *Refutación adicional:* el corpus no nombra el bit 3. Que el driver use una constante
> mágica `0x8` sin nombre no prueba nada sobre hardware; puede ser un valor legado.

#### Mapa hipótesis ↔ falsador

| # | H | Falsador explícito | disciplined |
|---|---|---|---|
| H1 | El workload es *GPU-busy*: el hardware está ocupado, la CPU no es el techo | `GUI_ACTIVE==0` sostenido durante toda la ventana de benchmark | Si se cumple, H1 queda **REFUTADA** |
| H2 | Starvation (H8): la GPU pasa hambre porque no hay trabajo | `GUI_ACTIVE==0` **y** `GRBM_STATUS2 != 0x8` durante la ventana | H2 queda **REFUTADA**; si `GRBM_STATUS2==0x8` con GUI inactivo, el RLC está arriba y no hay hambre → otro凉了 motivo |
| H3 | El techo es un motor concreto (p. ej. TA) | `TA_BUSY==0` en ≥95 % de muestras mientras GUI_ACTIVE==1 | Si TA no está casi siempre activo, la hipótesis «cuello en TA» es **REFUTADA** |
| H4 | El techo es la largura de banda de VRAM | todos los `*_BUSY==0` y `GUI_ACTIVE==0` en la ventana | **REFUTADA** como hipótesis de motor |
| H5 | El techo es la presentación / RLC | `GRBM_STATUS2==0x8` sostenido (RLC busy) y `GUI_ACTIVE` intermitente |cuello **PARCIALMENTE** supportive |
| H6 | El techo es *submission* (CPU no llena la cola) | `GUI_ACTIVE` con huecosanskiy系统性: bursts de 0 separados por periods de 1 | distinguishable de H1 por la **forma temporal**, no por el valor medio |
| H7 | *Submission y* GPU compiten | correlación entre `CP_BUSY` y `GUI_ACTIVE` en la serie temporal | test de |

> **Advertencia metodológica, y es la que más importa.** H1 y H6 **no se distinguen con
> promedios**: ambos pueden dar 50 % de occupancy. Sólo se separan por la estructura
> temporal de la serie (ráfagas vs. huecos). Un experimento que mida «porcentaje de
> tiempo activo» sin conservar la serie **no puede falsar ninguna de las dos**, y por lo
> tanto no decide nada. Esta es la trampa concreta de N-INT-101.

### 5.2 · El conjunto de 14 bits que el driver **sí** usa — y el que no

```text
MEDIDO  gfx_v8_0.c:4890-4950  gfx_v8_0_check_soft_reset()
        4897  tmp = RREG32(mmGRBM_STATUS);
        4898-4904  if (tmp & ( PA_BUSY|SC_BUSY|BCI_BUSY|SX_BUSY|TA_BUSY|VGT_BUSY|
                               DB_BUSY|CB_BUSY|GDS_BUSY|SPI_BUSY|IA_BUSY|
                               IA_BUSY_NO_DMA|CP_BUSY|CP_COHERENCY_BUSY ))
        4905-4910  ⇒ SOFT_RESET_CP=1, SOFT_RESET_GFX=1, SRBM SOFT_RESET_GRBM=1
        4914-4930  GRBM_STATUS2: RLC_BUSY→SOFT_RESET_RLC
                               CPF_BUSY|CPC_BUSY|CPG_BUSY→SOFT_RESET_CPF/CPC/CPG
        4933-4934  SRBM_STATUS.GRBM_RQ_PENDING → SRBM SOFT_RESET_GRBM
        4937-4939  SRBM_STATUS.SEM_BUSY       → SRBM SOFT_RESET_SEM
        4941-4944  si cualquiera ⇒ return true  (hay que resetear)
```

> **MEDIDO y relevante: el driver usa 14 de los 17 bits `*_BUSY`.** Excluye
> `WD_BUSY` (bit 21) y `WD_BUSY_NO_DMA` (bit 16).
>
> **Lo que esto prueba:** la elección de 14 sobre 17 es *deliberada* — un conjunto
> "`_BUSY` que implica bloqueos para poder hacer soft-reset".
>
> **Lo que esto NO prueba:** que `WD_BUSY` carezca de valor diagnóstico. Y hay una
> hipótesisAlternative con falsador limpio: si WD (el *dispatcher*) no está en el
> conjunto del soft-reset, es porque soft-resetear con WD activo no es seguro, **no**
> porque WD no sea relevante para el cuello de botella. **Discriminante:** medir
> `WD_BUSY` durante el mismo workload en el que `GUI_ACTIVE` es alto. Si `WD_BUSY`
> sigue a `GUI_ACTIVE` con un retraso fijo, es un indicador de latencia de dispatch, y
> no aparece en el mapa de reset por razones de seguridad, no de irrelevancia.

### 5.3 · `GRBM_STATUS2` (18 campos, `gfx_8_0_sh_mask.h:5543-5577`)

```text
MEDITO  ME0PIPE1_CMDFIFO_AVAIL  0x0000000F :5543
        ME0PIPE1_CF_RQ_PENDING  0x00000010 :5545
        ME0PIPE1_PF_RQ_PENDING  0x00000020 :5547
        ME1PIPE0..2_RQ_PENDING  0x00000040..0x00000080 :5549..5551
        ME1PIPE3_RQ_PENDING     0x00000100 :5553
        ME2PIPE0..3_RQ_PENDING  0x00000200..0x00002000 :5555..5563
        RLC_RQ_PENDING          0x00004000 :5565
        RLC_BUSY                0x01000000 :5567
        TC_BUSY                 0x02000000 :5569
        TCC_CC_RESIDENT         0x04000000 :5571
        CPF_BUSY                0x10000000 :5573
        CPC_BUSY                0x20000000 :5575
        CPG_BUSY                0x40000000 :5577
```

| H | Falsador |
|---|---|
| H8: el techo es el *command processor* (fetch/submit) | todos los `ME*_RQ_PENDING` == 0 y `CP_BUSY` == 0 mientras `GUI_ACTIVE==1` ⇒ **CP no es el techo** |
| H9: el techo es el RLC | `RLC_BUSY==0` durante toda la ventana ⇒ **REFUTADA** |
| H10: el techo es el ROP/presentación | `TCC_CC_RESIDENT==1` sostenido con `GUI_ACTIVE` alto |falsaría H10 |

> Nota: `TCC_CC_RESIDENT` y `TCC_*_BUSY` no están en la lista de 14 bits del soft-reset
> (`gfx_v8_0.c:4898-4904`), pero sí hay `mmTCC_PERFCOUNTER*` en el archivo de
> registros (`gfx_8_0_d.h:2252-2265`). **Son dos caminos distintos al mismo subsistema,
> y sólo uno de ellos es alcanzable sin root.**

### 5.4 · `SRBM_STATUS` (20 campos, `oss/oss_3_0_sh_mask.h:469-507`)

Campos de `*_BUSY` y `*_RQ_PENDING` citados por nombre:

```text
UVD_RQ_PENDING 0x2 :469      VMC_BUSY 0x100 :481        ACP_BUSY 0x10000 :495
SAMMSP_RQ_PENDING 0x4 :471   MCB_BUSY 0x200 :483        IH_BUSY 0x20000 :497
ACP_RQ_PENDING 0x8 :473      MCB_NON_DISPLAY_BUSY 0x400 :485   UVD_BUSY 0x80000 :499
SMU_RQ_PENDING 0x10 :475     MCC_BUSY 0x800 :487        SAMMSP_BUSY 0x100000 :501
GRBM_RQ_PENDING 0x20 :477    MCD_BUSY 0x1000 :489       GCATCL2_BUSY 0x200000 :503
HI_RQ_PENDING 0x40 :479      VMC1_BUSY 0x2000 :491      OSATCL2_BUSY 0x400000 :505
SEM_BUSY 0x4000 :493         BIF_BUSY 0x20000000 :507
```

Éste es el registro con **más valor diagnóstico por bit** de los alcanzables, porque
nombraIP-wide en vez de por motor:

| H | Falsador |
|---|---|
| H11: el techo es la semántica / sync (`SEM_BUSY`) | `SEM_BUSY==0` sostenido ⇒ **REFUTADA**; y si los 94 contadores muestran wait-events alto, la variante es *cuello de sync* y no *cuello de motor* |
| H12: el techo es el fetch de comandos desde VRAM | `GRBM_RQ_PENDING` alto mientras `GUI_ACTIVE==0` ⇒ la GPU está esperando datos, no計算 |
| H13: el techo es PCIe (`BIF_BUSY`) | `BIF_BUSY==0` durante toda la ventana ⇒ **REFUTADA**. Es la forma más barata de matar «es I/O» |
| H14: el techo es eliod de reloj / power (`VMC_BUSY`, `MCD_BUSY`, `MCC_BUSY`) | los tres == 0 con GUI activo ⇒ **REFUTADA** |

### 5.5 · `CP_STAT` (23 campos, `gfx_8_0_sh_mask.h:3583-3627`)

```text
ROQ_RING_BUSY 0x200 :3583        DMA_BUSY 0x400000 :3609
ROQ_INDIRECT1_BUSY 0x400 :3585    RCIU_BUSY 0x800000 :3611
ROQ_INDIRECT2_BUSY 0x800 :3587    SCRATCH_RAM_BUSY 0x1000000 :3613
ROQ_STATE_BUSY 0x1000 :3589      CPC_CPG_BUSY 0x2000000 :3615
DC_BUSY 0x2000 :3591             CE_BUSY 0x4000000 :3617
ATCL2IU_BUSY 0x4000 :3593        TCIU_BUSY 0x8000000 :3619
PFP_BUSY 0x8000 :3595            ROQ_CE_RING_BUSY 0x10000000 :3621
MEQ_BUSY 0x10000 :3597           ROQ_CE_INDIRECT1_BUSY 0x20000000 :3623
ME_BUSY 0x20000 :3599            ROQ_CE_INDIRECT2_BUSY 0x40000000 :3625
QUERY_BUSY 0x40000 :3601         CP_BUSY 0x80000000 :3627
SEMAPHORE_BUSY 0x80000 :3603
INTERRUPT_BUSY 0x100000 :3605
SURFACE_SYNC_BUSY 0x200000 :3607
```

| H | Falsador |
|---|---|
| H15: el techo es el *vertex fetch* | `PFP_BUSY==0` y `ATCL2IU_BUSY==0` con GUI activo ⇒ **REFUTADA** |
| H16: el techo es el pixel shader (`ME_BUSY`) | `ME_BUSY==0` con GUI activo ⇒ **REFUTADA**. Es la hipótesis que más se ha dado por cierta sin medirse |
| H17: el techo es la rasterización/export | `CE_BUSY==0` y `TCIU_BUSY==0` con GUI activo ⇒ **REFUTADA** |
| H18: el techo es *surface sync* (espera de recursos entre passes) | `SURFACE_SYNC_BUSY` alto **y** `SEMAPHORE_BUSY` alto ⇒ supportive; si ambos bajos, **REFUTADA** |

> `CP_STAT.CP_BUSY` (`0x80000000`, línea 3627) y `GRBM_STATUS.CP_BUSY`
> (`0x20000000`, línea 5537) son **bits homónimos en registros distintos**. No son
> redundantes: uno es el CP global, el otro un flag de GRBM. Confundirlos sería el
> error de redundancia más fácil de cometer con este mapa. Ambos deben leerse.

### 5.6 · `SDMA0_STATUS_REG` / `SDMA1_STATUS_REG`

```text
MEDIDO  58 campos SDMA0_STATUS_REG__* definidos en
        include/asic_reg/oss/oss_3_0_sh_mask.h
MEDIDO  alcanzable sólo como la entrada 10 y 11 de la lista de vi.c,
        con base +0x0 (vid.h:26) y +0x200 (vid.h:27)
```

| H | Falsador |
|---|---|
| H19: el techo es la copia engine↔VRAM | `SDMA_STATUS` idle durante toda la ventana ⇒ **REFUTADA**. Es la falsificación directa de «es un problema de VRAM» |

### 5.7 · La falsación cruzada que hace el mapa utilizable

Con 21 registros MMIO-vivo, la *combinación* de los cinco bloques es lo que discrimina:

```text
  SRBM_STATUS  ── global (sem, bif, clocks, IP-wide)
  GRBM_STATUS  ── por motor, y GUI_ACTIVE
  GRBM_STATUS2 ── CP/ME/RLC
  CP_STAT      ── descompone el CP
  SDMAx_STATUS ── copia
```

Regla de decisión, con su falsador:

> Si `GUI_ACTIVE` es alto **y** todos los `*_BUSY` de motor son bajos, el techo **no**
> es un motor de graphics. **Falsador de la regla:** una lectura en la que
> `GUI_ACTIVE==1` y un `*_BUSY` de motor sea 1 la mayor parte del tiempo.

---

## 6 · LA PUERTA

Se puede construir con criterio. Se ejecutó **en línea, sin crear fichero** (el nodo
permite exactamente un fichero nuevo, y lo ocupa este documento), y por tanto **no
existe como artefacto persistente**. `TOOL_STATE = SELF_TESTED`, no `VALIDATED`.

### 6.1 · Especificación

**GATE-MAP-GFX8-v1.** Para cada entrada `e` del mapa:

- **G1** `e.registro` debe resolverse a un `#define mm<…> <hex>` en el conjunto de
  cabeceras GFX8. *Fail* si no.
- **G2** `e.via` debe pertenecer al conjunto cerrado
  `{READ_MMR_REG, DEBUGFS_AMDGPU_REGS, DEBUGFS_AMDGPU_REGS2}`. *Fail* si no.
- **G3** Si `e.via == READ_MMR_REG`, `e.registro` debe ser miembro de
  `vi_allowed_read_registers[]` (`vi.c:666..741`). *Fail* si no.
- **G4** `e.via` debe llevar escrito el requisito de privilegio. *Fail* si no.

*Pass:* todas las entradas satisfacen G1–G4.

### 6.2 · Controles negativos (obligatorios)

| control | inyección | resultado exigido |
|---|---|---|
| N1 | registro inexistente `mmGRBM_STATUS_NOT_REAL` | **FAIL** por G1 |
| N2 | registro real no listado (`mmTA_STATUS`) declarando `READ_MMR_REG` | **FAIL** por G3 |
| N3 | vía fuera del conjunto cerrado (`TELEPATHY`) | **FAIL** por G2 |

### 6.3 · Resultado ejecutado

```text
=== GATE RUN (2ª pasada) ===
  P  positivo (mapa completo)          : 27 entradas -> PASS
  N1 control: registro inexistente     : 1 entrada  -> FAIL
       ! mmGRBM_STATUS_NOT_REAL: NOT DEFINED in GFX8 header set
       ! mmGRBM_STATUS_NOT_REAL: claims READ_MMR_REG but absent from
                                  vi_allowed_read_registers[]
  N2 control: real, no listado, READ_MMR_REG : 1 entrada -> FAIL
       ! mmTA_STATUS: claims READ_MMR_REG but absent from vi_allowed_read_registers[]
  N3 control: vía no declarada         : 1 entrada  -> FAIL
       ! mmGRBM_STATUS: path 'TELEPATHY' outside closed set

GATE VERDICT: VALID (P passes; N1,N2,N3 fail as required)
```

**La puerta tiene valor real y hay que decirlo:** en la **primera** pasada, P **falló**
sobre mi propio mapa:

```text
  P (1ª pasada): 23 entradas -> FAIL
       ! mmGRBM_GFX_CNTL: NOT DEFINED in GFX8 header set
```

El motivo es instructive y es exactamente la clase de error que G1 existe para
atrapar: `mmGRBM_GFX_CNTL` se usa en `soc15.c:372` y `soc21.c:273-278` con
`WREG32_SOC15_RLC_SHADOW`, pero **no** existe en `gfx_8_0_d.h` — pertenece a la tabla
`reg*` de `soc15_registers.h`, que para GFX8 no se resuelve por `mm*`. Si se hubiera
publicado el mapa sin la puerta, habría ASSERTADO la existencia de un registro
lecturable por ese nombre en esta ASIC. Eso no se habría detectado nunca por lectura.

---

## 7 · LO QUE QUEDA ABIERTO, Y CON QUÉ ESTADO

Nada de esto es un plan. Es el registro de lo que **no** se puede afirmar todavía.

| # | Cuestión | Estado | Por qué no se cierra |
|---|---|---|---|
| 1 | Semántica de cada bit `*_BUSY` | **`PROVEN_ABSENT` en el corpus** | No hay fuente. Los nombres son la única evidencia. La única semántica comportamental es `gfx_v8_0_is_idle` (§5.1) y el conjunto de soft-reset (§5.2) |
| 2 | `GRBM_STATUS2 == 0x8` | **`HYPOTHESIS`** (H0) | Requiere lectura real |
| 3 | Escritura por `amdgpu_regs` (0400) | **`NOT_VERIFIED`** | Requiere root y escribir en hardware. Este nodo no hace eso |
| 4 | Que los 94 contadores funcionen | **`NOT_DETERMINED`** | Están en la tabla de registros. Que el silicio los implemente no está probado |
| 5 | Mapping `SELECT` → evento | **`PROVEN_ABSENT` en este corpus** | `sq_cmds` = 0 ficheros. Sin esto, un contador es un entero sin nombre |
| 6 | Los 176 registros de sh_mask sin offset, y los 36 sin campos | **`NOT_DETERMINED`** | Requiere el parseo revisado contra el fichero completo |
| 7 | `WD_BUSY` / `WD_BUSY_NO_DMA` excluidos del set de soft-reset | **`HYPOTHESIS`** | §5.2, discriminante dado |
| 8 | `rmmio_size` efectivo de esta placa | **`NOT_DETERMINED`** | `amdgpu_device.c:3814/3817` lo toma de `pci_resource_len`; el valor numérico requiere config space con privilegios (§ de `HARDWARE-FINGERPRINT.md:137` ya dice que no es legible sin ellos) |
| 9 | `H1` vs `H6` (GPU-busy vs starvation) | **separables sólo por estructura temporal** | §5, nota metodológica. Un agregado de occupancy no las separa |

### 7.1 · Lo que este nodo cambió respecto al encargo

1. `gc/` → **`gca/`**. La ruta de cabeceras del encargo era de otra generación.
2. `soc21.c` / `soc15.c` → **`vi.c`**. GFX8 no entra en
   `amdgpu_discovery_set_common_ip_blocks`; su whitelist real tiene 76 entradas.
3. «19 registros alcanzables» → **21 MMIO-vivo + 53 caché-software**, y 53 de las 76
   entradas **no son una medida del hardware**. Este es el punto donde la lista se
   convierte en mapa.
4. «16 703 nombres» → **2 555 registros** para este ASIC; 9 104 de esos nombres no le
   describen.
5. «no hay contadores» sería **incorrecto**: hay 94 contadores y 119 selectores
   declarados en `gca/gfx_8_0_d.h`. Lo que falta es el significado del selector. La
   premisa de R-NEW-94..98 es *parcialmente* correcta y por tanto más útil, no menos.

---

## 8 · PRÓXIMO NODO SUGERIDO (no ejecutado aquí)

```text
WORK_ID          = MEDIR-GUI_ACTIVE-SIN-ROOT
QUESTION         ¿cuál es la tasa de ocupación real de GUI_ACTIVE bajo un workload
                 controlado, y es estacionaria?
DEPENDENCIAS     este mapa (ya cerrado)
REQUIRED_OBS     serie temporal de GRBM_STATUS (bit 31) y GRBM_STATUS2 vía
                 AMDGPU_INFO_READ_MMR_REG, sin root
REQUIRED_CAP     lectura MMIO por ioctl — YA MEDIDA COMO EXISTENTE (§3.2)
DISCRIMINANT     H1 (GPU-busy, occupancy alta) vs H6 (starvation, huecos).
                 Un agregado NO los separa (§5, nota). Hace falta la serie.
PASS             se obtiene una serie de N muestras con marca temporal
FAIL             la lectura devuelve -EINVAL para 0x2004
INVALID          devuelve valores de la caché software en vez de MMIO
ABORT            si cualquier lectura devuelve un valor constante idéntico
                 durante toda la ventana ⇒ sospechar caché, no hardware
RIESGO           NINGUNO. READ_ONLY. count ≤ 128, sin escrituras.
COSTE            bajo — un binario userspace, sin privilegios
```

Este nodo es el que **no requiere root** y el que **no depende** del mapping
`SELECT→evento` ausente. Es el único discriminante disponible hoy que no está bloqueado
por lo que §7 deja abierto.

---

```text
DISCREPANCIA REGISTRADA:
  ID       D-CONTADORES-01
  ENCARGO  «los nombres SÍ están, en cabeceras include/asic_reg/gc/ — 30 ficheros»
  MEDIDO   los 30 ficheros de gc/ son GFX9..GFX12; GFX8 está en gca/ (12 ficheros)
  ALCANCE  invalida cualquier trabajo que use gc/ para esta tarjeta

  ID       D-CONTADORES-02
  ENCARGO  «lista blanca para soc21 … 19 entradas, todas SOC15_REG_ENTRY(GC,0,…)»
  MEDIDO   (a) el camino de Polaris12 es vi.c, no soc21 ni soc15
           (b) vi.c:665-742 tiene 76 entradas, no 19
           (c) «todas GC,0» es falso: soc21.c:294-295 son SDMA0/SDMA1
  ALCANCE  cambia el número de contrapuntos de 19 a 21 (MMIO-vivo)

  ID       D-CONTADORES-03
  ENCARGO  «el path de perfmon de GFX8 no está en el kernel»
  MEDIDO   sq_cmds / grnm / BUMP_SET_ = 0 ficheros en TODO el árbol amd.
           No es una propiedad de GFX8; es del corpus.
  ALCANCE  la ausencia no se puede atribuir al hardware

  ID       D-CONTADORES-04 (descubierto por la propia puerta)
  ENCARGO   —
  MEDIDO    mmGRBM_GFX_CNTL se usa en soc15.c:372 / soc21.c:273-278 pero NO existe
            en gfx_8_0_d.h; pertenece a la tabla reg* de soc15_registers.h
  ALCANCE   la puerta G1 lo detectó sobre el propio mapa; sin puerta habría pasado
```