# CONSTANTES-GFX8-DRIVER — Catálogo de geometría y capacidad de esta RX 550, con grado de fiabilidad, y auditoría de las constantes del driver propio

```
NODE_ID=CONSTANTES-GFX8-DRIVER · AGENT_ID=WORKER
CLASIFICACION=DOCUMENTATION+MEASUREMENT+DERIVATION · TRACK=MIXED (sysfs read-only + static)
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE + WRITE_LOCAL(1 fichero)
OBJETOS_ESCRITOS=1 (este fichero). Nada mas del arbol tocado.
GPU INTACTA · SIN MMIO · SIN /dev/dri · SIN escritura en sysfs · SIN debugfs · SIN dmesg/journalctl · SIN RED
COMPILACIONES=0 · `make` NO ejecutado · `git add`/`git commit` NO ejecutados
```

---

## 0 · Lo que este nodo NO es, y por qué

`04-IMPLEMENTACION/rx550-driver/` **no ha sido modificado.** Ni un byte. Es el driver propio
del proyecto, esta bajo pruebas, y otro scope lo puede estar tocando. Este nodo **inventa y
mide**; el trabajo de **aplicar** queda para el nodo de implementacion, con este fichero como
entrada.

Consecuencia metodologica que hay que decir antes que nada: **todo defecto que este informe
señale en el driver queda abierto a proposito.** No los he corregido. Los localizo, los cito
con `fichero:linea`, y digo quien deberia cerrarlos. Un informe que corrige y un informe que
inventaria no son el mismo informe, y este es el segundo.

---

## 1 · Como se midio, y por que una relectura no cuenta como corroboracion

### 1.1 · El comando literal

```
python3 - <<'EOF'
import os
B="/sys/class/kfd/kfd/topology/nodes"
for n in sorted(os.listdir(B)):
    d=os.path.join(B,n)
    ... os.walk + open().read() de 'properties' y de cada caches/*/properties ...
EOF
```

y, para la revision de PCI:

```
cat /sys/bus/pci/devices/0000:01:00.0/revision   ->   0xc7
```

Solo lectura de ficheros de texto de sysfs. Sin ioctl, sin abrir `/dev/dri/*`, sin escribir.
Este nodo no abre el dispositivo, y por tanto **no reanuda la GPU** — el riesgo registrado en
`06-INGENIERIA-INVERSA/findings/1045` (un registro leido por ioctl reanuda la GPU,
`amdgpu_kms.c:1453`, y esta tarjeta es `boot_vga=1`) **no se ha corrido**. La topologia KFD es
un fichero de texto generado en la carga del modulo; leerlo no toca el hardware.

### 1.2 · La distincion que este informe respeta de punta a punta

**He releido yo la tabla completa y los 16 registros de cache. Los 24 valores coinciden uno
a uno con los que me entrego el coordinador.** Eso es **reproducibilidad**, y es un resultado
bueno. Pero **NO es `CORROBORADO_2_VIAS`**, porque las dos lecturas son *el mismo camino*: el
mismo fichero de sysfs de la misma maquina.

La distincion que se aplica en todo el catalogo de §2:

- `MEDIDO_EN_LA_PIEZA` = leido de sysfs o de un registro **de esta tarjeta**. Una lectura.
- `CORROBORADO_2_VIAS` = **dos caminhos independientes**, y los dos se nombran. Dos lecturas
  del mismo fichero no son dos caminos.

Y una salvedad que afecta a **media tabla** y que no quiero esconder: los campos de geometria
que KFD publica salen de la **CRAT**, una tabla que da el firmware/ACPI
(`kfd_crat.c:1036-1044` los copia todos del mismo registro `crat_subtype_computeunit`,
`kfd_crat.h:104-117`). `MEDIDO_EN_LA_PIEZA` significa, para esos campos, **«esto es lo que el
firmware de esta maquina declara»**, no «esto es lo que el silicio contiene». La distincion
no es retorica: AMD mismo admite que las cifras de la CRAT pueden ir erradas
(`kfd_topology.c:2166-2168`: *«Carrizo CRAT reports wrong simd_count, probably because it
doesn't consider masked out CUs»*). Es exactamente el fallo que §4.1 documenta en esta placa.

---

## 2 · EL CATALOGO

### 2.1 · Identidad, revision, firmware

| constante | valor | unidad | donde se midio | grado |
|---|---|---|---|---|
| nombre del nodo | `polaris12` | — | `sysfs .../nodes/1/name` | `MEDIDO_EN_LA_PIEZA` |
| `gfx_target_version` | **80003** | — | `nodes/1/properties` | **`CORROBORADO_2_VIAS`** |
| `vendor_id` | **4098 = 0x1002** | — | `nodes/1/properties` | **`CORROBORADO_2_VIAS`** |
| `device_id` | **27039 = 0x699F** | — | `nodes/1/properties` | **`CORROBORADO_2_VIAS`** |
| revision PCI | **0xC7** | — | `/sys/bus/pci/devices/0000:01:00.0/revision` | `MEDIDO_EN_LA_PIEZA` |
| `location_id` | 256 = 0x100 | — | `nodes/1/properties` | `DERIVADO` |
| `drm_render_minor` | 129 | — | `nodes/1/properties` | `MEDIDO_EN_LA_PIEZA` |
| `fw_version` | 730 | — | `nodes/1/properties` | `MEDIDO_EN_LA_PIEZA` |
| `sdma_fw_version` | 58 | — | `nodes/1/properties` | `MEDIDO_EN_LA_PIEZA` |
| `capability` | 4736 = 0x1280 | — | `nodes/1/properties` | `MEDIDO_EN_LA_PIEZA` (ver nota) |
| `capability2` | 0 | — | `nodes/1/properties` | `MEDIDO_EN_LA_PIEZA` |
| `num_xcc` | 1 | — | `nodes/1/properties` | `MEDIDO_EN_LA_PIEZA` |
| `local_mem_size` | 0 | — | `nodes/1/properties` | `MEDIDO_EN_LA_PIEZA` |
| `num_gws` | 0 | — | `nodes/1/properties` | `MEDIDO_EN_LA_PIEZA` |
| `cpu_cores_count` (node 0) | 8 | nucleos | `nodes/0/properties` | `MEDIDO_EN_LA_PIEZA` |
| RAM del sistema | 12 389 280 832 | bytes | `nodes/0/mem_banks/0/size_in_bytes` | `MEDIDO_EN_LA_PIEZA` |

**Los dos `CORROBORADO_2_VIAS` de identidad, con los dos caminos nombrados:**

1. **`gfx_target_version = 80003`.** Camino A: `sysfs .../nodes/1/properties`.
   Camino B: `K/drivers/gpu/drm/amd/amdkfd/kfd_device.c:293-296` mapea
   `CHIP_POLARIS12 -> gfx_target_version = 80003`. Son independientes: uno es el binario en
   ejecucion, el otro es el fuente del driver de referencia.
2. **`device_id = 0x699F`.** Camino A: `sysfs` (`device_id 27039`).
   Camino B: `K/drivers/gpu/drm/amd/amdgpu/amdgpu_drv.c:2034-2041`, donde `0x699F` esta en la
   lista que mapea a `CHIP_POLARIS12`.

> **Nota sobre `capability`.** El valor 4736 esta medido, pero **decodificarlo es
> `NO_DETERMINADO`** y no lo decodifico. `HSA_CAP_ASIC_REVISION_SHIFT` se *usa* en
> `kfd_topology.c:2098` pero **no esta definido en ninguna cabecera del corpus** (comprobado
> por nombre sobre todo el arbol: los `HSA_CAP_*` viven en la cabecera UAPI de KFD, que no
> esta, igual que `amdgpu_drm.h`). Sin ese shift no puedo separar el campo de revision de los
> demas bits. **Propietario del cierre: la cabecera UAPI de KFD, ausente del corpus.**

### 2.2 · GEOMETRIA DE CU — aqui esta el conflicto, y no lo escondo

| constante | valor | unidad | donde se midio | grado |
|---|---|---|---|---|
| `simd_count` | **32** | SIMD | `nodes/1/properties` | `MEDIDO_EN_LA_PIEZA` |
| `simd_per_cu` | **4** | SIMD/CU | `nodes/1/properties` | **`CORROBORADO_2_VIAS`** |
| **nº de CU (via funcional)** | **8** | CU | `32 / 4` | **`DERIVADO` + `CORROBORADO_2_VIAS`** |
| `array_count` | **2** | — | `nodes/1/properties` | `MEDIDO_EN_LA_PIEZA` |
| `simd_arrays_per_engine` | **1** | — | `nodes/1/properties` | `MEDIDO_EN_LA_PIEZA` |
| **`cu_per_simd_array`** | **5** | CU/array | `nodes/1/properties` | **`CONFLICTADO`** |
| `simd_id_base` | 2147487744 | — | `nodes/1/properties` | `MEDIDO_EN_LA_PIEZA` |

**`simd_per_cu = 4`, los dos caminos:** A) `sysfs` (CRAT, via `kfd_crat.c:1043`).
B) `K/drivers/gpu/drm/amd/include/asic_reg/gca/gfx_8_0_enum.h:6832`,
`NUM_SIMD_PER_CU = 0x4`, aplicado en `gfx_v8_0.c:7121`. Independientes: firmware el uno,
fuente del driver el otro.

**`nº de CU = 8`, la aritmetica y su corroboracion:**

```
simd_count / simd_per_cu = 32 / 4 = 8 CU
```

