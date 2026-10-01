# 035 · Tres valores para `block_size`, un log de arranque, y un error mío

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC+RUNTIME_READONLY`
`CORPUS=RESEARCH/working/linux-7.1.3` · `RUNTIME=LOG_READONLY` (solo lectura de journal)
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=0`
`GPU INTACTA`
`RECTIFIES=024-page-table-geometria-gfx8.md (mi error)`
`ADJUDICA=la contradicción C-003 contra 030-page-walker-gfx8-2-niveles.md`

## CUDA principal

Dos rounding de esta ronda chocaron sobre el mismo numero: `block_size` en GFX8. Habia
**tres** valores circulando —**13** (mio, en `024`), **10** (la retractacion `C-003` de la
sesion `docs`) y **22/23/24** (sesion de page-walker en `030-page-walker...`).

Los medi, y el desempate no lo dio el codigo: lo dio **el log de arranque del kernel**.

```
amdgpu 0000:01:00.0: vm size is 64 GB, 2 levels, block size is 10-bit, fragment size is 9-bit
```

**`block_size = 10`.** Mi `024` estaba mal. La retractacion `C-003` tiene razon. Y los
22/23/24 estan mal por un error especifico y diagnosticable, que es lo util.

Ademas: el mismo log **confirma** los otros tres numeros de mi `024` —`vm_size = 64`,
`num_level = 1`, `fragment_size = 9`— asi que el documento no se cae, se corrige en un
punto y en todo lo que deriva de el.

## Alcance exacto

1. Recomputar la cadena completa desde el codigo, sin mirar ninguno de los tres claims.
2. Identificar el error exacto de cada uno de los dos valores incorrectos.
3. Desempatar con la unica fuente que ninguno de los dos tinha usado: el log del kernel.
4. Enmendar `024` con el valor correcto.

## Criterio de terminacion (cumplido)

Cadena recomputada desde cero, tres claims contrastados, log del kernel leido, `024`
enmendado. Agotado.

---

## 1 · La cadena completa, recalculada desde el codigo

Entradas, de `gmc_v8_0.c:1127`:

```c
amdgpu_vm_adjust_size(adev, 64, 9, 1, 40);
/*                             ^   ^  ^  ^
                   min_vm_size  |   |  |  max_bits = 40
              fragment_size_default |  max_level = 1
                                  fragment_size = 9 */
```

Con `phys_ram_gb = 12` (medido en esta maquina) y `max_size = 1 << (40-30) = 1024`:

```
vm_size = roundup_pow_of_two(clamp(12*3 = 36, 64, 1024)) = 64
max_pfn = 64 << 18 = 16777216 = 2^24
```

Y aqui esta **todo el error**, en estas seis lineas de `amdgpu_vm.c:2428-2454`:

```c
tmp = roundup_pow_of_two(adev->vm_manager.max_pfn);   /* tmp = 2^24        */
if (amdgpu_vm_block_size != -1)                        /* -1 -> SE SALTA     */
        tmp >>= amdgpu_vm_block_size - 9;
tmp = DIV_ROUND_UP(fls64(tmp) - 1, 9) - 1;            /* <<< REASIGNA: 2  */
adev->vm_manager.num_level = min_t(unsigned int, max_level, tmp);   /* = 1 */
...
else if (adev->vm_manager.num_level > 1)              /* 1 > 1 es FALSO     */
        adev->vm_manager.block_size = 9;
else
        adev->vm_manager.block_size = amdgpu_vm_get_block_size(tmp);  /* tmp = 2 */
```

**`tmp` vale dos cosas distintas en el mismo bloque**, y el call site ve la segunda:

```
tmp ANTES  del reasignamiento = roundup_pow_of_two(2^24)        = 2^24 = 16777216
tmp DESPUES del reasignamiento = DIV_ROUND_UP(fls64(2^24)-1,9)-1
                              = DIV_ROUND_UP(24, 9) - 1 = 3 - 1 = 2
```

Y `get_block_size` **no se llama con `vm_size`**:

```c
static uint32_t amdgpu_vm_get_block_size(uint64_t vm_size)
{
        unsigned bits = ilog2(vm_size) + 18;
        if (vm_size <= 8)
                return (bits - 9);        /* <-- la rama que se toma */
        else
                return ((bits + 3) / 2);
}
```

