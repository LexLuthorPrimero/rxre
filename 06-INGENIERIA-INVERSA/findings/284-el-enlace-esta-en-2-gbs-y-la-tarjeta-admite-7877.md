# 284 · Auditoría del número que sostiene a `282`: el enlace está en 2,00 GB/s, la tarjeta admite 7,877 GB/s, y `258` se equivocó en el techo de mejora

```text
CLASSIFICATION=AUDIT+MEASUREMENT+ERROR_CORRECTION · TRACK=RUNTIME + HARDWARE_FINGERPRINT
CORPUS=RESEARCH/working/linux-7.1.3 + /sys/bus/pci/devices/0000:01:00.0
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY (sysfs y findings) · NIVEL=1
MODIFICATIONS_CORPUS=0 · GPU INTACTA
PROVENCIA_DE_LA_CODIFICACION=especificación PCIe (NO es corpus del proyecto)
```

## Qué resuelve

**⇒ `PROVEN`. El argumento central de `282` —que una lectura de 4 B encadenada no puede costar
2,970 GB/s— se apoya en el techo de 2,000 GB/s de `258`, y ese número queda verificado contra
`sysfs`: `current_link_speed` = 5,0 GT/s y `current_link_width` = 4.** `PROVEN`.

**⇒ `PROVEN`. Pero la misma fuente que verifica el 2,000 GB/s desmiente el techo de mejora que
`258` publica: `max_link_speed` = 8,0 GT/s y `max_link_width` = 8. La tarjeta admite 7,877 GB/s,
no 6,40 GB/s.** `PROVEN`.

**⇒ `ERROR_CORRECTION`: `258` aplicó codificación 8b/10b a Gen3, que usa 128b/130b. El margen de
mejora del enlace es 3,94 veces, no 3,2.** `ERROR_CORRECTION`.

**⇒ `PROVEN_DERIVED`. La conclusión de `282` sobrevive y queda acotada: los 2,970 GB/s superan
en 1,49× el enlace **actual**, y son sólo el 0,38× del enlace **máximo** de la tarjeta. «Imposible»
es una afirmación sobre el estado actual del enlace, no sobre el hardware.** `PROVEN_DERIVED`.

## 1 · La auditoría, y por qué era la acción correcta

**⇒ `PROVEN_DERIVED. `282` publicó que una medición superaba en 1,49× un techo físico, y todo el
peso de la conclusión descansaba en ese techo. Un número del que depende una afirmación de
imposibilidad es un número que hay que auditar antes de construir encima, y yo había construido
dos notas encima sin comprobarlo.** `PROVEN_DERIVED`.

**⇒ `PROVEN. La fuente primaria es `sysfs`, y los cuatro campos existen sin root.** `PROVEN`.

```text
/sys/bus/pci/devices/0000:01:00.0/current_link_speed   = 5.0 GT/s PCIe
/sys/bus/pci/devices/0000:01:00.0/current_link_width   = 4
/sys/bus/pci/devices/0000:01:00.0/max_link_speed       = 8.0 GT/s PCIe
/sys/bus/pci/devices/0000:01:00.0/max_link_width       = 8
```

**⇒ `CORROBORATED`. `258` ya había usado `current_link_speed` y `current_link_width`, luego su
cifra de 2,00 GB/s es correcta y no necesita corrección. Lo que estaba mal era el otro número,
el del techo máximo, que salió de la misma lectura pero con una regla de codificación
equivocada.** `CORROBORATED`.

## 2 · El error de `258`, y por qué la conclusión sobrevive

**⇒ `ERROR_CORRECTION`. `258` §2 dice «PCIe, con codificación 8b/10b» y aplica ese factor tanto a
Gen2 como a Gen3.** `ERROR_CORRECTION`.

```text
la especificacion de PCIe:
  Gen1, Gen2   -> 8b/10b     sobrecarga del 20%
  Gen3 y posteriores -> 128b/130b   sobrecarga del 1,5625%
```

**⇒ `PROVEN`. Con las dos codificaciones, calculadas por programa:** `PROVEN`.

| magnitud | GB/s |
|---|---|
| Gen2 ×4, 8b/10b — enlace **actual** | 2,000 |
| Gen3 ×8, 8b/10b — lo que publica `258` | 6,400 |
| Gen3 ×8, 128b/130b — **correcto** | **7,877** |

**⇒ `ERROR_CORRECTION`: el margen de mejora del enlace es 3,94 veces, de 2,000 a 7,877 GB/s, no 3,2
veces de 2,00 a 6,40. El error de `258` es del 18,8% sobre el techo máximo.** `ERROR_CORRECTION`.

**⇒ `PROVEN_DERIVED. Y la conclusión de `258` no se mueve: «incluso con el enlace al máximo el
equipo seguiría siendo link-bound» sigue siendo cierto, y con más holgura. 7,877 contra 24,0 GB/s
de VRAM son 3,0 veces, donde `258` calculaba 3,75. El razonamiento —la VRAM es más ancha que
cualquier enlace PCIe que esta placa pueda negociar— no dependía del número exacto, y por eso
un error del 18,8% en el techo no lo tumba.** `PROVEN_DERIVED`.

**⇒ `NOT_DETERMINED`: por qué el enlace está en Gen2 ×4 y no en Gen3 ×8 sigue sin respuesta, y
`258` ya lo había marcado así. No es el PCI bus numbering, porque la función está en `01:00.0`
y su padre es `00:01.0`, o sea el segundo puerto, no el primero.** `NOT_DETERMINED`.

## 3 · Un control independiente de la codificación, que sí tengo

**⇒ `CORROBORATED. La codificación del enlace actual se puede corroborar con una medición
independiente: la copia de staging que `270` midió a 1,228 GB/s.** `CORROBORATED`.

