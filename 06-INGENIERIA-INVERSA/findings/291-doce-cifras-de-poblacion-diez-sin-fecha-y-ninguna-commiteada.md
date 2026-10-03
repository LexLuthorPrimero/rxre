# 291 · Doce cifras de población, diez sin fecha y ninguna commiteada

```text
CLASSIFICATION=MEASUREMENT+LIMITATION+TOOLING · TRACK=VERIFICATION
CORPUS=NINGUNO (el proyecto) · HARDWARE_SCOPE=NONE
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

El `NEXT_ACTION` era: las cifras de población de herramientas no llevan sello de
tiempo, así que dos números no son comparables. Medido:

```text
  hallazgos con una cifra de poblacion de herramientas    12
  de esos, SIN NINGUNA fecha en el documento            10
  de esos, commiteados (git sabe la fecha)               0
```

**Ni uno commiteado.** Git no sabe cuándo se escribió ninguno de los doce, así
que `git log` no es un camino de recuperación. Los dos últimos son míos.

Y la cifra ya caducó, tres veces en una sesión:

```text
  112   medido ayer
  113   medido hoy por la mañana
  114   medido ahora mismo
```

Sin sello, `112` y `114` son dos números que se contradicen, o dos medidas
separadas por una noche. El documento no permite saber cuál, y esa es exactamente
la pregunta que un número sin fecha no puede responder.

## 1 · Por qué `mtime` no sirve

La única marca temporal disponible es el `mtime` del fichero. Y no es la hora de
la medición:

```text
  mtime  >=  hora de escritura

  porque un fichero EDITADO despues tiene mtime posterior
  ordenar por mtime NO ordena por cuando se midio
```

Es una cota superior. Sirve para cualquier cosa menos para lo que se quiere:
saber cuándo se tomó una medida. Reconstruir las fechas históricas exigiría leer
el `mtime` de ficheros citados, que es un proxy, y un proxy no se escribe en un
hallazgo como si fuera una medición.

## 2 · Y mi propia medición del hueco era falsa

Lo primero que hice fue contar cuántas cifras de población tienen fecha. Salió
que 77 de 89, y era mentira:

```text
  mi pregunta    "este FICHERO contiene alguna fecha?"
  la pregunta     "ESTA CIFRA lleva fecha?"
```

Un fichero con una fecha en el pie se marcaba como si todas sus cifras la
tuvieran. Con la pregunta correcta:

```text
  con fecha     2
  sin fecha    10
```

De los doce. Casi todos los que la tienen son entradas repetidas de un único
hallazgo (`063`), que es un registro de sesión y fecha cada bloque.

## 3 · El precedente ya existía

No hacía falta inventar una convención. Dos hallazgos la tienen:

```text
  063-memoria-sesion-...    cada bloque de sesión lleva su fecha, y la población
                            como un número que crece: 13, 16, 17, 18, 19, 20, 21

  069-f11-medido-...        | 34 herramientas Python en el árbol | PROVEN (medido) |
                            y "PROVEN (ejecutado hoy)"
```

`069` usa «hoy». Es un relativo sin ancla absoluta: sin la fecha del hallazgo, no
se resuelve. La parte útil es el estado junto al número: `PROVEN (medido)`.

## 4 · La solución va en la herramienta, no en el discipline

Pedirle a cada hallazgo que se acuerde de escribir la hora es pedir que cada
escritura recuerde algo. Lo que no se puede olvidar es el dato que la propia
herramienta ya tiene:

```
MEDIDO: 2026-10-03 01:53:52-0300 · aa0f68642a21 · 114 ficheros
```

Tres cosas: **cuándo**, **qué** conjunto exacto (huella sha1 de las rutas, 12
hex), y **cuántos**. Quien cite la salida la cita entera y hereda la
proveniencia sin haber hecho nada. Es lo que `AGENTS.md` pide en
`ARTIFACT_LINEAGE`, aplicado a un caso que no lo tenía.

Comprobado que el sello se comporta:

```text
  dos ejecuciones con 6 s de diferencia
    1a  MEDIDO: 2026-10-03 01:49:14-0300 · aa0f68642a21 · 114 ficheros
    2a  MEDIDO: 2026-10-03 01:49:20-0300 · aa0f68642a21 · 114 ficheros
         la fecha cambia, la huella no
