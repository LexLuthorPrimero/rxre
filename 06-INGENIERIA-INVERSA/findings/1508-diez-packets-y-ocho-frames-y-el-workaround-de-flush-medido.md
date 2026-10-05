# 1508 — El frame del anillo gfx son **10** packets, no 7, y hay **ocho** frames idénticos. Los cuatro `EVENT_WRITE_EOP` son dos llamadas a `emit_fence_gfx`, y el `+1` entre el dummy y el real es el *workaround* de flush de caché, medido en el artefacto

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

CORRIGE, mio   1500 y 1502.  El frame tiene 10 packets, no 7: hay CUATRO
               EVENT_WRITE_EOP y solo mire uno.  Y CONTEXT_CONTROL esta en el
               dword 15, no en el 16.
CORRIGE, mio   1502 §7 "el frame del anillo gfx esta cerrado: 7 de 7".  Era
               UNO de OCHO, y con el recuento equivocado.  Un frame no es un
               evento: es una plantilla que se repite.

PROVEN         la ventana son 8 frames de 256 dwords, identicos 8 de 8, y la
               contabilidad cierra exacta: 8 x (50 + 206) = 2048, cero dwords
               sin repartir.
PROVEN         los 4 EVENT_WRITE_EOP son 2 invocaciones de
               gfx_v8_0_ring_emit_fence_gfx, que emite DOS EOP: uno dummy con
               seq-1 y el real con seq.  El +1 esta medido: 0x9bae/0x9baf y
               0x9be7/0x9be8.
PROVEN         el IB NO esta en el anillo.  length_dw 344/1104/1488 no caben
               en un frame de 256.  El trabajo de GPU es INVISIBLE en las 21
               capturas.
CIERRA         el frame de compute: productores en gfx_v8_0.c:6779 y 6245,
               con counts 5 y 5, que coinciden con los del anillo.
ERROR, mio     4a vez la misma forma: un `| head` me trunco el inventario y
               casi escribo un NOT_FOUND falso.
```

## 0 · LO QUE SE CORRIGE, Y ES DE `1500`

`1500` dio por bueno este frame:

```text
  dword  op    nombre                count
     3    0x22  COND_EXEC                3
     8    0x3c  WAIT_REG_MEM             5
    16    0x28  CONTEXT_CONTROL         1      <- esta en 15, no en 16
    18    0x3f  INDIRECT_BUFFER          2
    22    0x37  WRITE_DATA              3
    27    0x47  EVENT_WRITE_EOP         4
    33    0x8b  SWITCH_BUFFER           0      <- y no es el siguiente: hay 3
```

Y `1502` lo cerro con `7 de 7`. **Re-parsando el frame entero salen diez.**

```text
   [  3] 0x22  COND_EXEC            count=3    cuerpo 4 dwords
   [  8] 0x3c  WAIT_REG_MEM         count=5    cuerpo 6
   [ 15] 0x28  CONTEXT_CONTROL      count=1    cuerpo 2
   [ 18] 0x3f  INDIRECT_BUFFER      count=2    cuerpo 3
   [ 22] 0x37  WRITE_DATA           count=3    cuerpo 4
   [ 27] 0x47  EVENT_WRITE_EOP      count=4    cuerpo 5
   [ 33] 0x47  EVENT_WRITE_EOP      count=4    cuerpo 5     <- se me fue
   [ 39] 0x47  EVENT_WRITE_EOP      count=4    cuerpo 5     <- se me fue
   [ 45] 0x47  EVENT_WRITE_EOP      count=4    cuerpo 5     <- se me fue
   [ 51] 0x8b  SWITCH_BUFFER        count=0    cuerpo 1
```

El desfase del `CONTEXT_CONTROL` explica por que `1500` no vio el resto: con el
tercer paquete desplazado una posicion, la cadena se rompe ahi y el resto queda
como "desconocido" en vez de como packet.

**Y los cuatro EOP no son el mismo packet repetido.** Ver §3.

## 1 · HAY OCHO FRAMES, NO UNO

Los ocho `INDIRECT_BUFFER` estan a distancia **exactamente constante**:

```text
  dword del IB        18  274  530  786 1042 1298 1554 1810
  delta al siguiente  --  256  256  256  256  256  256  256
  MEDIDO  7 de 7 deltas son 256
