# 1193 — `ibref.py` de 77 a 85 de 116. Ocho fallos que NO eran del entorno: el evaluador del **stub** emparejado con las macros de verdad, y un `quitar_cast_tipo` que hacía tres cosas distintas y ninguna era la que decía

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=INSTRUMENT-RECOVERY + BUG-CLUSTER
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   tools/ibref.py
CLASE=ERROR · IMPLEMENTATION · ESTADO=PARCIAL_MEDIDO
CONTINUA=1183 (reconstruccion parcial) · ORACULO=tools/_orculo_ibref.pyc 116/116
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST
```

## 0 · Un error mío antes que ninguno: los 5 fallos de `ALIGN` no eran del instrumento

Para trabajar sobre una copia, la copié a `/tmp`. `RAIZ` se resuelve como
`dirname(dirname(abspath(__file__)))`, así que pasó a ser `/tmp`, y
`entrada_por_defecto()` devolvió `/tmp/RESEARCH/…`, que no existe. Los cinco
vectores de `ALIGN` fallaron.

Diagnóstico correcto: **`RAIZ` estaba mal, no `ibref.py`**. Se montó un árbol espejo
(`RESEARCH` y `08-ARQUITECTURA` enlazados, el fichero dentro) y se volvió a medir.

```text
  montaje erroneo (RAIZ=/tmp)              77 de 116
  arbol espejo (RAIZ con sentido)          77 de 116
```

Mismo número, y aun así había un bug real debajo. Lo que sigue.

## 1 · `ALIGN`: el evaluador del stub con las macros de verdad

El selftest carga **dos** juegos:

```text
  ev, lm        el STUB       (cargar_evaluador(pystub))
  _ev_real, _lm_real   los de verdad  (cargar_evaluador())
```

Los cinco vectores de `ALIGN` pasaban `macR` (macros reales) junto a `ev` (el
stub). El stub no tiene headers de kernel, así que `ALIGN` no se podía evaluar y
`== 0` nunca se cumplía. Los vectores de condicionales, treinta líneas más arriba,
**sí** usaban los reales — y por eso pasaban.

```python
macR      = _macros_reales(lm, ev)          # stub
sintetizar(expr, ev, macR, ...)              # stub
```

Corregido a `_lm_real` / `_ev_real`: **+5 vectores**.

> Un par (macros, evaluador) de Procedimientos distintos no es una entrada válida.
> Las dos mitades tienen que venir del mismo sitio, y nada lo exigía.

## 2 · `quitar_cast_tipo`: tres versiones, tres fallos distintos, todos con aspecto de errata

El contrato es `(__typeof__(x))(a)` → `a`. La primera versión usaba un regex:

```python
RE_CAST_TIPO = r"\(\s*__typeof__\s*\(\s*[^()]*?\s*\)\s*\)\s*\(\s*([^()]*?)\s*\)"
```

`[^()]*?` no puede consumir un argumento que tenga paréntesis, así que en

```text
(__typeof__(x))(__typeof__(y))(7)   ->   (__typeof__(x))7
```

se comía el cast de dentro. Eso no se arregla con otro regex: es emparejamiento de
paréntesis. Se escribió `_cierra()` y se quitó el cast de cabeza, encadenando.

**Segunda versión, dos bugs nuevos:**

| Lo que hacía | Lo que devolvía |
|---|---|
| `s = s[c3 + 1:]` — lo que viene **después** del argumento | `""` |
| sin desenvolver el argumento sobrante | `(7)` en vez de `7` |

Y `_desenvuelve` llamaba a `balanced()`, que **existe en el `STUB` como cadena y no
como función del módulo**. Un `NameError` disfrazado de fallo de la regla.

**Tercera versión: la que rompió `ALIGN`.** Al desenvolver paréntesis siempre, cambió
el cuerpo de macros del árbol:

```text
  (((x) + ((a) - 1)) & ~((a) - 1))  ->  ((x) + ((a) - 1)) & ~((a) - 1)
