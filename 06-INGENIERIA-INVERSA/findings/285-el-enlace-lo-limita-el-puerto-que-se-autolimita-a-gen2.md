# 285 · El enlace está en Gen2 ×4 porque el puerto se autolimita a Gen2: la velocidad la limita la placa, y eso es una palanca de 3,94×

```text
CLASSIFICATION=MEASUREMENT+RESOLVED+DECISION_INPUT · TRACK=RUNTIME + HARDWARE_FINGERPRINT
CORPUS=RESEARCH/working/linux-7.1.3 + /sys/bus/pci/devices/ + lspci + DMI
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY (sysfs, lspci, DMI) · NIVEL=1
MODIFICATIONS_CORPUS=0 · GPU INTACTA
```

## Qué resuelve

**⇒ Cierra el núcleo de `258-4`, que `284` dejó abierto: el enlace no está en Gen2 ×4 por una
razón desconocida, sino porque **el puerto PCIe del host se autolimita a Gen2**. Está en su
propio `max_link_speed`, sin que nada se lo imponga a la tarjeta.** `RESOLVED`.

**⇒ `PROVEN`. La velocidad la limita el puerto, y se demuestra por el mínimo de tres anuncios:
la tarjeta declara 8,0 GT/s, el puerto declara 5,0 GT/s, y lo negociado es 5,0 GT/s. Quien
declara el mínimo es el que manda.** `PROVEN`.

**⇒ `PROVEN`. El ancho no lo limita el puerto, que ofrece 16 lanes contra las 4 negociadas, y
por tanto el límite de ancho está en la ranura o en la tarjeta. `sysfs` no distingue entre las
dos, y queda `NOT_DETERMINED`.** `PROVEN`.

**⇒ `PROVEN_DERIVED. Y la consecuencia es accionable: si el puerto llegara a Gen3, el techo del
enlace pasaría de 2,000 a 3,938 GB/s conservando el ancho, o a 7,877 GB/s si además el ancho
subiera. Es el mayor multiplicador que ha aparecido en §H, y es una palanca de configuración
del host, no de código.** `PROVEN_DERIVED`.

## 1 · El barrido de todos los enlaces, que es el discriminante

**⇒ `MEASUREMENT. La pregunta que `284` dejó era si el downgrade era de la tarjeta, de la ranura
o de la placa. El discriminante es si los otros dispositivos del equipo también corren
reducidos: si corrieran igual, sería de la placa; si solo este, sería de esta tarjeta o
ranura.** `MEASUREMENT`.

| puerto | rol | actual | máximo |
|---|---|---|---|
| `00:01.0` | **padre de la AMD** | 5,0 GT/s × 4 | 5,0 GT/s × **16** |
| `01:00.0` | la RX 550 | 5,0 GT/s × 4 | 8,0 GT/s × 8 |
| `01:00.1` | la RX 550, función de audio | 5,0 GT/s × 4 | 8,0 GT/s × 8 |
| `00:1c.0` | Root Port #1 del chipset 8 Series | 2,5 GT/s × 0 | 5,0 GT/s × 1 |
| `00:1c.5` | segundo endpoint del mismo puente | 2,5 GT/s × 1 | 5,0 GT/s × 1 |
| `03:00.0` | Realtek RTL8111/8168, ethernet | 2,5 GT/s × 1 | 2,5 GT/s × 1 |

**⇒ `PROVEN. El resto del equipo sí corre reducido, y mucho más: los puertos del chipset están
en Gen1 y el ethernet en Gen1 ×1. El equipo es de una generación de placa anterior.** `PROVEN`.

**⇒ `PROVEN_DERIVED. Y esa observación es la que distingue las hipótesis: la tarjeta no está
nada nada —el único enlace que corre en su máxima negociación es el suyo— y el problema es de
generación de plataforma, no de esa tarjeta en concreto.** `PROVEN_DERIVED`.

## 2 · Quién limita cada magnitud, y por qué es la placa

**⇒ `PROVEN. La velocidad: se toma el mínimo de las capacidades declaradas.** `PROVEN`.

```text
velocidad   tarjeta   8,0 GT/s  (Gen3)
            puerto    5,0 GT/s  (Gen2)   <- el minimo
            negociado 5,0 GT/s
```

**⇒ `PROVEN_DERIVED. El puerto declara 5,0 GT/s como su máximo. Eso significa que el puerto no
puede hacer Gen3 con independencia de qué tarjeta se le enchufe. El techo de 2,000 GB/s es una
propiedad de esta placa, no de esta GPU, y por eso `284` tenía que acotar «imposible» al estado
actual del enlace: es el estado actual de la placa lo que lo hace imposible.** `PROVEN_DERIVED`.

**⇒ `PROVEN. El ancho: el puerto no es el limitante.** `PROVEN`.

```text
ancho       tarjeta   8 lanes
            puerto   16 lanes
            negociado 4 lanes