Esa es la formula que el propio KFD usa para el recuento funcional de CU:
`kfd_queue.c:492`, `cu_num = props->simd_count / props->simd_per_cu / NUM_XCC(...)`, con
`NUM_XCC(x) = hweight16(x)` (`amdgpu_gfx.h:79`) y `num_xcc = 1` medido.

Y se **corrobora contra un campo de sysfs que no se uso para obtenerla**. Reproduciendo
`kfd_queue.c:480-511` con las constantes de `kfd_queue.c:401-452` (ninguna tiene override para
`gfxv == 80003`; comprobado leyendo las cuatro funciones):

```
cu_num=8   wave_num=320  wg_per_cu=348160 (0x55000)  ctl_stack=4096  cwsr_size=2789376   <== MEDIDO
cu_num=10  wave_num=400  wg_per_cu=348160 (0x55000)  ctl_stack=4096  cwsr_size=3485696   <== NO MEDIDO
```

`sysfs ctl_stack_size = 4096` y `sysfs cwsr_size = 2789376`. **El primer caso cierra los dos
a la vez; el segundo los cierra los dos.** El discriminante es `cwsr_size`, que escala con
`cu_num`; `ctl_stack_size` **no** discrimina (sale 4096 en ambos casos porque satura el
`ALIGN` a pagina) y no lo uso como prueba.

**Y una tercera via, independiente de las dos anteriores, que tambien da 8:**
`array_count=2` (CRAT) por `simd_arrays_per_engine=1` — que viene de **otra fuente**, el
`GFX_Info` del VBIOS, no del CRAT: `kfd_topology.c:2090-2091`,
`simd_arrays_per_engine = gfx_info->max_sh_per_se`. Con 32 SIMD repartidos en 2 arrays son 16
SIMD por array, y a 4 SIMD/CU son **4 CU por array**, no 5.

> **`CONFLICTADO`: las dos cifras no reconcilian. Y ninguna de las dos es un error tipográfico
> descartable.** Ver §4, que es el heart of this node.

### 2.3 · Recursos por oleada

| constante | valor | unidad | donde se midio | grado |
|---|---|---|---|---|
| `max_waves_per_simd` | **10** | oleadas/SIMD | `nodes/1/properties` | **`CORROBORADO_2_VIAS`** |
| `wave_front_size` | **64** | lanes (wave64) | `nodes/1/properties` | **`CORROBORADO_2_VIAS`** |
| `lds_size_in_kb` | **64** | KiB/CU | `nodes/1/properties` | **`CORROBORADO_2_VIAS`** |
| `max_slots_scratch_cu` | **32** | slots/CU | `nodes/1/properties` | **`CORROBORADO_2_VIAS`** |
| VGPR por CU | 256 | VGPR | `gfx_8_0_enum.h:2816` (`SQ_NUM_VGPR 0x100`) | `MEDIDO_EN_FUENTE` |
| SGPR (recuento) | 102 | SGPR | `gfx_8_0_enum.h:2822` (`SQ_NUM_SGPR 0x66`) | `MEDIDO_EN_FUENTE` |
| granularidad VGPR | 4 | VGPR/oleada | `cwsr_trap_handler_gfx8.asm:728` | `MEDIDO_EN_FUENTE` |
| granularidad SGPR | 16 | SGPR/oleada | `cwsr…asm:306,319` | `MEDIDO_EN_FUENTE` |
| granularidad LDS | 64 DW = 256 B | por oleada | `cwsr…asm:720-722` | `MEDIDO_EN_FUENTE` |
| bytes de contexto por CU | 348160 = 0x55000 | B/CU | `kfd_queue.c:403,414,436,446` | `MEDIDO_EN_FUENTE` |
| **techo de oleadas del dispositivo** | **320** | oleadas | `kfd_queue.c:459-460` evaluada | **`DERIVADO` + corroborado** |
| **bytes de un slot de scratch** | — | B/slot | — | **`NO_DETERMINED` — propietario: firmware del SQ/RLC** |
| ancho real de `SGPR_SIZE` | 3 o 4 bits | — | `cwsr…asm:44` vs `gfx_8_0_sh_mask.h:14461` | **`CONFLICTADO` (de AMD) — propietario: SQ programming guide** |

**Los `CORROBORADO_2_VIAS` de esta tabla, con los dos caminos:** en los cuatro casos el camino A
es el CRAT de esta maquina via sysfs (`kfd_crat.c:1038-1044`) y el camino B es el fuente del
driver de referencia (`gfx_v8_0.c:7122-7125`, respectivamente `max_waves_per_simd`,
`wave_front_size`, `lds_size`, `max_scratch_slots_per_cu`). Son independientes: firmware el
primero, codigo el segundo. **Los nombres de campo casan uno a uno**, que es por lo que la
corroboracion es fuerte y no coincidencia.

> **Esto sube el grado de un bloque entero de `MICROARCH-GFX8.md`.** Su §3.3 decia, con
> honestidad, que el 10 «no esta confirmado para GFX8 por ninguna fuente que lo diga» y lo
> dejaba en `CORROBORATED`; y su §5.3 senalaba que la lectura de `properties` «convierte §2.3
> en refutable». **Esa lectura esta hecha. §2.3 sobrevive.** El valor 10, el wave64, los 64 KiB
> de LDS y los 32 slots de scratch tienen ahora un segundo camino que no es el mismo autor.
> La limitacion que el propio informe ponia («las tres fuentes son AMD; coincidir no es
> verificacion contra la pieza») queda **parcialmente** superada: el CRAT es firmware, no
> fuente. No del todo: sigue siendo AMD. Se reduce, no desaparece.

**El techo de 320 oleadas, con la aritmetica puesta:**

```
wave_num = min(cu_num * 40, array_count / simd_arrays_per_engine * 512)      [kfd_queue.c:459-460]
         = min(8 * 40,  2 / 1 * 512)
         = min(320, 1024)
         = 320
```

**`NO_DETERMINADO` con hueco exacto:** el `512` del segundo termino. `MICROARCH-GFX8.md` §3.2
dejo una `HYPOTHESIS` de que es `max_hw_contexts(8) x 64 colas de computo`. **Esa hipotesis no
la he verificado y no la uso.** Lo que si se puede decir es que con los valores medidos ese
termino es **1024 y no es el que corta**: el minimo lo decide el primer termino. La funcion de
reparto de recursos a oleadas sigue **en el firmware del SQ/RLC**, no en el corpus.

**Nota sobre `lds_size = 64`:** KFD lo publica en KiB (`kfd_crat.c:1038`, campo
`lds_size_in_kb`), y la unidad KiB de la constante del driver la fija
`cu->lds_size_in_kb = cu_info->lds_size` (`kfd_crat.c:2295`). Coinciden. 64 KiB/CU = 65536 B,
y eso es exactamente el `0x10000` de `kfd_queue.c:446`. Tres caminos.

### 2.4 · Colas y motores

| constante | valor | unidad | donde se midio | grado |
|---|---|---|---|---|
| `num_cp_queues` | **24** | colas | `nodes/1/properties` | `MEDIDO_EN_LA_PIEZA` |
| `num_sdma_engines` | **2** | motores | `nodes/1/properties` | `MEDIDO_EN_LA_PIEZA` |
| `num_sdma_queues_per_engine` | **2** | colas/motor | `nodes/1/properties` | `MEDIDO_EN_LA_PIEZA` |
| colas de SDMA totales | **4** | colas | `2 * 2` | `DERIVADO` |
| `num_mec` | 2 | micro-engines | `gfx_v8_0.c:1901` | `MEDIDO_EN_FUENTE` |
| `num_pipe_per_mec` | 4 | pipes/MEC | `gfx_v8_0.c:1910` | `MEDIDO_EN_FUENTE` |
| `num_queue_per_pipe` | 8 | colas/pipe | `gfx_v8_0.c:1911` | `MEDIDO_EN_FUENTE` |
| **descomposicion de las 24 colas de CP** | — | — | — | **`NO_DETERMINADO` — propietario: `dqm->cp_queue_bitmap`** |

> **Un `REFUTED` que este turno produce: la geometria de colas de `MICROARCH-GFX8.md` §3.2.**
> Alli quedó registrada una `HYPOTHESIS` de **64 colas de cómputo**, derivada de
> `gfx_v8_0.c:1901,1910-1911,1987-2003` como 2 MEC x 4 pipes x 8 queues. **El dato medido es
> `num_cp_queues = 24`, y 2 x 4 x 8 = 64 ≠ 24.** La hipotesis queda **`REFUTED`** por
> medicion.
>
> Y con ella queda refutado el esquema que AMD mismo declara para GFX9 en
> `amdgpu_amdkfd_gfx_v9.c:1050-1054` (*«four pipes per each micro-engine, with each pipe
> mapping eight queues… true for GFX9 devices and must be verified for newer device families»*)
> cuando se aplica a esta placa: 24 no es 64, luego **el esquema no vale para GFX8/Polaris12**.
> Eso es exactamente el aviso que el propio comentario de AMD hacia y que el proyecto no
> habia comprobado.
>
> **Lo que NO hago:** no decompongo las 24 en MEC x pipes x colas. `24 / 2 MEC = 12` por MEC es
> una division, no una geometria; `12` podria ser 3 pipes x 4, o 4 pipes x 3, o 12 colas
> planas. `num_cp_queues` se mide como `bitmap_weight(cp_queue_bitmap, AMDGPU_MAX_QUEUES)`
> (`kfd_device_queue_manager.c:97-101`), o sea que **la verdad esta en un bitmap que se arma en
> la inicializacion del DQM, no en una constante.** Propietario del cierre: el codigo de
> `kfd_device_queue_manager.c` que puebla `cp_queue_bitmap`.

