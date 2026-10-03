# 306 · `mmCONFIG_MEMSIZE` existe: el hallazgo 279 es un `PROVEN` sobre un patrón que no puede coincidir

```
CLASSIFICATION=VERIFICATION+CORRECTION · TRACK=STATIC · WORK_CLASS=READ_ONLY/EVIDENCE
CORPUS=RESEARCH/working/linux-7.1.3 (SUBTREE PARCIAL) · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WRITE_EXECUTION=NONE · MODIFICATIONS_CORPUS=0 · MODIFICATIONS_PROPIOS=1 (este fichero + 1 instrumento)
RUNTIME=NOT_RUN · GPU INTACTA
INSTRUMENTO=03-EXPERIMENTOS/ep08-mc-vram-geometry/mc_geometry.c (29 aserciones, 0 fallos)
CORRECTS=279-rx550-mc-config-memsize-no-es-un-registro.md
CORRECTS=199-seccion-f-la-base-de-vram-y-el-agujero.md
CONTINUES=164-lexa-pro-y-el-gart-fija-mc-mask.md
AUTORIA=AGENT-08 (MC / VRAM / MEMORY CONTROLLER)
PENDIENTE=FBBASE-ASIC | HALLAZGO=306-mmconfig-memsize-existe-el-279-refutado-y-el-199-tiene-una-igualdad-falsa.md | ESTADO=NOT_OBSERVED
  | NECESITA=/sys/bus/pci/devices/0000:01:00.0/resource5 (mmap del BAR5)
  | ALCANZABLE_SIN_ROOT=NO_MEDIDO
PENDIENTE=CONFIGMEMSIZE-ASIC | HALLAZGO=306-mmconfig-memsize-existe-el-279-refutado-y-el-199-tiene-una-igualdad-falsa.md | ESTADO=NOT_OBSERVED
  | NECESITA=/sys/bus/pci/devices/0000:01:00.0/resource5 (mmap del BAR5)
  | ALCANZABLE_SIN_ROOT=NO_MEDIDO
PENDIENTE=FBTOP-SEM | HALLAZGO=306-mmconfig-memsize-existe-el-279-refutado-y-el-199-tiene-una-igualdad-falsa.md | ESTADO=NOT_DETERMINED
  | NECESITA=/sys/bus/pci/devices/0000:01:00.0/resource5 (mmap del BAR5)
  | ALCANZABLE_SIN_ROOT=NO_MEDIDO
```

## Qué resuelve

**Un hallazgo del registro con tres afirmaciones `PROVEN` que el corpus
refuta, y una igualdad `PROVEN_DERIVED` de `199` que es falsa.** `PROVEN`.

El mecanismo del error de `279` es lo que lo hace instructive: **el `grep` que
usó como evidencia no podía encontrar el símbolo ni aunque el símbolo
existiera.** No es una búsqueda que salió vacía; es una búsqueda
incapaz de tener éxito. `PROVEN`.

## 1 · La refutación de `279`

### 1.1 · Lo que `279` afirma, y lo que hay

| afirmación de `279` | estado en `279` | veredicto |
|---|---|---|
| `CONFIG_MEMSIZE` no aparece en ningún `.c` ni `.h` de amdgpu | `PROVEN` | **`REFUTED`** |
| `0x150a` "pertenece a otro bloque" (BIF/DCN), no a GMC | `PROVEN` | **`REFUTED`** — es *justamente* el bloque correcto |
| El tamaño de VRAM lo dice el firmware, no el hardware | `CONCLUSIÓN` | **`REFUTED`** — lo dice un registro de hardware |
| `mmMC_VM_FB_LOCATION = 0x809` | `PROVEN` | `PROVEN` — **acertó** |
| `RX550_MC_CONFIG_MEMSIZE = 0x150a` es una constante muerta y engañosa | `PROVEN` | **`REFUTED`** — la constante es correcta |

### 1.2 · El símbolo existe y lo lee el driver de GFX8

```
amdgpu/gmc_v8_0.c:560      tmp = RREG32(mmCONFIG_MEMSIZE);
```

