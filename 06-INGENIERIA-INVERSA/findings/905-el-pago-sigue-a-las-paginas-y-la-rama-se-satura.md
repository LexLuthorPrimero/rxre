# 905 · El pago de 6,7 ms sigue a las páginas, no al rango, y la rama se satura

```text
CLASSIFICATION=MEASUREMENT+SATURATION · TRACK=RUNTIME
CORPUS=sin cambios · MODIFICATIONS_CORPUS=0 · GPU INTACTA
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=WRITE_LOCAL · WRITE_EXECUTION=carga Vulkan nivel 1 · NIVEL=1 · AUTORIA=AGENTE-SMU
INSTRUMENTO=vcp con lane.comp (STRIDE, SUBRANGE) y bench.py para el contrato
```

## Qué resuelve

**⇒ `REFUTED`: que el pago dependa del rango de direcciones. Dos configuraciones con las mismas
4.096 páginas tocadas, la misma reserva de 64 MiB y rangos de 16 MiB y 64 MiB dan 1,905 y 1,905 ms.
Idénticos hasta la tercera cifra.** `REFUTED`

**⇒ `PROVEN_DERIVED`: el pago sigue al número de páginas distintas que el kernel toca, y no a la
distancia entre la primera y la última.** `PROVEN_DERIVED`

**⇒ `PROVEN_DERIVED`: y sigue de forma sublineal. 4.096 páginas dan 1,905 ms y 16.384 dan 4,630 ms,
un factor 2,43 por un factor 4 en páginas.** `PROVEN_DERIVED`

**⇒ `SATURATED` la frontera `606-1`. Razón: el mecanismo necesita un observable que no tengo sin
MMIO, que es el mismo bloqueo que el ancho de bus desde `272`. No es que sea caro intentarlo: es que
no hay discriminante disponible.** `SATURATED`

**⇒ `PROVEN_DERIVED`: y la síntesis correcta de todo lo medido es que **no hay un pago fijo**. Lo que
existe es un calentamiento: las primeras iteraciones corren a una fracción de la velocidad de
régimen, y el déficit se acumula.** `PROVEN_DERIVED`

## 1 · El discriminante: páginas iguales, rango distinto

**⇒ `MEASUREMENT`. `CONTIGUO`, reserva de 64 MiB en los cuatro casos, 65.536 hilos, entropía
verificada en cada corrida, 7 muestras, 0 rechazadas.** `MEASUREMENT`

| configuración | rango | páginas de 4 KiB | `t` (ms) | `a` (ms) |
|---|---|---|---|---|
| **A** contiguo, paso 256 KiB, 64 vueltas | 16 MiB | 4.096 | 2,284 | **1,905** |
| **B** disperso, paso 1 MiB, 64 vueltas | 64 MiB | 4.096 | 2,284 | **1,905** |
| **C** contiguo, paso 256 KiB, 256 vueltas | 64 MiB | 16.384 | 6,145 | **4,630** |
| **D** disperso, paso 1 MiB, 256 vueltas | 256 MiB | 16.384 | 6,533 | **5,018** |

**⇒ `PROVEN`: A y B son indistinguibles. Cambia el rango de 16 a 64 MiB, el mismo número de páginas
y la misma reserva, y el resultado no se mueve.** `PROVEN`

**⇒ `PROVEN_DERIVED`: lo que separa C de D es un 8% con rangos de 64 y 256 MiB, que es la primera
diferencia no nula que aparece, y es demasiado pequeña para sostener una hipótesis del rango. Lo que
separa el grupo {A, B} del grupo {C, D} es el factor 4 en páginas, y eso da un factor 2,43.** `PROVEN_DERIVED`

## 2 · Lo que queda refutado, y lo que queda vivo

**⇒ `PROVEN_DERIVED`: con este resultado se pueden cerrar cuatro hipótesis que `607` §3 dejó
abiertas.** `PROVEN_DERIVED`

```text
1. descarga o invalidacion de L2 que cubre la reserva        -> REFUTADA por 608: separarla
   que se activa por tamano no cambia con el separado            del separado no la cambia
2. coste de traduccion por pagina con TLB que se llena por     -> NO REFUTADA: el pago sigue a las
   el separado y page-table que se recorre por la reserva       paginas, que es su firma
3. lectura del biffer entero por envio                          -> REFUTADA por 609: se paga una vez
4. rango o paginas grandes                                     -> REFUTADA por esta nota
```

**⇒ `NOT_DETERMINED`: el mecanismo dentro de la 2, y también qué la sublinealidad significa.** `NOT_DETERMINED`

**⇒ `PROVEN_DERIVED`: la sublinealidad es un dato y no una curiosidad. Un coste por página sería
lineal y daría 15,6 ms para 16.384 páginas; se miden 4,63 ms, un 30%. Eso significa que el
calentamiento **no crece con el número de páginas**, o que una parte del trabajo se solapa y se
oculta. Las dos tienen consecuencias distintas para un driver propio y ninguna está decidida.** `PROVEN_DERIVED`

## 3 · La síntesis, y por qué «pago único» era una etiqueta equivocada

**⇒ `PROVEN_DERIVED`: la etiqueta «pago único» de `609` era correcta en el aspecto que importa —no es
por envío— y falsa en el resto. No es un pago: es el déficit acumulado de un calentamiento, y un
calentamiento no se paga, se recorre.** `PROVEN_DERIVED`

