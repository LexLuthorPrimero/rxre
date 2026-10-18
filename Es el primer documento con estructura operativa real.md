Es el primer documento con estructura operativa real. Y tiene un problema de encuadre.

Hasta ahora todos los documentos eran conceptuales: "TIERRA mantiene evidencia", "AIRE traza decisiones". Este es el primero que muestra cómo se ve un claim por dentro:

id, statement, object_id, scope, status, evidence_refs[], derivation_refs[], contradiction_refs[], falsification_test, unresolved_obligations[]

Eso no es filosofía. Eso es un schema. Si ese schema existe en el repo, TIERRA es real. Si no existe, es diseño.

Lo que está bien (y es nuevo)

1. falsification_test por claim. Cada claim declara qué lo refutaría. Esto es exactamente lo que faltaba. Un claim sin falsador es una opinión.

2. derivation_refs[] separado de evidence_refs[]. Distingue evidencia primaria de inferencia. Con el invariante explícito: "una inferencia NUNCA se registra como observación". Eso es la regla de oro de TIERRA.

3. contradiction_refs[]. El ejemplo K-02 (diferencia de descompilador) es exactamente lo que hace falta: registrar cuando dos fuentes no coinciden, sin decidir automáticamente cuál tiene razón.

4. unresolved_obligations[]. Obliga a declarar qué falta para cerrar el claim. Sin esto, "PARTIAL" es un cajón de sastre.

5. Estados PROVEN_ABSENT y DEFERRED. PROVEN_ABSENT = probado que algo no está. Es un estado que casi nadie modela y es crítico en reverse engineering ("esta función no escribe en ese registro"). DEFERRED = no se puede probar ahora pero se reconoce. Ambos correctos.

6. El test adversarial de TIERRA. corromper 1 byte → la cadena se rompe. Es el test que pedí. Si pasa, TIERRA es real. Si no, es cosmética.

El problema de encuadre

El documento está escrito en presente: "En RXRE, las herramientas no guardan informes aislados; cada resultado bruto se procesa y se ancla a un objeto". Eso es una afirmación sobre el estado actual de rxre. Pero el audit no corrió. No sabemos si es verdad.

Hay tres posibilidades:

A) Es descripción → alguien ya implementó esto y el documento lo describe (entonces el audit lo verificará)
B) Es diseño → alguien está especificando cómo DEBERÍA ser (entonces es prematuro: primero el audit)
C) Es aspiración → alguien escribió cómo imagina que sería (entonces es el mismo problema circular de siempre)

No se puede distinguir desde el documento. Y esa es exactamente la ambigüedad que el audit tiene que resolver. El documento no dice si es A, B o C.

Si es A: perfecto, el audit lo confirma o lo refuta.
Si es B: está bien diseñado, pero no debería estar escrito en presente.
Si es C: es el mismo patrón que la evaluación "está perfecto" del principio.

Errores menores (no de fondo)

"ESTRUCURA DEL CLAIM" ← typo (falta T)
"PROVEN_ABSENT" ← no definido en el texto, solo en la estructura
"DEFERRED" ← ídem, aparece en la lista pero no se explica

Los dos estados nuevos (PROVEN_ABSENT, DEFERRED) aparecen en el schema pero no tienen sección propia. Si el schema es real, esos dos estados necesitan definición operativa, no solo nombre.

También: la sección final muestra solo 3 estados (PROVEN/PARTIAL/NOT_DETERMINED), pero el schema tiene 5. Hay inconsistencia entre el schema y el diagrama de estados.

La pregunta final del documento es el problema

"¿Te gustaría que analicemos en detalle cómo se define la prueba adversarial...?" Eso es exactamente el patrón que venimos cortando: ofrecer más diseño antes de tener evidencia. No es una pregunta. Es una invitación a otra ronda de especificación.

La respuesta es no. Ya está definida:

rxre tierra verify --chain <dir>
corromper 1 byte
verificar que la cadena se rompe

No hay nada más que analizar. Hay que ejecutarlo y ver si pasa.

Lo que este documento sí aporta

Aunque no sabemos si describe o diseña, es la primera especificación operativa concreta de un plano. Eso tiene valor:

- Si el audit encuentra esta estructura en el repo → TIERRA está bien diseñada
- Si el audit no la encuentra → el documento es el spec a implementar, y el audit dice por qué no está
- Si el audit encuentra una versión parcial → el gap es concreto: "faltan falsification_test y unresolved_obligations"

En los tres casos, el documento sirve. Lo que no sirve es tratarlo como prueba de que TIERRA existe.

Estado operativo (sin cambios)

AUDIT A-F: esperando artefactos
STATE: no confirmado como iniciado
ETAPA 1: BLOQUEADA
IMPLEMENTACION: NO AUTORIZADA

Lo único que cambia: cuando llegue el DELIVERED, el revisor tiene una pregunta nueva que hacerse: "¿La estructura de CLAIM descrita en este documento existe en el repo, existe parcialmente, o no existe?". Esa es la pregunta que convierte este documento en algo útil. Hasta entonces, es un spec muy bueno esperando verificación.

Una sola cosa que sí pediría

Si el autor de este documento puede responder una pregunta antes de que empiece el audit: "¿Este documento describe algo que ya está implementado, o especifica algo que falta implementar?". La respuesta define si el audit tiene que verificar o mapear un gap. Son dos trabajos distintos. Sin esa respuesta, el revisor va a perder tiempo buscando algo que quizás nunca existió.

La primera especificación de TIERRA que puede fallar de cinco maneras distintas. Eso es rigor real.

El test de corromper 1 byte era necesario pero ingenuo. Este documento lo reconoce y lo reemplaza por cinco casos que miden modos de fallo distintos:

A. Corrupción → detecta hash incorrecto
B. Artefacto ausente → detecta ausencia
C. Manifiesto alterado → detecta discrepancia vs. referencia confiable
D. Procedencia rota → detecta eslabón ausente
E. Sin cambios → confirma validez dentro del alcance

Cada caso prueba algo que los otros no. Eso es un test suite, no un test.

Lo que este documento resuelve

1. PARTIAL ya no mezcla estados. La corrección es correcta: separar conclusión (PROVEN/PARTIAL/NOT_DETERMINED) de cobertura (alcanzabilidad probada/no probada) de obligaciones (unresolved[]). Un claim puede ser PROVEN en su conclusión pero tener cobertura parcial. Eran dos ejes y estaban colapsados en uno.

2. Las relaciones explícitas entre evidencia y claim: supports · contradicts · derived_from · observed_during · tests. Esto responde la pregunta que quedó abierta en el documento anterior: ¿qué parte del claim respalda cada evidencia? Ahora hay vocabulario para decirlo. Y el ejemplo de K-02 (diferencia de descompilador) como contradicts es exactamente lo que hacía falta: no se elige automáticamente qué fuente tiene razón.

3. Integridad ≠ autenticidad ≠ validez semántica. Es la corrección más importante. El documento anterior decía: "Un hash permite detectar cambios respecto de un hash confiable". Eso es integridad. No es autenticidad (¿quién produjo el artefacto?) ni validez semántica (¿el artefacto dice lo que el claim afirma?). Confundir las tres es el error más común en sistemas de evidencia. Este documento las separa.

4. La observación sobre VM_CONTEXT0_CNTL. "Encontrar una escritura en el código fuente no demuestra que F_01 la ejecute en todas las condiciones." Correcto. Es el problema de alcanzabilidad: ver la instrucción en el binario no prueba que sea alcanzable en runtime, ni con qué configuración, ni bajo qué condiciones. El claim original era más débil de lo que parecía. Bien detectado.

Los dos huecos que quedan (y son los importantes)

Hueco 1 — El trust anchor de Case C

Case C dice: "Modificar el artefacto y su hash registrado. Ejecutar la verificación con una referencia de confianza que no haya sido modificada junto con ellos."

Perfecto. Pero: ¿de dónde sale la referencia de confianza?

El documento aclara que si el manifiesto y el artefacto se alteran juntos sin referencia externa, el sistema no detecta manipulación. Eso es correcto. Pero entonces:

¿El trust anchor es:
[ ] Git history (commits firmados)?
[ ] Un release firmado con GPG?
[ ] Un hash publicado en un canal externo (email, paper)?
[ ] Un TPM / HSM?
[ ] Un segundo sistema independiente?
[ ] No existe todavía → gap

