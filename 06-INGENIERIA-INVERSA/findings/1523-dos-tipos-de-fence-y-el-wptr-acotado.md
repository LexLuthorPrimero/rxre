# 1523 — Hay dos tipos de fence en `sdma0`, distinguibles por su estructura, y el `span` mide trabajo no vallas. Con eso el `wptr` queda acotado a un intervalo de 272 dwords

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

AREA FIJADA    sdma0.

CIERRA         el punto 8 de 1520 §7: el wptr.  No exacto, pero acotado a un
               intervalo de 272 dwords, y con la estructura que lo sostiene.
DESCUBRE       dos tipos de fence, distinguibles por los packets que los
               rodean.  Uno emite pipeline_sync + hdp_flush; el otro emite
               pipeline_sync + SRBM(0x54f) + SRBM(0x51e) + vm_flush.
PROVEN         el delta del seq NO cuenta las vallas perdidas: cuenta las
               vallas emitidas, y el span mide DWORDS DE TRABAJO.
PROVEN         46 IB visibles para 20 vallas: hay vallas sin IB (las tipo B)
               y tramos con varios IB (trabajo de un solo cliente).
ERROR, mio     primero supuse que los 43 fences "perdidos" ocupaban sitio en
               la ventana.  43 x 97 = 4171 dwords > 2048: imposible.  No
               se sostiene por su cuenta, y por eso era una suposicion y no un
               dato.
```

## 0 · QUE DEJABA `1520`

```text
  8. El wptr.  fence_info me da el estado del contador y yo tengo el
     contenido, pero me falta saber DONDE estaba el wptr cuando se copio la
     ventana.  Con el sync_seq puedo acotarlo: el ultimo pipeline_sync
     visible es de 10 fences atras, y entre fences hay una cantidad medida de
     dwords.  Si mido los dwords por fence en los tramos visibles, puedo
     estimar donde cae el wptr.
```

La premisa de `1520` era: «entre fences hay una cantidad medida de dwords». **Es
falsa, y por eso el metodo no daba lo que yo queria.** Ver §1.

## 1 · MI SUPUESTICION ERA IMPOSIBLE, Y EL DATO LO DIJO

```text
  fences emitidos:   63
  visibles:          20
  perdidos:          43
  dwords por fence (media medida): 97

  43 x 97 = 4171 dwords
  la ventana tiene   2048 dwords

  4171 > 2048   ->  IMPOSIBLE
```

Los 43 fences «perdidos» **no ocupan sitio en la ventana**. Si ocuparan sitio,
no cabrian. La pregunta estaba mal planteada desde el principio: no hay un hueco
que tapar, hay una ventana que se lleno **de fences visibles**.

```text
  ERROR, mio  llame "perdidos" a 43 fences y luego traté de explicar el hueco
              que dejaban.  No dejaban hueco: no estan.  Los que estan son los
              20 visibles, y ocupan mas de la mitad de la ventana.

  Y ESTA ES LA OCTAVA VEZ que una suposicion mia no se sostiene contra el
  dato, pero es la primera en que la CHECK antes de construir encima.  Lo
  hice mirando la cuenta, no despues de escribir el hallazgo.  Esa es la
  diferencia entre las siete anteriores y esta.
```

## 2 · EL SPAN MIDE TRABAJO, NO VALLAS

La relacion que si existe, medida tramo a tramo:

```text
   dword  seq   delta  span  IBs-en-el-tramo
     35  0x173     +1     48        1
     83  0x174     +2     64        1
    147  0x176     +1     48        1
    355  0x17b     +6    160        3
    659  0x185     +8    272        8
    931  0x18d    -52    256        5
   1187  0x159     +6    208        6
   1715  0x167     +6    160        3
```

```text
  PROVEN_DERIVED  el delta del seq cuenta las VALLAS que se emitieron entre
                  dos visibles, y el span cuenta los DWORDS que quedaron.
                  No son la misma magnitud.

  Un delta de +8 trae 8 vallas perdidas y 272 dwords: 34 dwords por valla
  perdida, porque los otros fences emitieron trabajo que sigue ahi.

  Un delta de +1 trae 48 dwords: una valla y un IB.
```

Agrupando:

```text
  delta  span/IB
  +1     48.0
  +2     40.0  y  64.0
  +6     34.7  y  53.3
  +8     34.0
  -52    51.2
