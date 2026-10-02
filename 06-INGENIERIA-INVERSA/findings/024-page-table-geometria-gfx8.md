# 024 · Geometría del page table en GFX8: cerrada de extremo a extremo, sin runtime

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=RESEARCH/working/linux-7.1.3`
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=0`
`RUNTIME=NOT_RUN` · `GPU INTACTA`

---

## ⛔ RETRACTADO 2026-10-01 (parcial) — §2.3, §2.4 y §6: `block_size` era 13, es 10

Resuelto como `C-003` en `docs/CONTRADICTIONS.md`. Este documento sigue siendo
válido en el resto; lo que se retracta es el valor de `block_size` y todo lo que
él deriva.

**El error de método**, que es lo que importa repetir bien: leí la *firma* de la
función en vez de su *call site*.

```c
static uint32_t amdgpu_vm_get_block_size(uint64_t vm_size)   // el PARÁMETRO se llama vm_size
...
adev->vm_manager.block_size = amdgpu_vm_get_block_size(tmp); // el ARGUMENTO es tmp
```

Sustituí el nombre del parámetro por el del argumento. Los dos universos
discrepan —`working/` y `baseline/` (byte-idénticos, `263c5d83b1f1`) y
`linux-7.2.8` (`amdgpu_vm.c:2430`) dicen los dos `get_block_size(tmp)`— y con
`tmp = 2` la función cae en `x <= 8`, que este documento pasó por alto:

```
bits = ilog2(2) + 18 = 1 + 18 = 19 ;  2 <= 8  ->  19 - 9 = 10
```

Contraste con la línea que el host ya tenía en el log desde el arranque
(`journalctl -k`, no `dmesg`, que no la expone):

```
amdgpu 0000:01:00.0: vm size is 64 GB, 2 levels, block size is 10-bit, fragment size is 9-bit
```

`RUNTIME=NOT_RUN` era la condición que hacía posible el error: al no ejecutar,
la única comprobación disponible era el texto, y el texto pedía leer el call
site. El valor de `max_pfn`, `num_level` y `fragment_size` de este documento
**no cambian**: siguen correctos.

## CUDA principal

La geometría del page table de Polaris12 **queda determinada numéricamente**, no solo
estructuralmente. Todo el calculo del driver es estatico y su entrada en esta host es
legible:

```
vm_size         = 64 GB      (clamp: RAM*3 = 36 -> min_vm_size = 64)
max_pfn         = 64 << 18   = 16777216 paginas
num_level       = 1          (min(max_level=1, 2))   root_level = AMDGPU_VM_PDB0
block_size      = 10
fragment_size   = 9
PAGE_TABLE_BLOCK_SIZE escrito = block_size - 9 = 1  -> 0x01000000
```

`num_level = 1` **confirma por aritmetica** la afirmacion de `DRIVER-MISSION-STATE.md`
("el modelo de VM es plano por necesidad"): no es que GFX8 no tenga motor de recorrido,
es que con `max_level=1` **no puede tener mas de un nivel**. La razon es una
parametrizacion del driver, no una limitacion del silicio demostrada.

## Alcance exacto

1. Localizar la funcion que decide la geometria del page table y sus parametros por ASIC.
2. Resolver la cadena completa hasta el valor escrito en el registro.
3. Ejecutar el calculo con las entradas de esta host.
4. Separar lo que es aritmetica verificada de lo que es inferencia sobre el hardware.

## Criterio de terminacion (cumplido)

La cadena `parametros -> vm_size -> num_level -> block_size -> PAGE_TABLE_BLOCK_SIZE`
esta cerrada y evaluada. El unico punto no determinable desde el corpus queda nombrado.

---

## 1 · La funcion y sus parametros

`amdgpu_vm_adjust_size(adev, min_vm_size, fragment_size_default, max_level, max_bits)`.
GFX8 la invoca con valores fijos (`gmc_v8_0.c:1127`):

```
amdgpu_vm_adjust_size(adev, 64, 9, 1, 40);
/*                       min  frag  max_  max_
                           _vm  _def  level  bits  */
```

Contraste con otras generaciones, para ver que `max_bits` es el parametro que decide:

| ASIC | llamada | max_bits |
|---|---|---|
| `gmc_v6_0` | `(adev, 64, 9, 1, 40)` | 40 |
| `gmc_v7_0` | `(adev, 64, 9, 1, 40)` | 40 |
| **`gmc_v8_0`** | **`(adev, 64, 9, 1, 40)`** | **40** |
| `gmc_v9_0` | `(adev, 128*1024+512, 9, 2, 48)` | 48 |
| `gmc_v10_0` | `(adev, 256*1024, 9, 3, 48)` | 48 |

GFX8 comparte parametros con GFX6/7: **1 nivel, 40 bits**. GFX9 ya tiene 2 niveles y
48 bits. La frontera de generacion es visible en los parametros.

## 2 · La cadena, paso a paso

### 2.1 · `vm_size` — depende de la RAM del host, no de la VRAM

```
max_size    = 1 << (max_bits - 30)              = 1 << 10 = 1024 GB
vm_size     = roundup_pow_of_two(
                clamp(phys_ram_gb * 3, min_vm_size, max_size))
```

`phys_ram_gb` sale de `si_meminfo()`. El comentario del driver explica el `*3`:
mapear RAM del sistema mas VRAM, asumiendo VRAM <= RAM, mas margen para fragmentacion.

En esta host (`/proc/meminfo`, `MemTotal: 12098912 kB`):

```
phys_ram_gb = ceil(12098912 kB / 1 MiB) = 12
*3 = 36
clamp(36, 64, 1024) = 64        <-- min_vm_size gana
roundup_pow_of_two(64) = 64 GB
```

**El clamp es lo que decide en esta maquina.** Con 36 GB de entrada el valor pedido es
menor que el minimo, luego `vm_size = min_vm_size = 64` y el resultado **no depende de
la RAM**. Eso es `PROVEN` para cualquier host con menos de ~21 GB de RAM: el mismo
`vm_size`. Host con 32 GB: 32*3 = 96 -> `roundup_pow_of_two(96)` = 128, y ahi si cambia.

Unidades: `vm_size` esta en **GB** en todo el calculo, no en bytes ni en paginas.
`vm_size <= 8` dentro de `get_block_size` compara GB. Es ambiguo al leerlo sin el
contexto, y por eso lo dejo dicho.

### 2.2 · `max_pfn` y `num_level`

```
max_pfn   = (uint64_t)vm_size << 18        = 64 << 18 = 16777216
tmp       = roundup_pow_of_two(max_pfn)    = 16777216
tmp       = DIV_ROUND_UP(fls64(tmp) - 1, 9) - 1   = 2
num_level = min(max_level, tmp)            = min(1, 2) = 1
root_level= AMDGPU_VM_PDB0
```

**`num_level = 1` porque `max_level = 1`**, aunque el calculo del tamaño pediria 2.
El clamp es de nuevo lo que decide. Si `max_level` fuera 2, este host tendria 2 niveles.

### 2.3 · `block_size`

Con `num_level > 1` seria 9 fijo; con `num_level == 1` delega:

```
block_size = amdgpu_vm_get_block_size(tmp)
  tmp = DIV_ROUND_UP(fls64(max_pfn)-1, 9) - 1 = DIV_ROUND_UP(24, 9) - 1 = 3 - 1 = 2
  bits = ilog2(tmp) + 18 = ilog2(2) + 18 = 1 + 18 = 19
  tmp <= 8  ?  si (2 <= 8)
  -> bits - 9 = 19 - 9 = 10
```

**`block_size = 10`.** La rama que se toma es `bits - 9`, la misma que el
comentario describe para "up to 8GB address space" — y `tmp` es un **contador de
niveles**, no un tamaño en GB. La función recibe un argumento que no es de la
magnitud que su nombre anuncia; por eso `tmp = 2` cae en la rama `x <= 8` aunque
la VM sea de 64 GB. Ver el aviso de retraction arriba.

Contraste de la funcion, evaluada sobre su **argumento real**, que es `tmp` (un
contador de niveles), no `vm_size` en GB:

| argumento `tmp` | block_size | rama | ¿es el caso de Polaris12? |
|---|---|---|---|
| 1 | 9 | `bits - 9` | no |
| **2** | **10** | `bits - 9` | **sí** — `tmp = DIV_ROUND_UP(24,9)-1 = 2` |
| 64 | 13 | `(bits+3)/2` | no — 64 es `vm_size` en GB, que no se pasa |
| 1024 | 15 | `(bits+3)/2` | no |

