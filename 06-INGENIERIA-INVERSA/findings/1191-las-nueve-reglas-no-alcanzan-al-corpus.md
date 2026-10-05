# 1191 — Las nueve reglas son ejecutables y **ninguna es aplicable a un solo hallazgo de los 676**. No es un fallo de los validadores: es que la prosa no se puede validar. Ocho campos que las reglas necesitan **no aparecen en ningún hallazgo**

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=EVIDENCE-FORMAT-AUDIT
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   tools/rxre.py  (171 -> 180 vectores, rc=0)
CLASE=MEASUREMENT · NEGATIVE_RESULT · ESTADO=MEDIDO
PRECEDE=1190 que lo declaro como "NO MEDIDO"
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
```

## 0 · La pregunta que 1190 dejó escrita

`1190` mide si los validadores **ven** el incumplimiento, por mutación, y contestar que sí
—16 de 17, 0 falsos verdes—. Pero mide sobre **hechos que yo construí**. Y quedaba la
pregunta que de verdad importa:

```text
¿alguno de los nueve validadores se puede EJECUTAR sobre un hallazgo real?
```

## 1 · El resultado

```text
$ rxre cobertura

COBERTURA DE LOS CAMPOS  676 hallazgos
  reglas APLICABLES a un hallazgo real: 0 de 9
  campos que las reglas necesitan: 17;  con presencia: 9
  campos que NO aparecen en NINGUN hallazgo:
    afirmacion, busqueda, caminos, compila, decodificado,
    reejecuta, reejecuta_igual, verificada
```

**Cero de nueve.** No "cero de nueve casi": cero. Ningún hallazgo de los 676 lleva
todos los campos que alguna regla necesita.

## 2 · Por regla, campo a campo

| Regla | Campos que necesita | Presencia | Aplicables |
|---|---|---|---|
| `VERDE_NO_ES_CORRECTO` | `rc`, `validado` | 15, **1** | 0 |
| `SOFTWARE_NO_ES_HARDWARE` | `fuente`, `afirmacion` | 8, **0** | 0 |
| `AUSENCIA_NO_ES_INEXISTENCIA` | `busqueda`, `resultado`, `veredicto` | **0**, 6, 2 | 0 |
| `NULO_NO_ES_CERO` | `valor`, `origen` | 2, 2 | 0 |
| `REPRESENTACION_NO_ES_FUENTE` | `origen`, `estado` | 2, 3 | 0 |
| `DECODIFICADO_NO_ES_VERIFICADO` | `decodificado`, `verificado` | **0**, 2 | 0 |
| `SIN_PROBAR_NO_ES_DISPONIBLE` | `estado`, `verificada` | 3, **0** | 0 |
| `COINCIDENCIA_UNICA_NO_ES_INDEPENDIENTE` | `caminos`, `afirmacion` | **0**, **0** | 0 |
| `COMPILAR_NO_ES_EJECUTAR` | `compila`, `reejecuta`, `reejecuta_igual` | **0**, **0**, **0** | 0 |

`COMPILAR_NO_ES_EJECUTAR` no tiene **ninguno** de sus tres campos. `COINCIDENCIA_UNICA`
no tiene ninguno de los dos. Esas dos reglas no se pueden ejecutar ni una vez.

## 3 · La distinción que hace que esto sea un hallazgo y no un error de guion

Al contar, la palabra `fuente` sale **266 veces** en 676 hallazgos, y `valor` **463**. Un
lector razonable diría "los campos están". No lo están:

```text
    busca como PALABRA     busca como CAMPO (campo= al principio de linea)
    fuente       266  ->  fuente=        8
    valor        463  ->  valor=         2
    resultado    403  ->  resultado=     6
    estado       405  ->  estado=        3
```

Las 266 son **prosa** sobre de dónde salió un dato. Las 8 son el campo que un validador
puede leer. Confundir las dos cifras produce un "el corpus tiene los campos" que es
falso, y un vector que lo comprueba obliga a contarlos por la forma correcta.

## 4 · Qué es esto, y qué no es

```text
NO ES   que las reglas sean falsas.  Salieron de errores reales y estarian mal
        escritas si estuvieran mal.  Y funcionan: 16 de 17 por mutacion.

NO ES   que los validadores esten rotos.  Responden bien a lo que se les da.

ES      que el SUJETO no existe.  Las reglas se escribieron, y el resultado se
        guardo en prosa, y la prosa no se puede validar.

    un validador sin corpus no es un validador roto:  es un validador sin entrada
