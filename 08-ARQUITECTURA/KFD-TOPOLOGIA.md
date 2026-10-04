# KFD-TOPOLOGIA — nodo KFD, 4 contradicciones, catálogo sysfs

**Nodo**: `KFD-TOPOLOGIA`
**Fecha**: 2026-10-04
**Kernel en ejecución**: `7.1.3-200.nobara.fc44.x86_64` (`/proc/version`)
**GPU observada**: `card1` = amdgpu, RX550 (PCI 0000:01:00.1), nodo KFD `1`

Todo lo de abajo está etiquetado:
`MEDIDO_AQUI` (leído en esta sesión) · `LEIDO_EN_CORPUS` (código, con fichero:línea) ·
`INFERIDO` (deducción con evidencia) · `NOT_DETERMINED` (no se puede con lo disponible).

---

## 0. CORRECCIONES PREVIAS AL ENCARGO (importan para todo lo demás)

Cuatro cosas que el encargo daba por buenas y **no lo son**. Se registran antes que las
contradicciones porque cambian cómo se citan.

### 0.1 `include/linux/kfd.h` NO EXISTE en el corpus. `MEDIDO_AQUI`

Barrido de todo el árbol del proyecto buscando ese fichero:

```
###  kfd.h 0        (0 ficheros en todo /home/lucas/Escritorio/RX550-INVESTIGACION)
```

No está en ninguna de las 4 copias del kernel. **La taxonomía de tipos de caché no está
donde se dijo.** Está en `include/uapi/linux/kfd_sysfs.h` (§1). Quien trayó un
`CACHE_TYPE_*` de otra versión de KFD importó un nombre ajeno a este kernel.

### 0.2 `drivers/gpu/drm/amd/amdgpu/amdgpu_hwmon.c` NO EXISTE en el corpus. `MEDIDO_AQUI`

```
hwmon-named files in corpus: 97      -> todos Documentation/** y evidencia del proyecto
amdgpu dir entries: 638
hwmon/sensor files: NONE
amdgpu_hwmon.c: ABSENT
```

El corpus de `amdgpu/` está **podado**: 304 `.c` presentes, pero ausentes
`amdgpu_pm.c`, `amdgpu_hwmon.c`, `amdgpu_smu.c`, `amdgpu_pci.c`. Consecuencia directa:
**22 de los atributos sysfs de esta GPU no se pueden clasificar desde el código de este
corpus.** Ver §5.3.

### 0.3 `amdgpu_kms.c` NO contiene ningún `amdgpu_show_*`. `LEIDO_EN_CORPUS`

```
total lines: 2002
sysfs attr macros in amdgpu_kms.c: 0
amdgpu_show_* functions found: 0
```

En esta versión los atributos sysfs no viven en `amdgpu_kms.c`. Están repartidos: los que
sí están en el corpus se definen en `amdgpu_vram_mgr.c`, `amdgpu_gtt_mgr.c`,
`amdgpu_preempt_mgr.c`, `amdgpu_atombios.c`, `amdgpu_device.c`.

Lo que **sí** se sostiene del encargo: `amdgpu_kms.c:1453` es literalmente
`r = pm_runtime_get_sync(dev->dev);`, dentro de la función de `open` del nodo render
(followed por `kzalloc` de `fpriv` y `amdgpu_pasid_alloc`). Cita correcta.

### 0.4 KFD está compilado DENTRO de `amdgpu.ko`, no como módulo `amdkfd`. `MEDIDO_AQUI`

Esto no estaba en el encargo y explica por qué `amdkfd` no aparece por ningún lado:

```
ls -d /sys/module/amdkfd        -> No existe el fichero o el directorio
/proc/modules                   -> amdgpu, amdxcp, ... ; NINGÚN amdkfd
```

ParecíaKFD ausente, pero `/proc/devices` tiene `237 kfd` y `/dev/kfd` existe. Mi primer
conteo de símbolos dio **0** `kfd_*`, y estuve a punto de escribir `PROVEN_ABSENT`: era un
**bug de índice de campo** mío — en `/proc/kallsyms` el nombre es el campo 3, no el 2.
Corregido (kallsyms sí es legible: 380 979 líneas, `kptr_restrict=0`):

```
total kfd_/amdkfd symbols: 379
    kfd_initialized        [amdgpu]
    kfd_client_funcs       [amdgpu]
    kfd_ioctl_get_version  [amdgpu]
    ...
top module tags: [amdgpu] 63248   [i915] 18999   ...
```

**Los 379 símbolos `kfd_*` llevan la etiqueta `[amdgpu]`.** Confirmado contra el binario
en disco:

```
decompressed size: 37494368
  cu_per_simd_array        occurrences=2
  processor_id_low         occurrences=3
  cache_lines_per_tag      occurrences=1
  cpu_cores_count          occurrences=2
```

Esas cadenas sysfs están **dentro de `amdgpu.ko`**. Por eso `amdkfd` no existe como módulo
y por eso el árbol `/sys/class/kfd` existe y lo produjo `amdgpu.ko`.

> `NOT_DETERMINED`: por qué esta build enlaza KFD en amdgpu y no aparte. La fuente de
> `amdkfd` en el corpus no incluye los ficheros de integración y `/usr/src/kernels/` no
> trae ningún `.c` de driver (148 `.c`, todos en `scripts/`), así que no se puede confirmar
> la causa. No afecta a nada de lo que sigue.

### 0.5 Identidad del corpus. `MEDIDO_AQUI`

Hay 4 copias del kernel. Sólo una es árbol completo:

| Árbol | `kfd_topology.c` | completo |
|---|---|---|
| `RESEARCH/kernelbuild/linux-7.1.3` | `6f98a156aab265ca` | **árbol completo** (`Makefile` VERSION 7/PATCHLEVEL 1/SUBLEVEL 3) |
| `RESEARCH/baseline/linux-7.1.3` | `6f98a156aab265ca` | sólo 3 entradas (Documentation, drivers, include) |
| `RESEARCH/working/linux-7.1.3` | `6f98a156aab265ca` | sólo 3 entradas |
| `rx550-upstream-7.2.8/linux-7.2.8` | `eaf97cd32b63bfcb` | **otra versión** — no usada |

