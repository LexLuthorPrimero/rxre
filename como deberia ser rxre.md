La forma en que yo diseñaría RXRE no sería como un menú que permite ejecutar Ghidra, Rizin, Coccinelle, GDB, un solver y veinte herramientas más. Eso sería solamente un lanzador de herramientas. Lo diseñaría como un sistema de investigación que convierte preguntas en afirmaciones verificables, donde cada herramienta cumple una función dentro de una cadena causal y la IA dirige la investigación sin poder confundir sus interpretaciones con los hechos.

La idea central es esta: yo no debería tener que saber de antemano qué herramienta usar, dónde buscar ni qué comando ejecutar. Debería poder formular una pregunta técnica y recibir evidencia trazable, un modelo de lo que sucede, las incertidumbres que persisten y la siguiente prueba capaz de distinguir entre explicaciones rivales.

Por ejemplo, si abro RXRE y pregunto «¿quién escribe esta entrada de la tabla de páginas y cómo llega ese valor a la GPU?», RXRE no debería limitarse a encontrar una función con un nombre prometedor. Debería reconstruir el recorrido completo desde el productor del valor hasta su efecto observable, incluyendo las transformaciones intermedias y los puntos todavía no demostrados.

## 1. El mapa general de RXRE

Este sería mi mapa conceptual de la plataforma completa. Las herramientas están abajo; el núcleo que las conecta está en el centro; la IA trabaja arriba, sobre evidencia estructurada, no directamente sobre una colección caótica de resultados.

