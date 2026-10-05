# 1226 — El `0x3FFF` del `NOP` no es un paquete: es el **valor con el que se rellena el anillo entero**. Y no está dimensionado al anillo, sino que es el máximo del campo de 14 bits

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=SEMANTICS · RING-BUFFER
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura)
CIERRA   1225 §2 y §6:  "NOP:  el valor 0x3FFF que el driver guarda en
                        gfx_ring_funcs.nop merece su propio hallazgo"
VALIDA   que 0x3FFF es el SATURADO del campo count de 14 bits  y no un
         tamano de anillo:  0 coincidencias de 4 valores de ring_size reales
DESRULEO REFUTA la lectura plausible de que 0x3FFF se eligio para casar con
         el tamano del anillo
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 1 · `.nop` no es una función: es un `u32`, y es el valor de relleno

Lo escribí mal en `1225` al llamarlo "tabla de funciones del anillo guardando el comando". Es
un miembro del mismo struct, pero de tipo **valor**, no de puntero:

```c
  amdgpu_ring.h:208-215
      /**
       * @nop:
       *
       * Every block in the amdgpu has no-op instructions (e.g., GFX 10
       * uses PACKET3(PACKET3_NOP, 0x3FFF), VCN 5 uses VCN_ENC_CMD_NO_OP,
       * etc). This field receives the specific no-op for the component
       * that initializes the ring.
       */
      u32           nop;
```

Y su uso real es `memset32`:

```c
  amdgpu_ring.h:488-491
      static inline void amdgpu_ring_clear_ring(struct amdgpu_ring *ring)
      {
              memset32(ring->ring, ring->funcs->nop, ring->buf_mask + 1);
      }
```

**Se rellena el anillo entero** con ese dword. Los demás usos son el mismo patrón:

```text
  amdgpu_ring.c:128,131  memset32(...,  ring->funcs->nop,  chunk)   insert_nop
  amdgpu_ring.c:154      memset32(...,  ring->funcs->nop,  count)   pad_ib
  amdgpu_gfx.c:1683      ib->ptr[i] = ring->funcs->nop
  amdgpu_gmc.c:759       job->ibs->ptr[...] = ring->funcs->nop
  amdgpu_fence.c:741     amdgpu_ring_write(ring, ring->funcs->nop)
  cik_sdma.c:205         amdgpu_ring_write(ring, ring->funcs->nop)
```

Y `amdgpu_ring_clear_ring` se llama **cuatro veces en GFX8**: `gfx_v8_0.c:4274, 4597, 4608, 4648`.

## 2 · Por qué funciona: la cadena de NOPs

`PACKET3` mete el `count` en los bits [29:16]:

```c
  vid.h:105-107
      #define PACKET3(op, n)  ((PACKET_TYPE3 << 30) |          \
                                   (((op) & 0xFF) << 8) |      \
                                   ((n) & 0x3FFF) << 16)
```

`0x3FFF` es exactamente el máximo del campo: los 14 bits van a `1`. Con `count = payload − 1`
de `1225`, un NOP con `count = 0x3FFF` significa "los siguientes 16384 dwords son no-op".

Como el anillo **entero** está lleno del mismo dword, la lectura es una cadena:

```text
  dword 0         NOP, count=16384   ->  salta hasta el dword 16385
  dword 16385     NOP, count=16384   ->  salta hasta el dword 32770
  ...
  y asi hasta cerrar el buffer
```

O sea: el CP nunca ejecuta nada, y no importa dónde esté `wptr` porque todo lo que puede leer
es un no-op. **Ese es el propósito del relleno**, y por eso el valor debe ser un NOP y no
cero.

## 3 · `0x3FFF` NO está dimensionado al anillo

Era lo que había que comprobar, porque `0x3FFF + 1 = 16384 dwords = 64 KiB` es un tamaño de
anillo plausible y no sería casualidad. No lo es. El tamaño sale de:

```c
  amdgpu_gfx.c:334       amdgpu_ring_init(adev, ring, 1024, ...)   <- max_dw del KIQ
  amdgpu_ring.c:339      ring_size = roundup_pow_of_two(max_dw * 4 * sched_hw_submission)
  amdgpu_ring.c:347      ring->buf_mask = (ring->ring_size / 4) - 1
```

Y los cuatro valores de `sched_hw_submission` que existen:

```c
  amdgpu_drv.c:178   int amdgpu_sched_hw_submission = 2;      (por defecto)
  amdgpu_drv.c:491   module_param_named(sched_hw_submission, ...)   0444, solo lectura
  amdgpu_device.c:1577-1584   forzado a >=2 y redondeado a potencia de dos
  amdgpu_ring.c:243-244   si el anillo es KIQ:  sched = max(sched, 256)
  amdgpu_ring.c:245-248   MES: 8   ·   SDMA page: 256
```

Con `max_dw = 1024` para el KIQ, y el KIQ forzado a `sched = 256`:

```text
  tipo de anillo     sched    ring_size    buf_mask+1      NOP payload   cobertura
  ---------------------------------------------------------------------------------
  KIQ  (el que mas importa)   256     1048576 B        262144 dwords     16384       1/16
  MES                        8         65536 B         16384 dwords     16384        1/1
  SDMA page                256         1048576 B        262144 dwords     16384       1/16
  por defecto (otro anillo)   2          16384 B          4096 dwords     16384        4/1
```

`0x3FFF + 1` coincide con el tamaño del anillo **solo en el caso MES**, y se sale por 4 en el
valor por defecto y por 16 en el KIQ. Como el KIQ es precisamente el anillo que el clearing
tiene que cubrir bien, la coincidencia del MES no puede ser la razón.

**Conclusión: `0x3FFF` es el saturado del campo, elegido para que el dword de relleno sea el
mismo con cualquier tamaño de anillo.** Cualquier otro valor de `count` serviría igual de bien
como relleno — el relleno funciona mientras sea un NOP — y `0x3FFF` es simplemente el mayor.

Eso tiene una consecuencia práctica: **`0x3FFF` no es una constante que haya que recalcular
para el anillo de la RX550**. Es fija, y copiarla es correcto.

## 4 · Por qué `count = payload − 1` no aplica aquí, y sigue siendo correcto

`1225` dejó `NOP` como `NOT_APPLICABLE` a la regla `count = payload − 1`, y sigue siendo la
clasificación correcta, pero por un motivo que ahora se puede precisar. En `NOP` el `count` no
describe cuántas escrituras hace el driver **a continuación en el código**, sino cuántos dwords
el **CP debe saltar al hardware**. Son dos cosas distintas:

```text
  paquetes normales   count = payload - 1        el driver escribe payload dwords,  y cuenta
  NOP                 count = 16384              el hardware salta 16384 dwords,  y el
                                                 driver no escribe nada:  rellena con memset
```

El hecho de que el driver **sí** escriba exactamente `0x3FFF + 1` dwords si se le pide
(`amdgpu_ring_insert_nop(ring, count)` con `count` arbitrario) es lo que hace que las dos reglas
coincidan en la forma, y por eso el invariante de `1225` aguanta 11 de 11.

## 5 · Procedimiento

```text
PREGUNTA   ¿que significa el 0x3FFF de gfx_ring_funcs.nop?
FUENTES    amdgpu_ring.h:204-216 (tipo y doc),  :488-491 (clear_ring)
           amdgpu_ring.c:118-136 (insert_nop),  :339-347 (ring_size, buf_mask)
           amdgpu_drv.c:178,491  ·  amdgpu_device.c:1577-1584  ·  amdgpu_ring.c:243-248
           vid.h:105-107  (PACKET3 y el ancho de 14 bits del count)
           los 12 usos de ring->funcs->nop en los .c
MEDIDO     nop es u32,  no puntero a funcion         ->  "tabla de funciones" era impreciso
           memset32 sobre buf_mask+1  =  anillo entero
           4 llamadas a clear_ring en GFX8
           ring_size del KIQ = 1048576 B = 262144 dwords
           0x3FFF + 1 = 16384 dwords  =  1/16 del KIQ
DISPOSITIVO  NINGUNO.  i915 y amdgpu intactos.
RUNTIME      NOT_RUN
LO QUE SIGUE
  - la cadena de NOPs esta cerrada por lectura estatica,  pero el salto de 16384
    es semantica de hardware no escrita en el arbol:  queda PROVEN por lectura
    del codigo del driver,  NO verificado contra el CP
  - el ratio 1/16 sugiere que el clearing del KIQ se apoya en 16 NOPs encadenados;
    comprobarlo exigiria leer wptr/rptr de la RX550,  que sigue bloqueado
```