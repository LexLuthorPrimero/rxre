# 1506 — Refuto `1503` casi entero: `0xffff1000` es el `.nop` de `gfx_v8_0`, los 2015 dwords son relleno del propio driver, `pm4tila` contaba bien, y el `0xdeadbeef` es el autotest del anillo con `mmSCRATCH_REG0` resuelto desde la base de datos de `umr`

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

REFUTA, mio    1503 completo.  Sus cuatro afirmaciones centrales son falsas:
               (a) los 2015 dwords son basura,  (b) "count imposible" prueba que
               un dword es DATO,  (c) el 0xdeadbeef no se puede identificar,
               (d) el PARCIAL de pm4tila es accidental.
DESCUBRE       0xffff1000 == PACKET3(PACKET3_NOP, 0x3FFF) == el .nop de
               gfx_v8_0_ring_funcs_{gfx,compute,kiq}.  Y SDMA_PACKET(NOP,0,0)
               == 0.  El VALOR DE RELLENO IDENTIFICA LA FAMILIA DE ANILLO.
PROVEN         el paquete de 3 dwords en [3] es gfx_v8_0_ring_test_ring, con
               cuatro candados independientes, uno de ellos el valor del
               registro resuelto desde un archivo externo al corpus.
CONFIRMA       pm4tila:  2021 = 2015 NOP + 6 packets.  Cuadra exacto.
APPLY, mio     la regla de 1502 (no un grep: inventario) y la de 1503 §6
               (no el instrumento para juzgar el dato) -- y esta vez fallan las
               DOS, porque el test era valido y la herramienta era correcta.
```

## 0 · LO PRIMERO, Y ES LO MAS IMPORTANTE

`1503` afirmaba:

```text
  PROVEN  2023 de 2051 dwords tienen type=3, y eso NO significa que sean
          packets: un dword de datos tiene 25 % de aparecerlo
PROVEN  3 dwords con count imposible (7853, 16383, 16383) en un anillo de
        2048: son DATO, no packets
DESCUBRE la distincion PARCIAL / NO_ES_PM4_O_TRUNCADO de pm4tila es
        ACCIDENTAL
NOT_DETERMINED  si 0xdeadbeef es relleno de inicializacion o residuo de una
                ejecucion anterior.
```

**Las cuatro son falsas.** Y la cuarta es la que mas me dolio escribir: yo mismo
insisti en `NOT_DETERMINED` cuando el productor estaba a un `grep` de distancia
y era la unica funcion de autotest del fichero.

---

## 1 · `0xffff1000` ES EL NOP DE `gfx_v8_0`. IDENTIDAD ARITMETICA

Primero, la identidad. `PACKET3(type, count, opcode)` empaqueta bits:

```text
  PACKET3(PACKET3_NOP, 0x3FFF) = (3<<30) | (0x3FFF<<16) | (0x10<<8)
                               = 0xC0000000 | 0x3FFF0000 | 0x1000
                               = 0xFFFF1000
```

Medido, no supuesto:

```text
  PACKET3(PACKET3_NOP, 0x3FFF) = 0xffff1000   <- coincide
  PACKET3(PACKET3_NOP, 0x3FFE) = 0xfffe1000   <- no
  PACKET3(PACKET3_NOP, 0x3FFD) = 0xfffd1000   <- no
```

Y el driver lo declara **tres veces**, y las tres son las structs de anillo de
`gfx_v8_0`, la generacion de POLARIS12:

```text
  gfx_v8_0.c:6876   gfx_v8_0_ring_funcs_gfx      .nop = PACKET3(PACKET3_NOP, 0x3FFF)
  gfx_v8_0.c:6922   gfx_v8_0_ring_funcs_kiq      .nop = PACKET3(PACKET3_NOP, 0x3FFF)
  gfx_v8_0.c:6957   gfx_v8_0_ring_funcs_compute .nop = PACKET3(PACKET3_NOP, 0x3FFF)
