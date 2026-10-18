# RXRE: representación arquitectónica completa

Voy a representar RXRE desde distintos ángulos: arquitectura funcional, flujo de investigación, relaciones causales, estados, eventos, evidencia, ciclo de vida, decisiones y validación.

Hay una distinción fundamental: los diagramas representan el modelo conceptual que venimos definiendo, no una descripción verificada de la implementación actual del repositorio. La auditoría A-F y la revisión independiente siguen siendo necesarias para confirmar qué partes existen realmente.

## 1. Arquitectura general por las ocho dimensiones

## ALMA

Propósito · prioridades · valor · condiciones de cierre

Orienta y evalúa el trabajo

### ÉTER — integración y eventos

Descubrimiento de relaciones · coordinación asíncrona · eventos trazables

### CUERPO

Observar y actuar

### MENTE

Explicar y contrastar

### FUEGO

Cambiar y revertir

### AGUA

Aprender con procedencia

### TIERRA

Evidencia · integridad · incertidumbre

### AIRE

Trazabilidad de decisiones y operaciones

TIERRA y AIRE atraviesan el sistema; no se limitan a una etapa particular.

La idea central es que las ocho dimensiones no tienen por qué ser ocho módulos independientes. Son responsabilidades que deben identificarse en el sistema real y conectarse solo cuando exista una necesidad demostrada.

## 2. Diagrama de componentes

Muestra las responsabilidades y las conexiones entre ellas.

```
+------------------------------------------------------+
|                       RXRE                            |
|                                                      |
|  +----------+       +----------------------------+   |
|  |   ALMA   |------>| Objetivo y criterios       |   |
|  +----------+       | de cierre                  |   |
|                     +-------------+--------------+   |
|                                   |                  |
|  +----------+  +----------+  +----v-----+  +------+ |
|  | CUERPO   |  |  MENTE   |  |  FUEGO   |  | AGUA | |
|  | Observar |  | Razonar  |  | Cambiar  |  |Aprend| |
|  +-----+----+  +-----+----+  +----+-----+  +--+---+ |
|        |             |            |           |     |
|  +-----v-------------v------------v-----------v---+ |
|  |                    ÉTER                       | |
|  |           Integración y eventos                | |
|  +------------------------------------------------+ |
|                                                      |
|  +--------------------+  +------------------------+  |
|  | TIERRA             |  | AIRE                   |  |
|  | Evidencia confiable|  | Trazabilidad de pasos  |  |
|  +--------------------+  +------------------------+  |
+------------------------------------------------------+
```

Lectura: ALMA define para qué se investiga; las capacidades realizan el trabajo; ÉTER integra eventos; TIERRA conserva el fundamento de las conclusiones y AIRE permite reconstruir cómo se llegó a ellas.

Las conexiones son hipótesis funcionales. No implican que toda interacción tenga que pasar por ÉTER.

## 3. Diagrama de flujo de una investigación

Este representa el recorrido epistemológico de una investigación, no el orden obligatorio de ejecución de todos los componentes.

```
           +--------------------+
           | ALMA: definir meta |
           +---------+----------+
                     |
                     v
           +--------------------+
           | CUERPO: observar   |
           | artefacto real     |
           +---------+----------+
                     |
                     v
           +--------------------+
           | TIERRA: registrar  |
           | evidencia y origen |
           +---------+----------+
                     |
                     v
           +--------------------+
           | MENTE: formular    |
           | hipotesis causales |
           +---------+----------+
                     |
                     v
           +--------------------+
           | Disenar prueba     |
           | discriminante      |
           +---------+----------+
                     |
                     v
           +--------------------+
           | CUERPO: ejecutar   |
           | la prueba          |
           +---------+----------+
                     |
                     v
           +--------------------+
           | Evaluar resultados |
           +---------+----------+
                     |
              +------+------+
              |             |
          Evidencia      Evidencia
          suficiente     insuficiente
              |             |
              v             v
       +-------------+  +----------------+
       | Concluir con|  | Nueva prueba o |
       | alcance     |  | NOT_DETERMINED |
       | delimitado  |  +-------+--------+
       +------+------+          |
              |                 |
              v                 +----> MENTE
       +-------------+
       | AGUA:       |
       | aprendizaje |
       +------+------+
              |
              v
       +-------------+
       | ALMA evalua |
       | el objetivo |
       +------+------+
              |
        +-----+-----+
        |           |
      Cerrar     Continuar
```