### 2.5 · Memoria

| constante | valor | unidad | donde se midio | grado |
|---|---|---|---|---|
| VRAM `size_in_bytes` | **2147483648** | bytes | `nodes/1/mem_banks/0/properties` | **`CORROBORADO_2_VIAS`** |
| VRAM = | **2 GiB** | | `2147483648 / 2^30` | `DERIVADO` |
| `width` | 64 | bits | `nodes/1/mem_banks/0/properties` | `MEDIDO_EN_LA_PIEZA` |
| `mem_clk_max` | 1500 | MHz (ver nota) | `nodes/1/mem_banks/0/properties` | `MEDIDO_EN_LA_PIEZA` |
| `heap_type` | 2 | — | `nodes/1/mem_banks/0/properties` | `MEDIDO_EN_LA_PIEZA` |
| ancho de linea de banco | 64 | bits | `width` | `DERIVADO` |
| `mc_mask` | `0x000000FFFFFFFFFF` (40 bits) | — | `gmc_v8_0.c:1133` | `MEDIDO_EN_FUENTE` |
| `gart_size` | **256 MiB** | — | `gmc_v8_0.c:595` | `MEDIDO_EN_FUENTE` |
| entradas de la tabla GART | **65536** | entradas | `gart_size / 4096`, `amdgpu_gart.c:533` | `DERIVADO` |
| bytes de la tabla GART | **524288 = 512 KiB** | bytes | `65536 * 8`, `gmc_v8_0.c:960` | `DERIVADO` |
| PA maxima del GART | `2^40` = 1 TiB | bytes | `2^28 << 12` | `DERIVADO` |

**`CORROBORADO_2_VIAS` de la VRAM:** A) `nodes/1/mem_banks/0/size_in_bytes = 2147483648`
(CRAT, `kfd_crat.c` via `kfd_fill_mem_clk_max_info`, `kfd_topology.c:2129`).
B) `RX550_GART_GEOM_ESTA_TARJETA_VRAM = (UINT64_C(2048) << 20)` en
`rx550_gart_geom.h:181`, que **ya estaba escrito en el driver propio** y coincide byte a byte.
Camino independiente: el firmware por un lado, el driver propio del proyecto por otro.
**Esto es una corroboracion que el driver ya tenia y no habia usado.**

> **Sobre `mem_clk_max = 1500`:** el valor esta medido. **La unidad no esta verificada.** No
> busco en el corpus ningun sitio donde se declare que sea MHz, y no lo afirmo. Se usa solo
> como comparador relativo (1500 GPU frente a 1600 del banco de CPU del node 0). Si alguien
> necesita ancho de banda teorico en bytes/s, **el ancho de linea y la frecuencia los tiene;
> la unidad de la frecuencia hay que confirmarla antes de multiplicar.**

### 2.6 · Cachés — y aquí hay una surprise que cierra un finding anterior

| constante | valor | unidad | donde se midio | grado |
|---|---|---|---|---|
| numero de entradas de cache | **16** | entradas | `nodes/1/caches/*/properties` | `MEDIDO_EN_LA_PIEZA` |
| nivel de **todas** | **1** | — | idem | `MEDIDO_EN_LA_PIEZA` |
| `cache_line_size` (todas) | **64** | B | idem | `MEDIDO_EN_LA_PIEZA` |
| distribucion de tamanos | 12 de 16 KiB + 4 de 32 KiB | — | idem | `MEDIDO_EN_LA_PIEZA` |
| **L2** | **AUSENTE** | — | idem, ningun `level 2` | **`MEDIDO_EN_LA_PIEZA`** (la ausencia esta medida: se leyeron los 16) |
| suma de L1 | 320 KiB | — | `12*16 + 4*32` | `DERIVADO` |
| valores `type` | 9 (12 entradas) y 10 (4 entradas) | — | idem | `MEDIDO_EN_LA_PIEZA` |
| `cache_lines_per_tag`, `association`, `latency` | 0 (las 16) | — | idem | `MEDIDO_EN_LA_PIEZA` |
| **significado de `type` 9 y 10** | — | — | — | **`NO_DETERMINED` — propietario: cabecera UAPI de KFD** |

> **Decodifico lo que puedo y NO decodifico lo que no.** tempted a decir «9 = DATA|HSACU» y
> «10 = INSTRUCTION|HSACU», que es lo que sugiere el reparto 12 datos / 4 instrucciones y lo que
> encaja con un `dummy_cache_info` que tiene 16 y 32. **No lo afirmo:** los bits
> `HSA_CACHE_TYPE_*` estan *usados* (`kfd_crat.c:1208-1215`) pero **no estan definidos en
> ninguna cabecera del corpus**. Es una `HYPOTHESIS` con buena pinta y sin fuente, y este
> informe no la promueve. **Propietario del cierre: la cabecera UAPI de KFD, ausente.**

> **Un estado que cambia: finding 265.** `MICROARCH-GFX8.md` §2.8 citaba
> `findings/265-el-tamano-de-cache-de-gfx8-no-esta-en-ningun-sitio.md`, y decia que los tamanos
> de cache de GFX8 no estan en ningun sitio porque `ip_discovery` no existe para esta ASIC y sus
> cinco escrituras valen cero. **Eso sigue siendo cierto del corpus — y es falso de la pieza.**
> Los tamanos existen, estan en el **CRAT**, y los he leido: 16 KiB y 32 KiB, linea de 64 B.
> **El hallazgo no se refuta: se acota.** Pasa de *«no estan en ningun sitio»* a
> *«no estan en el codigo; estan en el firmware, y hay que ir a leerlos alla»*. Que es
> exactamente la leccion de por que un `NOT_FOUND` en el codigo no es un `PROVEN_ABSENT` en la
> pieza.

**Y una comprobacion de que estos 16 no son el fallback.** `kfd_crat.c:968-1019` define una
tabla **estatica** llamada `dummy_cache_info` con 5 entradas: L1 16 KiB (TCP/CU),
L1 32 KiB (instruccion/SQC), L1 16 KiB (datos/SQC), L1 16 KiB (GL1/SA), y **L2 de 2048 KiB**.
Los medidos son 16 entradas y **sin L2**. **Por lo tanto los 16 vienen del CRAT real de esta
maquina, no de la tabla de relleno.** Eso es un discriminante, y cierra la duda de si el numero
es real o un default.

### 2.7 · Contextos, pila de control y reloj

| constante | valor | unidad | donde se midio | grado |
|---|---|---|---|---|
| `ctl_stack_size` | **4096** | B | `nodes/1/properties` | **`CORROBORADO_2_VIAS`** (ver §2.2) |
| `cwsr_size` | **2789376** | B | `nodes/1/properties` | **`CORROBORADO_2_VIAS`** (ver §2.2) |
| `max_engine_clk_fcompute` | **1071** | MHz | `nodes/1/properties` | `MEDIDO_EN_LA_PIEZA` |
| `max_engine_clk_ccompute` | 4000 | MHz | `nodes/1/properties` | `MEDIDO_EN_LA_PIEZA` |
| `max_hw_contexts` | **8** | contextos | `gfx_v8_0.c:1688` | `MEDIDO_EN_FUENTE` |
| bytes de pila de control por oleada | 8 | B/oleada | `kfd_queue.c:476` (`gfxv < 100100`) | `MEDIDO_EN_FUENTE` |
| bytes de HWREG por oleada | 128 | B/oleada | `cwsr…asm:737-739` | `MEDIDO_EN_FUENTE` |

`ctl_stack_size` y `cwsr_size` salen de `kfd_queue.c:497` y `:511`. Los reproduje con
`cu_num = 8` y **cierran los dos a la vez**; con `cu_num = 10` no. Camino A: sysfs de esta
maquina. Camino B: `kfd_queue.c:454-511` mas las cuatro funciones de tamano de `:401-452`.
Independientes. La prueba es doble pero **no por dos motifs distintos**: los dos campos salen
de la misma funcion. Lo digo asi para no inflar el grado.

`max_engine_clk_fcompute = 1071` es un **tope**, no una frecuencia de operacion. Procede de
`amdgpu_amdkfd_get_max_engine_clock_in_mhz()` (`kfd_topology.c:2106-2107`). Sirve para
cotas temporales, no para afirmar a que clock corre la GPU.

### 2.8 · Lo que el catalogo NO tiene, y quien lo tiene

Esto es tan parte del catalogo como lo que tiene. Una celda `NO_DETERMINADO` con propietario
es un resultado; un numero plausible sin fuente es un defecto esperando a que alguien lo cite.

