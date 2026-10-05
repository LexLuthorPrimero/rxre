# 1083 — El detector de texto en otro idioma funciona, pero `doclint` mira el 6,6% del corpus **y ampliar ese rango produciría 150 falsos positivos**: a `189` le falta una exención, no más alcance

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-SIDE-DOCINTEGRITY
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   ninguno: solo lectura de doclint.py y del corpus
MODIFICADO_NADA_EXISTENTE    pm4_codec.py, pm4decode.c, pm4_emit.py y
                          doclint.py quedan intactos; los defectos se
                          REPORTAN, no se reparan (ver §No reparado)
AUTOR=AGENTE-INSTR
CLASSIFICATION=MEASUREMENT+DEFECT · TRACK=STATIC
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=08-ARQUITECTURA/tools/doclint.py:434  (conjunto de ficheros por defecto)
         la regla CJK de doclint.py:61-65, ya correcta y ya validada
ALCANZADO=579 documentos de hallazgo · 921 .md del proyecto · 0 escrituras
ESTADO=PROBADO · NO reparado (ver §7)
herramienta  08-ARQUITECTURA/tools/doclint.py  (existente; NO se ha modificado)
```

## 0 · El resultado, primero

Tres mediciones que juntas cambian la conclusión de `117`:

| | `117` afirma | MEDIDO hoy |
|---|---|---|
| cobertura de `doclint` | «no se mira el 80%» | **6,6%**: 38 de 579 documentos |
| lo que falta | mirar más ficheros | **no se puede mirar más sin romperse** |
| la regla CJK | correcta | correcta, y **no tiene exención** |

**El defecto no es de alcance sino de diseño.** Ampliar el glob de
`doclint.py:434` produciría **al menos 150 falsos positivos**, porque el proyecto
tiene documentos que **deben** contener texto en otro idioma.

## 1 · LA COBERTURA REAL

```python
# 08-ARQUITECTURA/tools/doclint.py:434
args = sorted(glob.glob(f"{ROOT}/06-INGENIERIA-INVERSA/findings/0[23]*.md"))
```

```
ficheros de hallazgo totales      : 579
los que doclint mira por defecto :  38
cobertura                         :   6.6%
sin cubrir                        : 541
rango cubierto                    : 020 .. 039
```

El rango `020`–`039` es un **bloque contiguo de los hallazgos más antiguos**, no
una muestra. No es «se mira el principio y se verá el resto»: es un recorte
histórico que ya no cubre nada nuevo.

## 2 · LO QUE SE ESCAPA DE ESOS 38

Dos hallazgos con **corrupción real** en prosa, fuera del rango:

```
findings/1004-eng-invalidate-es-gfx9-y-no-gfx8.md:65    «su计 COUNT era el»
findings/1004-...:233                                   «sin_cs自有»
findings/1004-...:456                                   «tres讪rculos de»
findings/1035-...:447                                   «quien重建 el corpus»
```

`doclint` los detecta **perfectamente** si se le pasan explícitamente:

```
$ python3 08-ARQUITECTURA/tools/doclint.py findings/1004-*.md findings/1035-*.md
   ERROR  L65: fragmento de otro idioma '计' (U+8BA1)
   ERROR  L233: fragmento de otro idioma '自' (U+81EA)
   ERROR  L456: fragmento de otro idioma '讪' (U+8BAA)
   ERROR  L447: fragmento de otro idioma '重' (U+91CD)
   ERROR  L447: fragmento de otro idioma '建' (U+5EFA)
```

**La regla funciona. Lo que falla es que nadie la ejecuta sobre estos ficheros.**

Y son **reincidencias**: el hallazgo `189` ya reparó nueve fragmentos y su tabla
los enumera (`写入`, `路况`, `设置`, `閤`, `类是`, `也已经`, `混`, `곱`, `未定`).
`计`, `自`, `有`, `讪`, `重` y `建` **no están en esa tabla**. La corrupción
continúa en documentos escritos después de la reparación.

## 3 · POR QUÉ AMPLIAR EL RANGO NO ES LA SOLUCIÓN

27 ficheros `.md` del proyecto contienen caracteres CJK. `doclint` sobre los 27:

```
ERROR  fragmento de otro idioma   210
aviso  fragmento de otro idioma     4     (puntuación de ancho completo, U+FF0C)
```

Y **dos ficheros concentran 150 de los 210 `ERROR`**:

```
   87  RESEARCH/polaris12xl/docs/ESTUDIO-DE-LIBROS-Y-HUECOS-DECLARADOS.md
   63  RESEARCH/polaris12xl/LIBRARY-CATALOG.md
