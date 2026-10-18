```text
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║     LECTURA EXHAUSTIVA DEL DIAGRAMA RXRE v3+unificado                        ║
║     VERSIÓN CONSOLIDADA v2 — EXPANDIDA Y DETALLADA                          ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

> **Nota metodológica.** Este documento no es un resumen ni un prompt: es el despliegue del diagrama donde cada caja, flecha, marca `[v3]`, campo, estado y condición se examina hasta su implicación verificable. Síntesis de dos lecturas previas: toma el rigor epistemológico de la lectura que trataba FASE 1 como antecedente no corroborado, y la operacionalidad de la lectura que proveía tabla maestra con IDs y criterios PASS/FAIL. Corrige los defectos de ambas (detalle en §0.3). Cada sección incluye diagramas ASCII expandidos, tablas de verificación, matrices de dependencia y criterios de aceptación explícitos.

> **Advertencia epistemológica.** Todo el contenido arquitectónico es **hipótesis de diseño** hasta que exista evidencia suficiente. Las referencias a archivos, implementaciones, mutaciones y resultados de FASE 1 corresponden a **lo reportado**, no a verificación independiente. Cada mención de FASE 1 en este documento usa la forma *«FASE 1 reporta X; pendiente de corroboración por artefacto»*.

---

## §0. Encabezado, estado global y notas de método

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                        ESTADO GLOBAL DEL DOCUMENTO                           │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ESTADO: HIPÓTESIS. Ningún verbo es afirmación sobre el repo.               │
│  El audit A-F decide cuáles son reales.                                     │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  PROPIEDAD              │ VALOR              │ IMPLICACIÓN            │  │
│  ├─────────────────────────┼────────────────────┼────────────────────────┤  │
│  │ Naturaleza              │ Especificación     │ No es implementación   │  │
│  │ Alcance                 │ Diseño arquitect.  │ No es código ejecutable│  │
│  │ Verificación            │ Pendiente          │ Audit A-F requerido    │  │
│  │ Autorización            │ Bloqueada          │ Etapa 1 no inicia      │  │
│  │ FASE 1                  │ Reportada          │ No corroborada         │  │
│  └─────────────────────────┴────────────────────┴────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

Esta condición califica **todo** el documento. Tres consecuencias operativas:

1. **Cada verbo expresa un contrato esperado, no un hecho del repositorio.** «ÉTER notifica async» significa «ÉTER debe notificar async para cumplir el contrato»; no demuestra que hoy lo haga.
2. **El audit A-F es condición previa**, no posterior. Sin audit, el diagrama es mapa sin territorio.
3. **Ningún elemento visual sustituye evidencia.** Interpretar una caja o flecha como prueba de implementación contradice el estado declarado.

### §0.1 Erratas detectadas en el documento fuente

Para preservar trazabilidad, se registran las erratas del texto original y cómo se tratan:

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                         TABLA DE ERRATAS DETECTADAS                          │
├──────┬──────────────────┬────────────────────────┬──────────────────────────┤
│  #   │ Ubicación        │ Errata                 │ Tratamiento              │
├──────┼──────────────────┼────────────────────────┼──────────────────────────┤
│  1   │ §10 concurrencia │ «Los dos coexisten»    │ Se trata como TRES.      │
│      │                  │ pero enumera TRES      │ El error de redacción    │
│      │                  │ mecanismos             │ no altera el contrato:   │
│      │                  │                        │ son tres mecanismos      │
│      │                  │                        │ para tres operaciones.   │
├──────┼──────────────────┼────────────────────────┼──────────────────────────┤
│  2   │ §16 mutación #1  │ «7/7 mutaciones        │ Typo evidente por        │
│      │                  │ odexanadas» (en el     │ «7/7 mutaciones          │
│      │                  │ reporte de FASE 1)     │ detectadas». Se cita     │
│      │                  │                        │ la intención.            │
├──────┼──────────────────┼────────────────────────┼──────────────────────────┤
│  3   │ §15 diagrama     │ «ETAPA 1 (bloqueada    │ Correcto: ETAPA 1 se     │
│      │                  │ hasta aquí)» con       │ desbloquea SOLO con      │
│      │                  │ flecha desde ACCEPTED  │ ACCEPTED. No es errata.  │
└──────┴──────────────────┴────────────────────────┴──────────────────────────┘
```

### §0.2 Estados: 6, no más

El diagrama define **exactamente 6** estados: `PROVEN | PARTIAL | NOT_DETERMINED | PROVEN_ABSENT | DEFERRED | INVALIDATED`. Cualquier clasificación adicional que el audit quiera usar internamente (p. ej. `CORROBORATED`, `CONTRADICTED`, `OPEN`, `UNVERIFIED`) **debe mapearse a uno de los 6** para resolver la casilla. Añadir estados al diagrama violaría «consolidar sin inventar».

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    ESTADOS CANÓNICOS (EXACTAMENTE 6)                         │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐                │
│   │    PROVEN    │   │   PARTIAL    │   │ NOT_DETERMINED   │                │
│   │              │   │              │   │                  │                │
│   │ Respaldada   │   │ Evidencia    │   │ Se buscó; ni     │                │
│   │ dentro de    │   │ respalda     │   │ a favor ni en    │                │
│   │ alcance      │   │ parte del    │   │ contra           │                │
│   │ definido     │   │ alcance      │   │                  │                │
│   └──────────────┘   └──────────────┘   └──────────────────┘                │
│                                                                              │
│   ┌──────────────────┐   ┌──────────────┐   ┌──────────────────┐            │
│   │  PROVEN_ABSENT   │   │   DEFERRED   │   │   INVALIDATED    │            │
│   │                  │   │              │   │                  │            │
│   │ Ausencia         │   │ No evaluada  │   │ Respaldada       │            │
│   │ demostrada       │   │ o pospuesta  │   │ anteriormente;   │            │
│   │ dentro de        │   │ explícita-   │   │ dejó de estarlo  │            │
│   │ alcance definido │   │ mente        │   │ tras reevaluación│            │
│   └──────────────────┘   └──────────────┘   └──────────────────┘            │
│                                                                              │
│   REGLA: Cualquier estado interno adicional DEBE mapearse a uno de estos 6. │
│   VIOLACIÓN: Añadir estados al diagrama consolidado.                        │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Propuesta separada (v4, no vinculante):** la lectura previa introdujo 4 estados extra sin marcarlos como extensión. Se registran aquí como **propuesta abierta a evaluación**, no como parte del contrato v3.

### §0.3 Correcciones respecto de las dos lecturas previas

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│              CORRECCIONES RESPECTO DE LECTURAS PREVIAS                       │
├────────────────────────────────────┬─────────────┬──────────────────────────┤
│ Defecto                            │ Origen      │ Corrección en esta       │
│                                    │             │ versión                  │
├────────────────────────────────────┼─────────────┼──────────────────────────┤
│ Presentar FASE 1 como verificado   │ Lectura A   │ «FASE 1 reporta…;       │
│                                    │             │ pendiente de             │
│                                    │             │ corroboración»           │
├────────────────────────────────────┼─────────────┼──────────────────────────┤
│ Tratar tabla maestra como métrica  │ Lectura A   │ §21 aclara: los conteos  │
│ global                             │             │ de FASE 1 son de un      │
│                                    │             │ subconjunto; la tabla es │
│                                    │             │ la lista completa        │
├────────────────────────────────────┼─────────────┼──────────────────────────┤
│ Añadir estados no contemplados     │ Lectura B   │ §0.2: se mantienen 6;    │
│                                    │             │ extensiones van a v4     │
├────────────────────────────────────┼─────────────┼──────────────────────────┤
│ Perder operacionalidad             │ Lectura B   │ §21 con criterio         │
│                                    │             │ PASS/FAIL por casilla    │
├────────────────────────────────────┼─────────────┼──────────────────────────┤
│ No detectar errata «los dos»       │ Ambas       │ §0.1 #1                  │
│ vs tres                            │             │                          │
├────────────────────────────────────┼─────────────┼──────────────────────────┤
│ No distinguir «verificar» de       │ Lectura B   │ §21 con criterio mínimo  │
│ «cómo verificar»                   │             │ de PASS y evidencia      │
│                                    │             │ refutadora (FAIL)        │
└────────────────────────────────────┴─────────────┴──────────────────────────┘
```

---

## §1. ALMA — criterio de cierre y propósito

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                              ALMA                                            │
│                    criterio de cierre · propósito                            │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  RESPONSABILIDAD          │ ALCANCE              │ LÍMITE             │  │
│  ├───────────────────────────┼──────────────────────┼────────────────────┤  │
│  │ Definir propósito         │ Todo el sistema      │ No ejecuta         │  │
│  │ Establecer criterios      │ Evaluación final     │ No media sync      │  │
│  │ Orientar investigación    │ Dirección estratégica│ No sustituye obs.  │  │
│  │ Determinar cierre         │ Criterios de éxito   │ No registra        │  │
│  └───────────────────────────┴──────────────────────┴────────────────────┘  │
│                                                                              │
│  FASE 1 reporta: ALMA.py con 7 criterios evaluables                         │
│  PENDIENTE DE CORROBORACIÓN por inspección del archivo                      │
│                                                                              │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │ define/orienta
                                    ▼
                            ┌───────────────┐
                            │     ÉTER      │
                            └───────────────┘
```

### Qué representa

Componente conceptual responsable de definir el propósito y los criterios que determinan cuándo una investigación puede considerarse terminada. No ejecuta, no media síncronamente, no sustituye observación ni registro.

### Contratos esperados

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    CONTRATOS DE ALMA (DETALLADOS)                            │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  C1: CRITERIO DE CIERRE                                                     │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Función evaluable que responda «¿esto está terminado?» sin           │  │
│  │  ambigüedad. Una declaración textual no demuestra que sea ejecutable. │  │
│  │                                                                        │  │
│  │  PASS: Función invocable que retorna bool por criterio                │  │
│  │  FAIL: Solo hay declaración textual sin implementación                │  │
│  │  NOT_DETERMINED: No se encontró criterio ni declaración               │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  C2: PROPÓSITO                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Objetivo identificado y vinculado a los criterios de cierre.         │  │
│  │                                                                        │  │
│  │  PASS: Propósito referenciado por criterios de cierre                 │  │
│  │  FAIL: Propósito sin vínculo con criterios                            │  │
│  │  NOT_DETERMINED: No se encontró propósito                             │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  C3: DIRECCIÓN DEFINE/ORIENTA                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  ALMA → ÉTER. Unidireccional en el diagrama; la implementación puede  │  │
│  │  o no serlo, pero el contrato exige que ALMA no sea intermediario     │  │
│  │  síncrono obligatorio.                                                │  │
│  │                                                                        │  │
│  │  PASS: Planos operan sin llamada obligatoria a ALMA                   │  │
│  │  FAIL: Planos dependen de ALMA por llamada sync                       │  │
│  │  NOT_DETERMINED: No se pudo determinar la dirección                   │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Qué NO se infiere

- Que ALMA no pueda recibir información de una auditoría.
- Que exista `ALMA.py`.
- Que el número de criterios sea 7 (FASE 1 **reporta** 7; pendiente de corroboración por artefacto).
- Que la flecha represente dependencia real de código.

### Casilla de audit

Determinar si existe capacidad equivalente, si el criterio es evaluable, si el propósito está declarado, y si otras capacidades consultan esos criterios. FASE 1 reporta `ALMA.py` con 7 criterios evaluables; **pendiente de corroboración** por inspección del archivo, definición de criterios y resultados observables.

### Diagrama de dependencia de ALMA

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    DEPENDENCIAS DE ALMA (HIPÓTESIS)                          │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ALMA no depende de:                                                        │
│   ├── ÉTER (no espera respuesta para orientar)                               │
│   ├── AIRE (no observa directamente)                                         │
│   ├── TIERRA (no registra directamente)                                      │
│   ├── MENTE (no formula hipótesis)                                           │
│   ├── CUERPO (no observa)                                                    │
│   ├── FUEGO (no transforma)                                                  │
│   ├── AGUA (no aprende)                                                      │
│   └── ROUTER (no invoca capacidades)                                         │
│                                                                              │
│   ALMA orienta a:                                                            │
│   └── ÉTER (define criterios que ÉTER distribuye)                            │
│                                                                              │
│   ALMA es consultada por:                                                    │
│   └── Puerta de aceptación (verifica criterio de cierre antes de ACCEPTED)   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## §2. ÉTER — hub async

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                              ÉTER                                            │
│                      hub async · NO media sync                               │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  [v3] 3 MODOS DE FALLO                                                │  │
│  │                                                                        │  │
│  │  MODO 1: CAÍDA DE PROCESO                                             │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │  │
│  │  │  Condición: Proceso termina inesperadamente                     │  │  │
│  │  │  Efecto: RAM se pierde completamente                            │  │  │
│  │  │  Recuperación: Solo lo que alcanzó persistencia efectiva        │  │  │
│  │  │  Garantía: Nada se recupera desde RAM                           │  │  │
│  │  │  Prueba: Matar proceso → verificar que solo sobrevive disco     │  │  │
│  │  └──────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                        │  │
│  │  MODO 2: SATURACIÓN DE COLA                                           │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │  │
│  │  │  Condición: Cola de eventos llena                               │  │  │
│  │  │  Efecto: Descarte de eventos nuevos                             │  │  │
│  │  │  Garantía: Descarte CONTADO, consultable                        │  │  │
│  │  │  Distinción: «no llegó» ≠ «llegó y se descartó»                │  │  │
│  │  │  Prueba: Llenar cola → verificar contador de descartes          │  │  │
│  │  └──────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                        │  │
│  │  MODO 3: REINICIO                                                     │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │  │
│  │  │  Condición: Proceso reinicia (graceful o forzado)               │  │  │
│  │  │  Efecto: Estado en RAM se pierde                                │  │  │
│  │  │  Recuperación: Estado persistido + reglas de recuperación       │  │  │
│  │  │  Garantía: Solo disco vive tras reinicio                        │  │  │
│  │  │  Prueba: Reiniciar → verificar estado == persistido             │  │  │
│  │  └──────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  [v3] WRITE-AHEAD                                                     │  │
│  │                                                                        │  │
│  │  Flujo:                                                                │  │
│  │  evento → id único → fsync → confirmación → idempotencia              │  │
│  │                                                                        │  │
│  │  Reglas:                                                               │  │
│  │  ├── Id único asignado ANTES de persistencia                          │  │
│  │  ├── fsync DEBE completar antes de confirmar                          │  │
│  │  ├── Confirmación SOLO post-fsync exitoso                             │  │
│  │  ├── Mismo id reenviado NO produce doble efecto                       │  │
│  │  └── Eventos críticos: SIEMPRE disco, NUNCA solo RAM                  │  │
│  │                                                                        │  │
│  │  FASE 1 reporta: ÉTER.py con write-ahead, idempotencia y 3 modos      │  │
│  │  Mutación #1 detectada con 1 fallo                                    │  │
│  │  PENDIENTE DE CORROBORACIÓN                                           │  │
│  │                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │ notifica async
                                    ▼
                    ┌───────────────────────────────────┐
                    │         AIRE · TIERRA             │
                    └───────────────────────────────────┘