```
                         USUARIO / CHATGPT / IA LOCAL
                                      |
                                      | pregunta en lenguaje natural
                                      v
+-------------------------------------------------------------------+
|                         RXRE FRONTEND                             |
|                                                                   |
|  Chat / CLI / API / MCP / IDE                                     |
|                                                                   |
|  "Quien escribe VM_CONTEXT0_CNTL y bajo que condiciones?"         |
+----------------------------------+--------------------------------+
                                   |
                                   v
+-------------------------------------------------------------------+
|                     1. ORQUESTADOR DE INVESTIGACION               |
|                                                                   |
|  A. Interpreta la pregunta                                        |
|  B. Identifica el objeto y el alcance                             |
|  C. Descompone la pregunta en obligaciones de prueba              |
|  D. Consulta lo que ya se sabe                                    |
|  E. Identifica contradicciones y lagunas                           |
|  F. Selecciona la siguiente prueba con mayor poder discriminante  |
|                                                                   |
|  No elige herramientas por popularidad: las elige por necesidad.  |
+----------------------------------+--------------------------------+
                                   |
                                   v
+-------------------------------------------------------------------+
|                    2. MODELO DEL OBJETO                           |
|                                                                   |
|  Archivos / funciones / simbolos / estructuras / registros        |
|  Procesos / memoria / eventos / instrucciones / estados           |
|  Relaciones de llamadas / escrituras / dependencias / efectos     |
|                                                                   |
|  Identidad + version + procedencia + alcance + confianza          |
+----------------------------------+--------------------------------+
                                   |
                                   v
+-------------------------------------------------------------------+
|                     3. MOTOR DE PLANIFICACION                     |
|                                                                   |
|  Pregunta                                                         |
|    -> subpreguntas                                                |
|    -> hipotesis rivales                                           |
|    -> evidencias necesarias                                       |
|    -> capacidades requeridas                                      |
|    -> pruebas discriminantes                                      |
|    -> criterios de cierre                                         |
+----------------------------------+--------------------------------+
                                   |
                                   v
+-------------------------------------------------------------------+
|                     4. ROUTER DE CAPACIDADES                      |
|                                                                   |
|  Busca capacidades, no nombres de herramientas.                  |
|                                                                   |
|  "Encontrar escritores" -> referencias cruzadas + analisis estatico|
|  "Seguir el valor"      -> dataflow + CFG + desensamblado          |
|  "Confirmar el efecto"  -> debugger / trazas / medicion            |
|  "Descartar hipotesis"  -> prueba diferencial / solver / test      |
|                                                                   |
|  Comprueba disponibilidad, requisitos, coste y limitaciones.       |
+----------------------------------+--------------------------------+
                                   |
                  +----------------+----------------+
                  |                |                |
                  v                v                v
        +----------------+ +----------------+ +----------------+
        | FUENTES        | | ANALISIS       | | EJECUCION      |
        |                | |                | |                |
        | Codigo fuente  | | Ghidra         | | GDB / LLDB     |
        | Headers        | | Rizin          | | Frida          |
        | Firmware       | | radare2        | | QEMU           |
        | Documentacion  | | Coccinelle     | | AFL++          |
        | ELF / DWARF    | | Tree-sitter    | | perf / ftrace  |
        | BTF / simbolos | | CFG / dataflow | | trazas reales  |
        +-------+--------+ +-------+--------+ +-------+--------+
                |                  |                  |
                +------------------+------------------+
                                   |
                                   v
+-------------------------------------------------------------------+
|                  5. ADAPTADORES Y NORMALIZACION                   |
|                                                                   |
|  Herramienta -> resultado bruto -> formato canonico               |
|                                                                   |
|  Identidad del objeto                                             |
|  Ubicacion exacta: archivo, linea, simbolo, offset o evento        |
|  Entrada / salida / relaciones descubiertas                       |
|  Version de herramienta y parametros                              |
|  Errores, cobertura, limites y resultado vacio                    |
|                                                                   |
|  Los datos originales se conservan. Normalizar no significa       |
|  borrar las diferencias entre herramientas.                        |
+----------------------------------+--------------------------------+
                                   |
                                   v
+-------------------------------------------------------------------+
|                     6. GRAFO DE EVIDENCIA                         |
|                                                                   |
|  PRODUCTOR -> TRANSFORMACION -> REPRESENTACION -> CONSUMIDOR      |
|       |              |                |               |            |
|       +--------------+----------------+---------------+            |
|                                   |                               |
|                         EFECTO / CONSECUENCIA                     |
|                                                                   |
|  Cada relacion tiene evidencia, alcance, procedencia y estado.    |
|  Las relaciones inferidas no se presentan como observadas.        |
+----------------------------------+--------------------------------+
                                   |
                                   v
+-------------------------------------------------------------------+
|                  7. MOTOR DE PRUEBAS Y VALIDACION                 |
|                                                                   |
|  Contrasta hipotesis                                              |
|  Detecta contradicciones                                          |
|  Busca contraejemplos                                             |
|  Genera pruebas minimales                                         |
|  Compara herramientas independientes                              |
|  Ejecuta pruebas dinamicas cuando aportan informacion nueva       |
|  Registra resultados negativos y confusores                       |
+----------------------------------+--------------------------------+
                                   |
                                   v
+-------------------------------------------------------------------+
|                    8. REGISTRO DE CONOCIMIENTO                    |
|                                                                   |
|  Hechos       Mediciones       Derivaciones       Hipotesis        |
|  Evidencias   Contradicciones  Huecos             Pruebas          |
|  Versiones    Historial        Decisiones         Reproduccion     |
|                                                                   |
|  PROVEN / PARTIAL / NOT_DETERMINED / PROVEN_ABSENT / DEFERRED      |
+----------------------------------+--------------------------------+
                                   |
                                   v
+-------------------------------------------------------------------+
|                    9. RESPUESTA PARA LA IA                        |
|                                                                   |
|  Conclusion + evidencia + citas + razonamiento verificable        |
|  Diagrama causal + alternativas + limites + siguiente experimento |
|                                                                   |
|  La IA puede inspeccionar y continuar la investigacion mediante   |
|  consultas estructuradas, sin reconstruir todo desde cero.        |
+-------------------------------------------------------------------+
                                   |
                                   +-------> nueva pregunta o prueba
```

