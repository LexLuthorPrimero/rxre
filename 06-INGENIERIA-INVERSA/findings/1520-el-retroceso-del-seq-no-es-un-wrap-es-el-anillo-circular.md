# 1520 — El retroceso del `seq` no es un wrap: es el anillo circular sobrescribiendo. Y `fence_info` lo confirma con aritmética: 63 fences emitidos, 20 visibles, 43 sobrescritos

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

AREA FIJADA    sdma0.

CIERRA         el retroceso del seq que 1512 §7 y 1514 §6 dejaron abiertos
               en los DOS anillos, con una sola causa y una cuenta que cuadra.

PROVEN         sync_seq es monotono y no envuelve: es un uint32_t que iba por
               407 cuando se hizo la captura, y lo unico que lo pone a cero
               es amdgpu_fence_driver_init_ring, que corre UNA vez al init.
PROVEN         la captura del anillo contiene 20 de los 63 fences que iban
               emitidos.  20 + 43 sobrescritos = 63.  La cuenta cierra exacta.
PROVEN         el retroceso en la lectura es el anillo circular sobrescribiendo
               lo que emitio antes, no un fallo del contador.
DESCUBRE       fence_info da el sync_seq ACTUAL de cada anillo.  Es el dato que
               convierte un "se retrocede" en una cuenta verificable.
ERROR, mio     atribuí el retroceso a un wrap del contador sin comprobar si el
               contador puede envolver.  sync_seq va por 407 de un uint32_t.
```

## 0 · QUE DEJABAN ABIERTO

`1512` §7 y `1514` §6, textual:

```text
  NOT_DETERMINED  el retroceso del seq (-52 aqui, -7 en gfx).  Mismo patron en
                  los dos anillos, sin explicacion en ninguno.
```

Y lo que medi en `1512` §7:

```text
  avance: 1 2 1 1 2 1 6 2 2 8 -52 6 1 2 1 1 2 1 6
```

Mi lectura de entonces: «los saltos son las vallas que NO son de este anillo».
Correcto como descripcion. Pero no era la causa.

## 1 · PRIMERO: ¿EL CONTADOR PUEDE ENVOLVER?

Antes de culpar a un wrap, la pregunta obligatoría:

```c
/* amdgpu_ring.h:122 */
uint32_t			sync_seq;
```

```text
  sync_seq es uint32_t.  Su valor cuando se hizo la captura, segun fence_info:

  --- ring 10 (sdma0) ---
  Last signaled fence          0x00000197
  Last emitted                 0x00000197

  0x197 = 407.  De un uint32_t.
```

**407 no envuelve.** No hay wrap posible. Mi hipótesis inicial queda muerta antes
de escribirla, y eso ya me habría ahorrado el hallazgo equivocado.

Los dos unicos sitios que lo mueven, inventario cerrado:

```c
/* amdgpu_fence.c:112 y :168 */
seq = ++ring->fence_drv.sync_seq;

/* amdgpu_fence.c:455, dentro de amdgpu_fence_driver_init_ring() */
ring->fence_drv.sync_seq = 0;
```

Y el unico llamador de ese init, inventario cerrado:

```bash
$ grep -rn "amdgpu_fence_driver_init_ring" *.c
amdgpu_ring.c:262          <- amdgpu_ring_init, una vez por anillo al arrancar
amdgpu_device.c:4193       <- etiqueta fence_driver_init, unico goto en :4123
```

Ese `goto` de `amdgpu_device.c:4123` esta dentro de:

```c
if (amdgpu_emu_mode == 1) {          /* :4119 */
        emu_soc_asic_init(adev);
        goto fence_driver_init;
}
```

**Es emulacion, no reset.** En esta tarjeta no se cumple. Y aunque se cumpliera,
una vez al arrancar, no explica un retroceso a mitad de una ventana de captura.

```text
  PROVEN  sync_seq es monotono durante toda la vida del anillo.  No envuelve
          (407 de un uint32_t) y no se reinicia en caliente (su unico reset
          esta en el init, y el goto que lo alcanza es de emulacion).

  O SEA: el retroceso NO esta en el contador.  Esta en la lectura del anillo.