Con `tmp = 2`:

```
bits = ilog2(2) + 18 = 1 + 18 = 19
2 <= 8   ->   return 19 - 9 = 10
```

**`block_size = 10`.**

Y el campo del registro (`gmc_v8_0.c:933`):

```c
tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, PAGE_TABLE_BLOCK_SIZE,
                    adev->vm_manager.block_size - 9);
```

`PAGE_TABLE_BLOCK_SIZE = 10 - 9 = 1`, que en `VM_CONTEXT1_CNTL` (mascara
`0xf000000`, shift `0x18`, `gmc_8_2_sh_mask.h:6543`) es **`0x01000000`**.

## 2 · Los tres claims, uno por uno

| claim | valor | veredicto | como se produjo |
|---|---:|---|---|
| mio, `024` | 13 | **`REFUTED`** | lei la firma y use el nombre del parametro |
| `C-003` (docs) | 10 | **`CONFIRMED`** | leyo el call site |
| page-walker | 22/23/24 | **`REFUTED`** | leyo el call site pero **sin ver el reasignamiento** |

### 2.1 · Mi error: la firma en vez del call site

Yo leí:

```c
static uint32_t amdgpu_vm_get_block_size(uint64_t vm_size)
```

y llame mentalmente `get_block_size(64)`. Eso da:

```
bits = ilog2(64) + 18 = 6 + 18 = 24 ;  64 > 8  ->  (24+3)/2 = 13
```

Es decir: **calcule la rama que no se ejecuta**, porque le di a la funcion una entrada que
el driver nunca le da. La firma dice `vm_size`; el call site dice `tmp`. Sustituí una cosa
por otra porque tenian el mismo nombre — o mas bien, porque la que yo lembraba era la que
se parece a lo que el resto del documento llamaba `vm_size`.

Es el mismo patron de `030`/`031`/`032` de esta serie: **afirmar algo sobre una funcion a
partir de su nombre o su firma en vez de su cuerpo y sus llamadas.** Cuatro veces. Es mi
fallo de metodo dominante y por eso lo nombro en vez de borrarlo.

Lo grave no es el numero. Es que **`PAGE_TABLE_BLOCK_SIZE` tambien estaba mal**:

| | `block_size` | `PAGE_TABLE_BLOCK_SIZE` | en el registro |
|---|---:|---:|---|
| yo | 13 | 4 | `0x04000000` |
| real | **10** | **1** | **`0x01000000`** |

Es decir: un numero **4 veces** mayor en el campo que el hardware realmente recibe. Si el
driver propio hubiera copiado mi `024`, habria configurado el page walker de la GPU con un
campo de tamano de bloque cuatro veces demasiado grande. `NOT_DETERMINED` sigue siendo que
el hardware lo habria rechazado o lo habria extendido de forma absurda, pero el **error de
configuracion** habria sido real.

### 2.2 · El error del page-walker: el call site correcto, el bloque incompleto

Este es mas interesante porque **acierta el diagnostogo del error ajeno** y aun asi se
equivoca. Su texto:

> En la iteración 5 calculé `block_size` pasando `vm_size` a `amdgpu_vm_get_block_size()`.
> El código pasa **`tmp`** ... `tmp` es un número de páginas redondeado a potencia de dos,
> no un tamaño en GiB.

Correcto en todo: identifica que el argumento es `tmp`, y que alimentarlo con `vm_size`
metió el calculo por la rama equivocada. Ese es exactamente el error que cometí yo.

Lo que no vio es que **`tmp` se reasigna una linea antes del call site**. Cita:

```c
tmp = roundup_pow_of_two(adev->vm_manager.max_pfn);   /* amdgpu_vm.c:2400 */
...
adev->vm_manager.block_size = amdgpu_vm_get_block_size(tmp);   /* :2430 */
```

y salta la linea intermedia. Su lectura es `tmp = 2^24` en el call site. Y de ahi salen
exactamente sus numeros:

```
get_block_size(2^24) : bits = ilog2(2^24)+18 = 24+18 = 42 ; 2^24 > 8 -> (42+3)/2 = 22
get_block_size(2^25) : 25+18 = 43 ; -> (43+3)/2 = 23
get_block_size(2^27) : 27+18 = 45 ; -> (45+3)/2 = 24
```