Las tres 7.1.3 tienen `kfd_topology.c` **byte-idéntico**. Se cita `RESEARCH/kernelbuild/`
por ser el árbol completo. `7.2.8` queda fuera por.version.

**Limitación de honestidad**: el código fuente del kernel *en ejecución* **no está en esta
máquina** (`/usr/src/kernels/7.1.3.../drivers/gpu/drm/amd/amdkfd/` contiene sólo `Kconfig`
y `Makefile`). Lo que se lee es un árbol upstream 7.1.3, no el binario que produjo el
sysfs. Corroboración: `amdgpu_kms.c:1453` coincide exactamente con lo que el encargo
atribuyó al kernel corriendo, y la simulación de §4 reproduce los 16 cachés campo a campo
(§4.3). Eso es `CORROBORATED`, no `PROVEN`.

Hashes de las fuentes citadas (sha256, 16 hex):

```
6f98a156aab265ca  72038B  amdkfd/kfd_topology.c
f22f50b56a1da8da  71179B  amdkfd/kfd_crat.c
0fdbfa25304ff4b7   5841B  amdkfd/kfd_topology.h
1f26e1ea4a679b80   5450B  include/uapi/linux/kfd_sysfs.h
f59ff7fdab93a774  59741B  amdgpu/amdgpu_kms.c
660f40f1af97f39a 191231B  amdgpu/amdgpu_device.c
5e10ee151c4b1add  26606B  amdgpu/amdgpu_vram_mgr.c
0ef553b4c84d164e  10477B  amdgpu/amdgpu_gtt_mgr.c
da1ac6e2c7e34aa8  60399B  amdgpu/amdgpu_atombios.c
46c70794b62bd07d   6231B  amdgpu/smuio_v15_0_8.c
6a87329b456127f4   4336B  amdgpu/amdgpu_preempt_mgr.c
```

### 0.6 Formato real del sysfs. `MEDIDO_AQUI`

Confirmado: `clave valor` separada por **un espacio**, valores en **decimal**, sin `=`.
`properties` de `nodes/1` es un fichero único con 41 líneas. Las cachés tienen un único
fichero `properties` (no un fichero por atributo). Los valores de `processor_id_low` están
en **decimal**: el texto es `2147487745`, que es `0x80001001`.

> Corregir aquí: el encargo interpretó `2147487745` como `0x80000001`. **Es `0x80001001`**
> (la diferencia es `0x1001`, no `0x0001`). Ver §3.

---

## 1. CONTRADICCIÓN (1) — `type 9` y `type 10`

### 1.1 No son un enum: son flags. `LEIDO_EN_CORPUS`

`include/uapi/linux/kfd_sysfs.h:92-97`:

```c
/* Cache types in cache properties */
#define HSA_CACHE_TYPE_DATA		0x00000001
#define HSA_CACHE_TYPE_INSTRUCTION	0x00000002
#define HSA_CACHE_TYPE_CPU		0x00000004
#define HSA_CACHE_TYPE_HSACU		0x00000008
#define HSA_CACHE_TYPE_RESERVED		0xfffffff0
```

El comentario lo dice literalmente: **"Flag bits in cache properties"**. No hay
`CACHE_TYPE_*` ordinal. Descomposición:

| type | hex | bits | lectura |
|---|---|---|---|
| `9` | `0x9` | `0x1 \| 0x8` | **DATA \| HSACU** → caché de **DATOS**, ámbito CU HSA |
| `10` | `0xA` | `0x2 \| 0x8` | **INSTRUCTION \| HSACU** → caché de **INSTRUCCIÓN**, ámbito CU HSA |

Asignación: `kfd_topology.c:1645-1652` (camino no-CRAT) y `kfd_crat.c:1208-1215` (CRAT):

```c
if (pcache_info[cache_type].flags & CRAT_CACHE_FLAGS_DATA_CACHE)
        pcache->cache_type |= HSA_CACHE_TYPE_DATA;
if (pcache_info[cache_type].flags & CRAT_CACHE_FLAGS_INST_CACHE)
        pcache->cache_type |= HSA_CACHE_TYPE_INSTRUCTION;
if (pcache_info[cache_type].flags & CRAT_CACHE_FLAGS_CPU_CACHE)
        pcache->cache_type |= HSA_CACHE_TYPE_CPU;
if (pcache_info[cache_type].flags & CRAT_CACHE_FLAGS_SIMD_CACHE)
        pcache->cache_type |= HSA_CACHE_TYPE_HSACU;
```

El bit `HSACU` (0x8) viene de `CRAT_CACHE_FLAGS_SIMD_CACHE`. Por eso **todos** los
cachés de esta GPU tienen el bit 0x8 puesto: los 16 son `0x8 | (DATA|INST)`.

**Respuesta a la pregunta**: las **12 de `type 9` son de DATOS**; las **4 de `type 10`
son de INSTRUCCIÓN**. `PROVEN`.

### 1.2 Por qué 12+4 y no 8+8. `LEIDO_EN_CORPUS` + `MEDIDO_AQUI`

Polaris12 **no tiene tabla propia**: `kfd_crat.c:130` la define como alias de Carrizo.

```c
kfd_crat.c:130:  #define polaris12_cache_info carrizo_cache_info
```

Servida en `kfd_crat.c:1613-1616`:

```c
case CHIP_POLARIS12:
        *pcache_info = polaris12_cache_info;
        num_of_cache_types = ARRAY_SIZE(polaris12_cache_info);
        break;
```

`carrizo_cache_info` (`kfd_crat.c:90-123`) tiene **3** entradas, no 2:

| # | comentario en el código | size | level | line | flags | `num_cu_shared` | → type HSA |
|---|---|---|---|---|---|---|---|
| 0 | `TCP L1 Cache per CU` | 16 | 1 | 64 | DATA\|SIMD | **1** | **9** |
| 1 | `Scalar L1 Instruction Cache (in SQC module) per bank` | 32 | 1 | 64 | INST\|SIMD | **4** | **10** |
| 2 | `Scalar L1 Data Cache (in SQC module) per bank.` | 16 | 1 | 64 | DATA\|SIMD | **4** | **9** |

