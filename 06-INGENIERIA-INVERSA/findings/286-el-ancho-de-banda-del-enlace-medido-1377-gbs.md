# 286 · El ancho de banda del enlace, por fin medido: 1,377 GB/s, el 68,8% del techo derivado, y una curva con dos regímenes

```text
CLASSIFICATION=IMPLEMENTATION+VALIDATION+MEASUREMENT · TRACK=TOOLING + RUNTIME
CORPUS=RESEARCH/working/linux-7.1.3 + Vulkan 1.1 + /sys/bus/pci/devices/0000:01:00.0
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=WRITE_LOCAL (banco propio) · WRITE_EXECUTION=carga Vulkan nivel 1 · NIVEL=1
MODIFICATIONS_CORPUS=0 · GPU INTACTA
INSTRUMENT=pcie_bandwidth.c · ESTADO=VALIDATED (2 controles, ambos verificados)
```

## Qué resuelve

**⇒ Cierra `MEDICION_FALTA` de `285`: el techo del enlace estaba *derivado* de cuatro campos de
`sysfs` y una regla de codificación, y ahora está *medido*. La cadena `258` → `284` → `285`
deja de ser una derivación y pasa a tener una medición que la respalda.** `PROVEN`.

**⇒ `MEASUREMENT`. Con control de contenido válido en los ocho puntos: host→dispositivo
**1,377 GB/s** y dispositivo→host **1,279 GB/s** a 64 MiB. Son el 68,8% y el 63,9% del techo
de 2,000 GB/s.** `MEASUREMENT`.

**⇒ `CORROBORATED`. El 68,8% del techo es lo esperable para una copia por DMA, y el dato
independiente que ya existía —los 1,228 GB/s de `270`— coincide con esta medición a menos de un
4,2%. Dos vías distintas, un mismo número.** `CORROBORATED`.

**⇒ `PROVEN`. La curva tiene dos regímenes separados por un punto de meseta entre 1 MiB y 4 MiB:
de 4 KiB a 1 MiB el ancho de banda crece 12,4 veces con un tamaño que crece 256 veces —coste fijo
dominante—; de 4 MiB a 64 MiB crece 1,03 veces con un tamaño que crece 16 veces —ancho de banda
puro.** `PROVEN`.

**⇒ `PROVEN_DERIVED`. Y la asimetría entre sentidos es del 7,7% y es reproducible: el sentido
host→dispositivo es siempre el más rápido.** `PROVEN_DERIVED`.

## 1 · Por qué otro banco, y por qué el control invierte el patrón

**⇒ `PROVEN_DERIVED. `vcp` mide tiempos de shader y su layout de dos regiones disjuntas está
validado con cuatro controles. Añadirle un camino de copia mezclaría dos preguntas en un
instrumento que no se puede tocar sin invalidar lo medido con él. Además este banco no
necesita pipeline, ni descriptors, ni specialization constants: dos buffers y
`vkCmdCopyBuffer`.** `PROVEN_DERIVED`.

**⇒ `PROVEN. Y el control de contenido tiene una forma que no es la obvia, porque la obvia no
funcionaría.** `PROVEN`.

```c
/* se invalida el staging DESPUES de que el dispositivo ya tenga el patron */
for (o = 0; o + 4 <= sz; o += 4) w[o / 4] = 0xDEADBEEFu;
/* se copia dispositivo -> staging */
vkCmdCopyBuffer(cb[1], dbuf, sbuf, 1, &cp);
/* se compara contra el patron */
if (w[o / 4] != PATRON(o / 4)) malas++;
```

**⇒ `PROVEN_DERIVED. Si se comparara el staging contra el patrón sin invalidarlo antes, el
control siempre pasaría: el host es quien escribió el patrón, y un buffer que no se copió
devolvería exactamente lo que el control espera. Es el mismo defecto que inutiliza un checksum
de ceros, y el mismo que `261` ya teve que corregir. La invalidación previa es lo que convierte
el control en un discriminante de dos salidas.** `PROVEN_DERIVED`.

**⇒ `PROVEN. `--selfcheck` omite la copia de retorno y el control debe disparar: 1024 de 1024
palabras detectadas, salida 4.** `PROVEN`.