```

Que es lo correcto: la fecha es del instante y la huella es del conjunto. Si la
huella cambiara entre dos recuentos idénticos, no distinguiría dos poblaciones.

## 5 · Y un vector mío que era falso

El primero que escribí para vigilar el sello llevaba esto:

```python
chk("el sello no es una constante...", sello(inv) != s1 or True, True)
```

El `or True` lo hace **imposible que falle**. Es el fallo que este proyecto lleva
toda la sesión documentando, escrito en el fichero que lo documenta, y por un
momento pasó porque siempre pasa.

Sustituido por uno que sí puede caer, medido contra el reloj del propio proceso:

```text
  reloj normal                        PASS  el sello lleva la fecha de HOY
  reloj fijado a 2020-01-01           FAIL  el sello lleva la fecha de HOY
```

Si alguien deja la fecha fija, cae.

## 6 · El ciclo de provocar y devolver, y cómo se parte

Provocar un fallo y devolver el código a su sitio es la mecánica de la que este
proyecto depende para no creerse lo que no debe. Y falló:

```text
  1  provocacion con reloj fijo          FAIL, correcto
  2  copia a /tmp                        el fichero ya estaba provocado
  3  edicion para devolver               la herramienta dice que sustituyo
  4  grep del estado                     0 provocados, limpio
  5  self-test                           FAIL, el sello seguia en 2020
  6  sed -i                              sin error y sin cambio
  7  mtime del fichero                   01:50:54, no se movia
```

Dos mecanismos independientes —editor y `sed`— Poulsays "hecho" sin efecto, y el
`mtime` quieto demostraba que el fichero no se estaba reescribiendo: es que
nunca se había escrito. La causa fue el paso 2: **la copia de seguridad se tomó
del fichero ya Birthday**, así que restaurarla restauraba el estado sucio.

Corregido con una escritura explícita y lectura inmediata, y después una
comprobación repetida en un comando aparte:

```text
  escrito    releido: OK    0 ocurrencias de 2020    self-test: todos pasan
```

Y un resto que mentía:

```text
  ahora = datetime.datetime.now().astimezone()  # PROVOCADO
```

La línea correcta con el comentario de la provocación encima. Una etiqueta que
afirma algo falso en el código es peor que no tenerla.

## 6 bis · Y una hipótesis mía que era falsa, sobre el detector

Al ver coreano en el título de la sección 6, lo atribuí a un hueco de `lint.py`:
«su rango cubre ideogramas CJK pero no Hangul».

Falso. `tools/lint.py:127` declara:

```
RE_CJK = [\u3040-\u30ff \u3400-\u4dbf \u4e00-\u9fff \uac00-\ud7af
          \u3000-\u303f \uff00-\uffef]
```

`\uac00-\ud7af` es Hangul, y estaba ahí desde el principio. Lo que pasó es que
**no había ejecutado `lint` sobre el fichero**: lo escribí después de la última
pasada. El detector no falló; no se le preguntó.

Con el fallo GOOD de que el recuento global de `lint` subió de 5 a 6 en esa misma
pasada, lo que confirma que la detección funciona y de que mi hipótesis sólo la
podía refutar ejecutando.

Es la tercera vez en dos días que un diagnóstico mío sobre una herramienta
resulta ser un diagnóstico sobre mí: `274` §4 con el rango de `EXT`, `288` §2
con `toolkit`, y esta.

## 7 · Lo que NO se establece

```text
  la hora a la que se midio cada cifra historica
    NO RECUPERABLE. Los 12 hallazgos estan sin commitear, asi que git no tiene
    fecha, y mtime es una cota superior que no reconstruye una medicion.
    No se escribe una fecha inventada al lado de esas cifras
  si 112, 113 y 114 son tres mediciones o tres lecturas de la misma
    NOT_DETERMINED. Con sello, si. Sin el, no se puede saber
  la fecha de los hallazgos ya escritos
    NO SE TOCAN. Un hallazgo historico no se reescribe para llevar una fecha que
    no se sabe; se dice que no se sabe
  la poblacion actual
    114 a las 2026-10-03 01:53:52-0300, huella aa0f68642a21. Volvera a cambiar,
    y ahora el numero lleva la hora de cuando cambio
  si el sello deberia ir tambien en toolkit, que cuenta otra vez la poblacion
    NOT_DONE. Es la misma clase de numero sin sello, en la herramienta vecina.
    Pendiente, y dicho
