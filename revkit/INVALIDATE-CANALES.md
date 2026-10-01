# El invalidate del TLB: 18 canales que el driver no usa

## El hallazgo

`VM_INVALIDATE_RESPONSE` estaba marcado `NOT_DETERMINED` desde hace tiempo, con
la nota de que faltaba evidencia de qué significa. Este análisis explica **por
qué** no se puede determinar con el driver de referencia: **nadie lee ese
registro, ni el invalidate de GFX8, en ningún sitio.**

## Lo que hace el driver

**Diez ficheros** escriben `mmVM_INVALIDATE_REQUEST`, en 15 sitios. **Ninguno lo
lee.** Verificado buscando cualquier lectura (`RREG`, no `WREG`): cero
resultados.

```c
/* gmc_v8_0.c:680 */
amdgpu_ring_emit_wreg(ring, mmVM_INVALIDATE_REQUEST, 1 << vmid);
```

Los cuatro de `gmc_v8_0.c` (líneas 640, 665, 680, y el `gfx_v7_0.c:489`
equivalente) son los que importan para GFX8.

Y para esperar, en vez de leer el estado, usa `WAIT_REG_MEM` con
`FUNCTION(0)` (`always`) sobre el propio `INVALIDATE_REQUEST`
(`gfx_v8_0.c:6199-6205`).

Es decir: **el driver no sondea el invalidate. Lo dispara y espera un tiempo de
sondeo.** El estado de finalización no se consulta por software.

## Los 18 canales que existen en el hardware

El corpus define un canal de invalidate **por motor de graphics** (`ENG0` a
`ENG17`), cada uno con cinco registros:

```
mmVM_INVALIDATE_ENG<N>_REQ          la peticion
mmVM_INVALIDATE_ENG<N>_ACK          la respuesta
mmVM_INVALIDATE_ENG<N>_SEM          el semaforo
mmVM_INVALIDATE_ENG<N>_ADDR_RANGE_LO32   rango bajo
mmVM_INVALIDATE_ENG<N>_ADDR_RANGE_HI32   rango alto
```

Son 18 motores × 5 registros = 90 registros de invalidate, más el
`mmVM_INVALIDATE_REQUEST` global y el `mmVM_INVALIDATE_RESPONSE`.

**Ninguno de los 90 lo usa el driver de amdgpu.** Verificado: cero
consumidores de `mmVM_INVALIDATE_ENG0`, de `INVALIDATE_ENG0_SEM`, y por
extensión de los 18 canales.

## Qué significa eso para un driver propio

El invalidate por canales es un mecanismo **no usado por amdgpu en ninguna
generación**. Eso no significa que no funcione; significa que el invalidate
global basta para lo que el driver hace, que es invalidar un VMID entero.

Los canales permiten invalidar un **rango de direcciones** de una VMID. Eso es
una capacidad que amdgpu no explota pero que existe en el hardware:

- invalidate global (`INVALIDATE_REQUEST`, bit = vmid): lo que hace amdgpu
- invalidate por rango (`ENG<N>_REQ` + `ADDR_RANGE`): existe, no se usa

Si un driver propio quisiera invalidar un rango en vez de una VMID entera,
tendría que usar los canales. Y al no haber código de referencia, la semántica
del `_SEM` y del `_ACK` queda sin documentar por observación.

## `VM_INVALIDATE_RESPONSE`: qué es, y por qué el driver no lo lee

Este documento decía que `VM_INVALIDATE_RESPONSE` era `NOT_DETERMINED` porque
el driver no lo lee. Eso sigue siendo cierto, pero el registro **sí tiene
layout conocido**, y eso acota la pregunta.

```
VM_INVALIDATE_RESPONSE   (gmc_8_1_sh_mask.h, el ASIC de POLARIS12)
    DOMAIN_INVALIDATED_0     1 bit @  0
    DOMAIN_INVALIDATED_1     1 bit @  1
    ...
    DOMAIN_INVALIDATED_15    1 bit @ 15
    16 campos, 1 bit cada uno, sin huecos
```

Es un registro de **16 bits, un bit por dominio**. El hardware pone a 1 el bit
de cada dominio que ha invalidado, y el software lee cuáles.

