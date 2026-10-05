# 1516 — Los 46 IB de `sdma0` no son 46 objetos: son 46 slots de 256 bytes dentro de un rango de 251. Alineación, huecos y ocupación, todo medido. Y no hay ciclo, y no lo fuerzo

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

AREA FIJADA    sdma0.

PROVEN         los 46 gpu_addr de los INDIRECT_BUFFER estan TODOS dentro de
               64 KiB, con prefijo 0x000000ff en los 46, alineados a 256.
PROVEN         46 segmentos, CERO solapamientos.  No es una bolsa de objetos:
               es una particion.  Ocupacion 46 de 251 slots = 18.3 %.
PROVEN         length_dw solo toma dos valores: 8 (x19) y 16 (x27).
PROVEN         las 45 separaciones son multiplos de 256 bytes.  Mediana 1024,
               maximo 3328.
CIERRA         el punto 5 de 1514 §6: el prefijo comun es real, y el rango
               es una sola region.
REFUTA, mio    mi propia expectativa de 1514 §6: dije "los 46 IB son del mismo
               cliente".  INFERENCIA, no medida.  Lo que se mide es una
               particion; el cliente no se ve.
ERROR, mio     primero busco un ciclo de particion que no existe, y casi lo
               escribo.  No lo hay.
```

## 0 · DE DONDE VIENE

`1514` §6 dejo cinco cosas, y la quinta era esta:

```text
  5. Los 46 INDIRECT_BUFFER van con vmid=0 y sus gpu_addr empiezan en 0xff00.
     Y los 20 pipeline_sync usan fence 0xff00001680.  El prefijo 0xff es el
     mismo.  Eso sugiere un unico espacio de direcciones para todo el anillo,
     y por tanto que los 46 IB son del mismo cliente.
```

El prefijo se confirma. **La conclusion de "mismo cliente" no se puede
sostener**, y lo digo antes de medir el resto, porque es exactamente el tipo de
salto que `1503` y `1514` me corrigieron.

## 1 · EL PREFIJO, Y LA CORRECCION DE LAS 48 BITS

Aqui hay unaprecision mia que hay quefixar antes de seguir:

```text
  En 1512 escribi "la direccion de fence de sdma0 es 0xff00001680".
  ESO ESTA MAL COMO DIRECCION.

  MEDIDO  el producer escribe upper_32_bits(addr) en dw[i+2]  (sdma_v3_0.c:1040)
          y addr & 0xfffffffc en dw[i+1]                            (:1039)

  dw[i+1] = 0x00001680
  dw[i+2] = 0x000000ff
  direccion = (0x000000ff << 32) | 0x00001680 = 0x000000ff00001680

  O SEA: la direccion es 0x000000ff_00001680.  "0xff00001680" son 10 digitos
  hex, son 40 bits, y una GPU VA de Polaris12 son 48.  Perdi el 0x000000 inicial
  al escribirla.
```

```text
  CORRIGE  1512: la fence es 0x000000ff00001680, no 0xff00001680.
```

Los 46 IB, con el prefijo bien puesto:

```text
  [  13] addr=0x00ff003c9b00  length_dw=8
  [  53] addr=0x00ff003ca300  length_dw=16
  [ 117] addr=0x00ff003caf00  length_dw=8
  ...
  prefijo de 32 bits altos: 0x000000ff  x46   <- los 46, sin excepcion
```

```text
  PROVEN  los 46 IB de sdma0 y la fence de los 20 pipeline_sync comparten
          prefijo 0x000000ff.  Es una sola region de direcciones.
```

## 2 · ALINEACION: 256, Y MAS QUE LA QUE PIDE EL PRODUCTOR

El productor exige 32 bytes (`sdma_v3_0.c:436`, `lower_32_bits(...) & 0xffffffe0`):

```text
  los 46 addr_lo & 0x1f == 0?           True    <- lo que pide el driver
  alineacion real medida:                0x100   <- 256 bytes
```

```text
  PROVEN  los 46 estan alineados a 256 bytes, ocho veces mas de lo que exige el
          productor.  ElPitch de 256 no lo pone sdma_v3_0.c: lo pone quien
          asigna la memoria.
```

## 3 · NO ES UNA BOLSA: ES UNA PARTICION

La prueba que lo decide, y es la de solapes:

```text
  46 segmentos [addr, addr + length_dw*4)
  SOLAPAMIENTOS:  0
  huecos:         45
  rango barrido:  0xff003c1a00 .. 0xff003d1520   = 64288 bytes
  suma de los 46 length_dw:  2336 bytes
```

**64 KiB barridos para 2336 bytes de IB. 2,7 % de densidad.**

```text
  Un allocator normal pondria los 46 juntos y dejaria el hueco al final, o los
  separaria por el objeto.  Aqui el hueco esta ENTRE CADA DOS, y es
  systematically mas grande que los propios objetos.

  PROVEN_DERIVED  no son 46 objetos-Rhasta 46 objetos.  Es UN buffer de 251
                  slots de 256 bytes del que se han ocupado 46.

  Tamano del buffer medido:  64288 bytes = 251 slots
  Ocupacion:                 46 / 251 = 18.3 %
```

```text
  Y esto es coherente con algo que ya sabia:  1512 §9 punto 5.  Un solo
  cliente que tiene un pool fijo y va tomando slots.  Pero:
    - que sea UN cliente es INFERENCIA, no medida.  Ver §5.
```

## 4 · LOS DATOS QUE NO DEPENDEN DE NINGUN PATRON

Porque aqui es donde casi la cago, y lo escribo primero:

```text
  Las 45 separaciones, en bytes:
    256, 1024, 1280, 2048, 2304, 3072, 3328   (7 valores distintos)

  TODAS son multiplos de 256.          <- esto es solido
  Mediana: 1024
  Maximo:  3328
  Minimo:  256
