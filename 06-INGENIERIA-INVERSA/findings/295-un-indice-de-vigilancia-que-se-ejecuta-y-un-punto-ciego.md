# 295 · Un índice de vigilancia que se ejecuta, y un punto ciego que no se puede cerrar

```text
CLASSIFICATION=TOOLING+MEASUREMENT+LIMITATION · TRACK=TOOLING
CORPUS=NINGUNO (el proyecto) · HARDWARE_SCOPE=NONE
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

`294` respondio que «puede fallar este vector» no es una propiedad sintáctica, y que
dos detectores escritos a mano habían dado `0 de 411` y `366 de 486`, ambos
falsos. Lo que sí responde es la **mutación**: cambiar el código que el vector
vigila y ver si cae.

Eso ya se hacía a mano, siete veces, siete caídas. Lo que faltaba era automatizarlo
automatizado, y sobre todo **declarar qué mutaciones se aplican**, porque un
número de mutantes sobrevivientes sin conjunto declarado no mide nada: el
porcentaje es una decisión.

`tools/mutscore.py`. Siete mutaciones, una por línea, cada una con su
fichero, su texto, su texto de sustitución, **por qué debería detectarse** y
**qué vector debería verla**.

## 1 · Lo que mide, y lo que no

```text
  DETECTADA    el self-test falla tras la mutacion      <- el vector MUERDE
  SOBREVIVE    el self-test pasa igual                  <- PUNTO CIEGO
  SIN_APLICAR  el texto a mutar no esta ya en el fichero
  ERROR        la herramienta no se puede ejecutar      <- no se cuenta
```

Cada mutación se aplica a una **copia temporal** y se lanza el intérprete como
subproceso. El árbol no se toca, y hay un vector que lo comprueba comparando el
fichero antes y después.

Y una limitación escrita en la cabecera, porque si no el nombre engaña:

```text
  NO es un mutation score.
  Un mutation score muta cada linea del codigo y mide cuantos mutantes
  sobreviven. Aqui hay un CONJUNTO DECLARADO de 7, las que de verdad se han
  hecho a mano en una sesion. Un porcentaje sin cobertura declarada no es una
  medida: es una decision sobre que mutaciones se eligieron.
```

## 2 · El resultado

```
  DETECTADA    5
  SOBREVIVE    1
  SIN_APLICAR  1

  DETECTADA  nextnum: sin cerrojo
  DETECTADA  nextnum: la reserva no se ve a si misma
  DETECTADA  govcheck: los acentos no se quitan
  DETECTADA  govcheck: 'agents' vuelve a decidir
  DETECTADA  lint: el campo linea vuelve a ser texto
  SOBREVIVE  lint: la cuenta no incluye lo nuevo
  SIN_APLICAR govcheck: 'or True' vuelve a un vector
```

Cinco de siete. Y las dos que no sonMockito tienen explicaciones distintas, que
importan más que el resultado.

### `SIN_APLICAR`, y no es un fallo

La mutación busca un vector de `govcheck.py` que contenga `or True`. Ese vector
**ya no existe**: se quitó hace unas horas cuando se discovered que no podía
fallar. El motor no falla y no calla: dice

```text
  el texto a mutar no esta en tools/govcheck.py. ESTO ES IMPORTANTE: la
  mutacion hay que actualizarla cuando cambia la herramienta, y si no se
  actualiza, esta herramienta CALLA en vez de fallar
```

Un conjunto de mutaciones declarado se queda viejo. La herramienta lo dice en
lugar de dar un número, que es la diferencia entre un dato y una impresión.

### `SOBREVIVE`, y es el hallazgo

```text
  la mutacion   _v() pasa a contar SOLO los fallos
  el resultado   el self-test sigue en VERDE
```

Es decir: hay un mutante que **sobrevive**, y es el mismo defecto que se
corrigió antes en esta sesión y que se había vuelto a dejar abierto. Un self-test
puede ejecutar treinta y tres vectores, todos pasar, y el recuento decir treinta
cuando son treinta y tres, y nada se entera.

## 3 · Y no se puede cerrar con un vector

Se llevarlo cuatro intentos. El quinto es el que explica por qué:

```python
  _antes_de_este = len(vectores)
  _v("...", len(vectores) == _antes_de_este + 1)
```

**Los argumentos se evalúan antes de la llamada.** Cuando se calcula
`len(vectores)`, el vector todavía no está en la lista. La comparación es
`33 == 34`, y es `False` siempre, con el código correcto.

```text
  una comprobacion que vigila el efecto de su propio ayudante
    no se puede enunciar en este lenguaje
