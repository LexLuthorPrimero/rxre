# IMPL-CONSTANTES-CU — las dos constantes de CU, D1, D2, D3 y D4 aplicados al driver

```
NODE_ID=IMPL-CONSTANTES-CU · AGENT_ID=WORKER
ENTRADA=08-ARQUITECTURA/CONSTANTES-GFX8-DRIVER.md (§2, §4, §5, §6, §7), leido ENTERO
CLASIFICACION=IMPLEMENTATION · TRACK=WRITE_LOCAL
ESCRITOS=7 ficheros de 04-IMPLEMENTACION/rx550-driver/ + ESTE fichero. Nada mas.
GPU INTACTA · SIN MMIO · SIN /dev/dri · SIN escritura en sysfs · SIN debugfs · SIN dmesg/journalctl
SIN RED · SIN git add · SIN git commit · SIN grep (todo el recorrido con python3 + open()/os.walk)
COMPILACIONES=3 modificadores (dos mutaciones y una final) + la puerta
```

---

## 0 · LA PUERTA DE PASS, ANTES Y DESPUES

Los dos numeros pedidos, ejecutados **antes de editar** y **despues**:

| | antes | despues | veredicto |
|---|---|---|---|
| `make -s -C tests run` · rc | **0** | **0** | — |
| PASS de test | **1634** | **1634** | igual |
| FAIL de test | **0** | **0** | igual |
| estatico | **69 PASS / 0 FAIL** | **69 PASS / 0 FAIL** | igual |
| `make -s` · rc | **0** | **0** | — |
| `.ko` | **1 123 560 B** | **1 123 688 B** | +128 B, §5 |
| diagnosticos del compilador | **0** | **0** | igual |

`md5(rx550_drv.ko)` antes `160a88d8bec8c3ac9f8ab769514908a6` → despues
`f5712df25e1e64271ab789c4bed87db0`.

**Sobre los 0 avisos, con la linea que si cambia.** El build limpio y completo
(`make -s clean; make -s`) deja en stderr **dos** lineas, y las dos son de kbuild,
no de gcc:

```
warning: the compiler differs from the one used to build the kernel   <- ya estaba antes
Skipping BTF generation for rx550_drv.ko due to unavailability of vmlinux   <- NUEVA
```

La segunda no es un aviso del compilador y no la produce este cambio: sale de
`/usr/src/kernels/7.1.3-200.nobara.fc44.x86_64/scripts/Makefile.modfinal:44`, que es un
`printf` de `modfinal`, y depende solo de que no haya `vmlinux`. Aparece **cuando el
modulo se enlaza de verdad**: el `make -s` del "antes" fue un no-op (nada que
recompilar, `md5` identico antes y despues de esa llamada), y por eso no salia. La
prueba de que no depende del contenido: un `make -s` posterior, ya no-op, **no** la
vuelve a emitir, y el recuento de diagnostics con forma `fichero:linea:col: warning|error`
es **0** en el build limpio.

---

## 1 · QUE HE VERIFICADO ANTES DE ESCRIBIR, Y QUE NO HE HEREDADO

El encargo dice que la entrada son los items ya medidos. Eso es cierto y tambien es un
peligro: heredar un numero del informe es heredarlo de un solo autor. Asi que **volvi a
medir los dos discriminantes por mi cuenta**, y los dos reproducen:

**Lado (A), `cwsr_size`.** Leidas de `/sys/class/kfd/kfd/topology/nodes/1/properties`:
`simd_count=32`, `simd_per_cu=4`, `array_count=2`, `simd_arrays_per_engine=1`,
`ctl_stack_size=4096`, `cwsr_size=2789376`. Y leida la aritmetica del corpus,
`kfd_queue.c:401-511` linea a linea, con las cuatro funciones de tamano (`:414` vgpr
`0x40000`, `:403` sgpr `0x4000`, `:446` lds `0x10000` porque `gfxv=80003` no esta en la
lista de override de `:448`, `:436` hwreg `0x1000`):

```
cu_num    = 32/4                          = 8
WG/CU     = 0x40000+0x4000+0x10000+0x1000 = 348160  (0x55000)
wave_num  = min(8*40, 2/1*512)            = 320
wg_data   = ALIGN(8*348160, 4096)         = 2785280
ctl_stack = ALIGN(40 + 320*8 + 8, 4096)   = 4096
cwsr      = ALIGN(4096 + 2785280, 4096)   = 2789376   <== el medido
con cu_num=10                              = 3485696   <== NO es el medido
```