```text
si el enlace fuera Gen2 x4 con 8b/10b  -> techo 2,000 GB/s -> 1,228 es el 61,4%
si el enlace fuera Gen3 x8 con 128b/130b -> techo 7,877 GB/s -> 1,228 seria el 15,6%
```

**⇒ `PROVEN_DERIVED. El 61,4% es una eficiencia plausible para una copia host→dispositivo con
buffer de combinación por escritura. El 15,6% no lo es: una copia de staging que rindiera una
sextava parte del enlace significaría que el cuello está en otro sitio, y `270` ya mostró que no
lo está, porque con el banco corregido el coste por palabra bajó 9,5 veces y el PCIe dejó de
aparecer.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. De modo que la medición de `270` corrobora el 8b/10b del Gen2 por una vía que
no pasa por la especificación: el número que `258` saco de `sysfs` y el número que `270` midió
en runtime se confirman mutuamente.** `PROVEN_DERIVED`.

## 4 · La corrección que hay que hacer en `282`

**⇒ `PROVEN_DERIVED. La afirmación de `282` §3 —«3,013 GB/s es imposible en esta placa por una
razón que no depende del número de CUs ni del tamaño de caché»— es correcta, pero su alcance es
más estrecho del que la prosa sugiere. Es imposible dado el estado actual del enlace, no dado
el hardware.** `PROVEN_DERIVED`.

```text
lectura medida            2,970 GB/s
techo del enlace ACTUAL   2,000 GB/s   ->  1,49x  IMPOSIBLE AHORA
techo del enlace MAXIMO   7,877 GB/s   ->  0,38x  cabria de sobra
```

**⇒ `PROVEN_DERIVED. Y esa diferencia importa para el proyecto, porque es actionable: si el
enlace se negocia en Gen3 ×8, la lectura medida deja de ser imposible por el argumento del
enlace, y el `NOT_DETERMINED` de `282-1` vuelve a abrirse con la vía del enlace como
hipótesis más.** `PROVEN_DERIVED`.

**⇒ `NOT_DETERMINED`: si el argumento de `282` se sostiene o no depende del enlace, y el enlace
está en Gen2 ×4 por una razón que no se sabe. Son dos incógnitas encadenadas, y la segunda
bloquea a la primera.** `NOT_DETERMINED`.

## 5 · Errores y método

**⇒ `ERROR`: construí dos notas —`282` y `283`— sobre un techo que no había auditado, y el
techo tenía un error del 18,8% en su mitad superior.** `ERROR`.

**⇒ `PROVEN_DERIVED. La forma es la de siempre y con una variante nueva: el error estaba en el
dato heredado, no en el que medía. Es el primer caso en esta tanda donde el número que me delata
no es el mío, y aun así es mío — porque elegir el número sin verificar su
decisión mía.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Y la regla que esto añade es la más obvia y la que más he incumplido: un
número que se usa para declarar una imposibilidad es un número que hay que derivar del
observable, no de la nota que lo publicó. `258` es un hallazgo mío y por eso mismo es
justamente el que tenía que auditar.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Una consecuencia útil: `NOT_DETERMINED` no es sólo un estado de ignorance,
es un estado que se puede cerrar. El motivo por el que el enlace está en Gen2 ×4 se conocía
como misterio desde `258`; esta nota lo reformula en términos consultables —`max_link_speed` y
`max_link_width` están en `sysfs` sin root— y lo convierte en una pregunta con observable.** `PROVEN_DERIVED`.

## 6 · PENDIENTE

```text
PENDIENTE=258-4 | HALLAZGO=284-*.md | ESTADO=OPEN
           | PREGUNTA=¿por que el enlace se negocia en 5,0 GT/s x4 si la tarjeta admite
           |          8,0 GT/s x8? la funcion esta en 01:00.0 con padre 00:01.0.
           | OBSERVABLES_SIN_ROOT: max_link_speed, max_link_width (ya leidos);
           |   el estado del puerto padre 00:01.0 en /sys/bus/pci/devices/
           | ALCANZABLE_SIN_ROOT=si

CORRECCION=258-2 | APLICADA_EN=258
           | QUE=techo maximo del enlace: 6,40 GB/s -> 7,877 GB/s
           | POR_QUE=258 aplico 8b/10b a Gen3, que usa 128b/130b
           | AFECTA_A=margen de mejora 3,2x -> 3,94x
           | NO_AFECTA_A=la conclusion link-bound, que sigue siendo cierta

ALCANCE=282-3 | APLICADA_EN=282
           | QUE='imposible' pasa a ser 'imposible con el enlace actual'
           | POR_QUE=2,970 GB/s es 1,49x el enlace actual pero 0,38x el maximo de la tarjeta
```