**Ahí está el 12+4.** Las 12 de datos = 8 (entrada 0, `num_cu_shared=1`, una por CU) + 4
(entrada 2, `num_cu_shared=4`, una por banco de SQC). Las 4 de instrucción = entrada 1,
`num_cu_shared=4`.

No es "8+8" porque **hay dos cachés de datos distintas** en la tabla de Carrizo: la TCP L1
por CU y la Scalar L1 del SQC por banco. El desglose 8+4 sale de la propia tabla, no de
una decisión de KFD ni de una propiedad de la ASIC.

Y el orden de los índices sysfs lo confirma: la lista se rellena con
`list_add_tail` en orden `ct` (`kfd_topology.c:1821-1863`), así que

- `caches 0..7` = entrada 0 (datos, `num_cu_shared=1`) → **8** entradas, **una por CU**
- `caches 8..11` = entrada 1 (instrucción, `num_cu_shared=4`) → **4**
- `caches 12..15` = entrada 2 (datos, `num_cu_shared=4`) → **4**

`MEDIDO_AQUI` — confirmado:

```
cache  0: type= 9 ... size= 16 pid_low=2147487745
cache  7: type= 9 ... size= 16 pid_low=2147487753
cache  8: type=10 ... size= 32 pid_low=2147487745
cache 11: type=10 ... size= 32 pid_low=2147487753
cache 12: type= 9 ... size= 16 pid_low=2147487745
cache 15: type= 9 ... size= 16 pid_low=2147487753
```

Predice 12+4 y acierta; reparte 8+4+4 y acierta; los tamaños 16/32/16 y `cls=64` en todos
ciertas la tabla. `CORROBORATED`.

### 1.3 Descartado: que estos cachés vengan del CRAT de firmware

`kfd_crat.c:1206` pone `sibling_map_size = CRAT_SIBLINGMAP_SIZE` (128) en el camino CRAT;
`kfd_topology.c:1668` pone `sibling_map_size = 4` en el camino no-CRAT. El show emite
`kfd_topology.c:350-354`: `sibling_map_size` bytes × 8 valores.

`MEDIDO_AQUI`:

```
cache  0: sibling_map_values=   32   ones_at=[0]
cache  8: sibling_map_values=   32   ones_at=[0, 1, 2]
```

**32 valores = `sibling_map_size` 4** → camino **no-CRAT**. Si hubiera pasado por CRAT
salirían 1024 valores. **Descartado el CRAT**, y por tanto la tabla de Carrizo es la
fuente efectiva, no una descripción de firmware. Esto es lo que hace el resto del análisis
sólido.

---

## 2. CONTRADICCIÓN (2) — `cu_per_simd_array = 5` contra `32/4 = 8`

### 2.1 De dónde sale cada número. `LEIDO_EN_CORPUS`

Las dos propiedades se emiten tal cual en `kfd_topology.c:461-469` (sin aritmética), y se
llenan en `kfd_populated_cu_info_gpu` (`kfd_crat.c:1041-1043`) desde el campo homónimo del
subtipo CU del CRAT:

```c
kfd_crat.c:1041:  dev->node_props.array_count      = cu->array_count;
kfd_crat.c:1042:  dev->node_props.cu_per_simd_array = cu->num_cu_per_array;
kfd_crat.c:1043:  dev->node_props.simd_per_cu       = cu->num_simd_per_cu;
```

Y esos campos los pone `kfd_create_crat_image_virtual` (`kfd_crat.c:2282-2295`), que es
el que genera el CRAT virtual cuando no hay CRAT de ACPI:

```c
kfd_crat.c:2282:  cu->num_simd_per_cu = cu_info->simd_per_cu;
kfd_crat.c:2283:  cu->num_simd_cores  = cu_info->simd_per_cu *
kfd_crat.c:2284:          (cu_info->number / kdev->kfd->num_nodes);
kfd_crat.c:2288:  cu->array_count     = gfx_info->max_sh_per_se *
kfd_crat.c:2289:          gfx_info->max_shader_engines;
kfd_crat.c:2290:  total_num_of_cu     = (cu->array_count * gfx_info->max_cu_per_sh);
kfd_crat.c:2291:  cu->processor_id_low = get_and_inc_gpu_processor_id(total_num_of_cu);
kfd_crat.c:2292:  cu->num_cu_per_array = gfx_info->max_cu_per_sh;
```

**Las dos cifras no son el mismo tipo de cosa:**

| sysfs | campo | expresión | qué es |
|---|---|---|---|
| `cu_per_simd_array` = **5** | `num_cu_per_array` | `gfx_info->max_cu_per_sh` | **capacidad máxima** de CU por SH (incluye CU enmascaradas) |
| `simd_count`/`simd_per_cu` = **8** | `num_simd_cores / num_simd_per_cu` | `cu_info->number / num_nodes` | **CU activas** en el ASIC |

`5` viene de IP discovery (`gfx.config.max_cu_per_sh`). `8` viene de la cuenta de CU
habilitadas (`cu_info->number`). **KFD los llama con nombres que parecen multiplicables y
no lo son.**

### 2.2 Cuál de los dos es la cuenta de CU de esta ASIC

**El 8.** `PROVEN` por dos rutas independientes:

1. `simd_count = 32 = simd_per_cu(4) × number/num_nodes` ⇒ `number/num_nodes = 8`.
   Con `num_nodes = 1` (=`amdgpu_xcp_get_num_xcp`, `kfd_device.c:747`; esta GPU es un solo
   XCP, coherente con `num_xcc 1` medido) ⇒ **`cu_info->number = 8`**.
   El valor `num_nodes=1` es `INFERIDO` (no hay sysfs que lo exponga), pero la conclusión
   no depende de él: ver punto 2.

2. La entrada 0 de la tabla (`num_cu_shared=1`, una caché por CU) produce **exactamente 8
   entradas** medidas, y el número de entradas de esa fila es el número de **bits activos
   en el bitmap de CU**. 8 entradas ⇒ 8 CU activas. Esta vía **no** usa `num_nodes`.