Y el mismo símbolo en otras familias, que `279` también dijo que no existían:

```
amdgpu/gmc_v7_0.c:374-375   adev->gmc.mc_vram_size = RREG32(mmCONFIG_MEMSIZE) * 1024ULL * 1024ULL;
amdgpu/gmc_v6_0.c:318-319   (identico)
amdgpu/cik.c:1448, vi.c:977, si.c:1458   RREG32(mmCONFIG_MEMSIZE)
```

`PROVEN`. El símbolo aparece en seis ficheros `.c` del driver, en cuatro
generaciones.

### 1.3 · El valor `0x150a` es el correcto, y `279` tenía la prueba delante

```
amdgpu/gmc_v8_0.c:38        #include "bif/bif_5_0_d.h"
include/asic_reg/bif/bif_5_0_d.h:33   #define mmCONFIG_MEMSIZE   0x150a
```

**El include es incondicional** —no está dentro de ningún `#if`— así que la
cadena se resuelve leyendo dos líneas, sin evaluar ramas de compilación ni
necesitar el árbol completo del kernel. `PROVEN`.

Y el bloque es BIF **a propósito**: `mmCONFIG_MEMSIZE` es un registro de
configuración del bus, no del controlador de memoria. Vive en
`0x1500`-`0x150c`, junto a `mmBUS_CNTL`, `mmCONFIG_CNTL`,
`mmCONFIG_APER_SIZE`. Es coherente con el resto de su bloque.

> **⇒ La evidencia que `279` reunió era la prueba a favor, y la leyó al revés.**
> Escribió: *«busqué `0x150a` en todo `asic_reg` y sale en `bif_5_1_d.h`,
> `dcn/*_offset.h`»*, y de ahí concluYO *«`0x150a` es un offset válido **de
> otra cosa**»*. Pero **`bif_5_1_d.h` es precisamente donde vive
> `mmCONFIG_MEMSIZE`.** Encontrar el offset en el header del bloque no es
> prueba de que el offset sea de otro bloque: es prueba de que es del bloque
> correcto. `279` discriminated mal la dirección del argumento.

### 1.4 · El mecanismo: un patrón que no puede coincidir

La evidencia registrada de `279` es:

```
grep -rn "MC_CONFIG_MEMSIZE" amdgpu/*.c amdgpu/*.h    -> nada
```

El símbolo se llama **`mmCONFIG_MEMSIZE`**. La cadena buscada
`MC_CONFIG_MEMSIZE`:

- **no** es subcadena de `mmCONFIG_MEMSIZE` — para serlo tendría que empezar
  en el índice 1, y ahí hay `m`, no `M`;
- por tanto ese `grep` devuelve **cero hallazgos siempre**, haya o haya el
  símbolo.

De cero hallazgos, `279` concluyó *«no aparece en ningún `.c` ni `.h`»*, que
es una afirmación de **ausencia** construida sobre una búsqueda que no puede
tener éxito. `PROVEN`.

> **La lección es la de `199` §4, la misma, y en la variante más dura: allí
> el patrón era correcto y la conclusión estaba escrita antes de mirar; aquí
> el patrón es INCORRECTO, así que no hay forma de que la salida haya podido
> contradecirlo.** Un `grep` que no puede coincidir no es evidencia débil: es
> un instrumento que no puede fallar, y un instrumento que no puede fallar no
> puede sostener un `PROVEN`.

### 1.5 · La tercera refutación: el origen del tamaño de VRAM

`279` afirmó: *«El tamaño de VRAM lo dice el firmware, no el hardware»*, y
para sostenerlo Intensity `amdgpu_gmc.c:61`:

```c
u64 vram_size = adev->gmc.xgmi.node_segment_size * adev->gmc.xgmi.num_physical_nodes;
```

**Esa línea está dentro de `amdgpu_gmc_pdb0_alloc` (`amdgpu_gmc.c:57`)** —el
asignador del *page directory block 0*—, no de ninguna función de
descubrimiento de VRAM. Y la función que sí se llama en el descubrimiento,
`amdgpu_gmc_get_vram_info` (`amdgpu_gmc.c:1758`), devuelve **anchura, tipo y
fabricante**: ningún tamaño. `PROVEN`.

