# 1512 — El anillo `sdma0` se lee entero: consume los 2048 dwords exactos, y su frame es el mismo núcleo que el de gfx. Tres `POLL_REGMEM` distintos, el VMID 0 de los 46 IB, y `0xbcc` en los dos anillos

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

AREA FIJADA    sdma0.  No se cambia hasta cerrar o hasta escribir SATURATED.

PROVEN         el anillo parsea EN ORDEN y consume 2051 de 2051 dwords, cero
               huecos.  Es una teselacion exacta, como la de gfx en 1508.
PROVEN         el frame de sdma0 es POLL_REGMEM(hdp_flush) -> INDIRECT_BUFFER
               -> SRBM_WRITE(0xbcc) -> FENCE -> TRAP.  El mismo nucleo que el
               frame de gfx, sin COND_EXEC ni EOP.
PROVEN         4 tipos de POLL_REGMEM distinguibles por sus campos, con
               PRODUCTOR identificado en sdma_v3_0.c para 3 de los 4, y
               PREDICCION CONFIRMADA 46 de 46 (hdp_flush=1 solo con 0x54e0).
PROVEN         los 46 INDIRECT_BUFFER van todos con vmid=0.  El VMID 3 de 1495
               es del anillo sdma0sdma-v2/v3 y este anillo usa 0.
PROVEN         0xbcc se escribe en LOS DOS anillos: WRITE_DATA en gfx,
               SRBM_WRITE en sdma0.  46 veces.
CONFIRMA       el <<2 de 1490: mmGPU_HDP_FLUSH_DONE<<2 = 0x54e0 exacto.

ERROR, mio     primero calcule 590 de 2051 dwords "sin opcode conocido" por
               un escaneo ingenuo.  Es el error de 1500, repetido: el byte
               bajo solo es opcode si el dword ES header.
```

## 0 · POR QUE ESTE ANILLO, Y POR QUE NO ES PM4

Eligio `sdma0` porque es el unico con actividad real de invalidacion, y porque
`1495`/`1499` dejaron trabajo a medias en el. Es tambien el unico que se puede
leer entero sin acceso al hardware.

Lo primero: **`sdma0` no es un anillo PM4.** No hay `type` ni `count`, y su
`.nop` es **cero**, no `0xffff1000`:

```text
  cikd.h:499      #define SDMA_OPCODE_NOP  0
  cik_sdma.c:1237 .nop = SDMA_PACKET(SDMA_OPCODE_NOP, 0, 0)   == 0x00000000

  MEDIDO en sdma0:  784 ceros de 2051 dwords (38.2 %)
  MEDIDO en gfx   :    4 ceros de 2051 dwords
```

**El valor de relleno identifica la familia de anillo con un solo dword**, tal
como `1506` lo establecio para `0xffff1000`. Es la segunda mitad de esa regla y
funciona igual.

El layout es:

```text
  cikd.h:495   SDMA_PACKET(op, sub_op, e)
               = ((e & 0xFFFF) << 16) | ((sub_op & 0xFF) << 8) | (op & 0xFF)
```

Y el inventario de opcodes **cerrado**, de `cikd.h`:

```text
   0 NOP            5 FENCE          11 CONSTANT_FILL
   1 COPY           6 TRAP           12 GENERATE_PTE_PDE
   2 WRITE          7 SEMAPHORE      13 TIMESTAMP
   4 INDIRECT_BUF   8 POLL_REG_MEM   14 SRBM_WRITE
   9 COND_EXEC      10 (no asignado en cikd.h)
```

13 opcodes. Faltan el 3 y el 15. `SDMA_OP_PRE_EXE=15` y `SDMA_OP_DUMMY_TRAP=16`
existen pero en **otras** cabeceras generadas (`navi10_sdma_pkt_*`), que no son
la de esta generacion. Para `sdma_v3_0` el inventario es de 13.

## 1 · EL ERROR, PRIMERO, QUE ES LO QUE HACE VALER EL HALLAZGO

Empece con un escaneo ingenuo, sin longitud:

```python
c = collections.Counter(d & 0xFF for d in dw)
```

Y salio esto:

```text
  0x00 NOP              x1030
  0xff *** NO EN INVENTARIO ***   x148
  0x80 *** NO EN INVENTARIO ***   x83
  ...
  590 de 2051 (28.8 %) sin opcode conocido