```

Un test que necesita mirar el efecto de la llamada tiene que mirar después, y
entonces ya no puede distinguir si el efecto fue de esa llamada o de otra. No es
un defecto de este test: es una limitación del enunciado.

Así que el punto ciego queda **declarado y no cerrable**, que es lo único que se
puede hacer con él:

```
  la deberia ver : NINGUNO, Y NO SE PUEDE. Se llevo cuatro intentos de
                   escribir un vector que lo viera y el quinto explico por
                   que no existe
```

Y quien lo vigila es `mutscore`, que sí puede, porque mira el resultado desde
fuera del self-test.

## 4 · Lo que la herramienta encontró que yo no

El mutante que sobrevive estaba en `lint.py`, y su correccion
**destapó un segundo defecto que era peor**:

```text
  el self-test imprimo   FAIL  contar un vector nuevo cambia el total
  y la linea de abajo   RESULT: PASS (34 vectores)
```

Un informe con un `FAIL` en la lista y un `PASS` en el resumen. La causa: la
función `_v()` imprime `FAIL` y no sumaba, porque al arreglarla la vez anterior
se le había quitado el `fallos.append` de dentro.

**Un recuento separado del informe es un informe que puede mentir sobre sí
mismo**, y aquí no mentía sobre el código: mentía sobre su propio resultado.

Se corrigió dejando una sola verdad, `vectores`, y calculando el número de fallos
al final. Y al hacerlo se rompió dos veces más antes de quedar, que queda escrito
porque es la razón por la que la forma final es la que es:

```text
  1  `_v` imprime FAIL y no suma      ->  el RESULT miente
  2  arreglo con una lista de 1 casilla  ->  el RESULT la trata como booleano
  3  `del L[m]` se comio la linea del RESULT  ->  IndentationError
  4  el vector que vigila el recuento  ->  imposible, por evaluacion de argumentos
  5  una sola verdad: vectores, y el recuento al final
```

## 4 bis · El sesgo del conjunto, y cómo se quita

El resultado de arriba tiene un defecto que lo invalida como medida:

```text
  7 mutaciones, todas de defectos QUE YA SE HABIAN ENCONTRADO
  5 de 7 detectadas

  y ese 5 de 7 no mide nada
```

Es el peor sesgo posible: **confirmar que un defecto conocido sigue vigilado no
es vigilancia, es confirmación.** Un conjunto declarado que solo contiene lo que
ya se sabe, no puede encontrar nada que no se supiera.

La respuesta es mutar **sin saber qué debería caerse**, y para que la elección no
sea una decisión de quien escribe —que es donde esto fallaría, porque quien muta
tiende a elegir mutaciones que sus vectores ya cazan— la mutación la produce una
**regla**:

```text
  NEG_COND   toda linea  if X:  pasa a ser  if not X:      (y al reves: es toggle)
  SWAP_CMP   todo  ==  pasa a ser  !=, y  <=  a  >  (y al reves)
  RET_NONE   todo  return EXPR  pasa a ser  return None
```

Y aquí está la respuesta a la pregunta del `NEXT_ACTION` —qué habría que
declarar para que «elegir el cambio más probable» no sea una decisión de quien
escribe—: **no hay nada que declarar, porque el operador ES el conjunto.** Lo
único declarado es el alcance —cinco ficheros— y las excepciones, y las dos
cosas son comprobables.

Sitios que la regla produce, medidos:

```text
  NEG_COND   184
  SWAP_CMP   143
  RET_NONE   145
```

### El coste, medido antes de construir

```text
  herramienta      self-test     sitios if
  govcheck.py        7 458 ms       47
  nextnum.py           620 ms       37
  lint.py              118 ms       33
  fingerprint.py        63 ms       35
  toolaudit.py          62 ms       44
```

Una vuelta completa sobre `if` cuesta menos de siete minutos. Eso es lo que
decide que la automating sea posible: sin esa medición, «mutar 184 sitios» suena
a inviable.

### Y un mutante puede colgarse, y hay que decirlo

```text
  la primera version usaba el timeout de 900 s y se paso de quince minutos
  en tres mutantes

  volver  `if not match: continue`  en  `if match: continue`
  mete la herramienta en un bucle infinito
```

Un mutante que se cuelga **es** detectado —el self-test lo nota, gritando— pero
no en el tiempo que uno tiene. Así que `TIMEOUT` es una clase propia, y el
informe la nombra aparte: colgar no es lo mismo que fallar.

```text
  DETECTADA  el self-test falla
  TIMEOUT    el mutante no acaba     <- detectado, pero hay que decirlo
  SOBREVIVE  el self-test pasa igual