> **⇒ Para GFX8 el tamaño sale de un registro de hardware: `mmCONFIG_MEMSIZE
> × 1 MiB`, leído en `gmc_v8_0_mc_init` (`gmc_v8_0.c:560-567`).** `PROVEN`.
> El orden importa y es comprobable: `gmc_v8_0_mc_init` (`:510`) fija
> `mc_vram_size` en `:567`, y `gmc_v8_0_vram_gtt_location` —que la consume—
> se llama en `:609`, **99 líneas después, en la misma función**.

### 1.6 · Consecuencia para el driver del proyecto

`RX550_MC_CONFIG_MEMSIZE 0x150a` (`07-DRIVER/kernel/rx550_mc.h:73`) es
**correcto**. `279` lo declaro muerto y lo senalo como trampa para quien lo
consulte, y de ese modo lo desacredito: es el mismo argumento que aplico a

`RX550_MC_FB_LOCATION 0x809`, que si acerto. Una constante muerta convence
igual que una muerta. `PROVEN`.

`rx550_mc_vram_desde_registros(fb_location, config_memsize, out)` recibe
`config_memsize` como **parámetro**, y el registro que lo produciría existe y
es legible en un PF. **El camino del driver hacia `VRAM_END` está completo, no
roto.** `PROVEN`.

## 2 · Una corrección a `199`

`199` cierra su §F con, en `PROVEN_DERIVED`:

> *«`gart_end + gart_size = 0x000000FF1FFFFFFF = mc_mask + 1`»*

El primer miembro es correcto. **La igualdad es falsa.**

| magnitud | valor |
|---|---|
| `gart_end + gart_size` | `0x00FF1FFFFFFF` |
| `mc_mask + 1` | `0x010000000000` |
| iguales | **NO** |
| faltan | `0xE0000001` = **3,50 GiB** |

`PROVEN`. Y no es un error de redondeo mío: la diferencia tiene una causa
identificada y medible.

La colocación `BEST_FIT` pone el GART en
`R = max_mc_address − gart_size + 1 = 0x00FFF0000000`, y luego lo **alinea
hacia abajo a 4 GiB**, lo que lo baja a `0x00FF00000000`. Ese alineado deja
al GART exactamente **un residuo de la alineación** por debajo del tope:

| magnitud | valor |
|---|---|
| `R mod 4 GiB` (el residuo) | `0x00F0000000` |
| `mc_mask − gart_end` | `0x00F0000000` |
| iguales | **sí** |

`PROVEN_DERIVED`. **El invariante que sí se cumple es
`mc_mask − gart_end == R mod 4 GiB`**, no «el GART termina en el tope».

> **⇒ Y hay 3,50 GiB de espacio del MC por encima del GART que nadie mapea.**
> No es decorativo: es dirección MC decodificable y sin asignar, y es
> consecuencia directa de que el GART tenga que empezar en un límite de 4 GiB.
> `PROVEN_DERIVED`.

**Por qué survived `199`:** los dos números `0x00FF1FFFFFFF` y `0x00FFFFFFFFFF`
se parecen mucho —ambos empiezan por `FF`— y por eso la igualdad rota pasó
desapercibida. Es la misma clase que el error que `199` él mismo corrigió en su
propio §2: *«un número correcto al que se le atribuye el origen equivocado,
que hereda la autoridad del sitio del que se dice que viene»*. Aquí el número
no es correcto y la igualdad no se puede leer de un vistazo.

## 3 · Observación nueva: `FB_TOP` existe en la cabecera y no tiene consumidor en GFX8

```
gmc/gmc_8_1_sh_mask.h:3969   MC_VM_FB_LOCATION__FB_BASE_MASK   0xffff        SHIFT 0x0
gmc/gmc_8_1_sh_mask.h:3971   MC_VM_FB_LOCATION__FB_TOP_MASK    0xffff0000    SHIFT 0x10
```

Es **un** registro de 32 bits con dos campos: `FB_BASE` en los bits 0-15 y
`FB_TOP` en los 16-31. Para GFX8, `gmc_v8_0.c:417` lee **sólo** `& 0xFFFF`.

