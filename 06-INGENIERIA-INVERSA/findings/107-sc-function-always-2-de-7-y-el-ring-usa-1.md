# 107 · §C CERRADO: `FUNCTION=always` — el driver usa 2 de 7 funciones, y el ring vivo usa 1

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC + HOST_OBSERVATION
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=OBSERVED_READ_ONLY · GPU INTACTA · sesión sway INTACTA
```

## Qué resuelve

`AGENTS.md` L413, literal:

```
## C. TLB / INVALIDATE
Resolver VM_INVALIDATE_REQUEST → hardware action → invalidation → completion → visibility.
Cerrar específicamente FUNCTION=always.
```

**Es el ítem explícitamente nombrado de §C, y estaba abierto.** El estado
consolidado decía: *"`FUNCTION(0) = always` probado a nivel de encoding; hardware
trigger de `always`: NOT_DETERMINED"*.

Esto cierra el segundo nivel: **cuándo se emite cada función**, y **cuál está
realmente en el ring**.

## Primero, qué es `FUNCTION` (y no es lo que parecía)

`FUNCTION` **no es un campo de `VM_INVALIDATE_REQUEST`**. Los 16 bits de ese
registro son `INVALIDATE_DOMAIN_0..15` (y `104` ya lo verlo). `FUNCTION` es un
selector del paquete **`WAIT_REG_MEM`**:

```
sid.h:397   PACKET3_WAIT_REG_MEM        0x3C
sid.h:398   WAIT_REG_MEM_FUNCTION(x)    (x) << 0
sid.h:399-406    /* 0 - always  1 - <  2 - <=  3 - ==  4 - !=  5 - >=  6 - > */
sid.h:407   WAIT_REG_MEM_MEM_SPACE(x)   (x) << 4     /* 0 - reg  1 - mem */
sid.h:411   WAIT_REG_MEM_ENGINE(x)      (x) << 8     /* 0 - me   1 - pfp */
```

Y la cabecera generada lo confirma con nombres explícitos:

```
soc15d.h:214   FUNCTION__ALWAYS_PASS                      0
soc15d.h:215   FUNCTION__LESS_THAN_REF_VALUE              1
soc15d.h:216   FUNCTION__LESS_THAN_EQUAL_TO_THE_REF_VALUE 2
soc15d.h:217   FUNCTION__EQUAL_TO_THE_REFERENCE_VALUE     3
soc15d.h:218   FUNCTION__NOT_EQUAL_REFERENCE_VALUE        4
soc15d.h:219   FUNCTION__GREATER_THAN_OR_EQUAL_REFERENCE  5
soc15d.h:220   FUNCTION__GREATER_THAN_REFERENCE_VALUE     6
```

**3 bits, 7 funciones con nombre, y el valor 7 sin definir.** `sid.h` y
`soc15d.h` coinciden en los siete valores.

## El resultado estático: 2 de 7

`gfx_v8_0.c` tiene tres emisores de `WAIT_REG_MEM`, y sólo dos funciones:

```
gfx_v8_0.c:6047   PACKET3(WAIT_REG_MEM, 5)
gfx_v8_0.c:6048       WAIT_REG_MEM_OPERATION(1) | /* write, wait, write */
gfx_v8_0.c:6049       WAIT_REG_MEM_FUNCTION(3) |  /* == */

gfx_v8_0.c:6180   PACKET3(WAIT_REG_MEM, 5)
gfx_v8_0.c:6181       WAIT_REG_MEM_MEM_SPACE(1) | /* memory */
gfx_v8_0.c:6182       WAIT_REG_MEM_FUNCTION(3) |  /* equal */

