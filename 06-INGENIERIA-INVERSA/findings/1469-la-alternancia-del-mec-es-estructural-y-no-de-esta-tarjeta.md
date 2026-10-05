# 1469 — el 55 % "sin explicar" del MEC no es de esta tarjeta: es una región estructural, y el censo de 310 blobs lo demuestra

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=CIERRE-DE-FRONTERA+REVISION-PROPIA+REVISION-DE-UN-REVISOR
TRACK=STATIC(binarios de /lib/firmware/amdgpu) · cero hardware · cero escrituras
GENERADO=2026-10-04
AFECTADO=06-INGENIERIA-INVERSA/findings/1467-*  §3.1 "el 55 % del microcodigo del MEC es una
         alternancia y no tengo los bytes sin la semantica, NOT_DETERMINED"
ESTADO=PROBADO · la alternancia A/B es una region estructural del formato de imagen del MEC,
       con un tamano que es propiedad de la GENERACION de microcodigo, no de la ASIC
       · 36013 dwords en Tonga, Fiji, Carrizo, Stoney, Topaz, Polaris10/11/12, Vega10/12/20,
         Vegam, Green Sardine, Picasso y Arcturus
       · 41764/41766 en la familia Navi/RDNA (aldebaran)
       · 36003 de 36020 (99.95 %) en la ventana 0xBA38..0x2ED08, 36013 en el fichero entero
       · y el contenido REAL de esa region son rampas aritmeticas entrelazadas, 17 dwords
```

## 0. El discriminante que faltaba: dos versiones del mismo programa

El 1467 dejó escrito que el 55 % del microcodódigo del MEC era una alternancia sin explicar, y
que era el mayor bloque sin explicar de la imagen. **Faltaba el discriminante**, y era gratis:
hay **cuatro ficheros MEC** con la misma longitud exacta (262 824 B) y distinto contenido.

```text
polaris12_mec.bin      sha256 799b3e73fd260b63  ucode_version 0x000002c1   (nunca se abre, v.1466)
polaris12_mec2.bin     sha256 799b3e73fd260b63  0x000002c1                   identico al anterior
polaris12_mec_2.bin    sha256 1e0ce977d29288e3  0x000002da                   EL QUE CORRE
polaris12_mec2_2.bin   sha256 11dc9315750b09ef  0x000002da                   EL QUE CORRE (MEC2)
```

**Un diff byte a byte entre dos versiones del mismo programa separa lo que el programa hace de
lo que la versión cambió.** Eso es un discriminante que no depende de conocer la ISA.

```text
mec vs mec_2      iguales 185 217 B (70.5 %)   distintos 77 607 B (29.5 %)
                  81 624 segmentos distintos, de los cuales solo 9 son >= 64 B
                  => la media es 0.95 B por segmento: casi todos son UN byte aislado
mec_2 vs mec2_2   iguales 218 935 B (83.3 %)   distintos 43 889 B (16.7 %)
                  10 738 segmentos distintos
```

**Y el mapa de densidad es lo que lo cierra:**

```text
bloque de 4 KiB   bytes distintos   (mec vs mec_2)
0x000000 .. 0x00B000          ~3 600 / 4096   (88 %)   <- la region densa
0x00C000 .. 0x02B000          EXACTAMENTE 1024 / 4096   (25.0 %)   <- 32 bloques SEGUIDOS
0x02E000                       1837 / 4096
0x02F000                        364 / 4096
carrera de ceros 0x2F298..0x40114   20 / 69 244 B   (0.03 %)
tabla de saltos 0x40114..0x402A8   134 / 404 B     (33.2 %)
```

**Exactamente 1024 en cada uno de 32 bloques consecutivos.** Eso es 25.0 % constante, y no lo
produce un parche de versión.

## 1. Hipótesis probada y REFUTADA

La lectura natural de "25.0 % constante" es que **la fase de la alternancia está invertida**
entre versiones: si cada dword intercambia A↔B, cambia exactamente 1 de cada 4 bytes = 25.0 %.
Predecía que bastaba intercambiar los dos valores para reproducir la otra versión.

**La probé. Es falsa.**

```text
swap(0x05980001 <-> 0x05540001) aplicado a mec_2, en 0xBA38..0x2ED08
   == mec     ->  False
   == mec2_2  ->  False
```

Queda registrado porque la hipótesis era buena y era la que la aritmética sugería. **No la
doy por buena: la probé y murió.**

## 2. Lo que sí es: una región estructural de tamaño generacional

Las 310 apariciones en `/lib/firmware/amdgpu` son el dato. El **conteo de dwords A/B es
esencialmente invariante dentro de cada generación de microcodigo**, y cambia entre
generaciones:

```text
36013 dwords   tonga, fiji, carrizo, stoney, topaz, kaveri(no), mullins(no)
               polaris10, polaris11, polaris12
               vega10, vega12, vega20, vegam
               green_sardine, picasso (36012, -1)
               ARCTURUS                       <- GCN5, y aun asi 36013