La parte decisiva no es el número de bloques. Es que cada bloque tenga un contrato explícito y que la información viaje entre ellos sin perder procedencia ni grado de certeza.

## 2. Cómo lo usaría yo, como ChatGPT

Imaginemos que abro RXRE sin conocer previamente su implementación interna. Solo sé qué quiero descubrir.

La primera interacción debería parecerse a esto:

```
IA -> RXRE

PREGUNTA:
  Identificar quien escribe VM_CONTEXT0_CNTL,
  bajo que condiciones, y como se aplica el valor.

RXRE -> IA

OBJETO:
  Identificado y versionado.

CONOCIMIENTO PREVIO:
  4 escritores candidatos.
  2 rutas de ejecucion conocidas.
  1 relacion de escritura aun no demostrada.

INCERTIDUMBRES:
  U1: no se sabe si el escritor es alcanzable.
  U2: no se conoce la condicion exacta de ejecucion.
  U3: no se ha demostrado el efecto hardware.

SIGUIENTE ACCION:
  Reconstruir referencias a la escritura y sus
  condiciones de alcance antes de ejecutar nada.
```

Los números son ilustrativos. En un uso real, RXRE tendría que recuperarlos del registro de evidencia, no inventarlos.

A continuación, RXRE debería proponer un plan ejecutable:

```
PLAN DE INVESTIGACION
=====================

P1. Encontrar todas las escrituras candidatas.
    Capacidades: symbols, xrefs, source search, disassembly.

P2. Identificar el flujo de control de cada escritor.
    Capacidades: CFG, basic blocks, decompilation.

P3. Reconstruir el origen del valor.
    Capacidades: dataflow, type analysis, source inspection.

P4. Seguir las condiciones que habilitan la escritura.
    Capacidades: callers, CFG, predicates, path analysis.

P5. Determinar el consumidor del valor.
    Capacidades: register references, MMIO access, call chain.

P6. Determinar que puede afirmarse.
    Capacidades: evidence graph, contradiction checks.

P7. Si queda una duda que el analisis estatico no resuelve,
    disenar una prueba dinamica especifica y reversible.
```

Cada etapa consume los resultados de las anteriores. Si P2 demuestra que una supuesta ruta no puede alcanzarse bajo las condiciones examinadas, P4 no debería seguir tratándola como una ruta activa. Si P5 descubre otro consumidor, el plan se amplía.

Eso es importante: el plan no es una secuencia rígida de comandos, sino una investigación que se adapta a la evidencia sin perder el objetivo original.

## 3. La conexión más importante: un modelo común de evidencia

Si tuviera que elegir una sola pieza arquitectónica para que RXRE funcione de verdad, sería esta: un grafo de evidencia con relaciones tipadas y verificables.

Ghidra puede encontrar una función. Rizin puede encontrar la misma función con otra representación. Coccinelle puede localizar una asignación en el código fuente. Un análisis de flujo de datos puede sugerir de dónde procede el valor. Una traza puede mostrar que la instrucción se ejecutó.

Esos resultados no deberían guardarse como cuatro informes independientes. Deberían relacionarse con el mismo objeto y con la misma pregunta.

Por ejemplo:

```
                       [Pregunta Q-104]
                              |
                              v
               [Afirmacion C-104: escritor de R]
                              |
                  +-----------+-----------+
                  |           |           |
                  v           v           v
             [Evidencia] [Evidencia] [Evidencia]
              fuente      binario     runtime
                  |           |           |
                  v           v           v
              funcion F    offset O    evento E
                  |           |           |
                  +-----------+-----------+
                              |
                              v
                    [Relacion propuesta]
                              |
                  +-----------+-----------+
                  |                       |
                  v                       v
          [Prueba de alcance]     [Prueba de efecto]
                  |                       |
                  v                       v
           [Resultado P1]            [Resultado P2]
                  |                       |
                  +-----------+-----------+
                              |
                              v
                    [Estado de la afirmacion]
                              |
             +----------------+----------------+
             |                |                |
             v                v                v
          PROVEN           PARTIAL       NOT_DETERMINED
```

