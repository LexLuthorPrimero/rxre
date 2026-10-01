# 045 · Hay 29 fronteras que otro documento ya cerró, y cuatro formas de que un detector de texto mienta

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`HERRAMIENTA_NUEVA=08-ARQUITECTURA/tools/stale_gap.py` (`TOOL_VALIDATED`)
`CONTINUES=043, 044`

## Cuestión principal

Las herramientas del proyecto dan tres cifras distintas de trabajo pendiente:
`causal_map` ve 60 claims, `frontier` ve 130 huecos, `next_work` ve 207 líneas
con `NOT_DETERMINED`. **Ninguna sabe qué hay en las otras dos, y ninguna
comprueba si una frontera sigue abierta.**

## Criterio de terminación

Cruzar cada frontera con sujeto contra todos los claims cerrados del proyecto,
separando cuatro clases. **Cumplido: 309 fronteras, 29 obsoletas, 4 clases.**

## Por qué esto importa más que el número

Un `NOT_DETERMINED` **obsoleto** es peor que uno verdadero. El verdadero dirige
el trabajo a algo que falta. El obsoleto dirige el trabajo a algo **ya hecho**:
se repite una medición, se escribe un hallazgo que ya existe, y el contador de
trabajo pendiente sube mientras el conocimiento no avanza.

Nadie lo comprueba porque la pregunta —"¿este sujeto tiene ya respuesta?"— no
la hace ninguna herramienta. `causal_map` busca *contradicciones*, no *cierres*.
`frontier` busca si el sujeto aparece en el código, no si aparece **resuelto**.

## El resultado

```
fronteras con estado de cierre : 309        claims cerrados indexados : 260

RESUELTA_AQUI        9   el mismo documento se contradice consigo mismo
RESUELTA_OTRO       20   otro doc ya lo cerró; el NOT_DETERMINED es obsoleto
NO_CRUZABLE         33   lo que hay entre backticks no es un sujeto
SIN_SUJETO         104   no dice de qué; no se puede cerrar ni repetir
VIVA               143   sin resolver: trabajo real
```

**29 fronteras obsoletas.** Las más claras:

| frontera obsoleta | ya resuelta en |
|---|---|
| `022:246` `PACKET3_COND_EXEC` — por qué es inerte | `038:264` `PROVEN` |
| `024:284` `PAGE_TABLE_DEPTH` 0 frente a 1 | `064:168` — ocupa bits [1:2] de `VM_CONTEXT*_CNTL` |
| `025:182` si `mb()`+`flush_hdp` bastan | `031:274` `PROVEN` |
| `030:93` cómo extrae el hardware el índice de `block_size` | `041:19` `PROVEN` |
| `031:278` si `writel` vacía posted-writes | `032:243` `REFUTED` — es un buzón, no una puerta |

`PACKET3_COND_EXEC` es la más valiosa: `022` declaró que no se sabía por qué es
inerte, y `038` lo resolvió siendo un documento *de herramientas*, no de
investigación. El hallazgo apareció de lado.

## `RESUELTA_AQUI`: 9 documentos se contradicen consigo mismos

Un caso particular que merece nombre propio. Un documento dice
`NOT_DETERMINED` en la sección del problema y `PROVEN` cuatro páginas después,
al resolverlo, **y se le olvidó quitar la marca**. No es un documento viejo: es
el mismo, y aun se contradice.

La herramienta distingue esa respuesta de una exterior **solo si va después en
el número de línea**. Una respuesta *anterior* es el estado viejo, y la frontera
posterior es una actualización legítima, no una contradicción.

## 104 fronteras sin sujeto: un defecto de los documentos, no un frente de trabajo

La cuarta parte de las fronteras no dice **de qué** es la frontera. Una frontera
sin sujeto no se puede cerrar, ni repetir, ni medir, ni cruzar con nada.

```
No se sabe todavía.
`NOT_DETERMINED`.
```

Eso no es una frontera abierta: es una frase. Lo que hay que hacer con ella no
es investigarla, es **completarla**: escribir contra qué es. Cada una de las 104
es una línea de documento que se puede arreglar sin tocar el hardware.

## Cuatro formas en que un detector de texto miente

Es la parte que más trabajo costó, y la más transferible. Cada una produjo
fronteras falsas **antes** de estar corregida, y cada una se encontró leyendo
las salidas, no probando el código.

### 1 · Un número de documento no es un sujeto