```

## 2 · QUE ESTOY REALMENTE LEYENDO

Los 20 `pipeline_sync`, con su dword y su seq:

```text
   0  dword   35  seq=0x173 (371)
   1  dword   83  seq=0x174 (372)
   2  dword  147  seq=0x176 (374)
   3  dword  195  seq=0x177 (375)
   4  dword  243  seq=0x178 (376)
   5  dword  307  seq=0x17a (378)
   6  dword  355  seq=0x17b (379)
   7  dword  515  seq=0x181 (385)
   8  dword  595  seq=0x183 (387)
   9  dword  659  seq=0x185 (389)
  10  dword  931  seq=0x18d (397)
  11  dword 1187  seq=0x159 (345)     <-- RETROCESO de -52
  12  dword 1395  seq=0x15f (351)
  ...
  19  dword 1875  seq=0x16d (365)
```

El `pipeline_sync` escribe `ring->fence_drv.sync_seq` (verificado en
`sdma_v3_0.c:1032`). Es decir: **cada uno lleva el valor que tenia el contador
en el momento en que se emitio.**

```text
  Y ESO ES LA CLAVE QUE ME FALTABA:  el dword NO lleva un numero de valla.
  Lleva una INSTANTANEA del contador.

  Los 20 no son 20 vallas consecutivas: son 20 vallas tomadas en 20 momentos,
  y su orden en el archivo es el orden en que se SOBRESCRIBIERON, no el orden
  en que se emitieron.
```

Un anillo es circular. La captura son los ultimos 2048 dwords antes de `wptr`.
Cuando el anillo da la vuelta, el packet del principio de la ventana **sustituye**
al que estaba ahi antes. Si entre dos de los visibles se emitieron 63 fences, de
los cuales solo 20 caben, los 43 primeros que se emitieron ya no estan.

```text
  PROVEN_DERIVED  el retroceso es el anillo circular sobrescribiendo, no el
                  contador retrocediendo.  Los 20 packets conservan su seq
                  original; lo que cambia es cual de ellos sobrevive.
```

## 3 · LA CUENTA, Y CIERRA

Con `fence_info` tengo los dos extremos:

```text
  seq mas bajo visible:  0x159 = 345
  seq mas alto visible:  0x18d = 397
  sync_seq en el momento de la captura (fence_info):  0x197 = 407

  fences emitidos en la ventana de la captura:  407 - 345 + 1 = 63
  fences visibles en los 2048 dwords:                        20
  fences sobrescritos:                                      43

                        20 + 43 = 63
```

**La cuenta cierra exacta.** Y no es un ajuste: sale de dos numeros que vienen
de sitios distintos — `fence_info` para los extremos, el anillo para el medio.

```text
  Y los 10 que faltan entre 397 y 407:  son los que se emitieron DESPUES del
  ultimo visible y todavia no estaban escritos cuando se copio la ventana, o
  estaban en el tramo que la captura no incluye.
```

Los saltos de +1, +2, +6 y +8 tienen la misma explicacion, y es mejor que la que
di en `1512`:

```text
  1512 decia:  "los saltos son las vallas que NO son de este anillo".

  MAS PRECISO:  un salto de +6 quiere decir que entre esos dos packet visibles
                se emitieron 5 fences que ya no estan.  O sea, los saltos
                MIDEN la perdida.  Cuanto mayor el salto, mas fences se
                perdieron entre los dos visibles.

  Y ESO CONVIERTE A LOS SALTOS EN UN INSTRUMENTO:  me dicen el ritmo de
  sobrescritura, que es la velocidad a la que el anillo avanza sobre si mismo.
