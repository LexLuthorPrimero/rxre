# 274 · La población de herramientas era 112 y yo venía contando 31

```text
CLASSIFICATION=MEASUREMENT+ERROR+TOOLING · TRACK=TOOLING
CORPUS=NINGUNO (el proyecto) · HARDWARE_SCOPE=NONE
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

Un número que he repetido en varios informes:

```
31 herramientas, 407 comprobaciones, todas verdes
```

Y que no era el del proyecto. Medido:

```text
  tools/                        58 .py
  08-ARQUITECTURA/tools/        54 .py
  nombre compartido                3
  contenido identico (sha1)       0
  ..........................................
  poblacion UNICA               112
```

**Cero solape por contenido.** No son 54 herramientas con tres alias: son 112
distintas. Mi recuento cubría 31, el **28 %**.

## 1 · De dónde salía el 31

De contar las que imprimen un número en **una forma literal**:

```text
  "N vectores"  /  "N comprobaciones"
```

Los cuatro formatos que de verdad se usan al lanzar `--selftest` en `tools/`:

```text
  A  N vectores/comprobaciones               31
  B  RESULTADO OK + numero en otra forma      2
  C  RESULTADO OK SIN NUMERO                 14
  D  ni RESULTADO ni recuento                10
  ..........................................
  con numero legible: 33 de 57
  SIN numero       : 24 de 57
```

Veinticuatro de 57 no dan **ningún observable cuantificado** de su propio
self-test. Por eso el total del proyecto no es 407: es un suelo sobre el 58 % de
las herramientas, y su valor real es `NOT_DETERMINED`.

## 2 · El fallo que sí era de la herramienta

`toolaudit.py` existe exactamente para esto: su cabecera dice

> `toolaudit.py -- mide F11: qué herramientas existen, cuáles producen un titular, y
> si alguien ha LEIDO ese titular o sólo lo ha ejecutado.`

Y tenía el alcance clavado en un árbol:

```python
toolaudit.py:70   TOOLS = f"{PROJECT}/08-ARQUITECTURA/tools"
```

Su propio `inventariar()` recorría sólo ese `TOOLS`, y `tiene_titular_en_codigo()`,
`titular_de_codigo()` y `corre_self_test()` construían la ruta a mano desde ahí. Con
eso, **cualquier herramienta de `tools/` devolvía `""`**: se leía un fichero
inexistente y salía vacío sin avisar.

Medido, tras el parche:

```text
  HERRAMIENTAS PYTHON, AMBOS ARBOLES: 112   [08-ARQUITECTURA/tools=54  tools=58]
    con self-test           : 82
    con titular numerico    : 82
    que AVISAN si su filtro falla : 4
    CITED en la documentacion: 107 de 112
    NO cited             : 5
```

La misma clase de fallo que ya está registrada en el proyecto: **una prueba que
certifica un contrato falso**. El censo certificaba 54 cuando la población son 112,
y pasaba.

## 3 · Segundo fallo en la misma herramienta

`corre_self_test()` lanzaba siempre `--self`:

```python
subprocess.run([sys.executable, p, "--self"], ...)
```

Pero en `tools/` la convención es `--selftest`. La diferencia es observable:

```text
  SELF_TEST  acepta  --self, --self-test, def selftest, def self_test
  la EJECUCION usaba SIEMPRE  --self
  una herramienta que solo acepta --selftest  ->  rc != 0  ->  "FALLA"
```

Es decir: `FALLA` no significaba «el self-test falla», sino «yo invoqué una bandera
que no es la suya». El instrumento medía el instrumento, que es la forma más
limpia de no medir nada. Ahora usa la bandera que la herramienta declara en su
propio código, y por eso el recuento de la suite cambió: `validate_rx550_final`,
que «fallaba» por no aceptar `--selftest`, pasa.

## 4 · Tres errores míos, y el más grave de ellos

```text
  1  "el lint no escanea tools/, hay un hueco". FALSO. `EXT` ya incluye .py y
     `ficheros()` camina todo el arbol. El lint ya reportaba tools/fingerprint.py:82
     y yo lo lei como "solo hallazgos" porque filtre por nombre de fichero.
     Lo comproBE y lo desmenti antes de construir nada encima.

  2  "46 herramientas NO REGISTRADAS". Sesupports? NO. La tabla salio de un grep
     debil contra `02-AUDITORIA/herramientas.md`, que NO EXISTE, con un
     fallthrough a un grep recursivo sobre 01-AUDITORIA. Los 3 "REGISTRADA" eran
     coincidencias de palabra: "causal" y "fingerprint" aparecen en cualquier
     prosa. La tabla entera era basura y queda ANULADA. Y NOT_FOUND no es
     PROVEN_ABSENT: no hay registro de herramientas que leer, que es otra cosa.

  3  "27 herramientas pasan sin decir nada". FALSO, y lo vi al mirar dos. Imprimen
     "pruebas: 33   fallos: 0" y "RESULTADO OK · vectores conocidos reproducidos".
     Mi grep buscaba una sola frase literal y clasificaba como mudo a quien habla
     en otro dialecto. El fallo real es que NO HAY dialecto comun, que es distinto
     y si es un hallazgo.
