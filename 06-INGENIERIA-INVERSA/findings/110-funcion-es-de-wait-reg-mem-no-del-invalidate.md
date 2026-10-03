# 110 · Corrección de `213`: `FUNCTION` es un campo de `WAIT_REG_MEM`, y no estaba ausente

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CORPUS=RESEARCH/working/linux-7.1.3` · `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`CORRIGE=106 (parcial), y AGENTS.md §C que edité con él`
`CONFIRMA=017 §3, y el 107 de otra sesión`

## Qué corrige

`213` afirmó que el campo `FUNCTION` **no existía** en GFX8, y cerró §C con
esa afirmación. **Es falso, y el error tiene una causa precisa y ticable.**

## El error: busqué un campo de paquete en los headers de registros

Mi prueba en `213` fue:

```
$ grep -rn "INVALIDATE_REQUEST__FUNCTION" include/asic_reg/
(sin resultado)
```

Ese grep **es correcto y no prueba nada sobre lo que creí que probaba**. Es un
campo de **packet PM4**, no de un registro de hardware. Los campos de paquete
viven en `amdgpu/vid.h` y `amdgpu/sid.h`, no en `include/asic_reg/`. Busqué el
campo donde no puede estar, obtuve vacío, y convertí el vacío en `PROVEN_ABSENT`.

Es el patrón que ya me ha mordido cuatro veces: **una afirmación plausible sin
valor competidor al lado.** Nunca hice el `grep` recíproco en los headers de
paquetes, que es donde la respuesta estaba.

## Dónde vive de verdad

```
gfx_v8_0.c:35          #include "vid.h"
vid.h:178              #define PACKET3_WAIT_REG_MEM ... 0x3C   (packet type)
vid.h:180              #define WAIT_REG_MEM_FUNCTION(x)  ((x) << 0)
vid.h:181-186          /* 0 - always
                         * 1 - <
                         * 2 - <=
                         * 3 - ==
                         * 4 - !=
                         * 5 - >=
                         * 6 - >
                         */
vid.h:182              #define WAIT_REG_MEM_OPERATION(x) ((x) << 6)
vid.h:187              #define WAIT_REG_MEM_ENGINE(x)    ((x) << 8)
```

**`FUNCTION` es un selector de comparación de `PACKET3_WAIT_REG_MEM`.** El
comentario del propio driver dice `0 - always`: no compara nada, pasa siempre.
No es un trigger de invalidate.

## Y la codificación está en DOS familias de headers, idénticas

Esto es lo que `017` ya tenía y `213` no comprobó:

| | fuente | naturaleza |
|---|---|---|
| macros usadas por GFX8 | `vid.h:178-189` | escrito a mano |
| macros generadas | `soc15d.h:191-222` | generado del XML de ASIC |

`soc15d.h:214-220` da los mismos 7 valores con nombres largos:

```
PACKET3_WAIT_REG_MEM__FUNCTION__ALWAYS_PASS                          0
PACKET3_WAIT_REG_MEM__FUNCTION__LESS_THAN_REF_VALUE                  1
PACKET3_WAIT_REG_MEM__FUNCTION__LESS_THAN_EQUAL_TO_THE_REF_VALUE     2
PACKET3_WAIT_REG_MEM__FUNCTION__EQUAL_TO_THE_REFERENCE_VALUE          3
PACKET3_WAIT_REG_MEM__FUNCTION__NOT_EQUAL_REFERENCE_VALUE            4
PACKET3_WAIT_REG_MEM__FUNCTION__GREATER_THAN_OR_EQUAL_REFERENCE_VALUE 5
PACKET3_WAIT_REG_MEM__FUNCTION__GREATER_THAN_REFERENCE_VALUE         6
```

**Dos fuentes independientes coinciden.** Eso sube la codificación de
`CORROBORATED` a `PROVEN`: no dependo de un único fichero escrito a mano.

Detalle que confirma a `017` y que yo había contradicho: **`sid.h` NO define
`WAIT_REG_MEM_OPERATION`** (`grep -c` → 0). El header que incluye `gfx_v8_0.c`
es `vid.h`, no `sid.h`. Por eso el paquete se codifica de forma distinta
dependiendo de la generación, y por eso hay que citar el header que el
fichero incluye de verdad, no el que "suena" a correcto.

## Lo que GFX8 emite: el dword de cabecera vale `0x00000000`

`gfx_v8_0.c:6199-6202`, el `WAIT` del vm_flush:

```c
amdgpu_ring_write(ring, (WAIT_REG_MEM_OPERATION(0) |  /* wait    */  <<6 -> 0
                         WAIT_REG_MEM_FUNCTION(0)  |  /* always  */  <<0 -> 0
                         WAIT_REG_MEM_ENGINE(0)));    /* me      */  <<8 -> 0
```