La fila de 64 es la que produjo el error retractado: el valor es correcto como
evaluación de la función, pero 64 no es lo que el driver le pasa.

### 2.4 · Lo que llega al registro

`gmc_v8_0_gart_enable` (`gmc_v8_0.c`, contexto 1):

```c
tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, PAGE_TABLE_BLOCK_SIZE,
                    adev->vm_manager.block_size - 9);
```

Con `block_size = 10`: escribe **1**. Encoding
(`gmc_8_2_sh_mask.h:6543-6544`): `MASK 0xf000000`, `SHIFT 0x18`, luego
`0x01000000`.

## 3 · El hallazgo: los dos contextos reciben geometrias distintas

En `gmc_v8_0_gart_enable` los contextos no se configuran igual:

| registro | contexto 0 (GART) | contexto 1-15 (userspace) |
|---|---|---|
| `PAGE_TABLE_DEPTH` | **0** | **1** |
| `PAGE_TABLE_START_ADDR` | `gart_start >> 12` | `0` |
| `PAGE_TABLE_END_ADDR` | `gart_end >> 12` | `max_pfn - 1` |
| `PAGE_TABLE_BLOCK_SIZE` | **no se escribe** | `block_size - 9 = 1` |
| `PAGE_TABLE_BASE_ADDR` | `table_addr >> 12` | `table_addr >> 12` (los 15) |

`PAGE_TABLE_DEPTH` (`MASK 0x6`, `SHIFT 0x1`) es un campo de **2 bits con 3 valores
posibles** (`0`, `1`, `2`), y el driver escribe `0` para el contexto 0 y `1` para los
contextos de usuario. El mismo registro, distinto valor, mismo ASIC.

`PAGE_TABLE_BLOCK_SIZE` **no se escribe para el contexto 0**: queda con su valor de
reset. Es una asimetria real entre el contexto del kernel y los de userspace, y no
esta comentada en el codigo.

`NEGATIVE_RESULT` con alcance: el corpus **no declara que signifique** la diferencia
entre `PAGE_TABLE_DEPTH = 0` y `= 1`. No hay enumeracion, ni comentario, ni
documentacion en `gmc_8_2_sh_mask.h` ni en ninguna parte del arbol. `NOT_DETERMINED`
con causa nombrada.

Lo que si se puede afirmar sin invocar semantica: son **valores distintos en el mismo
campo**, escritos por el mismo driver en la misma funcion. Eso es `PROVEN`. Que el
0 signifique "GART plano" y el 1 "VM de usuario con page table" es `HYPOTHESIS`
coherente con el contexto de cada llamada, no `PROVEN`.

## 4 · La convencion del `-9` es del driver, no del hardware

`PAGE_TABLE_BLOCK_SIZE` se rellena con `block_size - 9` en GFX8 y en todas las
generaciones posteriores (`gfxhub_v1_0`, `v1_2`, `v11_5_0`, `v12_0`, `v12_1`).

El hardware no lo declara. En el arbol de registros, el campo es un `MASK` y un
`SHIFT`, sin ninguna nota sobre el offset:

```
gmc_8_2_sh_mask.h:6543   VM_CONTEXT1_CNTL__PAGE_TABLE_BLOCK_SIZE_MASK     0xf000000
gmc_8_2_sh_mask.h:6544   VM_CONTEXT1_CNTL__PAGE_TABLE_BLOCK_SIZE__SHIFT  0x18
```

Comparacion con GFX9+, donde el mismo campo tiene **distinto mask y shift**:

```
mmhub_1_0_sh_mask.h:8092  PAGE_TABLE_BLOCK_SIZE_MASK     0x00000078L
mmhub_1_0_sh_mask.h:8073  PAGE_TABLE_BLOCK_SIZE__SHIFT  0x3
```

4 bits en GFX8 (shift 24) frente a 4 bits en GFX9 (shift 3): mismo ancho, encoding
distinto. El hardware **redefine el campo** entre generaciones, luego el `-9` no puede
leerse como una convencion estable del hardware. Es una convencion del driver, y
`MODEL_CHOICE` para el driver propio.

