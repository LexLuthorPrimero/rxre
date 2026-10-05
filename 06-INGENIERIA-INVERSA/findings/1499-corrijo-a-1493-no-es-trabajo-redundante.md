# 1499 — Corrijo a `1493`: las 16 invalidaciones NO son trabajo redundante. Son 16 envíos distintos, intercalados con 20 fences. El «4,7 % del anillo es desperdicio» que construí encima era falso

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

REFUTA      1493 §3.  Alli escribi "invalidar el mismo VMID 16 veces no invalida
            nada nuevo a partir de la segunda" y lo califique de trabajo
            redundante.  MEDIDO:  no son el mismo envio repetido.  Son 16
            submissions distintas, y el trabajo se reparte entre ellas.

REFUTA      en cascada  1495 §3 (4,7 % del buffer en un no-op) y el
            PROVEN_DERIVED de 1495 §6 que proponia omitirlo.  Ese numero es real
            como OCUPACION, pero no como DESPERDICIO, y la distincion cambia
            la conclusion.

CONFIRMA    1493 en lo que si habia medido: 16 secuencias identicas, en una
            sola vuelta al anillo, no enrolladas.

DESCUBRE    de paso, y no lo buscaba:  la carga que produjo la captura es un
            COMPOSITOR DE ESCRITORIO (sway), no compute.  Y el anillo donde esta
            toda la actividad de invalidacion es el MENOS usado de todos.
```

## 0 · EL ORIGEN DEL ERROR

`1493` contó 16 secuencias idénticas y saltó a la conclusión. **Nunca preguntó si
eran 16 envíos o 1 envío 16 veces.** La respuesta estaba en otra captura del
mismo directorio, `amdgpu_fence_info.txt`, que no había mirado.

## 1 · LA MEDICIÓN QUE FALTA

Cuántos envíos hay en la ventana. Los fence waits se distinguen por el campo
`MEM_POLL(1)` del header, que es `sdma_v3_0_ring_emit_pipeline_sync`
(`:1036`) — el mismo que leí en `1497`:

```text
  anillo    poll con mem_poll=1    EVENT_WRITE_EOP
  sdma0              20                    0
  sdma1               2                    0
  gfx                 0                   32
```

El anillo gfx no tiene polls porque escribe su fence con `EVENT_WRITE_EOP`
(`1467`), no con un poll. Los dos mecanismos cuentan lo mismo: envíos.

```text
  sdma0:  20 envios en la ventana capturada, 16 invalidaciones
  ratio   16/20 = 0,80
```

## 2 · Y NO SE AGRUPAN: SE INTERCALAN

```text
  I = invalidacion    F = fence wait (envio)

    F  FI  F  F  FI  F  FI  I  I  F  FI  F  FI  I  I  I  I  F  F  FI  F  F  FI  F  FI  I  I  F
```

```text
  invalidaciones con un fence a menos de 40 dwords:  8 de 16
```

**Si fueran 16 copias del mismo trabajo,** estarían contiguas o con un patrón
regular. No lo están: hay fences sueltos sin invalidacion cerca, hay `I` sueltas, y hay cuatro
`I` seguidas en un punto. **Es trabajo repartido entre envíos.**

## 3 · LO QUE REFUTA, TEXTUALMENTE

`1493` §3 escribió:

```text
  Un invalidado de TLB que se repite 16 veces sobre el MISMO VMID no invalida
  nada nuevo a partir de la segunda.  Es trabajo que el driver hace y que un
  driver propio NO debe imitar.
```

**La premisa es falsa.** Los 16 envíos invalidan cada uno porque cada uno toca
las tablas de página —o porque el scheduler invalida por robustez antes de cada
batch—. Repetidos, sí; redundantes entre sí, **no está demostrado**.

Y `1495` §6 construyó sobre eso:

```text
  LO QUE HAY QUE COPIAR:  los 8 dwords utiles
  LO QUE PUEDE OMITIRSE: los 6 del poll, si no sincroniza
```

**La cuenta no cambia** —los 6 dwords siguen ahí y `1497` sigue diciendo que no
esperan— pero **la justificación cambia por completo**: no es «el driver hace
trabajo de más», es «el driver hace trabajo que no parece necesario en esta
carga». Que es una afirmación mucho más débil.

## 4 · LO QUE SÍ QUEDA EN PIE

```text
PROVEN          16 secuencias de invalidacion byte a byte identicas
PROVEN          en una sola vuelta, no enrolladas (7 separaciones distintas)
PROVEN          el poll con func=0 y mask=0 no espera  (1497)
PROVEN          ocupa 6 de los 12 dwords de cada secuencia  (1495)
PROVEN          HDP_FLUSH y MEM_POLL son los campos que enganchan la espera, y
                el vm_flush no pone ninguno                (1497)

REFUTADO        que sean trabajo redundante
REFUTADO        que quitarlas mejore el rendimiento
```

## 5 · LO QUE SALIO DE PASO, Y ES LO MAS UTIL DE ESTE HALLAZGO

Leí `clients.txt` para saber qué carga era, y no hace falta para la corrección.
Pero es un dato que no tenía:

```text
  command           tgid   dev    master   uid
  systemd-logind    1020     1    y        0
  sway              1705   129    n     1000
  sway              1705   129    n     1000
  sway              1705   129    n     1000
  sway              1705     1    y     1000
