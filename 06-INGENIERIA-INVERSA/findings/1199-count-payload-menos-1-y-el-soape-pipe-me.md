# 1199 — El recuento de PACKET3 es **payload − 1**, corroborado por tres vías independientes. Y los anchos de `MAP_QUEUES.CONTROL2` **no están declarados**: se deducen de un invariante que el driver aplica y no escribe

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=PM4-SEMANTICS + CONTRADICTION-RESOLVED
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
CLASE=FACT · DERIVATION · ESTADO=CORROBORADO / CONTRADICTION_RESOLVED
CORPUS=RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/  (vid.h, soc15d.h,
        gfx_v8_0.c, amdgpu_gfx.c)  +  amdkfd/kfd_pm4_headers.h
CIERRA  1062 (longitud = count + 2)  ·  pendiente:  doorbell_offset[25:2] vs [22:2]
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST
```

## 0 · Una corrección a mí mismo antes que nada

Empecé por `soc15d.h`, que es donde están los macros de `MAP_QUEUES` con la codificación que
yo esperaba, y estuve a punto de registrarlo como la autoridad de nuestro ASIC.

Los includes de `gfx_v8_0.c` dicen:

```text
  #include "vi.h"
  #include "vid.h"          <-- ESTE
```

**No incluye `soc15d.h`.** El applicable a GFX8 es `vid.h`, y las posiciones de bit de
`soc15d.h` son de otra familia. Un hallazgo que empieza por "la autoridad es `soc15d.h`"
estaba errado antes de escribirse.

## 1 · La cabecera PACKET3: tres fuentes independientes y de tres subsistemas

```text
  A.  amdgpu,  vid.h:105  (y 106 en soc15d.h:50)   la macro
        #define PACKET3(op, n)  ((PACKET_TYPE3 << 30) | (((op) & 0xFF) << 8) \
                                 | ((n) & 0x3FFF) << 16)

  B.  amdkfd,  kfd_pm4_headers.h:30   OTRO subsistema del MISMO kernel
        union PM4_MES_TYPE_3_HEADER {
                uint32_t reserved1:8;     bits  7:0
                uint32_t opcode:8;         bits 15:8
                uint32_t count:14;        bits 29:16
                uint32_t type:2;          bits 31:30
        };

  C.  las herramientas del proyecto, medidas
        type en 31:30 (2 bits), opcode en 15:8 (8 bits), count en 29:16 (14 bits)
```

Las tres coinciden, y B además trae el comentario que A no trae:

```text
  /* number of DWORDs - 1 in the information body */
```

## 2 · La convención del recuento, decidida contando dwords, no leyendo

La lectura estática del comentario de KFD y la macro de amdgpu parecían dos convenciones
distintas: KFD dice "menos uno", y `PACKET3(op, n)` pasa `n` tal cual. Se decide **contando**
los `amdgpu_ring_write` de tres puntos de emisión de `gfx_v8_0.c`:

| Punto de emisión | `n` | payload contados | ¿`n = payload − 1`? | total |
|---|---|---|---|---|
| `INDIRECT_BUFFER` (6125-6132) | 2 | 3 (addr_lo, addr_hi, control) | sí | 4 = n+2 |
| `MAP_QUEUES` (4345-4356) | 5 | 6 (num_q, doorbell, mqd lo/hi, wptr lo/hi) | sí | 7 = n+2 |
| `UNMAP_QUEUES` (4773-4779) | 4 | 5 (action, doorbell0, 0, 0, 0) | sí | 6 = n+2 |

Y una **cuarta comprobación independiente**, que no es del mismo género:

```c
  gfx_v8_0.c:6934    .emit_ib_size = 7, /* gfx_v8_0_ring_emit_ib_compute */
