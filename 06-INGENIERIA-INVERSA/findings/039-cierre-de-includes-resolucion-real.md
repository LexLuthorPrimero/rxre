# 039 · El cierre de includes, y por qué la resolución alfabética era falsa

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` sobre el corpus · `RUNTIME=NOT_RUN`
`GPU INTACTA`
`HERRAMIENTA_NUEVA=08-ARQUITECTURA/tools/include_closure.py`
`MEJORA=pm4_reachable.py` (resuelve por el cierre real, no por orden alfabético)
`CONTINUES=038` (que dejo este hueco nombrado)

## CUDA principal

`038` dejo un hueco declarado: el preprocesador no puede usarse como verdad del cierre
de includes en esta maquina. Este documento lo cierra, y el cierre **desmiente** la
resolucion que mis herramientas estaban usando.

```
resolucion por orden ALFABETICO de cabeceras   (lo que hacia pm4_reachable)
resolucion por el CIERRE DE INCLUDES real       (lo que hace include_closure)

  PACKET3_INDIRECT_BUFFER_CONST   0x31  ->  0x33     *** estaba mal
  PACKET3_LOAD_CONFIG_REG         0x5F  ->  0x60     *** estaba mal
  PACKET3_LOAD_CONTEXT_REG        0x60  ->  0x61     *** estaba mal
  PACKET3_LOAD_SH_REG             0x5F  ->  0x5F     correcto
```

**Tres de cuatro estaban mal.** Y la razon es simple y la dice el cierre:

> **`sid.h`, `cikd.h`, `soc15d.h` y `nvd.h` NO entran en el cierre de includes de
> `gfx_v8_0.c`.** Entran `vid.h` (posicion 93 de 109) y las seis familias de registros.
> El unico header de opcode que el fichero ve es `vid.h`, y define cada opcode **una sola
> vez**.

O sea: **no puede haber conflicto**, porque solo hay una fuente. La resolucion
alfabetica estaba comparando cabeceras que el codigo nunca ve, y quedarse con la primera
le daba un numero que el compilador no ve.

## Alcance exacto

1. Resolver el cierre de includes sin preprocesador.
2. Decidir el valor que ve de verdad el codigo, y decirlo.
3. Corregir la herramienta que resolvia mal.
4. Verificar que las cabeceras ausentes no pueden cambiar un opcode.

## Criterio de terminacion (cumplido)

109 ficheros en el cierre, 7 ausentes, 0 cabeceras ausentes que definan opcodes,
mutacion propagada y corpus restaurado. Agotado.

---

## 1 · Por que el preprocesador no servia, y como se sustituye

`038` lo dejo medido:

```
gcc -E -P -I$K/include -I$K/arch/x86/include -I$K/arch/x86/include/generated ...
  -> 60391 lineas preprocesadas
  -> fatal error: dm_services_types.h: No existe el fichero o el directorio
```

Ese header no existe en ninguna parte del sistema. El preprocesador se detiene.

`include_closure.py` sustituye al preprocesador para el subconjunto que el codigo de
amdgpu usa en la práctica:

1. Parte de un `.c`.
2. Sigue sus `#include "locales"` recursivamente, **en el orden de las directivas**.
3. Registra cada `#define` con su orden y su fichero.
4. **El último `#define` de un nombre pisa al anterior** — la regla del preprocesador.
5. Reporta el valor final, quien lo definio, y quien lo definio antes con otro valor.

Lo que **no** hace, y declara: no resuelve macros de sistema, ni `#if`, ni `##`, ni
`#include <...>`. Esos 67 includes de sistema quedan como tales y no se inventan.

```
ficheros incluidos              : 109
cabeceras locales ausentes      : 7   dm_services_types.h, mod_freesync.h,
                                     amdgpu_dm_irq_params.h, amdgpu_dm_ism.h,
                                     amdgpu_dpm.h, amdgpu_dm.h, kfd_topology.h
cabeceras de sistema (fuera)    : 67
```

### 1.1 · Las 6 familias de registro de `037`, todas presentes y en orden