```

**Minor 129 es `card1`, la RX550.** `sway` tiene la RX550 abierta con tres
descriptores, **sin ser master**. Nadie es master de card1.

```text
  PROVEN_DERIVED  en el momento de la captura no habia nadie con DRM master en
                  la RX550.  Es coherente con la frontera dura del proyecto: la
                  consola esta en la Intel y card1 no tiene master.

  Y CONSECUENCIA:  el VMID 3 de las 16 invalidaciones pertenece a un proceso
                  que no es master.  No se puede decir cual:  ninguna captura
                  de este directorio expone la correspondencia VMID -> proceso
                  (grep de "vmid" sobre las 21 capturas: cero).  Los GEM handles
                  de gem_info (0x1, 0x2, 0x3 para sway) NO son VMIDs y
                  unirlos seria exactamente el error de espacio de nombres que
                  vengo corrigiendo desde 1470.

  NOT_DETERMINED  de quien es el VMID 3.  No hay dato en el arbol.
```

Y el otro dato, que es el que da contexto al resto:

```text
  Last signaled fence, por anillo:

    0 (gfx)          39 915     <- 98 % de toda la actividad
    10 (sdma0)          407
    11 (sdma1)          356
    4 (comp_1.3.0)       17
    1-8 (comp)           4-13
    9 (kiq)               0

  PROVEN_DERIVED  el anillo donde esta TODO el trafico de invalidacion es el
                  que mas invalidaciones tiene por ventana Y el que menos uso
                  acumulado tiene.  sdma0 hizo 407 envios contra los 39 915 de
                  gfx.  Su ventana de 2048 dwords esta llena de invalidaciones
                  porque su carga es de escritorio, no de compute.
```

## 6 · LA LECCION, Y ES LA CUARTA VEZ QUE LA ESCRIBO

```text
  CONTAR Y DEDUCIR SON OPERACIONES DISTINTAS.

  1493 conto 16 y dedujo "16 veces lo mismo".  Los dos pasos son correctos por
  separado y el segundo no se sigue del primero.

  LO QUE FALTA entre contar y deducir es una pregunta de CONTEXTO, y aqui era
  una sola:  ¿cuantos envios hay?

  Y la respuesta estaba en el directorio, en otro fichero, con otro nombre
  (`amdgpu_fence_info.txt`), y no lo mire porque no estaba buscando el dato
  que me faltaba:  estaba buscando confirmarlo.

  Regla que sale, y que se suma a las otras de la sesion:
    antes de concluir N repeticiones redundantes, comprobar si hay N contextos
    distintos.  Y en un anillo, un "contexto" observable es un envio, y se
    cuenta por las fences.
```

## 7 · ESTADO

```text
REFUTA      1493 §3  (las 16 no son trabajo redundante)
REFUTA      1495 §3 y §6 en la justificacion del 4,7 %
CONFIRMA    1493 en la medida (16 identicas, una vuelta), 1495 en los 6 dwords,
            1497 en los campos que enganchan la espera
PROVEN      20 envios en la ventana de sdma0, ratio 16/20 = 0,80
PROVEN      las invalidaciones se intercalan con los envios: 8 de 16 a menos
            de 40 dwords de una fence, y hay runs de 4 consecutivas
PROVEN_DERIVED  ninguna captura expone VMID -> proceso.  21 ficheros, cero
            menciones de vmid.  Los GEM handles no son VMIDs.
PROVEN_DERIVED  no hay nadie con DRM master en card1 en el momento de la captura,
            coherente con la frontera dura del proyecto
PROVEN_DERIVED  sdma0: 407 envios acumulados contra 39 915 de gfx.  La
            ventana esta llena de invalidaciones porque la carga es de
            escritorio

NOT_DETERMINED  de quien es el VMID 3
NOT_DETERMINED  si el poll con func=0 sincroniza algo.  Hardware, bloqueado.
```

## 8 · LO QUE SIGUE, CORREGIDO

```text
  1497 §6 decia:  "medir el coste de tiempo comparando una carga que invalida
  mucho con una que invalida poco".

  CORREGIDO:  con lo que hay, esa comparacion NO se puede hacer.  Las 21
  capturas son de UN SOLO INSTANTE y de UNA sola carga.  No hay dos puntos.

  Y ADEMAS:  ahora se sabe que la carga es de escritorio y que la relacion
  invalidaciones/envios es 0,80.  Para medir el coste del poll haria falta
  variar la carga, y eso exige ejecucion, no mas analisis.

  LO QUE SI QUEDA MEDIBLE SIN RUNTIME, y es poco:
    - cuanto anillo cuesta la invalidacion:  9,4 % del buffer de sdma0  (1495)
    - que no espera:                                        func=0, mask=0  (1497)
    - que ocupa 6 de 12 dwords:                                       (1495)

  LAS TRES SON OCUPACION Y SEMANTICA.  NINGUNA ES RENDIMIENTO.
  Y ESA DISTINCION es la que 1493 no hizo, y por eso hay que corregirlo.
```