**Lado (B), las 16 caches.** Leidas las 16 entradas de `nodes/1/caches/N/properties`:
`simd_id_base=2147487744`, y los `processor_id_low` dan offsets
`1,2,3,4,6,7,8,9` con repeticiones; `level=1` **las 16**; `size` = 16 KiB en 12 y 32 KiB
en 4; `cache_line_size=64` en las 16; **ninguna de nivel 2**. Aplicando el test de
`kfd_crat.c:1173-1189` (`total_num_of_cu = array_count * cu_per_simd_array`, span
`[base, base+total)`):

```
total =  8  ->  publica 12 de 16
total =  9  ->  publica 13 de 16
total = 10  ->  publica 16 de 16    <== MEDIDO
```

Y que las 16 no son el relleno: `kfd_crat.c:968-1019` define `dummy_cache_info` con
**5** entradas y una de ellas es **un L2 de 2048 KiB**, que aqui no existe. Descartado.

**Los dos discriminantes son Opuestos y los dos son ciertos.** Por eso §4.3 va dos
constantes, y por eso no se ha resuelto el conflicto con un numero: no hay numero que
valga para las dos familias de decision.

---

## 2 · §4.3 · LAS DOS CONSTANTES DE CU

**Fichero nuevo:** `04-IMPLEMENTACION/rx550-driver/rx550_asic_geom.h`, 262 lineas,
`md5 fa1e2ab7b6360bf670ee2c35725ad42d`. **No incluye nada**: ni libc, ni kernel, ni
otros componentes, que es la regla de `.h` del proyecto y ademas lo que permite que los
`_Static_assert` se evaluen sin ningun tipo.

Las dos constantes, con el nombre que fijo el informe (`rx550_asic_geom.h:121-122`):

```c
#define RX550_NR_CU_CAPACIDAD	8u	/* CU que hay: CWSR, stack, oleadas, ocupacion */
#define RX550_NR_CU_INDICE_MAX	10u	/* span de ids que hay que cubrir al indexar   */
```

| constante | valor | fuente de la cifra | discriminante | consumidores |
|---|---|---|---|---|
| `RX550_NR_CU_CAPACIDAD` | **8** | `32 / 4`, con `32` y `4` de CRAT de esta maquina y `4` corroborado en `gfx_8_0_enum.h:6832` | `cwsr_size = 2789376` cierra y `3485696` no, con la aritmetica de `kfd_queue.c:454-511` | (a) dimension de `cwsr` y de la pila de control; (b) techo de oleadas y modelo de ocupacion; (c) reparto de un dispatch entre CU en PM4; (d) reparto de contadores `*_CU_FULL_*`; (e) atribucion de rebanadas de cache a su CU — **ninguno escrito todavia, §6** |
| `RX550_NR_CU_INDICE_MAX` | **10** | `array_count * cu_per_simd_array` = `2 * 5`, los dos de CRAT | 16 caches publicadas solo salen con span >= 10, con los ids **reales** leidos | el mismo (e), y el unico criterio de publicacion de `kfd_crat.c:1187-1189` |

**El comentario que dice que hay dos y por que** esta en el bloque `§4.3` de
`rx550_asic_geom.h:25-112`, con las dos contas escritas, el porque de no unirlas, el
`CONFLICTADO` sobre `cu_per_simd_array` marcado como tal, y los **refutadores** de la
seccion.

### 2.1 · Por que no son texto: los discriminantes son puertas

Nueve `_Static_assert` (`rx550_asic_geom.h:207-260`). No son identidades que se cumplan
para cualquier estado: cada uno se cae si el numero de CU se mueve al otro lado. Y hay
**asimetría deliberada**: cambiar `CAPACIDAD` a 10 rompe cinco asserts; cambiar
`INDICE_MAX` a 8 rompe los del lado (B).

Mutacion 1, `CAPACIDAD 8 -> 10` (MEDIDO):

```
rx550_asic_geom.h:207: error: fallo la asercion estatica: "el lado (A): 8 CU es lo que sale de simd_count / simd_per_cu"
rx550_asic_geom.h:213: error: fallo la asercion estatica: "el lado (A): cwsr_size medido = ctl_stack + 8 CU * contexto"
rx550_asic_geom.h:225: error: fallo la asercion estatica: "el techo de oleadas es el primer termino de kfd_queue.c:459"
rx550_asic_geom.h:246: error: fallo la asercion estatica: "el lado (B): CAPACIDAD no llega al id de cache mas alto que existe, …"
rx550_asic_geom.h:251: error: fallo la asercion estatica: "CAPACIDAD e INDICE_MAX son dos magnitudes distintas, …"
-> Error 1   (5 de 9 asserts caidos)
```

Mutaciones 2 y 3, `INDICE_MAX 10 -> 8` y `PLACEMENT_DEF LOW -> BEST_FIT`: tambien
`Error 1`. **Las tres revertidas**, y el fichero esta en el estado de §0.