Una afirmación debería poder responder, como mínimo:

- ¿Qué se afirma exactamente?
- ¿Sobre qué objeto, versión, configuración y condiciones?
- ¿Qué evidencia directa la respalda?
- ¿Qué pasos son inferencias?
- ¿Qué evidencia la contradice?
- ¿Qué prueba podría refutarla?
- ¿Qué falta para elevar su estado de confianza?
- ¿Qué otras conclusiones dependen de ella?

La confianza no debería calcularse sumando herramientas que coinciden. Dos herramientas pueden compartir el mismo motor, la misma base de datos o el mismo error. RXRE necesita registrar la independencia real de las evidencias, no simplemente contar resultados concordantes.

### La unidad fundamental no es el archivo ni la herramienta

Es la afirmación investigable.

```
CLAIM
  id
  statement
  object_id
  scope
  conditions
  status
  evidence_refs[]
  derivation_refs[]
  contradiction_refs[]
  falsification_test
  unresolved_obligations[]
```

Cada evidencia tendría su propio registro, con el resultado bruto preservado, la herramienta y versión utilizadas, los parámetros, el alcance y la localización precisa. Las relaciones del grafo serían objetos explícitos, no frases libres generadas por una IA.

De esa manera, cuando yo vuelva a consultar RXRE, podré pedir «demuéstrame por qué consideras probado este escritor» y el sistema podrá reconstruir la justificación sin depender de la memoria conversacional del modelo.

## 4. Cómo conectaría las herramientas para evitar redundancia y errores

No conectaría todas las herramientas con todas las demás. Eso produciría una red difícil de mantener, llena de adaptadores innecesarios y dependencias circulares.

Las conectaría mediante contratos de capacidades.

```
                       REGISTRO DE CAPACIDADES
                                  |
             +--------------------+--------------------+
             |                    |                    |
             v                    v                    v
       binary.functions      source.search        runtime.trace
             |                    |                    |
             v                    v                    v
       resultados JSON       ubicaciones          eventos ordenados
             |                    |                    |
             +--------------------+--------------------+
                                  |
                                  v
                         MODELO CANONICO
                                  |
                                  v
                          GRAFO DE EVIDENCIA
```

Una capacidad describe qué operación puede realizarse, no qué programa la realiza. Varios backends pueden implementarla, con diferentes limitaciones.

Por ejemplo:

| Capacidad                | Productores posibles                        | Papel en la investigación                              |
| ------------------------ | ------------------------------------------- | ------------------------------------------------------ |
| `binary.functions`       | Rizin, radare2, Ghidra                      | Localizar funciones y sus rangos                       |
| `binary.disassemble`     | Rizin, radare2, Capstone                    | Obtener instrucciones y direcciones                    |
| `binary.cfg`             | Ghidra, Rizin, análisis propio              | Reconstruir flujo de control                           |
| `binary.xrefs`           | Rizin, radare2, Ghidra                      | Encontrar referencias y relaciones                     |
| `source.semantic_search` | Coccinelle, Tree-sitter, otras herramientas | Localizar construcciones y relaciones en fuente        |
| `binary.decompile`       | Ghidra y otros backends compatibles         | Proponer una representación de alto nivel              |
| `runtime.trace`          | Depuradores, instrumentación y trazado      | Observar ejecución bajo condiciones concretas          |
| `formal.check`           | Z3, CBMC, KLEE u otros                      | Resolver o verificar propiedades dentro de sus modelos |

La tabla representa posibles asignaciones, no una garantía de compatibilidad universal.

Cada backend declararía:

```
CAPABILITY: binary.functions
BACKEND: rizin
INPUTS: objeto binario, formato admitido, opciones
OUTPUT: funciones con direcciones y atributos disponibles
LIMITATIONS: formatos, arquitectura, heuristicas
COST: tiempo, memoria, CPU
PROVENANCE: version y parametros
TESTS: fixtures y regresiones conocidas
```

El router podría entonces seleccionar Rizin para una exploración rápida y reservar Ghidra para un análisis más costoso cuando aporte información adicional. Si ambos producen resultados diferentes, la discrepancia se conserva y se convierte en una pregunta de investigación.

La redundancia útil se conserva para contrastar resultados; la redundancia inútil se elimina después de medirla.

## 5. Cómo haría que una IA pueda abrir RXRE y trabajar sin conocer su interior

Este punto es central. Si para utilizar RXRE tengo que leer cientos de scripts, conocer cada comando y recordar qué herramienta genera cada archivo, la integración ha fracasado.

Yo expondría una interfaz pequeña y estable. La IA debería operar mediante preguntas, consultas, planes, ejecución de capacidades y validación de afirmaciones.

Un ejemplo conceptual de sesión:

```
$ rxre

RXRE> project open .
RXRE> object identify ./amdgpu.ko

OBJETO IDENTIFICADO
  Tipo: ELF relocatable (ET_REL)
  Arquitectura: AMDGPU / GFX8, si se confirma
  Hash: ...
  Identidad de build: ...
  Limitaciones: ...

RXRE> ask "Quien escribe VM_CONTEXT0_CNTL?"

RXRE crea:
  Q-001: localizar todas las escrituras
  Q-002: identificar sus condiciones
  Q-003: reconstruir el origen de los valores
  Q-004: identificar consumidores y efectos

RXRE> investigate Q-001

  [1] Inventario de símbolos y secciones
  [2] Búsqueda de referencias y escrituras
  [3] Análisis de instrucciones y flujo de control
  [4] Correlación con fuente, si está disponible
  [5] Normalización y registro de evidencias

  Resultado:
    4 candidatos
    3 relaciones respaldadas
    1 candidato sin clasificación suficiente

RXRE> inspect candidate-4

  El candidato existe.
  Su alcance no está determinado.
  No se afirma que sea ejecutado.

RXRE> continue Q-001

  Se detecta que el objeto es ET_REL.
  La decompilación disponible no produjo funciones.
  Se conserva ese resultado como limitación del backend.
  Se utiliza un analizador alternativo para obtener
  referencias e instrucciones.

RXRE> status Q-001

  Candidatos localizados: 4
  Escritores confirmados: 2
  Candidatos sin resolver: 2
  Estado: PARTIAL

RXRE> next Q-001

  Próxima prueba: distinguir si candidate-3 es una
  escritura efectiva o una referencia no ejecutable.
```

El diálogo anterior es una simulación de cómo debería funcionar, no una transcripción de una ejecución real.

La interfaz real podría ofrecer tres formas complementarias de acceso:

- CLI: para que una IA local ejecute comandos y reciba resultados estructurados.
- API: para que un agente programe consultas, inspeccione evidencia y encadene pruebas.
- MCP: para que ChatGPT u otros modelos compatibles descubran y utilicen las capacidades de RXRE como herramientas.

No duplicaría la lógica de investigación en cada interfaz. Las tres llamarían al mismo núcleo.

### El contrato entre ChatGPT y RXRE

Diseñaría un conjunto reducido de operaciones conceptuales:

```
project.open
object.identify
knowledge.query
claim.inspect
evidence.inspect
capability.discover
investigation.plan
investigation.step
test.run
claim.validate
global_work_scan
report.generate
```

Cada operación tendría entradas tipadas, salidas estructuradas, errores explícitos y límites definidos. Los resultados grandes se consultarían por identificador, no se volcarían íntegramente en el contexto del modelo.