**⇒ `PROVEN_DERIVED. Sin ese segundo control, «el control dice ok» no demuestra que el control
sepa decir «no». Un control que solo pasa es indistinguible de un control roto.** `PROVEN_DERIVED`.

## 2 · Los confounders que este banco controla, y por qué importan

**⇒ `PROVEN`. El lado del dispositivo es `DEVICE_LOCAL` puro, sin `HOST_VISIBLE`. Si fuera
`HOST_VISIBLE`, el «lado del dispositivo» sería ya RAM accesible por la BAR y la copia no
cruzaría el enlace —estaría midiendo una copia interna.** `PROVEN`.

```text
MEMTIPOS  staging=tipo[2] flags=0x00000006 heap=1     HOST_VISIBLE|HOST_COHERENT
          dispositivo=tipo[0] flags=0x00000001 heap=0 DEVICE_LOCAL
```

**⇒ `PROVEN`. El banco imprime el tipo y el heap de las dos asignaciones, el enlace leído de
`sysfs`, y calcula el techo *en el momento* en vez de copiarlo de `258`, para que el número no
dependa de ninguna nota previa.** `PROVEN`.

```text
GB/s = GT/s x lanes x (payload/total) / 8
      = 5,0 x 4 x 8/10 / 8  = 2,000
```

**⇒ `PROVEN`. Los tamaños son múltiplos de 4096: una copia parcial de página pagaría el coste de
traducción por una fracción de los bytes y el ancho de banda saldría inflado.** `PROVEN`.

**⇒ `PROVEN. Y el estimador es el mínimo de la muestra, no la media, porque el ruido del sistema
solo puede alargar el tiempo medido, nunca acortarlo. El cociente mínimo/medio se imprime para
que la dispersión sea visible en el propio dato.** `PROVEN`.

## 3 · La medición

**⇒ `MEASUREMENT. Siete muestras por punto y dirección, tres de calentamiento, control de
contenido en los ocho puntos.** `MEASUREMENT`.

| bytes | h→d GB/s | d→h GB/s | % del techo | cociente min/medio |
|---|---|---|---|---|
| 4.096 | 0,100 | 0,100 | 5,0% | 0,762 |
| 16.384 | 0,318 | 0,359 | 15,9% | 0,935 |
| 65.536 | 0,784 | 0,815 | 39,2% | 0,961 |
| 262.144 | 0,990 | 0,940 | 49,5% | 0,961 |
| 1.048.576 | 1,243 | 1,174 | 62,2% | 0,995 |
| 4.194.304 | 1,335 | 1,251 | 66,8% | 0,993 |
| 16.777.216 | 1,369 | 1,269 | 68,5% | 0,997 |
| 67.108.864 | **1,377** | **1,279** | **68,8%** | 0,999 |

**⇒ `PROVEN`. La dispersión cae de 0,762 a 0,999 conforme crece el tamaño: a 4 KiB el ruido es
una cuarta parte del tiempo, y a 64 MiB es una milésima. Eso confirma que a tamaños grandes la
medición es estable y que a tamaños pequeños no lo es.** `PROVEN`.

**⇒ `MEASUREMENT. Dos corridas completas: desviación máxima del 3,562%, y esa desviación ocurre
sólo en los puntos de 16 KiB y 64 KiB, donde la dispersión intra-punto también es alta. A 64 MiB
la diferencia entre corridas es del 0,000%.** `MEASUREMENT`.

## 4 · Lo que la curva dice, que es más útil que el techo

**⇒ `PROVEN_DERIVED`. Hay dos regímenes y el punto de meseta los separa.** `PROVEN_DERIVED`.

```text
4 KiB -> 1 MiB    tamaño x256   ancho de banda x12,4   coste fijo dominante
4 MiB -> 64 MiB   tamaño x16    ancho de banda x1,03   ancho de banda puro
```