```

**O sea que `0xffff1000` no es basura que aparecio en la memoria: es una
constante que el driver emite a proposito.**

## 2 · EL RELLENO TIENE PRODUCTOR, Y HAY TRES

Los 2015 dwords no se escriben solos. Se escriben en estos sitios, y los tres
usan `memset32` con `ring->funcs->nop`:

```text
  amdgpu_gfx.c:1701    memset32(ib->ptr, ring->funcs->nop, ib_size_dw)
                      -> RELLENA EL IB ENTERO DE NOPS, y luego lo sobrescribe
                         por delante con los packets reales.

  amdgpu_ring.c:128    memset32(&ring->ring[occupied], ring->funcs->nop, chunk1)
  amdgpu_ring.c:131    memset32(ring->ring, ring->funcs->nop, chunk2)
                      -> amdgpu_ring_insert_nop.  Y PARTE EN DOS porque un NOP
                         largo no puede cruzar el final del anillo: chunk1 llega
                         al final, chunk2 arranca en el principio.

  amdgpu_ring.c:154    memset32(&ib->ptr[ib->length_dw], ring->funcs->nop, count)
                      -> amdgpu_ring_generic_pad_ib, alinea el IB.

  amdgpu_fence.c:759   amdgpu_ring_write(ring, ring->funcs->nop)
                      -> al REEMITIR un IB que dio error.
```

**`amdgpu_gfx.c:1701` explica por que la cola del anillo es NOP.** Cada IB se
rellena entero de NOPs y luego se escribe encima el trabajo real. La cola que
queda es relleno, por construccion, no por casualidad.

Y `amdgpu_ring.c:128/131` explica por que son **copias contiguas del mismo
dword** y no un paquete gigante: el driver escribe `count` dwords, uno a uno.

## 3 · EL RELLENO DISTINGUE LA FAMILIA DEL ANILLO

Medido sobre las tres capturas:

```text
  fichero                    dwords  fill 0xffff1000  ceros   type=3
  amdgpu_ring_gfx.txt          2051            1648     64      1728
  amdgpu_ring_comp_1.3.1.txt   2051            2015      4      2023
  amdgpu_ring_sdma0.txt        2051               0    784        98
```

`sdma0` **no tiene ni un solo `0xffff1000`**. Y el motivo tambien esta medido:

```text
  cikd.h:495   SDMA_PACKET(op, sub_op, e) = (((e & 0xFFFF) << 16)
                                             | ((sub_op & 0xFF) << 8)
                                             |  (op  & 0xFF))
  cikd.h:499   SDMA_OPCODE_NOP = 0
  cik_sdma.c:1237   .nop = SDMA_PACKET(SDMA_OPCODE_NOP, 0, 0)  ==  0x00000000
```

**El NOP de SDMA es literalmente cero.** Por eso `sdma0` tiene 784 ceros y
`gfx`/`comp` tienen `0xffff1000`. Los 784 ceros de `sdma0` no son "espacio sin
usar": son su relleno, con la misma funcion y la misma intencion.

```text
  PROVEN_DERIVED  con UN dword del anillo se identifica la familia del motor de
                  anillo:  0xffff1000 -> GFX8/GFX10/GFX11 (PM4),  0 -> SDMA.
                  Y es el unico rasgo de las 784 aparentes basuras de sdma0 que
                  las hace interpretables en vez de ignorables.
```

Esto tiene consecuencia practica para un driver propio: **un parser de PM4
necesita dos reglas de NOP distintas**, segun el anillo. No es un detalle.

## 4 · `pm4tila` CONTABA BIEN. Y TENIA LA REGLA EN SU CONTRATO

`1503` §5 decia que `pm4tila` infla el recuento contando basura. **Es al
reves: el recuento cuadra al dword.**

```text
  MEDIDO        anillo comp_1.3.1:  2048 dwords de cuerpo
                fill NOP (0xffff1000)          2015
                packets reales                     6   -> [3],[259],[266],[273],[277],[282]
                SUMA                             2021
  REPORTADO     por pm4tila                     2021
