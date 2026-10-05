# 1488 — No son tres copias: son tres protocolos de anillo distintos, hay una cuarta que ni toca el registro, y el `POLL_REGMEM` del driver aparece 16 veces en la tarjeta real, byte a byte

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

CIERRA      el NOT_DETERMINED de 1486: "son tres copias o uno con #define".
            NINGUNA DE LAS DOS.  Son tres implementaciones distintas del
            mismo efecto, en tres protocolos de anillo diferentes.
DESCUBRE    una CUARTA funcion que hace flush de VM sin tocar
            mmVM_INVALIDATE_REQUEST:  uvd_v6_0_enc_ring_emit_vm_flush, que
            habla con el codificador HEVC.
CONFIRMA    1486 y 1411 contra el ARTEFACTO REAL, no solo contra el fuente.
            16 POLL_REGMEM con la forma exacta de sdma_v3_0.c:1064-1072.
ESTADO     PROVEN.  El codigo se ejecuta en esta tarjeta, medido en el anillo.
```

## 0 · LA PREGUNTA QUE 1486 DEJÓ ABIERTA

`1486` terminó con:

```text
  NOT_DETERMINED  si los tres son copias o uno con #define.  No lo mire.
```

La pregunta era por el **coste de reimplementación**: si es una macro, hay un
código; si son tres copias, hay tres. Es la razón por la que se preguntó.

## 1 · LA RESPUESTA: NINGUNA DE LAS DOS

Las cuatro funciones, leídas completas:

```text
  1. gfx_v8_0.c:6197   gfx_v8_0_ring_emit_vm_flush
       amdgpu_gmc_emit_flush_gpu_tlb(ring, vmid, pd_addr)
       PACKET3(PACKET3_WAIT_REG_MEM, 5)
       WAIT_REG_MEM_OPERATION(0) | FUNCTION(0) | ENGINE(0)
       mmVM_INVALIDATE_REQUEST        <- registro DIRECTO, sin <<2
       0  0  0  0x20                  <- ref, mask, poll interval
       y un PFP_SYNC_ME si es anillo GFX

  2. sdma_v3_0.c:1058  sdma_v3_0_ring_emit_vm_flush
       amdgpu_gmc_emit_flush_gpu_tlb(ring, vmid, pd_addr)
       SDMA_PKT_HEADER_OP(SDMA_OP_POLL_REGMEM) | HDP_FLUSH(0) | FUNC(0)
       mmVM_INVALIDATE_REQUEST << 2   <- registro DESPLAZADO
       0  0  0  RETRY(0xfff)|INTERVAL(10)

  3. uvd_v6_0.c:1077    uvd_v6_0_ring_emit_vm_flush
       amdgpu_gmc_emit_flush_gpu_tlb(ring, vmid, pd_addr)
       PACKET0(mmUVD_GPCOM_VCPU_DATA0, 0)
       mmVM_INVALIDATE_REQUEST << 2
       PACKET0(mmUVD_GPCOM_VCPU_DATA1, 0)
       0
       PACKET0(mmUVD_GP_SCRATCH8, 0)
       1 << vmid            <- MASK REAL, NO CERO
       PACKET0(mmUVD_GPCOM_VCPU_CMD, 0)
       0xC

  4. uvd_v6_0.c:1137    uvd_v6_0_enc_ring_emit_vm_flush      <-- NUEVA
       HEVC_ENC_CMD_UPDATE_PTB ; vmid ; pd_addr >> 12
       HEVC_ENC_CMD_FLUSH_TLB ; vmid
       NO ESCRIBE mmVM_INVALIDATE_REQUEST.  No aparece.
```

```text
  LO QUE HAY ENTRE ELLAS:
    - tres formatos de paquete distintos: PM4 PACKET3, SDMA packet, UVD mailbox
    - el registro va DIRECTO en el gfx y DESPLAZADO <<2 en los otros dos
    - el gfx anade un PFP_SYNC_ME condicional; los otros dos no
    - UVD pone una mask REAL (1 << vmid); SDMA y gfx ponen 0

  Y LA CUARTA NO ES UNA VARIANTE: es otro protocolo entero (HEVC).
```

**El mask=0 de `1411` no es "el driver no inicializa".** En el anillo UVD el
driver **sí** escribe una mask con el bit del VMID. La afirmación de `1411`
—que aplica al camino gfx/sdma— es correcta y no se puede extender a UVD.

## 2 · EL HALLAZGO DE FONDO: CONTAR ESCRITORES NO ES CONTAR ACCIONES

`1486` contó autores de `mmVM_INVALIDATE_REQUEST` y llegó a 6 vivos. Esos 6
escriben el registro, sí, pero **solo 3 de ellos escriben un WAIT**. Y la
cuarta función hace la invalidación sin escribir el registro.

```text
 writers de mmVM_INVALIDATE_REQUEST   vivos: 6     (1486)
 de los cuales, ademas esperan:              2     (gfx y sdma)
 flush de VM sin escribir el registro:       1     (uvd enc, via HEVC)

  El conjunto "acciones de invalidacion" no es un subconjunto de "escritores
  del registro", ni al reves.  Son dos conjuntos que se solapan en 5 de 6.

  Y para un driver propio la consecuencia es operativa: no basta con saber
  quien escribe el registro.  Hay que saber quien MAS lo escribe cuando el
  anillo no es el de graficos.
```

## 3 · CONTRA EL ARTEFACTO REAL, NO SOLO CONTRA EL FUENTE

Esta es la parte que `1486` no pudo hacer, y `1441` la pidio: ¿existe ese
`POLL_REGMEM` en la tarjeta?

Layout del header, leído de `tonga_sdma_pkt_open.h:1957-1975` (el que incluye
`sdma_v3_0.c:48`, y `SDMA_OP_POLL_REGMEM = 8` en la línea 33):

```text
   op       bits [7:0]        sub_op    bits [15:8]
   hdp_flush  bit 26          func      bits [30:28]
   mem_poll   bit 31