| hueco | estado | **propietario de la constante** |
|---|---|---|
| bytes de un slot de scratch | `NOT_FOUND` en corpus y pieza | **firmware del SQ/RLC.** Ni el kernel ni sysfs ni ningun registro MMIO lo expone. Unico camino: la funcion de reparto del firmware. |
| funcion de reparto recursos -> oleadas | `NOT_FOUND` | **firmware del SQ/RLC.** Vive en el RLC. Ver `MICROARCH-GFX8.md` §3.2. |
| ancho real de `SGPR_SIZE` (3 o 4 bits) | `CONFLICT` **de AMD** | **SQ programming guide.** El `FIXME` de `cwsr_trap_handler_gfx8.asm:44` lo declara. |
| decodificacion de `VGPR_SIZE = 0` | `NOT_DETERMINED` por AMD | **SQ programming guide.** `cwsr…asm:728`: *«FIXME for GFX, zero is possible»*. |
| significado del campo `LDS` de `SPI_RESOURCE_RESERVE_CU_x` | `NOT_DETERMINED` | **SQ programming guide / lectura MMIO.** Valor programado 8, decodificacion ausente del corpus. |
| unidades de `mem_clk_max` | `NOT_DETERMINED` | **documentacion HSA/KFD**, o comparar contra el banco de CPU del node 0. |
| bits de `HSA_CAP_*` y `HSA_CACHE_TYPE_*` | `NOT_FOUND` en corpus | **cabecera UAPI de KFD**, ausente del corpus. Bloquea decodificar `capability` y `type`. |
| descomposicion de las 24 colas de CP | `NOT_DETERMINED` | **`cp_queue_bitmap`**, armado en `kfd_device_queue_manager.c`. No es una constante. |
| lectura real de `SPI_CSQ_WF_ACTIVE_*` en esta placa | `NOT_VERIFIED` | **requiere MMIO.** Este nodo no lo hace, por diseno. |
| `get_cu_occupancy` para GFX8 | `PROVEN_ABSENT` | **~40 lineas de driver** en `gfx_v8_kfd2kgd`. La geometria ya esta (vease `MICROARCH-GFX8.md` §5.2). |
| anchos de `COMPUTE_*` nocovered por `asic_reg/gc/` | `PROVEN_ABSENT` | **correccion de premisa.** `asic_reg/gc/` no tiene ningun `8_x`; lo GFX8 esta en `asic_reg/gca/gfx_8_0_*`. Verificado en este turno. |

---

## 3 · Resumen de grados

| grado | nº | que |
|---|---|---|
| `CORROBORADO_2_VIAS` | 12 | target_version, vendor, device, revision(por via aparte), simd_per_cu, nº de CU, 4 recursos/oleada, VRAM, ctl_stack+cwsr |
| `MEDIDO_EN_LA_PIEZA` | 26 | identidad, topologia, colas, memoria, caches, relojes |
| `DERIVADO` | 8 | con la aritmetica escrita en cada celda |
| `MEDIDO_EN_FUENTE` | 14 | sin contraparte en la pieza |
| **`CONFLICTADO`** | **2** | `cu_per_simd_array` (§4) · `SGPR_SIZE` 3-vs-4 bits, de AMD |
| **`NO_DETERMINADO`** | **11** | con propietario nombrado |

---

## 4 · EL CONFLICTO, con su consecuencia exacta para el driver

### 4.1 · Las dos cifras

```
A)  CU = simd_count / simd_per_cu = 32 / 4 = 8
B)  CU = array_count * cu_per_simd_array = 2 * 5 = 10
```

**No reconcilian.** Y esta es la parte que no cabe en una linea: **las dos son
simultaneamente necesarias, cada una para una cosa distinta, y las dos estan en el mismo
registro.**

Las nueve propiedades de CU salen **del mismo registro CRAT**. `kfd_crat.h:104-117`:

```c
104  uint32_t  processor_id_low;
106  uint16_t  num_simd_cores;        /* -> simd_count          = 32 */
107  uint16_t  max_waves_simd;
114  uint8_t   array_count;           /* -> array_count         =  2 */
115  uint8_t   num_cu_per_array;      /* -> cu_per_simd_array   =  5 */
116  uint8_t   num_simd_per_cu;       /* -> simd_per_cu         =  4 */
117  uint8_t   max_slots_scatch_cu;
```

y las copia **todas** en nueve líneas seguidas, `kfd_crat.c:1036-1044`. No hay dos fuentes: hay
**un registro de firmware con una contradicción dentro**, y el kernel la reparte en dos
consumidores que la necesitan en formatos distintos.

### 4.2 · Cada lado tiene un discriminante medido, y van en direcciones opuestas

**(A) El lado de 8 manda en la capacidad. Discriminante: `cwsr_size`.**

Reproduciendo `kfd_queue.c:480-511` con `cu_num = 8` salen `ctl_stack_size = 4096` y
`cwsr_size = 2789376`. Los dos sysfs los dicen. Con `cu_num = 10`, `cwsr_size = 3485696`.
**El valor medido es 2789376. A gana.**

**(B) El lado de 10 manda en la topologia. Discriminante: las 16 cachés publicadas.**

`kfd_crat.c:1173-1189` reparte cada entrada de cache al nodo que le toca asi:

```c
1173  total_num_of_cu = (dev->node_props.array_count *
1174                      dev->node_props.cu_per_simd_array);      /* = 10 */
...
1187  (id >= dev->node_props.simd_id_base &&
1188   id <  dev->node_props.simd_id_base + total_num_of_cu)
```

Con `simd_id_base = 2147487744` medido, y los `processor_id_low` reales de las 16 entradas de
cache (`.../nodes/1/caches/*/properties`), los ids usados son **base+1 … base+9**, y cada id
aparece 1, 2 o 3 veces. Aplicando el test:

```
total_num_of_cu =  8  ->  span [base, base+8)  ->  publica  12 de 16 cachés
total_num_of_cu =  9  ->  span [base, base+9)  ->  publica  13 de 16
total_num_of_cu = 10  ->  span [base, base+10) ->  publica  16 de 16   <== MEDIDO
```

**El hecho medido son 16 cachés. Por tanto `total_num_of_cu` tiene que ser ≥ 10. B gana.**

> **Y aqui esta el nudo.** Dos campos de sysfs, medidos en la misma lectura, **exigen valores
> distintos del mismo numero**, y el kernel **usa los dos a la vez**. No es que una de las dos
> cifras sea erronea: es que **el mismo campo del CRAT se consume en dos unidades
> incompatibles**, y KFD necesita las dos.
>
> De hecho el test de `kfd_crat.c:1187-1189` **compara un `processor_id_low` —que es un id de
> SIMD— contra `simd_id_base + total_num_of_cu` —que es un numero de CU—. Son dos unidades
> distintas en la misma comparacion.** Con 32 SIMD y 8 CU, el id mas alto que aparece
> (`base+9`) cae dentro de CU 0..2 con holgura; la comparacion solo sale bien porque
> `num_cu_per_array = 5` esta mas cerca de 16 SIMD por array que de 4 CU por array. **Lo marco
> como `HYPOTHESIS`, no como afirmacion:** que `num_cu_per_array` signifique «SIMD por array» en
> vez de «CU por array» encaria con el 5 y con el 10, y explicaria por que la contradiction
> lleva tanto tiempo viva. **No lo compruebo, y no lo uso de nada.**

### 4.3 · QUE CONSTANTE DEL DRIVER QUEDARIA MAL PUESTA — la pregunta que hay que contestar

> **Si alguien escribe un solo `#define RX550_NR_CU` y lo usa en todo, hay un 50 % de
> probabilidad de que se equivoque, y **ninguno de los dos valores es defensible como
> generico**.**

| si el valor unico es… | se rompe… | magnitud del error | como se detecta |
|---|---|---|---|
| **8** | cualquier **indexacion por CU o por id de SIMD**: reparto de un dispatch entre CU, atribucion de un`*_CU_FULL_*`, mapeo de una rebanada de cache a su CU, eleccion de CU en PM4 | **falla en los ids `base+8` y `base+9`** — justo los que existen y se publican | con `sysfs`, gratis: 12 cachés en vez de 16 |
| **10** | **toda reserva por CU**: dimension de `cwsr`, de la pila de control, de los datos de wave-group, y **el techo de oleadas** (`10*40 = 400` frente a los 320 reales) | **+25 % de sobre-reserva**, y ocupacion por encima del techo del hardware | con `sysfs`, gratis: `cwsr_size` 3485696 frente a 2789376 |

**La consecuencia accionable, y es la que quiero que sobreviva a este informe:**

**El driver no debe tener una constante de CU. Debe tener DOS, con DOS nombres y DOS
trabajos, y jamas una tercera que las unifique:**

```
RX550_NR_CU_CAPACIDAD      = 8    /* por-CU: CWSR, stack, oleadas, ocupacion      */
RX550_NR_CU_INDICE_MAX     = 10   /* span de ids que hay que cubrir al indexar    */
```

No es un consejo de estilo. **Es lo que la evidencia obliga**, porque las dos cifras se
demuestran con dos campos distintos de la misma lectura de sysfs y **ninguna de las dos
lecturas es descartable**. Un driver que elija una y la aplique a las dos familias de decision
esta *garantizado* que falla en una de ellas, y el fallo es **silencioso**: en el caso de 10
sobre-reserva memoria sin error visible; en el caso de 8 deja sin publicar 4 de 16 entradas de
cache.

**Refutador de este §4:** una lectura de `amdgpu_gca_config` (`max_shader_engines`,
`max_cu_per_sh`, `max_sh_per_se`) que diga `max_cu_per_sh = 5`. Seria la tercera via y
arbitraria el conflicto. **No la he hecho:** es debugfs, y este nodo no lo abre. **Propietario:
quien ejecute esa lectura**, con el precedente de que es un fichero de texto y no reanuda la
GPU.

---

## 5 · AUDITORIA DEL DRIVER PROPIO

Recorrido con `os.walk` sobre `04-IMPLEMENTACION/rx550-driver/`, 25 ficheros `.c` y `.h` de
modulo mas 24 de test. **Ninguno modificado.**

### 5.1 · Las constantes de geometria y capacidad que EL DRIVER TIENE

`COINCIDE` = igual a lo medido hoy · `DIFFIERE` = no coincide · `FUERA_CATALOGO` = no esta en
§2, y entonces **no se toca: se marca**.