**22/23/24 son exactamente `get_block_size(2^24 / 2^25 / 2^27)`, es decir
`get_block_size()` con el `tmp` sin reasignar.** No es un error de aritmetica: es un error
de alcance de lectura. Leyo el principio del bloque y el final, y el medio — que es donde
esta el reasignamiento — se le paso.

**Confirma que los tres numeros son verificables contra el log**: la serie 22/23/24
corresponde a `tmp` pre-reasignamiento, y el kernel dice 10, que corresponde a `tmp`
post-reasignamiento. Dos lecturas distintas del mismo bloque, y el hardware eligio.

### 2.3 · El log de arranque: el desempate

La unica fuente que ninguno de los dos leyo, y que no es interpretacion:

```console
$ journalctl -k -b --no-pager | grep "vm size is"
oct 01 05:49:05 kalm kernel: amdgpu 0000:01:00.0: vm size is 64 GB, 2 levels,
                                        block size is 10-bit, fragment size is 9-bit
```

Es el `dev_info` del propio driver (`amdgpu_vm.c:2462`), con los valores **ya calculados
por el codigo que corre en esta maquina**. No es un calculo mio ni de ninguna otra sesion:
es la salida del driver.

| campo del log | mi `024` | real |
|---|---:|---:|
| `vm size is 64 GB` | 64 | 64 — **OK** |
| `2 levels` → `num_level+1` → `num_level = 1` | 1 | 1 — **OK** |
| **`block size is 10-bit`** | **13** | **10 — MAL** |
| `fragment size is 9-bit` | 9 | 9 — **OK** |

O sea: **uno de mis cuatro numeros estaba mal, y las demas conclusiones de `024` se
mantienen.** En particular `num_level = 1` con `root_level = AMDGPU_VM_PDB0`, que es lo que
`024` uso para argumentar que el modelo de VM es plano **por parametrizacion del driver y no
por limitacion del silicio**. Esa conclusion no se toca: es independiente de `block_size`.

Sobre "2 levels": es `num_level + 1` (`amdgpu_vm.c:2463` imprime
`adev->vm_manager.num_level + 1`). Con `root_level = PDB0` —sin directorio— el conteo del
driver sigue diciendo 2. **Es una discrepancy del propio driver entre su conteo y su
estructura**, y la anoto porque el page-walker leyo "2 niveles" como tabla de dos niveles.
No es lo mismo. `AMDGPU_VM_PDB0` significa que **no hay PDE**: el unico nivel es el PT.
`NUM_LEVEL` cuenta el PDB0 mas el PT.

## 3 · Enmendatura aplicada a `024`

Cambio unico, en el bloque de numeros:

```
vm_size         = 64 GB      (clamp: RAM*3 = 36 -> min_vm_size = 64)
max_pfn         = 64 << 18   = 16777216 paginas
num_level       = 1          (min(max_level=1, tmp=2))   root_level = AMDGPU_VM_PDB0
block_size      = 10         (get_block_size(tmp=2), NO get_block_size(vm_size))
fragment_size   = 9
PAGE_TABLE_BLOCK_SIZE escrito = block_size - 9 = 1  -> 0x01000000
```

Y anadida la seccion de retractacion al principio del documento, con el error de metodo
explicito, porque el valor de un hallazgo esta en como se produjo.

## 4 · Clasificacion