Esto importa porque ChatGPT tiene una ventana de contexto finita. No necesito recibir diez mil líneas de desensamblado si RXRE puede conservarlas y devolverme las veinte instrucciones relevantes, sus direcciones y una referencia al resultado completo.

Tampoco quiero que la IA invente nombres de capacidades. RXRE debería permitir descubrir qué existe, qué está instalado, qué funciona, qué se ha probado y qué limitaciones tiene cada operación.

## 6. El problema del contexto: que la IA no pierda el hilo

Una IA que investiga durante muchas iteraciones necesita algo más que una base de datos de resultados. Necesita un estado de investigación persistente y reconstruible.

Yo separaría cuatro capas:

```
+------------------------------------------------------+
|  A. OBJETIVO                                         |
|     Que pregunta estamos intentando resolver?        |
+------------------------------------------------------+
                         |
                         v
+------------------------------------------------------+
|  B. OBLIGACIONES                                     |
|     Que hechos deben demostrarse para responder?     |
+------------------------------------------------------+
                         |
                         v
+------------------------------------------------------+
|  C. ESTADO DE EVIDENCIA                              |
|     Que esta probado, parcial o sin determinar?      |
+------------------------------------------------------+
                         |
                         v
+------------------------------------------------------+
|  D. FRONTERA DE INVESTIGACION                        |
|     Que prueba puede reducir la incertidumbre?       |
+------------------------------------------------------+
```

Al iniciar una sesión nueva, la IA no debería depender de recordar conversaciones anteriores. RXRE le entregaría un paquete de contexto compacto:

```
INVESTIGATION: Q-104

GOAL:
  Identificar el escritor efectivo del registro R.

PROVEN:
  C-01: existen dos sitios de escritura en el objeto analizado.

PARTIAL:
  C-02: uno de los sitios recibe el valor de una funcion auxiliar.

NOT_DETERMINED:
  C-03: no esta establecida la condicion de ejecucion.
  C-04: no se ha demostrado el efecto sobre el hardware.

CONTRADICTIONS:
  D-01: dos backends difieren en el limite de una funcion.

NEXT DISCRIMINATING TEST:
  Resolver el rango de instrucciones y contrastar las
  referencias con el flujo de control.

CONSTRAINTS:
  No modificar el hardware.
  No descartar resultados anteriores.
  No duplicar trabajo ya ejecutado.
```

Así puedo retomar la investigación sin volver a empezar ni tratar una hipótesis anterior como un hecho.

Además, cada conclusión debería depender de identificadores estables. Si cambia el binario, la versión del kernel, una configuración o una evidencia, RXRE debe detectar qué conclusiones necesitan revisión. No debería declarar automáticamente obsoleta toda la investigación ni considerar vigente toda conclusión previa.

## 7. Cómo lograría la ingeniería inversa quirúrgica

La palabra «quirúrgica» implica precisión de alcance, no solamente profundidad.

Si pregunto quién escribe un registro, RXRE no necesita descompilar todo el kernel, analizar todos los módulos y ejecutar un benchmark de GPU. Necesita localizar las rutas candidatas y realizar el menor conjunto de pruebas que permita responder correctamente.

El ciclo sería:

```
PREGUNTA
   |
   v
DEFINIR EL OBJETO Y LAS CONDICIONES
   |
   v
IDENTIFICAR OBLIGACIONES DE PRUEBA
   |
   v
RECUPERAR EVIDENCIA EXISTENTE
   |
   v
DETECTAR EL HUECO MAS IMPORTANTE
   |
   v
ELEGIR LA PRUEBA DE MAYOR VALOR
   |
   v
VALIDAR PRECONDICIONES Y RIESGOS
   |
   v
EJECUTAR UNA CAPACIDAD
   |
   v
CONSERVAR RESULTADOS BRUTOS
   |
   v
NORMALIZAR Y CONECTAR LA EVIDENCIA
   |
   v
CONTRASTAR HIPOTESIS
   |
   v
ACTUALIZAR EL ESTADO DE LA AFIRMACION
   |
   v
¿LA PREGUNTA ESTA DEMOSTRADA?
   |
   +---- SI ------> RESPUESTA CON EVIDENCIA
   |
   +---- NO ------> GLOBAL WORK SCAN
                         |
                         v
                  SIGUIENTE PRUEBA
```