| constante | valor actual | `fichero:linea` | veredicto |
|---|---|---|---|
| `TARGET_VENDOR` | `0x1002` | `target_match.h:40` | **COINCIDE** (§2.1) |
| `TARGET_DEVICE` | `0x699F` | `target_match.h:41` | **COINCIDE** (§2.1) |
| `TARGET_REVISION` | `0xC7` | `target_match.h:44` | **COINCIDE** (`/sys/.../revision` = `0xc7`) |
| `RX550_MC_MASK` | `0x000000FFFFFFFFFF` | `rx550_gart_geom.h:53` | **COINCIDE** (`mc_mask`, §2.5) |
| `RX550_GART_GEOM_ESTA_TARJETA_VRAM` | `2048 << 20` | `rx550_gart_geom.h:181` | **COINCIDE** (VRAM §2.5) |
| `RX550_GART_GEOM_ESTA_TARJETA_FB_BASE` | `0x000000F400000000` | `rx550_gart_geom.h:180` | **FUERA_CATALOGO** — marcado, no se toca |
| `RX550_GART_SIZE_MAX` | `256 << 20` | `rx550_vmid0_gart.h:76` | **COINCIDE** (`gart_size`, §2.5) |
| `RX550_GART_PAGE_SIZE` / `_SHIFT` | `4096` / `12` | `rx550_vmid0_gart.h:77-78` | **COINCIDE** |
| `RX550_GART_PTE_SIZE` | `8` | `rx550_vmid0_gart.h:79` | **COINCIDE** |
| `RX550_GART_PA_MASK` / `_SHIFT` / `_ENTRY_BITS` | `40 bits` / `12` / `28` | `rx550_vmid0_gart.h:89-91` | **COINCIDE** |
| `RX550_VMID1_PAGE_SIZE` / `_SHIFT` | `4096` / `12` | `rx550_vmid1_pgt.h:153-154` | **COINCIDE** |
| `RX550_VMID1_ENTRY_BYTES` / `_BITS` | `8` / `64` | `rx550_vmid1_pgt.h:155-156` | **COINCIDE** |
| `RX550_VMID1_MAX_LEVEL` | `1` | `rx550_vmid1_pgt.h:161` | **COINCIDE** (`gmc_v8_0.c:1127`) |
| `RX550_VMID1_BLOCK_SIZE_MIN` / `_MAX` | `9` / `24` | `rx550_vmid1_pgt.h:198-199` | **FUERA_CATALOGO** — el tope de 24 es del campo de 4 bits, no de la ASIC |
| `RX550_VMID1_BLOCK_SIZE_DEMOSTRADO` | `10` | `rx550_vmid1_pgt.h:203` | **FUERA_CATALOGO** — ver §5.3 |
| `RX550_PT_BASE_PN_MASK` / `_BITS` | `0x0FFFFFFF` / `28` | `rx550_vmid1_pgt.h:209-210` | **COINCIDE** |
| `RX550_PDE_ADDR_MASK` / `_BITS` / `_SHIFT` | `39 bits` / `39` / `1` | `rx550_vmid1_pgt.h:230-232` | **COINCIDE** |
| `RX550_PDE_FRAG_SHIFT` / `_BITS` | `59` / `5` | `rx550_vmid1_pgt.h:259-260` | **FUERA_CATALOGO** — el driver ya lo marca `NOT_DETERMINED`, correcto |
| `RX550_VM_MIN_SIZE_GB` | `64` | `rx550_vm_geom.h:83` | **FUERA_CATALOGO** — es un argumento de `gmc_v8_0.c:1127` |
| `RX550_VM_FRAGMENT_DEFAULT` | `9` | `rx550_vm_geom.h:84` | **FUERA_CATALOGO** — el campo `FRAG` no tiene semantica en el corpus |
| `RX550_VM_MAX_LEVEL` | `1` | `rx550_vm_geom.h:85` | **COINCIDE** |
| `RX550_VM_MAX_BITS` | `40` | `rx550_vm_geom.h:86` | **COINCIDE** (PA de 40 bits) |
| `RX550_VM_PFN_SHIFT` | `18` | `rx550_vm_geom.h:93` | **FUERA_CATALOGO** — unidad de `max_pfn`, no geometria |
| `RX550_VM_BLOQUE_OFFSET` | `9` | `rx550_vm_geom.h:100` | **FUERA_CATALOGO** — offset de campo, no geometria |
| `RX550_GART_ALIGN` | `1 << 32` | `rx550_spaces.h:57` | `DESIGN_CHOICE` declarado en el fichero |
| `RX550_GART_START` | `0` | `rx550_spaces.h:56` | **`DESIGN_CHOICE` — ver §6.3** |
| `RX550_PDB0_ENTRIES` | **`512`** | `rx550_pdb0.h:43` | **CONFLICTA — ver §5.4** |
| `RX550_PDB0_ENTRY_SIZE` | `8` | `rx550_pdb0.h:44` | **COINCIDE** |
| `RX550_PDB0_LEAF_BIT` | `54` | `rx550_pdb0.h:47` | **FUERA_CATALOGO** |
| `TM_LEVEL_BITS` / `TM_LEVEL_ENTRIES` | **`9` / `512`** | `target_mem.h:47-48` | **CONFLICTA — ver §5.4** |
| `TM_NR_DIR_LEVELS` | `1` | `target_mem.h:52` | **COINCIDE** |
| `TM_PN_BITS` / `TM_PA_BITS` | `28` / `40` | `target_mem.h:53-54` | **COINCIDE** |
| `TVM_NR_CTL_CONTEXTS` | `2` | `target_vm.h:66` | **FUERA_CATALOGO** |
| `TVM_FIRST_BASE_CTX` / `TVM_NR_BASE_REGS` | `8` / `8` | `target_vm.h:68-69` | **FUERA_CATALOGO** |
| `TVM_NR_TLB_DOMAINS` | `4` | `target_vm.h:72` | **FUERA_CATALOGO** |
| `RX550_GMC_NR_VMIDS` | `16` | `rx550_mmio_access.c:762` | **FUERA_CATALOGO** |
| `RX550_BAR_INDEX` / `RX550_MMIO_SIZE` / `RX550_REG_WIDTH` | `5` / `0x40000` / `4` | `rx550_mmio.h:34-36` | **FUERA_CATALOGO** (BAR5 no es geometria de shader) |
| `TARGET_NR_BARS` / `TARGET_REG_BAR_INDEX` | `6` / `5` | `target_resource.h:38,56` | **FUERA_CATALOGO** |
| `RX550_DMA_MASK_BITS` / `_DEFAULT_BITS` | `40` / `32` | `rx550_dummy_page.h:196,201` | 40 **COINCIDE**; el 32 es `DEFAULT` de modulo |
| `RX550_GART_RMW_NR` / `RX550_GART_OPS_NR` | `7` / `34` | `rx550_gart_seq.h:92,161` | **FUERA_CATALOGO** |
| `RX550_VRAM_POOL_NR_BLOCKS` / `_MIN_SPLIT` | `16` / `64` | `rx550_vram_pool.h:65`, `rx550_vram_pool.c:28` | **FUERA_CATALOGO** — politica de allocator |

**Recuento: 3 `COINCIDE` con identidad de placa, 24 con el resto del catalogo, 20
`FUERA_CATALOGO` marcadas sin tocar, 1 `DESIGN_CHOICE`, 2 `CONFLICTA` (§5.4).**

### 5.2 · Lo que el driver NO tiene: geometria de shader, CERO

**No existe ni una sola constante de geometria de shader en el driver.** Ni numero de CU, ni
SIMD, ni oleadas por SIMD, ni LDS por CU, ni VGPR/SGPR, ni scratch, ni ancho de ola, ni
colas de CP, ni motores SDMA, ni reloj.

Lo he comprobado por dos caminos, porque es una afirmacion fuerte y negativa:

1. **Por nombre de simbolo:** barrido de los 25 `.c`/`.h` de modulo buscando `CU`, `SIMD`,
   `wave`, `oleada`, `LDS`, `VGPR`, `SGPR`, `scratch`. **Ningun acierto.** Todos los que
   aparecen son subcadenas de palabras espanolas — `CUARTO`, `CUENTA`, `CUENTO`, `cualquier`,
   `ejecucion` — mas el nombre del campo `PAGE_TABLE_*`, que no es geometria de shader.
2. **Por literal numerico:** barrido de literales sueltos en los cuerpos `.c` fuera de
   comentario. Los que salen son **offsets de registro**, mascaras y campos de la tabla de
   MMIO (`rx550_mmio_access.c`, ~74 registros), y indices de array. **Ninguno es una magnitud
   de la ASIC.**

### 5.3 · EL CASO QUE SE PIDIO BUSCAR EXPLICITAMENTE

> *«Un driver que tiene `8` CU escritos a mano y no lo dice es peor que uno que no lo tiene:
> el primero se cita como autoridad.»*

**Ese caso NO existe en este arbol. Y hay que decirlo con claridad, porque es el resultado
del §5.2:**

**No hay ningun `8` de CU escrito a mano.** No hay ningun numero de CU, ni correcto ni
incorrecto. El driver esta en el dominio de VM/GART/IB y **aun no ha llegado al shader**. Por
lo tanto:

- **No hay ninguna constante inventada que se pueda citar como autoridad falsa.** El riesgo que
  se describia no se ha materializado. Eso es una buena noticia y no hay que disimularla.
- **Pero el riesgo sigue abierto**, y por el motivo opuesto al que se temia: en cuanto alguien
  escriba el primer `RX550_NR_CU`, tendra **el §4 entero** delante. **El riesgo no se ha
  cerrado; se ha displaced.** La mitigacion es §4.3, y por eso va antes que §5.