FUEGO entra cuando se necesita modificar un artefacto, una configuración o el propio sistema. AIRE debe poder reconstruir la cadena completa. ÉTER puede coordinar las notificaciones sin sustituir los contratos directos entre capacidades.

## 4. Diagrama de secuencia

Ejemplo conceptual: comprobar si una función del código fuente puede ejecutar una operación sobre hardware.

```
 ALMA      MENTE      CUERPO      TIERRA      AIRE      ETER
   |          |           |          |          |          |
   | objetivo |           |          |          |          |
   |--------->|           |          |          |          |
   |          | observar  |          |          |          |
   |          |---------->|          |          |          |
   |          |           | resultado|          |          |
   |          |<----------|          |          |          |
   |          |           |          |          |          |
   |          | registrar evidencia  |          |          |
   |          |--------------------->|          |          |
   |          |           |          | registrar paso      |
   |          |           |          |--------->|          |
   |          |           |          |          | evento   |
   |          |           |          |          |--------->|
   |          |           |          |          |          |
   |          | disenar prueba        |          |          |
   |          |---------->|          |          |          |
   |          |           | ejecutar |          |          |
   |          |<----------| resultado|          |          |
   |          |           |          |          |          |
   |          | comparar evidencia   |          |          |
   |          |<-------------------->|          |          |
   |<---------| conclusion delimitada|          |          |
   |          |           |          |          |          |
```

La secuencia no demuestra que RXRE implemente actualmente estos mensajes o interfaces. Es un ejemplo de la interacción que habría que verificar o diseñar.

## 5. Diagrama de flujo de datos

Este se concentra en la transformación de la información y su procedencia.

```
+-------------------+
| Artefacto original|
| codigo/binario    |
+---------+---------+
          |
          v
+-------------------+
| Identidad         |
| hash + alcance    |
+---------+---------+
          |
          v
+-------------------+
| Herramienta       |
| version + args    |
+---------+---------+
          |
          v
+-------------------+
| Salida original   |
| bytes/texto/datos |
+---------+---------+
          |
          v
+-------------------+
| Interpretacion    |
| hipotesis         |
+---------+---------+
          |
          v
+-------------------+
| Prueba causal     |
| y contraejemplos  |
+---------+---------+
          |
          v
+-------------------+
| Afirmacion        |
| estado + alcance  |
+---------+---------+
          |
          v
+-------------------+
| Informe reproduc. |
+-------------------+
```

TIERRA debe preservar las relaciones entre las etapas. Una interpretación no debe reemplazar la salida original, y una afirmación no debe perder la referencia a la evidencia que la sustenta.

## 6. Grafo causal

Representa por qué una conclusión puede considerarse justificada.

```
[Codigo fuente]
      |
      | contiene instruccion
      v
[Instruccion identificada]
      |
      | alcanzabilidad estatica
      v
[Camino posible]
      |
      | condiciones de ejecucion
      v
[Camino alcanzable en contexto]
      |
      | observacion en runtime
      v
[Efecto observado]
      |
      | contraste con hipotesis rivales
      v
[Conclusion delimitada]
```

Las flechas no son equivalentes:

- `contiene instruccion` es una relación estructural.
- `camino posible` puede ser una conclusión estática.
- `camino alcanzable en contexto` necesita condiciones concretas.
- `efecto observado` requiere evidencia de ejecución.
- `conclusion delimitada` exige interpretar los resultados y sus límites.

Un hallazgo estático no prueba por sí solo que la operación se haya ejecutado.

