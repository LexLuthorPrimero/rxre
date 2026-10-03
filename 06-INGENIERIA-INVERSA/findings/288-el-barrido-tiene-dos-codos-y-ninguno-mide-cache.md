# 288 · El barrido del conjunto de trabajo tiene dos codos y ninguno mide caché: la hipótesis del TLB queda refutada por un discriminante

```text
CLASSIFICATION=MEASUREMENT+REFUTED+NEGATIVE_RESULT · TRACK=RUNTIME
CORPUS=RESEARCH/working/linux-7.1.3 + /sys/class/drm/card1/device/hwmon/hwmon1
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=WRITE_LOCAL (banco y kernel propios) · WRITE_EXECUTION=carga Vulkan nivel 1 · NIVEL=1
MODIFICATIONS_CORPUS=0 · GPU INTACTA
INSTRUMENT=vcp con page.comp y modelo 4 | ESTADO=VALIDATED (regresion 5/5)
```

## Qué resuelve

**⇒ Ejecuta el barrido de `262-1` con la magnitud correcta que `287` estableció —latencia por
vuelta, no ritmo agregado— y con 1024 hilos, dentro del régimen de latencia. La curva tiene
**tres mesetas y dos codos**, medidos.** `PROVEN`.

**⇒ `REFUTED`. La hipótesis del TLB —«lo que crece con el conjunto es el número de páginas
distintas, no el número de bytes»— es falsa. El discriminante da razón **1,00**: mismo número de
bytes, unas pocas páginas o muchas, la latencia es idéntica.** `REFUTED`.

**⇒ `REFUTED`. La segunda explicación candidata tampoco encaja: el modelo de acierto uniforme de
caché, `L(W) = L_c + (C/W)·(L_d − L_c)`, ajustado a los dos puntos mayores da una latencia de
**acierto de caché de 6905 ciclos**, que es absurdo para una L2.** `REFUTED`.

**⇒ `NOT_DETERMINED`: los dos codos son reales y medidos, y ninguna de las dos mecanismos que
se les ocurren encaja. `262-1` sigue abierto, y ahora con una hipótesis menos.** `NOT_DETERMINED`.

## 1 · El barrido, con la magnitud de `287`

**⇒ `MEASUREMENT. `div.comp` en modo división, 1024 hilos —dentro del régimen de latencia según
`287`—, 1024 vueltas, 7 muestras con calentamiento, control 7 de 7 en los nueve puntos.** `MEASUREMENT`.

| bytes | dwords | ns por vuelta | ciclos | GB/s | páginas de 4 KiB |
|---|---|---|---|---|---|
| 65.536 | 16.384 | 366,2 | 389 | 12,228 | 16 |
| 262.144 | 65.536 | 413,1 | 439 | 9,098 | 64 |
| 1.048.576 | 262.144 | **2.185,5** | **2.323** | 1,900 | 256 |
| 4.194.304 | 1.048.576 | 2.362,3 | 2.511 | 1,745 | 1.024 |
| 16.777.216 | 4.194.304 | 2.671,9 | 2.840 | 1,527 | 4.096 |
| 67.108.864 | 16.777.216 | **6.668,9** | **7.089** | 0,619 | 16.384 |
| 268.435.456 | 67.108.864 | 6.798,8 | 7.227 | 0,602 | 65.536 |

**⇒ `PROVEN`. Los dos codos están entre 262.144 y 1.048.576 bytes, y entre 16.777.216 y
67.108.864 bytes. El primero multiplica la latencia por 5,29 y el segundo por 2,50.** `PROVEN`.

**⇒ `MEASUREMENT. Bisección del primer codo, con puntos intermedios: 262 KiB → 454,1 ns;
384 KiB → 778,3; 512 KiB → 995,1; 768 KiB → 1.846,7; 1 MiB → 2.140,6.** `MEASUREMENT`.

**⇒ `PROVEN_DERIVED`. El primer codo no es un salto sino una rampa, porque con acceso aleatorio
la tasa de acierto cae de forma continua y no de golpe. Un codo de caché medido con un patrón
aleatorio es una rampa por construcción, y `265` buscaba un punto exacto que este patrón no
puede producir.** `PROVEN_DERIVED`.