```

Y esa es exactamente la especificación que **§11 EVIDENCE REGISTRY** de la constitución
del proyecto ya pide, con sus campos (`EVIDENCE_ID`, `SOURCE`, `TYPE`, `PROVENANCE`,
`SCOPE`, `INPUT`, `OUTPUT`, `UNIT`, `TRANSFORMATION`, `PRODUCER`, `CONSUMER`,
`OBSERVABLE`, `TOOL`, `ARTIFACT`, `LIMITATION`) y que **no tiene implementación
medible**. El coste, medido: **0 de 9 reglas** son exigibles.

Corolario incómodo y útil:

```text
las nueve reglas son ejecutables contra hechos de laboratorio,
y cero ejecutables contra el archivo.
```

## 5 · Lo que este hallazgo NO mide

```text
MEDIDO      que los campos no estan, contado por dos vias:  la funcion, y un
            `grep` independiente que un vector exige que coincida
NO MEDIDO   si las reglas detectarian algo si los campos existieran.  Es
            NOT_DETERMINED,  no "si":  no se ha probado, y el 16/17 de 1190 es
            sobre OTRO conjunto de hechos,  no sobre los hallazgos
NO MEDIDO   que los hallazgos sean correctos.  Aqui no se juzga su contenido:
            se mide que no se puede pasarles una regla por automatico
NO MEDIDO   si 676 hallazgos 17 campos.  No se ha preguntado
```

## 6 · Dos fallos míos durante la medición, porque un instrumento que miente no sirve

### 6.1 Un `%s` sin sustituir dentro de una regex compilada

```python
RE_CAMPO = re.compile(r"(?m)^\s*[#|`\s]*(%s)\s*[=:]")   # y nunca se aplico el %
```

La expresión buscaba la cadena literal `%s`, no encontraba ningún campo, y devolvía:

```text
campos vivos: 0    reglas aplicables: 0
```

Que es **verosímil y falso**. Si no llego a contrastar con el `grep` de shell —que sí
encontraba 15 `rc=`— habría escrito un hallazgo entero diciendo que el corpus no tiene
ni un solo campo.

> Un marcador sin sustituir dentro de una regex compilada no da error: da un cero
> silencioso.

Hay ahora un vector que falla si queda un `%s` o un `{` en el patrón.

### 6.2 Sumar con duplicados y comparar con un conjunto

`campos_necesarios` salía **20** y `_CAMPOS_TODOS` daba **17**: tres campos los
necesitan dos reglas (`estado`, `origen`, `afirmacion`). El vector falló y tenía razón.
Para la pregunta "¿qué campos hay que registrar?" cuenta el **distinto** —20 obligaría a
registrar tres campos que no hacen falta—, y el total con repetición se conserva aparte
porque las dos cifras son ciertas y responden a preguntas distintas.

## 7 · La corrección del proceso, que fue el otro error

En el commit anterior escribí:

```text
python3 doclint.py 06-.../1190-*.md ; git commit -q -F -
```

El linter estaba en la **misma línea** que el commit, separado por `;`. Su salida se
vio —`errores: 1`— y el commit salió igual. Es §26 aplicado a mi propio bucle:

> Un control que no gobierna la acción es decorativo. Lo que hace falta es `&&`.

No pude reproducir ese `errores: 1` en cinco pasadas posteriores (cinco `errores: 0`, con
`errores: 0` también al pasar los 13 ficheros). **No reproducido, no refutado** — y lo
digo así porque el motivo de que fuera un error no depende de que la cifra fosse real:
depende de que el commit no estaba condicionado a ella.

## 8 · Procedimiento

```text
anadido     CAMPOS_DE_LA_REGLA   que campos lee cada una de las nueve reglas
            _porta_campos()      {hallazgo -> campos que DECLARA}, cacheado
            cobertura_de_campos() por regla: aplicables, por_campo, campos_muertos
            _CAMPOS_TODOS / RE_CAMPO  construido de la lista, sin marcadores
            CLI `rxre cobertura`

medido      676 hallazgos
            reglas aplicables: 0 de 9
            campos: 17 necesarios, 9 con presencia, 8 sin presencia alguna
            el mas comun es `rc` en 15 hallazgos de 676
            recuento de `rc` confirmado por segunda medicion independiente
            (funcion vs grep) y cuadrado por vector

distincion  palabra en prosa != campo.  fuente 266 veces, fuente= 8 veces
            validado=   35 veces, validado=  1 vez
            estado  405 veces, estado=   3 veces

no hecho    anadir los campos a los hallazgos.  Eso es escribir 676 veces, y es
            decision de formato del cuerpo, no de un instrumento
escrituras  tools/rxre.py unicamente
runtime     RUNTIME=NOT_RUN.  Ni la RX550 ni la Intel.  i915 y amdgpu intactos
```