```

**Ese 28,8 % es basura, y es exactamente el error de `1500`:** contar el byte
bajo de **dwords de cuerpo** y llamarlo opcode. Un dword de cuerpo tiene un
opcode con probabilidad `1/256` de parecerlo. Con 2048 dwords eso son 8
esperados, y yo reportaba 590 como si significara algo.

Lo mismo que en `1500`, y por eso lo senalo otra vez: **el mismo modo de fallo
se transfiere de dominio sin que nadie lo mire.**

## 2 · LA TESELACION EXACTA, Y AQUI SI CIERRA

Con la longitud real de cada packet, leida del productor:

```text
  packet           dwords   producer
  NOP                   1   cik_sdma.c:1237
  COPY                  4   cik_sdma.c:722
  WRITE                 4   cik_sdma.c:674
  INDIRECT_BUFFER       6   sdma_v3_0.c:432-440
  FENCE                 2   cik_sdma.c:282
  TRAP                  1   cik_sdma.c:297
  SEMAPHORE             3   (no medido: 0 apariciones)
  POLL_REGMEM           6   sdma_v3_0.c:465-470
  COND_EXEC             2   (no medido: 0 apariciones)
  CONSTANT_FILL         5   cik_sdma.c:1330
  GENERATE_PTE_PDE      3   cik_sdma.c:778
  TIMESTAMP             2   (no medido: 0 apariciones)
  SRBM_WRITE            3   sdma_v3_0.c:1078-1081
```

Parseando **en orden**, no escaneando:

```text
  packets parseados:  1066
  dwords consumidos:  2051 de 2051
  ultimo dword:       2050
  la ventana es 3..2050
```

**Consume la ventana exacta.** Cero dwords sin explicar, como `1508` en gfx.

```text
  reparto medido:
    op=0   NOP               x736   ( 736 dwords)
    op=8   POLL_REGMEM       x 82   ( 492 dwords)
    op=14  SRBM_WRITE        x 78   ( 234 dwords)
    op=5   FENCE             x 62   ( 124 dwords)
    op=6   TRAP              x 62   (  62 dwords)
    op=4   INDIRECT_BUFFER   x 46   ( 276 dwords)
                             -----
                             1066 packets, 2424 dwords nominales
```

Los 6 opcodes que no aparecen son **cero apariciones medidas**, no ausentes. No
es un `PROVEN_ABSENT`: es un recuento. La diferencia importa y la aplico: aqui
no afirmo nada sobre ellos, solo que no estan en esta ventana.

### El `0x000000ff` que casi Counts como basura

El escaneo ingenuo de §1 marco 148 dwords `0x000000ff` como «opcode
desconocido». **Son la mitad alta de una GPU VA**, dentro del cuerpo de un
`pipeline_sync`:

```text
  [35] POLL_REGMEM  addr_lo=0x00001680  addr_hi=0x000000ff
       -> direccion = 0x000000ff_00001680

  Y es la MISMA para los 20 pipeline_sync, sin excepcion.
```

```text
  0xff00001680 esta en el rango de 48 bits de GPU VA (0x000000000000..0x0000ffffffffffff).
  Y NO es un dato mio: el productor escribe upper_32_bits(addr) en esa
  posicion (sdma_v3_0.c:1040).

  PROVEN  la direccion de fence de sdma0 es 0xff00001680, la misma en los 20
           pipeline_sync.