El criterio para elegir la siguiente prueba no sería simplemente «la herramienta que todavía no usamos». Sería cuánto puede cambiar nuestra comprensión del problema.

Por ejemplo, si una búsqueda de símbolos y dos análisis estáticos ya demuestran que existen tres sitios de escritura, ejecutar otros cuatro descompiladores puede aportar muy poco. En cambio, comprobar una condición de ejecución todavía desconocida puede resolver la cuestión principal.

Y hay una distinción importante: una prueba dinámica solo merece ejecutarse cuando las pruebas estáticas no bastan o cuando la pregunta exige observar un efecto real. En hardware, el plan debe especificar precondiciones, reversibilidad, riesgos, criterios de interrupción y qué observación distinguirá las hipótesis. La existencia de una herramienta capaz de ejecutar algo no es justificación suficiente para hacerlo.

## 8. Cómo decidiría qué herramientas conservar

No conservaría herramientas por su reputación, cantidad de funciones o número de repositorios descargados. Tampoco eliminaría una herramienta porque otra obtiene resultados parecidos en un único ejemplo.

Mediría cada capacidad en tareas concretas:

| Dimensión        | Pregunta                                                                      |
| ---------------- | ----------------------------------------------------------------------------- |
| Cobertura        | ¿Qué preguntas puede resolver que antes no podíamos resolver?                 |
| Precisión        | ¿Produce ubicaciones y relaciones correctas en fixtures conocidos?            |
| Discriminación   | ¿Distingue entre hipótesis que otras herramientas confunden?                  |
| Independencia    | ¿Aporta evidencia nueva o repite el resultado de otro backend?                |
| Reproducibilidad | ¿Podemos repetir el resultado con las mismas entradas y versiones?            |
| Integración      | ¿Sus resultados pueden alimentar las demás capacidades sin pérdida semántica? |
| Coste            | ¿Cuánta CPU, RAM, disco y tiempo consume por evidencia útil?                  |
| Mantenimiento    | ¿Cuánto cuesta mantener el adaptador y sus regresiones?                       |

El resultado no sería una clasificación universal de herramientas buenas y malas. Sería una decisión contextual: conservar, sustituir, limitar a ciertos formatos, usar como contraste o retirar.

En tu máquina, por ejemplo, una capacidad que necesita casi media hora de CPU para analizar un módulo grande no debería ejecutarse automáticamente en cada consulta. Podría utilizarse de forma selectiva, sobre funciones concretas o cuando una pregunta realmente lo requiera.

## 9. El mapa final que yo intentaría construir

Esta es la arquitectura a la que aspiraría. Observa que el grafo de evidencia es el centro de integración; las herramientas son productores y verificadores que se conectan a él.