Un detalle de la asimetria que confirma que los dos numeros estan en familias distintas:
el assert *contrafactual* del lado (A) —`10 * 348160 + 4096 != 2789376`— **no** cayo en la
mutacion 1, y no tiene que caer: con las dos constantes a 10 la cuenta del lado (A)
sigue dando !=, y por eso una sola constante no puede satisfacer los dos lados a la vez.
Eso es §4.3 escrito en codigo.

### 2.2 · Donde se incluye, y por que ahi

`rx550_target.c:44-48`. Razon: **no hay ningun `.c` de shader** en el driver (§5.2 del
informe lo verifico por dos caminos), asi que no hay donde colgarlo; y se incluye desde
un `.c` que esta en `Makefile:30` **para que los asserts se compilen**, que es lo que los
convierte en puerta y no en prosa. Un `.h` sin incluir seria un fichero muerto, y el
proyecto ya tiene una puerta para eso (`COB-MODULOS`, `test_static.sh:327`).

`rx550_drv-objs` **no** se toca: no hay `.c` nuevo, y anadir un `.o` suelto crearia un
segundo modulo sin `MODULE_LICENSE()`.

---

## 3 · D1 · LAS DOS AUTORIDADES DEL ROOT

**MEDIDO, confirmado antes de tocar nada.** `rx550_pdb0.h` se llamaba a si mismo
"implementacion CANONICA" y declaraba `512` bajo `HARDWARE_REQUIREMENT`;
`rx550_vmid1_pgt.c:322-334` deriva `16384` para la ventana de 64 GiB. Los dos estan en
el mismo `.ko` (`Makefile:30`). `rx550_vmid1_pgt.h:45` ya advertia del error con todas
las letras. **Factor 32.**

**Lo que NO he hecho, y es la decision de este apartado:** no he cambiado `512` por
`16384`. El informe lo dice y yo lo he comprobado: **las dos cifras no compiten.**

- `rx550_pdb0` tiene `block_size = 9` → 512 entradas → **2 MiB por tabla**.
- `rx550_vmid1_pgt` tiene `block_size = 10` → cobertura de **64 GiB**, repartida en
  `root_entries = 16384` tablas de hoja.

Son ventanas distintas, no dos medidas de la misma. Cambiar el numero de una habria
hecho que un componente con 2 MiB de ambito administrara una ventana de 64 GiB **sin
decirlo**: el defecto con otro nombre.

**El criterio que si existe, y por eso no hubo que inventarlo:**

1. El hardware **no fija un numero de entradas**. Fija un campo de 4 bits:
   `PAGE_TABLE_BLOCK_SIZE = block_size - 9` (`gmc_v8_0.c:933-934`), luego el rango
   codificable es `[9, 24]` y 512 es el valor del campo en **cero**. Por tanto `512` no
   era un `HARDWARE_REQUIREMENT`, y **esa es la causa raiz del D1**: una propiedad
   derivada de un campo, escrita como constante de silicio.
2. El canonico del root de una VM es la **derivacion desde la ventana**
   (`rx550_vmid1_geometry()`), que no tiene ni un numero escrito a mano.
3. `rx550_pdb0` **no tiene ventana, no tiene `vm_size` y no tiene consumidor en el
   modulo**: `rx550_pdb0_*` no se llama desde ningun `.c` de `Makefile:30`, solo desde su
   propio test. No compite por el root.

**Lo aplicado en `rx550_pdb0.h`:**

- El titulo ya no dice `CANONICA`: dice `UNA TABLA DE 2 MiB`.
- `RX550_PDB0_ENTRIES` deja de ser un literal bajo `HARDWARE_REQUIREMENT` y pasa a
  `MODEL_CHOICE`, derivado: `#define RX550_PDB0_ENTRIES (1u << RX550_PDB0_BLOCK_SIZE)`
  con `#define RX550_PDB0_BLOCK_SIZE RX550_VMID1_BLOCK_SIZE_MIN`. **El 9 ya no vive
  suelto en este fichero**: se lee del componente que si lo declara con su corpus.
- La cabecera incluye `rx550_vmid1_pgt.h` **por un unico simbolo**, y dice por que no es
  una dependencia de ambito: `rx550_vmid1_pgt.h` no incluye esta (no hay ciclo), y lo
  que fluye es un hecho de hardware, no un ambito.
- Se declara por que se toma el **minimo** (9) y no el **demostrado** (10): el 9 es el
  unico valor que no depende de una ventana, y el unico cuya consecuencia esta escrita
  (512 entradas de 8 B son exactamente 4 KiB, una pagina; con 10 serian 8 KiB y haria
  falta un bloque contiguo que `rx550_pdb0_alloc()` no sabe expresar con su
  `alignment`).
