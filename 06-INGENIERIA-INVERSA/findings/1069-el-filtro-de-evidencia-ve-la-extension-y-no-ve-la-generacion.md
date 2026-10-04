# 1069 — el filtro de evidencia decide por extensión y no puede ver la generación: 2 de 76 artefactos de kbuild están sellados como evidencia

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN-VALIDITY
CLASSIFICATION=DEFECT+REPAIR · TRACK=STATIC+MUTATION
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=revkit/sello.py  NO_EVIDENCIA_EXT (filtro por extension) -> nueva regla
         07-DRIVER/kernel/rx550.mod.c, rx550_drv.mod.c   (ya sellados)
         + 5 .mod.c mas en otros 4 directorios (a punto de entrar)
ORIGEN=1060 §4 (la clase D, y su pregunta Q5)
ESTADO=PROBADO · REPARADO · 29 vectores (3 capas) · 3 mutaciones detectadas
herramienta   revkit/sello.py
```

## 0 · La regla, y por qué no es "una extensión más"

`sello.py` decide qué es evidencia con una lista de extensiones:

```python
NO_EVIDENCIA_EXT = {".o", ".ko", ".so", ".pyc", ".png", ".jpg", ".rgba", ".bin", ".spv", ...}
```

**Un `.mod.c` pasa, porque es `.c`.** El filtro ve la extensión y no ve **quién
escribió el fichero**, y un fichero generado por una construcción con extensión de
fuente es indistinguible de una fuente escrita usando sólo la extensión.

MEDIDO sobre el árbol entero:

```text
artefactos de kbuild (tienen hermano .cmd)          76
  NO sellados -- el filtro los para por su extensión   74
  SELLADOS como evidencia                              2      <-- los que se colaron
