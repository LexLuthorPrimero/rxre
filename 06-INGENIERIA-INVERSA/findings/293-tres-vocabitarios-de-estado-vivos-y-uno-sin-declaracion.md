# 293 · Tres vocabularios de estado vivos, y uno sin declaración

```text
CLASSIFICATION=MEASUREMENT+CONTRADICTION+LIMITATION · TRACK=VERIFICATION
CORPUS=NINGUNO (el proyecto y su git) · HARDWARE_SCOPE=NONE
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

El `NEXT_ACTION` anterior plantaba una pregunta —qué convierte una entrada
«validada» en algo que no sea una afirmación— y daba dos salidas. Eso era
preguntar lo que la medición ya podía decidir. Medido:

```
docs/TOOLS-STATUS.md, 3 257 líneas

  entradas cuyo estado es TOOL_VALIDATED o TOOL_PARTIAL   9
  entradas con el campo ESTADO                           37
  entradas con AMBAS cosas                                 1

  COMANDO   que se ejecutó para verificarlo      0
  VECTOR    que se comprobó                      0
  PRUEBA    que se pasó                          0
  EJECUT    con qué                              0
```

**Ni una sola entrada de 3 257 líneas dice con qué se verificó.** Ese es el hueco
real, y no son las 43 herramientas ausentes: es que las 71 presentes no llevan
base.

## 1 · El registro no tiene un esquema de entrada

```text
  ## TL-NN · `nombre` — ESTADO          10 entradas
  ESTADO   <valor>                       37 entradas
  las dos cosas a la vez                  1 entrada
```

Dos formatos, y una sola entrada que usa los dos. Un lector no sabe cuál buscar.
Y de los 37 valores de `ESTADO`, sólo 9 son una palabra:

```text
  SELF_TEST_OK                    18
  TOOL_VALIDATED,                  9
  SELF_TEST_OK,                    1
  TOOL_PARTIAL                     1
  TOOL_PARTIAL,                    1
  TOOL_UNVALIDATED                  1
  SIN                              2
  REFUSED_UNDECLARED               2
  NOT_EXECUTED                     1
  UNTRACKED.                       1
  pm4dw.c                          1     <- un NOMBRE DE FICHERO en el campo de estado
```

El último es el más instructivo: una entrada donde el estado se rellenó con la
ruta de un fichero. Nadie lo revisó porque el campo no tiene vocabulario que
pueda fallar.

## 2 · Tres vocabularios vivos, y uno sin declaración

```text
  A  el AGENTS.md ACTUAL, §22 y §88
     DISCOVERED · AVAILABLE · EXECUTABLE · CONTRACTED · SELF_TESTED
     VALIDATED · DEGRADED · INVALID · RETIRED

  B  el que se usaba y se declaraba hasta la sustitucion del documento
     TOOL_VALIDATED · TOOL_PARTIAL · TOOL_UNVALIDATED · TOOL_BROKEN

  C  el que escribe el registro, sin declarar en ninguna parte
     SELF_TEST_OK · SIN · NOT_EXECUTED · REFUSED_UNDECLARED · UNTRACKED.
```

Y el B está muerto de declaración pero vivo en el uso:

```text
  TOOL_VALIDATED     AGENTS.md actual   0    hallazgos que lo citan   24
  TOOL_PARTIAL       AGENTS.md actual   0    hallazgos que lo citan    6
  TOOL_UNVALIDATED   AGENTS.md actual   0    hallazgos que lo citan    2
```

## 3 · El vocabulario B sí se puede recuperar

```text
  git show 6fb9113:AGENTS.md   lineas 900-907

    → EDGE CASE → FAILURE CHECK → OUTPUT VALIDATION

    Clasificar:
      TOOL_VALIDATED
      TOOL_PARTIAL
      TOOL_UNVALIDATED
      TOOL_BROKEN