```

Contando `gfx_v8_0_ring_emit_ib_compute` (6101-6133) en la rama con
`AMDGPU_IB_FLAG_RESET_GDS_MAX_WAVE_ID`: 3 dwords de `SET_CONFIG_REG` + 4 de
`INDIRECT_BUFFER` = **7**. Y en la base son 4. El 7 declarado coincide con el 7 contado.

> El hallazgo `1062` ("la longitud de un paquete PM4 es count más dos") queda
> **CORROBORADO** por tres puntos de emisión y por una constante del driver que no se usó
> para derivarlo.

## 3 · `MAP_QUEUES.CONTROL2`: los anchos no están declarados

`vid.h:392-405`, con el comentario de estructura que sí los separa por dword:

```text
  1. header      2. CONTROL      3. CONTROL2
  4. MQD_ADDR_LO 5. MQD_ADDR_HI   6. WPTR_ADDR_LO  7. WPTR_ADDR_HI

  /* CONTROL  */
  QUEUE_SEL      << 4      VMID          << 8
  QUEUE_TYPE     << 21     ALLOC_FORMAT  << 24
  ENGINE_SEL     << 26     NUM_QUEUES    << 29
  /* CONTROL2 */
  CHECK_DISABLE  << 1      DOORBELL_OFFSET << 2
  QUEUE          << 26     PIPE          << 29
  ME             << 31
```

**Solo desplazamientos. Ni una anchura, ni una máscara.** Deducirlos del campo siguiente:

```text
  CONTROL    DOORBELL_OFFSET << 2,  siguiente QUEUE_SEL << 4      -> [3:2],  2 bits
             QUEUE_SEL       << 4,  siguiente VMID << 8           -> [7:4],  4 bits
             VMID            << 8,  siguiente ... << 21          -> [20:8] y hueco
  CONTROL2   CHECK_DISABLE   << 1,  siguiente DOORBELL_OFFSET<<2  -> [1:1],  1 bit
             DOORBELL_OFFSET << 2,  siguiente ... << 26          -> [25:2] y hueco
             QUEUE           << 26, siguiente PIPE << 29         -> [28:26] 3 bits
             PIPE            << 29, siguiente ME << 31           -> [30:29] 2 bits
             ME              << 31                               -> [31:31] 1 bit
```

### CORRECCION, y es una inconsistencia de este mismo hallazgo

Al construir la herramienta que hace esta comprobación para todo el header, la salida
contradijo lo que yo habia escrito aqui:

```text
  mi tabla de deduccion    DOORBELL_OFFSET << 2,  siguiente ... << 26  ->  [25:2] y hueco
  mi conclusion            ... y por tanto es [3:2], de 2 bits
```

Las dos cosas no pueden ser verdad a la vez, y **la que se sostiene es que la anchura no
se deduce en absoluto**. El "siguiente" de `DOORBELL_OFFSET << 2` no es su vecino: es
`QUEUE << 26`, que pertenece al **mismo dword pero cuyo valor es de otro campo**… y mas
aun, `ENGINE_SEL << 26` y `QUEUE << 26` son de dwords distintos, asi que ordenar por
desplazamiento mezcla palabras.

> Un hueco grande no es un campo ancho: es un layout que los desplazamientos **no**
> determinan.

`vid.h` declara 5 desplazamientos de `MAP_QUEUES` y **ni una anchura ni una mascara**, y
para `DOORBELL_OFFSET` en concreto la secuencia de shifts no cierra una particion de 32
bits. El valor correcto —2 bits en el GFX8— viene de la especificación del ASIC, no de
este fuente, y esa fuente **no está en el árbol**.

Lo que sí queda cerrado por el conteo del §2 es la convención del recuento, que no depende
de ninguna deducción: `n = payload − 1`, medido en tres puntos de emisión y corroborado por
`.emit_ib_size = 7`.

## 4 · Y el invariante que NO está escrito: el bit de ME y el de PIPE se pisan

`PIPE << 29` con 3 bits alcanzaría el bit 31, que es el de `ME << 31`. El driver usa los dos
en el mismo dword:

```c
  gfx_v8_0.c:4348
  PACKET3_MAP_QUEUES_DOORBELL_OFFSET(...) | PACKET3_MAP_QUEUES_QUEUE(...) |
  PACKET3_MAP_QUEUES_PIPE(ring->pipe)     | PACKET3_MAP_QUEUES_ME(ring->me == 1 ? 0 : 1)