Los únicos consumidores de `FB_TOP` en todo `amdgpu/*.c` son cuatro, y los
cuatro son de SOC15:

```
amdgpu/mmhub_v1_0.c:45, mmhub_v1_7.c:45, mmhub_v1_8.c:46   -> SOC15
amdgpu/mmhub_v9_4.c:48                                     -> SOC15
```

**Ninguno corre en GFX8.** `PROVEN_ABSENT` *dentro del alcance `amdgpu/*.c`
del corpus*, que es un negativo con alcance porque enumeré el conjunto
completo de consumidores.

Y hay un dato que hace la observación discriminante y no trivial: `FB_BASE`
ocupa los **bits 24-39** de la dirección del MC, y `FB_TOP` ocuparía los
**bits 40-55** — por encima del `mc_mask` de 40 bits (`gmc_v8_0.c:1133`,
`0xffffffffff`, *«40 bit MC»*). **En un MC de 40 bits no hay bits 40-55 que
extender.** luego en esta ASIC `FB_TOP` es o bien vestigial, o bien su
semántica no es extender la dirección.

Qué lo hace plausible lo dice el propio driver, en la rama de escritura que
sólo corre en una VF (`gmc_v8_0.c:474-478`):

```c
tmp  = ((adev->gmc.vram_end   >> 24) & 0xFFFF) << 16;   /* FB_TOP    = vram_end   */
tmp |= ((adev->gmc.vram_start >> 24) & 0xFFFF);         /* FB_BASE   = vram_start */
WREG32(mmMC_VM_FB_LOCATION, tmp);
```

**⇒ Los dos campos son `vram_start` y `vram_end`, en unidades de 16 MiB.** Y en
esa misma rama hay un comentario del propio upstream que conviene no perder:
`/* XXX double check these! */`, sobre las escrituras de
`mmHDP_NONSURFACE_*`. `OBSERVATION`.

> **Estado de `FB_TOP` en esta placa: `NOT_DETERMINED`.** Su valor real exige
> leer `mmMC_VM_FB_LOCATION` del ASIC. Es lectura de nivel 2, es la receta de
> `166`, y está pendiente. Lo que sí es `PROVEN` es que **amdgpu, en GFX8, no
> lo lee ni lo escribe en un PF**.

## 4 · El modelo, con las clases separadas

### `FACT` (texto del driver, cadena de includes resuelta)

| hecho | producer |
|---|---|
| `mmCONFIG_MEMSIZE = 0x150a` | `bif/bif_5_0_d.h:33`, incluido por `gmc_v8_0.c:38` |
| `mmMC_VM_FB_LOCATION = 0x809`, `FB_BASE` mask `0xffff` shift `0` | `gmc/gmc_8_1_d.h:281`, `gmc_8_1_sh_mask.h:3969-3970` |
| `mc_mask = 0xFFFFFFFFFF`, 40 bits | `gmc_v8_0.c:1133` |
| `AMDGPU_GMC_HOLE_START` es una **ternaria**, no una constante | `amdgpu_gmc.h:36-37` |
| `max_mc_address = min(mc_mask, HOLE_START−1)` | `amdgpu_gmc.c:299` |
| `gart_start` alineado a 4 GiB; `gart_end = gart_start + gart_size − 1` | `amdgpu_gmc.c:332-333` |
| `fb_start = vram_start`, `fb_end = vram_end` cuando `num_physical_nodes == 0` | `amdgpu_gmc.c:232-234` |

### `OBSERVATION` (kernel log, NIVEL 2, lectura)

```
VRAM: 2048M 0x000000F400000000 - 0x000000F47FFFFFFF (2048M used)
GART: 256M 0x000000FF00000000 - 0x000000FF0FFFFFFF
```

### `DERIVATION` (recalculada por el instrumento, cotejada)