```

El tercero es el que más daño habría hecho: de haberme creído, publicaba un
recuento de herramientas mudas que era la mitad falso, y con ese titular
justificaba reescribir 24 herramientas que funcionan.

## 5 · Lo que se cambió, y con qué dientes

`toolaudit.py`,Ampliado. No se creó una herramienta nueva: el dueño ya existía y
apuntaba mal (§40: EXISTING TOOL? → VALIDATE/USE).

```text
  ARBOLES = [08-ARQUITECTURA/tools, tools]
  resolver(nombre)          busca en los dos, no en uno
  inventariar()             recorre los dos, deduplica por realpath
  corre_self_test()         usa la bandera que la herramienta DECLARA
  los tres que hacian ruta a mano  pasan por resolver()
```

Cinco vectores nuevos, y uno de ellos tiene dientes de verdad:

```text
  PASS  una herramienta de tools/ RESUELVE por nombre
  PASS  el censo cubre tools/ y 08-ARQUITECTURA/tools/
  PASS  VECTOR CON DIENTES: quitar el segundo arbol encoge el censo
  PASS  el censo se restaura tras el mutaje
  PASS  ningun fichero aparece dos veces en el censo
```

El tercero muta `ARBOLES` a un solo árbol y exige que el censo **encoga**. Si
pasara con un solo árbol, no probaría nada. Y hay un cuarto vector que exige que el
número vuelva tras el mutaje, porque un test de dientes que ensucia el estado para
siempre es otra forma de certificar un contrato falso.

## 6 · Un rótulo que mentía

Tras el parche, la primera línea seguía diciendo:

```text
  HERRAMIENTAS PYTHON EN 08-ARQUITECTURA/tools: 112
```

Con el alcance cambiado, esa cabecera es falsa, y una cabecera falsa es peor que
ninguna: se lee como el alcance de todo lo de abajo.

```text
  HERRAMIENTAS PYTHON, AMBOS ARBOLES: 112   [08-ARQUITECTURA/tools=54  tools=58]
```

## 7 · Lo que NO se establece

```text
  el total de comprobaciones del proyecto
    NOT_DETERMINED. 407 es un suelo sobre 31 de 112 herramientas. No se afirma
    la cifra real hasta que 24 herramientas mas digan cuantas hacen.
  el estado de VALIDACION de esas 24
    UNKNOWN. Que no impriman numero no significa que no se validen: se validan
    mirando la salida a mano, que es lo que se ha estado haciendo
  si las 112 herramientas son 112 herramientas DISTINTAS en proposito
    NO PREGUNTADO. El censo las cuenta; si hay solape funcional entre `causal`,
    `causal_chain` y `causal_map` es otra pregunta, con otra metrica
  las 5 NO CITED
    SOSPECHOSO, que es lo que dice la propia herramienta. Mide presencia del
    nombre en un .md, no epistemologia
  por que hay 3 nombres compartidos y 0 contenidos identicos
    NOT_INVESTIGATED. Los 3 son `causal`, `fingerprint` y `run_all`, y los dos
    ultimos son versiones distintas de la misma idea
```

## 7 bis · Correspondencia: 245 ya sabía esto

Antes de escribir esto comprobé si lo de la reserva no atómica era un
descubrimiento mío. **No lo es.**

```text
  findings/245-cien-numeros-de-hallazgo-duplicados-y-la-reserva-no-atomica.md
    :143  "## 5 · La reserva no atómica, que es la causa de fondo"
    :148  "el defecto está en que la reserva no reserva"
    :153  "1  un fichero de bloqueo con flock, y un numero reservado que se
             okatiene"
    :164  "El mecanismo es flock, y no está hecho"
```

245 ya diagnosticó la causa y **prescribió exactamente la solución**: `flock` y
un número reservado que se mantiene tomado. Es decir, el defecto estaba escrito,
con nombre y con remedio, y el remedio seguía sin hacerse.

Lo que aporta esta sección es la **ejecución**, y una observación que 245 no
tenía:

```text
  lo que faltaba no era el diagnostico
  faltaba un vector que MUERDA al quitar el flock