```

Existe en las dos versiones commiteadas grandes y en ninguna pequeña:

```text
  6fb9113  1059 lineas  TOOL_VALIDATED=1
  daec702   983 lineas  TOOL_VALIDATED=1
  1bb4115   332 lineas  0
  4a437ac   301 lineas  0
  6fe40b2   276 lineas  0
  54b3ea8   255 lineas  0
  AGENTS.md actual  3736 lineas  TOOL_VALIDATED=0
```

O sea: la convención **existió, se aplicó, y murió con el documento** que la
declaraba. No se perdió un dato: se perdió la norma mientras sus 24 usos
seguían en pie.

## 4 · Contradicción con `071`, registrada y no resuelta

```text
  071-el-except-que-devuelve-stub-...md :99-101

    "`AGENTS.md` §AUTOMATIZACIÓN DE VALIDACIÓN exige clasificar cada
     herramienta como `TOOL_VALIDATED` / `TOOL_PARTIAL` / `TOOL_UNVALIDATED` /
     `TOOL_BROKEN`"

  MEDIDO contra el documento que hay:
    TOOL_VALIDATED     en el AGENTS.md actual   0 ocurrencias
    §AUTOMATIZACIÓN DE VALIDACIÓN  en las 6 versiones commiteadas  0
```

La premisa de `071` era cierta de la versión de 1 059 líneas y es **falsa del
documento vigente**. Y el título de sección que cita no está en ninguna versión
commiteada, tampoco: viene de la versión de 1 101 líneas que `268` ya declaró no
recuperable.

```
  CONTRADICTION_ID  vocabulary-of-tool-state
  CLAIM_A   071: AGENTS.md exige la familia TOOL_*
  CLAIM_B   el AGENTS.md vigente declara §22 y §88, y no contiene TOOL_*
  EVIDENCIA_A  071:99-101
  EVIDENCIA_B  grep TOOL_VALIDATED AGENTS.md -> 0; git show 6fb9113:900-907
  RESOLUTION  AMBIGUO, y no se resuelve aqui
```

No se corrige `071` —los hallazgos históricos no se reescriben— y no se elige
vocabulario: eso es una decisión de política del proyecto, no una medición.

## 5 · Lo que sí se puede decir del registro

Su propio encabezado declara para qué existe:

```text
  "Para cada herramienta: qué hace, con qué contrato de entrada y salida, de qué
   depende, si su salida está validada, y qué falla. Si una herramienta falla, su
   salida no se reutiliza como evidencia hasta que se repare."
```

Y lo que hace, medido:

```text
  qué hace                         si, con PROPOSITO en 34 entradas
  contrato de entrada y salida    INPUT/OUTPUT en 3 y 2
  de qué depende                   si
  si su salida esta VALIDADA       lo afirma, sin decir con que
  que falla                        lo dice
```

**La cuarta de las cinco, que es la que gobierna el resto, es la única que no
tiene base registrada.** Un registro cuya función es decidir si una salida vale
como evidencia, y cuyas entradas no dicen de dónde sale esa decisión, no puede
cumplir su función. No es que esté mal: es que no tiene el dato.

## 6 · Por qué esto no lo arregla `toolaudit`

Porque `toolaudit` no puede decidir el estado de una herramienta. Lo que sí puede,
y hace, es **contar cuántas están**:

```text
  114 ficheros censados   =  111 nombres distintos
  con entrada en el registro    71
  sin entrada                   43
  LAST_VERIFIED   2026-10-01 11:20 -03:00
```

Y el estado de las 43 se dice con la palabra que `§10` obliga:

```
  UNKNOWN   no   'validada'   no   'rota'