```

MEDIDO sobre los dos anillos SDMA capturados:

```text
  POLL_REGMEM con la firma del driver (RETRY=0xfff, INTERVAL=10)   125
    con la FORMA EXACTA de sdma_v3_0.c:1064-1072                     16
    con otra forma (func=3, poll sobre memoria)                    109
```

Los 16, byte a byte:

```text
  dw0 = 0x00000008   op=POLL_REGMEM, sub_op=0, hdp_flush=0, func=0 (always)
  dw1 = 0x00001478   mmVM_INVALIDATE_REQUEST << 2
  dw2 = 0x00000000
  dw3 = 0x00000000
  dw4 = 0x00000000
  dw5 = 0x0fff000a   RETRY_COUNT=0xfff, INTERVAL=10
```

**Es literalmente lo que escribe `sdma_v3_0.c:1064-1072`, en ese orden.** Y
`func=0` es el campo que `1411`dice que hace que no espere: está presente 16
veces en la tarjeta real.

Los otros 109 son `func=3` (mayor o igual) sobre `0x000054dc >= 0x00000400`, que
es un poll de memoria, no un poll de registro. Otro código.

```text
  PROVEN_DERIVED  el camino de sdma_v3_0.c se EJECUTA en esta tarjeta.
                  No es una rama teorica: aparece 16 veces en el anillo
                  capturado.

  Y con esto 1411 pasa de "el codigo parece no esperar" a
  "el codigo espera con func=0 sobre un valor que nunca va a cambiar, y lo
  hace 16 veces por captura".  La segunda frase es medible; la primera era
  una inferencia.
```

## 4 · TRES ERRORES PROPIOS, Y UNO ES DE LA MISMA CLASE QUE 1484

**4.1 · Busqué `POLL_REGMEM` como `0x10`.** El valor es `8`. Lo suposé en vez de
leerlo, y salí con "0 apariciones" en los anillos SDMA. Volví a la fuente y
`SDMA_OP_POLL_REGMEM 8` estaba en la línea 33.

**4.2 · Leí los campos del paquete por índice equivocado.** Con la firma
`0x0fff000a` en el dword `i`, leí `dw[i-3], dw[i-2], dw[i-1]` como
address/value/mask — y salía `0, 0, 0`, que **contradecía** al fuente. El
bloque empieza en `i-5`, no en `i-3`. Con los offsets correctos aparece
`0x1478`.

**Este es el que importa, y es `1484` repetido:** el error producía un `0` donde
el código escribe un valor no nulo. Es una contradicción entre artefacto y
fuente, y la resuelví **a favor del artefacto**, porque la fuente se puede leer
y el artefacto no se puede suponer. Cuando dos fuentes discrepan, la que se
puede releer gana.

**4.3 · `func=0` y `func=3` los leí como el mismo paquete.** En el corpus AMD,
`func` es el modo de comparación del poll (`0=always, 1=&, 2=~, 3=>=`). Confundir
`func=3` con el del driver infla el recuento por 7×. Salió al mirar los campos
declarados en vez de contar ocurrencias de un literal.

## 5 · LO QUE QUEDA ABIERTO, Y ES POCO

```text
NOT_DETERMINED  si el POLL_REGMEM con func=0 y mask=0 retorna o se queda
                esperando.  Eso es lo que 1411 plantea y NO lo responde el
                anillo: un anillo capturado es un instante, y no dice si el
                poll salio.  Necesita runtime, que sigue bloqueado por
                credenciales.
                PERO la pregunta tiene ahora una arista que no tenia: se
                puede buscar en el anillo el paquete POLL_REGMEM que
                EMITE, y si nunca aparece en una captura larga, es que no
                vuelve.  Eso no lo he medido.

NOT_DETERMINED  por que el anillo UVD escribe una mask real y los otros dos
                escriben 0.  Es una asimetria entre tres implementaciones del
                mismo efecto, y puede ser intencionada (UVD no tiene PFP y
                necesita sincronizar) o puede ser que una de las tres este mal.
                Es una pregunta de hardware, no de codigo.

ABRE            los 16 son en sdma0 y 0 en sdma1.  No hay razon para que un
                anillo use el flush de VM y el otro no, salvo que uno de los
                dos no tenga paginas.  No lo sigo: es una pregunta de runtime.
```

## 6 · ESTADO

```text
PROVEN          4 funciones de flush de VM en codigo vivo, no 3, y no son
                copias: 3 protocolos distintos (PM4 / SDMA / UVD mailbox)
                mas un cuarto via HEVC que no toca el registro
PROVEN          solo 2 de las 3 que escriben el registro ADEMAS esperan
PROVEN          el camino de sdma_v3_0.c se ejecuta: 16 POLL_REGMEM con su
                forma exacta en el anillo capturado
CONFIRMA        1411 con dato de hardware, y corrige su alcance: el mask=0 no
                se extiende al anillo UVD, que escribe 1 << vmid
CORRIGE         1486: 6 autores del registro no son 6 acciones de flush
NOT_DETERMINED  si el poll con func=0 y mask=0 retorna.  Un anillo es un
                instante y no lo dice.  Runtime, bloqueado.

REFUTADO, mio   leí la direccion del poll por indice equivocado y obtuve un 0
                donde el codigo escribe 0x1478.  Tercera vez esta sesion que
                un error de indice ME da un cero plausible.  Se resuelve a
                favor del artefacto, que es releible, contra la fuente, que
                tambien: pero el artefacto no se puede suponer.
```
