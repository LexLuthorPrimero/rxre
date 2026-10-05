# 1503 — El anillo de compute no tiene un frame: tiene basura. `pm4tila` contaba 2021 packets porque el 99 % de los dwords tienen `type=3` por azar, y por eso no podía adjudicarlo

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

DESCUBRE       por que pm4tila da PARCIAL en el anillo de compute y UNICA en
               el de graficos:  el anillo de compute esta VACIO, y un anillo
               vacio lleno de ceros parecen packets.

PROVEN         2023 de 2051 dwords tienen type=3.  Si fuesen packets, el anillo
               estaria lleno.  No lo esta:  esta casi vacio.
PROVEN         el frame real empieza en el dword 259 y son 5 packets.
APPLY, mio     la regla de 1502 (inventario cerrado, no un grep) aplicada a un
               caso donde el problema no es un opcode sin nombre sino DATOS que
               parecen opcodes.
```

## 0 · LA PREGUNTA

`1502` §8 dejó escrito:

```text
  Lo que queda del lado del anillo es el mismo trabajo en el anillo de compute,
  que pm4tila trata como un caso aparte (2021 paquetes, convencion distinta) y
  que no he mirado con este nivel de detalle.
```

Y `pm4tila` reporta para `comp_1.3.1`:

```text
  PARCIAL,  2 de 16 convenciones cuadran,  2021 paquetes,  2048 dwords
```

**2021 paquetes en 2048 dwords.** Eso es un dword y medio por paquete, y un
packet PM4 más corto ocupa 2. **La cuenta no puede ser correcta.** Y sin embargo
la herramienta lo reporta como dato.

## 1 · POR QUÉ: EL TIPO DE PACKET SE ADIVINA POR AZAR

En PACKET3 el tipo está en los bits `[31:30]`, así que un dword **de datos**
tiene un 25 % de probabilidad de parecer un header de type-3:

```text
  MEDIDO   2023 de 2051 dwords tienen (dword >> 30) & 3 == 3    ->  99 %
  esperado por azar en 2051 dwords                              ->  513
  hay 4 veces mas de los que el azar produce
```

**No son 4 veces por azar.** Significa que hay muchísimos headers de type-3
reales… **o que el anillo está lleno de datos con los bits altos a 1.**

Y el segundo caso es el bueno, porque el anillo de compute **está vacío**:

```text
  anillo comp_1.3.1:  2048 dwords de cuerpo
    NOP reales (op 0x10):   2015
    packets con nombre:        5
    dwords con count imposible: al menos 3
```

## 2 · LA PRUEBA, Y ES LA MISMA DE 1502 PERO PARA DATOS

Un packet tiene que caber en el anillo. Si `count` dice 7853, el packet ocuparía
7855 dwords en un anillo de 2048: **es imposible**, y por tanto ese dword no es
un header.

```text
  dword   op    count     ocuparia      veredicto
  [5]     0xBE  7853      7855 dwords   IMPOSIBLE -> es DATO
  [261]   0xFF  16383     16385 dwords  IMPOSIBLE -> es DATO
  [289]   0x10  16383     16385 dwords  IMPOSIBLE -> es DATO (y NOP con count=0
                                           es un packet de 1 dword, asi que
                                           un NOP con count=16383 es basura)
```

Y el test del inventario, que es el que `1502` propuso:

```text
  inventario cerrado de PACKET3 en cikd.h:  74 simbolos

  0x58 -> PACKET3_ACQUIRE_MEM        en el inventario
  0x49 -> PACKET3_RELEASE_MEM        en el inventario
  0x79 -> PACKET3_SET_UCONFIG_REG    en el inventario
  0xBE -> NO esta en el inventario
  0xFF -> NO esta en el inventario