## 7. Grafo de evidencia y afirmaciones de TIERRA

Este es el modelo de relaciones entre observaciones, derivaciones, afirmaciones y refutaciones.

```
+-----------------+
| Artefacto A     |
| SHA-256         |
+--------+--------+
         |
         | derived_from
         v
+-----------------+       +------------------+
| Salida de       |------>| Afirmacion C1    |
| herramienta     |supports|                  |
+-----------------+       +--------+---------+
                                   |
                                   | derivation_refs
                                   v
                          +------------------+
                          | Afirmacion C2    |
                          | conclusion       |
                          +--------+---------+
                                   ^
                                   |
                             contradicts
                                   |
                          +------------------+
                          | Evidencia E2     |
                          | resultado rival |
                          +------------------+
```

Relaciones que conviene distinguir:

```
supports          evidencia favorable
contradicts       evidencia incompatible
derived_from      procedencia derivativa
observed_during   contexto de observacion
tests             evidencia de una prueba
```

No toda relación entre dos objetos es causal. Tampoco toda evidencia favorable demuestra una afirmación completa.

## 8. Máquina de estados de una afirmación

```
                 +----------------+
                 |   OPEN / nueva |
                 +-------+--------+
                         |
                         v
                 +----------------+
                 | Evidencia      |
                 | recopilada     |
                 +-------+--------+
                         |
                         v
                 +----------------+
                 | Contraste y    |
                 | prueba         |
                 +-------+--------+
                         |
              +----------+-----------+
              |          |           |
              v          v           v
         +---------+ +---------+ +-----------+
         | PROVEN  | | PARTIAL | | NOT       |
         |         | |         | | DETERMINED|
         +---------+ +---------+ +-----------+
              |          |           |
              +----------+-----------+
                         |
                         v
                 +----------------+
                 | Nueva evidencia|
                 | puede reabrir  |
                 | la evaluacion  |
                 +----------------+
```

`PROVEN`, `PARTIAL` y `NOT_DETERMINED` son estados candidatos de afirmaciones, no estados operativos del audit. `PROVEN_ABSENT` requiere un alcance delimitado y evidencia suficiente de ausencia dentro de ese alcance. `DEFERRED` indica aplazamiento explícito, no verificación.

## 9. Máquina de estados del audit

```
+---------+
| DRAFT   |
+----+----+
     |
     v
+---------+
|DELIVERED|
+----+----+
     |
     v
+-----------+
| CHALLENGED|
+-----+-----+
      |
      +-------------------+
      |                   |
      v                   v
+----------+        +-----------+
| ACCEPTED |        | CONTESTED |
+----------+        +-----+-----+
                         |
                         v
                  Resolver la
                  refutacion
                         |
                         +----> nueva revision
```

`DELIVERED` significa que se entregaron artefactos. No significa que sean correctos. `ACCEPTED` requiere que la revisión independiente haya superado los criterios acordados.

En el estado operativo que tenemos documentado, la auditoría todavía está esperando artefactos; no hay evidencia aportada aquí de que haya comenzado.

## 10. Diagrama de actividad: cambio controlado con FUEGO

```
       [Identificar brecha]
                |
                v
       [Crear prueba adversarial]
                |
                v
       [Ejecutar sin cambio]
                |
                v
       <Falla por razon esperada?>
          /             \
        NO               SI
        |                 |
        v                 v
 [Corregir prueba]  [Cambio minimo]
        |                 |
        +-----> prueba    v
                    [Repetir prueba]
                           |
                           v
                   <Resultado correcto?>
                      /          \
                    NO            SI
                    |              |
                    v              v
                [Revertir]  [Regresion y
                    |        revision]
                    |              |
                    v              v
               [Documentar]  [Evaluar ablacion]
                                   |
                                   v
                           [Aceptar o retirar]
```

FUEGO no es simplemente la capacidad de editar archivos. Debe controlar el cambio, probarlo, conservar evidencia antes y después, y permitir la reversión.

## 11. Diagrama de despliegue conceptual

