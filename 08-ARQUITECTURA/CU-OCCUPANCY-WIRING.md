# CU-OCCUPANCY-WIRING — ¿se puede leer `SPI_CSQ_WF_ACTIVE_*` sin root en esta placa?

```
AGENT_ID      : WORKER (subagente)
NODE_ID       : CU-OCCUPANCY-WIRING
ENTRADA       : encargo escrito por el coordinador + §5.2 de 08-ARQUITECTURA/MICROARCH-GFX8.md
SALIDA        : 08-ARQUITECTURA/CU-OCCUPANCY-WIRING.md   (este fichero, y nada más)
MODO          : sólo lectura estática del corpus. Sin GPU. Sin /dev/dri/*. Sin sysfs.
                Sin debugfs. Sin dmesg/journalctl. Sin red. Sin grep. Sin git add/commit.
```

## 0. Corpus y estado de partida

| | |
|---|---|
| Kernel en ejecución | `uname -r` = `7.1.3-200.nobara.fc44.x86_64` |
| Corpus medido | `RESEARCH/working/linux-7.1.3/` |
| `drivers/gpu/drm/amd/amdgpu/vi.c` sha256 | `c554b770b71edb8476f29ca420fb71bf020cde85e556781058ea3883d746820f` |
| Identidad del fichero en los tres árboles | `RESEARCH/working/…7.1.3`, `RESEARCH/baseline/…7.1.3`, `rx550-upstream-7.2.8/…7.2.8` → **los tres con el MISMO sha256**. No hay deriva entre 7.1.3 y 7.2.8 para este fichero. |

`STATE_BEFORE` **heredado y NO_TRAZADO** (no lo adopto):

- «76 entradas, 53 caché, 21 hardware» → el **76 está CONFIRMADO**; la división **no**: es
  **54 / 22** (§1.1). Divergencia de 1 en cada mitad.
- «la única vía MMIO sin root es `AMDGPU_INFO_READ_MMR_REG`» → el ioctl existe y es la
  única ruta de lectura MMIO *por ioctl* (`amdgpu_drv.c:3057`, `amdgpu_kms.c:875`), pero
  que exija o no privilegios **no lo he medido**: `drm_ioctl.c` **no está en el corpus**
  (verificado por recorrido del árbol), así que la semántica de `DRM_AUTH` queda
  `NOT_TRACED`. No cambia el veredicto: el registro no está en la lista blanca en ningún
  caso.
- «geometría 4x8» → **`NOT_FOUND` / `NOT_TRACED`**. Para `CHIP_POLARIS12`,
  `gfx_v8_0.c:1681-1695` **no asigna** `max_shader_engines`, `max_sh_per_se` ni
  `max_cu_per_sh`: llama a `amdgpu_atombios_get_gfx_info(adev)` (`gfx_v8_0.c:1683`), que
  los copia de la tabla `GFX_Info` del VBIOS (`amdgpu_atombios.c:744-750`). No hay
  constante en el driver. El 4×8 no sale de este corpus.

---

## 1. Veredicto

### 1.1 El número, medido (no heredado)

Parseo literal del array y de los dos `switch` de `vi_get_register_value`:

| | cantidad | cómo se obtuvo |
|---|---|---|
| entradas de `vi_allowed_read_registers[]` | **76** | `vi.c:666-741`, 75 nombres únicos (`mmSDMA0_STATUS_REG` aparece dos veces con dos offsets) |
| nombres con `case` en `vi_get_register_value` (`vi.c:753-836`) | **54** | los dos `switch`: indexado `vi.c:753-762`, no indexado `vi.c:777-834` |
| ⇒ devuelven **caché de software** (`adev->gfx.config.*`) | **54** | conjunto por identidad de nombre |
| ⇒ caen en `default: return RREG32(reg_offset);` (`vi.c:834-835`) y **leen hardware** | **22** | complemento |

**El encargo dijo 53/21. Es 54/22.** El 76 coincide. Un origen plausible del «-1»: si se
cuenta por *nombres* en vez de por *entradas*, hay 75 (76 menos el duplicado de
`mmSDMA0_STATUS_REG`); y si se excluye `mmGB_BACKEND_MAP` de alguna manera se pierde uno
más. No importa la causa: la cuenta defendible es 54/22 y está reproducible con el
procedimiento de §2.

Mecánicamente: `vi_read_register` (`vi.c:840`) recorre el array (`vi.c:846`) y exige
coincidencia exacta de offset (`vi.c:849-850`); si no coincide devuelve error. Toda la
semántica de la lista está en esos 76 nombres.

### 1.2 La línea que lo sostiene

```
RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/vi.c:666 … :741
        (array completo; ninguna entrada empieza por mmSPI)
RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/vi.c:849
        if (reg_offset != vi_allowed_read_registers[i].reg_offset)
                continue;
```

Intersección medida:

```
|  vi_allowed_read_registers[] (75 nombres)  ∩  {mm* con PERF o COUNTER en gfx_8_0_d.h}  |  =  0
```

Y el número **349** del encargo queda **CONFIRMADO y con definición explícita**:
`gfx_8_0_d.h` tiene 2633 `#define mm*`; 346 nombres contienen `PERF`, 312 contienen
`COUNTER`, y la **unión vale exactamente 349**.

### 1.3 Veredicto

> **`ALCANZABLE_SIN_ROOT` = NO para `mmSPI_CSQ_WF_ACTIVE_STATUS` y
> `mmSPI_CSQ_WF_ACTIVE_COUNT_0..7` por cualquier vía de la que dispongamos hoy sin
> privilegios de administrador.**

Desglose por vía, cada una con su cita:

| vía | ¿alcanza el registro? | por qué |
|---|---|---|
| ioctl `AMDGPU_INFO_READ_MMR_REG` | **NO** | `amdgpu_kms.c:875-930` despacha a `amdgpu_asic_read_register` (`amdgpu_kms.c:912`), que para VI es `vi_read_register` (`vi.c:1431`); el offset debe estar en `vi_allowed_read_registers[]` o devuelve error (`vi.c:849-850`). No está. |
| `/sys/kernel/debug/drm/0/amdgpu_regs`, `amdgpu_regs2` | **NO sin root** | Sí leen **cualquier** offset MMIO, sin lista blanca (`amdgpu_debugfs.c:152` `RREG32(*pos >> 2)`), y con selector ME/PIPE/QUEUE/VMID (`amdgpu_debugfs.c:104-111`, `:142`). **Pero** se crean con modo `S_IFREG | 0400` (`amdgpu_debugfs.c:1743-1745`) → sólo el propietario (root) puede leerlos. Ademáscalled mismo reanuda: `pm_runtime_get_sync` en `amdgpu_debugfs.c:118` (y `:240` para `regs2`). |
| sysfs de amdgpu | **NO** | Los únicos atributos de dispositivo son `pcie_replay_count` 0444, `board_info` 0444, `carveout_options` 0444, `carveout` 0644 (`amdgpu_device.c:237`, `:360`, `:433`, `:497`). Ninguno lee registros. |
| `fdinfo` de DRM (`/proc/<pid>/fdinfo`) | **NO** | `amdgpu_fdinfo.c:86-121` publica `pasid`, `drm-memory-*`, `amd-evicted-vram`, `drm-engine-*`. Cero occupancy. |
| sysfs/procfs de KFD (`cu_occupancy`) | **NO — el fichero ni siquiera existe** | `kfd_process.c:601-604` sólo crea el atributo si `dev->kfd2kgd->get_cu_occupancy` es no-NULL; y `kfd_process.c:279-280` devuelve `-EINVAL` si se lee sin él. `gfx_v8_kfd2kgd` (`amdgpu_amdkfd_gfx_v8.c:592-610`, 14 entradas) **no tiene** `.get_cu_occupancy`. |
| `/dev/mem` | fuera de alcance | requiere `CAP_SYS_RAWIO`. No medido, no invocado. |

**Además, la vía que sí llega (el ioctl) reanuda la GPU.** Confirmado por mí, no heredado:
`amdgpu_driver_open_kms` está en `amdgpu_kms.c:1435` y su primera operación es
`pm_runtime_get_sync(dev->dev)` en `amdgpu_kms.c:1453`; es el `.open` de las **dos**
registraciones (`amdgpu_drv.c:3076` y `amdgpu_drv.c:3102`). Con `boot_vga = 1`, abrir el
nodo render es despertar el adaptador de la pantalla. Por eso el requerimiento «sin root »
de este nodo es, en la práctica, **«sin root *y* sin despertar la GPU»**, y las dos
condiciones sólo se pueden juntas por el camino de §4.

### 1.4 El falsador — qué observación Volvería la respuesta «SÍ»

El veredicto es `NO` sobre **tres** legs distintos. Cada leg tiene su propio falsador:

1. **Leg del ioctl.** *Refutador:* que exista una ruta de lectura MMIO por ioctl para VI
   **fuera** de `vi_read_register`. Contrarefutación ya hecha: barriendo todo
   `drivers/gpu/drm/amd/` hay exactamente **8** tablas `*_allowed_read_registers[]`, una
   por familia (`vi.c:665`, `soc15.c:381`, `nv.c:335`, `soc21.c:287`, `soc24.c:113`,
   `soc_v1_0.c:168`, `si.c:1119`, `cik.c:1043`), y el despacho de
   `AMDGPU_INFO_READ_MMR_REG` es **uno** (`amdgpu_kms.c:875`), hacia
   `amdgpu_asic_read_register`. Para Polaris12 ese es `vi_read_register` (`vi.c:1431`).
   Un refutador real sería: **un parche de kernel que añada el offset a
   `vi_allowed_read_registers[]`**, o un `AMDGPU_INFO_*` nuevo. Eso es una decisión de
   nivel de autorización (§5), no una vía de usuariospace que hoy exista.
2. **Leg de debugfs.** *Refutador:* que el fichero sea legible por el usuario actual.
   Afirmado desde el corpus: modo `0400` (`amdgpu_debugfs.c:1744`). **No he medido**
   el modo del montaje de `/sys/kernel/debug` (prohibición explícita de este nodo) ni
   el modo efectivo del fichero en esta máquina. *Refutador concreto:* un `stat` del
   fichero que devuelva un modo con bit de lectura para el grupo/otros. Con ese dato, y
   **aun aceptando el despertar**, la respuesta cambiaría a «SÍ, con despertar».
3. **Leg de la premisa «sin root».** *Refutador:* que `AMDGPU_INFO` no exija
   `CAP_SYS_ADMIN`. `amdgpu_drv.c:3057` lo declara `DRM_AUTH|DRM_RENDER_ALLOW`, pero
   `drm_ioctl.c` no está en el corpus, así que **no puedo cerrar esta leg**.
   *Refutador concreto:* una ejecución real del ioctl como usuario no-root que devuelva
   datos. Ese no la he hecho (reabre la GPU) y no se hará aquí.

**Una observación que NO falsaría nada:** que `SPI_CSQ_WF_ACTIVE_STATUS` devuelva 0.
Sería consistente tanto con «cero colas activas» como con «offset mal cableado». No
discrimina.

---

## 2. Las 22 entradas: el catálogo de lo que esta tarjeta deja leer sin root

Producto reutilizable. Offset en **índice dword** (convención `RREG32` =
`adev->mmio.dword[idx]`) y su equivalente en bytes (`idx*4`), que es lo que necesita
`readl`. La fuente de cada offset se indica porque **5 de los 22 nombres no están en
`gfx_8_0_d.h`**: para VI vienen del bloque OSS 3.0. Verificado calculando el **closure
completo de includes entrecomillados de `vi.c`** (42 includes directos → 127 ficheros) y
buscando cada `#define`: hay **exactamente una** definición de cada uno, todas en
`include/asic_reg/oss/oss_3_0_d.h`.