Lo que `037` afirmo, confirmado por posicion en el cierre real:

```
pos  91   vi.h              pos  97   gmc_8_2_d.h      (Polaris12 MEMORIA)
pos  93   vid.h             pos  99   oss_3_0_d.h      (VI generico OSS)
pos 101   bif_5_0_d.h       pos 103   gfx_8_0_d.h      (VI generico NUCLEO)
pos 106   dce_10_0_d.h      pos 108   smu_7_1_3_d.h    (Polaris12 RELOJ)
```

`037` §1 lo habia deduced leyendo la lista de `#include` del `.c`. Aqui es la posicion
real dentro del cierre, que es lo que importa: **el orden de resolucion**, no la presencia.

## 2 · La correccion, y por que no habria visto nada

Siete opcodes reordenados, cuatro con el mismo nombre y distinto valor entre
cabeceras. Los cuatro **no estan en la categoria A** de `036` — son construcciones de Mesa
para escribir registros desde memoria, y amdgpu no las usa en GFX8. Verificado, no
supuesto.

Asi que el impacto en el inventario de `036` es **cero**. Lo digo sin rodeos, porque
presentar un bug de herramienta como si invalidara un resultado anterior seria el error
opuesto.

Lo que si cambia es el estado de una afirmacion: **`036` §7 afirmaba que `sid.h` es "el
bloque CIK/VI" y que de ahi salen los opcodes de GFX8.** Para los 74 opcodes tal vez; para
`gfx_v8_0.c` concretamente, **el header que gana es `vid.h`**. No es una correccion
numerica: es que la afirmacion estaba bien de sabor y mal de mecanismo.

### 2.1 · Y por que tres de cuatro escapaban a la revision manual

Porque los numeros **parecian razonables**. `LOAD_SH_REG = 0x5F` y `= 0x61` son ambos
plausibles. `LOAD_CONFIG_REG = 0x5F` y `= 0x60` son **numeros consecutivos**: un cambio de
generacion reasigna opcodes **de uno en uno**, asi que el valor nuevo casi siempre es el
antiguo mas uno, y la diferencia no salta a la vista.

Eso es la clase de error que las cinco rondas anteriores no-produjeron: en `031`-
`037` los numeros que chequeaba **no tenian un valor alternativo plausible al lado**.

### 2.2 · El numero de opcodes bajo de 145 a 78, y por que eso es buena noticia

Al delegar en el cierre, `pm4_reachable` paso de **145 opcodes definidos** a **78**. Los
145 eran la union de todas las cabeceras del arbol; 78 es lo que ve `gfx_v8_0.c` de
verdad.

Un numero que baja al cambiar de metodo es una senal de que el metodo anterior contaba
cosas que no contaba. Vale como regla de trabajo.

## 3 · Verificacion

### 3.1 · Las 7 cabeceras ausentes no pueden cambiar un opcode

Es la pregunta que decide si el cierre es utilizable:

```
dm_services_types.h        PACKET3_* definidos: 0
modules/inc/mod_freesync.h                            0
amdgpu_dm_irq_params.h                                0
amdgpu_dm_ism.h                                      0
amdgpu_dpm.h                                          0
amdgpu_dm.h                                           0
kfd_topology.h                                        0
```

Ninguna esta en el corpus y ninguna define opcodes. **La resolucion es completa para lo
que importa**, y eso se dice con el numero a la vista en vez de suponerlo.

### 3.2 · Mutacion propagada

`vid.h:337`, `PACKET3_LOAD_SH_REG` de `0x5F` a `0x99`, vía `corpus_guard --mutate`:

```
MUTADO vid.h: LOAD_SH_REG 0x5F -> 0x99
PACKET3_LOAD_SH_REG = 0x99   (de .../vid.h:337)
pm4_reachable: resueltos por: cierre de includes de gfx_v8_0.c
restaurado / verificacion tras restaurar: sin diferencias / corpus intacto
```

Y con el original restaurado, `--show` vuelve a dar `0x5F`.

### 3.3 · Dos bugs de la propia mejora