```

Y los ocho frames tienen **la misma secuencia de diez packets, con los mismos
counts y los mismos offsets relativos**:

```text
  frame 0   +0 COND_EXEC  +5 WAIT  +12 CTX_CTRL  +15 IB  +19 WRITE_DATA
            +24 EOP  +30 EOP  +36 EOP  +42 EOP  +48 SWITCH
  frame 1   identico
  ...
  frame 7   identico
```

```text
  PROVEN  la ventana de 2048 dwords contiene 8 frames de 256, y los 8 tienen
          la misma ESTRUCTURA: mismo opcode, mismo count, mismo offset
          relativo, mismo body[0] y mismo body[2] de los cuatro EOP.
```

**Y esa frase estaba mal escrita, y lo corrijo aqui mismo.** No son
identicos *byte a byte*: los cuatro `body[0]` y los cuatro `body[2]` si lo
son, pero **`body[3]` cambia**, y es `lower_32_bits(seq)`. Ver §3.

```text
  frame 0   body[2] de los 4 EOP:  0x200000ff  0x400000ff  0x200000ff  0x220000ff
  frame 1   body[2] de los 4 EOP:  0x200000ff  0x400000ff  0x200000ff  0x220000ff
            identicos
  frame 0   body[3] de los 4 EOP:  0x00009bae   0x00009baf   0x00009be7   0x00009be8
  frame 1   body[3] de los 4 EOP:  0x00009baf   0x00009bb0   0x00009be8   0x00009be9
            DISTINTOS
```

```text
  PROVEN_DERIVED  la plantilla del frame es fija 8 de 8, y lo unico que corre
                  es el contador de valla.  Eso es lo que hace que un patron
                  sobreviva a la produccion: la forma no cambia, el numero si.
```

Por eso `1502` §7 decia una falsedad sin querer: **"el frame del anillo gfx
esta cerrado"**. Un frame no es un evento del anillo, es lo que se repite. Lo
que estaba cerrado era el frame 1, y mal contado.

### La contabilidad cierra exacta

```text
  ventana (dwords 3..2050)               2048
  8 frames x 256 dwords                   2048    <- cuadra

  por frame:  50 dwords de packets
              206 dwords de relleno NOP (0xffff1000, de 1506)
  8 x 50  =  400
  8 x 206 = 1648   <- MEDIDO, y es exactamente el fill_nop de gfx
  400 + 1648 =  2048
```

**Cero dwords sin explicar en los 2048.** Con el relleno identificado en `1506`
como `PACKET3(NOP, 0x3FFF)` emitido por el driver, este anillo esta
**completamente auditado**: no queda nada por interpretar en el anillo gfx.

## 2 · EL IB NO ESTA EN EL ANILLO. Y ESO ES EL LIMITE DURO DE ESTAS CAPTURAS

Los ocho IB tienen `length_dw` de **344, 1104, 344, 1488, 344, 1104, 344,
1488**, y el frame que los referencia son **256 dwords**.

```text
  length_dw minimo      344 dwords
  frame que lo contiene 256 dwords
  344 > 256
```

Un IB de 344 dwords no cabe en un frame de 256. **Y no es un error de
interpretacion: es la prueba de que el IB vive en otro sitio.**

`gpu_addr` es una direccion de **VRAM** (`0x1004f0000`), y el unico puntero a
ella que hay en el anillo son los tres dwords del propio `INDIRECT_BUFFER`. El
IB se ejecuta desde memoria, y su contenido **no esta en ninguna de las 21
capturas**.

```text
  PROVEN  el anillo contiene la SUBMISION, no el TRABAJO.

  Volumen medido:  6560 dwords de IB en vuelo = 26 240 bytes
                   repartidos en 8 frames de 256 dwords = 1024 bytes cada uno
  El IB es de media 820 dwords, 3.2 veces el frame que lo referencia.

  CONSECUENCIA PARA EL PROYECTO:  ningun packet de dibujo, ningun shader,
  ningun descriptor de vertex esta disponible en el material que tengo. Todo
  lo que heLEY del anillo gfx es la envoltura de la submit, no lo que se
  dibuja.  Y eso no se arregla con mas herramientas: no esta en los ficheros.
```

Este es el limite real del material, y conviene escribirlo ahora y no
descubrirlo dentro de un mes.

## 3 · LOS CUATRO EOP: EL WORKAROUND DE FLUSH DE CACHE, MEDIDO

Decodificados con el productor, `gfx_v8_0_ring_emit_fence_gfx`
(`gfx_v8_0.c:6141`), leido entero:

```c
/* Workaround for cache flush problems. First send a dummy EOP
 * event down the pipe with seq one below. */