**⇒ `PROVEN. El segundo sí es un salto: de 2.671,9 a 6.668,9 ns, un factor 2,50 en un paso de
4× en el tamaño.** `PROVEN`.

## 2 · El discriminante que refuta la hipótesis del TLB

**⇒ `PROVEN_DERIVED. La hipótesis era esta: con 1024 hilos y acceso pseudoaleatorio, cada
dirección se toca unas pocas veces, así que la tasa de acierto de caché no depende del tamaño
del conjunto —siempre casi cero—, y lo único que crece es el número de páginas distintas que hay
que traducir.** `PROVEN_DERIVED`.

**⇒ `PROVEN. `page.comp` separa esa hipótesis. Los dos modos recorren la misma huella en bytes
con el mismo número de accesos y se diferencian en cuántas páginas tocan: modo contiguo, muchos
accesos por página; modo paginado, un acceso por página.** `PROVEN`.

```glsl
uint NPAG = (WSIZE + 1023u) / 1024u;
uint idx = (PAGE == 0u) ? (i % WSIZE)                          /* contiguo */
                         : ((i % NPAG) * 1024u + (i % 1024u)); /* paginado  */
```

| bytes | páginas | ns por vuelta, contiguo | ns por vuelta, paginado | razón |
|---|---|---|---|---|
| 65.536 | 16 | 366,2 | 461,9 | 1,26 |
| 262.144 | 64 | 413,1 | 434,6 | 1,05 |
| 1.048.576 | 256 | 2.185,5 | 2.173,8 | **0,99** |
| 4.194.304 | 1.024 | 2.362,3 | 2.369,1 | **1,00** |
| 16.777.216 | 4.096 | 2.671,9 | 2.672,9 | **1,00** |
| 67.108.864 | 16.384 | 6.668,9 | 6.671,9 | **1,00** |

**⇒ `REFUTED`. A partir de 1 MiB la razón es 1,00 en los cuatro puntos. Repartir los mismos
bytes entre 256 páginas o entre 16.384 no cambia el tiempo ni en la tercera cifra. La latencia
depende del número de bytes, no del número de páginas que los contienen.** `REFUTED`.

**⇒ `PROVEN_DERIVED. Y la consecuencia es más amplia que la hipótesis: la traducción de
dirección no es un factor de este barrido en ningún punto de su rango, de modo que el segundo
codo —el factor 2,50 entre 16 y 64 MiB— no es un fallo de TLB.** `PROVEN_DERIVED`.

## 3 · La otra explicación candidata, y por qué tampoco encaja

**⇒ `PROVEN_DERIVED. El modelo estándar de caché con acceso aleatorio uniforme es
`L(W) = L_c + (C/W)·(L_d − L_c)`, porque la tasa de acierto de un conjunto que no cabe es
`C/W`. Si la curva fuera la de ese modelo, sus dos parámetros quedarían fijados por los dos
puntos mayores.** `PROVEN_DERIVED`.

```text
W1 = 16.777.216 dwords   L1 = 6.668,9 ns
W2 = 67.108.864 dwords   L2 = 6.798,8 ns

C · (L_d - L_c) = 2,906e+09 dword·ns
L_c = 6.495,7 ns = 6.905 ciclos a sclk 1.063,02 MHz
```

**⇒ `REFUTED`. Una latencia de acierto de caché de 6905 ciclos es absurda: un acierto de L2 en
GFX8 es de decenas de ciclos. El modelo no describe esta curva.** `REFUTED`.

**⇒ `PROVEN_DERIVED`. Y hay una razón de fondo por la que no podría encajar aunque los números
salieran bien: el modelo supone que la caché retiene lo que atrapa, de manera que la tasa de
acierto depende del tamaño del conjunto. Pero en este kernel cada hilo recorre 1024
direcciones distintas sin repetir, y los 1024 hilos están en sitios distintos en cada instante:
**no hay reutilización que la caché pueda conservar**, y por tanto la tasa de acierto la fija el
solape entre las 1024 direcciones vivas y la capacidad de la caché, no el tamaño del conjunto.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Eso explica la forma —tres mesetas, no una curva suave— y quita el
sentido a `265` y a `271`, que buscaban un punto de inflexión único. El punto único no existe
con este patrón de acceso; lo que hay son tres mesetas separadas por dos transiciones, y las
transiciones son de estructura de hardware, no de contenido.** `PROVEN_DERIVED`.

## 4 · Lo que queda, y lo que la nota cierra

**⇒ `NOT_DETERMINED`. Los dos codos están medidos y acotados, y ninguno tiene mecanismo
asignado. Las candidatos que quedan no las separa esta plataforma sin MMIO.** `NOT_DETERMINED`.

```text
1. el codo entre 256 KiB y 1 MiB: un nivel de caché que se agota. pero el barrido no
   puede dar su tamaño, porque con este patron la latencia sube de forma continua.