**Un defecto related, si, y es de la misma familia: dos cadenas de provenance obsoletas.**
`rx550_vmid1_pgt.h:203` dice que el valor demostrado es **10**, y `_Static_assert` en
`rx550_vmid1_pgt_backing.h:376` afirma `DEMOSTRADO != MIN` (o sea, 10 != 9). Pero **dos textos
siguen diciendo 9**, y son exactamente el tipo de cadena que un humano cita como autoridad:

- `rx550_vmid1_pgt.h:292` — `RX550_PGT_ERR_UNSUPPORTED_BLOCK_SIZE = -4, /* block_size != 9 */`
- `rx550_vmid1_pgt.c:698` — `"block_size distinto de 9: no demostrado para GFX8"`

**El codigo no acepta solo 9.** `rx550_vmid1_pgt.c:256-258` acepta el rango `[9, 24]`. **Lo
único incorrecto son las dos cadenas.** No las he tocado.

### 5.4 · DOS AUTORIDADES DEL «512», y estan en el MISMO `.ko`

Este es el defecto mas serio que ha salido de la auditoria, y no lo habia pedido nadie.

`rx550_pdb0.c` esta en la lista de objetos del modulo — `Makefile:30`,
`rx550_drv-objs := ... rx550_pdb0.o rx550_vmid1_pgt.o ...` — y se presenta a si mismo como
**«PDB0 … implementacion CANONICA»** (`rx550_pdb0.h:3`), con **512 entradas y 2 MiB de
cobertura** (`rx550_pdb0.h:9,19,43,46`).

En el **mismo binario**, `rx550_vmid1_pgt.c` calcula la raiz y dice que es lo contrario:

```c
319   uint64_t root_entries;
322   root_entries = ((max_pfn + root_shift - 1u) / root_shift);     /* round_up(max_pfn, 2^block_size) */
323   out->entries_per_level = ...
325   out->root_bytes = root_entries * RX550_VMID1_ENTRY_BYTES;
331   coverage = root_entries * (uint64_t)entries ... << 12
```

Con `block_size = 10` (el demostrado, `rx550_vmid1_pgt.h:203`) y la ventana de **64 GiB**:

```
max_pfn    = 64 << 18                       = 16777216
root_shift = 1 << 10                        = 1024
root_entries = ceil(16777216 / 1024)         = 16384        <-- el componente derivado
cobertura    = 16384 << 12                   = 64 GiB
```

frente a **`RX550_PDB0_ENTRIES = 512`** y **`RX550_PDB0_COVERAGE = 2 MiB`** del otro
componente. **Factor 32 en el numero de entradas del root.**

Y hay una **tercera** autoridad: `target_mem.h:47-48`, `TM_LEVEL_BITS 9` /
`TM_LEVEL_ENTRIES 512`, mas `TM_VA_SIZE` de 1 GiB. Los tres usos de 512 no son
arbitrarios — la cabecera del propio componente lo dice con todas las letras:

> `rx550_vmid1_pgt.h:45` — *«SI SE HARDCODEARA (1, 512, 512), EL CODIGO SERIA INCORRECTO EN EL
> MOMENTO»*

O sea: **alguien ya sabia que el 512 hardcodeado estava mal y lo dejo en dos ficheros
contiguos en lugar de quitarlo.** `RX550_PDB0_COVERAGE` sigue siendo 2 MiB en el `.h` que el
Makefile compila dentro del modulo.

> **NO LO HE TOCADO.** Lo localizo y lo dejo al nodo de implementacion. Nota para ese nodo:
> **no es un cambio de una constante**, es decidir cual de los dos componentes es el canonico
> del root, y si `rx550_pdb0.c` sobrevive como otra cosa (p.ej. una tabla de 2 MiB para un
> subrange) con un nombre que lo diga. El nombre `CANONICA` en `rx550_pdb0.h:3` es hoy falso.

---

## 6 · Lo que el driver tiene que DECIDIR y hoy no puede

### 6.1 · `block_size` de la tabla de paginas — `rx550_vmid1_pgt.h`, `rx550_gart_table.h`

**Lo que el driver ya tiene:** `BLOCK_SIZE_MIN 9`, `BLOCK_SIZE_MAX 24`,
`BLOCK_SIZE_DEMOSTRADO 10` (`rx550_vmid1_pgt.h:198-203`), con el rango derivado de que el
campo `PAGE_TABLE_BLOCK_SIZE` son 4 bits con `PAGE_TABLE_BLOCK_SIZE = block_size - 9`
(`gmc_v8_0.c:933-934`).

**Lo que ya NO puede decidir:**

- **El tope de 24 es del CAMPO, no de la ASIC.** `RX550_VMID1_BLOCK_SIZE_MAX 24u` es
  `9 + 15`. Es una cota de codificabilidad. **No hay ninguna medicion de esta placa que diga
  que esta ASIC llega mas alla de 10.** Marcarlo como tal, o ningun test lo hara.
- **Que valor escribe la referencia esta `NOT_DETERMINED` sin ejecucion.** El 10 viene de la
  aritmetica de `amdgpu_vm.c:2436-2466` con la ventana de esta maquina mas el log de arranque
  (`rx550_vmid1_pgt.h:182-188`). **Es `DERIVADO` + un indicio de log, no una lectura de
  registro.** El unico modo de pasarlo a `MEDIDO_EN_LA_PIEZA` es leer
  `VM_CONTEXT0_CNTL` / `VM_CONTEXT1_CNTL` campo `PAGE_TABLE_BLOCK_SIZE` con MMIO.
  **Propietario: un nodo con MMIO.** Y aviso del finding 1045: en esta tarjeta `boot_vga=1`,
  asi que leer un registro la reanuda. **Eso no se hace sin decidir que se acepta ese coste.**
- **La rama que decide el valor esta condicionada a `num_level > 1`, y `num_level` es siempre
  1.** `amdgpu_vm.c:2464` (`block_size = 9`) es **inalcanzable** en esta ASIC porque
  `max_level = 1`. Asimismo, `MICROARCH-GFX8.md` §3.3 ya avisto que el 9 es el valor de reset de
  **GFX9** (`mmhub_1_0_default.h`), no de esta. **El 9 no es un valor de GFX8**, y las dos
  cadenas obsoletas de §5.3 son la huella de esa contaminacion.

**Del catalogo de §2, esta decision necesita: nada.** Las constantes de shader no entran aqui.
Lo que bloquea esta decision es **una lectura MMIO**, no una constante que falta. **Distinto
de todo lo demas de este informe, y por eso lo digo aparte.**

### 6.2 · La formula de cobertura

**Lo que el driver tiene:** `root_entries = ceil(max_pfn / (1<<block_size))`;
`coverage = root_entries * (1<<block_size) << 12` (`rx550_vmid1_pgt.c:322-334`). Con la
correccion de `e417d64`, ya documentada en `rx550_vmid1_pgt.c:277-300`.

**Lo que no puede decidir:** la cobertura tiene que ser **exactamente la ventana pedida**, y el
driver lo comprueba (`rx550_vmid1_pgt.c:360`, `coverage < vm_size_bytes` ⇒ incoherent). El
problema es que **`block_size` y `root_entries` estan acoplados**, y `root_entries` depende de
la ventana. Con la ventana de 64 GiB salen 16384 entradas de root, y **el componente
`rx550_pdb0.c` del mismo modulo dice 512** (§5.4). **La formula esta; el valor unico del root,
no.**

**Del catalogo: nada que falte.** Es un problema de coherencia interna del driver, no de
conocimiento de la ASIC. **Propietario: nodo de implementacion, con §5.4 como entrada.**

### 6.3 · `RX550_GART_START = 0` — DESIGN_CHOICE, no un hecho

**Lo que el driver tiene:** `RX550_GART_START = UINT64_C(0)` con `RX550_GART_ALIGN = 1 << 32`
(`rx550_spaces.h:55-57`), **declarado bajo el epigrafe `DESIGN_CHOICE` en el propio fichero.**
El driver, ahi, esta siendo correcto: etiqueta su eleccion como eleccion.

**Lo que hay que tener claro, y que el catalogo ahora afianza:**

- **No es un hecho del hardware.** La referencia usa `BEST_FIT` (`gmc_v8_0.c:422`), y con la
  geometria medida de esta placa **esa rama elige la ALTA**: el GART del log de arranque esta en
  **`0x000000FF00000000`**, no en 0. `rx550_gart_geom.h:103-108` ya lo dice.
- **El 0 es la rama LOW** (`amdgpu_gmc.c:316-321`) y con `BEST_FIT` declarado como default
  (`rx550_gart_geom.h:108`) **la eleccion es incoherente consigo misma**: se declara
  `PLACEMENT_DEF = BEST_FIT` y a la vez `GART_START = 0`, que no es lo que `BEST_FIT` produce en
  esta maquina. **Eso si es un defecto, y es de coherencia interna, no de conocimiento.**
- **Consecuencia ya registrada** en `MEMORIA-GFX8.md` §4.6 punto 1: con `GART_START = 0`, la
  identidad `GART_ADDRESS == SYSTEM_PA` solo es cierta **por consecuencia de esa eleccion**.
  El diseño es coherente consigo mismo; lo que no es es una descripcion de la maquina.