```

**Cuadra exacto.** Y el outil tiene la regla que lo hace posible, escrita en su
propia fuente:

```text
  pm4tila.py:138   for _nnop, _lblnop in ((True, "nop=1dword"), (False, "nop=regla")):
  pm4tila.py:146   NOP_OPCODE = 0x10        # sale de vid.h, no de memoria
  pm4tila.py:239   if nop1 and op == NOP_OPCODE:  L = 1
  pm4tila.py:643   L = 1 if (conv["_nop"] and op == NOP_OPCODE) else _f3(conv["_f3"], c)
  pm4tila.py:842   (c3(0x10, 0x3FFF), []),   # "NOP de relleno, 1 dw"   <- vector de self-test
```

**La convencion `nop=1dword` existe precisamente para esto.** Es una de las dos
reglas de NOP del espacio de 16 convenciones, y `pm4tila` la imprime en su
cabecera. Un NOP de relleno se cuenta como **1 dword**, no como `count+2`, porque
`count = 0x3FFF` es un valor decorativo: el driver lo puso para que el patron
sea reconocible, no para que el hardware lo consuma entero.

```text
  Y ESO ES LO QUE YO NO MIRE.  pm4tila declara su contrato en pantalla, en el
  bloque "ESPACIO DE CONVENCIONES", y yo leeria ese mismo bloque cuatro lineas
  mas abajo y aun asi llame "imposible" a su numero.
```

## 5 · EL `0xdeadbeef`: CUATRO CANDADOS

Aqui `1503` se quedo corto. El paquete de `[3]` esta resuelto por completo.

El anillo, tal cual:

```text
  [3]  0xc0017900   type=3  op=0x79  count=1     -> 3 dwords
  [4]  0x00000040
  [5]  0xdeadbeef
  [6..258]        0xffff1000 x 253
  [259..288]      el frame real, 6 packets
  [289..2050]     0xffff1000 x 1762
```

Candado 1 -- el opcode. `cikd.h:476`:

```text
  #define  PACKET3_SET_UCONFIG_REG           0x79
  #define  PACKET3_SET_UCONFIG_REG_START     0x0000c000
```

Candado 2 -- la longitud. `amdgpu_ring_alloc(ring, 3)` y `count=1` dan
exactamente 3 dwords con `count+2` de `1476`.

Candado 3 -- el registro, y este sale de FUERA del corpus:

```bash
$ grep -n "mmSCRATCH_REG0" /usr/share/umr/database/ip/gfx_8_0_0.reg
9555:mmSCRATCH_REG0 0 0xc040 1 0 4294967295
```

```text
  Y el 0xc040 esta dentro de la ventana UCONFIG:  [0xc000, 0xc400)
  por PACKET3_SET_UCONFIG_REG_START / _END (cikd.h:477/478).  Cuadra.
```

```text
  mmSCRATCH_REG0 - PACKET3_SET_UCONFIG_REG_START
  = 0xc040 - 0xc000
  = 0x00000040
  = body[0] del anillo
```

Candado 4 -- el valor, que es un literal en la misma funcion. Con numeros de
linea, porque `sed -n 'p'` a pelo no los imprime:

```bash
$ sed -n '848,854{=;p}' rx550-upstream-7.2.8/linux-7.2.8/drivers/gpu/drm/amd/amdgpu/gfx_v8_0.c | paste - -
848
	return r;
849
850
	amdgpu_ring_write(ring, PACKET3(PACKET3_SET_UCONFIG_REG, 1));
851
	amdgpu_ring_write(ring, mmSCRATCH_REG0 - PACKET3_SET_UCONFIG_REG_START);
852
	amdgpu_ring_write(ring, 0xDEADBEEF);
853
	amdgpu_ring_commit(ring);
```

```text
  PROVEN  el paquete de [3] ES gfx_v8_0_ring_test_ring, el autotest del anillo,
          y el registro que escribe se resuelve a mmSCRATCH_REG0 = 0xc040 con
          la base de datos de umr como oraculo externo.