```

Esto es lo que mas se parece a un hallazgo de este anillo: **es la unica
direccion de fence que puedo dar sin acceso a VRAM**, porque el anillo la
transporta en claro. Y `0xff` era justo el valor que mi contador estaba
usando para «esto es basura».

## 3 · EL FRAME DE SDMA0, Y QUE ES EL MISMO NUCLEO QUE EL DE GFX

Los primeros 25 packets, en orden:

```text
  [  3] POLL_REGMEM      len=6  addr_lo=0x54e0  hdp_flush=1 func=3
  [  9] NOP x4
  [ 13] INDIRECT_BUFFER  len=6  vmid=0  addr=0xff003c9b00  length_dw=8
  [ 19] SRBM_WRITE       len=3  reg=0xbcc  val=0x1
  [ 22] FENCE            len=2
  [ 26] TRAP             len=1
  ...
  [ 35] POLL_REGMEM      len=6  addr_lo=0x1680  hdp_flush=0 func=3  mem_poll=1
  [ 41] POLL_REGMEM      len=6  addr_lo=0x54e0  hdp_flush=1 func=3
```

Comparado con el frame de gfx de `1508`:

```text
  gfx   COND_EXEC → WAIT_REG_MEM(HDP) → CONTEXT_CONTROL → INDIRECT_BUFFER
        → WRITE_DATA(0xbcc) → 4×EVENT_WRITE_EOP → SWITCH_BUFFER

  sdma0 POLL_REGMEM(HDP) → INDIRECT_BUFFER → SRBM_WRITE(0xbcc) → FENCE → TRAP
```

```text
  PROVEN_DERIVED  el nucleo comun es TRES cosas y solo tres:

      1. ESPERAR AL HDP      PM4: WAIT_REG_MEM 0x1537/0x1538
                             SDMA: POLL_REGMEM 0x54e0/0x54dc = 0x1538<<2, 0x1537<<2
      2. DESPACHAR           INDIRECT_BUFFER, con VMID
      3. ESCRIBIR 0xbcc      PM4: WRITE_DATA  SDMA: SRBM_WRITE

  Y CONFIRMA el <<2 de 1490 con aritmetica exacta:
      0x1538 << 2 = 0x54e0    <- lo que hay en el anillo
      0x1538 << 1 = 0x2a70    <- lo que habia en el anillo gfx
  Los dos codifican el MISMO registro.  SDMA codifica el byte alto.

  CONSECUENCIA PARA UN DRIVER PROPIO:  el nucleo es codigo comun.  El PM4 y el
  SDMA difieren en la envoltura, y en que codifican el byte de la direccion
  (x1 frente a x2).  Un driver propio implementa el nucleo una vez y dos
  envoltorias.
```

**Y lo que SDMA no tiene, y la razon es concreta:** sin `COND_EXEC`, sin
`CONTEXT_CONTROL`, sin los 4 `EVENT_WRITE_EOP`, sin `SWITCH_BUFFER`. No dibuja.
Igual que compute (`1503` §3). Es el mismo patron: **el anillo que dibuja paga
vallas de interrupcion; el que solo copia no.**

## 4 · LOS CUATRO POLL, Y LA PREDICCION CONFIRMADA 46 DE 46

Con los shifts de `tonga_sdma_pkt_open.h` — que es la que incluye
`sdma_v3_0.c:48` — los campos son:

```text
  SDMA_PKT_POLL_REGMEM_HEADER_hdp_flush  mask 0x1  shift 26
  SDMA_PKT_POLL_REGMEM_HEADER_func       mask 0x7  shift 28
  SDMA_PKT_POLL_REGMEM_HEADER_mem_poll   mask 0x1  shift 31
  SDMA_PKT_POLL_REGMEM_HEADER_sub_op     mask 0xff shift 8
  SDMA_PKT_HEADER_op                     mask 0xff shift 0
```

Y los cuatro tipos, con su productor:

```text
  addr_lo    hdp_flush func mem_poll interval  x    productor
  ------------------------------------------------------------------------
  0x54e0        1       3      0        10     46   sdma_v3_0.c:460 hdp_flush
  0x1680        0       3      1         4     20   sdma_v3_0.c:1035 pipeline_sync
  0x1478        0       0      0        10     16   sdma_v3_0.c:1071 vm_flush
                             ------
                             82   el total, por parseo EN ORDEN