**Del catalogo de §2: `gart_size = 256 MiB` es `MEDIDO_EN_FUENTE` (§2.5), y no hay forma de
subirlo a `MEDIDO_EN_LA_PIEZA` por sysfs.** No existe ningun atributo KFD que publique
`gart_size`. El unico caminoseria el log del kernel o el registro `GMC_VM_FB_LOCATION`, que ya
estaimplementado en `rx550_target.c:341-346` (`RX550_GEOM_FB_LOCATION_INDEX 0x809`). **La
cadena existe en el driver; lo que no se ha hecho es ejecutarla.** Propietario: un nodo que
acepte el MMIO.

> **Nota de seguridad de este punto, y es la mas importante de §6:** el acantilado real de la
> memoria es **`placements.lpfn = gart_size >> PAGE_SHIFT`** (`amdgpu_ttm.c:992`), y ahi el fallo
> es **duro, sin degradacion** (`amdgpu_ttm.c:997-998`). Con 256 MiB de ventana son 65536
> paginas. **Un driver propio que no coloque su GART en la misma ventana que la referencia no
> esta comparando su rendimiento con el rendimiento de la referencia**, porque el otro tiene un
> techo de espacio GTT que el nuestro no tiene. `MEMORIA-GFX8.md` §4.4(B) lo desarrolla. **Esto
> no es una constante que falte: es una consecuencia de una `DESIGN_CHOICE` ya escrita.**

---

## 7 · Lo que FALTA, ordenado por nº de sitios de decision que desbloquea

Orden **por decision sites**, no por importancia teorica. Un sitio de decision = un punto del
codigo que necesita la cifra y hoy la pone a ojo, la deja en un literal, o no puede existir.
Como §5.2 demuestra que el driver aun no ha llegado al shader, **la mayoria de estos sitios son
prospectivos**; lo digo en cada fila, porque un ranking de desbloqueos imaginarios no es un
ranking.

| # | constante | valor | grado | sitios que desbloquea | quien la tiene |
|---|---|---|---|---|---|
| **1** | **nº de CU, partida en dos** | **8** (capacidad) / **10** (span de ids) | `DERIVADO`+corroborado / `CONFLICTADO` | **5**, y es el unico que obliga a **dos** constantes en vez de una (§4.3): (a) dimension de `cwsr` y pila de control; (b) techo de oleadas y modelo de ocupacion; (c) reparto de un dispatch entre CU en PM4; (d) reparto de contadores `*_CU_FULL_*`; (e) atribucion de rebanadas de cache a su CU | **ya medido (§2.2, §4). No bloqueado. Lo unico que falta es escribirlo bien.** |
| **2** | **bytes de un slot de scratch** | — | `NO_DETERMINED` | **bloquea un subsistema entero**, no una linea: sin el no se puede dimensionar la pagina de scratch ni colocar un manejador de traps. Depende de (1) para el total por CU | **firmware del SQ/RLC.** No hay forma indirecta conocida. **Ítem que puede quedarse abierto mucho tiempo.** |
| **3** | **techo de oleadas / `wave_num`** | **320** | `DERIVADO`+corroborado | **4**: (a) reserva de contexto; (b) presupuesto de traps CWSR; (c) `COMPUTE_TMPRING_SIZE` si alguna vez se programa; (d) cualquier calculo de ocupacion | **ya medido.** Depende de (1) |
| **4** | **bytes de contexto por CU (VGPR/SGPR/LDS/HWREG)** | **348160 = 0x55000** | `MEDIDO_EN_FUENTE` | **3**, todos de la misma familia: `cwsr_size`, datos de wave-group, y el desglose que hace falta para el *performance* (saber que 262144 de esos 348160 B son VGPR es saber el 75 % del area de contexto) | **`MEDIDO_EN_FUENTE`, sin contraparte en la pieza.** Corroborable con el mismo argumento que (1): el `cwsr_size` medido sale bien con 0x55000 |
| **5** | **VGPR = 256 / SGPR = 102** | `256` / `102` | `MEDIDO_EN_FUENTE` | **3**: `PGM_RSRC1.VGPRS` al emitir un dispatch, `SPI_RESOURCE_RESERVE_CU_x.VGPR`, y el reparto de ocupacion | **fuente.** Depende de un emisor de shaders, que **no existe** (§2.8) |
| **6** | **clocks: `fcompute` 1071, banco 1500** | `1071` / `1500` | `MEDIDO_EN_LA_PIEZA` | **3**: (a) timeouts de fence y de PM4; (b) cualquier conversion de bytes/s **si** se confirma la unidad; (c) criterio de *sustained* frente a *burst* (§72 del AGENTS) | **ya medido**, pero **la unidad de `mem_clk_max` no esta verificada** — no multiplicar todavia |
| **7** | **`num_cp_queues` = 24** | `24` | `MEDIDO_EN_LA_PIEZA` | **2**+(a) tope de colas concurrentes; (b) planificacion de contexto. **Y arrastra la descomposicion MEC/pipes (§2.4), que si es `NO_DETERMINED`** | **medido el total. La descomposicion no esta en ninguna parte** |
| **8** | **SDMA: 2 motores x 2 colas** | `4` colas | `MEDIDO_EN_LA_PIEZA` | **2**: (a) reparto de la produccion de PTEs; (b) plan de canales para copia de memoria. Relevante: el corpus usa SDMA para producir PTEs (`finding 023`) | **ya medido** |
| **9** | **no hay L2** | — | `MEDIDO_EN_LA_PIEZA` | **2**, y las dos son **negativas** y por eso son valiosas: impide diseñar para L2, y permite afirmar que `cache_line_size` = 64 B es el unico nivel de cache que existe | **ya medido.** Cierra el vacio que dejo `finding 265` |
| **10** | **`cache_line_size` = 64 B** | `64` | `MEDIDO_EN_LA_PIEZA` | **2**: (a) unidad de cualquier lectura de caché; (b) criterio de granularidad para accesos del shader | **ya medido** |
| **11** | **`max_hw_contexts` = 8** | `8` | `MEDIDO_EN_FUENTE` | **2**: (a) reparto de VMID/contexto; (b) techo global de oleadas. **Y choca con dos constantes del driver** (`TVM_NR_CTL_CONTEXTS 2`, `RX550_GMC_NR_VMIDS 16`), ninguna corroborada | **fuente.** Corroborable por MMIO |
| **12** | **significado de `type` 9 / 10** | — | `NO_DETERMINED` | **1**, pero **desbloquea 4 celdas**: data/instruction, y por tanto que se puede distinguir una cache de codigo de una de datos | **cabecera UAPI de KFD, ausente del corpus** |
| **13** | **bits de `HSA_CAP_*`** | — | `NOT_FOUND` | **1**, y bloquea decodificar `capability`/`capability2` enteros, o sea **toda la palabra de capacidades HSA** | **cabecera UAPI de KFD, ausente del corpus** |
| **14** | **bits de `num_cu_per_array` que explicarían el 5-vs-8** | — | `HYPOTHESIS` (§4.2) | **0 sitios de codigo. Pero es la unica via para cerrar §4 sin MMIO**, y §4 gobierna el item 1 | **`kfd_crat.h:104-117` no documenta unidades.** Necesita la especificacion ACPI/CRAT, que no esta en el corpus |

**El bloque 1-5 es el shader. El bloque 6-11 es la capacidad de la pieza. El bloque 12-14 es
puertas cerradas por cabeceras ausentes.**

**Y una honestidad sobre el ranking:** los items 1, 3, 4, 6, 8, 9, 10 **ya estan medidos**.
No son huecos de informacion: son huecos de **escritura en el driver**, que es exactamente el
trabajo que este nodo tiene prohibido hacer. **La restriccion dura de este nodo es, en la
practica, el cuello de botella que queda**, y conviene que quede escrito asi.

---

## 8 · Estado de salida