```

### Qué representa

Hub de eventos asíncronos. `NO media sync` es una **prohibición**: si ÉTER media síncronamente, el contrato está roto aunque funcione.

### Direcciones

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    DIRECCIONES DE ÉTER (HIPÓTESIS)                           │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  RECIBE (async):                                                             │
│  └── ALMA → define/orienta                                                  │
│                                                                              │
│  EMITE (async):                                                              │
│  ├── ÉTER → AIRE (notificación de eventos)                                  │
│  └── ÉTER → TIERRA (notificación de eventos)                                │
│                                                                              │
│  NO RECIBE de:                                                               │
│  ├── MENTE (no es invocado por MENTE)                                       │
│  ├── CUERPO (no es invocado por CUERPO)                                     │
│  ├── FUEGO (no es invocado por FUEGO)                                       │
│  └── AGUA (no es invocado por AGUA)                                         │
│                                                                              │
│  NO MEDIA:                                                                   │
│  ├── MENTE ↔ CUERPO (sync directo, sin ÉTER)                                │
│  ├── CUERPO ↔ FUEGO (sync directo, sin ÉTER)                                │
│  └── MENTE ↔ FUEGO (sync directo, sin ÉTER)                                 │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Los tres modos de fallo `[v3]` — detalle expandido

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    MODOS DE FALLO DE ÉTER (DETALLE)                          │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  MODO 1: CAÍDA DE PROCESO                                                   │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐            │  │
│  │  │ Evento  │───►│ Id único│───►│ fsync   │───►│ Confirm.│            │  │
│  │  │ llega   │    │ asignado│    │ a disco │    │ post-   │            │  │
│  │  │         │    │         │    │         │    │ fsync   │            │  │
│  │  └─────────┘    └─────────┘    └─────────┘    └─────────┘            │  │
│  │       │              │              │              │                   │  │
│  │       │              │              │              │                   │  │
│  │       ▼              ▼              ▼              ▼                   │  │
│  │  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐            │  │
│  │  │ RAM     │    │ RAM     │    │ DISCO   │    │ DISCO   │            │  │
│  │  │ (volátil│    │ (volátil│    │ (persist│    │ (persist│            │  │
│  │  │  hasta  │    │  hasta  │    │  desde  │    │  desde  │            │  │
│  │  │  fsync) │    │  fsync) │    │  fsync) │    │  fsync) │            │  │
│  │  └─────────┘    └─────────┘    └─────────┘    └─────────┘            │  │
│  │                                                                        │  │
│  │  SI CAÍDA EN:     RAM (volátil)  RAM (volátil)  DISCO   DISCO         │  │
│  │  SE RECUPERA:     NADA           NADA          SÍ      SÍ            │  │
│  │                                                                        │  │
│  │  REGLA: Solo sobrevive lo que alcanzó persistencia efectiva.          │  │
│  │  NADA se recupera desde RAM.                                          │  │
│  │                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  MODO 2: SATURACIÓN DE COLA                                                 │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐            │  │
│  │  │ Evento  │───►│ Cola    │───►│ Cola    │───►│ Descarte│            │  │
│  │  │ llega   │    │ tiene   │    │ LLENA   │    │ contado │            │  │
│  │  │         │    │ espacio │    │         │    │         │            │  │
│  │  └─────────┘    └────┬────┘    └────┬────┘    └────┬────┘            │  │
│  │                      │              │              │                   │  │
│  │                      ▼              ▼              ▼                   │  │
│  │                 ┌─────────┐    ┌─────────┐    ┌─────────┐            │  │
│  │                 │Procesa  │    │Rechaza  │    │Contador │            │  │
│  │                 │normal   │    │nuevo    │    │incremen.│            │  │
│  │                 │         │    │evento   │    │         │            │  │
│  │                 └─────────┘    └─────────┘    └─────────┘            │  │
│  │                                                                        │  │
│  │  DISTINCIÓN CRÍTICA:                                                  │  │
│  │  ├── «No llegó»: Evento nunca alcanzó la cola                         │  │
│  │  └── «Llegó y se descartó»: Evento alcanzó la cola pero fue           │  │
│  │      rechazado por capacidad. CONTADOR registra este caso.            │  │
│  │                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  MODO 3: REINICIO                                                           │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐            │  │
│  │  │ Proceso │───►│ RAM se  │───►│ Disco   │───►│ Estado  │            │  │
│  │  │ reinicia│    │ pierde  │    │ persiste│    │ recuper.│            │  │
│  │  │         │    │         │    │         │    │         │            │  │
│  │  └─────────┘    └─────────┘    └─────────┘    └─────────┘            │  │
│  │                                                                        │  │
│  │  RECUPERACIÓN:                                                        │  │
│  │  ├── Estado = persistido en disco                                     │  │
│  │  ├── + Reglas de recuperación declaradas                              │  │
│  │  ├── + Eventos en tránsito según write-ahead                          │  │
│  │  └── - NADA desde RAM                                                 │  │
│  │                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Write-ahead `[v3]` — flujo detallado

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    WRITE-AHEAD DE ÉTER (FLUJO DETALLADO)                     │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PASO 1: EVENTO LLEGA                                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │  │
│  │  │  Evento E1 llega a ÉTER                                         │  │  │
│  │  │  Contenido: {tipo, payload, timestamp_origen, productor}        │  │  │
│  │  └──────────────────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                              │                                               │
│                              ▼                                               │
│  PASO 2: ID ÚNICO ASIGNADO (ANTES DE DISCO)                                  │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │  │
│  │  │  ID = generar_id_único()                                        │  │  │
│  │  │  Propiedad: Único dentro del ámbito de ÉTER                     │  │  │
│  │  │  Requisito: Sin ID, no hay idempotencia posible                 │  │  │
│  │  │  Ubicación: RAM (temporal hasta persistencia)                   │  │  │
│  │  └──────────────────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                              │                                               │
│                              ▼                                               │
│  PASO 3: FSYNC (PERSISTENCIA A DISCO)                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │  │
│  │  │  resultado = fsync(evento_con_id)                               │  │  │
│  │  │                                                                  │  │  │
│  │  │  SI fsync EXITOSO:                                              │  │  │
│  │  │  ├── Evento persistido en disco                                 │  │  │
│  │  │  ├── ID persistido en disco                                     │  │  │
│  │  │  └── Continuar a PASO 4                                         │  │  │
│  │  │                                                                  │  │  │
│  │  │  SI fsync FALLA:                                                │  │  │
│  │  │  ├── Evento NO persistido                                       │  │  │
│  │  │  ├── ID NO persistido                                           │  │  │
│  │  │  ├── NO confirmar                                               │  │  │
│  │  │  ├── Registrar error                                            │  │  │
│  │  │  └── Reintentar o descartar (según política)                    │  │  │
│  │  └──────────────────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                              │                                               │
│                              ▼                                               │
│  PASO 4: CONFIRMACIÓN (SOLO POST-FSYNC EXITOSO)                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │  │
│  │  │  SI fsync fue EXITOSO:                                          │  │  │
│  │  │  ├── Confirmar recepción al productor                           │  │  │
│  │  │  ├── Notificar a consumidores (AIRE, TIERRA)                    │  │  │
│  │  │  └── Marcar evento como confirmado                              │  │  │
│  │  │                                                                  │  │  │
│  │  │  SI fsync NO fue EXITOSO:                                       │  │  │
│  │  │  ├── NO confirmar                                               │  │  │
│  │  │  ├── Productor puede reenviar                                   │  │  │
│  │  │  └── Idempotencia previene doble efecto                         │  │  │
│  │  └──────────────────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                              │                                               │
│                              ▼                                               │
│  PASO 5: IDEMPOTENCIA (REENVÍO SIN DOBLE EFECTO)                             │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │  │
│  │  │  SI productor reenvía evento con MISMO ID:                      │  │  │
│  │  │  ├── Verificar si ID ya existe en disco                         │  │  │
│  │  │  ├── SI existe: NO procesar nuevamente                         │  │  │
│  │  │  ├── SI existe: Confirmar recepción (sin doble efecto)          │  │  │
│  │  │  └── SI no existe: Procesar como evento nuevo                   │  │  │
│  │  │                                                                  │  │  │
│  │  │  REQUISITO: Deduplicación en consumidores                       │  │  │
│  │  │  Sin deduplicación, idempotencia es incompleta                  │  │  │
│  │  └──────────────────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  REGLA ADICIONAL: EVENTOS CRÍTICOS                                           │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Eventos críticos: SIEMPRE disco, NUNCA solo RAM                      │  │
│  │                                                                        │  │
│  │  PROBLEMA: El diagrama NO enumera cuáles son críticos (§22 #1)        │  │
│  │  REQUISITO: Clasificación explícita de eventos críticos               │  │
│  │  AUDIT: Debe verificar que la clasificación existe y se aplica        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Qué NO se infiere

- Que ÉTER exista.
- Que el `fsync` esté efectivamente esperado.
- Que la idempotencia esté implementada (asignar id único no es suficiente).
- Que la clasificación de críticos esté definida.

### Casilla de audit

Verificar: identificación única, orden persistencia→confirmación, tratamiento de errores de fsync, deduplicación de reenvíos, recuperación tras caída/reinicio, clasificación de críticos, uso real por productores. FASE 1 reporta: `ETER.py` con write-ahead, idempotencia y 3 modos; mutación #1 detectada con 1 fallo. **Pendiente de corroboración** por examen de scripts, artefactos mutados y salidas.

---

## §3. AIRE — capa transversal que observa

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                              AIRE                                            │
│                    capa transversal · observa                                │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  TRAZA COMPLETA (3 TRAMOS)                                            │  │
│  │                                                                        │  │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐             │  │
│  │  │  DECISIÓN    │───►│  HERRAMIENTA │───►│  RESULTADO   │             │  │
│  │  │              │    │              │    │              │             │  │
│  │  │  ¿Por qué    │    │  ¿Con qué   │    │  ¿Qué se     │             │  │
│  │  │  se decidió  │    │  se ejecutó? │    │  obtuvo?     │             │  │
│  │  │  ejecutar?   │    │              │    │              │             │  │
│  │  └──────────────┘    └──────────────┘    └──────────────┘             │  │
│  │                                                                        │  │
│  │  REQUISITO: Los 3 tramos presentes, no 2.                             │  │
│  │  COBERTURA: También fallos y ejecuciones sin resultado satisfactorio. │  │
│  │  TRANSVERSAL: No debe convertirse en dependencia síncrona obligatoria.│  │
│  │                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  FASE 1 reporta: PARTIAL                                                     │
│  PENDIENTE DE CORROBORACIÓN por examen de trazas y esquema                   │
│                                                                              │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │ observa
                                    ▼
                    ┌───────────────────────────────────┐
                    │    PLANOS DE ACCIÓN (sync)        │
                    └───────────────────────────────────┘
```

### Qué representa

Capacidad de reconstruir la cadena de ejecución. Distinción funcional con TIERRA: **AIRE registra traza; TIERRA conserva evidencia**. La separación se evalúa por comportamiento, no por existencia de dos nombres.

### Contratos esperados

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    CONTRATOS DE AIRE (DETALLADOS)                            │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  C1: TRAZA COMPLETA (3 TRAMOS)                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Los 3 tramos (decisión → herramienta → resultado), no 2.             │  │
│  │                                                                        │  │
│  │  PASS: Trazas reales con los 3 tramos reconstruibles                  │  │
│  │  FAIL: Falta algún tramo en trazas reales                             │  │
│  │  NOT_DETERMINED: No hay trazas para evaluar                           │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  C2: COBERTURA DE FALLOS                                                    │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  También fallos y ejecuciones sin resultado satisfactorio.            │  │
│  │                                                                        │  │
│  │  PASS: Fallos registrados con traza completa                          │  │
│  │  FAIL: Solo éxitos registrados, fallos ausentes                       │  │
│  │  NOT_DETERMINED: No hay fallos registrados para evaluar               │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  C3: TRANSVERSALIDAD                                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  No debe convertirse en dependencia síncrona obligatoria.             │  │
│  │                                                                        │  │
│  │  PASS: Planos operan sin llamada síncrona obligatoria a AIRE          │  │
│  │  FAIL: Planos bloqueados esperando AIRE                               │  │
│  │  NOT_DETERMINED: No se pudo determinar                                │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  C4: TOOL_HASH (SI OBLIGATORIO)                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Si es obligatorio, debe identificar de forma reproducible el         │  │
│  │  artefacto de herramienta.                                            │  │
│  │                                                                        │  │
│  │  PASS: Hash de herramienta reproducible y verificable                 │  │
│  │  FAIL: Hash ausente o no reproducible                                 │  │
│  │  NOT_DETERMINED: No se pudo determinar si es obligatorio              │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Qué NO se infiere

- Que AIRE nunca escriba persistencia.
- Que AIRE no pueda emitir a otros componentes.
- Que una traza completa demuestre corrección semántica.
- Que exista `AIRE.py` o que `tool_hash` sea obligatorio en el repo actual.

### Casilla de audit

Comprobar si se reconstruye una ejecución real desde decisiones hasta resultados, si los fallos quedan representados, si la identidad de herramientas se verifica. FASE 1 reporta PARTIAL. **Pendiente de corroboración** por examen de trazas y esquema.

### Diagrama de traza completa

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    TRAZA COMPLETA DE AIRE (EJEMPLO)                          │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  TRAMO 1: DECISIÓN                                                           │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Timestamp: 2026-10-18T14:30:00Z                                      │  │
│  │  Actor: MENTE                                                           │  │
│  │  Decisión: Ejecutar análisis de funciones binarias                    │  │
│  │  Justificación: Hipótesis H1 requiere identificación de funciones     │  │
│  │  Contexto: Claim C-001, scope: driver_rx550.ko                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                              │                                               │
│                              ▼                                               │
│  TRAMO 2: HERRAMIENTA                                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Timestamp: 2026-10-18T14:30:01Z                                      │  │
│  │  Herramienta: binary.functions                                         │  │
│  │  Backend: rizin (versión 0.7.3)                                       │  │
│  │  tool_hash: sha256:a1b2c3d4e5f6...                                    │  │
│  │  Argumentos: [--format=json, --output=functions.json]                 │  │
│  │  Entorno: Nobara Linux, kernel 6.8.0                                  │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                              │                                               │
│                              ▼                                               │
│  TRAMO 3: RESULTADO                                                          │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Timestamp: 2026-10-18T14:30:05Z                                      │  │
│  │  Estado: SUCCESS / FAILURE / PARTIAL                                  │  │
│  │  Output: functions.json (hash: sha256:f6e5d4c3b2a1...)                │  │
│  │  Funciones identificadas: 42                                          │  │
│  │  Limitaciones: Sin símbolos DWARF, solo análisis estático             │  │
│  │  Duración: 4 segundos                                                 │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  SI ESTADO = FAILURE:                                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Timestamp: 2026-10-18T14:30:05Z                                      │  │
│  │  Estado: FAILURE                                                      │  │
│  │  Error: "No se pudo cargar binario: permiso denegado"                 │  │
│  │  Output: NINGUNO                                                      │  │
│  │  Funciones identificadas: 0                                           │  │
│  │  Limitaciones: Error de permisos, no se pudo ejecutar                 │  │
│  │  Duración: 0 segundos                                                 │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  REQUISITO: Ambos casos (éxito y fallo) DEBEN quedar registrados.           │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## §4. TIERRA — capa transversal que registra

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                              TIERRA                                          │
│                    capa transversal · registra                               │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  GRAFO DE EVIDENCIA                                                   │  │
│  │                                                                        │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │  │
│  │  │  COMPONENTE              │ FUNCIÓN                                │  │  │
│  │  ├──────────────────────────┼────────────────────────────────────────┤  │  │
│  │  │ Hash SHA-256             │ Integridad por artefacto               │  │  │
│  │  │ Procedencia              │ Productor → transformación → consumidor│  │  │
│  │  │ Contradicciones          │ Registro append con procedencia        │  │  │
│  │  │ Schema de claims         │ 10 campos obligatorios                 │  │  │
│  │  │ Concurrencia             │ 3 mecanismos por operación             │  │  │
│  │  │ Inmutabilidad            │ 4 mecanismos estructurales             │  │  │
│  │  │ Estados epistémicos      │ 6 estados canónicos                    │  │  │
│  │  │ 3 capas de hash          │ Integridad/autenticidad/validez        │  │  │
│  │  └──────────────────────────┴────────────────────────────────────────┘  │  │
│  │                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  FASE 1 reporta: PARTIAL en varias                                           │
│  CADA CONTRATO SE EVALÚA POR SEPARADO                                        │
│                                                                              │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │ registra
                                    ▼
                    ┌───────────────────────────────────┐
                    │    PLANOS DE ACCIÓN (sync)        │
                    └───────────────────────────────────┘