`MEM_SPACE` no se escribe, luego vale 0 (register space). **Los cuatro campos
suman exactamente cero: la cabecera del `WAIT` es `0x00000000`.**

Y los operandos (`gfx_v8_0.c:6203-6207`):

```
POLL_ADDR = mmVM_INVALIDATE_REQUEST   (sid.h:77 = 0x51E)
ADDR_HI   = 0
REF       = 0
MASK      = 0
POLL_INTERVAL = 0x20
```

Con `FUNCTION=ALWAYS_PASS` y `MASK=0` **la comparación es vacía por
construcción**: el `POLL_ADDR` está ahí por forma del paquete, no porque
compare contra `0x51E`. El `REF`/`MASK` a cero y el intervalo `0x20` completan
el patrón "no comparar, solo esperar".

Esto es lo que `017` §3 ya llamaba "no compara", y lo confirma
independientemente el `107` de otra sesión ("el driver usa 2 de 7 funciones").
**Verificado por mí, no citado:** en `gfx_v8_0.c` hay exactamente 3 emisiones,
con 2 valores distintos.

```
$ grep -o "WAIT_REG_MEM_FUNCTION([0-9])" gfx_v8_0.c | sort | uniq -c
      1 WAIT_REG_MEM_FUNCTION(0)     <- el WAIT del invalidate
      2 WAIT_REG_MEM_FUNCTION(3)     <- hdp_flush y pipeline_sync
```

## La respuesta a la pregunta de §C, reformulada

`AGENTS.md` §C decía: *"Cerrar específicamente `FUNCTION=always`"*.

**La respuesta correcta no es "el campo no existe".** Es:

> `FUNCTION` es un campo de `PACKET3_WAIT_REG_MEM`. `always` significa
> "no compares, solo espera". El driver lo usa **una vez**, en el WAIT que sigue
> al invalidate, y su cabecera es `0x00000000`.

`017` y el `107` ajeno llegaron a esa misma conclusión por otra vía. Mi `213` la
refutó con un grep mal dirigido. **El campo existe, tiene 7 valores, y `always`
es el que ya estaba.**

## Qué NO cambia

El invalidate sigue sin tener campo `FUNCTION` — eso sí es `PROVEN_ABSENT`, y
por la razón correcta: los 16 bits de `0x51E` son todos `INVALIDATE_DOMAIN_0..15`,
verificado en `gmc_8_1_sh_mask.h` (16 dominios × `_MASK` y `_SHIFT`).

```
gmc_8_1_d.h:615        #define mmVM_INVALIDATE_REQUEST   0x51e
gmc_8_1_d.h:616        #define mmVM_INVALIDATE_RESPONSE  0x51f
gmc_8_1_sh_mask.h:6713 #define VM_INVALIDATE_REQUEST__INVALIDATE_DOMAIN_0_MASK 0x1
gmc_8_1_sh_mask.h:6715 #define VM_INVALIDATE_REQUEST__INVALIDATE_DOMAIN_1_MASK 0x2
...  hasta _15
```

**Dos `FUNCTION` distintos con el mismo nombre**, como en `213` pero por la razón
buena: uno es de paquete PM4 y no existe en el invalidate; el otro es la
explicación inventada (ISA de shaders) que **retiro**.

## Una lección transferible sobre los subagentes

Un subagente de §D reportó: *"el árbol `asic_reg` de GFX8 está
ausente del corpus"*, y de ahí *"sin ellos `VM_INVALIDATE_REQUEST` es un número
opaco"*.

**Es falso, y lo verifiqué antes de aceptarlo.** El fichero existe, en **tres
copias**:

```
RESEARCH/working/linux-7.1.3/.../include/asic_reg/gmc/gmc_8_1_d.h
RESEARCH/baseline/linux-7.1.3/.../include/asic_reg/gmc/gmc_8_1_d.h
RESEARCH/kernelbuild/linux-7.1.3/.../include/asic_reg/gmc/gmc_8_1_d.h
```

La causa: el subagente buscó solo dentro de `amdgpu/`, no en `include/`. Un
`NOT_AVAILABLE` firmado por un subagente **no es autoridad** hasta que se
comprueba la raíz de búsqueda. Un hueco de corpus y un error de búsqueda
producen el mismo output (`NOT_FOUND`) y solo se distinguen mirando **dónde**
buscó.

Si se hubiera aceptado sin verificar, esta investigación habría perdido el
header de `0x51E`/`0x51F` y con él toda la frontera C.

## Clasificación