```
                          +------------------+
                          |    CHATGPT / IA  |
                          | pregunta, plan,  |
                          | hipotesis, juicio|
                          +--------+---------+
                                   |
                           API / MCP / CLI
                                   |
                                   v
                    +-----------------------------+
                    |       RXRE CORE             |
                    |                             |
                    | Identidad y contexto        |
                    | Planificador de pruebas     |
                    | Router de capacidades       |
                    | Control de precondiciones   |
                    | Gestion de recursos         |
                    +--------------+--------------+
                                   |
                +------------------+------------------+
                |                  |                  |
                v                  v                  v
        +---------------+  +---------------+  +---------------+
        | ADAPTERS      |  | ADAPTERS      |  | ADAPTERS      |
        | SOURCE        |  | BINARY        |  | RUNTIME       |
        |               |  |               |  |               |
        | Coccinelle    |  | Ghidra        |  | GDB / LLDB    |
        | Tree-sitter   |  | Rizin         |  | Frida         |
        | Semgrep       |  | radare2       |  | perf / ftrace |
        | LLVM          |  | Capstone      |  | AFL++         |
        +-------+-------+  +-------+-------+  +-------+-------+
                |                  |                  |
                +------------------+------------------+
                                   |
                                   v
                    +-----------------------------+
                    | NORMALIZACION Y PROCEDENCIA |
                    |                             |
                    | Resultados brutos           |
                    | Esquemas tipados            |
                    | Localizaciones              |
                    | Versiones y parametros      |
                    | Errores y limitaciones      |
                    +--------------+--------------+
                                   |
                                   v
                    +-----------------------------+
                    | GRAFO DE EVIDENCIA           |
                    |                             |
                    | Objetos                     |
                    | Afirmaciones                |
                    | Dependencias                |
                    | Transformaciones            |
                    | Contradicciones             |
                    | Pruebas y contraejemplos    |
                    +--------------+--------------+
                                   |
                      +------------+------------+
                      |                         |
                      v                         v
             +------------------+      +------------------+
             | MOTOR DE PRUEBAS |      | MEMORIA DE       |
             |                  |      | INVESTIGACION    |
             | Validacion       |      |                  |
             | Differential     |      | Estado durable   |
             | Fuzzing          |      | Historial        |
             | Solvers          |      | Proveniencia     |
             +--------+---------+      +--------+---------+
                      |                         |
                      +------------+------------+
                                   |
                                   v
                    +-----------------------------+
                    | INFORME PARA LA IA          |
                    |                             |
                    | Respuesta demostrada        |
                    | Evidencias citables         |
                    | Diagrama causal             |
                    | Incertidumbres              |
                    | Proxima prueba              |
                    +-----------------------------+
```

No instalaría todos esos componentes dentro del núcleo ni haría que RXRE dependiera obligatoriamente de ellos. Cada herramienta sería un backend sustituible. El núcleo conservaría los contratos, el contexto, la evidencia, las relaciones y el estado de la investigación.

### Mi conclusión

Si yo tuviera que usar RXRE como ChatGPT para realizar ingeniería inversa quirúrgica, mis prioridades serían estas:

1. Un protocolo de investigación estable para que una IA pueda preguntar, planificar, ejecutar y continuar sin conocer la implementación interna.
2. Un modelo común de evidencia que conecte resultados de herramientas diferentes sin convertir inferencias en hechos.
3. Un grafo causal consultable que permita seguir valores, llamadas, escrituras, transformaciones y efectos.
4. Un motor de pruebas discriminantes que seleccione la siguiente operación según la incertidumbre que puede resolver.
5. Memoria de investigación persistente para retomar el trabajo sin repetirlo ni perder sus límites.
6. Validación y medición de capacidades para conservar solamente las herramientas que aportan valor demostrable.

El principio arquitectónico más importante es que RXRE no debería responder únicamente «qué encontró Ghidra» o «qué dice Rizin». Debería responder: «qué afirmación estamos intentando demostrar, qué cadena de evidencia la respalda, qué parte sigue siendo una inferencia y cuál es el siguiente experimento que permitiría resolverla».

Y hay una condición adicional: el sistema no debe confiar ciegamente en su propio núcleo. El router, los adaptadores, los normalizadores y el registro de evidencia también pueden contener errores. Sus contratos y transformaciones necesitan pruebas, fixtures, detección de mutaciones y trazabilidad. De lo contrario, podríamos construir una plataforma que conecte perfectamente las herramientas y propague con eficiencia una conclusión incorrecta.

Ese sería mi objetivo para RXRE: no una colección de herramientas, sino un entorno de investigación asistida por IA, orientado a afirmaciones, evidencia causal y experimentos reproducibles, que pueda investigar objetos complejos sin perder precisión a medida que crece la investigación.