### 2.3 Y `array_count = 2` no contradice nada. `LEIDO_EN_CORPUS`

```c
kfd_topology.c:461-463:
  sysfs_show_32bit_prop(buffer, offs, "array_count",
                        dev->gpu ? (dev->node_props.array_count *
                        NUM_XCC(dev->gpu->xcc_mask)) : 0);
kfd_topology.c:2090-2091:
  dev->node_props.simd_arrays_per_engine = gfx_info->max_sh_per_se;
```

Con `max_sh_per_se = 1` (`simd_arrays_per_engine` medido = 1) y `NUM_XCC = 1`:
`array_count = 1 × max_shader_engines = 2` ⇒ **2 SE, 1 SH por SE**.

### 2.4 Reconciliación final

```
2 SE × 1 SH        = 2 SH          -> array_count = 2            (medido 2)  OK
1 CU-cap × 5       = max_cu_per_sh = 5                          (medido 5)  OK
4 CU activas × 2   = 8 CU activas                               (medido 8)  OK
espacio de ids: array_count × max_cu_per_sh = 2 × 5 = 10        (medido: ids hasta base+9)  OK
```

`5` es **por SH**; `8` es **el total**. No es la misma magnitud. Con `2` SH, 5 por SH daría
10 si las 10 estuvieran activas; hay 8 activas y 2 huecos (§3). **Las dos cifras son
correctas y no se reconcilian porque no son la misma magnitud.**

---

## 3. CONTRADICCIÓN (3) — los `processor_id_low`

### 3.1 Hay 8 ids distintos, no 9. `MEDIDO_AQUI`

El encargo cuenta 9 ids y "id 5 → ninguna". Eso es un artefacto de asumir que el rango
1..9 está lleno. Reparto real, leído del sysfs:

```
  text= 2147487745  hex=0x80001001  low32=...  caches=[(0,'9','16'), (8,'10','32'), (12,'9','16')]
  text= 2147487746  hex=0x80001002                caches=[(1,'9','16')]
  text= 2147487747  hex=0x80001003                caches=[(2,'9','16')]
  text= 2147487748  hex=0x80001004                caches=[(3,'9','16'), (9,'10','32'), (13,'9','16')]
  text= 2147487750  hex=0x80001006                caches=[(4,'9','16'), (10,'10','32'), (14,'9','16')]
  text= 2147487751  hex=0x80001007                caches=[(5,'9','16')]
  text= 2147487752  hex=0x80001008                caches=[(6,'9','16')]
  text= 2147487753  hex=0x80001009                caches=[(7,'9','16'), (11,'10','32'), (15,'9','16')]

distinct ids: 8  ['0x80001001','0x80001002','0x80001003','0x80001004',
                  '0x80001006','0x80001007','0x80001008','0x80001009']
0x80001005 present? False
```

**Son 8 ids distintos, que es exactamente el número de CU.** El id `0x80001005` no se
emite nunca. Contradicción (3) resuelta por aritmética.

**Y los ids no son `0x8000000N`**: el texto es decimal `2147487745` = **`0x80001001`**.
La palabra alta es `0x8000`, no `0x8000|small`. Corregir el finding original.

### 3.2 Qué representa el identificador. `LEIDO_EN_CORPUS`

`processor_id_low` es **el id de CU** (o de banco de CU) dentro del espacio de ids que KFD
reserva para la GPU. La base es una **constante compilada**, no un flag de hardware:

```c
kfd_crat.c:38:  static uint32_t gpu_processor_id_low = 0x80001000;

kfd_crat.c:40-51:
/* Return the next available gpu_processor_id and increment it for next GPU
 *	@total_cu_count - Total CUs present in the GPU including ones masked off */
static inline unsigned int get_and_inc_gpu_processor_id(unsigned int total_cu_count)
{
        int current_id = gpu_processor_id_low;
        gpu_processor_id_low += total_cu_count;
        return current_id;
}
```

Y la base se publica como `simd_id_base` (`kfd_crat.c:1036`), que medido vale
`2147487744` = **`0x80001000`**, exactamente la constante. Coincidencia exacta.

**Respuesta a la hipótesis del encargo**: `0x80000000` **no** es un flag de tipo de caché
ni marca de "instruction cache". Es la mitad alta de una constante literal de KFD
(`0x80001000`). La hipótesis queda **`REFUTED`**.

Comentario clave en el propio código: el espacio reservado es
`total_cu_count` = "Total CUs present in the GPU **including ones masked off**". O sea el
hueco del id 5 es **diseño**: KFD numera también las CU apagadas.

### 3.3 Por qué falta el `base+5`. `LEIDO_EN_CORPUS`

`kfd_topology.c:1640`:

```c
pcache->processor_id_low = cu_processor_id + (first_active_cu - 1);
```

`cu_processor_id` avanza en cada iteración del bucle (`kfd_topology.c:1846`,
`cu_processor_id += num_cu_shared`) **aunque la CU esté inactiva**. `first_active_cu` es
`ffs()` de la máscara de CUs Hermanas (`kfd_topology.c:1625-1628`):

```c
cu_sibling_map_mask = cu_bitmask;
cu_sibling_map_mask >>= cu_block;
cu_sibling_map_mask &= ((1 << pcache_info[cache_type].num_cu_shared) - 1);
first_active_cu = ffs(cu_sibling_map_mask);
```

Si la CU en posición 0 de un SH está apagada, `ffs` salta y el id resultante se desplaza.
El `sibling_map` **confirma el desplazamiento** en los datos: las cachés de banco con 3
CU activas tienen `ones_at=[0,1,2]`, es decir el código del CU activo sematerialsó
correctamente. `MEDIDO_AQUI`:

```
cache  8: type=10 pid=0x80001001 sibling ones_at=[0, 1, 2]   <- 3 CU en el banco
cache  9: type=10 pid=0x80001004 sibling ones_at=[0]         <- 1 CU en el banco
cache 10: type=10 pid=0x80001006 sibling ones_at=[0, 1, 2]   <- 3 CU
cache 11: type=10 pid=0x80001009 sibling ones_at=[0]         <- 1 CU
```