| # | `vi.c` | nombre en el array | índice dword | byte | dónde se define el offset | lectura honesta |
|--:|---|---|---|---|---|---|
| 1 | 666 | `mmGRBM_STATUS` | `0x2004` | `0x8010` | `gfx_8_0_d.h:862` | hardware |
| 2 | 667 | `mmGRBM_STATUS2` | `0x2002` | `0x8008` | `gfx_8_0_d.h:863` | hardware |
| 3 | 668 | `mmGRBM_STATUS_SE0` | `0x2005` | `0x8014` | `gfx_8_0_d.h:864` | hardware |
| 4 | 669 | `mmGRBM_STATUS_SE1` | `0x2006` | `0x8018` | `gfx_8_0_d.h:865` | hardware |
| 5 | 670 | `mmGRBM_STATUS_SE2` | `0x200e` | `0x8038` | `gfx_8_0_d.h:866` | hardware |
| 6 | 671 | `mmGRBM_STATUS_SE3` | `0x200f` | `0x803c` | `gfx_8_0_d.h:867` | hardware |
| 7 | 672 | `mmSRBM_STATUS` | `0x394` | `0xe50` | `oss_3_0_d.h:91` | hardware |
| 8 | 673 | `mmSRBM_STATUS2` | `0x393` | `0xe4c` | `oss_3_0_d.h:90` | hardware |
| 9 | 674 | `mmSRBM_STATUS3` | `0x395` | `0xe54` | `oss_3_0_d.h:92` | hardware |
| 10 | 675 | `mmSDMA0_STATUS_REG + SDMA0_REGISTER_OFFSET` | `0x340d` | `0xd034` | `oss_3_0_d.h:303`, offset `0x0` en `vid.h:26` | hardware, **semántica sin corroborar** (a) |
| 11 | 676 | `mmSDMA0_STATUS_REG + SDMA1_REGISTER_OFFSET` | `0x360d` | `0xd834` | ídem, offset `0x200` en `vid.h:27` | hardware, **semántica sin corroborar** (a) |
| 12 | 677 | `mmCP_STAT` | `0x21a0` | `0x8680` | `gfx_8_0_d.h:564` | hardware |
| 13 | 678 | `mmCP_STALLED_STAT1` | `0x219d` | `0x8674` | `gfx_8_0_d.h:560` | hardware |
| 14 | 679 | `mmCP_STALLED_STAT2` | `0x219e` | `0x8678` | `gfx_8_0_d.h:561` | hardware |
| 15 | 680 | `mmCP_STALLED_STAT3` | `0x219c` | `0x8670` | `gfx_8_0_d.h:562` | hardware |
| 16 | 681 | `mmCP_CPF_BUSY_STAT` | `0x2088` | `0x8220` | `gfx_8_0_d.h:354` | hardware |
| 17 | 682 | `mmCP_CPF_STALLED_STAT1` | `0x2089` | `0x8224` | `gfx_8_0_d.h:355` | hardware |
| 18 | 683 | `mmCP_CPF_STATUS` | `0x2087` | `0x821c` | `gfx_8_0_d.h:353` | hardware |
| 19 | 684 | `mmCP_CPC_BUSY_STAT` | `0x2085` | `0x8214` | `gfx_8_0_d.h:351` | hardware |
| 20 | 685 | `mmCP_CPC_STALLED_STAT1` | `0x2086` | `0x8218` | `gfx_8_0_d.h:352` | hardware |
| 21 | 686 | `mmCP_CPC_STATUS` | `0x2084` | `0x8210` | `gfx_8_0_d.h:350` | hardware |
| 22 | 739 | `mmGB_BACKEND_MAP` | `0x263f` | `0x98fc` | `gfx_8_0_d.h:774` | hardware |

Los otros **54** (los que devuelven caché, sin tocar hardware) =
`mmGB_ADDR_CONFIG`, `mmMC_ARB_RAMCFG`, `mmGB_TILE_MODE0..31` (32), `mmGB_MACROTILE_MODE0..15`
(16) y los 4 indexados `mmCC_RB_BACKEND_DISABLE`, `mmGC_USER_RB_BACKEND_DISABLE`,
`mmPA_SC_RASTER_CONFIG`, `mmPA_SC_RASTER_CONFIG_1`. Los 4 indexados son los únicos con
`grbm_indexed = true` (`vi.c:737`, `:738`, `:740`, `:741`) y por eso pasan por
`vi.c:764-772` (selector SE/SH bajo `grbm_idx_mutex`).

### 2.1 Tres salvedades que hay que leer con la tabla

- **(a) `ALCANZABLE_SIN_ROOT` ≠ `DEVUELVE EL REGISTRO CORRECTO`.** Las entradas 10 y 11
  resuelven a `0x340d` y `0x360d`, y **`0x340d`/`0x360d` no aparecen en ninguna parte del
  camino de código de VI** (búsqueda literal sobre `drivers/gpu/drm/amd/amdgpu/*.c|.h`:
  0 ocurrencias). `vi.c:675-676` son sus **únicos** consumidores. `ALCANZABLE_SIN_ROOT`
  está probado; que ese offset sea el SDMA status correcto en Polaris12 es
  `SEMANTICA_NO_CORROBORADA`. No lo use como prueba de nada.
- **(b) Coherencia cruzada.** `mmGRBM_STATUS = 0x2004` → byte `0x8010` es exactamente lo
  que el driver propio ya tiene anotado en `04-IMPLEMENTACION/rx550-driver/target_regs.h:81`.
  Es la confirmación independiente de que la convención índice-vs-byte de este catálogo es
  la que el proyecto ya usa, y de que los offsets de esta cabecera son los buenos.
- **(c) Los otros `mm*` de la lista se corroboran contra el propio driver de amdgpu.**
  `mmSRBM_STATUS` (`0x394`) lo lee `gfx_v8_0.c:4933` en la ruta VI; `mmGB_BACKEND_MAP` lo
  usa `gfx_v8_0_get_rb_active_bitmap` vía `mmCC_RB_BACKEND_DISABLE`/`mmGC_USER_RB_BACKEND_DISABLE`
  (`gfx_v8_0.c:3421-3422`). Por eso esas dos sí tienen corroboración de semántica.

### 2.2 Procedimiento para re-derivar el catálogo (reproducible, sin `grep`)

```python
import re
p='RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/vi.c'
L=open(p).readlines()
arr=[]
for ln in range(665,742):
    m=re.match(r'\s*\{(mm[A-Za-z0-9_]+)(?:\s*\+\s*([A-Za-z0-9_]+))?(?:\s*,\s*(true|false))?\},\s*$', L[ln-1])
    if m: arr.append((ln,m.group(1),m.group(2),m.group(3)))
cache=set(); in_sw=False
for ln in range(744,839):
    s=L[ln-1].strip()
    if re.match(r'^switch\s*\(reg_offset\)', s): in_sw=True; continue
    if in_sw:
        m=re.match(r'^case\s+(mm[A-Za-z0-9_]+):', s)
        if m: cache.add(m.group(1))
        if s=='}': in_sw=False
hw=[e for e in arr if e[1] not in cache]
print(len(arr), len(cache), len(hw))   # -> 76 54 22
```

---

## 3. Comparación con las implementaciones de otras generaciones

### 3.1 Qué implementaciones existen (medido, no supuesto)

`amdgpu_amdkfd_gfx_v10_0.c` **no existe**. El fichero es `amdgpu/amdkfd/amdgpu_amdkfd_gfx_v10.c` (junto a
`_v10_3`, `_v11`, `_v12`, `_v12_1`).

`.get_cu_occupancy` aparece en **exactamente cuatro** tablas `kfd2kgd` de todo
`drivers/gpu/drm/amd/`:

```
amdgpu/amdkfd/amdgpu_amdkfd_gfx_v9.c:1259        .get_cu_occupancy = kgd_gfx_v9_get_cu_occupancy   (Vega / GFX9)
amdgpu/amdkfd/amdgpu_amdkfd_gc_9_4_3.c:541       .get_cu_occupancy = kgd_gfx_v9_get_cu_occupancy   (GFX9.4.3)
amdgpu/amdkfd/amdgpu_amdkfd_aldebaran.c:183     .get_cu_occupancy = kgd_gfx_v9_get_cu_occupancy   (GFX10)
amdgpu/amdkfd/amdgpu_amdkfd_arcturus.c:419      .get_cu_occupancy = kgd_gfx_v9_get_cu_occupancy   (GFX10)
```

**Corrección al encargo y a MICROARCH-GFX8 §5.1:** no es «GFX9 o posterior». Las tablas
`gfx_v10` (`amdgpu_amdkfd_gfx_v10.c:1093`), `gfx_v10_3` (`:658`), `gfx_v11` (`:809`),
`gfx_v12` (`:370`) y `gfx_v12_1` (`:373`) **tampoco lo tienen**. Y las cuatro que sí lo
tienen **comparten la misma función** —incluidas dos de GFX10—. Eso es un precedente de
upstream relevante: una implementación de GFX9 reutilizada literalmente en GFX10. **No
es un precedente de que funcione en GFX8**; sólo muestra que upstream considera la
estructura portable entre generaciones.

### 3.2 El algoritmo de `kgd_gfx_v9_get_cu_occupancy`, campo por campo

`amdgpu_amdkfd_gfx_v9.c:1022-1078`, más `get_wave_count` (`:950-975`). Orden exacto:

| paso | qué lee | cita |
|---|---|---|
| 0 | `mutex` sobre `grbm_idx_mutex` + `srbm_mutex` | `v9.c:1033`, `:934-938` |
| 1 | `soc15_grbm_select(adev, 1, 0, 0, 0, inst)` → programa `GRBM_GFX_CNTL{PIPEID,MEID,VMID,QUEUEID}` | `v9.c:1034`; `soc15.c:363-373` |
| 2 | por cada SE: `amdgpu_gfx_select_se_sh(se_idx, 0, 0xffffffff, inst)` → `GRBM_GFX_INDEX` | `v9.c:1046`; `gfx_v8_0.c:3387-3409` (equivalente GFX8) |
| 3 | **`mmSPI_CSQ_WF_ACTIVE_STATUS`** → mapa de bits de colas por pipe | `v9.c:1047` |
| 4 | por cada `qidx` con bit activo **y** presente en `mec_bitmap[0].queue_bitmap` → `get_wave_count` | `v9.c:1055-1067` |
| 5 | dentro: `pipe = qidx / num_queue_per_pipe`, `queue_slot = qidx % num_queue_per_pipe`, re-`soc15_grbm_select`, y **`RREG32(mmSPI_CSQ_WF_ACTIVE_COUNT_0 + queue_slot)`** enmascarado con `SPI_CSQ_WF_ACTIVE_COUNT_0__COUNT_MASK` | `v9.c:962-967` |
| 6 | si `wave_cnt != 0`: **`mmCP_HQD_PQ_DOORBELL_CONTROL`** → `DOORBELL_OFFSET` | `v9.c:968-974` |
| 7 | `*max_waves_per_cu = cu_info.simd_per_cu * cu_info.max_waves_per_simd` | `v9.c:1076-1077` |
| 8 | restauran selectores y sueltan mutex | `v9.c:1071-1073` |

### 3.3 Y aquí está el punto que hay que corregir antes de emocionarse

**`SPI_CSQ_WF_ACTIVE_COUNT_x` NO es un contador por CU. Es un contador por COLA.**

La lectura de `v9.c:966` es `mmSPI_CSQ_WF_ACTIVE_COUNT_0 + queue_slot`, con
`queue_slot = queue_idx % adev->gfx.mec.num_queue_per_pipe` (`v9.c:963`). Y el comentario
del propio upstream lo dice sin ambigüedad (`v9.c:1009-1011`):

> *«Read (SPI_CSQ_WF_ACTIVE_COUNT_0 + queue_idx) register. It provides the number of waves
> that are in flight for the queue at specified index. The index ranges from 0 to 7.»*

Los 8 registros no son «CU 0..7 de la SH». Son «ranura de cola 0..7 del pipe
seleccionado». Por eso los índices van 0..7 y no «por cada CU de la placa» (que serían 8
en Tonga, pero la placa real tiene las cifras del VBIOS).

Consecuencia para R-NEW-64: **la columna Y que se puede construir es «oleadas en vuelo
por cola, agregadas», no «ocupación por CU» ni «ocupación por punto del barrido»**. El
eje X (ILP) sí se puede barrer; el eje Y es un número absoluto de waves in flight, que se
normaliza por el techo total. Eso **sigue siendo una matriz occupancy×ILP válida**, pero
con Y = `waves_in_flight / (nº_CU × waves_por_CU)`, no con Y = «CU ocupadas».

Y la conversión que hace KFD es exactamente esta, y produce un **número de CU, no un
porcentaje** (`kfd_process.c:322`):

```c
cu_cnt = (wave_cnt + (max_waves_per_cu - 1)) / max_waves_per_cu;   /* ceil */
```

Esto significa que `cu_occupancy` de KFD, aunque existiera en GFX8, **no daría el eje Y
de R-NEW-64 tal como está formulada** (daría un entero de CU, sin total al que dividir).
El eje Y necesita el agregado de `wave_cnt`, que es un nivel más abajo en el código.

### 3.4 Registro por registro: qué existe en GFX8 y qué no