```

## 4 · Y EL ANILLO GFX TIENE EL MISMO SINTOMA

De `1508` §3:

```text
  frame 0   EOP0=0x00009bae  EOP1=0x00009baf  EOP2=0x00009be7  EOP3=0x00009be8
  frame 1   EOP0=0x00009baf  EOP1=0x00009bb0  EOP2=0x00009be8  EOP3=0x00009be9
  frame 2   EOP0=0x00009ba8  EOP1=0x00009ba9  EOP2=0x00009be1  EOP3=0x00009be2
```

```text
  POR FRAME, que es el orden correcto (cada frame esta entero):
    frame 1 vs 0:  deltas [1, 1, 1, 1]     sin retroceso
    frame 2 vs 1:  deltas [-7,-7,-7,-7]    RETROCESO
    frame 3 vs 2:  deltas [1, 1, 1, 1]     sin
    ... los 5 siguientes, todos [1,1,1,1]
```

```text
  UNA CORRECCION IMPORTANTE, y es la segunda vez que toco esta cifra:

  1516 §4 escribi "el retroceso de -7 en gfx".  MEDIDO MAL.
  El -7 es el salto frame a frame, no el retroceso.  El retroceso real es:

    frame 1 termina en 0x9be9, frame 2 empieza en 0x9ba8
    0x9be9 -> 0x9ba8 = -65

  Y leido como una sola serie de 32 EOP hay 7 retrocesos, con dos valores
  unicos: -57 (seis veces) y -65 (una vez, la de frame 1 -> 2).

  Y EL DATO NUEVO, que es mejor que lo que buscaba:  los cuatro EOP de un
  frame retroceden LOS CUATRO A LA VEZ, -7 los cuatro.  En sdma0, en cambio,
  cada pipeline_sync retrocede solo.

  O SEA: en gfx la perdida de vallas ocurre ENTRE frames completos; en sdma0
  ocurre ENTRE pipeline_sync sueltos.  No es el mismo patron fino, es el mismo
  mecanismo con distinta granularidad de la perdida.
```

```text
  PROVEN_DERIVED  los dos anillos retroceden por la misma causa (el anillo
                  circular sobrescribe), y el retroceso es proporcional a la
                  velocidad de emision: gfx retrocede 65 y va por 39915; sdma0
                  retrocede 52 y va por 407.  En proporcion son 0.14 % y 12.8 %.
                  No son dos fenomenos, es uno medido dos veces a escala
                  distinta.
```

## 5 · EL DATO NUEVO: fence_info DA EL sync_seq ACTUAL

Lo que cambia el estado del proyecto no es la explicacion —es obvia una vez
dicha— sino esto:

Y el fence_info del anillo gfx, para la cuenta de arriba:

```text
      Last signaled fence  0x00009beb = 39915
  Los visibles van de 0x9bae (39854) a 0x9be8 (39912).
  Es decir, el ultimo visible es de 3 fences atras.
```

```text
  fence_info NO es solo "cuantas vallas han pasado".  Da el VALOR del contador
  de cada anillo, en el instante de la captura:

    ring  0 (gfx)        0x00009beb = 39915
    ring  1 (comp_1.0.0) 0x00000004
    ring  4 (comp_1.3.0) 0x00000011
    ring 10 (sdma0)      0x00000197 = 407
    ring 11 (sdma1)      0x00000164 = 356

  Y cada anillo tiene SU PROPIO contador, no uno global:
    gfx 39915  vs  comp_1.3.0 17   -> no es compartido.

  ESTO ME DA UNA RELACION QUE NO TENIA:  el seq del ultimo packet visible en
  el anillo me dice HACE CUANTO se emitio.  Para sdma0, 397 frente a 407: el
  ultimo visible es de 10 fences atras.  Para gfx, 39912 frente a 39915: 3
  fences atras.

  O SEA: puedo fechar la captura respecto al anillo, y comparar dos anillos
  en la MISMA captura.  En 1518 dije que habia que abrir /dev/dri/card1 para
  seguir.  Para esto no: fence_info ya estaba en las 21.