### 3.4 Las 16 cachés, tabla completa. `MEDIDO_AQUI`

| cache | type | kind | size | pid (hex) | id−base | sibling_map | fila de tabla |
|---|---|---|---|---|---|---|---|
| 0 | 9 | datos | 16 | `0x80001001` | 1 | `[0]` | 0 (`num_cu_shared=1`) |
| 1 | 9 | datos | 16 | `0x80001002` | 2 | `[0]` | 0 |
| 2 | 9 | datos | 16 | `0x80001003` | 3 | `[0]` | 0 |
| 3 | 9 | datos | 16 | `0x80001004` | 4 | `[0]` | 0 |
| 4 | 9 | datos | 16 | `0x80001006` | 6 | `[0]` | 0 |
| 5 | 9 | datos | 16 | `0x80001007` | 7 | `[0]` | 0 |
| 6 | 9 | datos | 16 | `0x80001008` | 8 | `[0]` | 0 |
| 7 | 9 | datos | 16 | `0x80001009` | 9 | `[0]` | 0 |
| 8 | **10** | **instr** | 32 | `0x80001001` | 1 | `[0,1,2]` | 1 (`num_cu_shared=4`) |
| 9 | **10** | **instr** | 32 | `0x80001004` | 4 | `[0]` | 1 |
| 10 | **10** | **instr** | 32 | `0x80001006` | 6 | `[0,1,2]` | 1 |
| 11 | **10** | **instr** | 32 | `0x80001009` | 9 | `[0]` | 1 |
| 12 | 9 | datos | 16 | `0x80001001` | 1 | `[0,1,2]` | 2 (`num_cu_shared=4`) |
| 13 | 9 | datos | 16 | `0x80001004` | 4 | `[0]` | 2 |
| 14 | 9 | datos | 16 | `0x80001006` | 6 | `[0,1,2]` | 2 |
| 15 | 9 | datos | 16 | `0x80001009` | 9 | `[0]` | 2 |

---

## 4. CONTRADICCIÓN (4) — `cache_line_size 64`, `latency 0`, `association 0`

### 4.1 Respuesta: KFD no los rellena. No es que la ASIC no los declare. `PROVEN`

En el camino que Traceyó estas 16 cachés (`fill_in_l1_pcache`,
`kfd_topology.c:1615-1674`) sólo se asignan **cinco** campos:

```c
kfd_topology.c:1639:  memset(pcache, 0, sizeof(struct kfd_cache_properties));
kfd_topology.c:1640:  pcache->processor_id_low = cu_processor_id + (first_active_cu - 1);
kfd_topology.c:1641:  pcache->cache_level      = pcache_info[cache_type].cache_level;
kfd_topology.c:1642:  pcache->cache_size       = pcache_info[cache_type].cache_size;
kfd_topology.c:1643:  pcache->cacheline_size   = pcache_info[cache_type].cache_line_size;
kfd_topology.c:1645-1652:  pcache->cache_type |= ...   (los 4 flags)
kfd_topology.c:1660-1666:  pcache->sibling_map[0..3]
kfd_topology.c:1668:  pcache->sibling_map_size = 4;
```

`cachelines_per_tag`, `cache_assoc` y `cache_latency` **no aparecen**. Se quedan en 0 por
el `memset` de la línea 1639. El `memset` es la razón, no una lectura de hardware que
devuelva cero.

Contraste con el camino CRAT, que **sí** los copia del firmware
(`kfd_crat.c:1198-1200`):

```c
props->cachelines_per_tag = cache->lines_per_tag;
props->cache_assoc        = cache->associativity;
props->cache_latency      = cache->cache_latency;
```

Como §1.3 probó que el camino CRAT **no** corrió (`sibling_map_size`=4, no 128), el cero
es de KFD.

### 4.2 Por qué esto importa (el punto que el encargo señalaba)

`localmenteCacheable` / cualquier decisión de residency basada en "el ASIC declara
asociatividad/latencia" **no tiene respaldo aquí**: no es "el dato es cero", es "no hay
dato". Un driver propio que lea estos campos de sysfs obtendrá 0 indistinguible de "no
declarado", y **no puede** usar `cache_assoc=0` como si fuera "direct-mapped" ni
`cache_latency=0` como si fuera "0 ciclos".

`cache_line_size=64` **sí** es dato real: viene de `carrizo_cache_info` línea 95/105/115
(las tres entradas), que es lo que KFD copia a `cacheline_size`.

### 4.3 La indistinción es demostrable

Un consumidor de sysfs **no puede** distinguir "KFD no lo rellenó" de "el ASIC no lo
declara", porque en este camino ambos casos producen exactamente `0`. La única manera de
saberlo es el código, y por eso esta conclusión es `LEIDO_EN_CORPUS` y no `MEDIDO_AQUI`.

---

## 5. Verificación independiente: la simulación reproduce los 16 cachés

### 5.1 Modelo. `INFERIDO` → `CORROBORATED`

Simulé `kfd_fill_cache_non_crat_info` + `fill_in_l1_pcache` literalmente, con:

- `simd_id_base = 0x80001000` (constante de `kfd_crat.c:38`, y medida: `simd_id_base 2147487744`)
- `max_sh_per_se = 1`, `max_shader_engines = 2`, `max_cu_per_sh = 5`
- `carrizo_cache_info` tal cual
- bitmap de CU: `0b11110` por SH (CU activas en posiciones 1,2,3,4)

Salida del modelo vs sysfs medido:

```
 ct kind size type        pid pid-base sib_ones          |  MEDIDO
 0    D   16    9   0x80001001       1 [0]               |  cache  0  9 16 0x80001001 [0]     OK
 0    D   16    9   0x80001002       2 [0]               |  cache  1 ...                        OK
 0    D   16    9   0x80001003       3 [0]               |  cache  2 ...                        OK
 0    D   16    9   0x80001004       4 [0]               |  cache  3 ...                        OK
 0    D   16    9   0x80001006       6 [0]               |  cache  4 ...                        OK
 0    D   16    9   0x80001007       7 [0]               |  cache  5 ...                        OK
 0    D   16    9   0x80001008       8 [0]               |  cache  6 ...                        OK
 0    D   16    9   0x80001009       9 [0]               |  cache  7 ...                        OK
 1    I   32   10   0x80001001       1 [0, 1, 2]         |  cache  8 10 32 0x80001001 [0,1,2]  OK
 1    I   32   10   0x80001004       4 [0]               |  cache  9 10 32 0x80001004 [0]      OK
 1    I   32   10   0x80001006       6 [0, 1, 2]         |  cache 10 ...                        OK
 1    I   32   10   0x80001009       9 [0]               |  cache 11 ...                        OK
 2    D   16    9   0x80001001       1 [0, 1, 2]         |  cache 12  9 16 0x80001001 [0,1,2]  OK
 2    D   16    9   0x80001004       4 [0]               |  cache 13 ...                        OK
 2    D   16    9   0x80001006       6 [0, 1, 2]         |  cache 14 ...                        OK
 2    D   16    9   0x80001009       9 [0]               |  cache 15 ...                        OK

total entries: 16
by type: Counter({'D': 12, 'I': 4})
pids: [1, 2, 3, 4, 6, 7, 8, 9]
```

**Los 16, con tipo, tamaño, id y `sibling_map`, campo a campo.** Eso no es un ajuste
aproximado; es la tabla de Carrizo confirmada contra esta ASIC.

### 5.2 Falsación: el bitmap es único

Busqué **todos** los bitmaps de CU (2 SH × 5 bits = 1024 combinaciones) que reprodujeran
*simultáneamente* type, size, pid y sibling_map de las 16 entradas medidas:

```
bitmaps reproducing ALL measured fields exactly: 1
   SE0=0b11110 (active CUs [1, 2, 3, 4])  SE1=0b11110 (active CUs [1, 2, 3, 4])
=> active CUs per SH: 4 | total: 8
```

**Una sola solución de 1024.** El bitmap no es un grado de libertad que ajusté: está
determinado. Y confirma §2.2 por vía independiente: 8 CU activas.

### 5.3 Qué haría refutar esto

Para que §1–§4 fueran incorrectos haría falta ver **cualquier** de estas observaciones:

- un `sibling_map` de 1024 valores → probaría que el camino fue CRAT y entonces los
  `type 9/10` podrían venir de flags de firmware, no de `carrizo_cache_info`;
- `simd_id_base` distinto de `0x80001000` → rompería la cadena `get_and_inc_gpu_processor_id`;
- un 9º `processor_id_low` distinto de los 8 medidos;
- `max_cu_per_sh` ≠ 5 con la misma tabla → descartaría el modelo de la tabla de Carrizo.

No hay ninguna de las cuatro.

---

## 6. CATÁLOGO sysfs: qué se lee con la GPU dormida (encargo punto 5)

### 6.1 La columna que decide, y por qué "sysfs vs ioctl" es la distinción equivocada

La distinción correcta es **dónde lee el driver el valor**:

- **RAM** → `adev->…` o una estructura en memoria → leer sysfs **no toca hardware**
- **REGISTRO** → `RREG*` / `READ_REGISTER` / MMIO → leer sysfs **accede al hardware**

Un atributo sysfs puede ser cualquiera de las dos, y **no hay forma de saberlo por el
nombre**. §6.3 da el contraejemplo.

### 6.2 Atributos CLASIFICADOS desde el corpus. `LEIDO_EN_CORPUS`

`card1` expone 69 ficheros + 15 directorios. 38 son genéricos PCI/DRM (`config`,
`resource*`, `vendor`, `uevent`, …) y no son de amdgpu. De los propios de amdgpu, sólo 10
tienen su fuente en el corpus. Todos verificados leyendo el cuerpo de la función:

| atributo | fuente | expresión | clase |
|---|---|---|---|
| `mem_info_vram_total` | `amdgpu_vram_mgr.c:102-108` | `adev->gmc.real_vram_size` | **RAM** |
| `mem_info_vis_vram_total` | `amdgpu_vram_mgr.c:119-125` | `adev->gmc.visible_vram_size` | **RAM** |
| `mem_info_vram_used` | `amdgpu_vram_mgr.c:136-144` | `ttm_resource_manager_usage(&adev->mman.vram_mgr.manager)` | **RAM** |
| `mem_info_vis_vram_used` | `amdgpu_vram_mgr.c:155-163` | `amdgpu_vram_mgr_vis_usage()` → `atomic64_read(&mgr->vis_usage)` (`:781-783`) | **RAM** |
| `mem_info_gtt_total` | `amdgpu_gtt_mgr.c:45-54` | `ttm_manager_type(…,TTM_PL_TT)->size` | **RAM** |
| `mem_info_gtt_used` | `amdgpu_gtt_mgr.c:65-73` | `ttm_resource_manager_usage()` | **RAM** |
| `mem_info_preempt_used` | `amdgpu_preempt_mgr.c:36-44` | `ttm_resource_manager_usage()` | **RAM** |
| `vbios_version` | `amdgpu_atombios.c:1807-1815` | `ctx->vbios_pn` | **RAM** |
| `vbios_build` | `amdgpu_atombios.c:1818-1826` | `ctx->build_num` | **RAM** |
| **`board_info`** | `amdgpu_device.c:333-357` → `smuio_v15_0_8.c:162-167` | **`RREG32_SOC15(SMUIO, 0, regSMUIO_MCM_CONFIG)`** | **REGISTRO** |

**9 de RAM, 1 de registro.**

### 6.3 `board_info` es la trampa. `LEIDO_EN_CORPUS`

Devuelve una cadena corta con aspecto de dato estático:

```c
/* amdgpu_device.c:342-343 */
if (adev->smuio.funcs && adev->smuio.funcs->get_pkg_type)
        pkg_type = adev->smuio.funcs->get_pkg_type(adev);
...
return sysfs_emit(buf, "%s : %s\n", "type", pkg);   /* :357 */
```

Y para gfx8 ese vfunc **lee un registro**:

```c
/* smuio_v15_0_8.c:162-167 */
static enum amdgpu_pkg_type smuio_v15_0_8_get_pkg_type(struct amdgpu_device *adev)
{
        ...
        data = RREG32_SOC15(SMUIO, 0, regSMUIO_MCM_CONFIG);
        data = REG_GET_FIELD(data, SMUIO_MCM_CONFIG, PKG_TYPE);
```

`smuio_v15_0_8` es el ASIC de esta familia (gfx8 / VI). **`board_info` es un MMIO con
interrogación de hardware disfrazado de sysfs.** No lo he leído en esta sesión: hacerlo
sería acceder al hardware, que este nodo tiene prohibido.

> Refutación de esta clasificación: si existiera otro `get_pkg_type` asignado a esta ASIC
> (p. ej. `smuio_v13_0_3`, que consulta MP1) el cuerpo sería distinto. Se verificó que
> `get_pkg_type` sólo existe en `smuio_v13_0.c`, `smuio_v13_0_3.c` y `smuio_v15_0_8.c`
> (`amdgpu_smuio.h:46` declara el puntero), y para gfx8 elassigned es `v15_0_8`.

### 6.4 Topología KFD: 100 % RAM. `LEIDO_EN_CORPUS`

Las cuatro funciones `show` de la topología KFD, verificadas una a una:

```
node_show        kfd_topology.c:404-548  register_access=NO
kfd_cache_show   kfd_topology.c:325-358  register_access=NO
mem_show         kfd_topology.c:293-314  register_access=NO
iolink_show      kfd_topology.c:251-282  register_access=NO
```

Implicación que no es obvia: **todos** los números de §1–§4 (y `mem_banks`, `io_links`,
`nodes/0`) son **valores capturados en RAM durante el probe** e impresos tal cual. No son
lecturas del estado actual de la GPU. Leer `/sys/class/kfd/...` no toca hardware, pero
tampoco refleja nada que cambie: para DPM/ clocks es un snapshot de arranque, no un
medidor.

### 6.5 Lo que NO se puede clasificar con este corpus. `NOT_DETERMINED`

22 atributos sysfs de amdgpu **existen en la máquina** y **no tienen fuente aquí**, porque
sus ficheros no están en el corpus:

| atributo(s) | fichero ausente |
|---|---|
| `pp_dpm_sclk`, `pp_dpm_mclk`, `pp_dpm_pcie`, `pp_num_states`, `pp_force_state`, `pp_cur_state`, `pp_sclk_od`, `pp_mclk_od`, `pp_power_profile_mode`, `pp_table`, `power_dpm_state`, `power_dpm_force_performance_level` | `amdgpu_pm.c` |
| `gpu_busy_percent`, `mem_busy_percent`, `pcie_bw`, `thermal_throttling_logging` | `amdgpu_pm.c` / `amdgpu_smu.c` |
| `current_link_speed`, `current_link_width`, `max_link_speed`, `max_link_width` | `amdgpu_pci.c` |
| 30 de `hwmon/hwmon1/*` (`temp1_input`, `power1_input`, `freq1_input`, `fan1_*`, `pwm1`, …) | `amdgpu_hwmon.c` |

Comprobación cruzada: los 22 nombres **sí** están en el `amdgpu.ko` en marcha
(`pp_dpm_sclk` ×6, `pp_num_states` ×9, `pcie_bw` ×4, `gpu_busy_percent` ×4,
`thermal_throttling_logging` ×6, `mem_info_preempt_used` ×5…), y **cero** están en el
corpus. Es decir: el driver que corre los tiene; la copia de referencia no.

**No los clasifico.** No se puede afirmar que sean de registro ni que sean de RAM sin su
fuente, y `NOT_DETERMINED` es la respuesta honesta. Deliberadamente **no** los he leeído
para "medir" la columna: leerlos habría introducido exactamente la'accès a hardware que
este nodo prohíbe, y el resultado habría sido una observación única sin mecanismo.

Observación lateral sin explicar: `current_link_speed`, `current_link_width`,
`max_link_speed`, `max_link_width` **existen como ficheros sysfs pero sus nombres no
aparecen en el `.ko`**. `link_speed` aparece 14 veces y `link_width` 15, así que lo que
falta es el prefijo. `NOT_DETERMINED`; no lo atribuyo a nadie.

---

## 7. Qué queda del hallazgo 1045 (encargo punto 6)

### 7.1 Lo que se sostiene

`amdgpu_kms.c:1453` es `pm_runtime_get_sync(dev->dev);` en la función de `open` del nodo
render. Verificado en el corpus, línea exacta. Abrir el nodo render **reanuda** la GPU
según el mecanismo `pm_runtime` de Linux. Eso es correcto y no se toca.

### 7.2 Lo que NO se sostiene, y hay que decirlo

El hallazgo 1045 afirmaba que *"la telemetría de esta tarjeta exige abrir el nodo render"*.
**Eso es falso como generalidad**, y el motivo es preciso:

- La medición del coordinador (22 atributos legibles con la GPU dormida,
  `runtime_active_time` idéntico) es correcta y la **corrijo el marco**, no el dato.
- La columna de §6.2 explica **por qué** es correcta: 9 de los 10 atributos que pudo
  clasificar son **RAM**, y los 4 `show` de la topología KFD son **100 % RAM**.

O sea: el hallazgo-generalizó desde el subconjunto que sí abre hardware. Lo que el
1045 sostiene de verdad es **más estrecho y más útil**:

> Hay un subconjunto de telemetría que se puede leer sin abrir el nodo render
> (información de VRAM/GTT/preempt, VBIOS, topología KFD completa), y hay otro que no.

El segundo grupo **no está determined** aquí (§6.5): sin `amdgpu_pm.c` / `amdgpu_hwmon.c`
no se puede decir si `pp_dpm_sclk`, `temp1_input` o `pcie_bw` leen registro o no. La
pregunta original ("cuáles son de RAM y cuáles no") **queda a medias por falta de corpus,
no por falta de capacidad** — y se cierra Trayendo 4 ficheros, no haciendo más
experimentos.

### 7.3 No reescribo el 1045