- Se declara lo que **no** se hizo y quien lo cierra: el papel de esta tabla de 2 MiB no
  tiene consumidor, y sin consumidor **no hay criterio** para decidir si sobrevive como
  tabla de un subrange, si se absorbe en `rx550_vmid1_pgt.c` o si se retira.

**Comportamiento: cero.** `512`, `4096` y `2 MiB` siguen saliendo exactamente iguales
(`1u << 9`). Lo demuestra `tests/test_pdb0.c:91-101`, que comprueba `ENTRIES == 512`,
`BYTES == 4096` y `COVERAGE == 2 MiB` y que sigue en PASS.

### 3.1 · La tercera autoridad que el informe nombro y no toque

`target_mem.h:47-48`, `TM_LEVEL_BITS 9` / `TM_LEVEL_ENTRIES 512`. **No la he tocado** y
no la toco: `target_mem.h` no lo incluye **ningun** `.c` ni `.h` del arbol (lo verifique
por barrido; solo lo incluye su propio test), o sea que no esta en el `.ko` y no
compite con nadie hoy. Reescribirla seria trabajo sin consumidor, que es lo contrario de
lo que pide este encargo. Queda como `NO_DETERMINADO_EL_PAPEL`, y lo digo aqui para que
no se pierda: si algun dia entra en obj-m, tiene el mismo defecto que `rx550_pdb0` tenia.

---

## 4 · D2 · LAS CADENAS QUE DICEN "9"

Localizadas y unificadas. **Eran tres, no dos**, y la tercera no la habia pedido nadie:

| # | donde | decia | estado |
|---|---|---|---|
| 1 | `rx550_vmid1_pgt.h:292` (comentario del enum `RX550_PGT_ERR_UNSUPPORTED_BLOCK_SIZE`) | `block_size != 9` | **CORREGIDO** → `block_size fuera de [9, 24]` |
| 2 | `rx550_vmid1_pgt.c` (texto del switch de diagnostico) | `"block_size distinto de 9: no demostrado para GFX8"` | **CORREGIDO** → `"block_size fuera del rango codificable [9, 24]"` |
| 3 | `rx550_vmid1_pgt.c:234-246` (bloque "LO QUE SE SABE DE CADA VALOR") | `9 = DEMOSTRADO_EN_GFX8` y `10 = … NO ESCRIBE_EN_GFX8` | **CORREGIDO**: estaba al reves |

**Por que son el mismo defecto y no tres cosas:** las tres afirmaban que el codigo
comprueba el valor 9 cuando **la guarda acepta el rango `[9, 24]`**
(`rx550_vmid1_pgt.c:256-258`, `RX550_VMID1_BLOCK_SIZE_MIN`/`_MAX`). Un comentario de un
enum y un texto de diagnostico son exactamente el tipo de cadena que un humano cita como
autoridad, y el bloque 3 era peor: declaraba que el 10 **no se escribe** en GFX8, cuando
`rx550_vmid1_pgt.h:169-196` ya lo habia refutado en el mismo repositorio.

**El 3 no estaba en el encargo.** Se corrigio por la misma razon y en el mismo turno, y
por coherencia con el 1 y el 2: dejar una tercera cadena diciendo lo contrario habria
dejado el defecto vivo. No es un hallazgo nuevo ni renumerado; es la misma entrada de D2.

**Comportamiento:** el texto de `rx550_vmid1_err_str()` cambia, la guarda no
(`[9, 24]`, igual). El unico consumidor de ese texto es
`tests/test_vmid1_pgt_backing.c`, que lo imprime en un fallo; no compara la cadena.

---

## 5 · D3 · `PLACEMENT_DEF = BEST_FIT` CON `GART_START = 0`

**El defecto, con su nombre exacto:** `rx550_target.c:408` mete
`RX550_GART_PLACEMENT_DEF` en el calculo, y el unico sitio donde esa politica se
convierte en una direccion de GART es `RX550_GART_START`, que vale 0. Con la geometria
medida de esta tarjeta, `BEST_FIT` devuelve `0xFF00000000` (`rx550_gart_geom.c:121-131`,
y `tests/test_gart_geom.c:118-143` mide las dos ramas sobre la misma entrada). O sea: el
driver **declaraba una politica y fijaba a mano la direccion que esa politica no
produce.**

**Lo aplicado:** `RX550_GART_PLACEMENT_DEF` pasa de `BEST_FIT` a
`RX550_GART_PLACEMENT_LOW` (`rx550_gart_geom.h:155`). **`RX550_GART_START` no se toca**:
es una `DESIGN_CHOICE` del proyecto, y la regla es que si algo la contradice se dice, no
se cambia en silencio. Las tres ramas siguen en el `switch` y `BEST_FIT` sigue siendo un
valor pedido de la `enum`, porque es lo que hace el corpus.