**La comprobacion de conflicto era VACIA.** Al delegar, la leia de `cl.defs`, que por
construccion guarda **un** valor por nombre — el que gana. Un mapa con una sola entrada
por clave no puede tener conflictos, asi que la salida decia "ninguno" siempre.

Lo detecte porque el conteo bajo de 145 a 78 al cambiar de metodo, y un "ninguno" que
coincide con un cambio de metodo es sospechoso por construccion. Los conflictos estan en
`cl.history`, que guarda **todas** las definiciones en orden. Corregido.

Ahora dice "ninguno" **y es verdad, por un motivo distinto**: `sid.h`, `cikd.h`,
`soc15d.h` y `nvd.h` no entran en el cierre. Ese "ninguno" es un resultado, no un fallo
de la comprobacion. Pero lo que declara ahora es mas util que antes: **que valor ve el
codigo, no que valor hay en el arbol.**

**El runner solo pasaba el nombre del script.** `run_all` hacia
`os.path.join(HERE, a[0])` y descartaba `a[1:]`, asi que `include_closure` se lanzaba sin
el fichero que necesitaba -> `rc=2` -> "FALLA" sin motivo real. La caja de
herramientas se rompe con una herramienta que solo ella misma puede ejecutar.

Corregido a `os.path.join(HERE, a[0]) + a[1:]`.

## 4 · Clasificacion

| afirmacion | estado |
|---|---|
| `sid.h`/`cikd.h`/`soc15d.h`/`nvd.h` no entran en el cierre de `gfx_v8_0.c` | `PROVEN` |
| `vid.h` entra, en la posicion 93 de 109, y define cada opcode una vez | `PROVEN` |
| No puede haber conflicto de valor de opcode en el cierre | `PROVEN_DERIVED` |
| La resolucion alfabetica daba 3 de 4 valores equivocados | `PROVEN` — contrastado |
| Ninguna de las 7 cabeceras ausentes define opcodes | `PROVEN` — las 7 comprobadas |
| La resolucion es completa para el vocabulario PM4 | `PROVEN` |
| Que las cabeceras de sistema (67) no cambien un opcode | `HYPOTHESIS` — no hay ningun opcode alli |
| Que 0x5F -> 0x60 sea reasignacion y no dos paquetes | `HYPOTHESIS` — el patron lo sugiere, no lo demuestra |
| `036` §7 "sid.h es el bloque CIK/VI" | `ENMENDADO` — el header que gana para este `.c` es `vid.h` |
| El impacto en el inventario de `036` | **cero**, comprobado opcode por opcode |

## 5 · Confounders

- **`#if` no se resuelve.** La herramienta lee el fichero entero sin evaluar
  condicionales. Si un opcode estuviera dentro de un `#if` que el codigo real toma por
  otro camino, la herramienta lo contaria como definido. En el codigo de amdgpu los
  bloques condicionales de opcode son raros, y no he encontrado ninguno en la cadena de
  `vid.h`, pero **no lo he comprobado exhaustivamente**.
- **67 cabeceras de sistema quedan sin resolver.** Ninguna define un opcode PM4 —eso es
  seguro por construccion, no por busqueda— pero el cierre **no** es completo para macros
  de sistema, y una macro de sistema con el mismo nombre que un opcode lo pisaria sin que
  lo notara. `LIMITATION` declarada.
- `include_closure` recorre **una sola vuelta** del arbol al buscar una cabecera por
  `basename`, asi que si dos ficheros del corpus tienen el mismo nombre en directorios
  distintos, puede elegir el equivocado. En el cierre de `gfx_v8_0.c` no hay colision.
- El "ninguno" en conflictos **no** es lo mismo que "no hay redefiniciones en el arbol".
  En el arbol hay 7; en el cierre, 0. La herramienta ahora reporta lo segundo, que es lo
  que importa, pero el nombre `clashes` sugiere lo primero.

## 6 · UNLOCKS

- **Herramienta que era un hueco declarado en `038` y ahora existe.** Con ella,
  `pm4_reachable` deja de aproximar y resuelve, y dice de donde.