```

### Qué representa

Capacidad de conservar evidencia y relacionarla con afirmaciones. El grafo y el schema del claim (§9) forman parte del contrato; su existencia efectiva se comprueba por separado.

### Contratos esperados

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    CONTRATOS DE TIERRA (DETALLADOS)                          │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  C1: INTEGRIDAD                                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Hash SHA-256 por artefacto, sobre bytes definidos, verificable en    │  │
│  │  punto pertinente.                                                    │  │
│  │                                                                        │  │
│  │  PASS: Cada artefacto con hash calculado y verificable                │  │
│  │  FAIL: Artefacto sin hash o hash no verificable                       │  │
│  │  NOT_DETERMINED: No hay artefactos para evaluar                       │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  C2: PROCEDENCIA                                                            │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Cadena productor → transformación → consumidor cuando esos           │  │
│  │  eslabones existan.                                                   │  │
│  │                                                                        │  │
│  │  PASS: Cadena reconstruible para evidencia real                       │  │
│  │  FAIL: Eslabón perdido en cadena real                                 │  │
│  │  NOT_DETERMINED: No hay evidencia con procedencia para evaluar        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  C3: CONTRADICCIONES REGISTRADAS                                            │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  No resueltas automáticamente (ver §12.2).                            │  │
│  │                                                                        │  │
│  │  PASS: Registro append con procedencia de contradicciones             │  │
│  │  FAIL: Contradicciones descartadas o resueltas automáticamente        │  │
│  │  NOT_DETERMINED: No hay contradicciones registradas                   │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  C4: SEPARACIÓN DE RESPONSABILIDADES                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Registrar ≠ validar semántica ≠ decidir estado.                      │  │
│  │                                                                        │  │
│  │  PASS: TIERRA registra sin validar semántica ni decidir estado        │  │
│  │  FAIL: TIERRA valida semántica o decide estado                        │  │
│  │  NOT_DETERMINED: No se pudo determinar                                │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Qué NO demuestra TIERRA por sí sola

- Que un artefacto sea auténtico porque su hash coincide (§13).
- Que la evidencia respalde semánticamente una afirmación.
- Que todas las transformaciones posibles estén registradas.
- Que el sistema conserve inmutabilidad efectiva por declararla.

### Casilla de audit

Examinar schema de claims, registros de evidencia, procedencia, integridad y representación de contradicciones. FASE 1 reporta PARTIAL en varias. **Cada contrato se evalúa por separado**; una clasificación general de TIERRA no transfiere la misma conclusión a todos.

### Diagrama de grafo de evidencia

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    GRAFO DE EVIDENCIA DE TIERRA                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────┐                                                           │
│   │    CLAIM     │                                                           │
│   │   C-001      │                                                           │
│   │              │                                                           │
│   │ statement:   │                                                           │
│   │ "driver_rx550│                                                           │
│   │  soporta     │                                                           │
│   │  2GB VRAM"   │                                                           │
│   │              │                                                           │
│   │ epistemic_   │                                                           │
│   │ state:       │                                                           │
│   │ PARTIAL      │                                                           │
│   └──────┬───────┘                                                           │
│          │                                                                   │
│          │ evidence_refs[]                                                   │
│          │                                                                   │
│          ├──────────────────────────────────────────────────────────────┐    │
│          │                                                              │    │
│          ▼                                                              ▼    │
│   ┌──────────────┐                                               ┌──────────┐│
│   │  EVIDENCE    │                                               │ EVIDENCE ││
│   │   E-001      │                                               │  E-002   ││
│   │              │                                               │          ││
│   │ type:        │                                               │ type:    ││
│   │ binary_analy │                                               │ runtime_ ││
│   │ source_hash: │                                               │ source_  ││
│   │ sha256:a1b2. │                                               │ hash:    ││
│   │ tool_version:│                                               │ sha256:  ││
│   │ rizin_0.7.3  │                                               │ f6e5d4.  ││
│   │ output_hash: │                                               │          ││
│   │ sha256:c3d4. │                                               │          ││
│   │ provenance:  │                                               │          ││
│   │ MENTE→CUERPO │                                               │          ││
│   │ immutable:   │                                               │          ││
│   │ TRUE         │                                               │          ││
│   └──────────────┘                                               └──────────┘│
│          │                                                              │    │
│          │ derivation_refs[]                                            │    │
│          │                                                              │    │
│          ▼                                                              │    │
│   ┌──────────────┐                                                      │    │
│   │  DERIVATION  │                                                      │    │
│   │   D-001      │                                                      │    │
│   │              │                                                      │    │
│   │ tool:        │                                                      │    │
│   │ binary.func. │                                                      │    │
│   │ version:     │                                                      │    │
│   │ 0.7.3        │                                                      │    │
│   │ in_hash:     │                                                      │    │
│   │ sha256:a1b2. │                                                      │    │
│   │ out_hash:    │                                                      │    │
│   │ sha256:c3d4. │                                                      │    │
│   └──────────────┘                                                      │    │
│                                                                          │    │
│   ┌──────────────┐                                                      │    │
│   │CONTRADICTION │◄─────────────────────────────────────────────────────┘    │
│   │   CT-001     │                                                           │
│   │              │                                                           │
│   │ claim_a:     │                                                           │
│   │ C-001        │                                                           │
│   │ claim_b:     │                                                           │
│   │ C-002        │                                                           │
│   │ reason:      │                                                           │
│   │ "VRAM report │                                                           │
│   │  1GB vs 2GB" │                                                           │
│   │ severity:    │                                                           │
│   │ HIGH         │                                                           │
│   │ status:      │                                                           │
│   │ OPEN         │                                                           │
│   └──────────────┘                                                           │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## §5. Planos de acción: MENTE, CUERPO, FUEGO

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    PLANOS DE ACCIÓN (CONTRATOS SÍNCRONOS)                    │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌────────────────────┐         ┌────────────────────┐                     │
│   │       MENTE        │◄═══════►│       CUERPO       │                     │
│   │                    │  sync   │                    │                     │
│   │ hipótesis rivales  │         │ observación real   │                     │
│   │ causalidad · CFG   │         │ medición · artefacto│                    │
│   │ [v3] falsificación │         │ [v3] hash verificado│                    │
│   │  explícita         │         │  en punto de uso   │                     │
│   └─────────┬──────────┘         └─────────┬──────────┘                     │
│             │                              │                                 │
│             │                              │                                 │
│             └══════════ sync ══════════════╪══════════ sync ═══════════┐    │
│                                            │                          │    │
│                                            ▼                          │    │
│                                  ┌────────────────────┐              │    │
│                                  │       FUEGO        │              │    │
│                                  │                    │              │    │
│                                  │ transformación     │              │    │
│                                  │ controlada         │              │    │
│                                  │ [v3] R12: rollback │              │    │
│                                  │  por dispositivo   │              │    │
│                                  └─────────┬──────────┘              │    │
│                                            │                          │    │
│                                            │                          │    │
│                                            └══════════ sync ══════════┘    │
│                                            │                                │
│                                            ▼                                │
│                                  ┌────────────────────┐                     │
│                                  │        AGUA        │                     │
│                                  │                    │                     │
│                                  │ aprendizaje con    │                     │
│                                  │ procedencia        │                     │
│                                  │ [v3] revalidar al  │                     │
│                                  │  recuperar         │                     │
│                                  └────────────────────┘                     │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Qué representan

- **MENTE:** formular y contrastar hipótesis, causalidad, CFG, falsificación.
- **CUERPO:** observar sistemas reales, medir, producir artefactos.
- **FUEGO:** transformar controladamente, con recuperación adecuada.

Comunicaciones **síncronas directas** entre los tres. Bus sync inferior hacia AGUA. Estas relaciones son **hipótesis arquitectónicas**, no hechos del dibujo.

### 5.1 MENTE — detalle expandido

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    MENTE (DETALLE DE CONTRATOS)                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  C1: HIPÓTESIS RIVALES                                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Cuando hay alternativas relevantes, deben formularse hipótesis       │  │
│  │  distinguibles por evidencia. No todo caso requiere rivales (algunas  │  │
│  │  propiedades admiten una única hipótesis razonable dentro de un       │  │
│  │  alcance delimitado).                                                 │  │
│  │                                                                        │  │
│  │  PASS: Múltiples hipótesis distinguibles en casos relevantes          │  │
│  │  FAIL: Solo una hipótesis sin justificación                           │  │
│  │  NOT_DETERMINED: No hay casos con alternativas relevantes             │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  C2: CAUSALIDAD                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Conclusiones causales con pruebas discriminantes, no solo            │  │
│  │  correlaciones.                                                       │  │
│  │                                                                        │  │
│  │  PASS: Pruebas que discriminan causas                                 │  │
│  │  FAIL: Solo correlación sin prueba discriminante                      │  │
│  │  NOT_DETERMINED: No hay conclusiones causales                         │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  C3: CFG (CONTROL FLOW GRAPH)                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Representación útil cuando el dominio lo requiera; no obligatoria    │  │
│  │  en todos los dominios.                                               │  │
│  │                                                                        │  │
│  │  PASS: Representación disponible para dominios que la requieran       │  │
│  │  FAIL: No disponible donde se requiere                                │  │
│  │  NOT_DETERMINED: No hay dominios que requieran CFG                    │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  C4: [v3] FALSIFICACIÓN EXPLÍCITA                                            │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Condiciones de refutación comprobables, ejecutables o identificadas  │  │
│  │  con precisión como pendientes.                                       │  │
│  │                                                                        │  │
│  │  PASS: Cada claim con falsification_test comprobable                  │  │
│  │  FAIL: Claim sin refutación                                           │  │
│  │  NOT_DETERMINED: No hay claims para evaluar                           │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 CUERPO — detalle expandido

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    CUERPO (DETALLE DE CONTRATOS)                             │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  C1: OBSERVACIÓN REAL                                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Distinguir de datos simulados o inferidos.                           │  │
│  │                                                                        │  │
│  │  PASS: Distinción explícita en la interfaz                            │  │
│  │  FAIL: Observación simulada sin marca                                 │  │
│  │  NOT_DETERMINED: No hay observaciones para evaluar                    │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  C2: MEDICIÓN                                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Magnitudes, unidades, condiciones, procedimiento.                    │  │
│  │                                                                        │  │
│  │  PASS: Mediciones con magnitudes, unidades, condiciones               │  │
│  │  FAIL: Mediciones sin condiciones                                     │  │
│  │  NOT_DETERMINED: No hay mediciones para evaluar                       │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  C3: ARTEFACTOS                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Conservar resultados materiales.                                     │  │
│  │                                                                        │  │
│  │  PASS: Artefacto material recuperable                                 │  │
│  │  FAIL: Solo traza, no artefacto                                       │  │
│  │  NOT_DETERMINED: No hay artefactos para evaluar                       │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  C4: [v3] HASH VERIFICADO EN PUNTO DE USO                                    │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Re-verificar al consumir, no solo al almacenar. Reduce el riesgo de  │  │
│  │  usar contenido alterado. NO demuestra autenticidad ni interpretación │  │
│  │  correcta (§13).                                                      │  │
│  │                                                                        │  │
│  │  PASS: Recomputación al consumir                                      │  │
│  │  FAIL: Uso sin re-verificar                                           │  │
│  │  NOT_DETERMINED: No hay consumo de artefactos                         │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 5.3 FUEGO — detalle expandido

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    FUEGO (DETALLE DE CONTRATOS)                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  C1: TRANSFORMACIÓN CONTROLADA                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Alcance acotado, efectos registrados, condiciones de recuperación.   │  │
│  │                                                                        │  │
│  │  PASS: Alcance, efectos, condiciones de recuperación documentados     │  │
│  │  FAIL: Sin control                                                    │  │
│  │  NOT_DETERMINED: No hay transformaciones para evaluar                 │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  C2: [v3] R12: ROLLBACK POR DISPOSITIVO                                      │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Unidad de recuperación = dispositivo afectado. Un rollback de        │  │
│  │  transacción SQLite NO demuestra R12 (§5.5).                          │  │
│  │                                                                        │  │
│  │  PASS: Test de rollback por unidad-device                             │  │
│  │  FAIL: Journal SQLite o global                                        │  │
│  │  NOT_DETERMINED: No hay transformaciones con rollback                 │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 5.4 Bus síncrono inferior

El bus representa la hipótesis de que los tres planos proporcionan información a AGUA vía interacción síncrona. **No especifica** protocolo, semántica de llamadas, política de errores ni comportamiento ante fallos parciales. No demuestra que la agregación sea atómica.

### 5.5 Homonimias a vigilar

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    HOMONIMIAS A VIGILAR                                      │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  TÉRMINO: «Rollback»                                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Journal de SQLite ≠ R12.                                             │  │
│  │  Coincidencia de nombre no es equivalencia funcional.                 │  │
│  │                                                                        │  │
│  │  SQLite rollback: Revierte transacciones en base de datos             │  │
│  │  R12 rollback: Revierte estado de dispositivo (GPU, PCIe, MMIO)       │  │
│  │                                                                        │  │
│  │  AUDIT: Debe verificar que R12 no se confunde con SQLite rollback     │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  TÉRMINO: «Sync»                                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Flecha sync entre planos ≠ protocolo definido.                       │  │
│  │  Es hipótesis de comunicación síncrona, no especificación.            │  │
│  │                                                                        │  │
│  │  AUDIT: Debe verificar si hay protocolo o solo flecha                 │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  TÉRMINO: «Hash en punto de uso»                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Recomputar ≠ demostrar autenticidad ni validez.                      │  │
│  │                                                                        │  │
│  │  AUDIT: Debe verificar que no se confunde integridad con autenticidad │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Casilla de audit

Determinar qué capacidades existen, qué relaciones de comunicación se observan y qué contratos cubren pruebas. FASE 1 reporta `planos.py` agrupando MENTE/CUERPO/FUEGO; **pendiente de corroboración** por examen de interfaces, mutación #4 (2 fallos reportados) y artefactos.

---

## §6. AGUA — aprendizaje con procedencia

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                              AGUA                                            │
│                    aprendizaje con procedencia                               │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  [v3] REVALIDACIÓN AL RECUPERAR                                       │  │
│  │                                                                        │  │
│  │  El conocimiento persistido no se considera correcto por el hecho de  │  │
│  │  estar guardado. Al recuperarlo, se comprueban condiciones pertinentes│  │
│  │                                                                        │  │
│  │  Puede incluir:                                                        │  │
│  │  ├── Integridad del registro                                          │  │
│  │  ├── Procedencia y condiciones originales                           │  │
│  │  ├── Vigencia respecto del sistema investigado                        │  │
│  │  ├── Reevaluación de afirmaciones dependientes de condiciones         │  │
│  │  │   cambiantes                                                       │  │
│  │  └── Distinción entre aprendizaje reutilizable y conocimiento         │  │
│  │      demostrado                                                       │  │
│  │                                                                        │  │
│  │  La revalidación NO es uniforme: depende del tipo de conocimiento y   │  │
│  │  de las condiciones que puedan invalidarlo.                           │  │
│  │                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  FASE 1 reporta: PARTIAL/AUSENTE según contrato                              │
│  PENDIENTE DE CORROBORACIÓN por artefactos                                   │
│                                                                              │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │ invoca capacidades
                                    ▼
                    ┌───────────────────────────────────┐
                    │         ROUTER DE CAPACIDADES     │
                    └───────────────────────────────────┘
```