```

Lo que el hallazgo añade es que **ese mismo `UNKNOWN` es el estado correcto de las
71 que sí tienen entrada**, en cuanto a la evidencia se refiere. No porque la
herramienta sea mala: porque su entrada no dice con qué se validó.

## 7 · Lo que NO se establece

```text
  cual es el vocabulario oficial
    NO SE DECIDE AQUI. Es politica del proyecto. Lo que se mide es que hay tres
    vivos y que uno no lo declara nadie
  si las 71 entradas con entrada son falsas
    NO SE AFIRMA. Se afirma algo mas pequeño y verificable: NINGUNA declara con
    que se verifico, y por eso su estado no es CITABLE como evidencia. Una
    entrada puede ser correcta y no decirlo
  si la seccion por la que se sustituyo el documento existe todavia
    NOT_DETERMINED. El titulo no esta en ninguna version commiteada
  las 43 sin entrada
    UNKNOWN, y eso es un dato, no un defecto. Su estado correcto es ese
  TOOL_VALIDATED frente al vocabulario de §22
    AMBIGUO de proposito. §22 es del documento vigente; TOOL_* es del que se
    sustituyo. Los dos existen y solo uno esta declarado
```

## 8 · Trazabilidad

```text
  docs/TOOLS-STATUS.md            3257 lineas, LAST_VERIFIED 2026-10-01 11:20
  git show 6fb9113:AGENTS.md:900  la declaracion recuperada de TOOL_*
  AGENTS.md §22 y §88             el vocabulario vigente
  findings/071:99-101             la premisa que ahora es falsa
  findings/268                    la version de 1101 lineas, no recuperable
  findings/291                    el sello y el hueco con el registro
  08-ARQUITECTURA/tools/toolaudit.py   hueco_de_registro(): cuenta, no opina
```

## 9 · Correspondencia

```text
  268   las convenciones se perdieron al sustituir el documento rector
  291   las cifras de poblacion no tienen sello
  293   ESTE: el caso donde la convencion perdida sigue viva en 24 hallazgos y en
        el registro que gobierna si una salida vale como evidencia

  y el precedente del metodo:
  071   ya habia detectado que la clasificacion de herramientas se hacia por la
        palabra 'selftest' en vez de por ejecutar el self-test, y produjo
        24 de 25 TOOL_VALIDATED falsas. Aqui se ve que ademas el vocabulario con
        el que se etiqueto ya no lo declara nadie
```

## 10 · Y un campo que parecía un número y era un texto

Cerrando esto apareció en `lint` un campo que parecía un número y era un texto:

Measurado sobre el propio informe:

```
  antes    linea="```"        el TEXTO de la ultima linea del bloque
  despues  linea=201          un entero
  filas afectadas                      36 de 43
```

El bucle que busca el final del bloque se llamaba `ln`, el mismo nombre que el
número de línea calculado dos líneas antes. Al salir del bucle, `ln` contenía el
texto de la última línea. **No hacía fallar nada**: un diccionario acepta
cualquier valor, así que `linea="```"` se guardaba tan tranquilo como
`linea=201`. Solo reventaba más downstream, en el `>` que compara contra un
entero.

Es la misma clase que el campo `MEMORY` de los buffers que nadieaba: un sitio
donde el tipo no encaja y el sistema lo acepta en silencio.

```
  PROVIDED: el sombreado de `ln` restaurado
    TypeError: '>' not supported between instances of 'str' and 'int'
  restaurado
    RESULT: PASS (33 vectores)
```

### Y la clase `HALLAZGO_AMBIGUO`

Al mirar por qué `258-veinticuatro-...` salía como referencia rota:

```
  PENDIENTE=258-*.md
```

Y hay **dos** ficheros que empiezan por `258-`. Un comodín sobre un número
duplicado no resuelve nunca: se escriba lo que se escriba, el comodín seguirá
ayudando a dos. Ese `PENDIENTE` **no se puede cumplir jamás**, y no es una
referencia rota: es una ambigua.

```text
  antes    HALLAZGO_QUE_NO_EXISTE   19
  despues  HALLAZGO_QUE_NO_EXISTE   11
           HALLAZGO_AMBIGUO          8   <- reclasificados, con el numero de
                                             candidatos y sus nombres