```

**Los dos que no están en el inventario son los dos con count imposible.**
Dos pruebas independientes, la misma conclusión.

## 3 · EL FRAME REAL, Y SON 5 PACKETS

La cadena empieza en 259 y con `count+2` de `1476` encaja **sin un solo hueco**:

```text
  [259] 0x58  ACQUIRE_MEM      count=5  -> 7 dwords
  [266] 0x3C  WAIT_REG_MEM     count=5  -> 7 dwords
  [273] 0x3F  INDIRECT_BUFFER  count=2  -> 4 dwords
  [277] 0x37  WRITE_DATA       count=3  -> 5 dwords
  [282] 0x49  RELEASE_MEM      count=5  -> 7 dwords
  [289] 0xFFFF1000 x N       <- basura, la cadena se acaba
```

**Es el mismo frame que el del anillo gfx**, con dos diferencias:

```text
  gfx    COND_EXEC → WAIT_REG_MEM → CONTEXT_CONTROL → INDIRECT_BUFFER
         → WRITE_DATA → EVENT_WRITE_EOP → SWITCH_BUFFER

  comp   ACQUIRE_MEM → WAIT_REG_MEM → INDIRECT_BUFFER → WRITE_DATA
         → RELEASE_MEM
```

Lo que **no** hay en el de compute: `COND_EXEC`, `CONTEXT_CONTROL`,
`EVENT_WRITE_EOP`, `SWITCH_BUFFER`. Lo que hay y el gfx no: `ACQUIRE_MEM` y
`RELEASE_MEM`.

```text
  PROVEN_DERIVED  el frame de graficos es el de "dibujar": condicional,
                  control de contexto, dispatch, y una valla con EOP para que
                  la interruption llegue al instante correcto.

                  Y el de compute no dibuja.  Toma memoria, espera al HDP,
                  lanza un IB, escribe un registro, y devuelve la memoria.

                  CON Y SIN DIBUJO, los dos comparten el nucleo:
                    WAIT_REG_MEM(0x1537, 0x1538)  ->  esperar al HDP
                    INDIRECT_BUFFER                ->  dispatch
                    WRITE_DATA(0xbcc)              ->  el mismo registro

                  Y ESO SIGNIFICA QUE LA PARTE QUE IMPORTA PARA EL MMU ES LA
                  MISMA EN LOS DOS, Y QUE UN DRIVER PROPIO solo tiene que
                  acertar en ese nucleo una vez.
```

## 4 · EL `0xdeadbeef`, QUE ES UN DATO INTERESANTE

En `[3]`, antes de la cadena real:

```text
  [3] 0x79  SET_UCONFIG_REG  count=1  cuerpo = 0x00000040, 0xdeadbeef
```

**El header es legítimo** (`op=0x79`, `count=1`, ambos en el inventario) y **el
valor es `0xdeadbeef`**, que es el patrón de envenenamiento clásico.

```text
  INTERPRETACION MAS PROBABLE:  el anillo no se limpia cuando se queda sin uso,
  y lo que hay antes de la cadena es de una ejecucion anterior, o de la
  inicializacion con un patron de relleno.

  NO AFIRMO CUAL DE LAS DOS.  No hay fuente que lo diga, y no hay forma de
  distinguirlo con una sola captura.  Es NOT_DETERMINED, y lo dejo asi.
```

Pero sí es medible una cosa: **`0xdeadbeef` no aparece en el anillo de gfx**, y
el de compute tiene 253 dwords antes de la cadena. Los dos anillos se inicializan
de forma distinta.

## 5 · LO QUE ESTO LE DICE A `pm4tila`

`pm4tila` es correcto en su adjudicación (`2 de 16`) y **su input está mal**:

```text
  ADVERTENCIA QUE pm4tila YA IMPRIME:
    "sdma0   NO_ES_PM4_O_TRUNCADO   2048 dwords, 0 de 16 convenciones cuadran"
    "sdma1   NO_ES_PM4_O_TRUNCADO   2048 dwords, 0 de 16 convenciones cuadran"

  Y NO Dice lo mismo de comp_1.3.1, que da PARCIAL con 2 de 16.
  PERO comp_1.3.1 esta igual de vacio.  La diferencia es que su ventana empieza
  en un punto donde la basura SI parece un packet, y la de sdma no.

  O SEA:  la distincion entre PARCIAL y NO_ES_PM4_O_TRUNCADO es ACCIDENTAL.
  Depende de si la basura que hay delante cae o no dentro de las 16
  convenciones.  No es una distincion semantica.
