# 288 · «Falla» no es una unidad: cinco herramientas estaban encontrándose a sí mismas

```text
CLASSIFICATION=MEASUREMENT+ERROR+TOOLING+CONTRADICTION · TRACK=TOOLING
CORPUS=NINGUNO (el proyecto) · HARDWARE_SCOPE=NONE
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

El `NEXT_ACTION` era: los códigos de salida de once herramientas no significan una
cosa. Al contarlas, nueve de ellas estaban **informando de un defecto del
proyecto**, no rompiéndose:

```text
  findings_index         rc=1   DEFECTO DE INTEGRIDAD: el numero de hallazgo
                               no es clave unica
  num_collision          rc=3   reporta el problema de colisiones
  toolkit                rc=1   contrato valido 40/47
  validate_rx550_final   rc=2   no acepta --selftest. Preexistente y declarado.
```

Y de esas, cinco **son herramientas que funcionan**:

```text
  una herramienta que ha encontrado un problema y sale con 1
    NO es lo mismo que
  una herramienta cuyo test se ha roto y sale con 1

  y un recuento que las mete en el mismo saco no tiene unidad
```

Es el espejo exacto de lo que `AGENTS.md` §24 prohíbe en la dirección contraria.
Ahí: `binary missing + exit 0 = INVALID_RESULT`. Aquí: `defecto encontrado +
rc 1 = test roto`.

## 1 · Lo que NO se toca, y por qué

No se cambian los códigos de salida de esas herramientas.

```text
  cambiar la semantica de una herramienta que hoy reporta un defecto real
    seria PEOR que la ambiguedad

  porque la ambiguedad se puede nombrar
  y el defecto silencioso no se puede
```

Lo único que se hace es no mentir en el rótulo: `rc != 0` cuya salida dice
`DEFECTO DE INTEGRIDAD` se etiqueta **`DEFECTO`**, no `FALLA`.

## 2 · Lo puse primero en la herramienta equivocada

Añadí la clase `DEFECTO` a `toolkit.py`. No funcionó: salió cero veces.

Medida la razón:

```text
  toolkit NO ejecuta self-tests
  toolkit hace analisis ESTATICO de cabeceras

  y en analisis estatico su FALLA significa SIEMPRE "he encontrado algo"
  nunca "mi test se ha roto"

  no hay ambiguedad que quitar ahi
```

Los siete `FALLA` que produce son siete violaciones de contrato encontradas
leyendo código. Renombrarlas sería mentir al revés. La clase se retiró de ahí, se
dejó escrito por qué, y la expresión se mudó a `toalaudit.py --run`, que es donde
sí ejecuta.

## 3 · Y entonces llegó el desastre silencioso

Para elegir qué bandera pasar, `toalaudit` pasó por tres métodos. El primero leía
el fuente:

```text
  herramienta que solo acepta --selftest  ->  se le pasa --self  ->  rc!=0
  -> marcada FALLA. Instrumento que no es el que se cree.
```

El segundo preguntó al `--help`:

```text
  bienintentado: un texto que MENCIONA una bandera no la DECLARA
  pero el --help miente por omision en algunos casos, y se pierden 15
```

El tercero sondeó ejecutando las candidatas y exigiendo que la salida mencionase
un self-test. Y aquí está lo que pasó, medido:

```text
                     ANTES      DESPUES
  con self-test         82   ->    113     "ha mejorado mucho"
  DEFECTOS               5   ->      1     "ya no hay"
```

**La herramienta mejoraba en el papel mientras perdía.** El sonda siempre elegía
la bandera equivocada, y la razón es la que no se había visto:

```text
  findings_index --selftest     rc=1   "DEFECTO DE INTEGRIDAD"
                                        AUDITA EL PROYECTO y falla si encuentra algo

  findings_index --self-test    rc=0   "self-test OK (2 vectores de
                                        normalizacion)"
                                        PRUEBA VECTORES INTERNOS y sale 0
```

Dos cosas distintas con nombres casi iguales. El sonda elegía la segunda porque
es la única cuyo texto dice «self-test».

### Y `rc = 0` tampoco es señal

Otra cosa que se breakdownsó al medir:

```text
  aperture.py --selftest    rc=0   imprime su salida NORMAL, no un self-test
  aperture.py --self-test   rc=0   imprime "self-test OK (2 vectores...)"
  aperture.py --help        declara NADA
```

`rc = 0` **no significa que la bandera se haya reconocido**. Estas herramientas no
erroran ante una opción desconocida: hacen su trabajo de siempre y salen con 0.
Es `INVALID_RESULT` en estado puro, y por eso el código de salida no puede ser la
prueba de nada.

## 4 · Lo que sí funciona, en tres criterios y un orden

```text
  1  DECLARADA EN CODIGO   add_argument("--self")     una declaracion
  2  DECLARADA EN --help   lo que ofrece al usuario     una declaracion
  3  CONVENCION            --selftest                 si no hay de las dos

  y el orden de las candidatas no es negociable:
  `--selftest` antes que `--self-test`, siempre
```

El criterio 1 existe por un caso concreto y medido: `toolaudit.py` declara
`--self` y sólo `--self`, pero **su fuente contiene la cadena `--selftest`**
porque la escribí yo en un comentario al arreglar esto. Leyendo el fuente, la
herramienta lee su propia traducción y cree que acepta una bandera que no acepta.

```text
  una cadena "--selftest" en un comentario   NO es una declaracion
  add_argument("--selftest")                SI lo es