```

Y `length_dw` solo toma **dos** valores:

```text
  length_dw=16  x27   (64 bytes)
  length_dw=8   x19   (32 bytes)
  Ningun otro valor en los 46.
```

```text
  PROVEN  los IB de sdma0 son de 32 o de 64 bytes, sin variantes.  Y estan
          separados por multiplos de 256.
```

### Lo que intente y no existe

Busque un ciclo de particion, porque el conjunto de deltas de `1514` Prometia uno:

```text
  separaciones en slots de 256:
    4, 4, 8, 4, 4, 8, 12, 1, 12, 4, 9, 8, 9, 5, 13, 4, 4, 8, 4, 4, 8, 12,
    1, 12, 4, 9, 8, 9, 5, 9, 4, 1, 4, 4, 1, 4, 1, 4, 4, 1, 4, 4, 1, 4, 4

  [0:11]   4, 4, 8, 4, 4, 8, 12, 1, 12, 4, 9
  [11:22]  8, 9, 5, 13, 4, 4, 8, 4, 4, 8, 12
  iguales?  False

  Y buscando el periodo maximo que se repita EXACTAMENTE: ninguno.
```

```text
  NO HAY CICLO.  Y casi lo escribo igual, porque un patron parcial es muy
  mas bonito que "no hay patron".

  ERROR, mio  el razonamiento fue: "hay un repeating de 12 y otro de 30", lo
  cual es verdad de 22 comparaciones y falso de 8.  Y "hay dos modos, 8 y 16"
  que SI es verdad, pero es del len_dw, no de las direcciones.

  LA LECCION, y es distinta de las otras cuatro:

    LAS CINCO ERRORES ANTERIORES FUERON "DECIDI ANTES DE VER".
    ESTE ES "VI Y PREFERI VER".

    Un ciclo parcial se ve porque hay un ciclo parcial: el ojo lo completa.
    El discriminante no es "busco mas", es "exijo que se repita EXACTAMENTE y
    cuento las coincidencias".  Si el mejor periodo da 22 de 30, no hay ciclo,
    y el numero 22 de 30 es el dato.
```

## 5 · LO QUE NO SE PUEDE DECIR, Y POR QUE

```text
  LO QUE SE MIDE:
    una particion de 251 slots de 256 bytes, 46 ocupados, prefijo comun
    0x000000ff, VMID 0 en los 46, y la fence 0x000000ff00001680 tambien
    dentro del prefijo.

  LO QUE NO SE MIDE:
    cuantos clientes hay.  Y por tanto NO PUEDO AFIRMAR "un cliente".

  PARA AFIRMARLO necesitaria  el GEM handle del BO que respalda esa region.
  Y eso esta en amdgpu_gem_info.txt, que es de otro proceso, o en el
  allocator del driver, que es codigo.

  La pista que SÍ tengo:  la direccion de la fence (0x000000ff00001680) esta
  en el mismo prefijo que los 46 IB, y esta FUERA del rango de los 64 KiB que
  contienen los IB.  O sea: hay al menos dos objetos en el mismo prefijo, a
  distancias distintas.  Y la fence es del driver, no del cliente.

  NOT_DETERMINED  cuantos clientes.  El dato que lo resolveria es el GEM
                  handle del BO de esa region, y no esta en las 21 capturas.
```

## 6 · ESTADO

```text
PROVEN          los 46 gpu_addr de sdma0 estan todos dentro de 64288 bytes
                (rango 0xff003c1a00..0xff003d1520), con prefijo de 32 bits
                altos 0x000000ff en los 46, alineados a 256 bytes.
PROVEN          46 segmentos, cero solapamientos, 45 huecos.  Es una
                particion, no una bolsa: 46 de 251 slots, 18.3 % de ocupacion.
PROVEN          length_dw solo toma 8 (x19) y 16 (x27).  Ningun otro valor.
PROVEN          las 45 separaciones son multiplos de 256.  Mediana 1024,
                maximo 3328, minimo 256.
PROVEN          la fence de los 20 pipeline_sync (0x000000ff00001680) comparte
                prefijo con los 46 IB, y cae FUERA del rango de 64 KiB.
CORRIGE, mio    1512: la fence es 0x000000ff00001680.  Escribi
                "0xff00001680", que son 40 bits y no 48.
REFUTA, mio    mi propia inferencia de 1514 §6 de que "los 46 IB son del
                mismo cliente".  Es una inferencia.  Lo medido es una
                particion; el numero de clientes es NOT_DETERMINED.
ERROR, mio    intente un ciclo de particion que no existe.  El mejor periodo
              coincide 22 de 30, no 30 de 30.  No lo escribo.
```

## 7 · LO QUE SIGUE DENTRO DE ESTA AREA

De las cinco de `1514` §6, esta queda cerrada. Quedan cuatro:

```text
  2. El retroceso del seq (-52 aqui, -7 en gfx) y los saltos de +2, +6, +8.
  3. El VMID 0 frente al 7 del anillo gfx.
  4. Los 736 NOP: relleno o restos.
  6. NUEVO, y sale de este hallazgo:  por que length_dw solo toma 8 y 16.
     El productor escribe ib->length_dw tal cual, sin redondeo
     (sdma_v3_0.c:438).  O sea que el redondeo a potencia de 2 lo pone quien
     construyo el IB, y eso es codigo de Mesa, no del kernel driver.  Es la
     primera vez que la particion me lleva a un sitio que NO es el kernel.
```

Ese sexto punto es el que mas me interesa: es la primera vez que el rastro de
este anillo sale del driver y entra en el cliente, que es donde vive el
`1508`-style `length_dw` mismatch que nos dejara el IB sin poder leer.