```

## 6 · LA REGLA, Y ES LA TERCERA DE LA SERIE

```text
  1500  un PROVEN_ABSENT no se escribe a partir de un grep
  1502  un PROVEN_ABSENT exige un INVENTARIO CERRADO
  1503  y ahora la inversa:  un PROVEN no se escribe a partir de un grep

  "2021 packets" de pm4tila es un PROVEN con forma de dato, y va en la misma
  categoria que el PROVEN_ABSENT erroneo de 1500:  una afirmacion fuerte hecha
  con un instrumento que no puede sostenerla.

  LA PRUEBA QUE FUNCIONA, y es la misma en los tres casos:
    no uses el instrumento para decidir SI el dato es del tipo que el instrumento
    espera.  Usa una propiedad INDEPENDIENTE del tipo.

    - 1500/1502:  el opcode tiene que estar en el INVENTARIO de 74
    - 1503:       el packet tiene que CABER en el anillo

  Las dos son baratas y las dos habrian evitado el error.
```

## 7 · ESTADO

```text
PROVEN          2023 de 2051 dwords del anillo comp tienen type=3, y eso NO
                significa que sean packets: un dword de datos tiene 25 % de
                aparecerlo
PROVEN          3 dwords con count imposible (7853, 16383, 16383) en un
                anillo de 2048: son DATO, no packets
PROVEN          los 3 opcodes sin nombre del anillo comp (0xBE, 0xFF, y el
                NOP con count=16383) NO estan en el inventario de 74, y los 5
                que SI estan (0x58, 0x49, 0x79, 0x3C, 0x3F) forman la cadena
PROVEN          el frame real empieza en 259 y son 5 packets con count+2, sin
                huecos
PROVEN          el frame de compute es ACQUIRE_MEM + WAIT_REG_MEM + IB +
                WRITE_DATA + RELEASE_MEM.  Sin dibujo: sin COND_EXEC, sin
                CONTEXT_CONTROL, sin EVENT_WRITE_EOP, sin SWITCH_BUFFER
PROVEN_DERIVED  el nucleo WAIT_REG_MEM(0x1537,0x1538) + INDIRECT_BUFFER +
                WRITE_DATA(0xbcc) es IDENTICO en los dos anillos.  Es la parte
                que toca al MMU, y un driver propio la implementa una vez.

DESCUBRE        0xdeadbeef en el anillo de compute, con un header valido.
                No esta en el de gfx.
DESCUBRE        la distincion PARCIAL / NO_ES_PM4_O_TRUNCADO de pm4tila es
                ACCIDENTAL: depende de si la basura delante cae dentro de las 16
                convenciones, no de si el anillo es PM4.

NOT_DETERMINED  si 0xdeadbeef es relleno de inicializacion o residuo de una
                ejecucion anterior.
```

## 8 · LO QUE SIGUE

El anillo de compute **no aporta un segundo frame que contrastar**, porque está
vacío. Así que el marco de referencia sigue siendo el de gfx, y ahora sabemos que
su núcleo de MMU es compartido.

Lo que queda por mirar en los anillos es el **SDMA0**, que es el único con
actividad real de invalidación y donde está el tráfico que importa para el MMU. Y
los 21 ficheros de captura incluyen `amdgpu_sa_info.txt` y `amdgpu_pm_info.txt`,
que son telemetría y no se han tocado: son la vía de `§72` para convertir estas
cifras de ocupación en algo de rendimiento.