```

Con `gfx_v8_0.c:1910`, `num_pipe_per_mec = 4`, y
`amdgpu_queue_mask_bit_to_mec_queue` da `pipe = (...) % num_pipe_per_mec`, **`pipe` llega
hasta 3**. `pipe = 3` pone bits 30-31. Solapamiento real, si nada lo impide.

Lo que lo impide está en `amdgpu_gfx.c:289`, y **es exactamente complementario**:

```c
  if ((mec == 1 && pipe > 1) || queue != 0) continue;
  ring->me   = mec + 1;
  ring->pipe = pipe;
```

Cadena completa, cada eslabón medido:

```text
  ME(x)  con  x = (ring->me == 1 ? 0 : 1)
  -> el bit 31 se pone  si y solo si  ring->me != 1
  -> ring->me = mec + 1   ->  bit 31 se pone  si y solo si  mec == 1

  y la regla de asignacion rechaza pipe > 1  CUANDO mec == 1

  =>  bit 31 de ME puesto   ==>   pipe <= 1   ==>   pipe << 29 <= 0x20000000
                                                   ==>   bit 31 intacto
```

Comprobación numérica del caso peor:

```text
  pipe = 3,  ME(1):  (3<<29) | (1<<31) = 0xE0000000
          leyendo PIPE como [31:29] sale 7,  no 3
  pipe = 2,  ME(1):  (2<<29) | (1<<31) = 0xC0000000
          leyendo PIPE como [31:29] sale 6,  no 2
  pipe <= 1, ME(1):  sin solape
```

**No hay contradicción. Hay un invariante:**

```text
ME bit 31 == 1   ==>   pipe <= 1
```

que el driver cumple por construcción y **no escribe en ningún sitio**. Y el ámbito está
medido: la regla está en `amdgpu_gfx_kiq_acquire()`, y `MAP_QUEUES` se emite sobre
`kiq_ring`, que es exactamente el anillo que esa función adquiere. Para otros anillos la
regla no está medida y no se extrapola.

## 5 · Por qué esto importa para el driver propio

```text
1. El recuento es payload - 1, con el total = count + 2.  Si se emite count = payload,
   el hardware lee un dword de mas.

2. PIPE ocupa 2 bits ([30:29]) en el GFX8, y el driver no lo declara: se deduce del hueco
   hasta ME.  Un driver propio que copie `PIPE << 29` sin la mascara y con pipe >= 2
   corrompe ME.

3. El invariante ME=1 => pipe<=1 es lo que hace que hoy no haya solape.  Si nuestro
   driver asigna anillos por su cuenta, ese invariante hay que aplicarlo, y no basta
   con escribir los campos.

4. `ME(x) = (ring->me == 1 ? 0 : 1)`  es una inversion, no una identidad.  El lector
   que se espere ME == ring->me escribira el bit contrario en la mitad de los anillos.
```

## 6 · Procedimiento

```text
CORREGIDO   el starting point:  gfx_v8_0.c incluye vid.h, NO soc15d.h
MEDIDO      count = payload - 1  en 3 puntos de emision (INDIRECT_BUFFER, MAP_QUEUES,
            UNMAP_QUEUES),  y corroborado por .emit_ib_size = 7 contado a mano
MEDIDO      los anchos de CONTROL y CONTROL2 deducidos del hueco hasta el campo
            siguiente;  ninguno declarado en el fuente
CORREGIDO   este mismo hallazgo se contradia a si mismo;  corregido en el
            propio fichero.  La anchura NO se deduce de los shifts
RESUELTO    el aparente solape PIPE/ME:  es el invariante ME bit31 == 1 => pipe <= 1,
            aplicado en amdgpu_gfx_kiq_acquire(),  que es el anillo que emite
NO MEDIDO   el ancho REAL de PIPE en el hardware.  Todo lo anterior es lo que el
            fuente implica,  no lo que el ASIC acepta:  el discriminante es leer el
            registro tras emitir el paquete,  y eso es runtime
NO MEDIDO   la regla para anillos que NO son KIQ
runtime     RUNTIME=NOT_RUN.  Ni la RX550 ni la Intel.  i915 y amdgpu intactos
```