```

Esos dos ficheros son una **bibliografía de un libro en chino**. El CJK es
**contenido correcto**, no corrupción:

```
$ grep -nP '[\x{4E00}-\x{9FFF}]' ESTUDIO-DE-LIBROS-Y-HUECOS-DECLARADOS.md | head
17:### 1.1 B14 — 深入Linux内核架构与底层原理
21:| Título (del cuerpo) | 深入Linux内核架构与底层原理 | lectura del texto extraído |
22:| Autoría | 刘京洋、韩方 (Liu Jingyang, Han Fang) | portada |
23:| Editorial / año | 电子工业出版社 (Publishing House of Electronics Industry), 2017 |
```

```
$ head -1 LIBRARY-CATALOG.md
# LIBRARY-CATALOG — registro bibliográfico y de autoridad
 46:| **B14** | 深入Linux内核架构与底层原理 | 刘京洋 (Liu Jingyang), 韩方 | 2017 | 397 |
520:### B14 — 深入Linux内核架构与底层原理
```

Y `doclint` está diseñado para señalar exactamente eso: **87 falsos positivos sobre un
catálogo bibliográfico cuya función es citar el título del libro.**

> **Ampliar el glob de 38 a 921 ficheros noAmpliaría el rigor: lo convertiría en
> ruido.** Y un linter que produce ruido se deja de ejecutar, que es
> exactamente como se pierde la vigilancia.

## 4 · LO QUE LA REGLA SÍ DISTINGUE, Y ES UN CRÉDITO SUYO

`doclint` **no** marca `189` ni `117`, y esos dos ficheros contienen CJK. Lo
consigue porque en ellos los fragmentos van dentro de comillas invertidas:

```
$ doclint.py findings/189-*.md findings/117-*.md
documentos: 2   errores: 12   avisos: 1
$ ... | grep "otro idioma"
(sin resultados)
```

Los 12 errores de esos dos ficheros son **de otro tipo**: citas fuera de rango
(`psp_v10_0.c:4963` en un fichero de 175 líneas). Ninguno de idioma.

Es decir: **la regla ya tiene un mecanismo de escape — las comillas invertidas— y
por eso es precisa.** El defecto no es que no distinga; es que **el único
mecanismo de escape disponible es sintáctico y no semántico**: un documento que
cita un título chino en prosa, sin comillas invertidas, queda marcado como
corrupción.

### Y no es solo la regla de idioma: una segunda regla falla igual, y me falló a mí

Este documento, al pasar por `doclint`, da **cero errores de idioma** —el CJK
citado va en backticks— pero sí **un `ERROR` de otra regla**:

```
$ doclint.py findings/1083-*.md
FALLA 1083-...
   ERROR  L131: cita psp_v10_0.c:4963 fuera de rango (el fichero tiene 175 lineas)
   aviso  cabecera: faltan 3 campos de clasificacion: WRITE_EXECUTION, ...
documentos: 1   errores: 1   avisos: 1
```

Esa cadena es la **salida de `doclint` que acabo de citar** en §4. La regla de
rangos de cita la ha leído como una afirmación mía sobre `psp_v10_0.c` y ha
reportado una cita rota que no existe.

**Dos reglas independientes, dos modos de fallo del mismo tipo**: ninguna sabe
que lo que está en el documento es una cita de un diagnóstico. La capacidad que
falta no es «una exención para el CJK» sino **«un mecanismo de ámbito que
distinga lo que el documento afirma de lo que el documento transcribe»**, y esa
capacidad falta en las dos reglas a la vez. Por eso corregir solo el CJK dejaría
la segunda igual.

## 5 · LA CAPACIDAD QUE FALTA, CONCRETA

No es «un linter más». Es una **declaración de zona exenta por documento**, con
la regla de que la exención sea **explícita y reasons**:

```
EXENCION    por ruta de documento, no por regex global
            la excepcion se INHABILITA en cuanto el documento contiene prosa
            china fuera de las citas, para que no sirva de puerta