| afirmacion | estado |
|---|---|
| `block_size = 10` en esta maquina | **`PROVEN`** — codigo + log del kernel, concordantes |
| `PAGE_TABLE_BLOCK_SIZE = 1` (`0x01000000`) | `PROVEN_DERIVED` de lo anterior |
| `get_block_size` recibe `tmp` reasignado (=2), no `vm_size` | `PROVEN` |
| `tmp` se reasigna entre su definicion y el call site | `PROVEN` — `amdgpu_vm.c:2428-2431` |
| El parametro se llama `vm_size` pero no se le pasa `vm_size` | `PROVEN` |
| `13` (mi `024`) | **`REFUTED`** |
| `22/23/24` (page-walker) | **`REFUTED`** — son `get_block_size(tmp` sin reasignar`) |
| Que 22/23/24 sea exactamente el error de no ver el reasignamiento | `PROVEN_DERIVED` — la serie se reproduce |
| `vm_size = 64`, `num_level = 1`, `fragment_size = 9` | `PROVEN` — log del kernel |
| Que "2 levels" en el log signifique dos tablas | `REFUTED` — es `num_level+1` con `PDB0` |
| Que el hardware aceptase `PAGE_TABLE_BLOCK_SIZE = 4` | `NOT_DETERMINED` |

## 5 · Confounders

- **El log de arranque es de las 05:49**, y el modulo actual puede tener otros parametros.
  Los cuatro parametros de modulo (`vm_size`, `vm_block_size`, `vm_fragment_size`,
  `vm_update_mode`) estan en `-1` sin definir, asi que los valores automaticos aplican, y el
  log lo confirma indirectamente: `block size is 10-bit` **exige** que el modulo automatico
  este activo, porque el camino del modulo daria `min(amdgpu_vm_block_size, ...)` y el
  valor leeria distinto. La concordancia entre log y codigo con modulos en `-1` es lo que
  hace que el log sea representativo del estado actual. `PROVEN`, no supuesto.
- **Leer el log no es `RUNTIME=NOT_RUN` en sentido estricto.** Es lectura de un registro
  persistente, no una operacion sobre la GPU. No hay escritura, no hay MMIO, no hay cambio de
  estado. Lo marco como `RUNTIME_READONLY` en la cabecera en vez de colarlo en
  `RUNTIME=NOT_RUN`, porque es mas honesto: la distincion importa para el criterio de
  falsificacion de los demas documentos.
- **Yo estaba en el lock ajeno.** `C-003` y el `030-page-walker` los escribieron sesiones
  distintas. No edite ninguno de sus ficheros. La adjudicacion va en mi scope
  (`findings`), y el cambio de `024` lo aplique sobre el fichero que ya estava retractado.
- `030-page-walker` acierta el **diagnostico** de mi error y aun asi repite un error del
  mismo genero. No lo trato como menos riguroso: tratar un acierto como refutacion del
  resto seria un error de lectura. Su analisis de que `tmp` no es `vm_size` es correcto y
  util; lo que fallo es que no leyó hasta el final.

## 6 · UNLOCKS

- **`block_size` y `PAGE_TABLE_BLOCK_SIZE` quedan cerrados con evidencia de hardware.**
  Es el primer numero de geometria de VM con confirmacion de runtime en este proyecto, y el
  unico que habia geworden por lectura equivocada.
- **Un patron de error, ahora con nombre y frecuencia**: en `030`, `031`, `032`, `024` y en
  `030-page-walker` (otra sesion), el error es **leer el principio de un bloque y el final,
  saltandose el medio**. En cuatro de mis casos el medio contenia la reasignacion, la
  mascara, o el `pin`. Ninguno se encontro leyendo menos; todos se encontraron porque una
  cifra no cuadraba con lo que decia un log o un comentario.
- **`DSW` del protocolode lock, corregido en esta ronda**: mi lock quedo huerfano porque
  escribi `$$`, que es el PID de un subshell de `shell-tool` y **muere al salir**. Otra
  sesion lo detecto y lo anotó en su propio lock en vez de tomarlo. Corregido: el owner
  referencia ahora el PID del proceso `opencode` persistente (4535), no el de un subshell.
- **`030-page-walker` necesita rehacerse por su cuenta**: su conclusion de que
  `AMDGPU_VM_PTE_COUNT = 1 << block_size` fija el ancho del indice de PTE **sigue siendo
  valida** como estructura; lo que cambia es el numero. Con `block_size = 10` el indice de
  PTE es de 10 bits, no de 22, y eso cambia la cuenta de entradas por PTB y por tanto la
  conclusion sobre "4 Mi entradas por PTB". No lo edito — es scope ajeno — pero queda
  registrado que su geometria numerica necesita rehacerse con 10.

## 7 · Criterio de falsificacion

Los cuatro puntos de falsificacion **los he comprobado, y ninguno se activa**:

**(a) Modulo con `vm_block_size` distinto de `-1`.** Leido:

```
$ for m in vm_size vm_block_size vm_fragment_size vm_update_mode; \
      do printf "  %-18s %s\n" "$m" "$(cat /sys/module/amdgpu/parameters/$m)"; done
  vm_size            -1
  vm_block_size      -1
  vm_fragment_size   -1
  vm_update_mode     -1
