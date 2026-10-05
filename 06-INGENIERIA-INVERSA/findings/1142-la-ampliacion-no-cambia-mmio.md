# 1142 — La ampliación de `1141` es un **no-op medido** para `mmio`: 20440 macros nuevas, 0 valores nuevos, 0 veredictos que cambien. Y el parser estricto ha evitado un falso positivo que "arreglar" habría creado

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=VALIDATION · NEGATIVE-RESULT
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   08-ARQUITECTURA/artifacts/R14-INCLUDES/salida.txt
                              (seccion final)
MODIFICADO_NADA_EXISTENTE    nada: es una medicion
CLASSIFICATION=MEASUREMENT · NEGATIVE-RESULT · SCOPE-BOUNDING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
ESTADO=ALCANCE DE LA AMPLIACION ACOTADO CON NUMEROS
```

## 0 · El resultado, primero

```text
macros nuevas que aporta la ampliación        20440
  de ellas macros mm*                            6

índice inverso de MMIO, con y sin ampliación:
  valores mm*                     10219  ->  10219
  con un único nombre mm*           9117  ->   9117
  valores cuyo número de nombres cambia       0

=> la ampliación NO cambia ningún veredicto de mmio
```

Y la razón de que esas 6 no entren, que es lo interesante:

```text
mm_alloc_cid         cuerpo = alloc_hooks(mm_alloc_cid_noprof(__VA_ARGS__))
mm_forbids_zeropage  cuerpo = (0)
mm_p4d_folded        cuerpo = __is_defined(__PAGETABLE_P4D_FOLDED)
mm_pmd_folded        cuerpo = __is_defined(__PAGETABLE_PMD_FOLDED)
mm_pud_folded        cuerpo = __is_defined(__PAGETABLE_PUD_FOLDED)
mm_zero_struct_page  cuerpo = ((void)memset((pp), 0, sizeof(struct page)))
```

## 1 · POR QUÉ ESTO ESTA ESCRITO

`1141 §8` dejó pendiente, textualmente, *"No he ampliado las includes en
`mmio.py`... Se puede reutilizar `macros_ampliadas` tal cual, y no lo he hecho
porque `mmio` tiene su propio `cargar_emit` y el cambio es de un minuto"*.

Medir antes de cambiar era lo correcto, y el resultado dice que **el cambio no
haría nada**. Aplicarlo habría sido añadir una dependencia y una ruta de código
para mover **cero** veredictos: `§98` (no automatización de teatro) y `§99` (no
herramientas de teatro) aplicados a una línea de código.

> Un resultado negativo medido vale más que un cambio sin efecto, porque el
> primero cierra la pregunta y el segundo la deja abierta con más código.

## 2 · POR QUÉ SOLO 6 DE 20440 SON `mm*`, Y POR QUÉ ESTO ES LO ESPERADO

El árbol de kernel que aporta la ampliación es `include/`: 16322 ficheros de
`linux/`, `asm/`, `vdso/`… El kernel no nombra registros MMIO de la GPU con
prefijo `mm`; eso es una convención de amdgpu. De 20440 macros nuevas, tener 6
`mm*` no es casualidad ni fallo: es la razón por la que `mm*` funciona como
filtro.

```text
indice mm*   10219 valores, de 83441 macros leidas   (12%)
             103881 macros leidas, mismos 10219      (10%)
```

El índice es pequeño porque se construye con un filtro estricto: solo `mm*` y
solo cuerpo literal. Ese filtro es el instrumento entero.

## 3 · EL CASO INTERESANTE: `(0)` Y POR QUÉ NO HAY QUE "ARREGLARLO"

`mm_forbids_zeropage` tiene cuerpo `(0)`. Eso **es** un entero: un cero entre
paréntesis. `int("(0)", 0)` lanza `ValueError`, así que `indice_mm` lo salta.

Con la lectura ingenua, el arreglo es quitar paréntesis antes de convertir:

```text
mm_forbids_zeropage  (0)  ->  valor 0x0000  ->  indexado
```

Y entonces `mmio` resolvería la **dirección `0x0000`** con el nombre
`mm_forbids_zeropage`.

Eso es un falso positivo de manual:

```text
mm_forbids_zeropage   NO es un registro MMIO
                     es un flag en tiempo de compilacion que dice si el
                     kernel prohibe la pagina cero. Su valor es 0 porque
                     "no" es 0.
```

La dirección `0x0000` no es un registro de la GPU. Indexarla metería en el mapa
inverso un nombre que no es un nombre de registro, y como `0` es un valor muy
atractivo para aparecer (direcciones, offsets), contaminaría la resolución de
todo lo que caiga cerca de cero.

Las otras cinco tienen cuerpos que ni siquiera son constantes: llamadas a
funciones, `__is_defined`, `memset`. Saltarlas es lo único sensato.

> **La estrictez del parser no es una limitación pendiente: es un filtro que
> está haciendo su trabajo.** Y la prueba de que funciona es un caso donde
> aflojarlo produciría un nombre equivocado. Merece la pena decirlo porque la
> tentación de "arreglar `(0)`" es exactamente el tipo de mejora que parece
> obviously-correcta y no lo es.

## 4 · LO QUE ESTO ACOTA

La ampliación de raíces de include tiene un alcance declarado y **medido**:

```text
SI cambia
   el conjunto de macros disponibles        83441 -> 103881
   ALIGN y su cadena                        antes no resolvian, ahora si
   cualquier macro interna de kernel        por el mismo camino

NO cambia
   el indice inverso de MMIO                0 valores
   los veredictos UNICO de mmio             9117 -> 9117
   ninguna medida de la linea base          48 -> 48, sin deriva
```

La tercera fila es la que más importa para la puerta: **ampliar 20440 macros no
movió ninguna de las 48 medidas**. Eso es coherencia interna, y es un dato
sobre lo mucho que ya estaba resuelto: el árbol de amdgpu aporta 83441 macros y
todo lo que las herramientas necesitan está ahí.

## 5 · LO QUE NO ESTÁ HECHO

**No he aplicado la ampliación a `mmio`.** Por lo medido en §1.

**No he comprobado el otro lado**: si `mmio` carga sus macros con su propio
`cargar_emit`, y ese camino no usa `macros_ampliadas`, entonces **cualquier
ajuste en las tablas de kernel no llega a `mmio`**. Es una dependencia
declarada, no un problema actual, y no lo he verificado porque hasta ahora no
importa — pero el día que importe, el sitio donde mirar está nombrado.

**No he buscado macros internas de kernel que sean *útiles*.** He medido qué
cambia; no he medido qué falta. Eso es un `NOT_DETERMINED`, no un
`PROVEN_ABSENT`, y la diferencia importa: `ALIGN` faltaba y era útil; puede haber
otras que falten y no sean.

**Y nada de esto es evidencia de hardware.** `RUNTIME=NOT_RUN`. Todo lo medido
es sobre ficheros y sobre la aritmética que el kernel escribe en ellos.