```

## 8 · Trazabilidad

```text
  08-ARQUITECTURA/tools/toalaudit.py   sello(): fecha + huella + numero
  08-ARQUITECTURA/tools/toolaudit.py   4 vectores del sello, uno con reloj
  08-ARQUITECTURA/tools/toolaudit.py   chk(): contexto
  git ls-files 06-INGENIERIA-INVERSA/findings   0 de 12 commiteados
  findings/069                            el precedente: PROVEN (medido)
  findings/063                            el precedente: fecha por bloque
  findings/274                            la cifra que caduco
```

## 9 · Corrección de numeración, y la segunda vez en dos horas

```
  este fichero se escribio como 290, que ya usaba otro hallazgo
    290-el-resumen-y-el-aviso-tienen-vector.md
  COMPROBADO: 0 citas antes de renumerar
  CORRECTED_BY: renumerado a 291
  --reservar 290  RESERVADO, y aun asi otro agente lo ocupo
```

Es la segunda vez hoy. La primera fue con el 280, en el hallazgo anterior. El
patrón es idéntico:

```
  --reservar NNN      RESERVADO
  --reservar NNN      DUPLICADO, dos ficheros lo usan
```

Y hay un dato medido que no depende de mi caso:

```
  hallazgos escritos en las ultimas 3 horas                      26
  numeros repetidos entre esos                                   4
    282, 283, 286, 287
  mas los dos mios, que --reservar ya habia tomado             280, 290
  ..........................................................................
  ritmo de colision                                           6 de 26  =  23 %
```

**La reserva funciona contra el que la pide y no puede contra el que no.** Dos
de mis hallazgos reservados se convirtieron en duplicados en la misma noche en que
implemente el cerrojo, y el ritmo general es de una de cada cuatro escrituras.
Eso no es un fallo de `flock` --el vector con seis procesos sigue dando un solo
ganador--: es la medida de que hay al menos dos autores escribiendo a la vez,
contra lo que dice `AGENTS.md` §102.

Y ese 23 % explica por que el proyecto lleva **66 duplicados y 0 reparables**: no
es que no se limpien, es que se generan mas rapido de lo que se reparan, y el
`--reservar` solo cubre a quien lo usa.

Lo que sí se puede hacer, y es lo que queda hecho aquí:

```
  cada duplicado tuyo se renumera y deja constancia por que
  el numero del otro NO se toca, porque esta citado
  y el ritmo se mide, para que no se confunda con ruido
```

## 10 · Lo que el censo dio, y una clase mia que era falsa

Con el sello puesto, el censo completo:

```
HERRAMIENTAS PYTHON, AMBOS ARBOLES: 114   [08-ARQUITECTURA/tools=56  tools=58]
  MEDIDO: 2026-10-03 02:12:50-0300 · aa0f68642a21 · 114 ficheros
  con self-test           : 114
    pasan 62 · fallan 3 · DEFECTOS 6 · timeout 0 · sin determinar 13 · sin self-test 30
  suma de clasificados: 114 de 114