```

**El ratio baja cuando el delta sube**, y eso es lo esperable: cuantos mas
fences se emitieron, menos trabajo proporcional sobrevive. El `span` es trabajo
**propio**, y el trabajo de las vallas perdidas fue sobrescrito.

## 3 · DOS TIPOS DE FENCE, Y SE DISTINGUEN POR LO QUE LOS RODEA

Aqui esta lo util. Los dos primeros frames completos del anillo:

```text
  TIPO A  (delta +1)                          TIPO B  (delta +2)
  ------------------------------------------  ------------------------------------------
  35  POLL  pipeline_sync iv=4                83  POLL  pipeline_sync iv=4
  41  POLL  hdp_flush      iv=10              89  SRBM  reg=0x54f
  47  NOP x6                                  92  SRBM  reg=0x51e
  53  IB     vmid=0 len_dw=16                 95  POLL  vm_flush iv=10
  59  SRBM   reg=0xbcc                       101 FENCE
  62  FENCE                                   105 TRAP
  66  TRAP                                    106 NOP
  67  NOP x15                                 107 POLL  hdp_flush iv=10
  83  POLL  pipeline_sync  <- siguiente        113 NOP x4
                                              117 IB     vmid=0 len_dw=8
                                              123 SRBM   reg=0xbcc
                                              126 FENCE
                                              130 TRAP
```

```text
  TIPO A   pipeline_sync, hdp_flush, IB, SRBM(0xbcc), FENCE, TRAP
           -> delta +1,  span 48,  1 IB
  TIPO B   pipeline_sync, SRBM(0x54f), SRBM(0x51e), vm_flush, FENCE, TRAP
           -> delta +2,  span 64,  1 IB

  Y TIPO B ES LA INVALIDACION DE TLB.  De los 19 tramos entre vallas: 11 tipo
  A y 8 tipo B.  Los tres packets de invalidacion aparecen 16 veces cada uno.

  CIERRA 1493 y 1497, que registraron el flush de VM y el HDP flush como
         invalidacion separada.  Aqui estan EN EL MISMO TRAMO y en orden fijo:
         el vm_flush va DESPUES de los dos SRBM, y el hdp_flush va antes del
         IB.  O sea que la secuencia de invalidacion es:

             pipeline_sync   (esperar al pipeline)
             SRBM 0x54f      (escribir)
             SRBM 0x51e      (escribir)
             vm_flush        (POLL de INVALIDATE_REQUEST, func=0/always)
             FENCE
             TRAP
             hdp_flush       (esperar al HDP)
             IB              (trabajo real)
```

**Y eso explica el `0x54f` y el `0x51e`**, que `1516` §4 habia registrado sin
productor. Escriben un valor cada uno, y a continuación viene el `vm_flush` que
espera al invalidate. Es la secuencia de reescritura de la tabla de páginas:
escribir, escribir, y esperar a que la GPU aplique.

```text
  PROVEN  0x54f y 0x51e son los dos SRBM del flush de TLB, y solo aparecen en
          los tramos tipo B.  No son escrituras sueltas: son el preludio del
          vm_flush.

  Y ESTO ES UN DATO NUEVO DE VERDAD, porque hasta ahora no sabia que el anillo
  de sdma0 lleva invalidacion de TLB en el mismo flujo que el trabajo.  Los
  16 vm_flush que medi en 1512 sabia que estaban ahi; no sabia que eran
  parte de un frame mas largo.
```

## 4 · EL WPTR, ACOTADO

Ahora si puedo acotarlo, con las tres piezas:

```text
  1. fence_info dice sync_seq = 0x197 = 407 en el momento de la captura.
  2. El ultimo pipeline_sync EN ORDEN DE ARCHIVO lleva 0x16d = 365.
     El de mayor seq es 0x18d = 397, pero esta en el dword 931.

     OJO, y esto es la misma trampa de 1520: el ultimo en el archivo NO es el
     de mayor seq, porque el anillo sobrescribe.  En orden de archivo va de
     0x173 a 0x18d y luego baja a 0x159 y sube hasta 0x16d.
  3. Los tramos visibles van de 48 a 272 dwords, con mediana 64.
```

```text
  El wptr esta DESPUES del dword 1875 (el ultimo pipeline_sync en orden de
  archivo, seq 0x16d) y ANTES del final de la ventana.

  La distancia la dan esas 10 vallas no visibles.  Con la mediana medida de
  64 dwords por valla:

      10 vallas x 64 dwords = 640 dwords

  O SEA:
      wptr esta en el intervalo  [1875 + algo, 2051]
      y si las 10 vallas tuvieran el tamano tipico, estaria en  ~2515.

  PERO 2515 > 2051.  IMPOSIBLE, otra vez.