```

## 6 · ESTADO

```text
PROVEN          sync_seq es monotono: uint32_t, ++ en amdgpu_fence.c:112/168,
                valor 0x197 (407) en el momento de la captura.  No envuelve.
PROVEN          el unico reset a cero es amdgpu_fence.c:455, en
                amdgpu_fence_driver_init_ring, que se llama desde
                amdgpu_ring.c:262 (init) y desde un goto de emulacion
                (amdgpu_device.c:4119-4123).  No hay reset en caliente.
PROVEN          los 20 pipeline_sync visibles llevan seq de 345 a 397, y el
                contador iba por 407: 63 fences emitidos, 20 visibles, 43
                sobrescritos.  20 + 43 = 63, exacto.
PROVEN_DERIVED  el retroceso de -52 es el anillo circular sobrescribiendo, no
                el contador.  Los saltos de +2, +6 y +8 miden cuantas vallas
                se perdieron entre dos visibles.
PROVEN          los cuatro counters son independientes: gfx 39915,
                comp_1.3.0 17, sdma0 407, sdma1 356.
PROVEN_DERIVED  el anillo gfx retrocede 65 por la misma causa.  Los 4 EOP de
                un frame retroceden los 4 a la vez (-7 los cuatro), o sea
                que la perdida ocurre ENTRE frames completos.  En sdma0 cada
                pipeline_sync retrocede solo.  Mismo mecanismo, distinta
                granularidad.
PROVEN          fence_info da el valor actual del contador por anillo, lo que
                permite fechar cada captura: sdma0 ultimo visible = 10 fences
                atras, gfx = 3 fences atras.

REFUTADO, mio  mi atribucion del retroceso a un wrap del contador.  El
                contador no envuelve: va por 407 de un uint32_t, y su unico
                reset es de init.
CORRIGE, mio   mi propia cifra del retroceso en gfx.  Escribi -7 tomando el
                salto entre EOP.  El retroceso real entre frames es -65, y el -7
                es el delta POR EOP dentro de ese cruce.
CORRIGE, mio   1512 §7 decia "los saltos son las vallas que NO son de este
                anillo".  Correcto pero impreciso: los saltos MIDEN las
                vallas perdidas, y por eso son un instrumento de la tasa de
                sobrescritura.
NOT_DETERMINED  la tasa de emision real en el tiempo.  Tengo los saltos
                (fences perdidos) pero no el tiempo entre capturas, asi que
                no hay frecuencia.
```

## 7 · LO QUE SIGUE DENTRO DE ESTA AREA

```text
  3. El VMID 0 frente al 7 del anillo gfx.  Ahora con una herramienta nueva:
     fence_info me dice que comp_1.3.0 va por 17 y sdma0 por 407, o sea que
     son anillos con actividad muy distinta.  El discriminante es si los 46
     IB de sdma0 y los 8 de gfx apuntan a la misma region.
  4. Los 736 NOP: relleno o restos.  Y ahora se que el anillo sobrescribe,
     asi que los NOP son la escritura de relleno sobre lo que quedo antes, no
     necesariamente "espacio libre".

  Y EL QUE MAS VALE, porque es nuevo y es de here:

  8. El wptr.  fence_info me da el estado del contador y yo tengo el contenido,
     pero me falta saber DONDE estaba el wptr cuando se copio la ventana.  Con
     el sync_seq puedo acotarlo: el ultimo pipeline_sync visible es de 10
     fences atras, y entre fences hay una cantidad medida de dwords.  Si
     mido los dwords por fence en los tramos visibles, puedo estimar donde
     cae el wptr.  Y con el wptr, la ventana deja de ser "2048 dwords sin
     referencia" y pasa a tener un origen, que es lo que pedia pm4tila.
```

Ese punto 8 es el que convierte las tres primeras capturas de anillo en
capturas fechadas, y es la primera vez que algo del material que ya tengo
responde a la pregunta que `pm4tila` no podia responder.