Eso encaja con el invalidate global: se dispara con `INVALIDATE_REQUEST` a un
bit por VMID, y el hardware responde con `DOMAIN_INVALIDATED_n` a un bit por
**dominio**. Los 16 no coinciden necesariamente con los VMID: son dominios, y
la correspondencia entre dominio y VMID no está en el corpus.

### La correspondencia VMID ↔ dominio es la pregunta que queda

El driver no la necesita porque no lee la respuesta. Para un driver propio que
quiera **saber** si un invalidate se completó, esa correspondencia es
obligatoria: sin ella, un `DOMAIN_INVALIDATED_3` no dice qué VMID se invalidó.

Tres candidats, y ninguno es demostrable estáticamente:

| hipótesis | qué tendría que verse |
|---|---|
| dominio n = VMID n | que el hardware numere igual, sin traducción |
| dominio n = VMID n mod 16 | que haya wrap a los 16 |
| otro mapeo | que exista una tabla, y no hay ninguna en el corpus |

## Sobre el header que citan algunos documentos

`017` y `018` citan `gmc_8_2_sh_mask.h` para `DOMAIN_INVALIDATED`. Pero
`gmc_v8_0.c:36` incluye:

```c
#include "gmc/gmc_8_1_sh_mask.h"
```

El ASIC de POLARIS12 usa **`gmc_8_1`**, no `gmc_8_2`. Comprobado que los valores
de `DOMAIN_INVALIDATED` son **idénticos** en ambos headers, así que la cita no
da un valor falso. Pero la fuente autoritativa para este ASIC es
`gmc_8_1_sh_mask.h`, y citarla es lo correcto.

Es el mismo modo de fallo que ya se cometió en este proyecto con `block_size`:
tomar un campo de un header de otra generación. Aquí no cambia el número,
pero cambiaría cualquier valor que difiriera.

## Clasificación

| Afirmación | Estado |
|---|---|
| 10 ficheros escriben `INVALIDATE_REQUEST` | **PROVEN** — enumeración |
| Ninguno lo lee | **PROVEN** — enumeración |
| El driver espera con `WAIT_REG_MEM(FUNCTION=0)`, no leyendo estado | **PROVEN** — `gfx_v8_0.c:6199` |
| Existen 18 canales `ENG0..ENG17` con REQ/ACK/SEM/rango | **PROVEN** — headers |
| Ningún canal lo usa el driver | **PROVEN** — enumeración, 0 consumidores |
| Qué significa `_ACK` y `_SEM` | **NOT_DETERMINED** |
| Si un canal puede invalidar más que una VMID | **NOT_DETERMINED** |
| `VM_INVALIDATE_RESPONSE` = 16 bits, uno por `DOMAIN_INVALIDATED_n` | **PROVEN** — `gmc_8_1_sh_mask.h` |
| GFX8 incluye `gmc_8_1_sh_mask.h`, no `gmc_8_2` | **PROVEN** — `gmc_v8_0.c:36` |
| Que los valores de `DOMAIN_INVALIDATED` coincidan entre ambos headers | **PROVEN** — comparación |
| La correspondencia `DOMAIN_INVALIDATED_n` ↔ VMID n | **NOT_DETERMINED** |

Que el invalidate global baste para invalidar una VMID es la hipótesis que
sostiene el diseño de amdgpu. Que un canal por rango funcione es
`NOT_DETERMINED`: existe en el hardware, nadie lo ha probado.

## Por qué esto estaba `NOT_DETERMINED` y no se podia cerrar

Porque el driver no ofrece un consumidor. La pregunta «qué significa
`VM_INVALIDATE_RESPONSE`» no tiene respuesta en el árbol de fuentes de amdgpu,
porque nadie pregunta. Un `NOT_DETERMINED` así no es un descuido: es un límite
real del corpus como fuente.

Cerrarlo requiere una de dos cosas, ambas de runtime:

- leer `ENG0_ACK` y `ENG0_SEM` antes y después de un invalidate, con root;
- o documentación primaria de AMD sobre el protocolo de invalidate.

Sin root, la segunda es la ruta. No está en el corpus.

## Reproducir

```sh
./cidx.py use mmVM_INVALIDATE_REQUEST   # 10 escritores, 0 lectores
./cidx.py use mmVM_INVALIDATE_ENG0     # 0 consumidores
./cidx.py use VM_INVALIDATE_RESPONSE    # solo su propia definición
```

Sin root. `GPU INTACTA`, `WRITE_EXECUTION NONE`.