El defecto, por tanto, **no era que el default fuera LOW: era que DECIA `BEST_FIT` y ERA
LOW.**

**El test que demuestra el cambio de comportamiento:**
`tests/test_gart_geom.c:136-141` calcula `LOW` sobre la geometria medida y comprueba
`lo.gart_start == 0` y `RX550_GART_START == 0`; `:142-143` comprueba que **no** es lo que
hace el hardware por defecto. Ese test pasa antes y despues, y es el que convierte "LOW
produce el 0 declarado" en medida y no en argumento.

**Y la puerta, que es lo quefaltaba:** un `_Static_assert` en `rx550_gart_geom.h:117`
que ata `RX550_GART_PLACEMENT_DEF == RX550_GART_PLACEMENT_LOW`. **No es una tautologia:**
se cae si alguien vuelve a poner `BEST_FIT` ahi (mutacion 3: `Error 1`) **o** si cambia
`RX550_GART_START` sin cambiar el default. Ese era el punto unico donde las dos
cantidades se podian separar, y por eso hacia falta.

**Honestidad sobre el alcance del cambio:** `.text` baja **32 bytes** (22 750 → 22 718), y
ese es el unico cambio de maquina codigo del turno: la rama `LOW` del `switch` en vez de
la rama `BEST_FIT`. **El comportamiento por defecto del modulo NO cambia**, porque
`rx550_probe_geometry()` esta tras `module_param(rx550_geometry_probe)` con default **0**
y hace `if (!rx550_geometry_probe) return;` (`rx550_target.c:348,375`). La linea que
cambia es la que se imprime por `pci_info` **cuando alguien activa ese parametro a mano**.

---

## 6 · D4 · LITERALES DUPLICADOS — Y UNA CORRECCION AL ENCARGO

El encargo traia tres literales con su identidad ya decidida. **Los tres estan en el
corpus como literales sueltos**, y al comprobarlos **una de esas tres identidades es
falsa**. Se nombra antes de aplicar, porque aplicar la identidad falsa habria sido
exactamente el defecto que D4 quiere cerrar.

| literal | el encargo dice | MEDIDO | aplicado |
|---|---|---|---|
| `rx550_vmid1_pgt.c:101` `18u` | `= RX550_VM_PFN_SHIFT` | el 18 es de `amdgpu_vm.c:2359`; `RX550_VM_PFN_SHIFT` es el de `amdgpu_vm.c:2421`. **Dos literales distintos**, mismo sentido (GiB → paginas de 4 KiB), distinta cuenta | `RX550_VMID1_BITS_POR_GB`, declarado en este componente. **No** fusionado con el del otro |
| `rx550_vmid1_pgt.c:106` `9u` | `= RX550_VM_BLOQUE_OFFSET` | **FALSO.** Es el ancho minimo de un nivel de tabla (`amdgpu_vm.c:2361-2364`), no el offset del campo `PAGE_TABLE_BLOCK_SIZE` | `RX550_VMID1_NIVEL_MIN_BITS`, con su propia cita |
| `rx550_vmid1_pgt.c:271` `9u` | `= RX550_VM_BLOQUE_OFFSET` | correcto: `gmc_v8_0.c:933-934` | `RX550_VMID1_BLOCK_OFFSET` |
| `rx550_vmid1_pgt.c` (DIV_ROUND_UP) `9u` | no nombrado en el encargo | mismo hecho que `:106` (anchos de nivel) | `RX550_VMID1_NIVEL_MIN_BITS` |

**Por que la identidad de `:106` era falsa, y por escrito:** el propio proyecto lo dice en
`rx550_vm_geom.h:95-100` — *«El 9 del `PAGE_TABLE_BLOCK_SIZE = block_size - 9`, y el 9 de
`amdgpu_vm_get_block_size()`, son COSAS DISTINTAS que valen lo mismo»*. Aplicar la
identificacion del encargo seria fusionar dos hechos que el codigo declara separados a
proposito, y hacerian falta cambiar los dos a la vez sin que nadie lo decidiera.

**Ademas, una cita que era falsa en el propio fichero receptor:**
`rx550_vm_geom.h:89` decia *«el 18 es de amdgpu_gmc.h»*. **No existe ningun simbolo de
`PFN_SHIFT` en `amdgpu_gmc.h`** (buscado por nombre en el fichero entero). El 18 esta en
`amdgpu_vm.c:2421` y `amdgpu_vm.c:2359`. Corregido con las dos citas.