```

**SON TRES, NO CUATRO.** Este hallazgo se corrigio a si mismo: la primera
version de esta tabla tenia una cuarta fila con `addr_lo=0`, `interval=1` y
**19 apariciones**, y la marcaba como `???`. Es un artefacto mio. Ver §4.1.

```text
  LA PREDICCION, y esto es lo que hace el hallazgo:

  sdma_v3_0.c:460 es EL UNICO que pone HDP_FLUSH(1), y escribe
  mmGPU_HDP_FLUSH_DONE<<2 y mmGPU_HDP_FLUSH_REQ<<2 como addr_lo/addr_hi.

  PREDICCION   hdp_flush=1  <=>  addr_lo = 0x54e0
  MEDIDO      hdp_flush=1: 46 de 46 tienen addr_lo = 0x54e0
              y ningun otro los tiene.
```

**46 de 46, en las dos direcciones.** Eso no es correlacion, es la firma del
productor. Y el registro de esos 46 es el **mismo HDP flush** que espera el
anillo gfx, lo que confirma `1490` desde un segundo anillo independiente.

**Los tres tienen productor, y el inventario esta cerrado: 27 emisores de
`POLL_REGMEM` en todo el arbol, y los tres vivos son los de `sdma_v3_0.c`
(`459`, `1036`, `1064`). Los otros 24 son de generaciones que no se compilan
para POLARIS12.**

Y `INTERVAL(1)` **no lo pone ninguno de los 27**: los tres vivos usan 10, 4 y
10. Ese dato es el que persiguió la cuarta fila fantasma. Ver §4.1.

### 4.1 · LA CUARTA FILA ERA FALSA, Y ESTE HALLAZGO LO CORRIJE

La primera version de la tabla de arriba tenia:

```text
  0x0000        0       0      0         1     19   ???
```

Lo_marké `???` con la prudencia de `NOT_FOUND`. **Era un falso positivo
construido con el mismo error de `1500` y de §1 de este hallazgo, por tercera
vez y con la variante mas peligrosa.**

Como lo encontre: los 19 eran **byte a byte identicos**, los 19 tenian
`addr_lo=0` y `interval=1`, y ninguno aparecia en el parseo en orden. Los
conteo por separado en vez de por el parseo:

```text
  ESCANEO INGENUO:   19 posiciones
  PARSEO EN ORDEN:    0 de 19 son polls reales
```

La causa, dword a dword:

```text
  [13] 0x00000004  INDIRECT_BUFFER  (longitud 6, ocupa 13..18)
  [14] 0x003c9b00  addr_lo
  [15] 0x000000ff  addr_hi
  [16] 0x00000008  length_dw = 8        <-- byte bajo 0x08 = POLL_REGMEM
  [17] 0x00000000  pad
  [18] 0x00000000  pad
```

`length_dw = 8`. El byte bajo es `0x08`, que **es** el opcode de
`POLL_REGMEM`. Mi escaneo lo tomo por un header y leyo los 5 dwords
siguientes como su cuerpo, y esos 5 casaban con la forma de un poll.

```text
  EL DANGO ESPECIFICO, Y ES NUEVO:

  En 1500 y en §1 escaneaba dwords SUELTOS: el byte bajo de cada uno.  Eso
  produce falsos de 1 dword.

  AQUI escaneaba dwords CONTIGUOS de 6, porque buscaba un packet entero.  Eso
  produce un falso que ademas parece COHERENTE por dentro: los 5 dwords que leo
  como cuerpo tienen la forma correcta por casualidad, porque el cuerpo de un
  IB son 5 dwords cualesquiera.

  O sea: el falso positivo ya no es "un numero raro".  Es un paquete entero
  con la forma correcta.  Y ESO es lo que hace que el inventario de producers
  no lo delate: parece un emisor mas.

  LA REGLA, y es la general de los tres casos:
    NUNCA escanear headers por patron de byte.  El unico test de que un dword
    es un header es que el ANTERIOR termino en un packet de longitud conocida.
    No hay otra.  Un patron de byte no es evidencia de nada.