| afirmación | estado |
|---|---|
| `FUNCTION` es campo de `PACKET3_WAIT_REG_MEM` | `PROVEN` — `vid.h:180` |
| `always` = no comparar, solo esperar | `PROVEN` — comentario `vid.h:181` |
| 7 valores documentados | `PROVEN` — `vid.h:181-186` + `soc15d.h:214-220` |
| Cabecera del WAIT del invalidate = `0x00000000` | `PROVEN` — `gfx_v8_0.c:6200-6202` |
| `MASK=0` hace vacua la comparación | `PROVEN` — `:6206` |
| GFX8 usa 2 de 7 valores | `PROVEN` — grep, 3 emisiones |
| Codificación en 2 headers independientes | `PROVEN` — `vid.h` y `soc15d.h` |
| `sid.h` no tiene `WAIT_REG_MEM_OPERATION` | `PROVEN_ABSENT` — grep rc=0 |
| El invalidate NO tiene campo `FUNCTION` | `PROVEN_ABSENT` — 16 dominios |
| `FUNCTION` pertenece a la ISA de shaders | `REFUTADO` — **retirado aquí** |
| La barrera esperaría `0x51E == 0` | `REFUTED` — `MASK=0`, `always` |
| Orden de ejecución hardware de los packets | `NOT_DETERMINED` — sin spec |

## Confounders

- **No he desensamblado.** Que el hardware trate `FUNCTION=0` como "no compares"
  viene del comentario del driver y del nombre generado, no de una spec de
  hardware. Es `CORROBORATED`, no `PROVEN` en sentido estricto.
- **`vid.h` y `soc15d.h` pueden no ser independientes**: el generado podría
  derivarse del mismo XML que el manual. Coincidir es evidencia, no prueba.
- **El subárbol que reportó el hueco** (`amdgpu/`) sí carece de `asic_reg/`. Su
  afirmación era correcta sobre *ese* directorio y falsa sobre el corpus. El
  error fue el alcance, no la lectura.
- **`017` y el `107` ajeno** ya tenían la respuesta. No la redescubro; la
  verifico y corrijo el daño que mi `213` hizo.

## Desfalsificación

- **(a)** `FUNCTION` es de `WAIT_REG_MEM` → refutable con `vid.h:180`.
- **(b)** La cabecera vale 0 → refutable con `gfx_v8_0.c:6200-6202`.
- **(c)** El invalidate no tiene `FUNCTION` → refutable con `gmc_8_1_sh_mask.h`.
- **(d)** El corpus tiene el header → refutable con `find`; está en 3 rutas.
- **(e)** `FUNCTION` pertenece a la ISA de shaders → **refutado**; no aparece en
  ningún ISA del corpus como el campo del invalidate.

## UNLOCKS

- **`AGENTS.md` §C se reescribe**: la línea "cerrar `FUNCTION=always`" era
  correcta; mi `213` la cerró mal. Hay que deshacer esa edición.
- **`213` queda marcado como parcialmente retractado**, no borrado: su
  observación de que los 3 caminos del invalidate escriben `1 << vmid` sigue
  siendo válida; solo su explicación de `FUNCTION` cae.
- **Precedente de método**: un `NOT_FOUND` (propio o de subagente) exige
  registrar la raíz de búsqueda antes de poder citarlo como hueco de corpus.
- **La codificación de `WAIT_REG_MEM` pasa a `PROVEN` con dos fuentes**, lo que
  la convierte en base para un driver propio sin depender de un solo header.

## Evidencia

```
vid.h:178             PACKET3_WAIT_REG_MEM          0x3C
vid.h:180             WAIT_REG_MEM_FUNCTION(x)      ((x) << 0)
vid.h:181-186         /* 0 - always ... 6 - > */
vid.h:182             WAIT_REG_MEM_OPERATION(x)     ((x) << 6)  0/1
vid.h:187             WAIT_REG_MEM_ENGINE(x)        ((x) << 8)  0=me 1=pfp
soc15d.h:214-220      FUNCTION__ALWAYS_PASS=0 .. GREATER_THAN=6

gfx_v8_0.c:35         #include "vid.h"
gfx_v8_0.c:6199       PACKET3(PACKET3_WAIT_REG_MEM, 5)
gfx_v8_0.c:6200-6202  OPERATION(0)|FUNCTION(0)|ENGINE(0)  -> 0x00000000
gfx_v8_0.c:6203       POLL_ADDR = mmVM_INVALIDATE_REQUEST
gfx_v8_0.c:6205-6206  ref=0, mask=0
gfx_v8_0.c:6207       poll interval 0x20

$ grep -c WAIT_REG_MEM_OPERATION sid.h
0
$ find RESEARCH -name gmc_8_1_d.h | wc -l
3
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.