Los tres nombres nuevos viven en `rx550_vmid1_pgt.h:198-236` con un bloque que explica **por
que los dos 9 no se unifican**, y `_Static_assert` que los atan a lo que deducen
(`(1 << NIVEL_MIN_BITS) == 512`, `BLOCK_OFFSET == BLOCK_SIZE_MIN`, `BITS_POR_GB == 18`).

**Comportamiento: cero.** Los cuatro reemplazos son el mismo entero. `1u << 9 = 512`, `bits - 9`,
`block_size - 9`: identicos. Lo demuestra el 1634/0 y, en concreto,
`tests/test_vmid1_pgt.c` (24 CHECK) y `tests/test_block_size.c`.

---

## 7 · EL RANKING DE §5 · LAS MEDIDAS QUE FALTABAN

Por orden de desbloqueo de §7, y con lo que se ha escrito de cada una:

| # §7 | constante | ¿escrita? | donde |
|---|---|---|---|
| **1** | **nº de CU, partida en dos** | **SI** | `rx550_asic_geom.h:121-122` — §2 de este fichero |
| 2 | bytes de un slot de scratch | **NO, y no se puede** | `NO_DETERMINED`. Sin el no se puede dimensionar la pagina de scratch. **Propietario: firmware del SQ/RLC.** No hay forma indirecta. Item que puede quedar abierto mucho tiempo, y con el es el que bloquea el subsistema de traps entero |
| **3** | **techo de oleadas = 320** | **SI** | `RX550_ASIC_WAVE_TECHO`, con los dos terminos de `kfd_queue.c:459-460` y el assert que los compara |
| **4** | **bytes de contexto por CU = 348160** | **SI** | `RX550_ASIC_BYTES_CTX_POR_CU`, con los cuatro sumandos citados y el assert de `cwsr_size` |
| 5 | VGPR 256 / SGPR 102 | **NO** | `MEDIDO_EN_FUENTE` (`gfx_8_0_enum.h:2816,2822`). Depende de un emisor de shaders, que **no existe** (§2.8: `get_cu_occupancy` para GFX8 es `PROVEN_ABSENT`). Escribirlo sin consumidor seria una constante de autoridad sin nadie que la cite |
| 6 | clocks: `fcompute` 1071 | **SI** | `RX550_ASIC_CLK_FCOMPUTE_MAX_MHZ`. **`mem_clk_max` NO**, y es una decision: el valor esta medido pero **la unidad no esta verificada** en ningun sitio del corpus, y multiplicarlo por el ancho de linea daria un ancho de banda con una unidad inventada |
| 7 | `num_cp_queues` = 24 | **SI**, sin decomponer | `RX550_ASIC_NUM_CP_QUEUES`. `24 / 2 MEC = 12` es una division, no una geometria: la verdad esta en `cp_queue_bitmap` (`kfd_device_queue_manager.c:97-101`), que no es una constante. **NO_DETERMINED**, propietario nombrado |
| **8** | **SDMA 2 motores x 2 colas = 4** | **SI** | `RX550_ASIC_NUM_SDMA_ENGINES`, `_QUEUES_POR_ENGINE`, y `_QUEUES` derivado como producto |
| **9** | **no hay L2** | **SI** | `RX550_ASIC_CACHE_NIVEL_MAX 1u`, con el assert que lo declara. La ausencia **esta medida**: se leyeron las 16 y ninguna es de nivel 2, y `dummy_cache_info` **si** tiene un L2 de 2048 KiB |
| **10** | **`cache_line_size` = 64 B** | **SI** | `RX550_ASIC_CACHE_LINE_SIZE` |
| 11 | `max_hw_contexts` = 8 | **NO, y con nombre propio** | ver abajo |
| 12 | significado de `type` 9/10 | **NO** | `NOT_FOUND` en el corpus. Las cabeceras UAPI de KFD no estan. **No se decodifica lo que no se puede citar** |
| 13 | bits de `HSA_CAP_*` | **NO** | `NOT_FOUND` en el corpus, misma causa. Sin el shift no se decodifica `capability` |
| 14 | unidades de `num_cu_per_array` | **NO** | `HYPOTHESIS` en el informe, **sin comprobar**. No se ha usado para nada de lo escrito, y el bloque `§4.3` lo dice explicitamente para que nadie lo cite despues |