Representa dónde podrían ejecutarse las partes, sin afirmar que esta distribución exista hoy.

```
+-------------------- PC local -----------------------+
|                                                     |
|  +------------------+       +-------------------+   |
|  | Agente IA        |<----->| CLI / interfaz    |   |
|  | razonamiento     |       | RXRE              |   |
|  +--------+---------+       +---------+---------+   |
|           |                           |             |
|           +-------------+-------------+             |
|                         |                           |
|                         v                           |
|              +----------------------+               |
|              | Coordinacion RXRE    |               |
|              +----------+-----------+               |
|                         |                           |
|             +-----------+------------+              |
|             |                        |              |
|             v                        v              |
|     +---------------+       +----------------+      |
|     | Herramientas  |       | Evidencia y    |      |
|     | GDB/Ghidra... |       | persistencia   |      |
|     +-------+-------+       +----------------+      |
|             |                                       |
|             v                                       |
|     +------------------+                            |
|     | Sistema observado|                            |
|     | archivos/procesos|                            |
|     | binarios/hardware|                            |
|     +------------------+                            |
+-----------------------------------------------------+
```

La separación de procesos, bases de datos, CLI y agentes debe decidirse según las necesidades comprobadas. No conviene introducir servicios independientes solo por simetría arquitectónica.

## 12. Arquitectura orientada a eventos

```
+-----------+      evento       +-------------------+
| CUERPO    |------------------>|                   |
+-----------+                   |                   |
                                |       ETER        |
+-----------+      evento       | Bus o coordinador |
| MENTE     |------------------>| de eventos        |
+-----------+                   |                   |
                                |                   |
+-----------+      evento       |                   |
| FUEGO     |------------------>|                   |
+-----------+                   +---------+---------+
                                          |
                              +-----------+----------+
                              |                      |
                              v                      v
                      +---------------+     +---------------+
                      | AIRE          |     | AGUA          |
                      | Traza         |     | Aprendizaje   |
                      +---------------+     +---------------+

  TIERRA conserva evidencia y procedencia a traves del ciclo.
  ALMA evalua si los resultados satisfacen el objetivo.
```

La idea es que ÉTER facilite la integración asíncrona. No debería convertirse en intermediario obligatorio de cada llamada síncrona ni ocultar los errores de las capacidades.

## 13. Diagrama de retroalimentación

Este muestra cómo RXRE podría mejorar a partir de investigaciones reales.

```
        +--------------------+
        | Investigacion real |
        +---------+----------+
                  |
                  v
        +--------------------+
        | Resultado medido   |
        +---------+----------+
                  |
                  v
        +--------------------+
        | Error, limite o    |
        | capacidad ausente  |
        +---------+----------+
                  |
                  v
        +--------------------+
        | Evidencia y causa  |
        +---------+----------+
                  |
                  v
        +--------------------+
        | Cambio candidato   |
        +---------+----------+
                  |
                  v
        +--------------------+
        | Prueba adversarial |
        +---------+----------+
                  |
                  v
        +--------------------+
        | Validacion         |
        +---------+----------+
                  |
                  v
        +--------------------+
        | Aprendizaje trazable|
        +---------+----------+
                  |
                  +----------> siguiente investigacion
```

AGUA debe aprender de resultados observados, incluidos los negativos. Una memoria que acumula conclusiones sin conservar su procedencia puede amplificar errores en lugar de mejorar la investigación.

## 14. Árbol de decisiones