```

### Y el límite grande, que va en la cabecera de la herramienta

**Un mutante que sobrevive no es un vector débil.** Puede ser código muerto, una
rama inalcanzable, o dos ramas que hacen lo mismo. Por eso el informe **no da un
porcentaje**: da la lista con fichero y línea, para que se lea. Un porcentaje de
mutantes sobrevivientes aquí sería un número con el mismo problema que el 5 de 7
del apartado anterior, pero con más decimales.

## 4 ter · La vuelta completa, y lo que dicen los 188

```text
  MUTACION A CIEGAS, 472 sitios que produjo la REGLA
  No hay conjunto declarado: el operador es el conjunto.

  DETECTADA  283
  SOBREVIVE  188
  TIMEOUT      1

  TIMEOUT 1: nextnum.py L114  if n not in usados:
             el mutante se CUELGA, y eso tambien es detectado
```

Un `TIMEOUT` de los 472, y el que cuelga es `siguiente()`: volver `if n not
in usados` en `if n in usados` hace que el bucle de búsqueda nunca termine. El
self-test lo nota gritando, que es detección, pero no en el tiempo que uno
tiene. Por eso `TIMEOUT` es clase propia y no `DETECTADA`.

### Los 188 sobrevivientes, leídos

No son 188 vectores débiles. La lista enseña otra cosa:

```text
  if __name__ == "__main__":        5 veces, una por herramienta
  if a.json: / if a.selftest: / if a.censo:
  if a.uncited: / if a.no_titular: / if a.limite:
  return 0 / return 1 / return 2   al final de main()
  return "NO_OBSERVADO", None
  if txt is None:
  if __name__ ... y largos de comentarios y docstrings
```

Son **fontanería de línea de órdenes y ramas que el self-test no ejecuta**. Un
mutante de `if a.json:` sobrevive porque el self-test no pasa por `--json`, y
eso no dice que la comprobación sea floja: dice que **esa línea no está probada**.

Que es la distinción que hace falta, y que la herramienta NO hace todavía:

```text
  SOBREVIVE en linea que el self-test ejecuta     ->  el vector NO MUERDE
  SOBREVIVE en linea que el self-test no ejecuta  ->  la linea NO ESTA PROBADA
```

Son dos defectos de distinta naturaleza y con distinta arreglo, y confundirlos
es lo que haría que un porcentaje de este informe no significara nada.

### Y la cobertura por línea, que sí se ha podido medir

`trace` no sirvió, y la razón está medida: traza el proceso entero —librerías
incluidas— y el `.cover` de `fingerprint.py` llega a la línea 8086 de un fuente
de 517. No está mal hecho; mide otra cosa.

Lo que sí funciona es un `sys.settrace` puesto **dentro** del proceso del
self-test, filtrando por `co_filename`, así que sólo recoge las líneas del
fichero de la herramienta. Da números de línea reales y acotados.

```text
  govcheck.py       348 de  883 lineas   39%
  nextnum.py        224 de  522 lineas   42%
  lint.py           367 de  950 lineas   38%
  fingerprint.py    172 de  518 lineas   33%
  toolaudit.py      265 de  916 lineas   28%
```

**Los self-tests de este proyecto ejecutan entre el 28 % y el 42 % de su propio
código.** Ese es un dato que no se tenía, y es la respuesta a «qué líneas no
prueba nadie».

### Y con el segundo eje, los 188 se parten

```text
  SUPERVIVIENTES                              189
    en linea que el self-test EJECUTA          39   <- VECTOR QUE NO MUERDE
    en linea que el self-test NUNCA ejecuta   150   <- LINEA SIN PROBAR
```

De 188 a dos listas con naturalezas distintas. La segunda no dice nada de los
vectores: son 150 líneas que nadie ejecuta. La primera sí lo dice, y al leerla
aparece una tercera categoría que no estaba en el lista:

```text
  govcheck.py   L730  L882 L721 L731      el arnés del self-test
  nextnum.py    L521  L183 L409 L434      idem
  lint.py       L859  L949 L847 L860 L719  idem
  fingerprint   L483  L517 L474 L484      idem
  toolaudit     L774  L915 L758 L775      idem
  lint.py       L602 L736 L746 L757 L781  las aserciones del propio self-test
  toolaudit     L670 L673                 idem
  nextnum.py    L114                      el mutante que se CUELGA