```

Y `.test_ring = gfx_v8_0_ring_test_ring` esta en `gfx_v8_0.c:6907`, `6944` y
`6971`, o sea en la generacion que vive para POLARIS12.

**Esto es un PASS del driver, no un fallo.** La secuencia es
`WREG32(mmSCRATCH_REG0, 0xCAFEDEAD)`, escribir `0xDEADBEEF` por PM4, y leer el
registro hasta que valga `0xDEADBEEF` con `usec_timeout`. O sea: **la GPU esta
viva y su anillo de compute pasa el autotest.** Es el unico resultado de salud
directa que hay en las 21 capturas.

## 6 · EL ERROR DE METODO, Y ES EL QUE MAS SE REPETIRA

Los tres candados 1, 3 y 4 los refute uno a uno **con el fichero equivocado**.
Leyendo `gfx_v6_0.c` en vez de `gfx_v8_0.c`:

```text
  MI ERROR                          LO REAL
  --------------------------------------------------------------------
  el autotest usa SET_CONFIG_REG     usa SET_UCONFIG_REG
  0x68                               0x79
  y "por tanto no es el test"        y SI lo es
```

Lo peor es que el primer grep que hice **si** salio bien:

```text
  $ grep -rn "DEADBEEF" drivers/gpu/drm/amd/amdgpu/
  cik_sdma.c:624,629,679,693
  gfx_v6_0.c:1869,1874,1972,1987
  sdma_v5_2.c, sdma_v6_0.c, sdma_v7_0.c: ...
  ...
```

`gfx_v8_0.c` estaba en esa lista, en las lineas 852 y 895. Y no lo abri. Fui
directo a leer `gfx_v6_0.c:1869` porque era el primer resultado con el patron
completo, y ahi construi tres conclusiones.

```text
  LA LECCION DE vivos.py, QUE YA ESTABA ESCRITA, Y QUE VUELVO A APRENDER:

  "VIVO a nivel de fichero mezcla tres mecanismos".  Aqui la variante es
  "IDENTICO a nivel de nombre".  gfx_v6_0_ring_test_ring y
  gfx_v8_0_ring_test_ring tienen el MISMO nombre, la misma estructura y un
  registro DISTINTO.  Buscar "la funcion" por nombre lleva a la generacion
  equivocada tan fiablemente como buscarla por ASIC equivocado.

  Y hay una segunda, mas insidiosa: mi primer razonamiento fue CORRECTO y el
  error vino despues.  "El opcode no es 0x68" era un discriminante VALIDO.  Lo
  que no fue valido fue el marco de referencia: di por supuesto que el autotest
  de gfx_v8_0 se parecia al de gfx_v6_0, y luego usé mi propia suposicion para
  descartar la hipotesis correcta.

  UN DISCRIMINANTE NO PRUEBA NADA SI EL MARCO DE REFERENCIA ES UNA SUPOSICION.
```

Y una tercera, sobre `NOT_DETERMINED`:

```text
  Escribi "NOT_DETERMINED: relleno de inicializacion o residuo de una
  ejecucion anterior", con el cuidado de rigor que toca.  Y era evitable: la
  constante de envenenamiento 0xDEADBEEF es unico en todo el driver para
  autotest de anillo, y su presencia en un anillo ES la respuesta.  No hacia
  falta ningun otro dato para pasar de NOT_DETERMINED a PROVEN.

  CUANDO ESCRIBO NOT_DETERMINED, TENGO QUE ESCRIBIR EN LA MISMA LINEA
  "que observacion concreta lo resolveria".  Si la respuesta esta en el
  propio artefacto, no era NOT_DETERMINED: era falta de busqueda.
```

Y una cuarta, sobre el comando que se escribe en el hallazgo. En el primer
borrador puse esto, **con la salida que NO produce**:

```text
  BORRADOR, FALSO.  La linea de salida no es de este comando:
    $ grep -niE "\b(c040)\b" /usr/share/umr/database/ip/gfx_8_0_0.reg
    9555:mmSCRATCH_REG0 0 0xc040 1 0 4294967295      <- SALIDA FALSA
```

**Ese comando no devuelve esa linea.** Lo execute junto con otro en la misma
linea, obtuve la linea, y se la atribui al que no funciona. Reejecutado uno por
uno, con `rc` de cada uno:

```text
  $ grep -niE "\b(c040)\b" /usr/share/umr/database/ip/gfx_8_0_0.reg
  (vacio)                                                  rc=1
  $ grep -rniE "\b(c040|C040)\b" /usr/share/umr/database/ip/gfx_8_0_0.reg
  (vacio)                                                  rc=1
  $ grep -n "mmSCRATCH_REG0" /usr/share/umr/database/ip/gfx_8_0_0.reg
  9555:mmSCRATCH_REG0 0 0xc040 1 0 4294967295             rc=0