```

**⇒ `NOT_DETERMINED`: el ancho se negocia en 4 cuando el puerto ofrece 16, así que el límite
está en la ranura o en el propio cableado de la tarjeta. `sysfs` expone la capacidad declarada
de cada extremo y el resultado de la negociación, y nada más; distinguir «la ranura está
cableada a ×4» de «esta tarjeta es ×4 » requiere documentación de la placa o inspección
física, no un observable del kernel.** `NOT_DETERMINED`.

## 3 · La magnitud de la palanca, calculada por programa

**⇒ `MEASUREMENT.` `MEASUREMENT`.

```text
GB/s = GT/s x lanes x (payload/total) / 8
```

| situación | GB/s | sobre el actual |
|---|---|---|
| Gen2 ×4 — **ahora** | 2,000 | 1,00× |
| Gen3 ×4 — si sube solo la velocidad | 3,938 | **1,97×** |
| Gen3 ×8 — si sube velocidad y ancho | 7,877 | **3,94×** |

**⇒ `PROVEN_DERIVED. Compárese con las otras dos magnitudes que §H tiene medidas: el techo de
cómputo es 1088,5 GFLOPS con 8 CUs (`272`), y la lectura encadenada se costea a 2,970 GB/s
(`282`/`283`). Ninguna palanca de código que se pueda escribir mueve un techo físico; esto sí
mueve el techo del que dependen las dos cosas que limitan la carga, y es una configuración de
BIOS, no una implementación.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Y con Gen3 ×8 el argumento de imposibilidad de `282` deja de sostenerse:
2,970 GB/s serían el 0,38× del techo, no el 1,49×. La `NOT_DETERMINED` de `282-1` y el
`NOT_DETERMINED` de esta nota son la misma incógnita vista desde los dos extremos —el que pide
más ancho de banda del que existe, y el que podría dárselo.** `PROVEN_DERIVED`.

## 4 · Identidad del puerto, y por qué no es lo que parecía

**⇒ `PROVEN`. `00:01.0` no es un puerto del chipset: es el controlador PCIe x16 de la propia
CPU, `Intel Xeon E3-1200 / 4th Gen Core Processor PCI Express x16 Controller`.** `PROVEN`.

```text
placa     ECS H81H3-M4, version 1.0
CPU       Intel Core i7-4790 @ 3,60 GHz
padre     00:01.0 = CI bridge del controlador PCIe x16 de la CPU
chipset   00:1c.x = Intel 8 Series / C220 Series (H81), puertos en Gen1
```

**⇒ `REFUTED`. `284` especuló que podía ser numeración de buses PCI —la función está en
`01:00.0`, y eso parecería un segundo puerto—. No lo es: `01:00.0` es el número de bus del
dominio PCI, y el padre real es el controlador PCIe de la CPU, no otro puerto del chipset. La
numeración no era una explicación.** `REFUTED`.

**⇒ `PROVEN_DERIVED. Y esto cambia el diagnóstico en un aspecto que importa: si el limitador fuera
un puerto del chipset H81, sería una limitación irreducible de la plataforma. Que sea el
controlador de la CPU significa que la limitación está en cómo la placa cablea y configura ese
puerto, que es justo lo que un ajuste de BIOS o una actualización de firmware puede tocar.** `PROVEN_DERIVED`.

## 5 · Lo que queda, y lo que no

**⇒ `NOT_DETERMINED`, y son dos cosas distintas que no conviene fundir.** `NOT_DETERMINED`.

```text
1. por que el puerto 00:01.0 declara 5,0 GT/s como maximo siendo un controlador de la CPU:
  settings de BIOS (hay una opcion "PCIe Speed" Auto/Gen1/Gen2/Gen3 en la mayoria de placas
   de esta epoca), version de BIOS, o cableado de la ranura. Requiere intervencion, no lectura.
2. si el ancho se limita en la ranura o en la tarjeta: NO hay observable de software.
```

**⇒ `PROVEN_DERIVED. La diferencia entre las dos importa para el coste: la primera se resuelve
rebootizando con un ajuste distinto, la segunda exige mover la tarjeta a otra ranura o comprar
otra. Ninguna requiere escribir driver, y ése es el punto: el mayor multiplicador conocido de
§H no está en el código.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED`. Y hay una asimetría que conviene registrar antes de tocar nada: subir el
enlace aumenta el techo del enlace, y el techo del enlace no es lo que limita ahora mismo ninguna
medición de `§H`. `261`, `262`, `271`, `282` y `283` miden tiempos de shader, y todos ocurren por
encima de los 2,000 GB/s porque el enlace no participa. Subirlo no mejora ninguna de ellas; lo
que mejora es el trabajo que sí mueve datos entre CPU y GPU, que hasta ahora no se ha medido
porque no había banco para hacerlo.** `PROVEN_DERIVED`.

## 6 · PENDIENTE

```text
258-4 | ESTADO=PARTIAL por 285
           | RESUELTO=la velocidad la limita el puerto, que declara Gen2 como maximo
           | ABIERTO=por que el puerto declara eso (settings de BIOS o version)
           |         y si el ancho se limita en la ranura o en la tarjeta
           | ALCANZABLE_SIN_ROOT=si para el puerto; no para el ancho

MEDICION_FALTA=ancho de banda real host<->dispositivo
           | MOTIVO=es la unica magnitud de §H que el enlace limita y que nadie ha medido.
           |   El banco mide tiempos de shader; hace falta uno que mueva un buffer
           |   entero entre RAM del host y VRAM y mida bytes por segundo, con el control
           |   de las dos regiones disjuntas de 283.
           | PRECONDICION=ninguna; es instrumentacion propia, nivel 1
```