```

Los cuatro en `-1`, luego el camino del modulo **no** se toma y `block_size` viene
efectivamente de `get_block_size(tmp)`. Ademas hay una comprobacion cruzada que no
necesite el modulo: si `amdgpu_vm_block_size != -1`, el bloque haria el
`tmp >>= amdgpu_vm_block_size - 9` **antes** del reasignamiento, y con un
`amdgpu_vm_block_size >= 9` eso daria un `tmp` distinto. El log da 10, que es
exactamente el camino sin el `>>=`. El log y el codigo coinciden por construccion.

**(b) El `dev_info` imprime antes de que `adjust_size` termine.** No: esta en
`amdgpu_vm.c:2462`, **despues** del `switch` de `root_level`, **despues** de la asignacion de
`block_size` (`:2454`) y **despues** de la de `fragment_size` (`:2457`). Es la ultima
sentencia con efectos de la funcion. Refutado.

**(c) El log es de otro kernel.** `uname -r` = `7.1.3-200.nobara.fc44.x86_64`, que es el
del proyecto y el del log. Refutado.

**(d) `AMDGPU_VM_PDB0` podria significar "directorio presente".** No. El enum es:

```c
/* amdgpu_vm.h:191-196 */
enum amdgpu_vm_level {
        AMDGPU_VM_PDB3,      /* 0 */
        AMDGPU_VM_PDB2,      /* 1 */
        AMDGPU_VM_PDB1,      /* 2 */
        AMDGPU_VM_PDB0,      /* 3 */
        AMDGPU_VM_PTB        /* 4 */
};
```

`PDB0` es la base: **el indice 0 significa que no hay directorio, la raiz es la propia tabla
de PTB.** `num_level = 1` selecciona `root_level = AMDGPU_VM_PDB0`, y el unico nivel
recorrido es el PTB. El "2 levels" del log es `num_level + 1` contando PDB0 y PTB. Refutado.

**Conclusion del criterio de falsificacion: la lectura se sostiene en los cuatro puntos.**
El unico que queda abierto es de hardware puro —que el hardware aceptase
`PAGE_TABLE_BLOCK_SIZE = 4` si alguien escribiera el valor de mi `024`— y no es
desfalsificable sin tocar la GPU.

## 8 · Evidencia

```
CODIGO:
  gmc_v8_0.c:1127          amdgpu_vm_adjust_size(adev, 64, 9, 1, 40)
  amdgpu_vm.c:2356-2367    get_block_size(vm_size)  <-- nombre del parametro
  amdgpu_vm.c:2428         tmp = roundup_pow_of_two(max_pfn)      -> 2^24
  amdgpu_vm.c:2429-2430    if (amdgpu_vm_block_size != -1) ...     -> se salta
  amdgpu_vm.c:2431         tmp = DIV_ROUND_UP(fls64(tmp)-1,9)-1   -> 2   <<< AQUI
  amdgpu_vm.c:2432         num_level = min_t(..., max_level, tmp) -> 1
  amdgpu_vm.c:2450-2454    num_level>1 ? 9 : get_block_size(tmp)  -> 10
  amdgpu_vm.c:2462-2463    dev_info con num_level+1
  gmc_v8_0.c:933-934       REG_SET_FIELD(..., PAGE_TABLE_BLOCK_SIZE, block_size - 9)
  gmc_8_2_sh_mask.h:6543   PAGE_TABLE_BLOCK_SIZE__MASK 0xf000000 __SHIFT 0x18

RUNTIME (LECTURA):
  journalctl -k -b | grep "vm size is"
    "vm size is 64 GB, 2 levels, block size is 10-bit, fragment size is 9-bit"

CALCULO (independiente, reimplementado en python):
  get_block_size(2^24) = 22   <- el claim del page-walker, reproducible
  get_block_size(2)    = 10   <- el valor real, reproducible
```

`WRITE_EXECUTION=NONE`. Ninguna escritura a la GPU, ningun MMIO de escritura.
`GPU INTACTA`.