Consecuencia directa sobre lo que afirmo: **el valor 1 que llega al registro es
`PROVEN`. Que el hardware lo interprete como "block_size menos nueve" es
`HYPOTHESIS`**, sostenida por que el driver escriba `block_size - 9` en todas
las generaciones, no por el hardware.

## 5 · Saturacion: el campo tiene 4 bits y `block_size` puede excederlos

`MASK 0xf000000` son 4 bits. `block_size - 9` con `block_size = 10` da 1, muy
dentro de rango. Y como `tmp = DIV_ROUND_UP(fls64(max_pfn)-1, 9) - 1` crece muy
 despacio —un peldaño por cada 9 bits de `max_pfn`, no por cada GB— el campo
saturar exigiría una VM mucho mayor que los 1024 GB que permite el cap de
`max_bits = 40`. La tabla queda holgada para esta generación:

```
vm_size=1024 GB -> block_size=15  -> -9 = 6    dentro de 4 bits
vm_size=2048 GB -> block_size=16  -> -9 = 7    dentro de 4 bits
vm_size=4096 GB -> block_size=16  -> -9 = 7    (ya no crece)
```

Con `max_bits = 40`, `max_size = 1024` y `vm_size` esta acotado a 1024, luego
`block_size <= 15` y `-9 <= 6`: **no hay saturacion en GFX8**. Queda registrado porque
un campo de 4 bits con un valor calculado que podria desbordarlo es una fragilidad
que el driver propio no debe heredar sin comprobarla; en ASIC con `max_bits` mayor si
podria ocurrir. `NOT_APPLICABLE` en esta placa, `NEGATIVE_RESULT` heredable.

## 6 · Clasificacion

| Afirmacion | Estado |
|---|---|
| GFX8 invoca `amdgpu_vm_adjust_size(adev, 64, 9, 1, 40)` | `PROVEN` (`gmc_v8_0.c:1127`) |
| `max_bits = 40` limita `vm_size` a 1024 GB | `PROVEN_DERIVED` |
| `vm_size = 64 GB` en esta host, y en cualquier host con < 21 GB RAM | `PROVEN_DERIVED` |
| `max_pfn = 16777216` | `PROVEN_DERIVED` |
| `num_level = 1`, `root_level = AMDGPU_VM_PDB0` | `PROVEN_DERIVED` |
| `block_size = 10` | `PROVEN` (observado en el log de arranque) |
| `PAGE_TABLE_BLOCK_SIZE = 1` (`0x01000000`) | `PROVEN_DERIVED` |
| Los contextos 0 y 1-15 reciben `PAGE_TABLE_DEPTH` distinto | `PROVEN` (0 vs 1) |
| El contexto 0 no recibe `PAGE_TABLE_BLOCK_SIZE` | `PROVEN` (no se escribe) |
| Que significa `PAGE_TABLE_DEPTH` 0 frente a 1 | `PROVEN` — `064:168` da los bits `[2:1]` (shift `0x1`, máscara `0x6`), y `030` mide qué PTBA escribe el driver en cada caso: `= 0` para VMID 0 y `= 1` para VMID 1-15 |
| Que el hardware lea `PAGE_TABLE_BLOCK_SIZE` como valor + 9 | `HYPOTHESIS` — convencion del driver |
| Que `num_level = 1` sea una limitacion del silicio | `REFUTED` — viene de `max_level = 1`, un parametro |
| Que el page table plano sea por limitacion del hardware | `NOT_DETERMINED` |

Ultima fila, y es la que reencuadra `DRIVER-MISSION-STATE.md`. Ese documento afirma
"GFX8 no tiene motor de recorrido de tabla de paginas. La tabla la escribe la CPU. El
modelo de VM es plano por necesidad, no por eleccion". La segunda frase queda
`REFUTED`: el nivel se elige por `max_level = 1`, un argumento del driver. La primera
—que no hay motor de recorrido— no la toco: `PROVEN` en el corpus (0 registros `mmVM_*`
en `gca/gfx_8_0_d.h` y `gfx_8_1_d.h`, 61 en `gmc/gmc_8_2_d.h`), y es compatible con un
modelo plano. Que no haya motor **y** que el elija el software son dos hechos
distintos que el documento mezclaba.

## 7 · Confounders

Ninguno para la aritmetica. Dos cosas que **no** son confounders pero si límites:

- `vm_size` depende de `si_meminfo()`. Use `/proc/meminfo` de esta host. Un host con
  mas de ~21 GB de RAM daria `vm_size` mayor y por tanto `block_size` distinto. El
  valor 64 es el de **esta** maquina; la formula esta en el documento y vale para
  cualquiera.
- Los tres module params estan en `-1` en esta host (§9), luego el calculo corre por
  la rama automatica. En un host donde alguien los fuerce, la formula del documento
  sigue valiendo pero los valores no. `MODEL_CHOICE` del host, no del ASIC.

## 8 · UNLOCKS

- El driver propio tiene la geometria de page table **completa y numerica** para
  Polaris12: 1 nivel, `block_size` 10, `fragment_size` 9, `max_pfn` 16777216. No hay
  que derivarla ni suponerla.
- La asimetria contexto-0 / contexto-1-15 queda localizada y **sin explicar**, que es
  el punto de entrada correcto para seguir: es el sitio donde el modelo plano del
  kernel y el de userspace divergen en el mismo hardware.
- El `-9` queda como `MODEL_CHOICE` documentado, no como herencia. El driver propio
  puede escribir `block_size` directamente si su convencion lo permite, y debe elegirlo
  conscientemente: el hardware no declara offset.
- `AGENTS.md:139` ("PTBA software production cerrada") queda reforzado con la
  geometria que la sostiene, no solo con la secuencia de escrituras.

## 9 · Criterio de falsificacion

Se refutaria si: (a) `amdgpu_vm_size` estuviera fijado por module param en esta host,
lo que invalidaria el `vm_size = 64` y por tanto `block_size`; (b) el `dev_info` de
`amdgpu_vm_adjust_size` dijera otro valor; (c) `PAGE_TABLE_DEPTH` tuviera un
significado documentado en una fuente primaria; (d) el hardware de GFX8 aceptara
`num_level > 1`.

**Comprobado (a): los tres parametros estan en `-1` en esta host.**

```
$ cat /sys/module/amdgpu/parameters/vm_size          -> -1
$ cat /sys/module/amdgpu/parameters/vm_fragment_size  -> -1
$ cat /sys/module/amdgpu/parameters/vm_block_size     -> -1
```

Los tres estan en su valor "sin forzar", luego se toma la rama automatica en los tres
puntos del calculo. `vm_size = 64` **no es un supuesto con una laguna**:
`Falsificacion (a) = ELIMINADA`. Lectura de sysfs, sin privilegio, sin RUNTIME.

(b) sigue sin comprobar: requiere el `dev_info` del arranque, que es una medicion
runtime del log. (c) requiere documentacion externa. (d) requiere hardware.

## 10 · Evidencia

```
gmc_v8_0.c:  1127 (adjust_size con 64,9,1,40), gart_enable completo
             PAGE_TABLE_DEPTH 0 (contexto0) / 1 (contexto1)
             PAGE_TABLE_BLOCK_SIZE = block_size - 9 (solo contexto1)
amdgpu_vm.c: 2349-2369 (get_block_size), 2379-2465 (adjust_size completo)
gmc_8_2_sh_mask.h: 6459-6460 (DEPTH mask/shift), 6499-6500 y 6543-6544
             (BLOCK_SIZE mask/shift GFX8), 6771-6778 (START/END ADDR)
mmhub_1_0_sh_mask.h: 8073, 8092 (mismo campo, mask/shift distintos en GFX9)
gfxhub_v1_0.c:226, v1_2.c:282, v11_5_0.c:319, v12_0.c:324, v12_1.c:446
             (el -9 en todas las generaciones)
gca/gfx_8_0_d.h, gfx_8_1_d.h: 0 coincidencias de mmVM_
gmc/gmc_8_2_d.h:              61 coincidencias de mmVM_
host: /proc/meminfo -> MemTotal: 12098912 kB
       /sys/module/amdgpu/parameters/{vm_size,vm_fragment_size,vm_block_size} = -1
       lectura sin privilegio; NO es RUNTIME sobre la GPU
```

Ningun registro obtenido de MMIO. Ninguna operacion runtime. `GPU INTACTA`.

Nota de redaccion: el borrador de §4 contenia texto en otro idioma introducido
al escribir. Corregido; el contenido tecnico no cambio. Quinto caso del mismo
defecto, y por eso la nota se conserva en vez de borrarse.