| lo que `v9` usa | ¿existe en GFX8? | valor GFX8 | valor GFX9 | cita |
|---|---|---|---|---|
| `mmSPI_CSQ_WF_ACTIVE_STATUS` | **SÍ** | `0x24db` | `0x04db` | `gfx_8_0_d.h:1823` / `gc_9_0_offset.h:779` |
| máscara `…_STATUS__ACTIVE_MASK` | **SÍ** | `0xffffffff`, shift `0x0`, **sin subcampos** | `0xFFFFFFFFL`, shift `0x0` | `gfx_8_0_sh_mask.h:12809-12810` / `gc_9_0_sh_mask.h:4449-4450` |
| `mmSPI_CSQ_WF_ACTIVE_COUNT_0..7` (los 8) | **SÍ, los 8** | `0x24dc..0x24e3` | `0x04dc..0x04e3` | `gfx_8_0_d.h:1824-1831` / `gc_9_0_offset.h:781-795` |
| máscara `…_COUNT_n__COUNT_MASK` | **SÍ, los 8** | `0x7ff` (11 b) | `0x000007FFL` (11 b) | `gfx_8_0_sh_mask.h:12811-12826` / `gc_9_0_sh_mask.h:4454…` |
| campo `…_COUNT_n__EVENTS` | **NO existe en GFX8** | — | `0x07FF0000L` @ shift `0x10` | sólo `gc_9_0_sh_mask.h:4455`, `:4460`, … |
| `mmCP_HQD_PQ_DOORBELL_CONTROL` | **SÍ** | `0x3254` | `0x1254` | `gfx_8_0_d.h:645` / `gc_9_0_offset.h:2849` |
| máscara `DOORBELL_OFFSET` | **SÍ** | `0x7ffffc` @ shift `0x2` | — | `gfx_8_0_sh_mask.h:3939-3940` |
| `mmGRBM_GFX_INDEX` (SE/SH) | **SÍ** | `0xc200` | `0x2200` | `gfx_8_0_d.h:871` / `gc_9_0_offset.h:4913` |
| campos `GRBM_GFX_INDEX__{INSTANCE,SH,SE}_INDEX` | **SÍ, idénticos** | `0xff`@0, `0xff00`@8, `0xff0000`@16 | `0x000000FF`@0, `0x00FF0000`@16, … | `gfx_8_0_sh_mask.h:5685-5690` / `gc_9_0_sh_mask.h:19848-19850` |
| **`mmGRBM_GFX_CNTL` + campos `PIPEID/MEID/VMID/QUEUEID`** | **NO EXISTE EN GFX8** | — | `0x0022`; `0x3`@0, `0xc`@2, `0xf0`@4, `0x700`@8 | 0 ocurrencias de `GRBM_GFX_CNTL` en `gfx_8_0_d.h` **y** en `gfx_8_0_sh_mask.h`; en GFX9 `gc_9_0_offset.h:83`, `gc_9_0_sh_mask.h:499-506` |
| **sustituto en GFX8: `mmSRBM_GFX_CNTL`** | **SÍ** | `0x391` | — | `oss_3_0_d.h:88` (y `oss_3_0_d.h:167-168` para el par `_SELECT`/`_DATA` en `0xfa2e/0xfa2f`) |
| campos `SRBM_GFX_CNTL__{PIPEID,MEID,VMID,QUEUEID}` | **SÍ, layout idéntico** | `0x3`@0, `0xc`@2, `0xf0`@4, `0x700`@8 | — | `oss_3_0_sh_mask.h:417-424` |
| `adev->gfx.cu_info.{simd_per_cu,max_waves_per_simd}` | **SÍ, lo rellena GFX8** | `simd_per_cu = NUM_SIMD_PER_CU`, `max_waves_per_simd = 10`, `wave_front_size = 64` | idem | `gfx_v8_0.c:7072`, `:7121-7124`, invocado en `:3734` |
| `adev->gfx.mec.num_pipe_per_mec` / `num_queue_per_pipe` | **SÍ** | `4` / `8` | `4` / `8` | `gfx_v8_0.c:1910-1911` / `gfx_v9_0.c:2275-2276` |
| `adev->gfx.mec.num_mec` | **SÍ — Y DIFIERE** | **`2`** para `CHIP_POLARIS12` | `1` (Vega) | `gfx_v8_0.c:1893-1901` / `gfx_v9_0.c:2231-2234` |
| `adev->gfx.mec_bitmap[0].queue_bitmap` | **SÍ, se puebla** | bucles en `gfx_v8_0.c:1988-1989`, `bitmap_zero` en `:1293` | idem | `gfx_v8_0.c:1988-1989` |
| `select_me_pipe_q` (selector ME/PIPE/Q/VMID) | **SÍ, cableado** | `gfx_v8_0_select_me_pipe_q` → `vi_srbm_select` | `gfx_v9_0_select_me_pipe_q` | `gfx_v8_0.c:3411-3415`, `.select_me_pipe_q` en `gfx_v8_0.c:5255`; puntero en `amdgpu_gfx.h:353`, macro en `:561` |

**Lo que GFX8 no tiene, y la lista es tan informativa como la otra:**

1. **`mmGRBM_GFX_CNTL` no existe.** El selector de cola de GFX9 no se puede escribir con el
   mismo nombre en GFX8. El equivalente funcional en GFX8 es **`mmSRBM_GFX_CNTL`
   (`0x391`)** vía `vi_srbm_select` (`vi.c:578-587`), que escribe exactamente los mismos
   cuatro campos con las mismas máscaras y los mismos shifts (`oss_3_0_sh_mask.h:417-424`
   vs `gc_9_0_sh_mask.h:499-506`) — **a un offset distinto y con otro nombre**. Y esa vía
   **ya está en uso en el propio árbol para GFX8**: `amdgpu_amdkfd_gfx_v8.c:42-49`
   (`lock_srbm` → `WREG32(mmSRBM_GFX_CNTL, …)`) y `vi.c:578-587`.
2. **`…_COUNT_n__EVENTS` no existe en GFX8.** Los bits 11..31 de los 8 registros no están
   documentados como nada. GFX9 los usa. Copiar el layout de GFX9 tal cual no da error
   (la máscara `COUNT` es la misma), pero da una palabra cuyos bits altos no se pueden
   interpretar como GFX9.
3. **El MEC es otro.** GFX8 Polaris12 tiene **2** micro-engine engines (`gfx_v8_0.c:1901`);
   GFX9/Vega tiene **1** (`gfx_v9_0.c:2234`). El comentario de `v9.c:1050-1054` dice
   literalmente *«four pipes per each micro-engine, with each pipe mapping eight queues.
   This schema is true for GFX9 devices and must be verified for newer device families»*.
   Los números `4` y `8` coinciden con GFX8 (`gfx_v8_0.c:1910-1911`), **pero la dimensión
   ME dobla**, así que el barrido de GFX9 no cubre las colas de GFX8 sin cambios. Eso no
   lo verifica `v9.c`; lo verifica `gfx_v8_0.c`.
4. **`GRBM_STATUS_SE0..SE3` en la lista blanca son 4 registros fijos**, no un rango
   (§2). Con 4 SE en esta placa cuadra; con más no. `adev->gfx.config.max_shader_engines`
   viene del VBIOS (§0), así que **no está cerrado que 4 sea el número real**.

---

## 4. Qué haría nuestro propio driver

No lo implemento — el encargo dice que describo. Y `04-IMPLEMENTACION/rx550-driver/` **no
se ha tocado**. Leo lo que hay:

| pieza | estado en `04-IMPLEMENTACION/rx550-driver/` | cita |
|---|---|---|
| primitiva de lectura MMIO | **existe**: `struct rx550_mmio_map{base,size}`, `rx550_mmio_map_make`, `rx550_mmio_size_ok`, `rx550_mmio_map_in_window`, y el accessor con `readl` | `rx550_mmio.h:99-101`, `:118`, `:136`, `:147` |
| convención de unidades | **ya asentada**: el índice dword se multiplica por 4 antes de indexar el mapping. El propio fichero escribe el ejemplo `mmCP_RB0_RPTR → index 0x21c0 → byte 0x8700` | `rx550_mmio.h:7-18` |
| tabla de registros con índice **y** byte y procedencia | **existe**: `target_regs.h`, columnas `(nombre, índice, byte, ancho, acceso, …)` | `target_regs.h:72-155` (p. ej. `:81` `mmGRBM_STATUS 0x2004 0x8010 32 R`) |
| ventana MMIO | `rmmio_size = 0x40000` | `rx550_mmio.h:16`, `:23-26` |
| superficie ioctl a userspace | **no existe**: el propio driver lo dice — *«este componente no expone ioctls»* | `rx550_gart_boot.h:28-31` |

**Consecuencia medida:** `SPI_CSQ_WF_ACTIVE_STATUS` en índice `0x24db` → byte `0x936c`, y
`COUNT_0..7` → `0x9370..0x938c`. Todos dentro de `0x40000`. También dentro, para lo que
hace falta para seleccionar: `mmSRBM_GFX_CNTL` → `0xe44`, `mmGRBM_GFX_INDEX` → `0x30800`,
`mmCP_HQD_PQ_DOORBELL_CONTROL` → `0xc950`.

### 4.1 Lo que habría que añadir — descripción, no código

1. **Cinco filas en `target_regs.h`** (o donde corresponda), con el mismo formato de las
   9 que ya hay, con `conf` explícita:
   | nombre | índice | byte | ancho | acceso | conf |
   |---|---|---|---|---|---|
   | `mmSPI_CSQ_WF_ACTIVE_STATUS` | `0x24db` | `0x936c` | 32 | `R` | `EXISTE_EN_LA_CABECERA` (`gfx_8_0_d.h:1823`); `ALCANZABLE_SIN_ROOT` = **NO** (§1.3) |
   | `mmSPI_CSQ_WF_ACTIVE_COUNT_0..7` | `0x24dc..0x24e3` | `0x9370..0x938c` | 32 | `R` | ídem (`gfx_8_0_d.h:1824-1831`) |
   | `mmSRBM_GFX_CNTL` | `0x391` | `0xe44` | 32 | `RW` | usado ya por `vi_srbm_select` (`vi.c:586`) y por `amdgpu_amdkfd_gfx_v8.c:48`. **Es un `RW`, no un `R`**: escribirlo cambia el enrutamiento de lecturas del propio bus. Eso es lo que hace que esto sea `CONTROLLED_WRITE`, no `READ_ONLY`. |
   | `mmGRBM_GFX_INDEX` | `0xc200` | `0x30800` | 32 | `RW` | igual: `gfx_v8_0.c:3408`. Hay que **restaurar a broadcast** al salir, como hace `gfx_v8_0.c:3579`. |
   | `mmCP_HQD_PQ_DOORBELL_CONTROL` | `0x3254` | `0xc950` | 32 | `R` | `gfx_8_0_d.h:645` |

2. **Un instrumento de investigación**, no producción: el módulo ya sabe mapear BAR5 y
   leer (`rx550_mmio.h`). Lo que **no** tiene es por dónde sacar el resultado, porque no
   expone ioctls. Habría que elegir **una** de estas tres superficies, y la elección
   cambia el perfil de riesgo:
   - un `procfs`/`sysfs` propio de sólo lectura (modo `0444`) — entrega el dato a
     cualquier proceso del usuario, sin privilegios;
   - un ioctl nuevo (`READ_ONLY` en el contrato) — necesita `CAP_SYS_ADMIN` o una
     política de permisos, y es superficie nueva;
   - imprimir dentro del propio módulo — no requiere superficie nueva, pero el resultado
     sólo es observable por `dmesg`, que este proyecto tiene prohibido como canal de
     lectura.

   Nada de esto lo decido aquí (§5).

3. **La secuencia de lectura**, si el instrumento se escribe, en el orden de §3.2 pero con
   el selector de GFX8. Y con un **registro en «estado antes / estado después»**, porque
   los dos selectores se quedan programados si el instrumento no los restaura.

### 4.2 Qué hace falta para convertir el número bruto en «ocupación por ola»

Esto es lo que `v9.c:1076-1077` y `kfd_process.c:322` hacen, y para GFX8 **el numerador y
el denominador existen por escrito**:

- **Numerador** `waves_in_flight` = suma de `RREG32(mmSPI_CSQ_WF_ACTIVE_COUNT_0 + queue_slot)`
  sobre las colas del proceso, usando el bit de `SPI_CSQ_WF_ACTIVE_STATUS` para saber
  cuáles están ranuradas. Ojo: **agregado por cola, no por CU** (§3.3).
- **Denominador** `max_waves_per_cu` = `cu_info.simd_per_cu × cu_info.max_waves_per_simd`,
  exactamente `v9.c:1076-1077`. Para GFX8 los dos factores los fija `gfx_v8_0.c:7121-7122`:
  `NUM_SIMD_PER_CU` y **10**. Con `wave_front_size = 64` (`gfx_v8_0.c:7124`). El producto
  es el mismo que usa KFD para GFX9.
- **Atribución a un proceso** (el paso que separa esto de «GPU ocupada»): `v9.c:968-974`
  lee `mmCP_HQD_PQ_DOORBELL_CONTROL` bajo el selector de la cola y compara
  `DOORBELL_OFFSET` con las colas del proceso (`kfd_process.c:308-319`,
  `kfd_dqm_is_queue_in_process`). En nuestro módulo, el doorbell de nuestro propio ring
  es conocido por construcción, así que este paso es **más simple que en KFD**: no hay que
  filtrar, hay que sumar las nuestras y descartar el resto. Ojo con el aviso de
  `v9.c:990-996`: entre leer el VMID y leer el PASID un remapeo puedefalsear la cuenta.
  Es un confounder conocido y documentado, no una sorpresa.
- **Para R-NEW-64**: `Y = waves_in_flight / (nº_CU_activos × max_waves_per_cu)`. El
  denominador **agregado** (`nº_CU × waves_por_CU`) necesita el nº de CU, que viene del
  VBIOS (`amdgpu_atombios.c:744-750`), no de una constante.

### 4.3 Lo que NO se puede decidir sin hardware (registrado como abierto, no como planes)