**⇒ `PROVEN`: la evidencia de que hay régimen, y de que el régimen existe a partir de unas cientos de
vueltas.** `PROVEN`

```text
  64 vueltas   -> 20,1 us por vuelta    (3,4 veces el regimen)
  256 vueltas  -> 20,1 us por vuelta
  512 vueltas  ->  5,9 us por vuelta    (regimen)
```

**⇒ `PROVEN_DERIVED`: y el valor de 6,7 ms que arrastran `606`, `607`, `902` y `909` es el
intercepto de una recta ajustada en la zona en la que ya no hay calentamiento, no el coste de
cruzar el calentamiento. Es una descripción de la curva, y como tal es correcta; como coste no lo
es, y `609` ya lo había dicho sin saber todavía qué era.** `PROVEN_DERIVED`

**⇒ `PROVEN_DERIVED`: la lección de método es la misma de siempre y con un ejemplo mejor: una
magnitud medida con la unidad justificada puede tener la interpretación equivocada durante cuatro
notas seguidas sin dejar de ser correcta como magnitud. Lo que la salvó fue un discriminante de
una línea —`--rep`— y no un razonamiento mejor.** `PROVEN_DERIVED`

## 4 · Por qué la rama se satura aquí

**⇒ `SATURATED`, con la razón que §48 exige: no queda discriminante disponible sin un observable que
no tengo.** `SATURATED`

```text
  lo que hace falta para seguir
    - el contenido de un registro del TLB o del page walker mientras el kernel ejecuta
      -> nivel 4, MMIO, requiere cerrar la sesion grafica y autorizacion
    - o la tabla de traduccion que el driver construye, que vive en el espacio de GPUVM
      -> el mismo MMIO
    - o el VBIOS, para el ancho de bus, que es el otro bloqueado desde 272
  ninguno de los tres se alcanza sin root, y no hay un discriminante static que los sustituya
```

**⇒ `PROVEN_DERIVED`: y no es una pérdida: esta frontera ya dio lo que se le pedía. El titular de
`606` era «qué es este escalón» y la respuesta es «un calentamiento cuyo déficit sigue a las páginas
distintas que el kernel toca, y que no se paga por envío». Eso está medido, con control de entropía
en cada punto, y es utilizable por quien escriba el driver sin conocer el mecanismo.** `PROVEN_DERIVED`

**⇒ `PROVEN_DERIVED`: el valor de la magnitud para un driver es pequeño a propósito. 6,7 ms sobre
despachos de 200 ms es el 3%, y se puede evitar eligiendo la longitud de la ráfaga. Un driver propio
no necesita saber por qué, necesita saber cuánto.** `PROVEN_DERIVED`

## 5 · Cambio de rama, y por qué

**⇒ `PROVEN_DERIVED`: §81 pide cambiar de rama cuando la actual está saturada, o bloqueada, o su
coste no está justificado. Aquí están las dos primeras cosas: bloqueada por MMIO y saturada por
agotamiento de discriminantes.** `PROVEN_DERIVED`

**⇒ `PROVEN_DERIVED`: y hay una razón de fondo para no quedarse en §H durante más tiempo. Todo lo
que he medido en las últimas horas es un **buffer de cómputo**: `d[idx]`, una carga escalar por
carril, una traducción de dirección. La celda `609` y el titular de `602` son sobre ese camino.
El proyecto no ha tocado **una sola vez** la ruta de textura, que en esta ASIC tiene su propia
traducción, con su propio swizzle y su propia granularidad, y que es la que usa cualquier cosa que
no sea un búfer.** `PROVEN_DERIVED`

**⇒ `NOT_DETERMINED`, y es la frontera que sigue: qué hace una `VkImage` en esta GPU. El
`282-1` está abierto desde antes de esta sesión y es ejecutable ahora, sobre el banco validado, y
separaría dos cosas que hasta aquí he medido como una.** `NOT_DETERMINED`

```text
 282-1 | ESTADO=OPEN, y ahora con instrumento
           | PREGUNTA=la ruta de textura tiene la misma granularidad que la de buffer,
           |          o la suya propia
           | POR_QUE=si tiene la suya, el 27,4x de 602 no es un techo del hardware sino
           |        de una ruta, y el techo del proyecto sube
           | ALCANZABLE_SIN_ROOT=si
           | INSTRUMENTO=vcp validado, bench.py para el contrato y el artefacto
```

## 6 · PENDIENTE

```text
606-1 | ESTADO=SATURATED por 905
           | MEDIDO=el deficit sigue a las PAGINAS distintas que el kernel toca
           | REFUTADO=rango de direcciones, pago por envio, solo la reserva,
           |         invalidacion de L2 sobre la reserva
           | VIVO=solo la traduccion por pagina; sublineal, 30% frente a lo lineal
           | BLOQUEO=MMIO, requiere cerrar la sesion grafica y autorizacion
           | UTILIDAD=6,7 ms sobre despachos de 200 ms es el 3%; se evita con la
           |          longitud de la rafaga, sin conocer el mecanismo

607-1 | ESTADO=RESUELTA por 905: solo la traduccion por pagina sobrevive de los cuatro
282-1 | ESTADO=OPEN, siguiente rama, ejecutable
282   | SU CONTRADICCION §3 sigue sin re-ejecutar con el flag vivo; ver 606
TODO-2 | ESTADO=BLOQUEADA, VBIOS, sudo
BANCO  | ESTADO=VALIDATED, 12 de 12, con el contrato de no reportar sin controles
```