amdgpu_ring_write(ring, PACKET3(PACKET3_EVENT_WRITE_EOP, 4));
... EVENT_INDEX(5)));
amdgpu_ring_write(ring, addr & 0xfffffffc);
amdgpu_ring_write(ring, (upper_32_bits(addr) & 0xffff) | DATA_SEL(1) | INT_SEL(0));
amdgpu_ring_write(ring, lower_32_bits(seq - 1));        /* <-- el DUMMY */
amdgpu_ring_write(ring, upper_32_bits(seq - 1));

/* Then send the real EOP event down the pipe: */
amdgpu_ring_write(ring, PACKET3(PACKET3_EVENT_WRITE_EOP, 4));
... EVENT_INDEX(5) | (exec ? EOP_EXEC : 0)));
amdgpu_ring_write(ring, addr & 0xfffffffc);
amdgpu_ring_write(ring, ... DATA_SEL(write64bit ? 2 : 1) | INT_SEL(int_sel ? 2 : 0));
amdgpu_ring_write(ring, lower_32_bits(seq));             /* <-- el REAL */
amdgpu_ring_write(ring, upper_32_bits(seq));
```

El cuerpo son cinco dwords, y el cuarto es `lower_32_bits(seq)`. En el anillo:

```text
  EOP  dword  flags    addr_lo    flags2    seq_lo   seq_hi
   0    27   0x00038514 0x016b7000 0x200000ff 0x9bae  0
   1    33   0x00038514 0x016b7000 0x400000ff 0x9baf  0
   2    39   0x00038514 0x00001040 0x200000ff 0x9be7  0
   3    45   0x00038514 0x00001040 0x220000ff 0x9be8  0
```

```text
  seq_lo:  0x9bae -> 0x9baf   = +1      <- el par dummy/real de la valla 1
           0x9be7 -> 0x9be8   = +1      <- el par dummy/real de la valla 2
```

**Los cuatro EOP son dos vallas**, y en cada una el primero lleva `seq-1` y el
segundo `seq`. El `+1` que se ve en el artefacto **es** el workaround, no una
coincidencia.

Decodificacion del resto, con los macros de `cikd.h`/`vid.h`:

```text
  body[0] = 0x00038514
    bits[7:0]  EVENT_TYPE = 0x14 = 20 = CACHE_FLUSH_AND_INV_TS_EVENT
    bits[15:8] EVENT_INDEX(5)
    bit 15     EOP_TCL1_ACTION_EN     bit 16  EOP_TC_ACTION_EN
    bit 17     EOP_TC_WB_ACTION_EN
    los cuatro bodies[0] son IDENTICOS  ->  EOP_EXEC vale lo mismo en las dos
                                          vallas (no se distinguish por ahi)

  body[2]:
    DATA_SEL(x)     = x << 29     INT_SEL(x)      = x << 24
    EOP_CACHE_POLICY(x) = x << 25
    EOP0  0x200000ff  DATA_SEL(1)                       (dummy, 64bit fijo)
    EOP1  0x400000ff  DATA_SEL(2)  -> write64bit = 1
    EOP2  0x200000ff  DATA_SEL(1)                       (dummy)
    EOP3  0x220000ff  DATA_SEL(1) | EOP_CACHE_POLICY(1) -> write64bit = 0
```

```text
  DESCUBRE  las dos vallas del frame NO son iguales: la primera se emite con
            AMDGPU_FENCE_FLAG_64BIT y la segunda con 32 bits y cache policy 1.
            Y las dos escriben en direcciones distintas: 0x016b7000 frente a
            0x00001040 (estos son los 32 bits bajos de la addr del fence).
```

**Y esto es lo que hace que `1500` no lo viera**: los cuatro EOP comparten
opcode, count, y hasta tres de los cinco dwords del cuerpo. Un solo campo de un
bit — `DATA_SEL` — distingue el segundo del primero. Cualquier lectura que mire
"los packets del frame" en vez de "los cinco dwords de cada cuerpo" los
colapsa en uno.

## 4 · EL FRAME DE COMPUTE, AHORA CON PRODUCTOR

`1503` §3 nombro `ACQUIRE_MEM` y `RELEASE_MEM` en el frame de compute, y temi
que fuera una atribucion mia sin respaldo. **Hay respaldo, y es exacto:**

```text
  ACQUIRE_MEM  gfx_v8_0.c:6779  gfx_v8_0_emit_mem_sync_compute   PACKET3(..., 5)
  RELEASE_MEM  gfx_v8_0.c:6245  gfx_v8_0_ring_emit_fence_compute PACKET3(..., 5)
  anillo:                        op=0x58 count=5   y   op=0x49 count=5