```

Son casi todos **el arnés del propio self-test**: el `if __name__ == "__main__"`,
el `return selftest()`, el `return 0 if not fallos`, el `print("... selftest")`.

Y eso tiene nombre: **un self-test no puede probar su propia fontanería de salida.**
El código que decide si el self-test dice PASS o FAIL no está dentro del self-test,
así que su mutante sobrevive siempre, y no porque la comprobación sea floja.

Es la tercera cosa que este informe separa y que no son la misma:

```text
  283  DETECTADA   el self-test muerde
    1  TIMEOUT     el mutante se cuelga, que tambien es morder
   39  de los 188:  lineas EJECUTADAS cuyo vector no muerde, y casi todas
                   son el arnés del propio self-test, que no se puede probar
  150  de los 188:  lineas NO EJECUTADAS por nadie
    --  y entre ellas, 52 lineas de linea de ordenes --json --selftest --censo
```

## 5 · Lo que NO se establece

```text
  el mutation score del proyecto
    PARCIALMENTE MEDIDO. 472 sitios que produjo la REGLA:
      DETECTADA 283   SOBREVIVE 188   TIMEOUT 1
    Son tres operadores y cinco ficheros, no el proyecto entero

  cuantas de las 472 podrian sobrevivir
    NO RESUELTO, y es el hallazgo del apartado 4 ter. Los 188 se leen, y la
    lectura es que son lineas de linea de ordenes y ramas que el self-test no
    ejecuta: no vectores debiles. Falta el segundo eje --alcanzable o no--, y
    sin el un porcentaje aqui no significa nada

  si las 150 lineas sin ejecutar contienen algo que importe
    NO SE HA MIRADO UNA A UNA. El informe las lista, y estan en el fichero de la
    vuelta completa, pero no se ha leido si son fontaneria o logica. Es lo
    unico que queda de este hallazgo, y es una lista de trabajo
  si los tres operadores cubren bien la superficie de ESTOS CINCO ficheros
    NO SE AFIRMA. Con 28 % a 42 % de cobertura, la superficie que queda sin
    tocar es la mayoria del codigo, y el rendimiento de un operador sobre lo que
    ejecuta no dice nada sobre lo que no ejecuta

  si los tres operadores cubren bien la superficie
    NO SE AFIRMA. Son los tres clasicos, y nada mide que basten para este codigo

  el mutante de `or True` en `govcheck`
    SIN_APLICAR, porque el vector ya no existe. La mutacion queda declarada y
    sin ejecutar: es una promesa, no una medida
```

## 6 · La regla que sale, y que es más corta que la herramienta

```text
  UN VECTOR PUEDE FALLAR   <=>   al cambiar el codigo que vigila, cae

  y un vector que nunca ha caido no es un vector validado:
  es un vector de capacidad DESCONOCIDA.
```

`AGENTS.md` §88 llama `SELF_TESTED` a haber pasado los vectores. Pasar vectores
no exige hoy que uno de ellos caiga alguna vez, y con el trabajo de esta sesión
se ha visto que **cuatro de ellos no podían**, y que dos intentos de censarlos
por análisis dieron dos números falsos. El índice que mide eso es `mutscore`, y
lo que entrega no es un porcentaje: es la lista de los que nadie puede refutar.

## 7 · Trazabilidad

```text
  tools/mutscore.py           la herramienta, 7 declaradas + 3 operadores a ciegas,
                              21 vectores
  tools/mutscore.py           ALCANCE_CIEGO: cinco ficheros. Lo unico declarado
  tools/mutscore.py           BOOTSTRAP: el settrace que hace el segundo eje
  tools/mutscore.py           --eje2: la particion que convierte la lista en
                              diagnostico
  tools/lint.py              el punto ciego, y su causa: argumentos antes de la llamada
  tools/nextnum.py            2 mutaciones, ambas DETECTADAS
  tools/govcheck.py           2 DETECTADAS y 1 SIN_APLICAR
  findings/294                por que no se puede detectar por analisis
```

## 8 · Correlación

```text
  294   "puede fallar" no es una propiedad sintactica, y dos detectores mentiron
  295   ESTE: la mutacion si se puede automatizar, con el conjunto declarado, y
        el primer resultado es un punto ciego en lint.py que nadie habia visto
```

Y el hilo que los dos comparten, que es la regla del apartado 6: **lo que no se
puede refutar no está validado, y no saber si se puede refutar no es lo mismo
que saber que no.**

## 9 · Corrección de numeración

```text
  este fichero se escribio como 295, reservado con --reservar antes de escribir
  CORRECTED_BY: --reservar 295  RESERVADO
```