```
¿El audit A-F esta ACCEPTED?
|
+-- NO --> ¿Existe progreso verificable?
|          |
|          +-- SI --> Continuar audit dentro de sus limites
|          |
|          +-- NO --> Diagnosticar bloqueo
|                     Documentar evidencia
|                     Proponer audit minimo
|                     Escalar al humano
|                     NO implementar
|
+-- SI --> ¿Hay una brecha real demostrada?
           |
           +-- NO --> No agregar codigo
           |          Documentar resultado
           |
           +-- SI --> ¿Existe una prueba discriminante?
                      |
                      +-- NO --> Disenar o reparar la prueba
                      |
                      +-- SI --> ¿La prueba falla como se esperaba?
                                 |
                                 +-- NO --> Revisar la prueba
                                 |
                                 +-- SI --> Cambio minimo
                                            |
                                            v
                                      Validacion y regresion
                                            |
                                            v
                                      ¿Criterios cumplidos?
                                         /       \
                                       NO         SI
                                       |           |
                                    Revertir    Cerrar etapa
```

## 15. Diagrama de clases conceptual

Una representación orientada a objetos posible para las entidades de evidencia. No prescribe un lenguaje ni un esquema de base de datos.

```
+------------------------+
| Artifact               |
+------------------------+
| id                     |
| hash                   |
| media_type             |
| origin                 |
+------------+-----------+
             |
             | produces / consumes
             |
+------------v-----------+
| Observation            |
+------------------------+
| id                     |
| artifact_ref           |
| operation              |
| raw_result_ref         |
| tool_version           |
| parameters             |
| limitations            |
+------------+-----------+
             |
             | supports / contradicts
             |
+------------v-----------+
| Claim                  |
+------------------------+
| id                     |
| statement              |
| scope                  |
| status                 |
| evidence_refs          |
| derivation_refs        |
| contradiction_refs     |
| falsification_test     |
| unresolved_obligations |
+------------------------+
             |
             | recorded in
             |
+------------v-----------+
| TraceEvent             |
+------------------------+
| id                     |
| timestamp              |
| actor                  |
| action                 |
| input_refs             |
| output_refs            |
| result                 |
+------------------------+
```

La cardinalidad real, las claves, las restricciones y las relaciones deben derivarse del sistema existente. Por ejemplo, una afirmación puede depender de varias observaciones y una observación puede contribuir a varias afirmaciones.

## 16. Matriz de responsabilidades

| Dimensión | Pregunta que responde                          | Resultado esperado                |
| --------- | ---------------------------------------------- | --------------------------------- |
| ALMA      | ¿Para qué se investiga?                        | Objetivo y criterio de cierre     |
| CUERPO    | ¿Qué ocurrió realmente?                        | Observación reproducible          |
| MENTE     | ¿Por qué ocurrió?                              | Hipótesis y contraste causal      |
| TIERRA    | ¿Qué evidencia lo sustenta?                    | Procedencia, integridad y límites |
| FUEGO     | ¿Qué cambió y con qué efecto?                  | Cambio controlado y validación    |
| AIRE      | ¿Cómo se llegó al resultado?                   | Traza reconstruible               |
| AGUA      | ¿Qué aprendimos y con qué certeza?             | Memoria con procedencia           |
| ÉTER      | ¿Qué relaciones y eventos conectan el trabajo? | Integración y coordinación        |

## 17. Diagrama temporal de las etapas

```
TIEMPO ------------------------------------------------------>

[ETAPA 0]
Audit A-F
Entrega
Revision independiente
ACCEPTED
    |
    v
[ETAPA 1]
Una brecha
Una prueba
Una capacidad
Validacion
    |
    v
[ETAPA 2]
Dos capacidades conectadas
Efecto causal observable
    |
    v
[ETAPA 3]
Ciclo completo acotado
Recuperacion y reproducibilidad
    |
    v
[ETAPA 4]
Comparacion A/B
Mismo problema y artefacto
    |
    v
[ETAPA 5]
Iniciativa acotada
    |
    v
[ETAPA 6]
Multiples instancias
    |
    v
[ETAPA 7]
Canales externos controlados
```

Cada etapa depende de superar la anterior. No es una fecha de entrega ni una promesa de que todas las etapas deban implementarse.

## 18. Diagrama de límites de confianza