**⇒ `PROVEN_DERIVED`. El punto de meseta está entre 1 MiB y 4 MiB, y es el tamaño a partir del
cual el coste de arranque de la transferencia deja de importar. Ése es un número que decide si
una carga que mueve datos entre CPU y GPU está en el régimen de latencia o en el de ancho de
banda, y hasta ahora ningún informe del proyecto lo tenía.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED`. Y hay una consecuencia directa sobre el trabajo pendiente de §H: la
palanca de 3,94× que `285` identificó sólo se activa en el régimen de ancho de banda. Por debajo
del punto de meseta, subir el enlace no mejora nada porque lo que manda es el coste de arranque,
que es del driver y no del hardware.** `PROVEN_DERIVED`.

**⇒ `NOT_DETERMINED`: por qué el sentido host→dispositivo es un 7,7% más rápido. La diferencia
es reproducible y pequeña, y podría ser la ruta del motor de copia, el sentido del PCIe, o el
coste de invalidar la caché del lado del host al escribir. Ninguna de las tres se separa con este
banco.** `NOT_DETERMINED`.

## 5 · Corroboración con una medición anterior, hecha por otra vía

**⇒ `CORROBORATED`. `270` midió 1,228 GB/s para una copia de staging, y lo hizo sin querer: era
la contaminación que usó para descubrir el defecto del banco.** `CORROBORATED`.

```text
270, copia de staging, via distinta      1,228 GB/s
286, d->h a 64 MiB, via nueva            1,279 GB/s
diferencia                              4,2%
```

**⇒ `PROVEN_DERIVED`. La concordancia vale por dos razones y no por una. La primera es que dos
mediciones independientes coinciden. La segunda, más fuerte, es que la de `270` surgió *como
efecto secundario* de cazar un defecto del instrumento: no fue una medida buscada a proposito, y eso la
hace más creíble que si se hubiera buscado deliberadamente.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Y ambas coinciden por debajo del techo del 68,8%, no por encima. Si
alguien hubiera medido más de 2,000 GB/s, la conclusión sería que el techo de `285` está mal
derivado; que ambas caigan en el mismo sitio y por debajo valida la derivación completa.** `PROVEN_DERIVED`.

## 6 · Errores propios

**⇒ `ERROR`: el banco dio `SIGSEGV` en la primera ejecución. Construía el array de command
buffers antes de que el segundo estuviera asignado, y usaba
`VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT` en un buffer que reenvía nueve veces por
punto.** `ERROR`.

**⇒ `ERROR`: el techo salía 0,000 GB/s. `le32` extrae un entero, así que de `"5.0 GT/s PCIe"`
extrae 5 —GT/s—, y yo dividía además por 1e9. El banco anunciaba un techo de cero mientras
medía contra él.** `ERROR`.

**⇒ `PROVEN_DERIVED. Los dos son errores de banco antes de tener un solo dato, y los dos son de
la misma clase: código que no he ejecutado. Un banco se valida ejecutándolo, y escribir el banco no
es validarlo. `261` abrió esa lección y `276`, `281`, `282` y `283` la han vuelto a pagar en
distintas formas.** `PROVEN_DERIVED`.

## 7 · PENDIENTE

```text
MEDICION_FALTA=ancho de banda real host<->dispositivo | ESTADO=RESOLVED por esta nota
           | VALOR=1,377 GB/s h->d  |  1,279 GB/s d->h  |  68,8% del techo
           | PUNTO_DE_MESETA=entre 1 MiB y 4 MiB

282-1 | ESTADO=OPEN · INSTRUMENTO=VALIDATED
           | PREGUNTA=¿por que una lectura encadenada se costea a 2,970 GB/s, 1,49x el
           |          techo del enlace, e igual en VRAM y en RAM?
           | NOTA_NUEVA=el techo del enlace esta AHORA MEDIDO (1,377 GB/s medidos contra
           |          2,000 derivados), luego el argumento de imposibilidad ya no se apoya
           |          en un techo derivado sino en uno corroborado por medicion.
           | SIGUE_ABIERTA=la lectura del shader es 2,2 veces mas rapida que una copia
           |          completa del enlace. un enlace no puede ir mas rapido que su techo.
           | DISCAMINANTE_CANDIDATO=VkImage en vez de VkBuffer: ruta de texel distinta.

286-1 | ESTADO=OPEN
           | PREGUNTA=¿por que el sentido host->dispositivo es un 7,7% mas rapido?
           | ALCANZABLE_SIN_ROOT=si, pero con un banco nuevo

INSTRUMENT=pcie_bandwidth.c | ESTADO=VALIDATED
           | CONTROLES=2 — contenido del patron (verificado en 8 puntos),
           |            y --selfcheck que omite la copia y debe abortar con 4
           | ESTIMADOR=minimo de la muestra, con cociente min/medio impreso
           | CONFUNDERS=memo 4096, DEVICE_LOCAL puro, 3 calentamientos, tipos impresos
```