```

El vector que parecía bueno se pasaba sin cerrojo, porque seis procesos que
arrancan escalonados se serializan solos. El que muerde mide el tiempo de
espera. Sin esa distinción, la implementación podía haberse dado por buena con
un test que no distinguía el cerrojo de su ausencia.

CORRECTED_BY: `245` §5 es el antecedente del defecto. Esta entrada no lo
descubre, lo implementa y lo prueba.

## 8 · Lo que costó el número: la reserva no era atómica

Escribir este hallazgo interfered con el número. Lo que pasó, medido:

```text
  18:49:41  272-el-techo-de-overdrive-sale-de-una-lectura-fuera-de-rango.md
  18:56:35  272-cg-mask-y-cu-mask-son-categorias-distintas.md
  19:04:41  272-la-poblacion-de-herramientas-era-112-y-contamos-31.md
```

Tres ficheros con el mismo número, quince minutos, tres autores.

Y lo importante: **`nextnum.py --check` no tenía fallo**. Informó `LIBRE` con razón,
porque en ese instante no había fichero. El defecto es otro, y es estructural:

```text
  --check  INFORMA
  <hueco>
  escribir el fichero
```

Comprobar y escribir **no es una operación atómica**, y en el hueco cabe otra
petición. Dos autores que pasen a la vez se llevan el mismo número.

### Los 66 duplicados, y por qué probablemente son esto

El proyecto arrastra 66 números duplicados y 0 reparables. La lectura más
barata —y la que encaja con esto— es que **no son errores de quien escribe, son
errores de quien reparte números**. Un repartidor que informa sin tomar no puede
garantizar unicidad, por muy correcta que sea su respuesta.

`AGENTS.md` §102 dice `PROJECT_ACTIVE_AGENT <= 1`, y eso reduce la probabilidad.
No la hace cero, y las sesiones que incumplen esa regla se solapan igual. La
regla es de disciplina; el reparto tiene que ser de mecanismo.

### `--reservar`

```text
  --reservar NNN   toma el numero de forma ATOMICA
                  devuelve 0 si se concede, 1 si ya estaba ocupado
                  --check NO reserva, y ahora lo DICE en el --help
```

`flock` exclusivo sobre `.nextnum.lock`, que es lo que el kernel ya ofrece para
esto. Si el proceso muere, el cerrojo se suelta solo: un número reservado se
queda **ocupado**, que es el fallo tolerable, y no **colgado**, que es el que no
lo es.

Y una cosa que hacía falta y no estaba: `reservados()`. El registro de reservas
vive en el fichero de bloqueo y `indice()` mira ficheros de hallazgos, así que
**una segunda reserva del mismo número se concedía**. Los dos vectores que
estaban fallando lo detectaron. Ahora `--check` también ve las reservas, que si
no informaría `LIBRE` sobre un número ya tomado y repetiría el defecto por el
otro lado.

## 9 · Un vector con dientes que NO tenía dientes

Es lo que máspresupuesto costó, y merece su propio apartado porque es el error que más
se ha repetido en este proyecto: **una prueba que dice vigilar algo y no lo
vigila**.

El primer vector de carrera lanzaba seis procesos pidiendo el mismo número. Con el
cerrojo puesto: uno gana. Perfecto. Pero entonces lo provoqué:

```text
  Cerrojo DESACTIVADO a proposito
    OK     la primera reserva de 001 concede
    OK     la segunda reserva de 001 RECHAZA
    OK     un numero ya ocupado por un FICHERO no se puede reservar
    OK     6 procesos piden 050 a la vez, gana UNO
    RESULT: PASS (17 vectores)
```

**Diecisiete de diecisiete sin cerrojo.** El vector no muerde: los seis procesos
arrancan escalonados por el arranque del intérprete y se serializan solos. No
había carrera, había seisolone.

La causa no estaba en el vector sino en lo que el vector medía. Medía el
resultado, que puede salir bien por Fortune; tenía que medir la **propiedad**.

El sustituto mide el tiempo: el padre toma el cerrojo, el hijo llama a
`reservar()`, y el padre lo suelta medio segundo después. Sin `LOCK_EX` no hay
espera posible, así que la espera lo separa sin discusión.

```text
  CON cerrojo:     FAIL   espera 0.00s
  SIN cerrojo:     FAIL   espera 0.00s

  restaurado:      PASS   espera 0.48s
  ---------------- RESULT: PASS (17 vectores)
  provoked:        FAIL   espera 0.00s