### Qué representa

Capacidad de conservar y reutilizar aprendizaje con procedencia. Recibe de los tres planos (bus sync) e invoca capacidades vía ROUTER.

### `[v3]` Revalidación al recuperar — flujo detallado

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    REVALIDACIÓN AL RECUPERAR (FLUJO)                         │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PASO 1: SOLICITUD DE RECUPERACIÓN                                           │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  AGUA solicita recuperar aprendizaje L-001                            │  │
│  │  Contexto: Claim C-001, scope: driver_rx550.ko                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                              │                                               │
│                              ▼                                               │
│  PASO 2: VERIFICACIÓN DE INTEGRIDAD                                          │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  ¿Hash del registro == hash declarado?                                │  │
│  │                                                                        │  │
│  │  SI PASS: Continuar a PASO 3                                          │  │
│  │  SI FAIL: Aprendizaje corrupto, NO recuperar                          │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                              │                                               │
│                              ▼                                               │
│  PASO 3: VERIFICACIÓN DE PROCEDENCIA                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  ¿Procedencia y condiciones originales están registradas?             │  │
│  │                                                                        │  │
│  │  SI SÍ: Continuar a PASO 4                                            │  │
│  │  SI NO: Aprendizaje sin procedencia, marcar como NOT_DETERMINED       │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                              │                                               │
│                              ▼                                               │
│  PASO 4: VERIFICACIÓN DE VIGENCIA                                            │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  ¿El aprendizaje sigue vigente respecto del sistema investigado?      │  │
│  │                                                                        │  │
│  │  Ejemplo: Aprendizaje sobre kernel 6.5 puede no ser vigente en 6.8    │  │
│  │                                                                        │  │
│  │  SI VIGENTE: Continuar a PASO 5                                       │  │
│  │  SI NO VIGENTE: Aprendizaje obsoleto, NO recuperar                    │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                              │                                               │
│                              ▼                                               │
│  PASO 5: REEVALUACIÓN DE AFIRMACIONES                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  ¿Las afirmaciones dependientes de condiciones cambiantes siguen      │  │
│  │  siendo válidas?                                                      │  │
│  │                                                                        │  │
│  │  SI SÍ: Recuperar aprendizaje                                         │  │
│  │  SI NO: Reevaluar antes de recuperar                                  │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                              │                                               │
│                              ▼                                               │
│  PASO 6: DISTINCIÓN APRENDIZAJE/CONOCIMIENTO                                 │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  ¿Es aprendizaje reutilizable o conocimiento demostrado?              │  │
│  │                                                                        │  │
│  │  Aprendizaje reutilizable: Puede aplicarse en contextos similares     │  │
│  │  Conocimiento demostrado: Probado dentro de alcance definido          │  │
│  │                                                                        │  │
│  │  Marcar tipo antes de recuperar                                       │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Contrato de invocación

AGUA → ROUTER: solicitar **capacidad**, no nombre de herramienta. La abstracción se demuestra por interfaces y ejecuciones reales.

### Frontera AGUA/TIERRA