```

Ocho referencias estaban mal clasificadas, y ninguna estaba realmente rota.

## 11 · Lo que el código le afirma a `AGENTS.md`

La pregunta anterior —qué hace válida una entrada «validada»— tiene una segunda
mitad que sí se podía medir: no sólo qué dice el registro, sino **qué le atribuye
el propio código al documento rector**.

```text
  17 lineas de tools/ y 08-ARQUITECTURA/tools/ que AFIRMAN una proposicion
  sobre AGENTS.md en vez de nombrarlo   (con el filtro completo: 46)
```

Y una de ellas es una cita colgante de manual:

```
  tools/artifacts.py:789
    "AGENTS.md: *TOOL_UNVALIDATED no puede cerrar una afirmacion critica*"

  donde ESTA esa proposicion:  6fb9113:909
  en el AGENTS.md vigente:     0 ocurrencias de TOOL_UNVALIDATED
```

La herramienta **imprime esa cita como autoridad cada vez que se ejecuta**, y la
cita no resuelve contra el documento que está en vigor. No es un hallazgo old;
es una salida que el proyecto produce.

Reparto de las 46, medido:

```text
  EN_VIGENTE     17   la proposicion tiene su termino en el documento vigente
  SOLO_ANTES     12   lo tiene en una version que ya no es la vigente
  NO_DECIDIBLE   17   el metodo no llega
```

Y las 12 `SOLO_ANTES` **nombradas**, que es lo que hace el dato utilizable:

```text
  tools/artifacts.py          L789   tool_unvalidated
  tools/artifacts.py          L954   referencias
  tools/hwip.py               L66    investigacion
  tools/hwip.py              L955   investigacion
  tools/lint.py              L212   permisos
  tools/sysaccess.py          L13    prioritarias   <- seccion FRONTERAS PRIORITARIAS F
  08-ARQUITECTURA/tools/ipver_zero.py  L18  exactamente
  y cinco mas de govcheck, que ahora se cita a si mismo
```

`sysaccess.py:13` es el caso limpio: **`FRONTERAS PRIORITARIAS F`** es una
sección de un documento que ya no existe, y `sysaccess` sigue invocándola.

## 12 · El método necesitó tres correcciones, y las tres se pueden ver

Las clases se escribieron mal tres veces seguidas, y cada vez el número era
plausible.

### Una · El patrón no casaba con nada

```text
  r'AGENTS\.md[:\s]\s*\*?`?\s*\**\{0,2}[A-Za-z...]'
```

`\**\{0,2}` es un asterisco repetido y una llave literal. Primera ejecución:
**0 citas sobre 46**. Un cero es un número.

### Dos · Dos palabras corrientes decidían

```text
  con >= 2 terminos compartidos     EN_VIGENTE     <- MAL

  "AGENTS.md: TOOL_UNVALIDATED no puede cerrar una afirmacion critica"
    comparte 'cerrar' y 'puede'
  y salia EN_VIGENTE, con TOOL_UNVALIDATED a cero en el documento
```

Las dos palabras más comunes del castellano decidían si una proposición estaba o
no. El término que de verdad identifica la cosa es `TOOL_UNVALIDATED`, y no se
miraba.

### Tres · Dos términos largos tampoco

```text
  con los 2 mas largos   46 de 54 en NO_DECIDIBLE     <- TAMAN POCO
```

Exigir dos palabras raras a la vez es pedir más de lo que hay. Casi ninguna
afirmación tiene dos términos largos.

### Lo que quedó

```text
  UN SOLO TERMINO DECIDE: el mas largo

  y ese termino no puede salir de "AGENTS.md" itself:
    `AGENTS.md: zzzz qqqq` resolvia SOLO_ANTES con `decidio=agents`
    porque 'agents' esta en el CIEN POR CIEN de las lineas de este conjunto
    por construccion. Un termino que esta en todos los casos no distingue nada.