| magnitud | cálculo | valor | observado |
|---|---|---|---|
| `vram_start` | `FB_BASE << 24`, `FB_BASE = 0xF400` | `0x000000F400000000` | **coincide** |
| `vram_end` | `vram_start + 2048 MiB − 1` | `0x000000F47FFFFFFF` | **coincide** |
| `max_mc_address` | `min(0xFFFFFFFFFF, HOLE_START−1)` | `0x00FFFFFFFFFF` | — |
| `gart_start` | `(max_mc_address − 256 MiB + 1) & ~(4 GiB−1)` | `0x000000FF00000000` | **coincide** |
| `gart_end` | `gart_start + 256 MiB − 1` | `0x000000FF0FFFFFFF` | **coincide** |
| `mc_mask − gart_end` | `0x00FFFFFFFFFF − 0x00FF0FFFFFFF` | `0x00F0000000` | = residuo |

### `DERIVATION` del entregable, entera

- **VRAM_START** = `0x000000F400000000`, múltiplo de 16 MiB **por
  representación** (el campo es de 16 bits con desplazamiento 24). `PROVEN`.
- **VRAM_END** = `0x000000F47FFFFFFF`, borde **incluido**. `PROVEN`.
- **MC base / tope**: `mc_mask = 0x00FFFFFFFFFF`; espacio direccionable
  `2^40` = 1 TiB. `PROVEN`.
- **max_mc_address** = `0x00FFFFFFFFFF` = `mc_mask`. El **hueco no entra**:
  las dos ramas de la ternaria (`0x0100000000000000` y `0x0000800000000000`)
  son **mayores** que `mc_mask`, así que el `min` es siempre `mc_mask` en esta
  placa. `PROVEN`.
- **Address hole**: `0x0000800000000000`–`0x00FFFFFFFFFFFFFF` es el hueco del
  espacio de VA de 48 bits; **no correspondiente** a ninguna dirección MC de
  esta placa. `PROVEN`.
- **BAR visibility**: `visible_vram_size = aper_size` (256 MiB, BAR Mandatory),
  y `amdgpu_vram_limit = UINT_MAX` / `vis_vramlimit` sin valor por defecto
  **no recortan nada** (`amdgpu_gmc.c:217-229`, `amdgpu_drv.c:152`). De ahí que
  el log diga `2048M used` y no la cifra recortada. `PROVEN`.
- **Framebuffer placement**: `fb_start = vram_start`, `fb_end = vram_end`,
  por `num_physical_nodes == 0` (no-XGMI). El ASIC **no se programa**: en un
  PF el driver **sólo lee** `FB_BASE`; escribe `mmMC_VM_FB_LOCATION` únicamente
  bajo `amdgpu_sriov_vf`. `PROVEN`.
- **Alignment constraints**: `FB_BASE` → 16 MiB (campo 16 bits << 24);
  `gart_start` → 4 GiB; `vram_start`/`vram_end` se publican a
  `mmMC_VM_SYSTEM_APERTURE_{LOW,HIGH}_ADDR` **>> 12**, o sea con granularidad
  de **4 KiB** (`gmc_v8_0.c:469-471`). `PROVEN`.

### `MODEL_CHOICE` (decisiones del autor, no hechos)

- Que `FB_BASE = 0xF400` **se deduce por inversion** del `vram_start` observado,
  y no leído del VBIOS. Es coherente con la especificación del campo, pero
  **no es una lectura**. `NOT_OBSERVED`.
- Que el `mc_mask` de 40 bits sea un hecho del ASIC y no una decision del driver.
  Es un literal escrito en `gmc_v8_0.c:1133` **para GFX8**; por qué vale
  `0xffffffffff` y no otro número es `NOT_DETERMINED`.

## 5 · Lo que NO cierra