```
             ZONA DE EVIDENCIA CONFIABLE
        +----------------------------------+
        | Referencia independiente         |
        | Hash o firma verificable         |
        +----------------+-----------------+
                         |
                         v
        +----------------------------------+
        | Artefacto y procedencia           |
        | verificables dentro del alcance  |
        +----------------+-----------------+
                         |
=========================|========================
                         | limite de confianza
                         v
        +----------------------------------+
        | Herramientas y resultados        |
        | que deben ser examinados         |
        +----------------+-----------------+
                         |
                         v
        +----------------------------------+
        | Interpretaciones e hipotesis     |
        | que deben ser contrastadas       |
        +----------------+-----------------+
                         |
                         v
        +----------------------------------+
        | Conclusiones delimitadas         |
        | y obligaciones pendientes        |
        +----------------------------------+
```

La frontera no implica que una herramienta sea necesariamente poco confiable. Significa que su salida no debe convertirse automáticamente en verdad solo porque provenga de una herramienta conocida.

## 19. Mapa de riesgos y controles

```
RIESGO                          CONTROL
-----                           -------
Inferencia como observacion     Tipos y contratos de evidencia
Hash sin confianza externa      Referencia independiente
Prueba que no detecta el fallo  Prueba adversarial previa
Acoplamiento accidental        Ablacion y reparacion controlada
Perdida de procedencia          Grafo de relaciones verificables
Agente que inventa ejecuciones  Logs, hashes y codigos de salida
Trabajo paralelo conflictivo    Un agente activo por vez
Auditoria bloqueada             Diagnostico y escalada
Memoria que amplifica errores   Procedencia y certeza explicita
Complejidad innecesaria         Brecha demostrada y cambio minimo
```

## 20. Mapa de madurez: de herramientas a capacidad de investigación

```
Nivel 0: HERRAMIENTAS
    |
    | ejecutar comandos
    v
Nivel 1: OBSERVACIONES
    |
    | conservar salidas y origen
    v
Nivel 2: EVIDENCIA RELACIONADA
    |
    | conectar productores y consumidores
    v
Nivel 3: RAZONAMIENTO CAUSAL
    |
    | hipotesis rivales y pruebas
    v
Nivel 4: INVESTIGACION REPRODUCIBLE
    |
    | reconstruir resultados sin memoria conversacional
    v
Nivel 5: CICLO AUTONOMO ACOTADO
    |
    | decidir, ejecutar, evaluar y detenerse
    v
Nivel 6: APRENDIZAJE VERIFICABLE
    |
    | mejorar investigaciones posteriores sin
    | perder procedencia ni propagar errores
    v
Nivel 7: INVESTIGACION INTEGRADA
      multiples capacidades y canales controlados
      con trazabilidad, recuperacion y limites
```

Estos niveles son una escala conceptual de capacidades, no una clasificación confirmada del estado actual de RXRE.

## Síntesis: cómo encajan todos los diagramas

ALMA define el objetivo.

El sistema necesita saber qué pregunta intenta resolver y qué resultado justificaría cerrar la investigación.

CUERPO observa y actúa; MENTE explica.

Las hipótesis deben conducir a pruebas capaces de distinguir explicaciones alternativas.

TIERRA y AIRE preservan la verificabilidad.

Una conclusión debe conservar su evidencia, procedencia, límites y cadena de operaciones.

FUEGO transforma; AGUA aprende.

Los cambios se validan y revierten cuando corresponde; los aprendizajes conservan su procedencia y certeza.

ÉTER integra las relaciones.

Conecta eventos y descubrimientos sin ocultar dependencias ni convertirse en intermediario obligatorio de toda operación.

El principio arquitectónico central: RXRE no debería limitarse a ejecutar herramientas y almacenar resultados. Su objetivo conceptual es construir una cadena verificable desde la pregunta inicial hasta la conclusión, permitir que otra IA cuestione esa cadena y mejorar el proceso a partir de los fallos reales.

El próximo paso correcto no es implementar los diagramas. Es contrastarlos con el repositorio después de superar la puerta de entrada del audit y distinguir qué está implementado, qué es parcial, qué solo está especificado y qué permanece indeterminado.