```

El vector de seis procesos se conserva, porque reproduce de verdad la carrera de
los 272, y lleva escrito que **no prueba el cerrojo**. Es la misma disciplina que
las excepciones de `lint.py`: un límite que se declara es un límite; un límite
escondido hace que el recuento de fallos parezca mejor de lo que es.

## 10 · Lo que NO se establece

```text
  el total de comprobaciones del proyecto
    NOT_DETERMINED. 407 es un suelo sobre 31 de 112 herramientas. No se afirma
    la cifra real hasta que 24 herramientas mas digan cuantas hacen.
  el estado de VALIDACION de esas 24
    UNKNOWN. Que no impriman numero no significa que no se validen: se validan
    mirando la salida a mano, que es lo que se ha estado haciendo
  si las 112 herramientas son 112 herramientas DISTINTAS en proposito
    NO PREGUNTADO. El censo las cuenta; si hay solape funcional entre `causal`,
    `causal_chain` y `causal_map` es otra pregunta, con otra metrica
  las 5 NO CITED
    SOSPECHOSO, que es lo que dice la propia herramienta. Mide presencia del
    nombre en un .md, no epistemologia
  por que hay 3 nombres compartidos y 0 contenidos identicos
    NOT_INVESTIGATED. Los 3 son `causal`, `fingerprint` y `run_all`, y los dos
    ultimos son versiones distintas de la misma idea
  los otros 65 duplicados
    NO RESUELTOS por esta herramienta. `--reservar` impide los nuevos; los
    antiguos siguen necesitando leer dos hallazgos y decidir, que no es
    automatizable
```

## 11 · Trazabilidad

```text
  08-ARQUITECTURA/tools/toolaudit.py   :70    TOOLS clavado a un arbol (corregido)
  08-ARQUITECTURA/tools/toolaudit.py   :112   inventariar() sobre un arbol (corregido)
  08-ARQUITECTURA/tools/toolaudit.py   :413   rotulo con alcance equivocado (corregido)
  tools/nextnum.py                     :100   reservar(), sin reserva atomica
  tools/nextnum.py                     :130   reservados(), registro invisible al indice
  tools/nextnum.py                     :250   vector de carrera que no muerde
  tools/lint.py                        :118   EXT ya incluia .py: mi hipotesis era falsa
  02-AUDITORIA/herramientas.md                 NO EXISTE: no hay registro que leer
  .nextnum.lock                               registro de reservas, artefacto nuevo
```

## 12 · Y el código de salida tampoco significa lo que parece

Al contar las 105 herramientas de los dos árboles, once salen con `rc != 0`.
La primera reacción es «se han roto». Medido:

```text
  validate_rx550_final   rc=2   no acepta --selftest. Preexistente y declarado.
  findings_index         rc=1   DEFECTO DE INTEGRIDAD: el numero de hallazgo
                                  no es clave unica
  num_collision          rc=3   reporta el problema de colisiones
  toolkit                rc=1   contrato valido 40/47
```

Las tres últimas **estánInformando de un defecto del proyecto**. Su self-test
funciona: ha encontrado algo y por eso salen distinto de cero.

```text
  convencion A   rc 0    = "todo pasa"          -> 11 herramientas
  convencion B   rc != 0  = "he encontrado un defecto"  -> 3 herramientas
  y rc != 0 tambien significa "mi test se ha roto"      -> las dos cosas
```

Es el espejo exacto de lo que `AGENTS.md` §24 prohíbe en la otra dirección. Ahí
está escrito que `binary missing + exit 0 = INVALID_RESULT`; aquí ocurre que
`defecto encontrado + rc 1 = test roto`, y **una suite que agrega códigos de
salida no puede distinguir los dos casos**.

No lo corrijo, porque el arreglo no es mío: o estas herramientas salen con 0 y
dejan el defecto en el texto, que es peor, o cambian la semántica de todo el
proyecto. Lo que sí hago es **dejarlo escrito**, porque mientras no esté escrito
cualquier recuento de "cuántas herramientas fallan" es un número sin unidad.

Y hay un detalle que hace esto más grave de lo que parece:

```text
  findings_index --selftest  ->  "el numero de hallazgo no es clave unica"
```

Eso no es un defecto hipotético. Es **este hallazgo**. Mi 272 se colisionó con
dos ficheros más, y la herramienta que existe para detectinglo lleva informing
de ello desde antes de que yo empezara.

## 12 · Corrección de numeración

```text
  este fichero se escribio como 272, que ya usaban otros dos hallazgos
  CORRECTED_BY: renumerado a 274
  COMPROBADO: 0 citas a "272-la-poblacion" antes de renumerar
  el numero 272 sigue duplicado entre los otros dos ficheros, y NO se toca:
    renumerar un miembro cuando el otro esta citado rompe la referencia
  --reservar 274  RESERVADO antes de escribir
```