El diagrama no traza la frontera entre «aprendizaje reutilizable» (AGUA) y «evidencia/afirmaciones auditables» (TIERRA). Queda como ausencia (§22 #5).

### Casilla de audit

Verificar existencia, procedencia, revalidación al recuperar. FASE 1 reporta PARTIAL/AUSENTE según contrato. **Pendiente de corroboración** por artefactos.

---

## §7. ROUTER de capacidades

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    ROUTER DE CAPACIDADES                                     │
│           (busca capacidades, no nombres de herramientas)                    │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────┬──────────────────────┬──────────────────────┐     │
│  │ binary.functions      │ source.semantic_search│ runtime.trace        │     │
│  │ binary.disassemble    │                       │                       │     │
│  │ binary.xrefs          │                       │                       │     │
│  │ (Rizin, Ghidra,      │ (Coccinelle,          │ (GDB, LLDB, Frida,  │     │
│  │  Capstone)            │  Tree-sitter)         │  perf)                │     │
│  └──────────────────────┴──────────────────────┴──────────────────────┘     │
│                                                                              │
│  ┌──────────────────────┐                                                   │
│  │ formal.check          │                                                   │
│  │                       │                                                   │
│  │ (Z3, CBMC)            │                                                   │
│  └──────────────────────┘                                                   │
│                                                                              │
│  FASE 1 reporta: dispatch.py como mapa, no contrato; PARTIAL                 │
│  PENDIENTE DE CORROBORACIÓN                                                  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Qué representa

Resolvedor de capacidades. Regla: **solicitar capacidad, seleccionar backend adecuado**, no acoplar la investigación a un nombre de herramienta.

### Familias de capacidad — tabla expandida

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    FAMILIAS DE CAPACIDAD (DETALLE)                           │
├────────────────────────┬─────────────────────┬──────────────────────────────┤
│ Capacidad              │ Backends citados    │ Propósito                    │
├────────────────────────┼─────────────────────┼──────────────────────────────┤
│ binary.functions        │ Rizin, Ghidra,      │ Identificación de funciones  │
│                         │ Capstone            │ en binarios ELF/DWARF        │
├────────────────────────┼─────────────────────┼──────────────────────────────┤
│ binary.disassemble      │ Compatibles         │ Desensamblado de código      │
│                         │                     │ máquina a assembly           │
├────────────────────────┼─────────────────────┼──────────────────────────────┤
│ binary.xrefs            │ Compatibles         │ Referencias cruzadas entre   │
│                         │                     │ funciones y datos            │
├────────────────────────┼─────────────────────┼──────────────────────────────┤
│ source.semantic_search  │ Coccinelle,         │ Búsqueda semántica en código │
│                         │ Tree-sitter         │ fuente (patrones, no regex)  │
├────────────────────────┼─────────────────────┼──────────────────────────────┤
│ runtime.trace           │ GDB, LLDB, Frida,   │ Observación de ejecución en  │
│                         │ perf                │ tiempo real                  │
├────────────────────────┼─────────────────────┼──────────────────────────────┤
│ formal.check            │ Z3, CBMC            │ Verificación formal de       │
│                         │                     │ propiedades                  │
└────────────────────────┴─────────────────────┴──────────────────────────────┘

NOTA: Los nombres son EJEMPLOS; no implican instalación, conexión ni
disponibilidad.
```

### Contrato de resolución — flujo detallado

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    CONTRATO DE RESOLUCIÓN DE ROUTER                          │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PASO 1: RECIBIR SOLICITUD                                                   │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Interfaz recibe:                                                     │  │
│  │  ├── Capacidad solicitada (ej: binary.functions)                      │  │
│  │  ├── Parámetros (ej: archivo=driver_rx550.ko, formato=json)          │  │
│  │  └── Precondiciones (ej: requiere_binario=true)                       │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                              │                                               │
│                              ▼                                               │
│  PASO 2: IDENTIFICAR BACKENDS COMPATIBLES                                    │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Buscar backends que soporten la capacidad solicitada                 │  │
│  │                                                                        │  │
│  │  Ejemplo: binary.functions → [rizin, ghidra, capstone]                │  │
│  │                                                                        │  │
│  │  SI no hay backends: Informar por qué no puede                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                              │                                               │
│                              ▼                                               │
│  PASO 3: SELECCIONAR POR CRITERIOS DECLARADOS                                │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Criterios de selección:                                              │  │
│  │  ├── Disponibilidad (¿está instalado?)                                │  │
│  │  ├── Costo (tiempo, recursos)                                         │  │
│  │  ├── Precisión (calidad del resultado)                                │  │
│  │  ├── Cobertura (qué puede y qué no puede)                             │  │
│  │  └── Compatibilidad con parámetros                                    │  │
│  │                                                                        │  │
│  │  PROBLEMA: El diagrama NO especifica criterios (§22 #4)               │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                              │                                               │
│                              ▼                                               │
│  PASO 4: EJECUTAR O INFORMAR FALLO                                           │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  SI backend seleccionado está disponible:                             │  │
│  │  ├── Ejecutar con parámetros                                          │  │
│  │  └── Continuar a PASO 5                                               │  │
│  │                                                                        │  │
│  │  SI backend falla:                                                    │  │
│  │  ├── Intentar con otro backend compatible (si existe)                 │  │
│  │  └── O informar por qué no puede                                      │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                              │                                               │
│                              ▼                                               │
│  PASO 5: DEVOLVER RESULTADO CON PROCEDENCIA                                  │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Resultado incluye:                                                   │  │
│  │  ├── Output de la ejecución                                           │  │
│  │  ├── Procedencia del backend (nombre, versión)                        │  │
│  │  ├── Argumentos utilizados                                            │  │
│  │  ├── Limitaciones conocidas                                           │  │
│  │  └── Timestamp de ejecución                                           │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  REGLA CRÍTICA:                                                              │
│  Un mapa con backend_por_defecto NO demuestra resolución dinámica ni         │
│  selección contractual.                                                      │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Casilla de audit

Verificar interfaz de capacidades, selección, comportamiento ante fallo de backend, procedencia reproducible. FASE 1 reporta `dispatch.py` como mapa, no contrato; PARTIAL. **Pendiente de corroboración.**

---

## §8. MUNDO REAL

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                            MUNDO REAL                                        │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  código fuente · binarios ELF/DWARF · procesos                        │  │
│  │  memoria · hardware MMIO · PCIe                                       │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  FASE 1 reporta: rz_functions.py y rz_container.py para binarios;            │
│  los demás dominios como NOT_DETERMINED                                      │
│  PENDIENTE DE CORROBORACIÓN                                                  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Qué representa

Los 6 dominios sobre los que la plataforma investiga:

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    DOMINIOS DEL MUNDO REAL (DETALLE)                         │
├────────────────────────┬──────────────────────────────────────────────────────┤
│ Dominio                │ Descripción y alcance                                │
├────────────────────────┼──────────────────────────────────────────────────────┤
│ 1. Código fuente       │ Estructuras, declaraciones, operaciones.             │
│                        │ Herramientas: Tree-sitter, Coccinelle               │
│                        │ Evidencia: AST, patrones semánticos                  │
├────────────────────────┼──────────────────────────────────────────────────────┤
│ 2. Binarios ELF/DWARF  │ Código ejecutable y metadatos de depuración.        │
│                        │ Herramientas: Rizin, Ghidra, Capstone               │
│                        │ Evidencia: Funciones, desensamblado, xrefs           │
├────────────────────────┼──────────────────────────────────────────────────────┤
│ 3. Procesos            │ Comportamiento en ejecución.                         │
│                        │ Herramientas: GDB, LLDB, perf                       │
│                        │ Evidencia: Trazas, estados, llamadas al sistema      │
├────────────────────────┼──────────────────────────────────────────────────────┤
│ 4. Memoria             │ Regiones, contenidos, accesos observables dentro    │
│                        │ de permisos.                                         │
│                        │ Herramientas: GDB, /proc/meminfo, Frida             │
│                        │ Evidencia: Dump de memoria, patrones de acceso       │
├────────────────────────┼──────────────────────────────────────────────────────┤
│ 5. Hardware MMIO       │ Registros y regiones mapeadas accesibles.           │
│                        │ Herramientas: devmem, iomem, lspci                  │
│                        │ Evidencia: Valores de registros, estados de hardware │
├────────────────────────┼──────────────────────────────────────────────────────┤
│ 6. PCIe                │ Dispositivos, configuración, conexiones observables.│
│                        │ Herramientas: lspci, setpci, sysfs                  │
│                        │ Evidencia: Configuración de dispositivos, enlaces    │
└────────────────────────┴──────────────────────────────────────────────────────┘
```

### Implicación arquitectónica

ROUTER resuelve **contra artefactos o sistemas concretos**, no contra nombres abstractos. Para cada dominio deben identificarse backends, requisitos de acceso, limitaciones y tipos de evidencia.

La presencia de una herramienta de análisis de binarios **no demuestra** cobertura de procesos, memoria o hardware.

### Casilla de audit

Evaluar cada dominio por separado. FASE 1 reporta `rz_functions.py` y `rz_container.py` para binarios; los demás dominios como NOT_DETERMINED. **Pendiente de corroboración.**

---

## §9. Schema del claim

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                            SCHEMA DEL CLAIM                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  id                      │ Identificador único                         │  │
│  │  statement               │ Afirmación atómica                          │  │
│  │  object_hash             │ Hash del artefacto al que se refiere        │  │
│  │  scope                   │ Delimitación temporal/funcional/componente  │  │
│  │  epistemic_state         │ Uno de los 6 estados, CALCULADO             │  │
│  │  evidence_refs[]         │ Referencias a evidencia (no copias)         │  │
│  │  derivation_refs[]       │ Cadena de derivación                        │  │
│  │  contradiction_refs[]    │ Referencias a contradicciones               │  │
│  │  falsification_test      │ Prueba de refutación. OBLIGATORIA           │  │
│  │  unresolved_obligations[]│ Obligaciones pendientes                     │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  FASE 1 reporta: schemas.py con 19 checks                                     │
│  PENDIENTE DE CORROBORACIÓN por examen del archivo y de los checks           │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Qué representa

El claim es la **unidad atómica** del grafo. El schema tiene **10 campos**; no hay campo decorativo.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    CAMPOS DEL SCHEMA (DETALLE COMPLETO)                      │
├──────┬──────────────────────┬────────────────────────────────────────────────┤
│  #   │ Campo                │ Función contractual                            │
├──────┼──────────────────────┼────────────────────────────────────────────────┤
│  1   │ id                   │ Único dentro del ámbito definido.              │
│      │                      │ Sin id, no hay referencia posible.             │
├──────┼──────────────────────┼────────────────────────────────────────────────┤
│  2   │ statement            │ Afirmación atómica. Si tiene «y», son dos     │
│      │                      │ claims. Debe ser falsable.                    │
├──────┼──────────────────────┼────────────────────────────────────────────────┤
│  3   │ object_hash          │ Integridad del artefacto al que se refiere,   │
│      │                      │ cuando corresponda. No siempre aplica.        │
├──────┼──────────────────────┼────────────────────────────────────────────────┤
│  4   │ scope                │ Delimitación temporal/funcional/componente.   │
│      │                      │ Sin scope, el claim es ambiguo.               │
├──────┼──────────────────────┼────────────────────────────────────────────────┤
│  5   │ epistemic_state      │ Uno de los 6 estados, CALCULADO, no declarado.│
│      │                      │ No se asigna manualmente.                     │
├──────┼──────────────────────┼────────────────────────────────────────────────┤
│  6   │ evidence_refs[]      │ Referencias a evidencia (no copias).          │
│      │                      │ Permite trazabilidad sin duplicación.         │
├──────┼──────────────────────┼────────────────────────────────────────────────┤
│  7   │ derivation_refs[]    │ Cadena de derivación.                         │
│      │                      │ Permite reconstruir cómo se llegó al claim.   │
├──────┼──────────────────────┼────────────────────────────────────────────────┤
│  8   │ contradiction_refs[] │ Referencias a contradicciones (evento, no     │
│      │                      │ estado).                                      │
├──────┼──────────────────────┼────────────────────────────────────────────────┤
│  9   │ falsification_test   │ Prueba de refutación. OBLIGATORIA.            │
│      │                      │ Describe condición comprobable.               │
├──────┼──────────────────────┼────────────────────────────────────────────────┤
│  10  │ unresolved_          │ Obligaciones pendientes.                      │
│      │ obligations[]        │ No vacío → no puede ser PROVEN pleno.        │
└──────┴──────────────────────┴────────────────────────────────────────────────┘
```

### Restricciones propuestas

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    RESTRICCIONES DEL SCHEMA                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  R1: SCOPE OBLIGATORIO                                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Sin scope definido → debe declararse esa limitación.                 │  │
│  │  No se permite claim sin scope.                                       │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  R2: HASH NO FICTICIO                                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Ausencia de hash → no se resuelve con hash ficticio; determinar si   │  │
│  │  el tipo de afirmación exige artefacto identificable.                 │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  R3: PROVEN NO AUTOMÁTICO                                                    │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  PROVEN NO se asigna por tener evidencia; requiere prueba relevante   │  │
│  │  ejecutada y ausencia de contradicciones críticas sin resolver.       │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  R4: FALSIFICATION_TEST NO ES EJECUCIÓN                                      │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  falsification_test describe condición comprobable; su existencia no  │  │
│  │  demuestra que se haya ejecutado.                                     │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  R5: OBLIGACIONES PENDIENTES                                                 │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  unresolved_obligations[] no vacío → no puede ser PROVEN pleno; a lo  │  │
│  │  sumo PARTIAL.                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Regla de aplicabilidad del `object_hash`

La exigencia universal de `object_hash` necesita matiz: algunas afirmaciones refieren a relaciones, ejecuciones o conjuntos de artefactos y requieren otro modelo de identificación. El audit debe determinar si el schema cubre esos casos o si exige ampliación.

### Casilla de audit

Verificar schema efectivo, validación de campos, restricciones, referencias y reglas de cálculo del estado. FASE 1 reporta `schemas.py` con 19 checks; **pendiente de corroboración** por examen del archivo y de los checks individuales.

---

## §10. Concurrencia por operación (no global) `[v3]`

> **Errata §0.1 #1:** el diagrama dice «Los dos coexisten» pero enumera **tres** mecanismos. Se trata como tres.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    CONCURRENCIA POR OPERACIÓN [v3]                           │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  OPERACIÓN             │ MECANISMO              │ INVARIANTE          │  │
│  ├────────────────────────┼────────────────────────┼─────────────────────┤  │
│  │ actualizar estado      │ optimistic             │ Detectar           │  │
│  │                        │ (version + row_count)  │ actualizaciones    │  │
│  │                        │                        │ concurrentes       │  │
│  ├────────────────────────┼────────────────────────┼─────────────────────┤  │
│  │ agregar evidencia      │ append, sin lock       │ Conservar todas    │  │
│  │                        │ sobre el claim         │ las adiciones      │  │
│  │                        │                        │ válidas            │  │
│  ├────────────────────────┼────────────────────────┼─────────────────────┤  │
│  │ reevaluación           │ pessimistic            │ Evitar             │  │
│  │                        │ (locked_by + expires)  │ reevaluaciones     │  │
│  │                        │                        │ simultáneas        │  │
│  └────────────────────────┴────────────────────────┴─────────────────────┘  │
│                                                                              │
│  FASE 1 reporta: mutación #3 (LOCK_GLOBAL) con 2 fallos                     │
│  PENDIENTE DE CORROBORACIÓN por examen de mutación, alcance y causas         │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Qué representa

Tres clases de operación, tres mecanismos de coordinación. La necesidad de cada mecanismo depende del modelo de almacenamiento, transacciones y patrones de concurrencia observados.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    MECANISMOS DE CONCURRENCIA (DETALLE)                      │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  MECANISMO 1: OPTIMISTIC (ACTUALIZAR ESTADO)                                 │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │  Flujo:                                                                │  │
│  │  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐            │  │
│  │  │ Leer    │───►│ Modificar│───►│ Verificar│───►│ Escribir│            │  │
│  │  │ version │    │ estado  │    │ version  │    │ si OK   │            │  │
│  │  │ actual  │    │         │    │          │    │         │            │  │
│  │  └─────────┘    └─────────┘    └────┬────┘    └─────────┘            │  │
│  │                                     │                                  │  │
│  │                                     │ SI version cambió:              │  │
│  │                                     ▼                                  │  │
│  │                                ┌─────────┐                             │  │
│  │                                │Conflicto│                             │  │
│  │                                │detectado│                             │  │
│  │                                └─────────┘                             │  │
│  │                                                                        │  │
│  │  OBLIGACIÓN: Detectar actualizaciones concurrentes incompatibles;     │  │
│  │  evitar sobrescrituras silenciosas.                                   │  │
│  │                                                                        │  │
│  │  CONDICIONES:                                                          │  │
│  │  ├── version cambia según regla documentada                           │  │
│  │  ├── row_count se interpreta según operación y garantías              │  │
│  │  │   transaccionales                                                  │  │
│  │  └── row_count == 0 PUEDE indicar conflicto, pero NO DEBE             │  │
│  │      traducirse automáticamente en reintento infinito                 │  │
│  │                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  MECANISMO 2: APPEND (AGREGAR EVIDENCIA)                                     │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │  Flujo:                                                                │  │
│  │  ┌─────────┐    ┌─────────┐    ┌─────────┐                            │  │
│  │  │ Nueva   │───►│ INSERT  │───►│ Sin lock│                            │  │
│  │  │evidencia│    │ (no     │    │ sobre el│                            │  │
│  │  │         │    │ UPDATE) │    │ claim   │                            │  │
│  │  └─────────┘    └─────────┘    └─────────┘                            │  │
│  │                                                                        │  │
│  │  OBLIGACIÓN: Conservar todas las adiciones válidas; evitar pérdidas   │  │
│  │  o duplicaciones.                                                     │  │
│  │                                                                        │  │
│  │  CONDICIONES:                                                          │  │
│  │  ├── Append mantiene restricciones de integridad y relaciones         │  │
│  │  └── No requiere lock sobre el claim                                  │  │
│  │                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  MECANISMO 3: PESSIMISTIC (REEVALUACIÓN)                                     │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │  Flujo:                                                                │  │
│  │  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐            │  │
│  │  │Solicitar│───►│Adquirir │───►│Reevaluar│───►│Liberar  │            │  │
│  │  │lock     │    │lock     │    │claim    │    │lock     │            │  │
│  │  │         │    │         │    │         │    │         │            │  │
│  │  └─────────┘    └─────────┘    └─────────┘    └─────────┘            │  │
│  │                                                                        │  │
│  │  OBLIGACIÓN: Evitar reevaluaciones simultáneas incompatibles;         │  │
│  │  recuperar bloqueos abandonados.                                      │  │
│  │                                                                        │  │
│  │  CONDICIONES:                                                          │  │
│  │  ├── Reglas de adquisición, renovación, expiración y recuperación     │  │
│  │  ├── locked_by identifica quién tiene el lock                         │  │
│  │  └── expires previene locks huérfanos                                 │  │
│  │                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  PRUEBA BAJO CONCURRENCIA REAL:                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Los tres mecanismos DEBEN probarse bajo concurrencia real,           │  │
│  │  incluidos fallos y reintentos.                                       │  │
│  │                                                                        │  │
│  │  Un test que pase sin concurrencia NO demuestra corrección.           │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Casilla de audit

Comprobar los tres mecanismos y que las pruebas **distingan** de una implementación incorrecta (no basta test que pase). FASE 1 reporta mutación #3 (`LOCK_GLOBAL`) con 2 fallos. **Pendiente de corroboración** por examen de mutación, alcance y causas de los dos fallos.

---

## §11. EVIDENCE — inmutabilidad como mecanismo `[v3]`

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    EVIDENCE: INMUTABILIDAD [v3]                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  INMUTABILIDAD COMO MECANISMO, NO COMO FLAG                           │  │
│  │                                                                        │  │
│  │  Un flag es convención (if not deleted: ...);                         │  │
│  │  un mecanismo es restricción estructural (motor o permiso impide la   │  │
│  │  operación).                                                          │  │
│  │                                                                        │  │
│  │  La diferencia: un flag se olvida; un mecanismo no.                   │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  LOS 4 MECANISMOS:                                                           │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  1. APPEND-ONLY: Nunca modifica in-place                              │  │
│  │     Toda escritura es INSERT, no UPDATE sobre evidencia existente     │  │
│  │     INSERT OR REPLACE PUEDE sustituir según restricciones y motor;    │  │
│  │     debe examinarse el caso concreto antes de concluir violación      │  │
│  ├────────────────────────────────────────────────────────────────────────┤  │
│  │  2. BORRADO RESTRINGIDO: Permiso a nivel de motor o autorización      │  │
│  │     impide DELETE                                                     │  │
│  │     La ausencia de triggers no basta para afirmar que el borrado sea  │  │
│  │     posible: revisar permisos, restricciones, interfaces              │  │
│  ├────────────────────────────────────────────────────────────────────────┤  │
│  │  3. HASH DE FILA VERIFICADO AL LEER: Recomputar y comparar con        │  │
│  │     declarado                                                         │  │
│  │     Sin esto, modificación silenciosa pasa desapercibida hasta         │  │
│  │     auditoría                                                         │  │
│  ├────────────────────────────────────────────────────────────────────────┤  │
│  │  4. SUPERSEDES_REF: Corrección como nuevo registro que referencia al  │  │
│  │     anterior; ambos se conservan                                      │  │
│  │     La anterior NO se borra                                           │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  FASE 1 reporta: mutación #5 (borrar dos triggers de evidence) con 1 fallo  │
│  PENDIENTE DE CORROBORACIÓN                                                  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Qué significa «mecanismo, no flag»

Un flag es convención (`if not deleted: ...`); un mecanismo es restricción estructural (motor o permiso impide la operación). **La diferencia: un flag se olvida; un mecanismo no.**

### Implicaciones

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    IMPLICACIONES DE INMUTABILIDAD                            │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. INSERT OR REPLACE no es violación per se; depende del comportamiento     │
│     del motor y de las restricciones. store.py:870 reportado por FASE 1     │
│     debe examinarse caso por caso.                                          │
│                                                                              │
│  2. 0 triggers no equivale a «borrado posible». Revisar permisos,           │
│     interfaces, restricciones.                                              │
│                                                                              │
│  3. La inmutabilidad se DEMUESTRA por pruebas que intentan modificar,        │
│     sustituir y borrar, no por declaración.                                 │
│                                                                              │
│  4. La corrección de evidencia NO es modificación: es nueva evidencia con    │
│     supersedes_ref.                                                         │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Casilla de audit

Ejecutar pruebas que **intenten** modificar, sustituir y borrar; alterar contenido almacenado; verificar relaciones de corrección. FASE 1 reporta mutación #5 (borrar dos triggers de `evidence`) con 1 fallo. **Pendiente de corroboración.**

---

## §12. Estados epistémicos — 6 estados `[v3]`

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    ESTADOS EPISTÉMICOS (6 ESTADOS) [v3]                      │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────┐  ┌──────────┐  ┌────────────────┐  ┌───────────────┐        │
│   │  PROVEN  │  │ PARTIAL  │  │ NOT_DETERMINED │  │ PROVEN_ABSENT │        │
│   └──────────┘  └──────────┘  └────────────────┘  └───────────────┘        │
│                                                                              │
│   ┌──────────┐  ┌────────────────┐                                          │
│   │ DEFERRED │  │  INVALIDATED   │                                          │
│   └──────────┘  └────────────────┘                                          │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Definiciones

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    DEFINICIONES DE ESTADOS (DETALLE)                         │
├────────────────────┬──────────────────────────────────────────────────────────┤
│ Estado             │ Significado y criterio general                           │
├────────────────────┼──────────────────────────────────────────────────────────┤
│ PROVEN             │ Respaldada dentro de alcance definido; superó pruebas   │
│                    │ pertinentes.                                             │
│                    │                                                          │
│                    │ Criterio: Evidencia suficiente + prueba relevante       │
│                    │ ejecutada + sin contradicciones críticas pendientes.    │
├────────────────────┼──────────────────────────────────────────────────────────┤
│ PARTIAL            │ Evidencia respalda parte del alcance u obligaciones     │
│                    │ abiertas.                                                │
│                    │                                                          │
│                    │ Criterio: Cobertura y obligaciones identificadas        │
│                    │ explícitamente.                                          │
├────────────────────┼──────────────────────────────────────────────────────────┤
│ NOT_DETERMINED     │ Se buscó; ni a favor ni en contra.                      │
│                    │                                                          │
│                    │ Criterio: Búsqueda/evaluación documentada; evidencia    │
│                    │ insuficiente o ambigua.                                  │
├────────────────────┼──────────────────────────────────────────────────────────┤
│ PROVEN_ABSENT      │ Ausencia demostrada dentro de alcance definido.         │
│                    │                                                          │
│                    │ Criterio: Búsqueda y evidencia negativa suficientes     │
│                    │ para ese alcance.                                        │
├────────────────────┼──────────────────────────────────────────────────────────┤
│ DEFERRED           │ No evaluada o pospuesta explícitamente.                 │
│                    │                                                          │
│                    │ Criterio: Motivo o condición pendiente registrada.      │
├────────────────────┼──────────────────────────────────────────────────────────┤
│ INVALIDATED        │ Respaldada anteriormente; dejó de estarlo tras          │
│                    │ reevaluación documentada.                                │
│                    │                                                          │
│                    │ Criterio: Evidencia contradictoria suficiente +         │
│                    │ decisión registrada.                                     │
└────────────────────┴──────────────────────────────────────────────────────────┘

ESTOS ESTADOS NO SE CONFUNDEN con estado de ejecución de prueba (§12.2) ni con
nivel de cobertura.
```

### 12.1 INVALIDATED no es automático `[v3]`

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    INVALIDATED: FLUJO DE REEVALUACIÓN                        │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐                                                         │
│  │  Contradicción  │                                                         │
│  │  detectada      │                                                         │
│  └────────┬────────┘                                                         │
│           │                                                                  │
│           ▼                                                                  │
│  ┌─────────────────┐                                                         │
│  │  Reevaluación   │                                                         │
│  │  documentada    │                                                         │
│  └────────┬────────┘                                                         │
│           │                                                                  │
│           ├──────────────────────────────────────────────────────────┐       │
│           │                                                          │       │
│           ▼                                                          ▼       │
│  ┌─────────────────┐                                        ┌──────────────┐│
│  │  INVALIDATED    │                                        │  PROVEN      ││
│  │                 │                                        │  (si la      ││
│  │  La contradicción│                                       │  contradicción││
│  │  es válida y    │                                        │  se refuta)  ││
│  │  suficiente     │                                        │              ││
│  └─────────────────┘                                        └──────────────┘│
│                                                                              │
│           │                                                                  │
│           ▼                                                                  │
│  ┌─────────────────┐                                                         │
│  │  Otro estado    │                                                         │
│  │  (si evidencia  │                                                         │
│  │  sigue          │                                                         │
│  │  insuficiente)  │                                                         │
│  └─────────────────┘                                                         │
│                                                                              │
│  REGLA: Una contradicción DESENCADENA reevaluación; no invalida por sí sola.│
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 12.2 Tres conceptos separados

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    TRES CONCEPTOS SEPARADOS                                  │
├────────────────────┬──────────────────────────────────────────────────────────┤
│ Concepto           │ Significado y requisito                                  │
├────────────────────┼──────────────────────────────────────────────────────────┤
│ Evento de          │ Registro de incompatibilidad entre afirmaciones/       │
│ contradicción      │ evidencias.                                             │
│                    │                                                          │
│                    │ Requisito: Conservar procedencia y contexto.            │
├────────────────────┼──────────────────────────────────────────────────────────┤
│ Severidad          │ Impacto sobre afirmaciones afectadas.                   │
│                    │                                                          │
│                    │ Requisito: Regla de cálculo o clasificación explícita.  │
├────────────────────┼──────────────────────────────────────────────────────────┤
│ Estado de prueba   │ Resultado de un test.                                   │
│                    │                                                          │
│                    │ Valores: PASS / FAIL / NOT_RUN / NOT_DETERMINED        │
└────────────────────┴──────────────────────────────────────────────────────────┘

COLAPSARLOS convierte una contradicción en «el claim está mal» sin reevaluación.
La separación permite registrar sin invalidar, calcular severidad sin decidir
estado, y distinguir «el test falló» de «el claim es falso».
```

### Casilla de audit

Comprobar representación, transiciones permitidas, tratamiento de contradicciones, separación estado de prueba / estado epistemológico. FASE 1 reporta: repo real con 5 estados, sin `INVALIDATED`; andamiaje con mutación #2 (contradicción invalida sola) → 1 fallo. **Ambas pendientes de corroboración.**

---

## §13. Tres capas del hash — separadas `[v3]`

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    TRES CAPAS DEL HASH [v3]                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  CAPA 1: INTEGRIDAD                                                          │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Pregunta: ¿hash actual == hash declarado?                            │  │
│  │  Resultado: PASS / FAIL                                               │  │
│  │                                                                        │  │
│  │  Significado: Contenido coincide con referencia declarada.            │  │
│  │  Limitación: NO demuestra origen.                                     │  │
│  │                                                                        │  │
│  │  Ejemplo: sha256(archivo) == sha256_declarado                         │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                              │                                               │
│                              ▼                                               │
│  CAPA 2: AUTENTICIDAD                                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Pregunta: ¿coincide con referencia confiable?                        │  │
│  │  Resultado: PASS / NOT_DETERMINED                                     │  │
│  │                                                                        │  │
│  │  Significado: Corresponde a referencia con confianza justificada      │  │
│  │  (firma verificable, fuente independiente).                           │  │
│  │  Limitación: Sin referencia confiable → NOT_DETERMINED, nunca PASS    │  │
│  │  por defecto.                                                         │  │
│  │                                                                        │  │
│  │  Ejemplo: hash == hash_de_fuente_confiable                            │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                              │                                               │
│                              ▼                                               │
│  CAPA 3: VALIDEZ SEMÁNTICA                                                   │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Pregunta: ¿el artefacto dice lo que el claim afirma?                 │  │
│  │  Resultado: Requiere prueba SEPARADA                                  │  │
│  │                                                                        │  │
│  │  Significado: Evalúa si el contenido respalda la afirmación.          │  │
│  │  Limitación: Requiere análisis/pruebas específicas.                   │  │
│  │                                                                        │  │
│  │  Ejemplo: El binario realmente soporta 2GB de VRAM                    │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  REGLA CENTRAL:                                                              │
│  Un hash detecta cambios respecto de una referencia. Por sí solo NO          │
│  autentica el origen ni demuestra validez semántica.                         │
│                                                                              │
│  PROHIBIDO:                                                                  │
│  ├── autenticidad := integridad                                             │
│  ├── Deducir validez semántica del hash                                     │
│  └── PASS de autenticidad sin referencia confiable                          │
│                                                                              │
│  FASE 1 reporta: mutación #6 con 1 fallo                                    │
│  PENDIENTE DE CORROBORACIÓN                                                  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Casilla de audit

Comprobar las 3 capas diferenciadas en esquema e implementación, que autenticidad pueda ser NOT_DETERMINED, y que existan pruebas que detecten la confusión integridad/autenticidad. FASE 1 reporta mutación #6 con 1 fallo. **Pendiente de corroboración.**

---

## §14. Disciplina por paso

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    DISCIPLINA POR PASO                                       │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  EVIDENCE ──► SEMANTICS ──► SCHEMA ──► DISCRIMINATING TEST ──►             │
│      ▲                                                     │                │
│      │                                                     │                │
│      │                                                     ▼                │
│      │                                              IMPLEMENTATION          │
│      │                                                     │                │
│      │                                                     ▼                │
│      │                                               VALIDATION             │
│      │                                                     │                │
│      └──────────────────── evidencia nueva ◄───────────────┘                │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Los 6 pasos — detalle expandido

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    LOS 6 PASOS (DETALLE COMPLETO)                            │
├──────┬────────────────────┬──────────────────────────────────────────────────┤
│  #   │ Paso               │ Obligación                                       │
├──────┼────────────────────┼──────────────────────────────────────────────────┤
│  1   │ EVIDENCE           │ Identificar evidencia disponible, procedencia,   │
│      │                    │ limitaciones.                                    │
│      │                    │                                                  │
│      │                    │ PASS: Evidencia con procedencia y limitaciones   │
│      │                    │ FAIL: Evidencia sin procedencia                  │
│      │                    │ NOT_DETERMINED: No hay evidencia                 │
├──────┼────────────────────┼──────────────────────────────────────────────────┤
│  2   │ SEMANTICS          │ Determinar qué significa la evidencia y qué      │
│      │                    │ conclusiones permite.                            │
│      │                    │                                                  │
│      │                    │ PASS: Interpretación documentada con límites     │
│      │                    │ FAIL: Interpretación sin límites                 │
│      │                    │ NOT_DETERMINED: No hay interpretación            │
├──────┼────────────────────┼──────────────────────────────────────────────────┤
│  3   │ SCHEMA             │ Definir representación y restricciones.          │
│      │                    │                                                  │
│      │                    │ PASS: Schema con restricciones explícitas        │
│      │                    │ FAIL: Schema sin restricciones                   │
│      │                    │ NOT_DETERMINED: No hay schema                    │
├──────┼────────────────────┼──────────────────────────────────────────────────┤
│  4   │ DISCRIMINATING     │ Diseñar prueba que distinga comportamiento       │
│      │ TEST               │ esperado de alternativa incorrecta relevante.   │
│      │                    │                                                  │
│      │                    │ PASS: Prueba que distingue comportamiento        │
│      │                    │ FAIL: Prueba que no distingue                    │
│      │                    │ NOT_DETERMINED: No hay prueba                    │
├──────┼────────────────────┼──────────────────────────────────────────────────┤
│  5   │ IMPLEMENTATION     │ Implementar solo después de contrato + prueba;   │
│      │                    │ y con fase autorizada.                           │
│      │                    │                                                  │
│      │                    │ PASS: Implementación post-contrato y post-prueba │
│      │                    │ FAIL: Implementación sin contrato o prueba       │
│      │                    │ NOT_DETERMINED: No hay implementación            │
├──────┼────────────────────┼──────────────────────────────────────────────────┤
│  6   │ VALIDATION         │ Comprobar frente al contrato, incluidas          │
│      │                    │ limitaciones y efectos secundarios.              │
│      │                    │                                                  │
│      │                    │ PASS: Validación contra contrato con límites     │
│      │                    │ FAIL: Validación sin contrato                    │
│      │                    │ NOT_DETERMINED: No hay validación                │
└──────┴────────────────────┴──────────────────────────────────────────────────┘
```

### Ciclo

La validación puede producir evidencia nueva que obligue a revisar semántica, esquema, prueba o implementación. El proceso **no es pipeline irreversible**.

**La existencia de una prueba no demuestra que sea discriminante.** Debe identificarse el comportamiento incorrecto que detectaría, y verificarse que **realmente** lo detecta. Un test que nunca falló no es evidencia de nada.

### Casilla de audit

Comprobar si el proceso conserva la relación evidencia→decisión→prueba→implementación→validación. FASE 1 reporta `test_arquitectura_v3_03_mutacion.py` con 7 mutaciones; **pendiente de corroboración** por examen de scripts, artefactos mutados, salidas y correspondencia mutación↔propiedad.

---

## §15. Puerta global de entrada

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    PUERTA GLOBAL DE ENTRADA                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  AUDIT A-F ──► STATE=DELIVERED ──► REVISIÓN INDEPENDIENTE                   │
│                                          │                                   │
│                            ┌─────────────┴─────────────┐                     │
│                            ▼                           ▼                     │
│                       CONTESTED                    ACCEPTED                  │
│                            │                           │                     │
│                            │ [v3] ACCEPTED no es      │                     │
│                            │ string manual:           │                     │
│                            │ · artefactos íntegros    │                     │
│                            │ · 0 refutaciones críticas│                     │
│                            │ · revisor declara no     │                     │
│                            │   haber participado      │                     │
│                            │ · autoridad nombrada     │                     │
│                            ▼                           ▼                     │
│                    vuelve a CHALLENGED             ETAPA 1                   │
│                    con evidencia nueva        (bloqueada hasta aquí)         │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Flujo — detalle expandido

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    FLUJO DE PUERTA (DETALLE)                                 │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PASO 1: AUDIT A-F                                                           │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Evaluación de afirmaciones y contratos.                              │  │
│  │  Resultado: STATE=DELIVERED                                           │  │
│  │  DELIVERED ≠ ACCEPTED                                                 │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                              │                                               │
│                              ▼                                               │
│  PASO 2: STATE=DELIVERED                                                     │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Entregable disponible para revisión.                                 │  │
│  │  NO significa aceptado.                                               │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                              │                                               │
│                              ▼                                               │
│  PASO 3: REVISIÓN INDEPENDIENTE                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Revisor que NO participó en la construcción.                         │  │
│  │  Independencia debe definirse respecto del trabajo evaluado y de las  │  │
│  │  decisiones relevantes para su construcción.                          │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                              │                                               │
│                              ▼                                               │
│  PASO 4: RESULTADO                                                           │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  CONTESTED: Refutaciones encontradas                                  │  │
│  │  ├── Registrar refutaciones                                           │  │
│  │  ├── Aportar evidencia                                                │  │
│  │  └── Volver a someter                                                 │  │
│  │                                                                        │  │
│  │  ACCEPTED: Condiciones cumplidas                                      │  │
│  │  ├── Verificar las 4 condiciones                                      │  │
│  │  └── Habilitar etapa siguiente                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 15.1 Las 4 condiciones de ACCEPTED `[v3]`

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    4 CONDICIONES DE ACCEPTED [v3]                            │
├──────┬────────────────────────────┬──────────────────────────────────────────┤
│  #   │ Condición                  │ Verificación propuesta                   │
├──────┼────────────────────────────┼──────────────────────────────────────────┤
│  1   │ Artefactos íntegros        │ Recalcular hashes; contrastar con        │
│      │                            │ referencias apropiadas.                  │
│      │                            │                                          │
│      │                            │ PASS: Hash PASS en todo artefacto        │
│      │                            │ FAIL: Integridad no verificada           │
├──────┼────────────────────────────┼──────────────────────────────────────────┤
│  2   │ 0 refutaciones críticas    │ Revisar contradicciones y su estado.     │
│      │ pendientes                 │                                          │
│      │                            │ PASS: Registro de contradicciones        │
│      │                            │ resueltas                                │
│      │                            │ FAIL: Refutación pendiente               │
├──────┼────────────────────────────┼──────────────────────────────────────────┤
│  3   │ Independencia del revisor  │ Declaración verificable de no            │
│      │                            │ participación en la construcción         │
│      │                            │ evaluada.                                │
│      │                            │                                          │
│      │                            │ PASS: Declaración verificable            │
│      │                            │ FAIL: Sin declaración                    │
│      │                            │                                          │
│      │                            │ NOTA: Esta condición es la que el        │
│      │                            │ constructor NO puede cumplir. Requiere   │
│      │                            │ tercero; sin tercero, CONTESTED.         │
├──────┼────────────────────────────┼──────────────────────────────────────────┤
│  4   │ Autoridad identificada     │ Persona/rol autorizado registrado.       │
│      │                            │                                          │
│      │                            │ PASS: Persona/rol registrado             │
│      │                            │ FAIL: Sin autoridad                      │
└──────┴────────────────────────────┴──────────────────────────────────────────┘
```

### 15.2 ACCEPTED no es string manual

La aceptación **resulta de condiciones verificadas**, no de asignación arbitraria. FASE 1 reporta mutación #7 (`faltan = []`) con 7 fallos. **Pendiente de corroboración.**

### 15.3 Bloqueo de Etapa 1

`DELIVERED ≠ ACCEPTED`. La falta de refutaciones registradas **no equivale automáticamente** a revisión satisfactoria.

### Casilla de audit

Comprobar si existe puerta efectiva, si las 4 condiciones se verifican con evidencia, y si hay vía para aceptar sin cumplirlas.

---

## §16. Las 7 correcciones v3 — detalle con verificación

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    LAS 7 CORRECCIONES v3 (TABLA COMPLETA)                    │
├──────┬──────────────────────┬──────────────────────┬──────────────────────┬──────┐
│  #   │ Corrección           │ Contrato             │ Violación a detectar │ Fails│
├──────┼──────────────────────┼──────────────────────┼──────────────────────┼──────┤
│  1   │ ÉTER: 3 modos +      │ Tratamiento          │ Descarte silencioso  │  1   │
│      │ write-ahead          │ verificable de       │ o confirmación pese  │      │
│      │                      │ caída/saturación/    │ a fallar persistencia│      │
│      │                      │ reinicio; persistencia│                     │      │
│      │                      │ antes de confirmar;  │                      │      │
│      │                      │ idempotencia         │                      │      │
├──────┼──────────────────────┼──────────────────────┼──────────────────────┼──────┤
│  2   │ INVALIDATED con      │ Invalidación requiere│ Invalidación         │  1   │
│      │ reevaluación         │ reevaluación         │ automática por       │      │
│      │                      │ documentada          │ contradicción        │      │
├──────┼──────────────────────┼──────────────────────┼──────────────────────┼──────┤
│  3   │ Concurrencia por     │ Mecanismos           │ Sustitución por      │  2   │
│      │ operación            │ diferenciados        │ lock global          │      │
├──────┼──────────────────────┼──────────────────────┼──────────────────────┼──────┤
│  4   │ Rollback por         │ Recuperación en      │ Desaparición de      │  2   │
│      │ dispositivo          │ unidad de dispositivo│ restricción de       │      │
│      │                      │                      │ alcance              │      │
├──────┼──────────────────────┼──────────────────────┼──────────────────────┼──────┤
│  5   │ Inmutabilidad        │ Append-only +        │ Eliminación de       │  1   │
│      │ estructural          │ restricciones + hash │ mecanismos           │      │
│      │                      │ + supersedes_ref     │                      │      │
├──────┼──────────────────────┼──────────────────────┼──────────────────────┼──────┤
│  6   │ 3 capas del hash     │ Separación           │ Deducir autenticidad │  1   │
│      │                      │ integridad/          │ o validez del hash   │      │
│      │                      │ autenticidad/validez │                      │      │
├──────┼──────────────────────┼──────────────────────┼──────────────────────┼──────┤
│  7   │ ACCEPTED con         │ 4 condiciones        │ Aceptación sin       │  7   │
│      │ condiciones          │ verificadas;         │ evaluar              │      │
│      │                      │ independencia;       │                      │      │
│      │                      │ autoridad            │                      │      │
└──────┴──────────────────────┴──────────────────────┴──────────────────────┴──────┘

CONTROL REPORTADO: 89 PASS / 0 FAIL en versión correcta; 7/7 mutaciones detectadas.
```

### Interpretación de los resultados

Si se corroboran los artefactos, estos datos respaldarían que las pruebas distinguen las 7 mutaciones ensayadas. **No demostrarían por sí solos:**

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    LIMITACIONES DE LOS RESULTADOS                            │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ✗ Que el conjunto de mutaciones cubra todas las violaciones relevantes      │
│                                                                              │
│  ✗ Que los contratos estén implementados en los PRODUCTORES REALES          │
│    (no solo en andamiaje)                                                    │
│                                                                              │
│  ✗ Que las pruebas no compartan supuestos incorrectos con la implementación │
│                                                                              │
│  ✗ Que las capacidades funcionen en escenarios externos al andamiaje        │
│                                                                              │
│  ✗ Que el sistema completo satisfaga la arquitectura                        │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

**FASE 1 reporta** además que dos pasadas previas detectaron 5/7 porque los patrones de mutación no coincidían con el fuente, y que se corrigió hasta 7/7. Ese registro debe preservarse: un contraste que nunca falló no es evidencia.

---

## §17. Qué NO resuelve el diagrama

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    LO QUE EL DIAGRAMA NO RESUELVE                            │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ¿ÉTER existe?                       → audit                                │
│  ¿El schema tiene INVALIDATED?       → audit                                │
│  ¿El rollback es por device?         → audit                                │
│  ¿ACCEPTED tiene autoridad?          → audit                                │
│  ¿El hash distingue las 3?           → audit                                │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

**No es la lista completa.** La lista completa son **todas las casillas**: cajas, flechas, campos, condiciones, estados, restricciones, marcas `[v3]`.

**Distinción central:** diagrama = qué debería ser; audit = qué es. Ninguno reemplaza al otro.

---

## §18. Por qué no es «perfecto»

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    POR QUÉ NO ES PERFECTO                                    │
├──────┬──────────────────────────┬──────────────────────┬────────────────────┤
│  #   │ Condición                │ Fuente de            │ Límite del         │
│      │                          │ verificación         │ diagrama           │
├──────┼──────────────────────────┼──────────────────────┼────────────────────┤
│  1   │ Evaluar casillas         │ Audit A-F            │ El diagrama no     │
│      │                          │                      │ inspecciona ni     │
│      │                          │                      │ ejecuta el repo    │
├──────┼──────────────────────────┼──────────────────────┼────────────────────┤
│  2   │ Revisión independiente   │ Tercero              │ No certifica su    │
│      │                          │                      │ propia             │
│      │                          │                      │ independencia      │
├──────┼──────────────────────────┼──────────────────────┼────────────────────┤
│  3   │ Superar puerta Etapa 1   │ Artefactos y pruebas │ No ejecuta las     │
│      │                          │ de la puerta         │ condiciones        │
├──────┼──────────────────────────┼──────────────────────┼────────────────────┤
│  4   │ Experimentos A/B         │ Ejecuciones          │ No mide resultados │
│      │                          │ controladas y        │                    │
│      │                          │ métricas             │                    │
├──────┼──────────────────────────┼──────────────────────┼────────────────────┤
│  5   │ Evaluación de resultados │ Evidencia del mundo  │ No garantiza que   │
│      │                          │ real                 │ la hipótesis       │
│      │                          │                      │ resulte correcta   │
└──────┴──────────────────────────┴──────────────────────┴────────────────────┘
```

Las condiciones **conservan orden de dependencia**. Experimentos posteriores no se inician antes de satisfacer puertas previas.

---

## §19. Qué SÍ es este diagrama

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    QUÉ SÍ ES ESTE DIAGRAMA                                   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  El techo del diseño sin evidencia.                                         │
│  Lo que puede especificarse sin atribuir hechos no demostrados.             │
│  Lo que puede consolidarse sin inventar capacidades.                        │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

1. **Límite del diseño previo a la evidencia:** formula contratos y preguntas auditables; no demuestra implementación.
2. **Especificación sin atribución indebida:** cajas/flechas = responsabilidades propuestas; no comportamiento observado.
3. **Consolidación de las 7 correcciones:** identificadas para localizar y contrastar; su presencia en el documento no demuestra implementación.

**El próximo avance sustantivo** depende de artefactos del audit y de la revisión independiente, no de añadir diagramas o componentes especulativos.

---

## §20. Estado — desglose operativo

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    ESTADO OPERATIVO (DESGLOSE)                               │
├──────────────────────────────┬──────────────────────┬────────────────────────┤
│ Línea                        │ Significado          │ Condición para cambiar │
├──────────────────────────────┼──────────────────────┼────────────────────────┤
│ AUDIT A-F:                   │ Sin evidencia        │ Artefactos de          │
│ ESPERANDO ARTEFACTOS         │ suficiente en este   │ ejecución verificables │
│                              │ documento para       │                        │
│                              │ afirmar que el audit │                        │
│                              │ comenzó o concluyó   │                        │
├──────────────────────────────┼──────────────────────┼────────────────────────┤
│ INICIO:                      │ Punto de partida no  │ Registrar HEAD, rama,  │
│ NO CONFIRMADO                │ acreditado           │ baseline, condiciones  │
│                              │                      │ iniciales              │
├──────────────────────────────┼──────────────────────┼────────────────────────┤
│ ETAPA 1:                     │ No se ha demostrado  │ Revisión independiente │
│ BLOQUEADA                    │ cumplimiento de la   │ + aceptación conforme  │
│                              │ puerta               │ al contrato            │
├──────────────────────────────┼──────────────────────┼────────────────────────┤
│ IMPLEMENTACIÓN:              │ No existe            │ Autorización explícita │
│ NO AUTORIZADA                │ autorización         │ de la fase aplicable   │
│                              │ documentada para     │                        │
│                              │ modificar el repo    │                        │
│                              │ real                 │                        │
├──────────────────────────────┼──────────────────────┼────────────────────────┤
│ DIAGRAMAS:                   │ Versión documental   │ No requiere desbloqueo;│
│ v3+unificado                 │ consolidada          │ sí revisión si aparece │
│                              │                      │ evidencia contradictoria│
├──────────────────────────────┼──────────────────────┼────────────────────────┤
│ HIPÓTESIS — no verificado    │ Propiedades no       │ Evidencia suficiente + │
│                              │ demostradas          │ pruebas pertinentes +  │
│                              │                      │ revisión independiente │
├──────────────────────────────┼──────────────────────┼────────────────────────┤
│ PENDIENTE DE AUDIT           │ Casillas por evaluar │ Resolución documentada │
│                              │ individualmente      │ por casilla            │
└──────────────────────────────┴──────────────────────┴────────────────────────┘
```

**El estado de este documento no debe confundirse con el estado actual del repositorio.** Cambios de estado requieren evidencia nueva.

---

## §21. Tabla maestra de casillas auditables con criterio PASS/FAIL

**Reglas de uso:**

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    REGLAS DE USO DE LA TABLA MAESTRA                         │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. Cada casilla tiene ID estable, afirmación delimitada, criterio MÍNIMO   │
│     de PASS y evidencia refutadora (FAIL).                                  │
│                                                                              │
│  2. Si no hay evidencia suficiente para PASS ni FAIL → NOT_DETERMINED.     │
│                                                                              │
│  3. Búsqueda incompleta ≠ PROVEN_ABSENT.                                   │
│                                                                              │
│  4. Prueba no ejecutada ≠ PASS.                                            │
│                                                                              │
│  5. Mutación detectada solo respalda la propiedad concreta que esa          │
│     mutación discrimina.                                                    │
│                                                                              │
│  6. Estados de FASE 1 son ANTECEDENTES REPORTADOS; no se elevan a PROVEN   │
│     sin corroboración.                                                      │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### ALMA

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    CASILLAS DE ALMA                                          │
├──────┬──────────────────────────────┬──────────────────────┬─────────────────┬──────────┐
│  ID  │ Afirmación                   │ PASS mínimo          │ FAIL si…        │ FASE 1   │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────┤
│  A1  │ Criterio de cierre evaluable │ Función invocable    │ Solo hay        │ PARTIAL  │
│      │                              │ que retorna bool por │ declaración     │          │
│      │                              │ criterio             │ textual         │          │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────┤
│  A2  │ Propósito declarado y        │ Propósito            │ Sin vínculo     │ PARTIAL  │
│      │ vinculado                    │ referenciado por     │                 │          │
│      │                              │ criterios            │                 │          │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────┤
│  A3  │ ALMA no media sync           │ Planos operan sin    │ Planos dependen │ PARTIAL  │
│      │ obligatoriamente             │ llamada obligatoria  │ de ALMA por     │          │
│      │                              │ a ALMA               │ llamada sync    │          │
└──────┴──────────────────────────────┴──────────────────────┴─────────────────┴──────────┘
```

### ÉTER

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    CASILLAS DE ÉTER                                          │
├──────┬──────────────────────────────┬──────────────────────┬─────────────────┬──────────────┐
│  ID  │ Afirmación                   │ PASS mínimo          │ FAIL si…        │ FASE 1       │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  E1  │ Hub async, aislado de sync   │ Planos operan sin    │ ÉTER en camino  │ PARTIAL      │
│      │                              │ pasar por ÉTER       │ síncrono        │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  E2  │ Modo caída: RAM pierde,      │ Test que mata        │ Recupera algo   │ PROVEN_ABSENT│
│      │ disco sobrevive              │ proceso y verifica   │ desde RAM       │              │
│      │                              │ recuperación de      │                 │              │
│      │                              │ solo-disk            │                 │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  E3  │ Saturación con descarte      │ Contador consultable │ Descarte sin    │ PROVEN_ABSENT│
│      │ contado                      │ de descartes         │ registro        │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  E4  │ Reinicio: estado = persistido│ Test de reinicio     │ Estado          │ PROVEN_ABSENT│
│      │                              │ reproduce estado     │ inconsistente   │              │
│      │                              │ persistido           │                 │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  E5  │ Write-ahead con id único     │ Id asignado antes    │ Id post-        │ PROVEN_ABSENT│
│      │                              │ de disco             │ escritura       │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  E6  │ fsync antes de confirmación  │ Test que fuerza      │ Confirma sin    │ PROVEN_ABSENT│
│      │                              │ fallo de fsync y     │ fsync           │              │
│      │                              │ verifica no-         │                 │              │
│      │                              │ confirmación         │                 │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  E7  │ Idempotencia efectiva        │ Reenvío mismo id no  │ Efecto          │ PROVEN_ABSENT│
│      │                              │ produce doble efecto │ duplicado       │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  E8  │ Críticos siempre disco       │ Clasificación        │ Solo RAM para   │ PROVEN_ABSENT│
│      │                              │ explícita +          │ algún crítico   │              │
│      │                              │ enforcement          │                 │              │
└──────┴──────────────────────────────┴──────────────────────┴─────────────────┴──────────────┘
```

### AIRE

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    CASILLAS DE AIRE                                          │
├──────┬──────────────────────────────┬──────────────────────┬─────────────────┬──────────┐
│  ID  │ Afirmación                   │ PASS mínimo          │ FAIL si…        │ FASE 1   │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────┤
│ Ai1  │ Observabilidad transversal   │ Traza de ejecución   │ No hay traza    │ PARTIAL  │
│      │                              │ real reconstruible   │                 │          │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────┤
│ Ai2  │ Traza decisión→herramienta→  │ Los 3 tramos         │ Falta algún     │ PARTIAL  │
│      │ resultado                    │ presentes            │ tramo           │          │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────┤
│ Ai3  │ tool_hash verificable (si    │ Identidad reproducible│ Hash ausente o │ PARTIAL  │
│      │ obligatorio)                 │ del artefacto        │ no reproducible │          │
└──────┴──────────────────────────────┴──────────────────────┴─────────────────┴──────────┘
```

### TIERRA

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    CASILLAS DE TIERRA                                        │
├──────┬──────────────────────────────┬──────────────────────┬─────────────────┬──────────────┐
│  ID  │ Afirmación                   │ PASS mínimo          │ FAIL si…        │ FASE 1       │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  T1  │ Grafo de evidencia           │ Nodos + relaciones   │ No hay grafo    │ PARTIAL      │
│      │                              │ consultables         │                 │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  T2  │ Hash SHA-256 por artefacto   │ Cada artefacto con   │ Artefacto sin   │ PARTIAL      │
│      │                              │ hash calculado       │ hash            │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  T3  │ Procedencia productor→       │ Cadena reconstruible │ Eslabón perdido │ PARTIAL      │
│      │ transformación→consumidor    │                      │                 │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  T4  │ Contradicciones registradas  │ Registro append con  │ Contradicciones │ PARTIAL      │
│      │                              │ procedencia          │ descartadas     │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  T5  │ Schema claim 10 campos       │ Todos presentes,     │ Falta campo o   │ PARTIAL      │
│      │                              │ obligatorios         │ es opcional     │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  T6  │ Concurrencia por operación   │ Los 3 mecanismos     │ Lock global o   │ PROVEN_ABSENT│
│      │ (3)                          │ operativos           │ ausencia        │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  T7  │ Evidencia append-only        │ Test de UPDATE       │ UPDATE permitido│ PROVEN_ABSENT│
│      │                              │ in-place falla       │                 │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  T8  │ Restricción efectiva de      │ Test de DELETE falla │ DELETE exitoso  │ PROVEN_ABSENT│
│      │ borrado                      │ por permiso/motor    │                 │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  T9  │ Hash de fila verificado al   │ Test de alteración   │ Alteración pasa │ PROVEN_ABSENT│
│      │ leer                         │ detectada al leer    │                 │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│ T10  │ Corrección vía supersedes_ref│ Nuevo registro       │ Anterior borrado│ PROVEN_ABSENT│
│      │                              │ referencia al        │                 │              │
│      │                              │ anterior; ambos viven│                 │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│ T11  │ 6 estados incluido           │ Los 6 presentes      │ 5 o menos       │ PROVEN_ABSENT│
│      │ INVALIDATED                  │                      │                 │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│ T12  │ INVALIDATED no automático    │ Contradicción        │ Invalidación    │ PROVEN_ABSENT│
│      │                              │ dispara reevaluación,│ directa         │              │
│      │                              │ no invalidación      │                 │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│ T13  │ Separación evento/severidad/ │ 3 conceptos          │ Colapsados      │ PROVEN_ABSENT│
│      │ test                         │ representables por   │                 │              │
│      │                              │ separado             │                 │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│ T14  │ 3 capas hash separadas       │ Integridad/          │ Confundidas     │ PROVEN_ABSENT│
│      │                              │ autenticidad/validez │                 │              │
│      │                              │ distintas            │                 │              │
└──────┴──────────────────────────────┴──────────────────────┴─────────────────┴──────────────┘
```

### MENTE

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    CASILLAS DE MENTE                                         │
├──────┬──────────────────────────────┬──────────────────────┬─────────────────┬──────────────┐
│  ID  │ Afirmación                   │ PASS mínimo          │ FAIL si…        │ FASE 1       │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  M1  │ Hipótesis rivales cuando     │ Múltiples hipótesis  │ Solo una        │ NOT_DETERMINED│
│      │ corresponda                  │ distinguibles en     │ hipótesis sin   │              │
│      │                              │ casos relevantes     │ justificación   │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  M2  │ Causalidad con pruebas       │ Pruebas que          │ Solo correlación│ NOT_DETERMINED│
│      │ discriminantes               │ discriminan causas   │                 │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  M3  │ CFG cuando pertinente        │ Representación       │ No disponible   │ NOT_DETERMINED│
│      │                              │ disponible para      │                 │              │
│      │                              │ dominios que la      │                 │              │
│      │                              │ requieran            │                 │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  M4  │ Falsificación explícita      │ Cada claim con       │ Claim sin       │ PROVEN_ABSENT│
│      │                              │ falsification_test   │ refutación      │              │
│      │                              │ comprobable          │                 │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  M5  │ Sync MENTE↔CUERPO            │ Interfaz síncrona    │ No hay sync     │ NOT_DETERMINED│
│      │                              │ operativa            │                 │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  M6  │ Sync MENTE↔FUEGO             │ Interfaz síncrona    │ No hay sync     │ NOT_DETERMINED│
│      │                              │ operativa            │                 │              │
└──────┴──────────────────────────────┴──────────────────────┴─────────────────┴──────────────┘
```

### CUERPO

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    CASILLAS DE CUERPO                                        │
├──────┬──────────────────────────────┬──────────────────────┬─────────────────┬──────────────┐
│  ID  │ Afirmación                   │ PASS mínimo          │ FAIL si…        │ FASE 1       │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  C1  │ Observación real (≠ simulada)│ Distinción explícita │ Observación     │ PARTIAL      │
│      │                              │ en la interfaz       │ simulada sin    │              │
│      │                              │                      │ marca           │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  C2  │ Medición reproducible        │ Magnitudes, unidades,│ Mediciones sin  │ PARTIAL      │
│      │                              │ condiciones          │ condiciones     │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  C3  │ Artefactos conservados       │ Artefacto material   │ Solo traza, no  │ PARTIAL      │
│      │                              │ recuperable          │ artefacto       │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  C4  │ Hash verificado en punto de  │ Recomputación al     │ Uso sin re-     │ PROVEN_ABSENT│
│      │ uso                          │ consumir             │ verificar       │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  C5  │ Sync CUERPO↔MENTE            │ Operativo            │ No hay          │ NOT_DETERMINED│
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  C6  │ Sync CUERPO↔FUEGO            │ Operativo            │ No hay          │ NOT_DETERMINED│
└──────┴──────────────────────────────┴──────────────────────┴─────────────────┴──────────────┘
```

### FUEGO

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    CASILLAS DE FUEGO                                         │
├──────┬──────────────────────────────┬──────────────────────┬─────────────────┬──────────────┐
│  ID  │ Afirmación                   │ PASS mínimo          │ FAIL si…        │ FASE 1       │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  F1  │ Transformación controlada    │ Alcance, efectos,    │ Sin control     │ PARTIAL      │
│      │                              │ condiciones de       │                 │              │
│      │                              │ recuperación         │                 │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  F2  │ R12 rollback por dispositivo │ Test de rollback por │ Journal SQLite  │ PROVEN_ABSENT│
│      │                              │ unidad-device        │ o global        │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  F3  │ Sync FUEGO↔MENTE             │ Operativo            │ No hay          │ NOT_DETERMINED│
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  F4  │ Sync FUEGO↔CUERPO            │ Operativo            │ No hay          │ NOT_DETERMINED│
└──────┴──────────────────────────────┴──────────────────────┴─────────────────┴──────────────┘
```

### AGUA

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    CASILLAS DE AGUA                                          │
├──────┬──────────────────────────────┬──────────────────────┬─────────────────┬──────────────┐
│  ID  │ Afirmación                   │ PASS mínimo          │ FAIL si…        │ FASE 1       │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  G1  │ Aprendizaje con procedencia  │ Cada aprendizaje con │ Aprendizaje sin │ PARTIAL      │
│      │                              │ cadena trazable      │ procedencia     │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  G2  │ Revalidación al recuperar    │ Test de recuperación │ Recupera sin    │ PROVEN_ABSENT│
│      │                              │ con revalidación     │ revalidar       │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  G3  │ Invocación por capacidad (no │ Solicitud por        │ Llamada a nombre│ PARTIAL      │
│      │ por nombre)                  │ capacidad            │ fijo            │              │
└──────┴──────────────────────────────┴──────────────────────┴─────────────────┴──────────────┘
```

### ROUTER

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    CASILLAS DE ROUTER                                        │
├──────┬──────────────────────────────┬──────────────────────┬─────────────────┬──────────┐
│  ID  │ Afirmación                   │ PASS mínimo          │ FAIL si…        │ FASE 1   │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────┤
│  R1  │ Resolución por capacidad     │ Interfaz recibe      │ Mapa estático   │ PARTIAL  │
│      │                              │ capacidad; backend   │ por nombre      │          │
│      │                              │ elegido por criterios│                 │          │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────┤
│  R2  │ 4 capacidades mínimas        │ Interfaz para las 4  │ Faltan familias │ PARTIAL  │
│      │ disponibles                  │ familias             │                 │          │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────┤
│  R3  │ Backends intercambiables     │ Fallo de backend se  │ Backend único   │ PARTIAL  │
│      │                              │ resuelve a otro o se │ fijo            │          │
│      │                              │ reporta              │                 │          │
└──────┴──────────────────────────────┴──────────────────────┴─────────────────┴──────────┘
```

### MUNDO REAL

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    CASILLAS DE MUNDO REAL                                    │
├──────┬──────────────────────────────┬──────────────────────┬─────────────────┬──────────────┐
│  ID  │ Afirmación                   │ PASS mínimo          │ FAIL si…        │ FASE 1       │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  W1  │ Investigación de código      │ Backend operativo    │ Sin backend     │ PARTIAL      │
│      │ fuente                       │ con artefacto real   │                 │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  W2  │ Investigación de binarios    │ Backend operativo    │ Sin backend     │ PARTIAL      │
│      │ ELF/DWARF                    │                      │                 │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  W3  │ Investigación de procesos    │ Backend operativo    │ Sin backend     │ NOT_DETERMINED│
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  W4  │ Investigación de memoria     │ Backend operativo    │ Sin backend     │ NOT_DETERMINED│
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  W5  │ Observación de MMIO          │ Backend operativo    │ Sin backend     │ NOT_DETERMINED│
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  W6  │ Investigación de PCIe        │ Backend operativo    │ Sin backend     │ NOT_DETERMINED│
└──────┴──────────────────────────────┴──────────────────────┴─────────────────┴──────────────┘
```

### DISCIPLINA

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    CASILLAS DE DISCIPLINA                                    │
├──────┬──────────────────────────────┬──────────────────────┬─────────────────┬──────────┐
│  ID  │ Afirmación                   │ PASS mínimo          │ FAIL si…        │ FASE 1   │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────┤
│  D1  │ Orden EVIDENCE→…→VALIDATION  │ Registro de pasos    │ Pasos salteados │ PARTIAL  │
│      │                              │ por decisión         │                 │          │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────┤
│  D2  │ Detección de saltos          │ Alerta/fallo ante    │ Saltos          │ PARTIAL  │
│      │                              │ salto                │ silenciosos     │          │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────┤
│  D3  │ Validación reabre evidencia  │ Ciclo cerrado        │ Validación      │ PARTIAL  │
│      │                              │                      │ terminal        │          │
└──────┴──────────────────────────────┴──────────────────────┴─────────────────┴──────────┘
```

### PUERTA

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    CASILLAS DE PUERTA                                        │
├──────┬──────────────────────────────┬──────────────────────┬─────────────────┬──────────────┐
│  ID  │ Afirmación                   │ PASS mínimo          │ FAIL si…        │ FASE 1       │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  P1  │ Audit + revisión             │ Revisor registrado   │ Auto-revisión   │ PARTIAL      │
│      │ independiente                │ como no-participante │                 │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  P2  │ CONTESTED → CHALLENGED con   │ Flujo registrado     │ CONTESTED       │ PARTIAL      │
│      │ evidencia nueva              │                      │ terminal        │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  P3  │ ACCEPTED: artefactos íntegros│ Hash PASS en todo    │ Integridad no   │ PROVEN_ABSENT│
│      │                              │ artefacto            │ verificada      │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  P4  │ ACCEPTED: 0 refutaciones     │ Registro de          │ Refutación      │ PROVEN_ABSENT│
│      │ críticas                     │ contradicciones      │ pendiente       │              │
│      │                              │ resueltas            │                 │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  P5  │ ACCEPTED: revisor no         │ Declaración          │ Sin declaración │ PROVEN_ABSENT│
│      │ participante                 │ verificable          │                 │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  P6  │ ACCEPTED: autoridad nombrada │ Persona/rol          │ Sin autoridad   │ PROVEN_ABSENT│
│      │                              │ registrado           │                 │              │
├──────┼──────────────────────────────┼──────────────────────┼─────────────────┼──────────────┤
│  P7  │ Etapa 1 bloqueada hasta      │ Gate efectivo        │ Avance sin      │ PROVEN_ABSENT│
│      │ ACCEPTED                     │                      │ ACCEPTED        │              │
└──────┴──────────────────────────────┴──────────────────────┴─────────────────┴──────────────┘
```

### Reconciliación con FASE 1

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    RECONCILIACIÓN CON FASE 1                                 │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  FASE 1 reporta:                                                            │
│  ├── 0 VERIFICADO                                                           │
│  ├── 7 PARTIAL                                                              │
│  ├── 9 PROVEN_ABSENT                                                        │
│  └── 3 NOT_DETERMINED                                                       │
│                                                                              │
│  Para un SUBCONJUNTO de casillas.                                           │
│                                                                              │
│  Los conteos NO son métrica global de esta tabla maestra (~60 casillas).    │
│                                                                              │
│  Deben reconciliarse con artefactos originales antes de usarse como KPI.    │
│                                                                              │
│  La tabla maestra es la LISTA COMPLETA que el audit debe cubrir.            │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## §22. Aspectos no definidos por el diseño

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    ASPECTOS NO DEFINIDOS POR EL DISEÑO                       │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Puntos que requieren especificación adicional o evidencia. Su ausencia     │
│  NO indica defecto de implementación; indica que el contrato no determina   │
│  todos los detalles para evaluación completa.                               │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    LISTA DE AUSENCIAS ESTRUCTURALES                          │
├──────┬──────────────────────────────┬────────────────────────────────────────┤
│  #   │ Ausencia                     │ Descripción                            │
├──────┼──────────────────────────────┼────────────────────────────────────────┤
│  1   │ Clasificación de eventos     │ Regla explícita de qué eventos         │
│      │ críticos en ÉTER             │ requieren persistencia obligatoria     │
├──────┼──────────────────────────────┼────────────────────────────────────────┤
│  2   │ Cálculo de severidad de      │ Factores y reglas de impacto           │
│      │ contradicción                │                                        │
├──────┼──────────────────────────────┼────────────────────────────────────────┤
│  3   │ Designación de autoridad de  │ Procedimiento que determina quién      │
│      │ aceptación                   │ acepta                                 │
├──────┼──────────────────────────────┼────────────────────────────────────────┤
│  4   │ Selección de backend en      │ Criterios de compatibilidad,           │
│      │ ROUTER                       │ disponibilidad, costo, precisión,      │
│      │                              │ tratamiento de fallos                  │
├──────┼──────────────────────────────┼────────────────────────────────────────┤
│  5   │ Frontera AGUA/TIERRA         │ Qué es aprendizaje reutilizable vs     │
│      │                              │ evidencia/afirmación auditable         │
├──────┼──────────────────────────────┼────────────────────────────────────────┤
│  6   │ Protocolo sync entre         │ Interfaces, garantías de llamada,      │
│      │ MENTE/CUERPO/FUEGO           │ errores, concurrencia                  │
├──────┼──────────────────────────────┼────────────────────────────────────────┤
│  7   │ Métricas de experimentos A/B │ Variable principal, controles,         │
│      │                              │ presupuesto, condiciones,              │
│      │                              │ interpretación                         │
└──────┴──────────────────────────────┴────────────────────────────────────────┘
```

Estos puntos **no se cierran añadiendo flechas o cajas**. Requieren contratos precisos, evidencia pertinente y pruebas discriminantes cuando corresponda.

---

## §23. Síntesis documental

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    SÍNTESIS DOCUMENTAL                                       │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  El diagrama RXRE v3+unificado constituye una ESPECIFICACIÓN ARQUITECTÓNICA │
│  EN ESTADO DE HIPÓTESIS.                                                    │
│                                                                              │
│  Consolida responsabilidades, relaciones y restricciones, y convierte sus   │
│  elementos en casillas auditables.                                          │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    CONTENIDO DEL DOCUMENTO                                   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  ELEMENTO                        │ CANTIDAD                            │  │
│  ├──────────────────────────────────┼─────────────────────────────────────┤  │
│  │ Componentes/dominios arquitect.  │ 9 principales                      │  │
│  │ Correcciones identificadas [v3]  │ 7                                  │  │
│  │ Estados epistemológicos          │ 6 (exactamente)                    │  │
│  │ Capas de hash diferenciadas      │ 3                                  │  │
│  │ Mecanismos de concurrencia       │ 3 (para operaciones distintas)     │  │
│  │ Mecanismos de inmutabilidad      │ 4                                  │  │
│  │ Condiciones para ACCEPTED        │ 4                                  │  │
│  │ Pasos de disciplina metodológica │ 6                                  │  │
│  │ Casillas auditables (PASS/FAIL)  │ ~60 (§21)                          │  │
│  │ Ausencias estructurales          │ 7 (§22)                            │  │
│  └──────────────────────────────────┴─────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

Las cantidades describen el **alcance documental**, no capacidades demostradas. Los estados reportados, recuentos de pruebas y referencias a archivos requieren **corroboración** mediante artefactos originales.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    CONCLUSIÓN OPERATIVA                                      │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  El diseño ofrece base para formular preguntas de auditoría.                │
│                                                                              │
│  El próximo paso sustantivo es obtener y examinar artefactos de ./audit/,   │
│  contrastar cada casilla con evidencia reproducible, y someter las          │
│  afirmaciones críticas a REVISIÓN INDEPENDIENTE.                            │
│                                                                              │
│  NO CORRESPONDE tratar la arquitectura como implementada ni iniciar la      │
│  siguiente etapa mientras el audit y la puerta de aceptación sigan sin      │
│  resolverse.                                                                │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

```text
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║                         FIN DEL DOCUMENTO                                    ║
║                                                                              ║
║  Estado: HIPÓTESIS — no verificado                                          ║
║  Audit A-F: ESPERANDO ARTEFACTOS                                            ║
║  Etapa 1: BLOQUEADA                                                         ║
║  Implementación: NO AUTORIZADA                                              ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```
