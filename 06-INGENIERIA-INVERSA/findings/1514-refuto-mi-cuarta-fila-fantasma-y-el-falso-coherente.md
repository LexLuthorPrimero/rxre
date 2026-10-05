# 1514 — Cierro la cuarta fila fantasma de `1512`: los 19 «polls sin productor» eran un `length_dw` leído como header. Y la regla que sale de eso es más fuerte que las anteriores

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

AREA FIJADA    sdma0.  No se cambia hasta cerrar o escribir SATURATED.

REFUTA, mio    1512 tabla de polls: la cuarta fila (addr_lo=0, interval=1,
               x19) no existe.  CERO de 19 son packets.
CIERRA         el anillo sdma0: 3 tipos de POLL_REGMEM, 3 productores, y el
               inventario de 27 emisores del arbol.  Cero piezas sin dueño.
DESCUBRE       el modo de fallo mas peligroso de la serie: el falso positivo
               que ademas es COHERENTE POR DENTRO y parece un emisor mas.
PROVEN         los 82 POLL_REGMEM del anillo tienen los 3 productores que
              sdma_v3_0.c declara, y sus intervalos son 10, 4 y 10.
```

## 0 · QUE TENIA PENDIENTE, Y QUE HIZO

`1512` §9 dejo cuatro cosas dentro de `sdma0`. La primera era:

```text
  1. El cuarto POLL (addr_lo=0, interval=1, x19).  Buscar en las cabeceras
     generadas, con inventario cerrado.  Es la unica pieza del anillo sin
     productor.
```

Y en `1512` §8, con prudencia:

```text
  NOT_FOUND  el cuarto POLL ... no tiene productor en el arbol.  No he
             terminado de mirar las cabeceras generadas de otras generaciones,
             asi que no es PROVEN_ABSENT.
```

Bien marcado. **La prudencia era correcta y por eso se pudo deshacer en vez de
defenderse.** Buscar primero, luego concluir: si hubiera escrito
`PROVEN_ABSENT`, este hallazgo seria un ataque a un claim mio en vez de una
correccion de una cuenta.

## 1 · EL INVENTARIO CERRADO: 27 EMISORES, Y NINGUNO PONE INTERVAL(1)

```bash
$ grep -rn "SDMA_OP_POLL_REGMEM\|SDMA_OPCODE_POLL_REG_MEM" *.c
```

Inventario completo, sin limitador:

```text
  cik_sdma.c        257  827  856              <- generico, no compila para POLARIS12
  sdma_v2_4.c       283  763  791
  sdma_v3_0.c       459 1036 1064              <- VIVOS, los 3
  sdma_v4_0.c       833
  sdma_v4_4_2.c     400
  sdma_v5_0.c       499 1267 1308
  sdma_v5_2.c       348 1167 1206 1229
  sdma_v6_0.c       333 1173 1211 1234
  sdma_v7_0.c       335 1192 1234
  sdma_v7_1.c      1198 1239
                             = 27 emisores
```

Y los intervalos:

```bash
$ grep -rnE "SDMA_PKT_POLL_REGMEM_DW5_INTERVAL" *.c
```

```text
  POLL_REGMEM_DW5_INTERVAL(4)     x 8
  POLL_REGMEM_DW5_INTERVAL(10)    x14
  POLL_REGMEM_DW5_INTERVAL(inv)   x 2   (v4_0.c:849, v4_4_2.c:416)
                                   ---
                                   24 declaraciones de intervalo
```

```text
  Las 2 de VPE (amdgpu_vpe.c:594 y :620) usan otro macro, VPE_CMD_*, que es un
  motor distinto.  Las dejo aparte y no las cuento.

  INTERVAL(1)   NINGUNO.  0 de 24.
```

```text
  PROVEN  ningun emisor de POLL_REGMEM en todo el arbol pone INTERVAL(1).  Con
          inventario cerrado de 27 emisores y 24 declaraciones de intervalo,
          con estos tres valores y solo estos tres.

  Y los tres vivos de POLARIS12 usan 10, 4 y 10, que es EXACTAMENTE lo que
  miden los 82 polls del anillo.
