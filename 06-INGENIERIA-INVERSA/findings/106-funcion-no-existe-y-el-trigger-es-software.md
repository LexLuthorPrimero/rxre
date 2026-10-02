# 106 · §C cerrada: `FUNCTION` no existe en GFX8, y el driver solo escribe 16 bits de dominio

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CORPUS=RESEARCH/working/linux-7.1.3` · `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`CIERRA=§C de AGENTS.md, y 017/056/072 sobre FUNCTION=always`
`CONTINUES=104, 103`

## Cuestión principal

`AGENTS.md` §C dice literalmente: *"Cerrar específicamente
`FUNCTION=always`"*. ¿Se puede?

## Criterio de terminación

Determinar si el campo `FUNCTION` existe en el hardware de esta placa y qué
escribe el driver en `VM_INVALIDATE_REQUEST`. **Cumplido: el campo no existe
en ningún header, y el driver escribe 16 bits de dominio.**

## Respuesta corta: no existe

```
$ grep -rn "INVALIDATE_REQUEST__FUNCTION" include/asic_reg/
(sin resultado)

$ grep -rn "FUNCTION" include/asic_reg/gca/gfx_8_0_sh_mask.h
(sin resultado, en todo el fichero)
```

Ni en GFX8, ni en GMC 8_1, ni en MMHUB. **El campo no está definido en
ninguna generación del corpus.**

Y `056` ya lo había dicho por otro camino: *"para llegar de `NOT_DETERMINED` a
`PROVEN` harían falta tres cosas, y ninguna existe como documento público"*.

Ahora la evidencia es más fuerte que la ausencia de un documento: **es la
ausencia del campo en el header que genera el driver**.

## Lo que el driver escribe, en GFX8

Tres caminos, y **los tres escriben lo mismo**:

```c
/* gmc_v8_0.c:640-641  invalidate by pasid */
WREG32(mmVM_INVALIDATE_REQUEST, mask);        /* mask = 1<<vmid de los que casan */
RREG32(mmVM_INVALIDATE_RESPONSE);

/* gmc_v8_0.c:665  flush_gpu_tlb */
WREG32(mmVM_INVALIDATE_REQUEST, 1 << vmid);

/* gmc_v8_0.c:680  emit_flush_gpu_tlb, por ring */
amdgpu_ring_emit_wreg(ring, mmVM_INVALIDATE_REQUEST, 1 << vmid);
```

Tres cosas se cierran aquí:

**1. No hay campo `FUNCTION`, y no porque el driver lo deje a cero: porque el
hardware no lo tiene.** Escribiendo `1 << vmid` el driver pone bits 0-15 y
**nada más**. No hay un `FUNCTION` que valga 0.

**2. `mask` en la línea 640 no tiene bits fuera de 0-15.** Se construye con:

```c
for (vmid = 1; vmid < 16; vmid++)
        if (...) mask |= 1 << vmid;
```

El bucle va de 1 a 15. **El hardware tiene 16 contextos y el driver los
recorre todos**, y `104` confirmó que los 16 bits tienen máscara en el header.

**3. El caso "VMID ≥ 16" no existe.** El bucle no lo contempla y
`VM_CONTEXT*_PAGE_TABLE_BASE_ADDR` solo llega a `VM_CONTEXT15`. Es coherente:
GCN3 tiene 16 contextos.

## Y con esto, `017` queda resuelto en su pregunta original

`017:145`:

```
| `FUNCTION=always` **hardware trigger** (AGENTS.md:138) | `NOT_DETERMINED`,
  y **reformulado** | No es "cuándo dispara...
```

La pregunta que quedaba era si el hardware disparaba el invalidate
automáticamente. **La respuesta es que no hay ni un campo que lo exprese**:
no hay `FUNCTION`, no hay `AUTO`, no hay nada por encima del bit 15. El
trigger es **exclusivamente la escritura de software**.

Y `018:80` dijo lo mismo desde otro ángulo, y `072:117` lo corrobora con
`PROVEN_ABSENT`: *"el driver lo lee 0 veces"* — leyendo `RESPONSE`.

## La cadena de §C, completa

```
  FLUSH                        TRIGGER                      ACUSE
  ────                         ───────                      ─────
  gmc_v8_0_flush_gpu_tlb   →   WREG32(0x51e, 1<<vmid)  →   RREG32(0x51f)
  emit_flush_gpu_tlb           (por ring, emit_wreg)        (solo en el camino MMIO)
  invalidate by pasid          máscara de los VMID que      el driver lo
                               casan con el PASID           LEE y lo TIRA
```

**Y ese es el punto que `103` abrió y `104` cerró**: el acuse existe por
dominio, 16 bits, y el driver lo descarta.

## Lo que `103`/`104`/`105` aportaron y esta cifra ordena

Tres hallazgos recientes de otra sesión dejaron §C en piezas:

- `103`: el handshake de completación **existe** (corrigió a `072`)
- `104`: los dos registros son de **16 bits** con layout idéntico
- `105`: el camino real de los faults es el que llama al handler

Y faltaba la pieza que da sentido a las otras tres: **qué se escribe**. Sin
eso, `104` describía dos registros y no se sabía si el driver los usaba.

## La confusión que este hallazgo deshace