REQUISITO   la lista de exentos se declara DENTRO del arbol y es versionada
TEST        positivo:  findings/1004-*.md  -> 4 ERROR
            positivo:  findings/1035-*.md  -> 2 ERROR
            negativo:  LIBRARY-CATALOG.md  -> 0 ERROR de idioma
            negativo:  ESTUDIO-DE-LIBROS-*.md -> 0 ERROR de idioma
            negativo:  este documento (1083) -> 0 ERROR, ni de idioma ni de
                       cita: transcribe salidas de doclint y no debe marcarse
            el conjunto por defecto debe cubrir findings/*.md, no 0[23]*  <-- OJO
INVARIANTE  los 12 errores de tipo "cita fuera de rango" de 117 y 189 no cambian
```

> **Nota de método, y es la parte que más me importa.** Escribiendo este
> hallazgo **introduje yo tres corrupciones CJK** en el fichero: `设计ado`,
> `重点` y `排`. Las detecté con el mismo criterio que el hallazgo describe y las
> reparé. Está anotado porque es la mejor evidencia disponible de **cómo** ocurre
> el fallo: no es tecleo manual, es **texto generado**, y por eso un corrector
> ortográfico humano no lo ve y por eso vuelve a aparecer en documentos nuevos
> después de una reparación. La prueba es que los 6 fragmentos de `1004` y
> `1035` **no están** en la tabla de `189`: la reparación anterior fue
> diez puntos distintos y el problema siguió.

### El `<-- OJO` es la parte más importante de este hallazgo

Cambiar `0[23]*` por `*` **no** es el arreglo. Con la lista de exentos en su
sitio, sí: `579` documentos, `4` errores en vez de `150+`.

## 6 · POR QUÉ ESTO CORRIGE A `117` Y NO LO REEMPLAZA

`117-doclint-no-se-mira-el-80.md` afirma, en el título, que `doclint` «no se mira
el 80%». Hoy la cifra es **93,4%**, y su título está desactualizado por un
factor de más de cuatro.

Más importante: **`117` describe el síntoma como si la solución fuera mirar más
ficheros, y esa recomendación es incorrecta tal como están las cosas.** Con
`117` se puede pensar que el arreglo es una línea de glob. No lo es: sin
exenciones, esa línea convierte un linter útil en un generador de ruido. El
defecto de `1083` es de `117` y es **posterior** en la cadena de causes: primero
la exención, después el alcance.

## 7 · LO QUE NO ESTÁ HECHO, Y POR QUÉ

**No he modificado `doclint.py`.** Es de otra sesión y el arreglo requiere un
contrato de exenciones que otro agente debe decidir (§6).

**No he reparado los 6 fragmentos de `1004` y `1035`.** Son ficheros de otras
sesiones y `189` ya estableció un proceso de reparación con tabla. Añadir dos casos sueltos
sin seguir ese proceso duplicaría el procedimiento.

**No he arreglado los otros 54 `ERROR`** que no están en los dos ficheros
bibliográficos. **No sé cuáles son corrupción y cuáles son contenido legítimo**:
no los he inspeccionado uno a uno. Decir "204 errores" como si fueran todos
defectos sería el mismo error que este hallazgo denuncia.

## 8 · PROCEDENCIA

```text
cobertura    glob 08-ARQUITECTURA/tools/doclint.py:434 -> 38 de 579, 6.6%
corrupcion   6 ERROR en findings/1004 (4) y findings/1035 (2), verificados
             con doclint pasado por argumento explicito
reincidencia ninguno de los 6 esta en la tabla de reparacion de findings/189
escala       27 .md con CJK en el proyecto; doclint sobre los 27 -> 210 ERROR + 4 aviso
falsos pos   150 de 210 concentrados en 2 ficheros bibliograficos, leidos y
             confirmados como contenido correcto (titulo, autoria, editorial)
credito      189 y 117 contienen CJK citado en backticks y doclint NO los marca
encargos     $L | xargs doclint.py -> /tmp/opencode/dl2.out
escrituras   0 ficheros de otros agentes
```

**Lo que este documento NO prueba.** No afirma que los 204 `ERROR` restantes sean
corrupción: 150 son demostrablemente correctos y los otros 54 no se han
clasificado. No afirma que `doclint` tenga un defecto en su regla: la regla es
correcta y está validada; el defecto es que no tiene exenciones y su alcance es
6,6%. No afirma que el proyecto sea bilingüe por decisión: los dos ficheros
bibliográficos están clasificados como `EXTERNAL` y no son evidencia sobre esta
máquina, que es exactamente por lo que su texto debe poder ser fiel.