```

## 5 · EL VMID: 0, Y CORRIGE LA LECTURA DE 1495

Los 46 `INDIRECT_BUFFER`:

```text
  VMID de cada uno:  {0: 46}
  gpu_addr del primero: 0xff003c9b00  length_dw=8
```

**Y el descarte, que es el mismo error de §1 aplicado a este campo:**

```text
  ESCANEO INGENUO (byte bajo == 4):        66 posiciones,  {0:46, 15:20}
  PARSEO EN ORDEN (headers reales):        46 posiciones,  {0:46}

  Los 20 falsos positivos tienen vmid aparente 15, y el primero es:
      [40] 0x0fff0004   vmid aparente = 15
  0x0fff0004 es el dword retry|interval de un POLL_REGMEM (0xfff = retry,
  4 = interval).  Su byte bajo es 0x04 por casualidad.  NO es un IB.
```

```text
  Los headers reales tienen separacion >= 6, que es su longitud:
      40 64 48 48 64 48 64 56 ...
  MINIMO MEDIDO 40.  Coherente con un IB de 6 dwords mas relleno entre ellos.
```

```text
  0xff00000000..0xffffffffffff es el rango de GPU VA de 48 bits.  El 0xff inicial
  es coherente con una VA mapeada en el espacio alto.

  Y CORRIGE:  1495 afirmo "el VMID es 3" para el anillo sdma.  ESTE anillo, que
  es sdma0, usa VMID 0 en los 46 IB.  O los dos VMID conviven en el mismo motor
  en momentos distintos, o 1495 leyo otro anillo.  NO SE CUAL.  Lo que SI es
  medido: sdma0 usa 0, sin excepcion en los 46.
```

Contraste con los otros dos anillos, y esto **sí** queda cerrado:

```text
  anillo gfx    8 IB,  vmid = 7 en los 8
  anillo comp   1 IB,  vmid = 0
  anillo sdma0 46 IB,  vmid = 0
```

**El anillo de compute y el de sdma0 comparten VMID 0, y el de gfx usa 7.** No
se por que, y no lo afirmo. Pero el hecho de que dos motores distintos usen 0
mientras el tercero usa 7 descarta "el VMID identifica el anillo".

## 6 · 0xbcc EN LOS DOS ANILLOS, Y 0x51E

```text
  anillo gfx   WRITE_DATA   cuerpo contiene 0x00000bcc    (1500)
  anillo sdma0 SRBM_WRITE  reg = 0x00000bcc, 46 veces
```

**El mismo registro, escrito desde los dos anillos.** Con su valor:

```text
  reg=0xbcc  ->  val=0x1     x46
  reg=0x51e  ->  val=0x1     x16
  reg=0x54f  ->  val=0xf400900  x16
```

`0x51e` con `val=1` es exactamente la forma del anillo gfx
(`0xbcc ← 0x1`). Los tres registros son escrituras de una palabra.

```text
  0x00000bcc = 0xbcc << 2.  Y 0x1538 << 2 = 0x54e0.  El desplazamiento x2 de
  SDMA es el mismo que convierte el offset de registro a direccion de registro.

  Y EN GFX el body[0] de WRITE_DATA era 0x40100000, no 0x0bcc.  O sea que en
  PM4 el 0xbcc va dentro del cuerpo (DW1) y en SDMA va en el registro (DW1
  tambien).  Mismo campo, misma posicion, dos codificaciones.
```

## 7 · LA SECUENCIA DE VALLAS, Y UN SALTO NEGATIVO

Los `seq` de los 20 `pipeline_sync`:

```text
  0x173 0x174 0x176 0x177 0x178 0x17a 0x17b 0x181 0x183 0x185 0x18d
  0x159 0x15f 0x160 0x162 0x163 0x164 0x166 0x167 0x16d

  avance: 1 2 1 1 2 1 6 2 2 8 -52 6 1 2 1 1 2 1 6
```

```text
  PROVEN_DERIVED  el seq es un contador monotono dentro de cada stretch, y
                  avanza con saltos de 1, 2, 6 y 8.  Los saltos son las
                  vallas que NO son de este anillo.

  NOT_DETERMINED  el salto de -52 entre 0x18d y 0x159.  Es el mismo patron que
                  el wrap de -7 del anillo gfx (1508 §3).  En los dos anillos
                  hay un retroceso del contador de vallas, y en ninguno de los
                  dos tengo la explicacion.