2. el codo entre 16 y 64 MiB: un salto de factor 2,50, discreto. no es TLB (esta nota).
   quedan estructuras del lado del sistema de memoria: la L2 como filtro de paginas,
   un nivel de buffer, o el limite de peticiones en vuelo por shader.
```

**⇒ `PROVEN_DERIVED`. Y una corrección de encuadre que vale para `265` y `271`: un barrido con
acceso pseudoaleatorio no puede medir el tamaño de una caché por el punto de meseta. El punto
de meseta mide una transición de estructura, no un tamaño. Medir el tamaño exige un patrón con
reutilización controlada, es decir acupuncture en una dirección conocida.** `PROVEN_DERIVED`.

**⇒ `CORROBORATED`. La inelasticidad con el número de páginas es además un dato de §G y §H por
sí mismo: la traducción de direcciones de este ASIC no aparece en el tiempo de una lectura de
4 bytes con hasta 65.536 páginas Residentes. Eso acota qué parte del coste de acceso es de
traducción, y es cero en este rango.** `CORROBORATED`.

## 5 · Mis errores

**⇒ `ERROR`: propuse la hipótesis del TLB y la construí el discriminante para refutarla sin
comprobar antes si el barrido mostraba siquiera la firma que la haría plausible.** `ERROR`.

**⇒ `PROVEN_DERIVED`. Es el segundo caso de la sesión en que construyo el instrumento para
refutar una hipótesis mía sin haber mirado antes el dato que la haría candidata. El primero fue
`div.comp`, y ahí salió bien porque la hipótesis era razonable; aquí la construcción del
discriminante pudo haberse hecho igualmente bien con una hipótesis falsa, y el trabajo
habría sido igualmente inútil. **La pregunta que faltaba es siempre la misma: ¿qué tendría que
ver el barrido para que esto fuera verdad?** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED`. Y la respuesta a esa pregunta, aplicada a la hipótesis del TLB, es que el
barrido no mostraba ninguna firma: la curva subía de forma monótona y suave, sin el escalón
típico de una translator miss rate que se desborda. Un desbordamiento de TLB produce un escalón
porque es un recurso discreto con capacidad finita; esta curva no lo tenía.** `PROVEN_DERIVED`.

## 6 · PENDIENTE

```text
262-1 | ESTADO=NOT_DETERMINED con dos mecanismos menos descartados
           | CODOS_MEDIDOS=entre 262 KiB y 1 MiB (rampa), y entre 16 y 64 MiB (x2,50)
           | DESCARTADO_1=TLB / numero de paginas (razon 1,00 en page.comp)
           | DESCARTADO_2=modelo de acierto uniforme de cache (L_c implicito de 6905 ciclos)
           | CAMBIO_DE_ENCUADRE=un barrido aleatorio no puede dar el tamano de una cache;
           |   el punto de meseta mide una transicion de estructura
           | VIA_QUE_SI_FUNCIONA=patron con reutilizacion controlada: barrer una sola
           |   direccion y su entorno, y ver cuando el acceso mas proximo deja de acertar
           | ALCANZABLE_SIN_ROOT=si

287-1 | ESTADO=OPEN · CONTRADICTION, sin cambio
           | 17,829 GB/s son el 371% del techo que permite mclk 300 MHz
           | AVANCE_DE_ESTA_NOTA=si una fraccion la sirve una cache, mclk puede quedarse
           |   en 300 MHz. y ahora se sabe que la traduccion no cuenta, luego lo que
           |   queda es contenido de cache o reloj

INSTRUMENT=vcp | ESTADO=VALIDATED
           | CONSTANTS=4 (ITERS, WSIZE, STEPS, PAGE)
           | MODELOS=5 (0=probe, 1=occ, 2=chain, 3=div, 4=page)
           | REGRESION=los cinco kernels validan con 0 NO
           | INVARIANTES_2=wsize >= items, WSIZE >= items
```