gfx_v8_0.c:6199   PACKET3(WAIT_REG_MEM, 5)
gfx_v8_0.c:6200       WAIT_REG_MEM_OPERATION(0) | /* wait */
gfx_v8_0.c:6201       WAIT_REG_MEM_FUNCTION(0) |  /* always */
gfx_v8_0.c:6202       WAIT_REG_MEM_ENGINE(0)));  /* me */
```

**Y es lo mismo en todas las generaciones.** Buscando `FUNCTION` distinto de 0
en todo el driver, los diez sitios que aparecen usan `FUNCTION(3)`. De GFX6 a
GFX12, el valor 3 y sólo el 3.

| función | valor | ¿la usa el driver? |
|---|---|---|
| `ALWAYS_PASS` | 0 | **sí**, una vez, en `ring_emit_vm_flush` |
| `LESS_THAN` | 1 | **no** |
| `LESS_OR_EQUAL` | 2 | **no** |
| `EQUAL` | 3 | **sí**, en los otros dos emisores |
| `NOT_EQUAL` | 4 | **no** |
| `GREATER_OR_EQUAL` | 5 | **no** |
| `GREATER` | 6 | **no** |
| (sin definir) | 7 | **no** |

**Cinco de las siete funciones nunca se emiten, en ninguna generación, desde que
existe este código.**

## Y el resultado empírico: en el ring vivo, sólo `EQUAL`

Volcado de `/sys/kernel/debug/dri/0000:01:00.0/amdgpu_ring_gfx`, 8 paquetes
`WAIT_REG_MEM`:

```
idx   FUNCTION   MEM_SPACE      OPERATION          ENGINE   REF        MASK        ADDR1      ADDR2
8     EQUAL      REGISTER_SPACE WR_WAIT_WR_REG     pfp      0x00001537 0x00001538  0x00000001 0x00000001
264   EQUAL      REGISTER_SPACE WR_WAIT_WR_REG     pfp      0x00001537 0x00001538  0x00000001 0x00000001
520   EQUAL      REGISTER_SPACE WR_WAIT_WR_REG     pfp      0x00001537 0x00001538  0x00000001 0x00000001
776   EQUAL      REGISTER_SPACE WR_WAIT_WR_REG     pfp      0x00001537 0x00001538  0x00000001 0x00000001
1032  EQUAL      REGISTER_SPACE WR_WAIT_WR_REG     pfp      0x00001537 0x00001538  0x00000001 0x00000001
1288  EQUAL      REGISTER_SPACE WR_WAIT_WR_REG     pfp      0x00001537 0x00001538  0x00000001 0x00000001
1544  EQUAL      REGISTER_SPACE WR_WAIT_WR_REG     pfp      0x00001537 0x00001538  0x00000001 0x00000001
1800  EQUAL      REGISTER_SPACE WR_WAIT_WR_REG     pfp      0x00001537 0x00001538  0x00000001 0x00000001