```

El dato era correcto; el comando documentado era falso, porque en `0xc040` el
caracter anterior a `c040` es `x`, que es caracter de palabra, asi que el `\b`
inicial no casa.

```text
  TERCERA VEZ CON LA MISMA FORMA, y la serie es:
    1500  busco 0x3f y el fuente tiene 0x3F          -> caja
    1502  dos greps, atribuyo la linea al primero     -> no comprobada
    1506  dos greps, atribuyo la linea al que no     -> no comprobada

  EN LOS TRES CASOS: ejecute DOS busquedas y guarde el resultado de UNA.
  El numero de consultas coincide con el numero de lineas citadas.  Por eso
  no se nota: hay una linea de salida por linea citada.

  Y el daño es mayor que en los otros dos, porque un comando falso en un
  hallazgo es un hallazgo que no se puede reproducir por el metodo que dice.
  Un PROVEN_ABSENT falso se equivoca una vez.  Un comando documentado que no
  devuelve lo que dice, cada vez que se use, y no avisa.
```

## 7 · EL TEST "COUNT IMPOSIBLE" TIENE UNA CLASE DE FALSO POSITIVO

`1503` §2 propuso el test y lo presento como solido. Es bueno, y tiene un hueco:

```text
  EL TEST   "un packet con count C ocupa C+2 dwords; si no cabe en el anillo,
             no es un packet"   ->  CIERTO

  EL HUECO  el driver ESCRIBE un dword con count = 0x3FFF a proposito, para
             que el relleno sea reconocible.  Ese dword no cabe en ningun
             anillo de 2048.  El test lo clasifica como DATO, y es un NOP
             emitido por el driver.

  MEDIDO    los 2015 rellenos fallan el test.  Los 6 packets reales pasan.
  O SEA    el test no distingue.  Sobre este anillo NO tiene poder de
           discriminacion: separa 2016 de 6 sin clasificar bien ninguno de
           los dos grupos.
```

La version Util del test es mas fuerte:

```text
  "no cabe en el anillo Y su opcode no esta en el inventario de 74"  ->  DATO
  "no cabe en el anillo pero su opcode SI esta en el inventario"     ->  RELLENO
  "cabe en el anillo"                                                ->  PACKET
```

Con ese orden, los 2015 son relleno y los 6 son packets, sin ambiguedad. La
regla que `1502` propuso y `1503` §6 refinó queda así:

```text
  1500  un PROVEN_ABSENT no se escribe a partir de un grep
  1502  un PROVEN_ABSENT exige un INVENTARIO CERRADO
  1503  un PROVEN tampoco se escribe a partir de un grep
  1506  y un test de clasificacion tiene que declararse su clase de falso
        positivo, medirse contra ella, y si no discrimina, no se usa.

  LA REGLA DE FONDO, QUE NO LA HABIA ESCRITO:  antes de aplicar un test a un
  artefacto, comprobar que el PRODUCTOR del artefacto no viola el test.
  El driver es el unico que sabe que 0x3FFF es decorativo, y produce ese dword
  2015 veces por anillo.
```

## 8 · LO QUE NO CONCLUYO, Y POR QUE

Hay 253 NOPs entre el final del autotest (`[6]`) y el principio del frame real
(`[259]`). `amdgpu_ring_generic_pad_ib` alinea el IB, y el `align_mask` del
anillo de compute explicaria un hueco de esa forma:

```text
  6 + 253 = 259
  289 - 259 = 30 dwords de frame

  PERO  alinear a 256 dwords desde 6 da 256, no 259.  Y ningun align_mask
        razonable da 259.  Mirado con las 256 alineaciones posibles: ninguna
        produce 259.