| afirmación | estado |
|---|---|
| `mmCONFIG_MEMSIZE` existe y vale `0x150a` | `PROVEN` |
| `gmc_v8_0.c:560` lo lee; `:567` fija `mc_vram_size` | `PROVEN` |
| El tamaño de VRAM sale de ahí, no de ATOMBIOS | `PROVEN` |
| `RX550_MC_CONFIG_MEMSIZE = 0x150a` es correcto | `PROVEN` |
| `gart_end + gart_size ≠ mc_mask + 1` | `PROVEN` |
| `mc_mask − gart_end == R mod 4 GiB` | `PROVEN_DERIVED` |
| 3,50 GiB de MC sin mapear por encima del GART | `PROVEN_DERIVED` |
| `FB_TOP` sin consumidor GFX8 | `PROVEN_ABSENT` en `amdgpu/*.c` |
| `FB_BASE`/`FB_TOP` = `vram_start`/`vram_end` en 16 MiB | `OBSERVATION` del código, sólo rama VF |
| **Valor real de `mmCONFIG_MEMSIZE` en ESTE ASIC** | **`NOT_OBSERVED`** |
| **Valor real de `FB_BASE` leído del ASIC** | **`NOT_OBSERVED`** |
| **Valor real de `FB_TOP`** | **`NOT_DETERMINED`** |
| **Semántica de `FB_TOP` en un MC de 40 bits** | **`NOT_DETERMINED`** |
| Por qué `mc_mask` es 40 bits y no otro | `NOT_DETERMINED` |

**Los cuatro `NOT_OBSERVED`/`NOT_DETERMINED` de arriba son una sola acción**:
un `RREG32` de `0x809` y de `0x150a` sobre BAR5. Es NIVEL 2, sólo lectura, y
la ruta está escrita. **Es el último hueco de §F en el lado de VRAM**, y lo
que decidiría es si el `MODEL_CHOICE` de arriba es un hecho o una hipótesis.

## Confounders

- **El corpus es un SUBTREE PARCIAL**: contiene `drivers/gpu/drm/amd/` y
  `include/` (la parte de amdgpu), pero **no** `include/drm/amd_asic_type.h` ni
  la definición de `CHIP_POLARIS12`. Por eso `tools/asic_resolver.py` **no
  puede** ejecutarse aquí (lo intenté: sale con aviso y **cero resoluciones**,
  `RC=0`, que es exactamente el `exit 0 ≠ resultado válido` del proyecto). Mi
  cadena de includes no necesita el árbol completo **porque el include es
  incondicional**, y eso está medido, no supuesto.
- `PROVEN_ABSENT` de `FB_TOP` es un negativo **con alcance**: `amdgpu/*.c` del
  corpus. No es un negativo sobre el silicio.
- No he construido el driver del proyecto ni ejecutado nada contra hardware.
  Todo lo del `07-DRIVER/` es lectura estática.

## Desfalsificación

- **(a)** `mmCONFIG_MEMSIZE` existe → refutable con `grep -rn mmCONFIG_MEMSIZE
  amdgpu/*.c`. **Verificado: 6 ficheros.**
- **(b)** `0x150a` es su valor → refutable con `grep -n "define mmCONFIG_MEMSIZE"
  include/asic_reg/bif/bif_5_0_d.h`. **Verificado: `:33`, `0x150a`.**
- **(c)** el include es incondicional → refutable leyendo `gmc_v8_0.c:38` y sus
  vecinos. **Verificado: no hay `#if` alrededor.**
- **(d)** el patrón de `279` no puede coincidir → refutable con una búsqueda
  de subcadena. **Verificado en el instrumento, sección 1: 0 ocurrencias de
  `MC_CONFIG_MEMSIZE` dentro de `mmCONFIG_MEMSIZE`.**
- **(e)** `amdgpu_gmc.c:61` está en `amdgpu_gmc_pdb0_alloc` → refutable con la
  firma de la función. **Verificado: `:57`.**
- **(f)** `gart_end + gart_size ≠ mc_mask + 1` → refutable por aritmética.
  **Verificado en el instrumento, sección 3.4b.**
- **(g)** `FB_TOP` sin consumidor GFX8 → refutable con `grep -rn FB_TOP
  amdgpu/*.c`. **Verificado: 4 resultados, los 4 SOC15.**

## Procedencia