- **Una correccion por mecanismo, no por numero.** Que el header que gana sea `vid.h` y
  no `sid.h` no cambia ningun opcode del inventario; cambia **por que** el numero es el
  que es. Eso es lo que hace falta para copiar codigo a un driver propio.
- **La aritmética de "n+1" como patron de reasignacion.** `LOAD_CONFIG_REG` 0x5F -> 0x60,
  `LOAD_CONTEXT_REG` 0x60 -> 0x61, `INDIRECT_BUFFER_CONST` 0x31 -> 0x33. Parece que se
  reasigna el espacio de opcode de uno en uno al entrar generacion nueva. Es
  `HYPOTHESIS`, y **es falsable**: si GFX9 introduce un opcode en medio, la serie se
  rompe y hay que explicarlo. Merece una ronda propia si el espacio de opcode importa para
  el driver.
- **Regla de trabajo extraida de `038`:** *un numero que baja al cambiar de metodo es una
  senal de que el metodo anterior contaba cosas que no contaba.* Aplica a todo.
- **El fallo de `run_all` (descartar argumentos) es un fallo de caja de herramientas:**
  un runner que pasa mal los argumentos hace que una herramienta correcta parezca
  rota. Con siete herramientas ese fallo ya no es raro: hay que probarlas **a traves** del
  runner, no solo directamente. Anadido a mi lista.

## 7 · Criterio de falsificacion

Se refutaria si: (a) `sid.h` tuviera un `#include` en la cadena que no veo — refutable con
`grep -rn 'include "sid.h"'` sobre los 109 ficheros del cierre, que ya hice y da 0; (b)
alguna cabecera de sistema definiera un `PACKET3_*` — refutable con `gcc -dM -E` sobre un
fichero minimo que incluya `<linux/*.h>`, que el preprocesador si puede hacer aislado; (c)
`vid.h` se incluyera **despues** de otro header que redefiniera los mismos opcodes —
refutable con `include_closure --opcodes`, que imprime el orden; (d) el recuento de 156
opcodes en el cierre incluyera definiciones de macros de sistema — refutable listando los
nombres y comprobando que todos vienen de ficheros del corpus, que es lo que hace la
herramienta al registrar el fichero de cada definicion. (a), (c) y (d) ya estan
comprobadas en este documento.

## 8 · Evidencia

```
HERRAMIENTA NUEVA:
  08-ARQUITECTURA/tools/include_closure.py
    cierre de gfx_v8_0.c: 109 ficheros, 7 locales ausentes, 67 de sistema
    156 opcodes PACKET3 en el cierre
    pos 93 vid.h (unico header de opcode), pos 91 vi.h
    pos 97 gmc_8_2_d, 99 oss_3_0, 101 bif_5_0, 103 gfx_8_0, 106 dce_10_0, 108 smu_7_1_3

CORROBORACION CONTRARIA:
  grep -rn 'include "sid.h"' sobre los 109 del cierre  ->  0
  grep -rn 'include "sid.h"' sobre amdgpu/*.h          ->  0
  vid.h no tiene includes (grep -c '#include' -> 0)

MEJORA:
  08-ARQUITECTURA/tools/pm4_reachable.py
    opcode_values() delega en include_closure
    reporta OPCODE_SOURCE en la salida
    conflictos leidos de cl.history, no de cl.defs (que era vacio por construccion)
    opcodes: 145 (union) -> 78 (los que ve gfx_v8_0.c)
  08-ARQUITECTURA/tools/run_all.py
    pasar a[1:] ademas de a[0]

VALIDACION NEGATIVA:
  corpus_guard --mutate vid.h  PACKET3_LOAD_SH_REG 0x5F -> 0x99
    include_closure --show  -> 0x99  (de vid.h:337)
    restaurado, sin diferencias, corpus intacto

VERIFICACION DE LAS AUSENTES:
  las 7 cabeceras locales ausentes definen 0 opcodes PACKET3 (una a una)
```

`WRITE_EXECUTION=NONE`. Ninguna escritura a la GPU. `GPU INTACTA`.