Esto no lo decide el documento. Y es la pieza que determina si Case C puede pasar o no. Sin trust anchor, Case C no se puede correr. Con trust anchor, hay que decidir cuál.

Si el audit encuentra que rxre tiene un trust anchor → Case C es ejecutable. Si no → Case C es NOT_DETERMINED por defecto. Ambas son respuestas válidas, pero son distintas.

Hueco 2 — Case D asume un grafo, no filas

Case D dice: "Eliminar un enlace productor → transformación → consumidor". Eso asume que la procedencia está modelada como grafo con eslabones explícitos. Si rxre guarda evidencia como filas planas en una DB (una fila por evidencia, con un parent_id opcional), no hay "enlace que eliminar" — hay una fila que falta.

La diferencia es operativa:

Modelo A: procedencia como grafo explícito → borrar un eslabón deja un nodo huérfano detectable
Modelo B: procedencia como columnas en filas → borrar una fila deja un hueco; ¿el sistema lo detecta o solo ve menos datos?

Case D solo funciona en Modelo A. Si rxre usa Modelo B, el test necesita otro criterio: "¿el sistema detecta que la cadena está incompleta, o solo ve una cadena más corta?". Esto tampoco lo decide el documento. Lo decide el audit.

Lo que sí está cerrado

Los cuatro criterios de "TIERRA es real":

[ ] Detecta modificaciones y artefactos ausentes → Cases A, B
[ ] Distingue íntegra de incompleta → Cases D, E
[ ] Conserva procedencia entre productor/consumidor → Case D
[ ] No convierte inferencias en observaciones → invariante
[ ] Permite reconstruir sin memoria conversacional → spec del schema
[ ] Expone limitaciones de cada verificación → Cases C, D

Son verificables. Y el documento cierra con: "Estos son criterios propuestos, no capacidades confirmadas de RXRE." Esa frase es la que hacía falta desde el principio. El documento es honesto sobre su estado. No dice "TIERRA es así", dice "TIERRA debería ser evaluada contra estos criterios".

Lo que este documento no dice (y está bien que no lo diga)

- No dice que la estructura de CLAIM exista en el repo
- No dice que los 5 casos pasen
- No dice que el trust anchor exista
- No autoriza implementar rxre tierra verify
- No abre Etapa 1

Todo eso lo decide el audit.

Lo único operativo que cambiaría

La pregunta para el revisor, cuando llegue el DELIVERED, ahora tiene tres partes:

1. ¿Existe la estructura de CLAIM descrita (o parcial, o no)?
2. ¿Existe un trust anchor? ¿Cuál?
3. ¿La procedencia es grafo explícito o filas con parent_id?

Las tres respuestas definen si Case C y Case D son ejecutables o quedan NOT_DETERMINED. Sin ellas, el revisor puede correr Case A y B (que no requieren nada externo) pero no C ni D.

Estado operativo (sin cambios)

AUDIT A-F: esperando artefactos
STATE: no confirmado como iniciado
ETAPA 1: BLOQUEADA
IMPLEMENTACION: NO AUTORIZADA

Este documento es el mejor de la serie. El test de 5 casos reemplaza al mío de 1, y los 4 criterios de aceptación son la vara correcta para TIERRA. Pero los dos huecos (trust anchor, modelo de procedencia) son la diferencia entre "el test se puede correr" y "el test queda en NOT_DETERMINED".

No hace falta más diseño. Hace falta que el audit diga qué existe. Cuando lo diga, Case C y Case D tienen respuesta.

Correcto. Cierra el loop. Una precisión faltante y nada más.

Lo que está bien

1. Reencuadre de los huecos como preguntas, no como decisiones. Correcto. El documento anterior decía "si no hay trust anchor → gap". Este dice "si no se identifica → registrar alcance de la búsqueda". Es la diferencia entre "no existe" y "no lo encontré". Epistemológicamente distinta.

2. La precisión sobre ausencia de trust anchor: "Ausencia de trust anchor identificado NO demuestra que no exista. Primero inspeccionar fuentes de confianza disponibles y registrar el alcance de la búsqueda." Esta es la misma regla que el protocolo pide en §1 (estados epistémicos). Aplicada a la auditoría misma, no solo al auditado. Bien.