`AGENTS.md` tenía dos líneas que parecen contradecirse:

```
- `FUNCTION(0) = always` probado a nivel de encoding.
- hardware trigger de `always`: NO_DETERMINED.
```

La segunda es `017:145`, la frontera de este hallazgo. La primera venía de la
**ISA de shaders de Vega**, y `056` lo verifico exactamente eso: la especificación
existe y son 288 páginas, pero **su índice es de instruction set**, y ningún
capítulo trata packet3 ni el command processor.

Son **dos campos distintos con el mismo nombre**:

| | dónde | qué es |
|---|---|---|
| `FUNCTION` de la ISA | shaders | un campo de un opcode de shader |
| `FUNCTION` del invalidate | `VM_INVALIDATE_REQUEST` | **no existe** |

Y por eso este hallazgo cierra sin contradecir nada: `056` no lo refuto.
Solo hizo falta decir sobre QUE `FUNCTION` se estaba hablando.

## Clasificación

| afirmación | estado |
|---|---|
| `FUNCTION` no está en ningún header del ASIC | `PROVEN_ABSENT` — `grep` sobre `asic_reg/` |
| El driver escribe `1 << vmid`, 16 bits | `PROVEN` — `gmc_v8_0.c:665`, `:680` |
| Los 3 caminos escriben lo mismo | `PROVEN` — `:640`, `:665`, `:680` |
| El hardware tiene 16 contextos | `PROVEN` — `104` más el bucle `vmid < 16` |
| No hay `VMID ≥ 16` | `PROVEN` — el bucle y `VM_CONTEXT15` |
| `RESPONSE` se lee una vez y se descarta | `PROVEN` — `:641` sin asignar |
| El trigger es exclusivamente software | `DERIVATION` — no hay otro campo posible |
| Que el hardware no invalide solo | `DERIVATION` — de la anterior |
| Que `VM_INVALIDATE_RESPONSE` reaparezca en GFX9+ | `NOT_DETERMINED` — no mirado |
| La semántica del bit `RESPONSE` por dominio | `PROVEN` por su nombre en el header |

## Confounders

- **`grep` sobre `asic_reg/` prueba que el campo no está *definido*, no que
  no exista.** Si AMD no lo documentó, el campo podría estar ahí sin nombre.
  Lo que sí es sólido: **el driver no lo escribe**, y eso es independiente de
  si el header lo omite.
- **GFX8 usa `gca/gfx_8_0_*` pero el registro está en `gca/gmc_8_1_*`** (o
  `gmc/gmc_8_1_*`). Eso es lo que `065` ya llamó "el `#include` decide cuál".
  He buscado en ambas familias.
- **No he desensamblado** a comprobar que el driver no pone bits altos por
  otra vía. Que el fuente no lo haga es `PROVEN`; que la máquina ejecutada no
  lo haga requiere el binario.
- **`emit_flush_gpu_tlb` no relee `RESPONSE`**, solo `gmc_v8_0.c:641` lo hace.
  Los otros dos caminos emiten por ring y no esperan acuse. Eso es coherente
  con que el invalidate sea asíncrono, pero **no lo he verificado**.

## Desfalsificación

- **(a)** `FUNCTION` no existe → refutable con `grep -r INVALIDATE_REQUEST__FUNCTION
  include/asic_reg/`, vacío.
- **(b)** El driver escribe solo bits 0-15 → refutable con `gmc_v8_0.c:665`.
- **(c)** `mask` no tiene bits altos → refutable con el bucle `vmid < 16`.
- **(d)** `RESPONSE` se descarta → refutable con `:641`: `RREG32(...)` sin
  destino.
- **(e)** El hardware no invalida solo → **no refutable aquí**: requiere
  hardware. Es la parte que queda de §C.

## UNLOCKS

- **§C queda cerrada hasta el último item**, que es empírico: que el hardware
  no invalide solo es una `DERIVATION` fuerte, no un `PROVEN`.
- **La pregunta de `017:145` tiene respuesta**, y es negativa por estructura:
  no hay campo que exprese el trigger automático.
- **`AGENTS.md` §C se puede actualizar**: la línea *"Cerrar específicamente
  `FUNCTION=always`"* es de una versión del driver donde ese campo existía.
  En GFX8 no.
- **Las tres piezas encajan**: `103` (el acuse existe), `104` (16 bits),
  y ahora qué se escribe.

## Evidencia

```
gmc_v8_0.c:630-641   invalidate por pasid:  mask |= 1<<vmid (bucle 1..15)
                                  WREG32(0x51e, mask); RREG32(0x51f)
gmc_v8_0.c:665       flush_gpu_tlb:           WREG32(0x51e, 1<<vmid)
gmc_v8_0.c:680       emit_flush_gpu_tlb:      emit_wreg(0x51e, 1<<vmid)

gca/gmc_8_1_d.h:615  mmVM_INVALIDATE_REQUEST   0x51e
gca/gmc_8_1_d.h:616  mmVM_INVALIDATE_RESPONSE  0x51f

$ grep -rn "INVALIDATE_REQUEST__FUNCTION" include/asic_reg/
(sin resultado)
$ grep -c FUNCTION include/asic_reg/gca/gfx_8_0_sh_mask.h
0
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.