```

Y el vector con dientes, que es el que obliga a que esto no vuelva:

```text
  PROVIDO: `agents` vuelve a decidir
    FAIL  una linea SIN termino propio NO se decide por 'agents'
    FAIL  y si se decide, no es por un termino que viene del propio AGENTS.md
    RESULT: FAIL (20 comprobaciones)
  restaurado
    RESULT: PASS (20 comprobaciones)
```

**El primer intento de este vector no muerde.** La primera vez que se provocation la exclusión de `agents`, los 20 vectores pasaron igual: ninguno miraba ese caso. Hubo que escribir el vector antes de poder comprobar que la regla hacía falta.

Y uno de los dos vectores nuevos **fallaba en verde**, porque su lista de términos prohibidos incluía `None`, y `None` significa «no decidido», que es exactamente lo correcto en ese caso. El vector era más estricto que la regla. Tercer recordatorio de la misma semana: una prueba que no se ha ejecutado no dice nada, ni en verde.

## 13 · `NO_DECIDIBLE`, y por qué no es `NO_ENCONTRADA`

La clase se llama así a propósito, y el nombre viejo era una afirmación falsa:

```text
  antes    NO_ENCONTRADA    20 lineas
  ahora    NO_DECIDIBLE     17 lineas
```

Porque casi ninguna de esas 20 estaba ausente: eran comentarios que **nombran**
`AGENTS.md` sin afirmar nada citable, como

```text
  # IMPONE UN FORMATO QUE AGENTS.md YA NO DECLARA
```

Que dos textos no compartan un término largo no dice que la proposición falte.
Dice que un método de solape de términos no llega. `NOT_FOUND` no es
`PROVEN_ABSENT`, y aquí el que no llega es el método.

## 14 · «Herramientas de autoridad contextual»: una, de 108

La pregunta anterior era si esa clase merece existir. Contada:

```text
  herramientas .py en los dos arboles                       108
  cuya cabecera dice que su autoridad dependia del AGENTS.md
  cargado en el contexto de la sesion                          1
```

**Una.** No merece clase ni herramienta. Y la que es, se resuelve sola:

```text
  tools/hwip.py:53
    "La version de AGENTS.md cargada en el contexto de la sesion era mas corta
     y no tenia esa seccion; SE GOBIERNA POR EL FICHERO EN DISCO, y el fichero
     en disco si la tiene."
```

Y comprobado, no leído:

```text
  ¿hwip.py abre AGENTS.md en algun momento?     grep -c 'AGENTS.md"'  ->  0
```

`hwip` dice en su propia cabecera que el problema lo resolvió anclándose al
fichero, y no lee el documento. **La premisa de la pregunta era falsa**: no hay
una clase, hay una herramienta que ya se arregló y lo escribió.

## 15 · Y al mirarlo, un bug que llevaba desde `268`

`hwip.py:955` salía `SOLO_ANTES` en mi censo, decidido por `investigacion`. La
palabra aparece **4 veces en el `AGENTS.md` vigente**. Una proposición que está en
el documento, clasificada como que sólo existió en una versión anterior.

```text
  terminos("investigación")  ->  {'investigaci'}
  "investigacion" en eso     ->  False
```

`terminos()` tiene este docstring **desde que se escribió**:

```
  "Palabras significativas de un texto: minusculas, sin acentos, sin ruido."
```

Y no quitaba acentos. La causa es el orden:

```python
  re.sub(r"[^A-Za-z0-9_]+", " ", texto)
```

La `ó` no es alfanumérica, así que caía como separador y **partía la palabra en
dos**: `investigaci n`. Quitar los acentos después ya no tenía nada que quitar.
Hay que normalizar a NFD y quitar las marcas **antes** de separar.

```text
  antes    EN_VIGENTE 18   SOLO_ANTES 13   NO_DECIDIBLE 27
  despues  EN_VIGENTE 22   SOLO_ANTES 11   NO_DECIDIBLE 25