```

**Los counts coinciden los dos.** Y el par tiene sentido: `emit_fence_compute`
va detras de `emit_mem_sync_compute`, o sea que compute toma la memoria, lanza
el IB, y la devuelve con su valla. Es el mismo esquema que gfx, sin dibujo.

Las dos funciones estan vivas para POLARIS12 — viven en `gfx_v8_0.c`, y
`.emit_fence = gfx_v8_0_ring_emit_fence_gfx` esta en
`gfx_v8_0_ring_funcs_gfx` (§3 lo uso como productor).

## 5 · EL ERROR DE METODO: CUARTA VEZ

Busque quien emite `PACKET3_RELEASE_MEM` para comprobar si el `0x49` del anillo
de compute tiene productor en `gfx_v8_0.c`, y mi comando fue:

```bash
$ grep -rn "PACKET3_RELEASE_MEM" .../amd/ | grep -v cikd.h | head
   ... solo salia gfx_v10_0.c:8722
```

Conclui, durante unos minutos, que **`gfx_v8_0.c` no emite `RELEASE_MEM`** y que
la atribucion de `1503` era mia y estava sin fuente. **Falso.** Sin el `| head`:

```text
  gfx_v8_0.c:6245   gfx_v10_0.c:8722  gfx_v11_0.c:6072  gfx_v12_0.c:4561
  gfx_v7_0.c:2167   gfx_v9_0.c:5593   gfx_v9_4_3.c:2965  gfx_v12_1.c:3462
```

Ocho emisores, y el primero es precisamente el de POLARIS12.

```text
  LA SERIE, Y AHORA ESTA CLARA:

    1500  busco 0x3f, el fuente tiene 0x3F
    1502  dos greps, atribuyo la linea al que no funciona
    1506  dos greps, atribuyo la linea al que no funciona
    1508  un `| head` trunca el inventario y concluyo PROVEN_ABSENT

  LAS CUATRO SON:  DECIDI UNA COSA ANTES DE HABER VISTO TODA LA SALIDA.

  Y 1508 es la mas peligrosa de las cuatro, porque las otras tres dejaban
  un dato falso en un hallazgo, y esta casi deja un PROVEN_ABSENT.  Un
  PROVEN_ABSENT cierra la frontera: el que venga leera "ya se buscaron todos
  los emisores" y no lo volvera a mirar.  Y el que lo escribe esta a un
  `| head` de mirar la respuesta real.

  LA REGLA, y es la unica que evita las cuatro:
    un inventario no es un grep.  Un grep con limitador es un teaser, y no
    admite PROVEN_ABSENT ni NOT_FOUND.  Si el inventario no cabe en pantalla,
    se escribe a un fichero y se cuenta.
```

## 6 · ESTADO

```text
PROVEN          la ventana del anillo gfx son 8 frames de 256 dwords, con
                delta medido 7 de 7 igual a 256, y los 8 identicos en opcode,
                count y offset relativo.
PROVEN          la contabilidad cierra exacta: 8 x (50 de packets + 206 de
                NOP) = 400 + 1648 = 2048.  Cero dwords sin explicar.
PROVEN          el frame tiene 10 packets, no 7.  Hay 4 EVENT_WRITE_EOP.
PROVEN          los 4 EOP son 2 llamadas a gfx_v8_0_ring_emit_fence_gfx
                (gfx_v8_0.c:6141/6165), que emite un dummy con seq-1 y el real
                con seq.   dejaban
  un dato falso en un hallazgo, y esta casi deja un PROVEN_ABSENT.  Un
  PROVEN_ABSENT cierra la frontera: el que venga leera "ya se buscaron todos
  los emisores" y no lo volvera a mirar.  Y el que lo escribe esta a un
  `| head` de mirar la respuesta real.

  LA REGLA, y es la unica que evita las cuatro:
    un inventario no es un grep.  Un grep con limitador es un teaser, y no
    admite PROVEN_ABSENT ni NOT_FOUND.  Si el inventario no cabe en pantalla,
    se escribe a un fichero y se cuenta.