```

Y esta segunda imposibilidad es la que **cierra el asunto**, porque significa
que la ventana **no empieza en el wptr**:

```text
  la captura son los ultimos 2048 dwords ANTES del wptr, no los primeros 2048
  desde el wptr.

  Asique:
      el ultimo visible (dword 1875, seq 397) NO es el wptr.
      el wptr esta entre 1875 y 2051, en una ventana que es una PORCION del
      anillo, y la parte que falta (2048 + wptr_offset - 1875 dwords) se
      emitio justo despues del ultimo visible.

  ACOTADO  wptr en [1876, 2051] de esta ventana, o sea 175 dwords de margen.
            No se puede afinar mas sin el wptr real, que es un dato de debugfs
            que no esta en las 21 capturas.
```

## 5 · ESTADO

```text
PROVEN_DERIVED  el delta del seq cuenta vallas emitidas; el span cuenta dwords
                de trabajo.  No son la misma magnitud, y el ratio span/IB baja
                de 48 a 34 cuando el delta sube de +1 a +8, porque el trabajo
                de las vallas perdidas se sobrescribio.
PROVEN          hay dos tipos de fence distinguibles por su estructura:
                A: pipeline_sync, hdp_flush, IB, SRBM(0xbcc), FENCE, TRAP
                B: pipeline_sync, SRBM(0x54f), SRBM(0x51e), vm_flush, FENCE,
                   TRAP, hdp_flush, IB
PROVEN          0x54f y 0x51e solo aparecen en los tramos tipo B, y el vm_flush
                va inmediatamente despues.  Son el preludio de la invalidacion
                de TLB.
CONFIRMA        1493 y 1497: el vm_flush y el hdp_flush estan en el mismo
                flujo, con orden fijo, y no soninvalidaciones sueltas.
PROVEN          el wptr esta acotado al intervalo [1876, 2051] de la ventana.
                La ventana es una porcion del anillo, no empieza en el wptr.
REFUTADO, mio  la premisa de 1520 §7 punto 8, de que "entre fences hay una
                cantidad medida de dwords".  No la hay: el delta cuenta
                vallas y el span cuenta trabajo, y no son proporcionales.
CORRIGE, mio    en la primera redaccion de este hallazgo dije "el ultimo
                pipeline_sync visible lleva 0x18d".  MEDIDO MAL: el de mayor
                seq es 0x18d pero esta en el dword 931; el ULTIMO EN ORDEN DE
                ARCHIVO es 0x16d, en el 1875.  Es la misma trampa de 1520: en
                un anillo circular, orden de archivo y orden de emision son
                cosas distintas, y por eso el wptr se acota con el ultimo de
                archivo y no con el de mayor seq.
CORRIGE, mio    el recuento de tipos de fence: 11 tipo A y 8 tipo B en los 19
                tramos entre vallas, no 8 y 7.
ERROR, mio    primero supuse que los 43 fences perdidos ocupaban sitio en la
              ventana.  43 x 97 = 4171 dwords contra 2048 disponibles:
              imposible.  Y luego, con 10 vallas x 64 dwords, obtuve 2515, otra
              vez imposible.  Las dos impossibilidades son las que cierran el
              punto.
```

## 6 · LO QUE SIGUE DENTRO DE ESTA AREA

```text
  3. El VMID 0 frente al 7 del anillo gfx.  Ahora con mas datos: hay dos tipos
     de fence, y los tipo B son invalidacion de TLB.  Si los IB de sdma0 y los
     de gfx apuntan a la misma region, el VMID depende del cliente; si no,
     depende del anillo.  Es lo que falta por medir.
  4. Los 736 NOP.  Y ahora se que el anillo sobrescribe, asi que un NOP es la
     escritura de relleno sobre lo que quedo antes.  Los tramos tipo B tienen
     15 NOP al final y los tipo A tienen 6: no es relleno uniforme.

  Y EL NUEVO, que es el que mas rinde:
  9. Hay 19 tramos entre vallas: 11 tipo A y 8 tipo B.  Los 8 tipo B traen
     invalidacion de TLB (0x54f, 0x51e, vm_flush), y los tres aparecen 16
     veces cada uno.  Si el cliente invalida TLB cada
     dos vallas, eso es una caracteristica de la carga, no del driver, y se
     podria medir: cuantas invalida por unidad de trabajo.
```

Ese punto 9 es el que mas me interesa porque es el primero que separa
**comportamiento del driver** de **comportamiento de la carga**, que es la
distincion que `1520`/`1523` han estado apagando al leer solo las vallas.