**Por que 11 NO se ha escrito, y este es el que mas puede incomodar:**
`max_hw_contexts = 8` esta en `gfx_v8_0.c:1688` y es `MEDIDO_EN_FUENTE`. Choca con dos
constantes del driver, **ninguna corroborada**: `TVM_NR_CTL_CONTEXTS 2`
(`target_vm.h:66`) y `RX550_GMC_NR_VMIDS 16` (`rx550_mmio_access.c:762`). **El criterio
que falta es este:** no se sabe si `max_hw_contexts` (tope de contextos de hardware
simultaneos, `gfx.config`) es **el mismo objeto** que `TVM_NR_CTL_CONTEXTS` (cuenta de
contextos de control del driver). Si lo son, escribir 8 crea una cuarta autoridad sin
resolver las otras dos; si no lo son, no hay conflicto y las tres conviven. **No se puede
decidir sin la definicion de `TVM_NR_CTL_CONTEXTS` en su propio `.c`, y ese `.c` no esta
en el arbol.** Declaro el criterio que falta; no lo invento. **Propietario del cierre: el
fichero que define esa constante.**

Las cinco que faltan (2, 5, 11, 12, 13) estan **todas** bloqueadas por una misma clase de
hueco — firmware del SQ/RLC, un emisor de shaders que no existe, o cabeceras UAPI
ausentes del corpus — y **ninguna se cierra escribiendo un numero en el driver.** Por eso
el ranking de §7 no baja de 7 de 14 en este turno, y eso es el resultado honesto.

---

## 8 · QUE NO PUDE HACER, Y POR QUE — CON NOMBRE PROPIO

| nombre | que es | por que no se hizo |
|---|---|---|
| **`D1-PAPEL-PDB0`** | Que papel tiene `rx550_pdb0` dentro del diseno: ¿tabla de 2 MiB de un subrange, o se absorbe en `rx550_vmid1_pgt.c`, o se retira? | **No hay consumidor.** `rx550_pdb0_*` no se llama desde ningun `.c` de `Makefile:30`, solo desde su test. Sin consumidor no hay criterio para elegir entre las tres, y elegir sin criterio seria inventar el diseno. **Propietario: el nodo que integre el backing.** Enquanto tanto: ambito intacto, numero intacto, y la ambiguedad escrita en la cabecera |
| **`D1-TERCERA-AUTORIDAD`** | Que papel tiene `target_mem.h` (`TM_LEVEL_ENTRIES 512`), que el informe llamo "tercera autoridad" | **No lo incluye nadie** en el arbol, verificado por barrido: no esta en el `.ko` y no compite con nadie. Reescribirlo es trabajo sin consumidor. **Propietario: el nodo que meta `target_mem.h` en obj-m**, que es cuando nace el conflicto |
| **`D4-FUSION-18`** | Fusionar el `18u` de `rx550_vmid1_pgt.c:101` con `RX550_VM_PFN_SHIFT` de `rx550_vm_geom.h` | **La identidad del encargo es incorrecta** (§6). Son dos literales del corpus (`amdgpu_vm.c:2359` y `:2421`) con el mismo sentido y dos cuentas distintas. Fusionarlos obligaria a un `.c` a incluir el `.h` de un componente que no comparte su ambito. Se nombran los dos por separado |
| **`MAX-HW-CONTEXTS`** | Escribir `max_hw_contexts = 8` | **Falta el criterio** (§7, item 11). Declarado en el bloque `LO QUE NO ESTA` de `rx550_asic_geom.h` con su conflicto y su propietario |
| **`MEM-CLK-UNIDAD`** | Escribir `mem_clk_max = 1500` | **La unidad no esta verificada** en ningun sitio del corpus. Escribirla invita a multiplicarla por el ancho de linea. **Propietario: documentacion HSA/KFD** |
| **`DECODE-CAPABILITY`** | Decodificar `capability = 4736` | `HSA_CAP_ASIC_REVISION_SHIFT` se **usa** (`kfd_topology.c:2098`) y **no esta definido** en ninguna cabecera del corpus. Sin el shift no se separan los campos. **Propietario: la cabecera UAPI de KFD, ausente** |
| **`5-CU-HIPOTESIS`** | Usar que `num_cu_per_array` signifique "SIMD por array" | Es `HYPOTHESIS` y sigue sin comprobar. Encaria con el 5 y con el 10, pero usarla para escribir una constante seria promover una hipotesis a hecho. Queda escrita **como hipotesis** en el bloque `§4.3`, con lo que explicaria y sin usarse |
| **`CU-CONSUMIDORES`** | Los cinco puntos de decision de §7 item 1 (dimension de cwsr, techo de oleadas, reparto de dispatch en PM4, `*_CU_FULL_*`, atribucion de cache a CU) | **No existe codigo de shader.** Verificado por el informe por dos caminos y no rehecho aqui: `get_cu_occupancy` para GFX8 es `PROVEN_ABSENT` (~40 lineas en `gfx_v8_kfd2kgd`) y no hay emisor de shaders. Las constantes tienen consumidor **declarado** en la cabecera y **cero** codigo que las use. Escribir ese consumidor seria escribir un subsistema entero que nadie ha pedido |