- `STATIC` -- `amdgpu/gmc_v8_0.c:38` (include), `:417` (lectura de `FB_BASE`),
  `:474-478` (escritura bajo `sriov_vf`), `:510` (`gmc_v8_0_mc_init`), `:560`,
  `:567`, `:609` (`gmc_v8_0_vram_gtt_location`), `:1133` (`mc_mask`);
  `include/asic_reg/bif/bif_5_0_d.h:33`; `include/asic_reg/gmc/gmc_8_1_d.h:281`;
  `include/asic_reg/gmc/gmc_8_1_sh_mask.h:3969-3972`;
  `amdgpu/amdgpu_gmc.h:36-37`; `amdgpu/amdgpu_gmc.c:57`, `:61`, `:214-237`
  (`:217`, `:218`, `:221`, `:232-234`), `:299`, `:332-333`;
  `amdgpu/amdgpu_drv.c:152`; `amdgpu/mmhub_v1_0.c:45`, `mmhub_v1_7.c:45`,
  `mmhub_v1_8.c:46`, `mmhub_v9_4.c:48`;
  `07-DRIVER/kernel/rx550_mc.h:71`, `:73`, `rx550_mc.c:112-148`.
- **Cálculo** -- las tablas de las §2 y §4 las imprime
  `03-EXPERIMENTOS/ep08-mc-vram-geometry/mc_geometry.c`, que compara
  «calculado» contra «observado» en su propia salida y **nombra cada aserción
  que falla**. 29 aserciones, 0 fallos. `gcc -Wall -Wextra`, sin avisos.
- `RUNTIME` — **no ejecutado** en este turno. Las líneas `OBSERVATION` vienen
  de `journalctl -k -b` vía `199`, y se declaran como observadas por otro, no
  medidas aquí.
- **No se editó ningún fichero del corpus, ni `AGENTS.md`, ni
  `OPEN-FRONTIERS.md`.**
- Encadenada con `199` (corregida en §2), `279` (refutada en §1), `164`
  (origen del número `0xFF0FFFFFFF`), `054` (las dos máscaras MC y PTE), `086`,
  `201` (los dos prefijos de `MC_VM_FB_LOCATION`), `204` (los 256 MiB del
  GART), `153`.

## Dos errores míos, de la misma clase que `199` §4

Los registro porque son la clase más cara que hay, y porque un hallazgo que
oculta los errores de su propio instrumento no vale lo que dice.

**El primero, en el instrumento.** Comprobé si el `vram_end` erroneous del
driver *desbordaba 64 bits*. No desborda: `0xF400000000 + 0xFFFF00000000`
cabe de sobra. El programa imprimía *«rebasa los 40 bits del MC = no»* y dos
líneas más abajo escribía *«ese fin no cabe en el MC»*. **Las dos frases no
pueden ser ciertas a la vez, y la segunda es la que yo quería.** Es
exactamente el patrón de `199` §4: la conclusión escrita antes de mirar. La
pregunta correcta no es si desborda el entero del host, sino si cabe en el
**MC**, y no cabe: 53 bits contra 40.

**El segundo, en la aserción.** Afirmé que el hueco final era «exactamente el
desnivel de la alineación». No lo es: el desnivel es `0x00F0000000` y el hueco
final `0x00E0000001`, y se diferencian en `1 − gart_size`. **Lo que sí es
exacto es `mc_mask − gart_end == R mod 4 GiB`**, que es el invariante
correcto.

**Y una tercera, menor pero del mismo tipo: la función `ok()` del instrumento
tenía la firma variádica de `printf` y no imprimía nada.** Contaba los fallos y
no decía **cuáles**. Un programa que dice «1 fallo» sin decir cuál obliga a
recompilar para enterarse, y por eso no puede usarse como veredicto. Lo
arreglé antes de fiarme de la salida, y fue ese arreglo el que hizo posible
encontrar el segundo error.

> **La regla que sale de las tres, y es la misma de `199`: *una herramienta
> que imprime contradicciones en su propia salida es lo más útil que existe, y
> sólo sirve si se lee hasta el final del bloque y si nombra lo que falla*.**
> Mis dos errores de este turno los encontró el instrumento, no yo. Lo que no
> hizo el instrumento —y sigue sin hacer— es decidir si el ASIC implementa
> `mmCONFIG_MEMSIZE` como campo de 16 bits o más ancho. Eso hay que leerlo.