```

## 6 · ESTADO

```text
PROVEN          la ventana del anillo gfx son 8 frames de 256 dwords, con
                delta medido 7 de 7 igual a 256.  Los 8 tienen la misma
                ESTRUCTURA (opcode, count, offset, body[0] y body[2] de los
                EOP), y NO son identicos byte a byte: body[3] cambia.
PROVEN          la contabilidad cierra exacta: 8 x (50 de packets + 206 de
                NOP) = 400 + 1648 = 2048.  Cero dwords sin explicar.
PROVEN          el frame tiene 10 packets, no 7.  Hay 4 EVENT_WRITE_EOP.
PROVEN          los 4 EOP son 2 llamadas a gfx_v8_0_ring_emit_fence_gfx
                (gfx_v8_0.c:6141/6165), que emite un dummy con seq-1 y el real
                con seq.  El +1 medido: 0x9bae/0x9baf y 0x9be7/0x9be8.
PROVEN_DERIVED  body[3] es lower_32_bits(seq), y avanza +1 por frame con un
                salto de -7 entre los frames 1 y 2.  El patron
                (seq-1, seq, seq+0x38, seq+0x39) se mantiene 8 de 8: las dos
                vallas de un frame comparten base y solo se separan en +0x38.
PROVEN_DERIVED  seq avanza +1 por valla, con un salto de -7 entre los frames 1
                y 2.  El patron (seq-1, seq, seq+0x38, seq+0x39) se mantiene
                8 de 8.
PROVEN_DERIVED  la valla 1 se emite con AMDGPU_FENCE_FLAG_64BIT (DATA_SEL=2) y
                la valla 2 con 32 bits y EOP_CACHE_POLICY=1.  Escriben en
                direcciones distintas.
PROVEN          el IB no esta en el anillo: length_dw 344 minimo contra un
                frame de 256.  gpu_addr es VRAM.  6560 dwords = 26 240 bytes
                de trabajo en vuelo que no estan en ninguna captura.

CIERRA          el frame de compute: ACQUIRE_MEM de gfx_v8_0.c:6779
                (emit_mem_sync_compute, count 5) y RELEASE_MEM de
                gfx_v8_0.c:6245 (emit_fence_compute, count 5).  Counts
                coincidentes con el anillo.

CORRIGE, mio    1500: 10 packets no 7; CONTEXT_CONTROL en el dword 15 no 16;
                cuatro EVENT_WRITE_EOP no uno.
CORRIGE, mio    1502 §7: el frame no estaba "cerrado", estaba uno de ocho
                leido y mal contado.
CORRIGE, mio    mi propia conclusion de hace 20 minutos: si, hay productor de
                RELEASE_MEM en gfx_v8_0.c, y con el count exacto.

ERROR, mio      `| head` en un inventario.  Cuarta vez que decido antes de ver
                toda la salida.  Un grep con limitador no admite
                PROVEN_ABSENT.

NOT_DETERMINED  por que hay 253 NOP entre el autotest y el frame de compute.
                align_mask = 0xff (medido en la tabla viva) implica 256, y 259
                no es multiplo de 256.  Los offsets del fichero son de
                ventana, no de anillo, y falta rptr/wptr.
NOT_DETERMINED  por que las dos vallas del frame tienen 64 y 32 bits y
                direcciones distintas.  El driver lo decide con flags que
                llegan desde el fence driver, y eso no esta en el anillo.
```

## 7 · LO QUE SIGUE

El anillo gfx esta **cerrado y auditado**. No queda nada que interpretar en
2048 dwords: los 400 de packets estan nombrados y decodificados, y los 1648 de
relleno son el `.nop` del driver (`1506`).

El limite real esta escrito y es de material, no de metodo: **el trabajo de GPU
no esta en las capturas**. El anillo da la envoltura; el contenido del IB esta
en VRAM y no se puede leer sin `/dev/dri/card1`, que es `root:video` y no estoy
en el grupo.

Lo que si queda abierto, y es de la parte de compute:

```text
  el frame de compute tiene 6 packets, uno de ellos un IB con length_dw = 5,
  gpu_addr = 0xff00ab6400 y VALID(bit23) = 1, cuando los 8 IB del anillo gfx
  lo tienen a 0.  El compute usa VMID 0 y marca el IB como valido; el gfx usa
  VMID 7 y no lo marca.  Eso no tiene todavia explicacion, y hay dos
  candidatos descartables: la distinta familia de anillo, o el camino
  distinto de valla (emit_fence_compute en vez de emit_fence_gfx).
```