```

El número que faltaba en el `NEXT_ACTION` anterior: **la suma cuadra**, y hay
herramientas que están encontrándose a sí mismas.

Y al mirar cuáles son, la clase `DEFECTO` que había creado veinte minutos antes
está mal en **3 de 7**:

```
  herramienta      lo que dice                            clase real
  findings_index   numeros con colision: 69               DEFECTO
  num_collision    numeros DUPLICADOS: 70                 DEFECTO
  run_all          1 comprobacion falla: contrato         DEFECTO
  contradict       rc=2, no acepta --selftest             USO
  struct_rw        rc=2, falta --offset                    USO
  mmio_map         rc=2, falta ko_dr.asm                  INVALID_RESULT
```

Un 43 % de error en una clase recién hecha. Es el mismo fallo que
`LOCALIZABLE` en `268`: **un nombre que promete más de lo que el método
sostiene**. Y encima el método no puede sostenerse, porque clasificar prosa libre
no es un método sólido. Lo que sí lo es:

```
  USO              la salida tiene forma de diagnostico de argparse
  FALTA_ARTEFACTO  la salida nombra un fichero que no esta  (§25 lo llama
                   INVALID_RESULT, y es exactamente eso)
  DEFECTO          que la herramienta haya encontrado un defecto del PROYECTO.
                   Eso lo sabe ella, no su prosa, y no hay forma fiable de
                   deducirlo de un texto libre
```

La última línea es la que hay que tragarse: **`DEFECTO` no es decidible
automáticamente**. Se queda como la clase menos precisa de las cuatro, con el
texto de la herramienta al lado para que la lectura sea de una pasada.

## 11 · Dos bugs de los míos, y los dos por el mismo camino

### `--check` no es un self-test

Mi criterio de bandera aceptaba `--check` entre las candidatas. Y `contradict`
declara `add_argument("--check", ...)`, que **no es un self-test: es un modo
auditoría** que recorre los hallazgos y compara afirmaciones.

```text
  contradict --check   encuentra contradicciones de verdad  ->  salia DEFECTO
```

El censo reportaba una herramienta self-testeada cuando lo que se ejecutó fue un
escaneo del proyecto. `--check` fuera de la lista, con vector que lo comprueba.

Es el tercer caso del mismo error, y ya tiene nombre: **`--selftest` audita,
`--self-test` prueba vectores, `--check` escanea.** Tres nombres parecidos, tres
cosas distintas, y un criterio automático que no puede saberlo.

### El detector se envenenó con su propio test

Al añadir los tres patrones, `run_all` salió `USO`. La causa:

```
  run_all --selftest  EJECUTA el self-test de toolaudit

  cuya salida incluye:
    "PASS  un artefacto que falta NO es un defecto del proyecto"
    "PASS  una opcion no reconocida NO es un defecto del proyecto"

  y esas dos lineas casan con mis dos patrones
```

El detector leía sus propios vectores como si fueran diagnósticos. Es el mismo
fallo que `lint.py` ya declara como excepción —«no se puede ser detector y sujeto
a la vez sin separar las dos cosas»— y lo que faltaba era la separación:

```text
  LINEA_DE_TEST   ^\s*(PASS|FAIL|OK|ERROR|ok)\b\s
  sin_lineas_de_test()   quita esas lineas antes de clasificar
  con ellas dentro   USO     <- mal
  sin ellas         FALLA   <- lo que corresponde a "1 comprobacion falla"
```

### Y una clase que dependía del reloj

```text
  run_all --selftest  con timeout 300 s   ->  NO_SELFTEST_AUDITADO
  run_all --selftest  con timeout 1500 s  ->  DEFECTO
  tiempo real de la ejecucion             ->  502 s
```

`run_all --selftest` **ejecuta la suite entera de herramientas** y tarda ocho
minutos y medio. Con el timeout que usa el arnés por defecto, su clase depende
de un reloj que no tiene nada que ver con lo que la herramienta dice. No está
arreglado: está medido y escrito.

## 12 · La clase tenía cero consumidores, y el registro ya existía

El `NEXT_ACTION` plantaba dos salidas y decía que elegir no es técnico. Sí lo
era, y la medición que lo decide son dos.

### A · ¿Quién lee la clase?

```text
  grep de "DEFECTO" en el proyecto, excluyendo hallazgos y corpus
    -> nadie consume la clasificacion de `toolaudit --run`