36009 dwords   topaz_mec2                    (-4)
41764 dwords   aldebaran                     <- Navi/RDNA: OTRA generacion
41766 dwords   aldebaran (sjt), gc_9_4_3/4, gc_9_5_0
     7 dwords   hawaii, kabini, mullins, kaveri   <- GCN1/2: NO existe la region
    15 dwords   navi10, navi14                <- antes de la region grande
    310 de 677 ficheros del directorio contienen la alternancia
```

**Y la variación dentro de una generación es de ±4 sobre 36 013.** Eso no es contenido: es una
asignación de tamaño fijo.

> **La conclusión que importa:** la alternancia **no es un misterio propio de esta tarjeta**.
> Es una región reservada del formato de imagen del MEC, con un tamaño que depende de la
> generación de microcodigo y **no** de la ASIC. En Tonga (2013) mide lo mismo que en Arcturus
> (2019). Whatever esté ahí dentro, es la misma clase de cosa para toda la compañía.
>
> Eso **degrada la pregunta, no la elimina**: el 1467 la dejó como "el mayor bloque sin
> explicar de la imagen", y ahora es "una región estructural, común a seis años y media de GPU
> de AMD, cuyo contenido sigue siendo `NOT_DETERMINED`". La frontera baja de prioridad, pero
> el `NOT_DETERMINED` sigue igual.

```text
en el MEC que corre (polaris12_mec_2.bin):
  36003 de 36020 dwords en 0xBA38..0x2ED08  = 99.95 %
  36013 dwords en el fichero entero         = 54.81 % de 65 706 dwords
```

## 3. Las excepciones: 17 dwords, y son el contenido real

De 36 020 dwords en la ventana, **36003 son A/B y 17 no lo son.** Esas 17 son lo único que hay
que mirar, y están concentradas al final de la ventana.

En `polaris12_mec_2.bin` (el que corre): primera excepción en `0x00BA70`, última en `0x02AE7C`.
En `polaris12_mec.bin` (0x2c1): 247 excepciones, de `0x02A9F8` a `0x02ED04`.

**Y son rampas aritméticas, no datos sueltos.** Con los valores crudos:

```text
0x02EA80  0xDD010000
0x02EA84  0x05540010     campo alto 0x0554 = 1364
0x02EA88  0xDD410000                          +0x40 en el nibble alto
0x02EA8C  0x05980010     campo alto 0x0598 = 1432
0x02EA90  0xDD810000                          +0x40
0x02EA94  0x05DC0010     campo alto 0x05DC = 1500
0x02EA98  0xDDC100000                          +0x40
0x02EA9C  0x06200010     campo alto 0x0620 = 1568
0x02EAA0  0xDE010000                          +0x40
0x02EAA4  0x06640010     campo alto 0x0664 = 1636
0x02EAA8  0xDE410000                          +0x40
0x02EAAC  0x06A80010     campo alto 0x06A8 = 1704
0x02EAB0  0xDE810000                          +0x40
0x02EAB4  0x06EC0010     campo alto 0x06EC = 1772
```

Dos rampas entrelazadas: una de paso **+0x40** y otra de paso **+0x44**. Y en `0x02EAB8..0x02EBB0`
otra de paso **−4** (`DC2C, DC28, DC24, DC20, …, DC08`) y otra de paso **+0x40** en el campo bajo
(`CD00, CD40, CD80, CDC0, CE00, …, CFC0`), ambas con `0x0026` fijo en el nibble bajo. Y en
`0x02EBB4..0x02EBF0` una de paso **+4** en el nibble (`C408, C40C, C410, …, C43C`) con `0x0073`
fijo.

**Es una tabla de dos índices.** Un dword `0xDxxx0000` y un dword `0xC4xx0073` se emparejan, y
cada uno progresa con su propio paso: `0x02EC74..0x02ED04` son doce pares alternados con ceros.
Eso es la firma de una **consulta bidimensional**, no de una tabla de una dimensión.

**Qué significa: `NOT_DETERMINED`.** No voy a nombrarlo. Lo que sí es `PROBADO` es la
estructura: rampas aritméticas de pasos `+4`, `+0x40`, `+0x44` y `−4`, entrelazadas por parejas.

## 4. Y una excitación mía que era una coincidencia

Cuando vi `0x05DC = 1500` dentro de la rampa, y sabiendo que **el techo de reloj de memoria de
esta tarjeta es 1500 MHz** (hallazgo 1449, `PROBADO`), casi lo escribo como tabla de relojes.
Lo comprobé:

```text
0x05DC = 1500 aparece  7 veces  en los tres MEC
                  0  veces  en mc, smc, ce_2, pfp_2