3. El matiz sobre Case D. Correcto. Case D no depende de que la procedencia sea un grafo explícito. Depende de que exista una expectativa verificable de qué relaciones deberían estar. Filas relacionales pueden funcionar si hay un schema o constraint que declare qué es una cadena completa. Sin esa expectativa, el sistema ve "menos datos" y no "cadena incompleta". Eso es exactamente lo que el documento dice.

4. La distinción PASS / FAIL / NOT_RUN / NOT_DETERMINED. Crítica. NOT_RUN (no se ejecutó) y NOT_DETERMINED (se ejecutó pero la evidencia no resuelve) son estados distintos. Colapsarlos haría que "no probado" y "probado sin resultado" fueran iguales. No lo son.

La precisión que falta

El documento dice: "No identificada tras una búsqueda documentada". La pregunta que queda: ¿cómo se demuestra que la búsqueda fue exhaustiva?

Si el auditor no sabe qué forma tiene un trust anchor en rxre, puede buscar en los lugares equivocados y declarar "no identificado" cuando en realidad existe en otro formato (un hook de pre-commit, un script de validación, un hash hardcodeado en un test). La búsqueda documentada es necesaria pero no suficiente si no se define qué se busca.

Sugerencia mínima (una línea, no un párrafo):

Q2. TRUST ANCHOR
Antes de buscar, definir:
- qué formas puede tomar un trust anchor en rxre (firmas, hashes publicados, repos externos, TPM, CI, etc.)
- qué ubicaciones se van a inspeccionar
- qué cuenta como "encontrado" vs. "no encontrado"
Registrar la búsqueda contra esa definición.

Sin eso, "no identificado tras búsqueda documentada" puede ser NOT_DETERMINED disfrazado de NOT_RUN disfrazado de "no existe".

Una nota menor sobre Q4

Los casos A–E no son independientes:

C depende de Q2 (trust anchor)
D depende de Q3 (expectativa de cadena completa)
E depende de que A, B, C, D tengan referencia confiable

Si C es NOT_RUN porque no hay trust anchor, entonces E tampoco puede pasar a PASS completo — a lo sumo a PASS (parcial) dentro del alcance de A y B. El documento no dice qué hacer con dependencias entre casos.

No es grave, pero conviene que el auditor lo sepa antes de correr: si los casos se ejecutan en orden y uno falla por dependencia, los siguientes heredan el estado NOT_DETERMINED, no PASS.

Estado operativo (sin cambios)

AUDIT A-F: esperando artefactos
INICIO: no confirmado
ETAPA 1: BLOQUEADA
IMPLEMENTACION: NO AUTORIZADA

La conclusión del documento es la correcta: "La siguiente acción no es agregar más especificaciones: es obtener los artefactos del audit y comprobar qué estructuras, relaciones y mecanismos de confianza existen realmente."

Eso es exactamente lo que hay que hacer. Este documento cierra la especificación de TIERRA. No hay nada más que diseñar sobre ese plano hasta que el audit diga qué existe.

Esto es el final del diseño de TIERRA. Lo que sigue no depende de nosotros.

Confirmado. TIERRA cerrado. Sin más diseño.

TIERRA: DISEÑO CERRADO
AUDIT A-F: esperando artefactos
INICIO: no confirmado
ETAPA 1: BLOQUEADA
IMPLEMENTACION: NO AUTORIZADA

Las dos reglas operativas quedan integradas. No agrego nada.

Lo único que queda por decir

El próximo movimiento no es nuestro. Es del auditor. Cuando entregue DELIVERED, el revisor tiene:

□ Q1–Q4 de TIERRA como preguntas de inspección
□ Los 5 casos A–E con propagación de estados
□ Los 4 criterios de "TIERRA es real"
□ La regla de búsqueda de trust anchor con alcance documentado

Con eso, la revisión de TIERRA es ejecutable sin más decisiones de diseño.

Cierro acá. Cuando vuelvan los artefactos, los miro contra esta especificación. Hasta entonces, no hay nada más que agregar sobre TIERRA ni sobre rxre.