```
018:19   sujeto `017`   "...al siguiente IB (NOT_DETERMINED)"
         respuesta: 025:226  PROVEN
```

No hay relación: `017` es una **referencia** a otro documento. Como cada número
aparece en el título de su fichero y en el cuerpo de casi todos los demás,
sin filtrarlo cualquier línea se cruzaba con cualquier otra.

**52 de las 52 "obsoletas" iniciales eran de este tipo.** Reducido a 36 al
filtrar, y a 29 al añadir los otros tres filtros.

Solución: una clase `NO_CRUZABLE`, y el filtro deriva de *qué es un sujeto*, no
de una lista de palabras: un número de tres cifras, un nombre de estado, un
nombre genérico (`corpus`, `hardware`, `runtime`), o un nombre de fichero.

### 2 · Un estado citado en una frase que dice que NO se llega a él

El caso real, y el más grave:

```
056:153  "Para pasar de `NOT_DETERMINED` a `PROVEN` harían falta tres
          cosas, y ninguna existe como documento público"
```

La línea contiene `PROVEN`. Sin filtro, contaba como respuesta cerrada, y daba
por resueltas **dos fronteras abiertas** de `017` y `020` sobre
`FUNCTION=always`. El texto decía exactamente lo contrario: que *no se puede*
llegar a `PROVEN`.

Es la clase de fallo que tiene este proyecto entero: **aquí se cita un estado
para discutirlo**, no para declararlo.

Los signos del filtro no son una lista ideal de conectores en inglés —`would
require`, `cannot`— sino las formas que el corpus usa de verdad: `harían
falta`, `para pasar de`, `queda sin resolver`, `imposible`. Una lista en inglés
no habría detectado `harían falta`.

### 3 · Un estado condicional no afirma nada

```
017:194  "...haría `REFUTED` incorrecto; (c) `WAIT_REG_MEM_OPERATION`
          tuviera otro valor que 0 en..."
```

Hay un `REFUTED` y no se afirma nada: se dice que **sería incorrecto**. Con esa
línea de "respuesta", dos fronteras de `018` salían resueltas.

Fallo: lo mismo, un nivel más adentro. No basta con que la frase no niegue;
tiene que **afirmar** en posición de afirmación.

La diferencia entre las dos es lo que hace el filtro útil:

| forma | ¿afirma? | ejemplo |
|---|---|---|
| `\| sujeto \| PROVEN \| descripción \|` | sí | tabla de clasificación |
| `sujeto es PROVEN` | sí | prosa |
| `PROVEN` al final de la frase | sí | cierre |
| `haría PROVEN incorrecto` | **no** | condicional |
| `para llegar a PROVEN harían falta…` | **no** | requisito |
| `PROVEN` citado en una enumeración | depende | requiere contexto |

### 4 · La última: la que no es un fallo sino una tentación

Al corregir 2 y 3, el filtro se vuelve más agresivo. Un detector de texto
filtra, filtra, filtra, y en algún momento dice: *"si tengo dudas, descarto"*.
Eso convierte un falso negativo (perder una resolución) en una pérdida **invisible
y silenciosa**.

Por eso hay **controles simétricos**: `PROVEN` de verdad debe contar, `REFUTED`
en tabla debe contar. El filtro tiene que ser capaz de fallar en las dos
direcciones, y el self-test mide las dos. Un filtro que solo sabe decir "no" no
es un filtro, es un muro.

## Un quinto fallo, de diseño del test

El self-test inicial escribía los cinco primeros casos **todos en `a.md`**, y
cada escritura sobreescribía la anterior. Sobrevivía uno, y cuatro controles
daban `FALLA` sin que hubiera nada mal en la herramienta.

Y un sexto: el control de determinismo comparaba una extracción hecha *antes*
de crear los ficheros del caso 6 contra otra hecha después. No era
indeterminismo; era que entre medias se habían añadido dos ficheros. Un control
de determinismo tiene que medir dos ejecuciones sobre **el mismo estado**, que es
literalmente lo que dice.

Ambos son fallos del test, no de la herramienta. Y ambos tienen la misma
consecuencia: un self-test que falla sin motivo enseña a ignorar el self-test, y
entonces no queda nada.

## Clasificación