```

Cuatro citas cambian de clase por una línea mal puesta. Y el sesgo era
sistemático: **toda palabra acentuada del castellano no podía casar**, o sea que
el método apuntaba siempre en la dirección de «esto ya no está», que es
precisamente la conclusión que un documento sustituido provoca.

### Por que no se vio antes, y una correccion a lo que escribi

Escribi que el proyecto tenia dos funciones de normalizacion y que los tests
cubrian la que funcionaba. **Eso es falso, y lo corrijo**: `normalizar()` y
`terminos()` tienen contratos distintos y no son duplicados.

```
  normalizar(s)   re.sub(r"[^A-Z0-9]", "", s.upper())
                  una CLAVE COMPACTA de titulo de seccion
                  "Discriminante-declarado" -> "DISCRIMINANTEDECLARADO"
                  usos: 7    (solo titulos de seccion)

  terminos(s)     un CONJUNTO DE PALABRAS para clasificar texto
                  usos: 16   (citas, afirmaciones, documentos)
```

Y el vector de acentos que ya existia era **informativo por construccion**:

```
  vec("una seccion con acentos se compara sin acentos",
      normalizar("DISCRIMINANTE DECLARADO") == normalizar("Discriminante-declarado"))
```

Su clase de caracteres es `[^A-Z0-9]`, y la `o` acentuada no esta ahi: quitarla no
es una regla que `normalizar()` cumpla, es una consecuencia de que conserva.
**Ese test no podia fallar**, ni antes ni despues, porque ejercita una funcion
donde el fallo no puede ocurrir.

Asi que la leccion no es "habia dos normalizadores". Es mas pequena y mas util:

```
  un test sobre una propiedad que esa funcion NO PUEDE tener
    no vigila nada, y ocupa el sitio donde uno que si vigilaria
```

Y el discriminante que habia prometido queda respondido sin unificar nada: no
habia nada que unificar, porque no eran la misma funcion. Lo que habia era un
docstring que describia un contrato y un cuerpo que no lo cumplia, y eso si esta
corregido.

Es decir: el proyecto tiene **dos** funciones de normalización, `normalizar()`
que quita acentos y `terminos()` que no, y los tests cubrían la que funcionaba.
Un test de acentos no dice «los acentos están tratados»: dice «los acentos están
tratados *en la función que ese test exercises*».

```
  PROVOCADO: terminos() vuelve a partir las palabras acentuadas
    FAIL  terminos() quita acentos, como dice su docstring
    FAIL  y una palabra acentuada no se parte en dos
    RESULT: FAIL (24 comprobaciones)
  restaurado
    RESULT: PASS (24 comprobaciones)
```

## 16 · Y un vector mío que fallaba en verde

```python
  vec("terminos() quita acentos, como dice su docstring",
      "investigacion" in acc, True)
```

`vec()` toma dos argumentos y yo pasé tres: `TypeError` en la primera ejecución.
Pero lo que importa es lo de al lado:

```python
  vec("y si se decide, no es por un termino que viene del propio AGENTS.md",
      _zz.get("decidio") not in ("agents", "md", None, ""))
```

Incluía `None` en la lista de prohibidos, y `None` significa **«no decidido»**,
que en ese caso es exactamente lo correcto. El vector era más estricto que la
regla que comprobaba. Hay una forma de ese error que no falla: cuando el
prohibido es un valor que el caso bueno nunca produce, el vector pasa siempre y
nunca miró nada.

## 17 · Corrección de numeración

```text
  este fichero se escribio como 293, reservado con --reservar antes de escribir
  CORRECTED_BY: --reservar 293  RESERVADO
  el ritmo de colisiones es de 6 de 26 por escritura, asi que se comprueba
```