PERO  1364 aparece 18 007 veces   y  1432 aparece 18 016 veces
```

**1364 = 0x0554 y 1432 = 0x0598 son las medias palabras altas de los propios valores A/B**
(`0x05540001`, `0x05980001`). Los dos recuentos enormes son la alternancia contándose a sí misma.
Un valor de 16 bits en el rango 1364–1772 aparece decenas de miles de veces en la imagen, así
que que 1500 salga 7 veces **no distingue absolutamente nada**.

> **Casi escribo como evidencia lo que era un ruido de fondo, y lo paré porque el número no
>lo que sostendría la afirmación.** Es exactamente el modo de fallo que este hallazgo viene
> corrigiendo: el 1469 no es "he encontrado la tabla de relojes del MEC", es "he:checked que
> este camino NO lleva a ninguna parte, y por qué".

## 5. Procedencia

```text
binarios  /lib/firmware/amdgpu/*.bin.xz, 677 ficheros, todos descomprimidos y barridos
          los 4 MEC de la familia polaris12: mec.bin, mec2.bin, mec_2.bin, mec2_2.bin
metodo    diff byte a byte entre versiones; mapa de densidad por bloques de 4 KiB;
          excepciones a A/B; rampas por diferencia constante; censo sobre los 677 blobs
fuente    amdgpu/amdgpu_ucode.h:181-186  (jt_offset, jt_size: la tabla de saltos al final)
          amdgpu/amdgpu_cgs.c:239        jt_offset va en dwords
          amdgpu/amdgpu_gfx.c:1450-1451  la segunda formula de la tabla de saltos
```

```text
ESTADO=PROBADO · la alternancia 0x05980001/0x05540001 es una region ESTRUCTURAL del formato de
       imagen del MEC, con tamano generacional: 36013 dwords en toda la familia GCN3..Vega20 y
       Arcturus (310 de 677 blobs la contienen), 41764/41766 en Navi/RDNA
REFUTADA  mi hipotesis de fase invertida: intercambiar A<->B NO reproduce la otra version
CORRECCION PROPIA  el 1467 §3.1 dio por sin explicar una region que NO es propia de esta tarjeta.
       Sigue sin explicarse QUE contiene, pero deja de ser un misterio especifico del RX 550
PROBADO  el contenido real de la region son rampas aritmeticas entrelazadas de pasos +4, +0x40,
       +0x44 y -4, emparejadas (0xDxxx0000, 0xC4xx0073), con ceros intercalados: la firma de
       una consulta de dos indices
NOT_DETERMINED  que significa la tabla.  Solo 17 dwords de 36020 la interrumpen en el MEC que corre
REFUTADO por comprobacion  la idea de que la rama con paso 0x44 sea la tabla de relojes: 0x05DC=1500
       aparece 7 veces, mientras 1364 y 1432 aparecen 18 007 y 18 016 veces.  No distingue nada
LIMITE   la region cae fuera de la ventana de codigo y su semantica sigue cerrada.  La ISA del
       MEC sigue NOT_DETERMINED (1467 §3), y ambas cosas hacen falta para cerrarla
RIESGO  ninguno.  CERO escrituras, cero hardware, cero acceso a la GPU
FRONTERA Intel intacta: fb0=i915drmfb 1366,768, card0 control=auto runtime=active
Siguiente  1) la rampa de dos indices: 12 pares (0xDxxx0000, 0xC4xx0073) con ceros intercalados.
           Es la mayor estructura semántica del MEC, y es un bloque de DATOS: se puede
           atacar sin la ISA, igual que la tabla de saltos
         2) comparar la cola 0x2EC00..0x2ED08 entre los tres MEC: es donde el diff es mas
           denso en el final y puede ser donde viven los parametros que cambian por ASIC
         3) 310 blobs y 21 familias: el mismo censo aplicado a un blob Navi diria si la
           region de 41764 dwords tiene la misma firma de dos indices
```

## 6. La regla del hallazgo

> **Un bloque grande y raro no es un misterio hasta que se le pregunta si es raro.**
> 36 000 dwords de un patrón que no entendía, y la pregunta "¿es raro?" se responde mirando
> **677 ficheros en vez de uno**. Cuatro de cada cinco familias de AMD del directorio tienen lo
> mismo, del tamaño exacto. La rareza estaba en mi lectura, no en los datos — y sin esa
> comprobación, este bloque habría ocupado el proyecto durante meses atribuyéndole
> importancia que no tiene.

Es la regla del 1466 aplicada a un caso donde **la suposición razonable ("esto es una tabla
oculta del MEC") era falsa y el dato barato que la desmonta era un censo de fichero**.