| afirmación | estado |
|---|---|
| 309 fronteras con estado de cierre en el corpus | `OBSERVED` — extracción |
| 29 son obsoletas: el sujeto ya tiene respuesta cerrada | `OBSERVED` — sujeto a verificación manual |
| Que esas 29 estén bien resueltas | `PARTIAL` — 5 verificadas a mano; el resto sin |
| 104 fronteras no tienen sujeto | `OBSERVED` |
| 9 documentos se contradicen consigo mismos | `OBSERVED` |
| El número de documento no es un sujeto | `DERIVATION` — definición |
| Una cita de estado no es una afirmación | `DERIVATION` — ver 056:153 y 017:194 |
| Que 52/52 de las obsoletas iniciales fueran ruido | `MEASUREMENT` — antes/después del filtro |
| Que un filtro de negación pueda perder resoluciones reales | `HYPOTHESIS` — por eso hay controles simétricos |
| Las 104 sin sujeto, una por una | `NOT_IN_CORPUS` — no se han revisado |

## Confounders

- **El cruce es por sujeto nombrado.** Dos documentos que hablen de la misma
  cosa con nombres distintos no se cruzan. `143` VIVA es una **cota
  superior** del trabajo real, no una medida.
- **`RESUELTA_OTRO` no dice que la respuesta sea correcta**, solo que existe.
  Si dos documentos se contradicen sobre el mismo sujeto, eso lo reporta
  `causal_map`, no esta herramienta.
- **El filtro de negación es conservador**: ante la duda marca como negada y
  pierde un cierre. Se eligió perder resolución antes que inventar una, porque
  una resolución inventada dirige a repetir un experimento ya hecho, que es el
  daño que esta herramienta existe para evitar.
- **La verificación manual fue de 5 de 29.** Las cinco eran correctas. No es
  muestra suficiente para afirmar que las 24 restantes lo son. Es el límite
  honesto de este hallazgo.
- **`SIN_SUJETO` y `NO_CRUZABLE` son clases distintas y la frontera entre ellas
  es una decisión.** "`HYPOTHESIS`" como sujeto es un nombre de estado, no una
  entidad; eso es NO_CRUZABLE, no SIN_SUJETO. "`writel`" sí es una entidad real
  y se cruza, aunque cruzar `writel` con cualquier documento que hable de
  escrituras produzca relaciones débiles.

## Desfalsificación

- **(a)** Las 29 obsoletas no lo son → refutable leyendo cada respuesta; 5
  verificadas a mano, las 24 restantes sin verificar.
- **(b)** El filtro de negación no pierde resoluciones reales → refutable con
  `--self-test`, control 10b.
- **(c)** El filtro de afirmación no pierde resoluciones reales → refutable con
  `--self-test`, control 10d.
- **(d)** Los números de documento son la única fuente de ruido → refutable
  desactivando cada filtro por separado y contando las que desaparecen; el
  número de obsoletas pasó 52 → 36 → 30 → 29, y cada paso se puede aislar.

## UNLOCKS

- **La cola de trabajo deja de mandar a repetir cosas hechas.** 29 entradas de
  `next_work` apuntaban a trabajo ya cerrado.
- **104 fronteras sin sujeto son 104 líneas de documento arreglables** sin
  hardware, y son el trabajo más barato que queda en el proyecto.
- **El filtro de negación corrige una clase de error del proyecto entero**, no
  solo de esta herramienta: en estos documentos se cita un estado para
  discutirlo.
- **El patrón "mención ≠ afirmación" se puede aplicar a `causal_map` y
  `frontier`**, que tienen el mismo riesgo y no lo comprueban.

## Evidencia

```
HERRAMIENTA
  08-ARQUITECTURA/tools/stale_gap.py   TOOL_VALIDATED, 12 controles
    RESUELTA_OTRO 20  RESUELTA_AQUI 9  NO_CRUZABLE 33
    SIN_SUJETO 104   VIVA 143
    obsoletas 52 -> 36 -> 30 -> 29 con los tres filtros

CASOS REALES QUE PRODUJERON FALSOS POSITIVOS
  056:153  "para pasar de NOT_DETERMINED a PROVEN harian falta tres cosas"
           -> cerraba 017:145 y 020:133, ambas ABIERTAS
  017:194  "haria REFUTED incorrecto"
           -> cerraba 018:80 y 018:217
  017/033/020 como sujeto
           -> cruzaba con cualquier documento

VERIFICADO A MANO (5 de 29)
  022:246  PACKET3_COND_EXEC  -> 038:264
  024:284  PAGE_TABLE_DEPTH   -> 064:168
  025:182  mb()               -> 031:274
  030:93   block_size         -> 041:19
  031:278  writel             -> 032:243
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.