```
PROVEN            sysfs de esta maquina: 32 SIMD, 4 SIMD/CU, wave64, 64 KiB LDS/CU, 32 slots
                  scratch/CU, 2 arrays, 1 array/engine, array_count 2, 16 caches todas L1 de
                  16 o 32 KiB con linea de 64 B, SIN L2, VRAM 2 GiB de ancho 64, 2 motores
                  SDMA x 2 colas, 24 colas de CP, ctl_stack 4096, cwsr 2789376, fcompute 1071,
                  revision PCI 0xC7.  Y las 16 cachés NO vienen de dummy_cache_info (que tiene
                  un L2 que aquin o aparece): vienen del CRAT real.

CORROBORADO_2_VIAS  target_version 80003 (sysfs | kfd_device.c:293-296)
                  device 0x699F (sysfs | amdgpu_drv.c:2034-2041), vendor 0x1002
                  simd_per_cu 4 (CRAT | gfx_8_0_enum.h:6832)
                  max_waves_per_simd 10, wave_front_size 64, lds 64 KiB, 32 slots
                      (los cuatro: CRAT de esta maquina | gfx_v8_0.c:7122-7125)
                  CU = 8 (CRAT 32/4, con la aritmetica de cwsr_size cerrando | via
                      independiente: array_count x (32/2)/4 = 4 CU por array)
                  VRAM 2 GiB (CRAT de esta maquina | rx550_gart_geom.h:181, del driver propio)
                  ctl_stack_size 4096 y cwsr_size 2789376 (sysfs | kfd_queue.c:480-511)

DERIVADO          techo de oleadas 320; 65536 entradas de tabla GART; 512 KiB; PA 2^40;
                  4 colas de SDMA; 320 KiB de L1 total; 4 CU por array

CONFLICTADO       cu_per_simd_array = 5 frente a simd_count/simd_per_cu = 8.  NO reconcilian,
                  y ambos lados son load-bearing y tienen discriminante medido (§4.2):
                  cwsr_size obliga a 8; las 16 caches publicadas obligan a >= 10.
                  ancho de SQ_WAVE_GPR_ALLOC.SGPR_SIZE: 3 bits (ensamblador de AMD) frente a
                  4 (mapa de registros).  CONFLICT de AMD, con su FIXME declarado.

REFUTED           la hipotesis de 64 colas de computo de MICROARCH-GFX8.md §3.2: el medido
                  son 24, y 2 MEC x 4 pipes x 8 colas = 64.  Con ella queda refutado para
                  GFX8 el esquema "4 pipes x 8 colas" que AMD declara para GFX9.

NO_DETERMINADO    bytes de un slot de scratch (firmware SQ/RLC); funcion de reparto de oleadas
                  (firmware SQ/RLC); significado del campo LDS de SPI_RESOURCE_RESERVE_CU_x;
                  unidades de mem_clk_max; descomposicion de las 24 colas de CP
                  (cp_queue_bitmap, no es una constante); lectura real de SPI_CSQ_WF_ACTIVE_*
                  (requiere MMIO)

NOT_FOUND         en el CORPUS, con propietario: bits HSA_CAP_* y HSA_CACHE_TYPE_*
                  (cabecera UAPI de KFD ausente); unidades de los campos de la CRAT
                  (kfd_crat.h no las documenta); la especificacion CRAT/ACPI que explicaria
                  num_cu_per_array

HYPOTHESIS        que num_cu_per_array signifique "SIMD por array" y no "CU por array": encaria
                  con el 5 y con el 10 y explicaria la persistencia del conflicto. NO usada
                  para nada.

DERIVADO_AQUI     el valor de block_size que escribe la referencia (10): sale de la aritmetica
                  de amdgpu_vm.c con la ventana de esta maquina, mas un log de arranque.
                  Para subirlo a MEDIDO_EN_LA_PIEZA hace falta MMIO, y finding 1045 avisa de
                  que en esta tarjeta eso reanuda la GPU.

DEFECTOS ENCONTRADOS, NO CORREGIDOS (restriccion dura de este nodo)
  D1  dos autoridades del 512, en el MISMO .ko: rx550_pdb0.h:43 (512 entradas, 2 MiB, declarada
      "CANONICA") contra rx550_vmid1_pgt.c:322-334 (16384 entradas, 64 GiB). .Makefile:30
      compila los dos.  rx550_vmid1_pgt.h:45 ya advertia del error.  Propietario:
      implementacion.
  D2  dos cadenas de provenance obsoletas que dicen "9": rx550_vmid1_pgt.h:292 y
      rx550_vmid1_pgt.c:698.  El codigo acepta [9,24] (rx550_vmid1_pgt.c:256-258).
      Propietario: implementacion.
  D3  RX550_GART_PLACEMENT_DEF = BEST_FIT (rx550_gart_geom.h:108) con
      RX550_GART_START = 0 (rx550_spaces.h:56): el BEST_FIT de esta maquina da 0xFF00000000.
      Incoherente consigo mismo.  Propietario: implementacion.
  D4  literales duplicados sin nombre: 18u en rx550_vmid1_pgt.c:101 (= RX550_VM_PFN_SHIFT),
      9u en :106 y :271 (= RX550_VM_BLOQUE_OFFSET).  Valores correctos hoy; si cambia la
      constante, el literal no la sigue.  Propietario: implementacion.
  D5  NO hay ningun "8 CU escrito a mano".  No hay constantes de geometria de shader en el
      driver, ni correctas ni inventadas (§5.2).  El riesgo no se ha cerrado: se ha desplazado
      al momento en que se escriban, y §4.3 dice como escribirlas.
```

### Refutadores de este informe, en una linea cada uno

| afirmacion | que la refutaria |
|---|---|
| 8 CU | `amdgpu_gca_config` con `max_cu_per_sh = 5`; o `cwsr_size != 2789376` |
| 16 caches reales | que las 16 entradas viniesen de `dummy_cache_info` — **refutado**: esa tabla tiene 5 entradas y un L2, y no hay L2 medido |
| el 10 es correcto en esta placa | `max_waves_per_simd != 10` en una relectura de sysfs |
| el 24 es el total de colas de CP | que `cp_queue_bitmap` se poblara distinto en otro arranque |
| `type` 9/10 = data/instr | la cabecera UAPI de KFD, que no esta |
| VRAM 2 GiB | `mem_banks/0/size_in_bytes != 2147483648` |
| las unidades de `mem_clk_max` | la documentacion HSA/KFD |

---

## 9 · Citas

**Medido en esta pieza (sysfs, lectura de fichero de texto, sin ioctl):**
- `/sys/class/kfd/kfd/topology/nodes/0/properties`, `nodes/0/mem_banks/0/properties`
- `/sys/class/kfd/kfd/topology/nodes/1/properties`, `name`, `mem_banks/0/properties`, `caches/0..15/properties`
- `/sys/bus/pci/devices/0000:01:00.0/revision`

**Corpus** — prefijo `K/` = `RESEARCH/working/linux-7.1.3/`:
- `K/drivers/gpu/drm/amd/amdkfd/kfd_crat.c:968-1019` (dummy_cache_info), `:1036-1044` (los nueve campos), `:1173-1189` (cache→CU), `:1208-1215`
- `K/drivers/gpu/drm/amd/amdkfd/kfd_crat.h:104-117`, `:158-167`
- `K/drivers/gpu/drm/amd/amdkfd/kfd_queue.c:401-452` (los cuatro tamanos por CU), `:454-469` (get_num_waves), `:476`, `:480-511`
- `K/drivers/gpu/drm/amd/amdkfd/kfd_topology.c:437-522` (sysfs), `:2090-2091` (simd_arrays_per_engine), `:2106-2107`, `:2127`, `:2129`, `:2144-2149`, `:2166-2174`, `:325-359` (kfd_cache_show)
- `K/drivers/gpu/drm/amd/amdkfd/kfd_device_queue_manager.c:97-101` (get_cp_queues_num), `:113-123`
- `K/drivers/gpu/drm/amd/amdkfd/kfd_device.c:293-296`
- `K/drivers/gpu/drm/amd/amdkfd/cwsr_trap_handler_gfx8.asm:44,306,319,720-722,728,737-739`
- `K/drivers/gpu/drm/amd/amdgpu/gfx_v8_0.c:783-791,1389,1688,1899-1901,1910-1911,7122-7125`
- `K/drivers/gpu/drm/amd/amdgpu/amdgpu_drv.c:2034-2041`
- `K/drivers/gpu/drm/amd/amdgpu/gfx_v8_0.h` / `amdgpu_amdkfd_gfx_v9.c:1050-1054`
- `K/drivers/gpu/drm/amd/include/asic_reg/gca/gfx_8_0_enum.h:2816,2822,6832`
- `K/drivers/gpu/drm/amd/include/asic_reg/gca/gfx_8_0_sh_mask.h:8317,14461-14462`
- `K/drivers/gpu/drm/amd/amdgpu/amdgpu_gfx.h:79` (NUM_XCC)
- `K/drivers/gpu/drm/amd/amdgpu/gmc_v8_0.c:416-418,422,595,933-934,960,1127,1133`
- `K/drivers/gpu/drm/amd/amdgpu/amdgpu_gart.c:533`, `amdgpu_ttm.c:988-998`, `amdgpu_kms.c:1453`
- `K/drivers/gpu/drm/amd/amdgpu/amdgpu_vm.c:2368-2379,2391-2478,2464,2466`, `amdgpu_vm_pt.c:58-107`

**Informes de este arbol, leidos y no repetidos:**
- `08-ARQUITECTURA/MICROARCH-GFX8.md` §1, §2.2-2.5, §3.2-3.4, §5.1-5.3, §7
- `08-ARQUITECTURA/MEMORIA-GFX8.md` §4.4(B) `:698-724`, §4.6 `:755-783`, `:966-967`
- `06-INGENIERIA-INVERSA/findings/265-el-tamano-de-cache-de-gfx8-no-esta-en-ningun-sitio.md` (via `MICROARCH-GFX8.md` §3.4)
- `06-INGENIERIA-INVERSA/findings/1045-…`, `1046-…` (via el encargo; no releidos, no re-derivados)

**Driver propio, LEIDO y NO MODIFICADO:**
- `Makefile:30` · `target_match.h:40-59` · `target_mem.h:43-94` · `target_vm.h:56-82` · `target_regs.h:42` · `target_resource.h:38,56`
- `rx550_spaces.h:50-57` · `rx550_gart_geom.h:53-108,180-181` · `rx550_gart_table.h:22-45,96,105` · `rx550_gart_write.h:58`
- `rx550_vmid0_gart.h:76-91,111-138,182` · `rx550_vmid1_pgt.h:20-60,150-161,198-213,230-261,292` · `rx550_vmid1_pgt.c:77-108,255-276,319-336,360,680-715`
- `rx550_vmid1_pgt_backing.h:349-376` · `rx550_vm_geom.h:70-114` · `rx550_vm_geom.c:69-187` · `rx550_pdb0.h:1-57` · `rx550_pdb0.c:1-30`
- `rx550_mmio.h:34-36` · `rx550_mmio_access.c:760-762` · `rx550_dummy_page.h:196-202` · `rx550_vram_pool.h:65` · `rx550_vram_pool.c:28` · `rx550_gart_seq.h:92,161`

**Renumeracion: ninguna.** No he creado ningun ID nuevo. No he editado ningun fichero del arbol
salvo este.