```

**74 de 76.** El filtro funciona para casi todo y falla exactamente en el formato
que no sabía que existía. Los dos que se colaron están en `07-DRIVER/kernel/`, y su
única inspección es §4 de la clase D del `1060`.

**Y lo que la reparación evita, que es lo que da la medida su valor:** hay **5
`.mod.c` más** en otros cuatro directorios que hoy no están en el manifiesto y que el
filtro habría dejado entrar la próxima vez:

```text
04-IMPLEMENTACION/rx550-driver/rx550_drv.mod.c
07-DRIVER/driver/rx550_pciid.mod.c
03-EXPERIMENTOS/control/rx550_drv.mod.c
03-EXPERIMENTOS/sandbox/rx550_drv.mod.c
03-EXPERIMENTOS/ep08-doorbell-suppression/nhwa.mod.c
```

## 1 · LA REGLA, Y POR QUÉ EL `.cmd` ES UN PREFIJO Y NO EL NOMBRE

kbuild deja un fichero de traza de órdenes llamado `.<salida>.cmd` junto a cada cosa
que produce. Y **"salida" no siempre lleva la misma extensión que el fichero**:

```text
rx550_drv.ko      <- .rx550_drv.ko.cmd     nombre IDÉNTICO
rx550_drv.mod.c   <- .rx550_drv.mod.cmd    el .cmd es PREFIJO, sin el .c
```

**La regla que queda en código:** existe un hermano `X.cmd` tal que **X es un prefijo
no vacío del nombre del fichero, o es igual**. Implementado en
`revkit/sello.py:es_generado_por_kbuild()`, y aplicado en `es_evidencia_candidata()`
que ahora recibe `raiz` porque sin directorio no se puede mirar nada.

`raiz` es **opcional a propósito**: sin él la excepción no se aplica, y eso es
`NOT_AVAILABLE` — *no he podido mirar* — y no *"no es generado"*. El vector `G9`
comprueba exactamente esa distinción.

## 2 · MI DETECTOR DIJO "0 SELLADOS" Y ERA FALSO

El primer censo que hice de esta clase dio:

```text
artefactos kbuild ... sellados: 0
```

Y ese 0 era **un bug mío, no un resultado**. Buscaba el hermano como
`base + extensión`, de modo que de `.rx550.mod.c.cmd`/`rx550.mod.c` no dessinaba nada
y `07-DRIVER/kernel/` no aparecía. Lo que lo distingue porque un detector que se pasa de
largo **se parece muchísimo a un detector que no ha encontrado nada**: los dos
responden "aquí no hay nada", y sólo uno tiene razón.

Lo digo sin adornos porque es la cuarta vez hoy que escribo una explicación y luego
la mido, y las cuatro han salido mal en algún sitio. Lo que salva esto no es escribir la cosa con cuidado: es que el resultado era **imposible** — dos `.mod.c` sellados que
el `1060` §4 ya había contado a mano — y una cifra que contradice un recuento hecho
a ojo se nota. Si no lo hubiera notado, este hallazgo sería *"0 artefactos
generados sellados, el filtro funciona"* y sería falso.

**El antídoto que queda:** el detector se prueba contra los dos casos que lo
rompieron, y con mutaciones que reproducen el fallo (M19).

## 3 · LAS TRES CAPAS DEL SELF-TEST, Y POR QUÉ HACE FALTA UNA TERCERA

`revkit/sello.py` no tenía ningún self-test. Ahora tiene tres capas, y cada una existe
porque una anterior **no cubría el camino donde estaba el defecto**:

| capa | qué prueba | por qué existe |
|---|---|---|
| 1 | el núcleo puro `clasifica_custodia` | `M16` (el rc) vivía fuera y pasaba 9 de 9 |
| 2 | `custodia()` e `indice_sellados()` sobre un repo falso | `M17` vivía en `indice_sellados()` |
| 3 | `es_generado_por_kbuild()` y la excepción | esta reparación |

```text
capa 1   9 vectores, 0 fallos
capa 2  10 vectores, 0 fallos
capa 3  10 vectores, 0 fallos
```

**Las tres mutaciones de esta capa, y las tres detectadas:**

```
M19  prefijo -> igualdad                    -> FALLA G1, G2, G7
M20  la excepcion no se aplica nunca        -> FALLA G7
M21  cualquier .cmd hermano cuenta          -> FALLA G5, G8
```

`M19` es el que importa: es **exactamente** el bug del §2, y sin vector habría
vuelto.

## 4 · Lo que la regla NO arregla

- **Los 2 ya sellados siguen sellados.** Este hallazgo **no re-sella**. Sacar del
  manifiesto algo que allí está es una decisión con su propio riesgo, y el `1060`
  §6 ya explican por qué re-sellar sin dejar constancia es peor que no re-sellar.
  Lo que este documento hace es **dejar de admitir más de los mismos**.
- **No cubre la generación de otros sistemas de construcción.** La regla es
  específica de kbuild porque es el sistema de construcción que tiene este
  proyecto. Un `.c` generado por otro mecanismo —un script, un generador de
  firmware— **no tiene `.cmd` hermano** y esta regla no lo ve. Declarado, no
  deducido: `LIMITACION`.
- **No mira contenido.** No comprueba que el fichero "parezca" generado: mira que
  tenga un hermano `.cmd`. Un fichero escrito a mano al lado de un `.cmd` se
  marcaría como generado. Es un **falso positivo posible**, y la dirección del error
  es la segura: excluir de más es recuperable, incluir de menos es lo que ha
  costado esto.
- **No toca los dos `.mod.c` ya dentro del manifiesto a propósito**, por lo de arriba.

## 5 · PROCEDENCIA

```text
regla      revkit/sello.py:es_generado_por_kbuild() + es_evidencia_candidata(rel, raiz)
censo      76 artefactos kbuild · 74 no sellados · 2 sellados · 5 mas en puerta
self-test  29 vectores en 3 capas, 0 fallos
mutaciones  M19 M20 M21, las 3 detectadas
invariante el sello principal NO cambia: OK 177 · MOVIDO 68 · ROTO 0 (rc=1)
escrituras 0 en el arbol.  No re-sellado.
```

**Lo que este documento NO prueba.** No prueba que los 2 sellados sean los únicos
artefactos generados en el manifiesto por otra vía: la regla es de kbuild y no la he
contrastado contra generación de otro tipo. No prueba que los 5 "en puerta" fueran a
entrar: estaban sin sellar cuando lo medí, y el manifiesto se genera a voluntad. Y no
sostiene nada sobre la GPU, sobre el driver ni sobre rendimiento.