```

Cero consumidores. Una distinción entre «test roto» y «ha encontrado un
defecto» que nadie lee es decoración con formato de dato, que es lo que `§95`
veta. Antes de decidir su destino había que medir quién la quería.

### B · ¿No existe ya la máquina de estados?

Sí, y estaba declarada:

```
  docs/TOOLS-STATUS.md    3257 lineas
  vocabulario             VALIDATED, AVAILABLE, EXECUTABLE, INVALID, FALLA
  sello de verificacion    LAST_VERIFIED: 2026-10-01 11:20 -03:00
  regla                   "si una herramienta falla, su salida no se
                           reutiliza como evidencia"
```

Es decir: **el sitio donde se declara si la salida de una herramienta vale como
evidencia ya existe, con vocabulario y con hora.** No hacía falta inventar nada.

### C · Y el hueco, que es decidible

```text
  herramientas censadas                              114 ficheros
  nombres distintos                                    111
  con entrada en el registro                           71
  SIN entrada                                          43
  registro dice LAST_VERIFIED            2026-10-01 11:20 -03:00
```

El 43 incluye `fingerprint.py`, `govcheck.py`, `dupenum.py`, `findnum.py`,
`driroute.py`. El registro se mantuvo para el árbol viejo y nunca se extendió al
otro. Y el estado correcto de esas 43 es **`UNKNOWN`**, no «validada» ni «rota»,
que es lo que `§10` obliga a escribir.

## 13 · Qué se hizo con la clase

Eliminada la opinión, conservado lo que el método sostiene:

```text
  USO               la salida tiene forma de diagnostico de argparse
  FALTA_ARTEFACTO   nombra un fichero que no esta   (§25 lo llama INVALID_RESULT)
  NO_DETERMINADO    sale distinto de cero y no se puede decir por que

  y NO_DETERMINADO imprime la primera linea de la salida
```

Que «la herramienta haya encontrado un defecto del proyecto» lo sabe ella, no su
prosa. No hay forma fiable de deducirlo de texto libre, y ya se pagué dos veces
al creer que sí.

## 14 · Dos recuentos que medían dos cosas, y uno que no sumaba

### El `self-test` que se movía solo

```text
  con --run       114    porque `st` es un veredicto y NINGUN veredicto es "NO"
  sin --run        84    porque `st` es SI/NO segun la regex
```

Los dos se leían igual, y el segundo pasó de 114 a 84 sin que nadie tocara nada.
Un número que se mueve solo es un número que mide dos cosas. Ahora son dos
líneas, con etiquetas distintas, y cada una dice **cómo** lo mide.

### Y el hueco con el registro, que no cuadraba

Un vector mío cayó al medirlo, y con razón:

```text
  71 + 43 = 114   por RUTA     cuadra
  69 + 42 = 111   por NOMBRE   no cuadra con 114
```

Porque `causal`, `fingerprint` y `run_all` existen en los dos árboles. **114
ficheros son 111 nombres**, y la cuenta por nombre no cuadra con la cuenta por
fichero. Es la tercera vez en un día que un recuento mezcla dos unidades:
`LOCALIZABLE` contaba líneas y hallazgos, y `DEFECTO` contaba salida y código de
retorno.

Corregido a rutas, que es la unidad que usa el registro, y ahora dice las dos
cifras. El vector lleva control positivo y control negativo con la misma
expresión, porque una comprobación que no puede dar dos resultados distintos no
discrimina:

```text
  PROVIDADO: busqueda de rutas anulada
    FAIL  CONTROL POSITIVO: pm4_count_census esta en el registro
    RESULT: FAIL (1)