Ni lo he tocado ni lo renumerado. Queda dicho aquí qué se sostiene y qué no; la decisión
de reformularlo es del coordinador.

---

## 8. Inventario de la topología KFD medido en esta sesión

`MEDIDO_AQUI`, `nodes/1` (GPU), formato `clave valor` decimal:

```
simd_count 32          array_count 2          simd_arrays_per_engine 1
cu_per_simd_array 5    simd_per_cu 4          wave_front_size 64
max_waves_per_simd 10  lds_size_in_kb 64      max_slots_scratch_cu 32
cwsr_size 2789376       ctl_stack_size 4096    num_cp_queues 24
num_sdma_engines 2      num_sdma_queues_per_engine 2   num_xcc 1
num_gws 0               local_mem_size 0       gds_size_in_kb 0
caches_count 16         mem_banks_count 1      io_links_count 1
p2p_links_count 0       simd_id_base 2147487744 (= 0x80001000)
gfx_target_version 80003   vendor_id 4098     device_id 27039 (0x699F)
location_id 256         domain 0               drm_render_minor 129
max_engine_clk_fcompute 1071   max_engine_clk_ccompute 4000
capability 4736         capability2 0          debug_prop 0
fw_version 730          sdma_fw_version 58     hive_id 0    unique_id 0
num_sdma_xgmi_engines 0
```

`mem_banks/0/properties` (el encargo omitió `flags`):

```
heap_type 2 (= HSA_MEM_HEAP_TYPE_FB_PRIVATE, kfd_sysfs.h:82)
size_in_bytes 2147483648    flags 0    width 64    mem_clk_max 1500
```

`io_links/0/properties` (el encargo stabilizó mal `max_bandwidth`):

```
type 2 (= HSA_IOLINK_TYPE_PCIEXPRESS, kfd_sysfs.h:101)   node_from 1  node_to 0
weight 20    min_bandwidth 0    max_bandwidth 2500    flags 1
min_latency 0  max_latency 0  recommended_transfer_size 0
```

> `max_bandwidth 2500`, no 0. Corrected.

`nodes/0` (CPU): `cpu_cores_count 8`, `simd_count 0`, `caches_count 0`, todo lo demás 0
salvo `max_engine_clk_ccompute 4000`. Que **no** emita `max_engine_clk_fcompute`,
`local_mem_size`, `fw_version`, `capability`, `capability2` ni `debug_prop` es exactamente
lo que manda el `if (dev->gpu)` de `kfd_topology.c:499-533`. `CORROBORATED`.

`perf/`: vacío, 0 entradas. `MEDIDO_AQUI`.

---

## 9. Resumen de estados

| # | afirmación | estado | evidencia que la refutaría |
|---|---|---|---|
| 1 | `type 9` = `HSA_CACHE_TYPE_DATA\|HSACU`; `type 10` = `INSTRUCTION\|HSACU` | **PROVEN** (`LEIDO_EN_CORPUS`) | un flag distinto asignado en 1645-1652/1208-1215 |
| 2 | 12 datos + 4 instr. por 3 entradas de `carrizo_cache_info` con `num_cu_shared` 1/4/4 | **PROVEN** | `polaris12_cache_info` ≠ `carrizo_cache_info` |
| 3 | `cu_per_simd_array`=5 es `max_cu_per_sh` (capacidad); 8 es `cu_info->number` (CU activas) | **PROVEN** | que 5 venga de otro campo en kfd_crat.c:2292 |
| 4 | hay **8** `processor_id_low` distintos, no 9 | **MEDIDO_AQUI** | un 9º id no medido |
| 5 | `0x80001000` es constante de KFD, no flag de tipo de caché | **PROVEN** | que `simd_id_base` ≠ `0x80001000` |
| 6 | ceros en `latency`/`association`/`lines_per_tag` = KFD no los rellena | **PROVEN** | que el camino fuera CRAT (`sibling_map_size`=128) |
| 7 | el camino fue el no-CRAT | **PROVEN** (`MEDIDO_AQUI`) | `sibling_map` con 1024 valores |
| 8 | bitmap de CU: 4 activas por SH × 2 SH = 8 CU | **CORROBORATED** (único de 1024) | otro bitmap que reprodujera todo a la vez |
| 9 | 9 de 10 atributos sysfs clasificados son RAM | **PROVEN** para los 10 listados | otro cuerpo de función show |
| 10 | `board_info` lee registro (`RREG32_SOC15`) | **PROVEN** | que gfx8 use otro `get_pkg_type` |
| 11 | los 4 `show` de topología KFD no tocan hardware | **PROVEN** | un `RREG` en esos cuerpos |
| 12 | clasificación de los 22 restantes | **NOT_DETERMINED** | traer `amdgpu_pm.c`, `amdgpu_hwmon.c`, `amdgpu_smu.c`, `amdgpu_pci.c` |
| 13 | por qué KFD va dentro de `amdgpu.ko` en esta build | **NOT_DETERMINED** | fuente de integración de amdkfd |
| 14 | `num_nodes`(=1) usado para derivar `cu_info->number` | **INFERIDO** | observación directa de `num_xcp` |

## 10. Lo que queda abierto

1. **Los 22 + 30 atributos no clasificables** (§6.5). Cierra con 4 ficheros, no con más
   experimentos. Es el hueco con más valor por coste de todo este nodo.
2. `num_nodes` / `num_xcp` no expuesto en sysfs. Requiere `debugfs` o ioctl → fuera de
   alcance aquí. La conclusión de §2.2 no depende de ello.
3. Por qué KFD se enlaza en `amdgpu.ko` en esta build.
4. `current_link_speed` et al.: existen en sysfs, su nombre no está en el `.ko`.

No se ha tocado la GPU, no se ha abierto `/dev/dri/*`, no se ha escrito en sysfs, no se ha
usado `dmesg`/`journalctl`/debugfs. Lecturas de sysfs, `/proc`, `/dev` (listado) y del
`.ko` en disco, más lectura del corpus. Único fichero escrito:
`08-ARQUITECTURA/KFD-TOPOLOGIA.md`.