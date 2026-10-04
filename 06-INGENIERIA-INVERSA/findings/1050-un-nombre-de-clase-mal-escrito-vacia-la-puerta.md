# 1050 — un nombre de clase mal escrito convertía la puerta del proyecto en un certificado de limpieza

```
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN-LINT
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=tools/lint.py:925-926  (el filtro)  ·  :865  (el self-test que no lo cubria)
ESTADO=PROBADO · REPARADO · self-test 35 -> 38 vectores
```

## El defecto

`tools/lint.py` es la puerta de integridad del texto escrito, `VERSION = "2.0.0"`, con
35 vectores de self-test. Su opción de filtrado por clase era:

```python
if a.solo:
    rows = [r for r in rows if r["clase"] == a.solo]
```

**Igualdad exacta de nombre de clase, y ninguna comprobación de que el nombre.existsiera.**
Medido, con los mismos tres comandos y sobre el mismo árbol:

| invocación | antes | después |
|---|---|---|
| `lint.py --solo cjk` | **0 hallazgos, rc=0**, y el texto *"NINGUNO. Y esto es un resultado, no un silencio"* | rc=**2**, y dice que no es ninguna clase |
| `lint.py --solo CJK_INSERTADO` | 12 hallazgos | 12 hallazgos |
| `lint.py --solo CJK_SUSTITUIDO` | 40 hallazgos | 40 hallazgos |

Las clases reales se llaman `CJK_INSERTADO`, `CJK_SUSTITUIDO`, `PERMITIDO`. **`--solo cjk`
no casa con ninguna.** Y el filtro no lo decía: devolvía una lista vacía, y la
herramienta la imprimía como si fuera una medición, con una línea que **afirmaba
explícitamente que ese vacío era significativo**.

> Es, literalmente, el defecto que `check_num_unico.py:799-801` ya describe en este
> proyecto: *«una puerta que sale con 0 porque "no hay problema" y una que sale con 0
> porque "no lo he mirado" —y nadie lo nota porque las dos se leen igual— son el mismo
> defecto con dos motivos.»*

**Y es la quinta instancia del patrón del hallazgo 1048**, ahora en la puerta más
madura del árbol.

## Por qué el self-test no lo vio

`tools/lint.py:865` ejercita exactamente dos formas de bandera:

```python
for _flag in (["--censo"], ["--solo", "ANGLICISMO"]):
```

`ANGLICISMO` **existe**. No había ningún vector con un nombre de clase que no exista,
porque un nombre inventado en un self-test parece tipografía, no una prueba. Y el
defecto no es que un filtro falle: es que **un filtro que no puede encontrar nada
confunde "no hay" con "no he mirado"**, y para distinguirlo hace falta una clase que no
exista.

**Reparado:** si el nombre pedido no está entre las clases que el informe produce, se
imprime el error, se listan las 11 clases que sí existen, y se sale con **código 2**.
El nombre pedido no se «corrige» ni se busca por aproximación: un filtro que no casa
tiene que decirlo, no interpretarlo.

**Tres vectores nuevos**, y el primero es el que faltaba:

```
OK  un --solo con nombre inexistente NO sale con 0   rc=2
OK    ...y lo dice, en vez de callar
OK    ...y lista las clases que si existen
RESULT: PASS (38 vectores)
```

## Cómo se encontró, que es la parte que importa

**Escribiendo una puerta que hacía falta y no hacía falta.**

Al empezar:

```
El proyecto YA TIENE cuatro linters de CJK: `tools/lint.py` (VERSION 2.0.0),
`08-ARQUITECTURA/tools/doclint.py`, `08-ARQUITECTURA/tools/commitmsg_lint.py` y
`tools/docscan.py`. No los mire antes de escribir el quinto, `tools/cjk_gate.py`.

Y al poner los dos lado a lado, el mio dio **90 lineas con CJK en 32 ficheros** y el
del proyecto dio **"0 hallazgos"**. Los dos no pueden ser ciertos, asi que medi, y la
culpa del 0 no era de mi puerta: era del filtro. **El defecto estaba en la herramienta
buena, y se vio porque una herramienta mala midio lo mismo.**
```

La puerta que escribí se ha borrado. `lint.py` la hace mejor: clasifica `CJK_INSERTADO`
—intrusión, borrable— de `CJK_SUSTITUIDO` —pegado a una palabra latina, ocupa el lugar
de una palabra perdida, y borrarlo deja una frase peor—, tiene diez marcadores
`INTENCIONALES` para los ficheros cuyo CJK **es la evidencia** (el hallazgo 117 entero,
el 189, las tablas que citan sus propios tokens, y sus propias regex de rango CJK), y
35 vectores. La mía cubría algo parecido de archivos y no clasificaba nada.

**Se queda lo que la puerta mala encontró:** que `lint.py` se delata a sí mismo con su
propio hallazgo, que es lo que su lista `INTENCIONALES` dice en su línea 179 y que está
bien hecho.

## Lo que también se corrigió aquí, y es mío

`08-ARQUITECTURA/CITAS-150-ADJUDICACION.md:410` cita
`tools/check_num_unico.py:635` como la línea del filtro `if num not in dups`.

**La 635 no es el filtro en ninguna revisión.** Medido: **662** en el árbol de trabajo,
**641** en `HEAD`. El número salió de un encargo mío que decía «línea ~635» —con
tilde, como una estimación no medida— y dos subagentes lo reproduciron como si fuera
una cita. Uno lo registró como discrepancia `D1` en su propio informe.

Corregido en el hallazgo 1048, que era mío. **No en los informes de los subagentes**:
un artefacto de otro nodo se corrige produciéndose una revisión, no editándolo por
detrás.

Y eso es la sexta vez del mismo patrón en esta sesión: **una cifra sin medir que viaja
dentro de un informe y sale como si estuviera medida.** La quinta fue un `\d{4}-` mío
que contaba 1 duplicado donde había 74. El patrón no es de los agentes: es de las
consignas.

## Regla que sale

> **Un filtro que acepta un nombre escrito por una persona tiene que responder a un
> nombre que no existe.**

Porque un nombre que no existe no es un caso raro: es lo que pasa la primera vez que
alguien escribe la clase en minúsculas, en corto, o en castellano. Y ese caso tiene que
producir un error, no un verde.

El arreglo no es «que el filtro sea más tolerante». Es **que el filtro diga lo que hizo**,
que es lo que el 1048 pide de toda herramienta que filtra: `CONTADO`, `EXCLUIDO`,
`JUSTIFICADO`. Aquí el excluido era «todo», y no lo decía.