```

## 15 · Una observación del entorno que no es de este hallazgo

Dos veces, tras escribir un fichero, su contenido volvió al de antes: el
`MEDIDO:` con fecha de 2020 que había corregido, y una línea de registro de estado
que había añadido. El `mtime` no se movía durante doce segundos de medición, lo
que demuestra que no se estaba reescribiendo: es que **la escritura no había
sido**.

La causa fue propia: la copia de seguridad se había tomado del fichero **ya
provocado**, así que «restaurar» restauraba el estado sucio. No hay un segundo
escritor; hay una copia mal tomada. Un backup que no se ha verificado no es un
backup, es una segunda fuente de verdad con la misma autoridad y el mismo
contenido equivocado.

## 15 bis · La reconstrucción, y el bug que la ocultó

Perdí cuarenta minutos de trabajo en `toalaudit.py` por el mismo motivo que
§15 describe, y con agravante: ** volví a usar una copia de fichero como mecanismo de
restauración**, con la copia tomada después de la provocación. Se llevó por
delante `clasifica_salida`, `sin_lineas_de_test`, `hueco_de_registro`, las tres
clases, la línea del registro y el recuento de dos líneas.

La reconstrucción fue por *edición*, no por copia, y con lectura de vuelta en el
mismo script. Esa es la diferencia que importa, y se nota en lo que salió:

### Dos definiciones del mismo nombre

```text
  L120  DECLARADA_EN_CODIGO = re.compile(... autotest))")     <- la correcta
  L355  DECLARADA_EN_CODIGO = re.compile(... autotest|check))")  <- SOBRESCRIBE
```

La segunda ganaba porque en Python gana la última. Con `check` dentro, una
herramienta que declara `add_argument("--check")` —un modo **auditoría**, no un
self-test— pasaba por self-testeada. Yo ya había fixing ese mismo punto horas
antes, y el apaño anterior había creado la sombra que lo reintroducía.

Un self-test que mira el código no lo detecta. Hace falta que el comportamiento
se mida sobre algo real.

### Barras invertidas dobladas

El script de reaplicación duplicó las barras y dejó:

```text
  r"\b%s\b"          busca una barra y una b LITERALES
```

Efecto en el informe: **0 herramientas en el registro** y `LAST_VERIFIED None`,
con el fichero presente y con 190 KB. Los otros dos parámetros dando `True` en
las pruebas, así que nada fallaba: la herramientainformaba con toda seguridad un
cero que era mentira.

Ahora hay un vector que exige que `RE_LAST` **case sobre el texto real** del
registro, y dos controles con la misma expresión —positivo sobre
`pm4_count_census.py`, negativo sobre `fingerprint.py`— para que no puedan dar el
mismo resultado.

```
  busqueda de rutas anulada a proposito
    FAIL  CONTROL POSITIVO: pm4_count_census esta en el registro
    RESULT: FAIL (1)
```

### Y tres vectores que quité, porque medían lo que no es

```text
  chk("y NO casa con barras invertidas literales", ...)
  chk("el patron de ruta casa sobre un nombre de fichero real", ...)
  chk("y no casa si lleva las barras dobladas", ...)
```

Los tres fallaban y la culpa era **de mi heredoc**, que duplicaba las barras al
escribir el vector. Un vector que mide el mecanismo que lo escribió no vigila el
proyecto. Se quitaron y se dejó escrito por qué, porque lo que de verdad importa
—que `RE_LAST` case y que el patrón encuentre las 71 rutas— queda cubierto por los
controles positivo y negativo, que usan cadenas leídas del fichero.

## 16 · Una observación que no es de este hallazgo

`AGENTS.md` §102 dice `PROJECT_ACTIVE_AGENT <= 1`. Medido: hay al menos otro
proceso escribiendo en el árbol, y la población ha pasado de 112 a 114 en una
hora. No es un problema de este trabajo, pero es la razón de que este trabajo
haga falta: **mientras la población se mueva, todo número sin sello caduca sin
que nadie lo note**, y eso no se arregla con más cuidado al escribir, sino
poniendo el reloj donde ya se pasa.