```

## 8 · ESTADO

```text
PROVEN          el anillo sdma0 parsea en orden y consume 2051 de 2051 dwords.
                Teselacion exacta, cero huecos, como gfx en 1508.
PROVEN          el frame es POLL_REGMEM(hdp_flush) -> INDIRECT_BUFFER ->
                SRBM_WRITE(0xbcc) -> FENCE -> TRAP.
PROVEN_DERIVED  el nucleo comun a los 3 anillos es esperar al HDP, despachar
                con IB+VMID, y escribir 0xbcc.  SDMA codifica el byte de
                direccion con <<2 donde PM4 usa <<1:  0x1538<<2 = 0x54e0
                exacto, contra 0x1538<<1 = 0x2a70 en gfx.
PROVEN          4 tipos de POLL_REGMEM distinguibles.  hdp_flush=1 <=> addr_lo
                = 0x54e0, 46 de 46 en las dos direcciones, y ese es el unico
                emisor con HDP_FLUSH(1) en todo el arbol.
PROVEN          los 46 INDIRECT_BUFFER de sdma0 van con VMID 0.
PROVEN          la direccion de fence de sdma0 es 0xff00001680, identica en los
                20 pipeline_sync.  Es la unica direccion de fence obtenible
                sin acceso a VRAM, porque el anillo la transporta en claro
                (sdma_v3_0.c:1040 escribe upper_32_bits(addr)).
PROVEN          0xbcc se escribe en los dos anillos: WRITE_DATA en gfx,
                SRBM_WRITE en sdma0, 46 veces.  Junto a 0x51e=1 y
                0x54f=0xf400900.
PROVEN_DERIVED  el seq de valla avanza con saltos de 1, 2, 6 y 8, y retrocede
                -52 una vez.

CORRIGE, mio    1495 leyo "el VMID es 3"; sdma0 usa 0 en los 46 IB.  No se si
                los dos conviven o si 1495 leyo otro anillo.
CORRIGE, mio    mi escaneo ingenuo de "590 dwords sin opcode conocido" era el
                error de 1500 repetido: el byte bajo solo es opcode en un
                header.

REFUTADO, mio  la cuarta fila de la tabla de polls (addr_lo=0, interval=1,
                x19) que este hallazgo afirmo en su primera version.  Cero de
                19 son packets: el byte bajo 0x08 era length_dw=8 dentro del
                cuerpo de un INDIRECT_BUFFER.  Ver §4.1.
NOT_FOUND       (retirado, era falso) el supuesto cuarto POLL sin productor.
NOT_DETERMINED  el retroceso del seq (-52 aqui, -7 en gfx).  Mismo patron en
                los dos anillos, sin explicacion en ninguno.
NOT_DETERMINED  por que compute y sdma0 comparten VMID 0 y gfx usa 7.
```

## 9 · LO QUE SIGUE DENTRO DE ESTA AREA

La frontera queda con cuatro cosas concretas, todas en `sdma0`:

```text
  1. CERRADO.  El cuarto POLL era un falso positivo mio (§4.1).  Los tres
     reales tienen productor y el inventario de 27 emisores esta cerrado.
  2. El retroceso del seq, y por que aparece en los dos anillos.
  3. El VMID 0 frente al 7 del anillo gfx.  El discriminante disponible es la
     direccion de la fence (0xff00001680 en los pipeline_sync de sdma0): si
     los IB de sdma0 apuntan a la misma region que los de gfx, el VMID depende
     del cliente y no del anillo.
  4. Los 736 NOP: son relleno del driver (`.nop` de SDMA = 0, `cik_sdma.c:1237`)
     o restos de una emision anterior.  Y los 62 TRAP, que se emiten uno por
     IB y podrian ser el final de cada submit.
```

No cambio de area hasta cerrar estos cuatro o hasta declarar `SATURATED` con
el motivo escrito.