| # | cuestión | por qué no se puede cerrar aquí | qué observación la cerraría |
|---|---|---|---|
| 1 | ¿`mmSRBM_GFX_CNTL` enruta las lecturas de `SPI_CSQ_WF_ACTIVE_*` en GFX8? | El offset y los campos existen (`oss_3_0_d.h:88`, `oss_3_0_sh_mask.h:417-424`) y el layout coincide campo a campo con `GRBM_GFX_CNTL` de GFX9 (`gc_9_0_sh_mask.h:499-506`). **Coincidencia de layout no es prueba de enrutamiento.** El enum `SRBM_GFX_CNTL_SEL` lista `GRBM = 3` (`oss_3_0_enum.h:255`), lo que hace plausible que SPI (dentro de GRBM/GC) esté cubierto, pero es un enum de cliente, no de bloque. | Escribir dos `QUEUEID` distintos en `mmSRBM_GFX_CNTL` y leer `COUNT_x`: si el valor **cambia**, el enrutamiento está probado. Si sale idéntico, no. Este es **el discriminante** y no requiere más que una lectura y dos escrituras controladas. |
| 2 | ¿los bits de `STATUS` se mapean a 4 pipes × 8 colas en GFX8, o a otra cosa? | `ACTIVE_MASK` es `0xffffffff` sin subcampos en ambas generaciones (`gfx_8_0_sh_mask.h:12809-12810` vs `gc_9_0_sh_mask.h:4449-4450`). El comentario de `v9.c:1050-1054` **advertencia explícita de no transferir**. | Lo mismo que #1, con `STATUS` en lugar de `COUNT`: el mapa de bits debe cambiar al cambiar `PIPEID`. |
| 3 | ¿cuántos motores de micro-engine (ME), SH y CU hay realmente? | Del VBIOS (`gfx_v8_0.c:1683` → `amdgpu_atombios.c:744-750`). `NOT_FOUND` en el corpus. | Leer `amdgpu_gca_config` en debugfs (root) — `MICROARCH-GFX8.md` §5 ya lo señala como la vía de una lectura — o parsear la tabla `GFX_Info` del VBIOS. |
| 4 | ¿los bits 11..31 de `COUNT_x` en GFX8 son algo? | GFX8 no los documenta; GFX9 los llama `EVENTS` (`gc_9_0_sh_mask.h:4455`). No se puede heredar el nombre. | Variar la carga y observar esos bits. |
| 5 | ¿el `COUNT` incluye o excluye la oleada en el slot de espera? | Semántica de firmware; `COMPUTE_TMPRING_SIZE.WAVES` es lo que la dimensiona (`gfx_8_0_sh_mask.h:8365-8366` según `MICROARCH-GFX8.md`) y nadie lo programa. | Comparar `COUNT` con una serie conocida de oleadas Submitidas. |
| 6 | ¿el ioctl `AMDGPU_INFO` pide privilegios? | `drm_ioctl.c` **no está en el corpus**. | Una ejecución real. No se hará aquí (reabre la GPU). |

---

## 5. La decisión que no es mía

**El enunciado del veredicto es: la lectura sólo es posible desde el módulo propio.**

De ahí sale, por una cadena que no me corresponde recorrer:

1. **Para leerlo sin `debugfs` hay que escribir en la placa.** `mmSRBM_GFX_CNTL` y
   `mmGRBM_GFX_INDEX` son `RW` y hay que **programarlos** para seleccionar la fila antes de leer.
   Leer `SPI_CSQ_WF_ACTIVE_*` no es `READ_ONLY`: es `CONTROLLED_WRITE` (grafo de §42).
   Aquí no hay `BACKUP` que la haga segura — un backup de un selector de enrutamiento es
   sólo información, no reversibilidad.
2. **Cualquier ruta que lo haga desde el driver de amdgpu requiere privileged.** El ioctl
   (`amdgpu_drv.c:3057`, `DRM_AUTH`) y el debugfs (`amdgpu_debugfs.c:1744`, modo `0400`)
   son los dos, y ambos además **despiertan la GPU** (`amdgpu_kms.c:1453` y
   `amdgpu_debugfs.c:118`). Con `boot_vga = 1`, eso es despertar el adaptador de la
   pantalla.
3. **El módulo propio tampoco expone superficie de lectura todavía** — no expone ioctls
   (`rx550_gart_boot.h:28-31`) — así que además hay que **elegir una superficie** (§4.1), y
   esa elección tiene consecuencias de permisos distintas según cuál sea.

**La decisión es de nivel de autorización, y es de quien la tiene:**

> ¿Se autoriza una escritura controlada de selectores de enrutamiento
> (`mmSRBM_GFX_CNTL`, `mmGRBM_GFX_INDEX`) sobre el adaptador **de la pantalla de
> arranque**, y con qué superficie de salida (procfs de sólo lectura / ioctl /
> `dmesg`), y con qué condición de abortación?

**No la tomo y no la pregunto.** La dejo enunciada con su causa. El riesgo que queda
asociado, sin heroicidades: un `QUEUEID`/`PIPEID` mal programa deja el bloque SRBM
enrutando a otro cliente hasta el siguiente `vi_srbm_select(adev, 0,0,0,0)` — que el
propio driver hace en `gfx_v8_0.c:4599-4601`, `:4981-4983`, `:5076-5078`, o sea en cada
doorbell de anillo — así que el estado no permanece corrupto más allá del próximo
submission, **pero** una lectura de occupancy hecha en medio puede devolver basura sin
que nada avise. Ése es el confounder a declarar antes de usar cualquier número que salga
de ahí.

Lo que **sí** es una consecuencia de este nodo y no necesita autorización: el sitio donde
se busca ha cambiado. Ya no es «una vía de userspace que no existe». Es, exactamente y en
este orden: **(1)** un discriminante de dos escrituras y una lectura que cabe en un módulo
propio; **(2)** el número de CU, que sale del VBIOS y se puede leer sin escribir nada;
**(3)** sólo después, el resto de la matriz.

---

## 6. Registro de lo que este nodo cambió