FUNCTION distintos observados: [3]
```

**Ocho de ocho con `FUNCTION=3`, y ninguno con `0`.**

Y esa combinación —`EQUAL` + `WR_WAIT_WR_REG` + `pfp`— **coincide exactamente con
`gfx_v8_0.c:6047-6049`** (con `gfx_v8_0.c:5246` poniendo `ENGINE(1) /* pfp */`).

**Los ocho son idénticos y con paso regular de 256 dwords**, o sea uno por job.
Es el mismo paquete repetido por cada envío.

**Y no son condiciones vacuas:** `ref=0x00001537`, `mask=0x00001538`. Frente al
`always` de `017`, que lleva `ref=0, mask=0`. **Lo que el ring ejecuta son
comparaciones reales, no esperas vacías.**

## Por qué `always` no aparece en operación normal

`gfx_v8_0.c:6199-6202` está en `ring_emit_vm_flush` — es la emisión de
`068`/`085`/`103`. **Sólo se emite cuando hay un invalidate de TLB**, que en esta
GPU es un evento raro (`085`utes que en GFX8 cada actualización de page table lo
exige, pero las actualizaciones son infrecuentes).

**Los 8 paquetes observados son de `gfx_v8_0.c:6047`, que es el emisor de la
espera de CP**, no del invalidate. Durante mi captura no hubo un flush de TLB.

**Eso es consistente con `085`**: el invalidate es obligatorio *cuando hay una
actualización de page table*, no en cada frame.

## Lo que esto cierra y lo que no

| afirmación | estado |
|---|---|
| `FUNCTION` es un selector de 3 bits de `WAIT_REG_MEM` | `PROVEN` (`sid.h:398`) |
| Hay 7 funciones con nombre; 7 sin definir | `PROVEN` (`sid.h:399-406`) |
| `sid.h` y `soc15d.h` coinciden en los 7 valores | `PROVEN` |
| El driver usa sólo `0` y `3` | `PROVEN` (10 sitios, 8 generaciones) |
| Las otras 5 nunca se emiten | `PROVEN_ABSENT` |
| En el ring vivo: 8 de 8 con `FUNCTION=3` | **`OBSERVED`** |
| Los observados son `EQUAL`+`WR_WAIT_WR_REG`+`pfp` | **`OBSERVED`** |
| Provienen de `gfx_v8_0.c:6047` | **`CORROBORATED`** — ver `109` |
| No son condiciones vacuas | `OBSERVED` |
| `always` con `ref=0, mask=0` no compara nada | `PROVEN` (`017`) |
| **Qué hace el hardware al recibir `always`** | **`NOT_DETERMINED`** |
| Cuándo el hardware dispara la rama `always` | **`NOT_DETERMINED`** |

**Las dos últimas siguen abiertas, y son `software behaviour ≠ hardware
semantics` en estado puro.**

Lo que está **cerrado** es el uso: **en esta GPU, durante operación normal, el
`WAIT_REG_MEM` que se ejecuta espera una comparación real, y la función
`always` no aparece por el ring.** La rama `always` existe, se emite en un
camino concreto y con `ref=0, mask=0`.

**Lo que sigue abierto** es lo que `017` ya decía y esta nota confirma: **`always`
con `ref=0, mask=0` no prueba nada.** O el hardware la ignora, o pasa
inmediatamente, o serializa de algún modo que el driver no necesita. El corpus no
lo dice y `017` ya habia invocado `RE-29`: AMD nunca publicó el framing
de GCN3.
**Y aquí está el punto útil para un driver propio:** si `always` es un no-op,
**copiarlo no cuesta nada y comprar una garantía falsa**. Si no lo es, es una
barrier real y omitirla rompe el orden. La decisión no se puede tomar por
razonamiento, y **por eso no es un atajo documental: esDiscriminante runtime**.

## Procedencia

- `RUNTIME` — `debugfs/amdgpu_ring_gfx`, sólo lectura. 8 paquetes
  `WAIT_REG_MEM` decodificados.
- `STATIC` — `sid.h:397-414`, `soc15d.h:199-225`, `gfx_v8_0.c:6047-6049` y
  `:6180-6202` y `:5246`, y los 10 emisores con `FUNCTION != 0` en 8 generaciones.
- **CONFOUNDER**: `debugfs` es sólo lectura aquí (a diferencia de
  `amdgpu_fence_info`, `098`). El volcado del ring no ejecuta nada.
- Corrige/completa `017`, que es de otra sesión: **lo informo, no lo edito.**
- Encadenada con `017` (encoding y el `ref=0/mask=0`), `068`/`085` (el emitter),
  `103`/`104` (el invalidate), `097` (el volcado del ring).
- Cierra el ítem explícito de `AGENTS.md` L413.
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`: son de otras sesiones.

**Dos notas de método.**

La primera: **adiviné la posición del bit de `OPERATION`.** Lo puse en los bits
[17:16] sin comprobarlo, decodifiqué, y el resultado no coincidía con **ninguno**
de los tres emisores de `gfx_v8_0.c`.

Eso fue lo que salvó el dato: **al buscar a qué emisor pertenecía el paquete y no
encontrar ninguno, sospeché del decode y no del ring.** `soc15d.h:201` dice
`OPERATION` está en el bit 6, no en el 16. Con el bit correcto, coincide
exactamente.

**Un decode que no puedo atribuir a un emisor conocido está mal decodificado,
aunque los campos parezcan razonables.** Ese es el control, y es barato.

La segunda: **`017` tenía la respuesta y yo no la había buscado.** El campo se
llama `FUNCTION` en el texto de `AGENTS.md` y yo lo associates mal con
`VM_INVALIDATE_REQUEST`, porque era el registro que estaba mirando. `017` —que
no es mío— lo tenía resuelto y lo nombraba en el título. **El corpus del
proyecto tenía la respuesta y yo la tenía delante y no la usé.**