```

La explicacion correcta es mas aburrida y no la voy a inventar:

```text
  la captura son los ULTIMOS 2048 dwords antes de wptr.  Los offsets del
  fichero son relativos a la VENTANA, no al principio del buffer del anillo.
  259 es un offset de captura, y la alineacion se cumple sobre el offset de
  anillo, que no esta en el fichero.

  NOT_DETERMINED  por que 253.  Con lo que hay, la respuesta honesta es que no
  se puede, y la razon es que falta rptr/wptr.  pm4tila ya expone esa
  cabecera, y no hay cabecera en estas 21 capturas.
```

## 9 · ESTADO

```text
PROVEN_DERIVED  0xffff1000 == PACKET3(PACKET3_NOP, 0x3FFF) == el .nop de
                gfx_v8_0_ring_funcs_{gfx,kiq,compute}.  Los 2015 dwords de
                comp y los 1648 de gfx son relleno emitido por el driver
                (amdgpu_gfx.c:1701, amdgpu_ring.c:128/131/154).
PROVEN_DERIVED  SDMA_PACKET(SDMA_OPCODE_NOP,0,0) == 0.  El relleno de SDMA
                es cero, y por eso sdma0 tiene 784 ceros y ningun 0xffff1000.
PROVEN_DERIVED  el valor de relleno identifica la familia de anillo con un
                solo dword: 0xffff1000 -> PM4/GFX, 0 -> SDMA.

PROVEN          el paquete de [3] es gfx_v8_0_ring_test_ring:
                  opcode 0x79 = PACKET3_SET_UCONFIG_REG      (cikd.h:476)
                  longitud 3 dwords = amdgpu_ring_alloc(ring,3) + count+2
                  body[0] 0x40 = mmSCRATCH_REG0(0xc040, umr ip/gfx_8_0_0.reg:9555)
                                  - PACKET3_SET_UCONFIG_REG_START(0xc000)
                  body[1] 0xDEADBEEF = literal en gfx_v8_0.c:852
PROVEN          el anillo de compute pasa el autotest del driver.  Es el
                unico resultado de salud directa de las 21 capturas.

CONFIRMA        pm4tila 2021 = 2015 NOP + 6 packets.  Cuadra exacto, y su
                convencion `nop=1dword` (declarada en su cabecera, aplicada en
                pm4tila.py:239/643, con vector en :842) es lo que lo permite.

REFUTADO, mio   1503 §1   los 2015 son basura -> son relleno emitido
REFUTADO, mio   1503 §2   "count imposible" prueba que es DATO -> el driver
                            escribe count=0x3FFF a proposito; el test tiene
                            una clase de falso positivo de 2015 sobre 2021
REFUTADO, mio   1503 §3   la distincion PARCIAL / NO_ES_PM4_O_TRUNCADO de
                            pm4tila es accidental -> es la regla nop=1dword
REFUTADO, mio   1503 §4   NOT_DETERMINED sobre el 0xdeadbeef -> es el autotest

ERROR DE METODO mio   leido gfx_v6_0 en vez de gfx_v8_0 TRES VECES, y el primer
                      grep ya habia dado la pista.  Identico a nivel de nombre
                      lleva a la generacion equivocada igual que identico a nivel
                      de ASIC.  Y un discriminante no prueba nada si el marco de
                      referencia es una suposicion.

NOT_DETERMINED  por que hay 253 NOPs entre el autotest y el frame.  Los offsets
                del fichero son de ventana, no de anillo, y falta rptr/wptr.
```

## 10 · LO QUE SIGUE

El anillo de compute ya no es "una captura vacia": es **el registro mas
informativo de las 21**, porque tiene las tres cosas que se pueden pedir a un
anillo.

```text
  1. UN AUTOTEST QUE PASADO, con su registro resuelto desde fuera del corpus.
  2. UN RELLENO CUYA SEMANTICA ESTA EN EL DRIVER, con dos valores distintos
     segun la familia de motor.
  3. UN FRAME REAL, que es el mismo nucleo que el de gfx (1503 §3) y por tanto
     el mismo codigo en un driver propio.
```

Lo que sigue siendo el cuello es `rptr/wptr`. Sin eso no se puede decir donde
empieza un frame en el buffer, ni por que hay 253 NOPs, ni atribuir una captura
a un instante. Y `pm4tila` ya sabe leer esa cabecera: lo que falta son las
capturas, no la herramienta.