```

Semánticamente idéntico, y los cinco vectores de `ALIGN` **volvieron a fallar**.

> Quitar paréntesis de todo lo que se pasa es cambiar cosas que no se han pedido
> cambiar. El contrato era "quitar casts", no "quitar paréntesis".

**Y el fallo que faltaba, que era el más silencioso:** al reescribir para quitarlos
solo de cabeza, se perdió el caso **en medio**. El cuerpo real es

```python
__ALIGN_KERNEL = __ALIGN_KERNEL_MASK(x, (__typeof__(x))(a) - 1)
```

con el cast incrustado. El regex viejo lo cubría porque sustituía en cualquier sitio.
El parser nuevo no, y `sintetizar("ALIGN(0,256)")` devolvió **`None`** — sin error, sin
excepción, sin decir nada.

> Un parser más estricto no es un parser más correcto: es un parser que ha perdido
> el caso que el regex cubría sin que se notara.

Versión final: cabeza (encadenado) + medio (uno por pasada), y `_desenvuelve`
**solo si se quitó un cast de cabeza**.

```text
  ('(__typeof__(u32))(3)')                -> '3'
  ('(u32)(3)')                            -> '(u32)(3)'   intacto, sin __typeof__
  ('(__typeof__(x))(__typeof__(y))(7)')   -> '7'
  ('(__typeof__(a))(1) + 2')              -> '(1) + 2'
  ('ring->q + 3')                         -> 'ring->q + 3' intacto
```

**+1 vector**, y `ALIGN` sigue bien.

## 3 · `P1`: la asignación compuesta no estaba

`RE_ASIGNACION` recognía `x = e;` y **no** `x += e;`. El vector
`a = 1; a += 1;` devolvía `{'a': 1}` — el valor **antes** del `+=`. La sentencia se
veía y se ignoraba; no se rechazaba.

Lo tentador es reescribir `a += 1;` como `a = a + 1;`. **Eso está mal para `*=`:**

```c
a *= 2 + 3;      /* C:  a = a * (2 + 3)   */
a = a * 2 + 3;   /* lo que sale de reescribir  */
```

Una reescritura textual de ese tipo acierta en `+=` y falla en `*=`, y el fallo sólo
aparece en el operador que no se mira. Se evalúa con paréntesis a ambos lados:

```python
valor = "(%d) %s (%s)" % (previo, operador[:-1], valor)
```

Y `+=` con valor previo **desconocido no se propaga**: rellenar con 0 sería
`NULO_NO_ES_CERO`.

**+2 vectores.**

## 4 · El saldo

```text
  ANTES   77 de 116
  AHORA   85 de 116          +8

  por bloque que queda
    desenrollo      18     hace falta lo que NO se ve: los ARRAY_SIZE de
                             RE_FOR_CUALQUIER / RE_IDX_WRITE / RE_ARRAY_SIZE
                             estan en las constantes del .pyc, no en el fuente
    round-trip       7     faltan los fixtures y los 6 estados con su formato
    decode           3
    cond             2     uno es un punto decimal; el otro, la lista de
                             escrituras que incluye lo que no se emite
    una              1     propagacion dentro de un if
    ampliacion       1     las macros del primario

  oraculo   tools/_orculo_ibref.pyc  116/116, sha256 e0bdb8d023b1…, modo 444
  NO se ha escrito encima ni un byte del .pyc
```

## 5 · Procedimiento, con el error de partida dentro

```text
ERROR PROPIO     copie el fichero a /tmp y rompi RAIZ;  diagnostique como si
                 fuera del instrumento.  Corregido con un arbol espejo
encontrado 1     stub + macros reales emparejados:  +5
encontrado 2     cast de cabeza mal tomado:  devolvia "" y luego (7)
encontrado 3     balanced() existe como cadena en el STUB, no como funcion
encontrado 4     _desenvuelve desarrollo los parentesis de TODAS las macros y
                 rompio ALIGN:  se limita a cuando se quito un cast
encontrado 5     al reescribir se perdio el cast EN MEDIO, y ALIGN paso a
                 devolver None sin decir nada:  reponido
encontrado 6     RE_ASIGNACION no reconocia +=:  +2
medido           77 -> 85 de 116
no hecho        desenrollo y round-trip,  que necesitan los fixtures literales
                del .pyc
runtime          RUNTIME=NOT_RUN.  Ni la RX550 ni la Intel
```