```

Si los 19 fuesen reales, el intervalo 1 no tendria quien lo emitiera. Eso ya
debia haberme hecho sospechar antes de mirar el anillo.

## 2 · LA CUARTA FILA, Y COMO LA MATÉ

Los 19, byte a byte:

```text
  hdr      addr_lo addr_hi  seq      mask      last
  0x00000008 0x000000 0x00000000 0xf000000e 0x00000bcc 0x00000001
```

Los 19 identicos. Sin excepcion. Eso es lo primero que me hizo mirar el
contexto en vez de contar:

```text
  ESCANEO INGENUO:   19 posiciones
  PARSEO EN ORDEN:    0 de 19 son polls reales
```

La causa, dword a dword:

```text
  [13] 0x00000004   INDIRECT_BUFFER   (longitud 6, ocupa 13..18)
  [14] 0x003c9b00   addr_lo
  [15] 0x000000ff   addr_hi
  [16] 0x00000008   length_dw = 8      <-- byte bajo 0x08 = POLL_REGMEM
  [17] 0x00000000   pad
  [18] 0x00000000   pad
  [19] 0xf000000e   SRBM_WRITE reg=0xf000000e   <- el packet REAL que sigue
```

**`length_dw = 8`.** Su byte bajo es `0x08`, que es el opcode de
`POLL_REGMEM`. Mi escaneo lo tomo por un header, leyo los 5 dwords siguientes
como su cuerpo, y esos 5 casaban con la forma de un poll: `addr=0`,
`addr_hi=0`, `ref`, `mask`, `retry|interval`.

```text
  Y fíjate en el detalle que lo hace ENDIABADO:  el "last" que leí es
  0x00000001, que parece retry=0 interval=1.  Y [20] es 0x00000001 de verdad,
  el VALOR del SRBM_WRITE que empieza en [19].  El falso poll se comio el valor
  del SRBM real siguiente y lo leyo como su intervalo.

  Es decir: el falso no solo es coherente, es coherente ROBANDO el campo
  correcto del packet siguiente.
```

## 3 · EL MODO DE FALLO, Y POR QUE ESTE ES EL PEOR DE LA SERIE

Tres veces he escaneado headers por patron de byte. Esta es la tercera, y
la variante es peor:

```text
  1500    escaneo de dwords SUELTOS por byte bajo.
          Un dword de cuerpo tiene 1/256 de parecer un header.
          El falso es de 1 dword.  Visible.

  1512 §1 lo mismo, y salio "590 de 2051 sin opcode conocido".
          Visible.  Lo detects por lo absurdo del numero.

  1514    escaneo de SECUENCIAS CONTIGUAS de 6 dwords, buscando un packet
          entero.  El falso es un PAQUETE ENTERO, y ademas su cuerpo tiene la
          forma correcta, porque el cuerpo de un IB son 5 dwords cualesquiera
          y los que leo son los de un IB real.

          INVISIBLE.
```

**Por qué el inventario de productores no lo delata.** Porque el falso
*parece un emisor más*. Una cuarta firma con su propio intervalo, su propia
dirección y su propio intervalo de reintento. Contra un inventario cerrado de 27
emisores, un emisor falso convence igual que uno verdadero: cumple el mismo
contrato.

Y por eso el inventario, que era miorgán de Against `PROVEN_ABSENT`,resultó
inutil contra esto. **Un patrón no es evidencia de nada.**

```text
  LA REGLA, y creo que esta es la definitiva de la serie:

    EL UNICO TEST DE QUE UN DWORD ES UN HEADER ES QUE EL DWORD ANTERIOR
    TERMINO EN UN PACKET DE LONGITUD CONOCIDA.

    No hay segundo test.  Ni el valor, ni el opcode, ni la forma del cuerpo,
    ni que el cuerpo "parezca" coherente.

    Por lo tanto: NUNCA escanear. siempre avanzar.  El escaneo es un atajo
    que produce falsos que parecen verdad, y el unico sintoma es que el
    recuento es raro.

  Y esto cierra 1512 entero, porque el parseo EN ORDEN ya era correcto:
      1512 §2  packets=1066, consumidos=2051 de 2051   <- esto es lo bueno
      1512 §4  los 19 polls con addr_lo=0              <- esto era basura

  El mismo hallazgo las contenia a las dos, y no lo vi, porque estan en
  secciones distintas y una es 4ta columna de una tabla.