```

Cuatro herramientas no usan argparse — `findings_index`, `aperture`,
`struct_rw`, `num_collision` — así que para ésos sólo hay convención. Y se declara
que se usa, en vez de fingir que se descubrió.

## 5 · El arreglo que faltaba de verdad: que la cuenta sume

Después de las dos pérdidas de datos de arriba, la lección no era cuál bandera
elegir. Era que **un recuento puede perder categorías sin que nadie lo note**.

```text
  pasan {p} · fallan {fl} · DEFECTOS {de} · timeout {to}
```

Con cuatro categorías, tres pueden caer a 0 por un cambio de código y el número
sigue teniendo aspecto de dato. Ahora se imprime también `sin determinar` y
`sin self-test`, y sobre todo la suma:

```text
  suma de clasificados: {p + fl + de + to + no + sin} de {len(filas)}
```

Una categoría a 0 tiene que leerse como «no hay», y si no la hay, tiene que verse.

## 6 · `toolkit`: por qué NO se amplía a `tools/`

`toolkit` cuenta 48 herramientas de un árbol. Antes de ampliarlo, medido:

```text
  08-ARQUITECTURA/tools    48 herramientas    42 con contrato  (88%)
  tools/                  58 herramientas     1 con contrato  ( 2%)
```

Ampliarlo habría metido 57 filas de «sin contrato» y habría tapado las 42 que sí
lo tienen. El reparto correcto ya existía:

```text
  toolaudit.py   cuenta la POBLACION, los dos arboles
  toolkit.py     vigila el CONTRATO, y el contrato solo esta en un arbol
```

Lo que faltaba era que `toolkit` lo dijera, porque su rótulo anterior era
«herramientas en 08-ARQUITECTURA/tools: 47» sin explicar el alcance. Ahora lo
explica con los dos números medidos encima.

## 7 · Y un defecto real que salió de paso

```text
  ResourceWarning: 210 por ejecucion
  siete sitios con `open(path).read()` que no cierra el descriptor
```

Con 48 herramientas leídas y siete aperturas sin cerrar por cada una. Un aviso
que se repite doscientas veces deja de avisar de nada: entrena al lector a ignorar
la salida. Corregido con un `_lee()`, que es el mismo patrón que ya usa
`toalaudit`.

## 8 · La población es un objetivo móvil

```text
  112 herramientas   medido ayer, en dos informes
  113 herramientas   medido hoy
```

Otro agente escribió herramientas mientras esto corría (`run_all.py`,
`driver_offsets.py`, ambas a las 00:42). `AGENTS.md` §102 dice
`PROJECT_ACTIVE_AGENT <= 1` y esa regla se está incumpliendo de forma visible y
constante.

Consecuencia práctica: **cualquier cifra de población necesita sello de tiempo**,
o no es comparable con la de al lado. `274` no lo lleva y debería.

## 9 · Lo que NO se establece

```text
  que bandera usa cada una de las 113
    NO_DETERMINADO para las que no declaran nada y no responden a la
    convencion. Se cuentan como "sin determinar", visibles, no repartidas
  si `--selftest` y `--self-test` significan lo mismo en las 42 que usan argparse
    NO_PREGUNTADO. Solo se ha medido en las cuatro sin argparse
  el estado de las 5 DEFECTO
    son self-tests que FUNCIONAN. Lo que han encontrado son defectos reales del
    proyecto, y esos defectos siguen abiertos
  si el resto del proyecto tiene la misma ambiguedad de codigos de salida
    NOT_INVESTIGATED. Solo se ha medido en estos dos arboles
  la population de hace tres dias
    NOT_COMPARABLE. Sin sello de tiempo, dos cifras de poblacion no se comparan
```

## 10 · Trazabilidad

```text
  08-ARQUITECTURA/tools/toalaudit.py   corre_self_test(): FALLA vs DEFECTO
  08-ARQUITECTURA/tools/toalaudit.py   bandera_que_declara(): criterio 2
  08-ARQUITECTURA/tools/toalaudit.py   DECLARADA_EN_CODIGO: criterio 1
  08-ARQUITECTURA/tools/toalaudit.py   bandera_convencion(): criterio 3
  08-ARQUITECTURA/tools/toalaudit.py   sondea_bandera(): FUERA DE SERVICIO, con motivo
  08-ARQUITECTURA/tools/toolkit.py     7x open() sin cerrar -> _lee()
  08-ARQUITECTURA/tools/toolkit.py     el rotulo no declaraba su alcance
  findings/274                         la poblacion de 112
```

## 11 · Corrección de numeración

```
  este fichero se escribio como 280, que ya usaba otro hallazgo
    280-la-multi-asignacion-producia-un-rango-falso-y-ya-no.md
  COMPROBADO: 0 citas antes de renumerar
  CORRECTED_BY: renumerado a 288
  el 280 del otro NO se toca: renumerar un miembro cuando el otro esta
    citado rompe la referencia
  --reservar 288  RESERVADO antes de escribir
```

Y una observación sobre cómo se produjo, porque es el mismo problema otra vez:

```
  --reservar 280        RESERVADO, a las 23:5x
  --reservar 280        DUPLICADO, dos ficheros lo usan, a la 1:0x

  otro agente escribio su hallazgo con ESE numero en el intervalo
  a pesar de que --reservar ya lo habia tomado
```

La reserva funciona contra el que no la pide. No puede contra el que no la pide.