| afirmación heredada | veredicto |
|---|---|
| «76 entradas en `vi_allowed_read_registers[]`» | **CONFIRMADA** (`vi.c:666-741`) |
| «53 caché / 21 hardware» | **CORREGIDA** → **54 / 22**, por parseo literal de los dos `switch` (`vi.c:753-836`) |
| «`default: return RREG32` en `vi.c:834-835`» | **CONFIRMADA** |
| «349 registros PERF/COUNTER en `gfx_8_0_d.h`, cero en la lista» | **CONFIRMADA y con definición**: unión `PERF` ∪ `COUNTER` = 346 ∪ 312 = **349**; intersección con los 75 nombres de la lista = **0** |
| «`cu_occupancy` ausente en `amdgpu_amdkfd_gfx_v8.c:592-609`» | **CONFIRMADA**; la tabla acaba en `:610` con `};` y son 14 entradas |
| «`.get_cu_occupancy` existe en 4 implementaciones, todas GFX9 o posterior» | **CORREGIDA**: existen en 4 tablas, pero `gfx_v10`, `gfx_v10_3`, `gfx_v11`, `gfx_v12`, `gfx_v12_1` **no** la tienen. Las 4 comparten `kgd_gfx_v9_get_cu_occupancy`, dos de ellas de GFX10 |
| «`amdgpu_amdkfd_gfx_v10_0.c`» | **NO EXISTE**; es `amdgpu_amdkfd_gfx_v10.c` |
| «`COUNT_0..7` = ocupación por CU» | **CORREGIDA**: es **por ranura de cola** (`v9.c:963-967`, comentario `:1009-1011`). KFD lo convierte a **nº de CU** con `ceil` (`kfd_process.c:322`), no a porcentaje |
| «geometría 4×8» | **`NOT_FOUND` / `NOT_TRAZADA`**: para Polaris12 sale del VBIOS (`gfx_v8_0.c:1683` → `amdgpu_atombios.c:744-750`), no de una constante |
| «no está en `debugfs`» | **MATIZADO**: no hay *filtro de lista blanca* en `debugfs` (`amdgpu_debugfs.c:152` lee cualquier offset), pero el fichero es `0400` (`amdgpu_debugfs.c:1744`) y el lector **despierta la GPU** (`:118`) |

### FALTANTE

- `drm_ioctl.c` no está en el corpus ⇒ **no** pude verificar la semántica de `DRM_AUTH`
  para `AMDGPU_INFO`. `NOT_TRACED`.
- No medí el modo del montaje de `/sys/kernel/debug` ni el modo efectivo del fichero en
  esta máquina (prohibición explícita de este nodo). El dato del corpus (`0400`) basta
  para el veredicto, pero la leg 2 queda con un hueco de medición.
- No hay ninguna lectura real de hardware en este nodo. Todo lo anterior es estático.

### BLOQUEO

Ninguno para la pregunta planteada: está cerrada con estado `PROVEN` (los registros
existen) y `PROVEN` (no hay vía sin root), y con `NOT_DETERMINED` honesto para el
enrutamiento GFX8 de `mmSRBM_GFX_CNTL`.

### ACCIÓN DISCRIMINANTE

**Una sola, y es la que decide la siguiente transición**: con el módulo propio, para un
mismo SE, escribir `QUEUEID = 0` y `QUEUEID = 1` en `mmSRBM_GFX_CNTL` (`0x391`) y leer
`mmSPI_CSQ_WF_ACTIVE_STATUS` (`0x24db`) y `mmSPI_CSQ_WF_ACTIVE_COUNT_0` (`0x24dc`).
Si los valores **difieren**, el enrutamiento SRBM cubre SPI en GFX8 y §4 es ejecutable tal
como está escrito. Si son **idénticos**, el selector no cubre este bloque en GFX8, la
columna Y de R-NEW-64 se cae en esta placa, y el sitio donde se busca vuelve a moverse.
Requiere autorización de escritura controlada (§5). No la pido.

### STATE_AFTER

- `SPI_CSQ_WF_ACTIVE_*` en GFX8: `EXISTE_EN_LA_CABECERA` = `PROVEN` (`gfx_8_0_d.h:1823-1831`,
  máscaras `gfx_8_0_sh_mask.h:12809-12826`).
- `SPI_CSQ_WF_ACTIVE_*` alcanzable sin root hoy: `PROVEN_ABSENT` en el ioctl (∅ en
  `vi.c:666-741`); `PROVEN_ABSENT` en sysfs/fdinfo; `PROVEN_ABSENT` en KFD (el atributo no
  se crea, `kfd_process.c:601-604`); en debugfs `ALCANZABLE` pero **modo `0400`** y
  despierta la GPU.
- Catálogo de lo que esta tarjeta deja leer sin root: **22 entradas de hardware**
  (§2), con 5 de ellas de offsets no corroborados semánticamente.
- Selector de cola para GFX8: `mmSRBM_GFX_CNTL` existe, con layout idéntico a
  `GRBM_GFX_CNTL` de GFX9, y ya se usa en el árbol (`vi.c:578-587`,
  `amdgpu_amdkfd_gfx_v8.c:42-49`). Que enrute SPI: **`NOT_DETERMINED`**.
- Eje Y de R-NEW-64: implementable **como waves-in-flight agregado por cola**, no como
  ocupación por CU. `mmCP_HQD_PQ_DOORBELL_CONTROL` existe en GFX8 (`gfx_8_0_d.h:645`),
  lo que hace la atribución a proceso viable desde nuestro propio módulo.
- Geometría de la placa: `NOT_FOUND` en el corpus. Relleno desde VBIOS.

### INPUT_HASHES

```
RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/vi.c
  sha256 c554b770b71edb8476f29ca420fb71bf020cde85e556781058ea3883d746820f
  (idéntico en RESEARCH/baseline/linux-7.1.3 y rx550-upstream-7.2.8/linux-7.2.8)
RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/gfx_v8_0.c        :1681-1695 :1893-1911 :3387-3415 :3421-3422 :5255 :7072-7125
RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/gca/gfx_8_0_d.h        2633 #define mm*
RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/gca/gfx_8_0_sh_mask.h  SPI_CSQ 18 defines
RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/oss/oss_3_0_d.h       :88 :90-92 :303
RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/oss/oss_3_0_sh_mask.h  :417-424
RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/gc/gc_9_0_offset.h    :83 :779-796 :2849 :4913
RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/gc/gc_9_0_sh_mask.h     :499-506 :4448-4488 :19848-19853
RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/amdgpu_amdkfd_gfx_v9.c  :950-975 :978-1021 :1022-1078 :1233-1259
RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdkfd/kfd_process.c       :265-325 :601-604
RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/amdgpu_debugfs.c    :46-72 :73-186 :191-195 :229-315 :1694-1728 :1736-1751
RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/amdgpu_kms.c        :875-930 :1435 :1453
RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/amdgpu_drv.c        :3057 :3076 :3102
RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/amdgpu_atombios.c    :744-750
RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/soc15.c             :363-373 :381-402 :436-457
uname -r = 7.1.3-200.nobara.fc44.x86_64
```

### OUTPUT_HASH

```
CU-OCCUPANCY-WIRING.md   (este fichero — sha registrado por el coordinador al incorporarlo)
```

### NEXT_NODE

El que corresponda a la decisión de §5. No lo selecciono.