```

## 4 · EL ANILLO QUEDA CERRADO

```text
  1066 packets, 2051 de 2051 dwords, cero huecos
    NOP               736
    POLL_REGMEM        82   -> 3 tipos, 3 productores, intervalos 10/4/10
    SRBM_WRITE         78   -> reg 0xbcc x46, 0x54f x16, 0x51e x16
    FENCE              62
    TRAP               62
    INDIRECT_BUFFER    46   -> vmid 0, los 46
```

```text
  CERO piezas del anillo sin dueño.  Cada tipo de packet tiene su productor en
  sdma_v3_0.c, y los seis tipos que no aparecen tienen 0 apariciones medidas,
  que es un recuento y no una ausencia.
```

## 5 · ESTADO

```text
PROVEN          el inventario de emisores de POLL_REGMEM es de 27 en todo el
                arbol, y solo 3 son de la generacion de POLARIS12
                (sdma_v3_0.c:459, 1036, 1064).
PROVEN          ningun emisor del arbol pone INTERVAL(1).  0 de 24
                declaraciones de intervalo (14 de 10, 8 de 4, 2 de inv).
PROVEN          los 82 POLL_REGMEM del anillo tienen addr_lo 0x54e0 (x46),
                0x1680 (x20) y 0x1478 (x16), con intervalos 10, 4 y 10, que
                son los de los tres productores vivos.
REFUTADO, mio  1512 tabla de polls, cuarta fila: addr_lo=0, interval=1, x19.
                Cero de 19 son packets.  El byte bajo 0x08 era length_dw=8
                dentro del cuerpo de un INDIRECT_BUFFER, y el "interval=1" era
                el valor del SRBM_WRITE siguiente.
PROVEN          el anillo sdma0 queda cerrado: 1066 packets, 2051 de 2051
                dwords, cero piezas sin productor.

DESCUBRE        el modo de fallo mas peligroso de la serie: un falso positivo
                de escaneo que es un PAQUETE ENTERE con el cuerpo coherente,
                porque el cuerpo de un packet real son 5 dwords cualesquiera.
                Invisible al inventario de productores.

CONFIRMA        la regla de 1502/1506: un inventario cerrado no salva de un
                falso positivo, porque el falso cumple el mismo contrato que
                un emisor verdadero.  Solo salva de un PROVEN_ABSENT.
```

## 6 · LO QUE SIGUE DENTRO DE ESTA AREA

De las cuatro cosas de `1512` §9, la primera queda cerrada. Quedan tres, y las
tres son de la misma familia: **por qué los numeros se mueven asi.**

```text
  2. El retroceso del seq (-52 aqui, -7 en gfx).  Mismo patron en los dos
     anillos, sin explicacion en ninguno.  Y los saltos de +2, +6, +8.
  3. El VMID 0 frente al 7 del anillo gfx.  Discriminante disponible: si los
     IB de sdma0 apuntan a la misma region que los de gfx, el VMID depende del
     cliente y no del anillo.
  4. Los 736 NOP: relleno del driver (.nop de SDMA = 0) o restos.
```

Y hay una quinta que solo se ve ahora que el anillo esta cerrado:

```text
  5. Los 46 INDIRECT_BUFFER van con vmid=0 y sus gpu_addr empiezan en 0xff00.
     Y los 20 pipeline_sync usan fence 0xff00001680.  El prefijo 0xff es el
     mismo.  Eso sugiere un unico espacio de direcciones para todo el anillo,
     y por tanto que los 46 IB son del mismo cliente.
```

No cambio de area hasta cerrar estos cinco o hasta declarar `SATURATED` con el
motivo escrito.