---

## 9 · LO QUE SE PUEDE ROMPER, Y COMO SE SABE

| clasificacion mia | como se refuta |
|---|---|
| `RX550_NR_CU_CAPACIDAD = 8` | una relectura de `nodes/1/properties` con `cwsr_size != 2789376`. **MEDIDO HOY = 2789376** |
| `RX550_NR_CU_INDICE_MAX = 10` | una relectura de `nodes/1/caches` con menos de 16 entradas, **o** con `array_count * cu_per_simd_array < 10`. **MEDIDO HOY = 16 entradas y 2 * 5** |
| las dos a la vez | una lectura de `max_cu_per_sh = 4` (2 arrays x 4 CU/array), que es el otro lado de la cuenta de §2.2 y arbitraria el conflicto. **NO HECHA: es debugfs** |
| `RX550_PDB0_BLOCK_SIZE = 9` | que el campo `PAGE_TABLE_BLOCK_SIZE` dejara de ser `block_size - 9` |
| `PLACEMENT_DEF = LOW` | que `RX550_GART_START` dejara de ser 0, y el `_Static_assert` cae |
| los dos 9 no fusionados | que `amdgpu_vm.c:2361-2364` y `gmc_v8_0.c:933-934` se refieran al mismo hecho. **No se ha comprobao** |
| todo el turno | una relectura del `.ko` con `.text` distinto de 22 718 B, o un `make -s clean && make -s` con algun `fichero:linea:col: warning` |

---

## 10 · ESTADO DE SALIDA

```
APLICADO
  §4.3   rx550_asic_geom.h, NUEVO, 262 lineas, md5 fa1e2ab7b6360bf670ee2c35725ad42d
         RX550_NR_CU_CAPACIDAD = 8   y   RX550_NR_CU_INDICE_MAX = 10
         con los dos discriminantes escritos, el CONFLICTADO marcado, los refutadores
         puestos, y 9 _Static_assert que son los discriminantes (mutacion: 5 de 9 caen)
         incluido desde rx550_target.c:44-48 para que se compilen.  obj-m intacto
  D1     rx550_pdb0.h: 512 deja de ser HARDWARE_REQUIREMENT, pasa a MODEL_CHOICE
         derivado de RX550_VMID1_BLOCK_SIZE_MIN.  "CANONICA" fuera.  El ambito escrito.
         Comportamiento: cero (512, 4096, 2 MiB).  Lo demuestra tests/test_pdb0.c
  D2     TRES cadenas corregidas, no dos: rx550_vmid1_pgt.h:292, el texto del switch de
         diagnostico, y el bloque "LO QUE SE SABE DE CADA VALOR" del .c, que estaba al
         reves.  Todas dicen ahora el rango [9, 24] que la guarda comprueba de verdad
  D3     RX550_GART_PLACEMENT_DEF: BEST_FIT -> LOW, con _Static_assert que ata la politica
         al RX550_GART_START declarado.  RX550_GART_START NO se toca.  .text -32 B;
         el comportamiento por defecto del modulo NO cambia (module_param a 0).
         Lo demuestra tests/test_gart_geom.c:136-143
  D4     4 literales nombrados, en 3 constantes distintas y SIN fusionar.
         UNA IDENTIDAD DEL ENCARGO REFUTADA: el 9u de :106 no es el offset del campo.
         Y una cita falsa corregida: el 18 no es de amdgpu_gmc.h, es de amdgpu_vm.c:2421
  §5     escritas 1, 3, 4, 6(parcial), 7, 8, 9, 10.  NO escritas 2, 5, 11, 12, 13, 14,
         cada una con su bloqueo y su propietario en §8 de este fichero

PUERTA
  make -s -C tests run   rc=0   1634 PASS / 0 FAIL   estatico 69 PASS / 0 FAIL   (igual)
  make -s                rc=0   .ko 1 123 688 B (antes 1 123 560)   0 diagnostics
  md5 .ko  f5712df25e1e64271ab789c4bed87db0

SIN TOCAR
  06-INGENIERIA-INVERSA/findings/  ·  sin renumerar nada  ·  sin hallazgo nuevo
  sin git add · sin git commit · sin grep · sin red · sin GPU · sin /dev/dri · sin sysfs
  escrito · sin debugfs · sin dmesg/journalctl
  RX550_GART_START = 0 intacto · las cuatro escrituras PRT golden intactas · las ocho
  escrituras de SECCION no se han tocado · la formula de cobertura (e417d64) intacta y
  no "simplificada" · core en C, sin C++/Rust/Go · los .h sin includes de libc
```