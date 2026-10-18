# Los tres ajustes son correctos. Aplico el mínimo.

No son objeciones de estilo. Son correcciones de especificación. Si los diagramas van a ser especificaciones ejecutables, los tres puntos son obligatorios.

---

## Fix 1 — Arquitectura: ÉTER coordina, no media

```mermaid
flowchart TB
    ALMA["ALMA<br/>propósito · criterio de cierre"]
    ETER{{"ÉTER<br/>coordinador de eventos<br/>(NO mediador de llamadas)"}}

    MENTE["MENTE"]
    CUERPO["CUERPO"]
    FUEGO["FUEGO"]
    AGUA["AGUA"]

    AIRE["AIRE · traza"]
    TIERRA["TIERRA · evidencia"]

    ALMA -->|"define criterio"| ETER
    MENTE <-->|"contrato directo<br/>(sincrónico)"| CUERPO
    CUERPO <-->|"contrato directo"| FUEGO
    MENTE <-->|"contrato directo"| AGUA

    MENTE -.->|"evento async"| ETER
    CUERPO -.->|"evento async"| ETER
    FUEGO -.->|"evento async"| ETER
    AGUA -.->|"evento async"| ETER

    ETER -.->|"notifica<br/>suscriptores"| AIRE
    ETER -.->|"notifica<br/>suscriptores"| TIERRA

    style ETER fill:#fff2e6,stroke:#d35400,stroke-width:2px
    style AIRE fill:#e6f2ff,stroke:#2980b9
    style TIERRA fill:#f0e6ff,stroke:#7d3c98
```

**Cambio**: las llamadas síncronas entre planos son directas (contrato explícito). ÉTER solo ve eventos asíncronos, para observabilidad y coordinación. Si ÉTER cae, las llamadas directas siguen. Eso elimina el punto único de falla que vos señalaste.

**Nota de especificación**: qué relaciones son síncronas y cuáles asíncronas **no está decidido**. Eso se verifica en el audit. El diagrama es hipótesis, no contrato.

---

## Fix 2 — Puerta: `ACCEPTED` no se gana con tres fallos

```mermaid
flowchart TB
    CHAL["CHALLENGED<br/>revisor selecciona 3 claims"]
    ATT["intento de refutación<br/>método registrado"]
    VALID{"¿el intento fue<br/>válido y reproducible?"}

    BAD["intento inválido<br/>(no cuenta)"]
    OK["intento válido"]
    RESULT{"¿refutó<br/>el claim?"}

    REPROD{"¿la evidencia original<br/>es reproducible<br/>por el revisor?"}

    CONT["CONTESTED<br/>refutación reproducible"]
    UNV["UNVERIFIED<br/>evidencia original<br/>no reproducible"]
    ACC["ACCEPTED"]

    CHAL --> ATT --> VALID
    VALID -->|"no"| BAD --> ATT
    VALID -->|"sí"| OK --> RESULT
    RESULT -->|"sí"| CONT
    RESULT -->|"no"| REPROD
    REPROD -->|"sí"| ACC
    REPROD -->|"no"| UNV

    CONT -->|"evidencia nueva +<br/>corrección documentada"| CHAL
    UNV -->|"nueva evidencia"| CHAL

    style ACC fill:#d5f5e3,stroke:#229954,stroke-width:2px
    style CONT fill:#fadbd8,stroke:#c0392b
    style UNV fill:#fdebd0,stroke:#d35400
    style BAD fill:#e8e8e8,stroke:#777
```

**Cambios respecto a la versión anterior**:

- `ACCEPTED` requiere **dos condiciones por claim**: (a) intento de refutación válido, (b) evidencia original reproducible por el revisor. Con una sola, no alcanza.
- Si el intento es inválido (método no reproducible), **no cuenta** — no se puede acumular "tres fallos vagos" y declarar victoria.
- `CONTESTED → CHALLENGED` requiere **evidencia nueva**, no solo "corrección". Sin esa flecha etiquetada, el estado se podía mover sin agregar información.
- Agregué `UNVERIFIED`: si la evidencia original no se reproduce, el claim ni se refuta ni se acepta. Queda abierto.

Esto cierra tu objeción: tres intentos fallidos, por sí solos, no mueven a `ACCEPTED`. Lo que mueve es **refutación fallida válida + evidencia reproducible**.

---

## Fix 3 — Micro-loop: quitar y que rompa no es prueba de nada

```mermaid
flowchart TB
    REMOVE["quitar el plano"]
    BREAKS{"¿algo se rompe?"}
    NOBREAK["el plano no era real<br/>→ rollback (decisión válida)"]

    WHAT["¿QUÉ se rompió?"]
    COUPLING{"¿lo roto se puede<br/>arreglar sin el plano?"}

    ACCIDENTAL["ACOPLAMIENTO ACCIDENTAL<br/>el plano era dependencia<br/>de algo que no lo necesitaba<br/>→ arreglar el acople y re-probar"]
    REAL["CAPACIDAD REAL<br/>lo roto depende<br/>genuinamente del plano<br/>→ commit"]

    REMOVE --> BREAKS
    BREAKS -->|"no"| NOBREAK
    BREAKS -->|"sí"| WHAT --> COUPLING
    COUPLING -->|"sí"| ACCIDENTAL --> REMOVE
    COUPLING -->|"no"| REAL

    style REAL fill:#d5f5e3,stroke:#229954,stroke-width:2px
    style ACCIDENTAL fill:#fdebd0,stroke:#d35400
    style NOBREAK fill:#fadbd8,stroke:#c0392b
```

**Cambio**: el paso "quitar → rompe → commit" se descompone. Antes de declarar que el plano es real, se prueba si lo roto es **dependencia genuina** o **acoplamiento accidental**. Si es accidental, se arregla el acople y se **vuelve a quitar**. Solo después de que quitar rompa algo que no se puede arreglar sin el plano, el plano se declara real.

**Nota de especificación**: "arreglar el acople" puede requerir cambiar otro plano. Si eso pasa, el commit del plano nuevo y el fix de acople van juntos o no va ninguno.

---

## Lo que no cambia

La secuencia operativa:

```
AUDIT A-F → DELIVERED → CHALLENGED → (CONTESTED ↔ CHALLENGED) → ACCEPTED → ETAPA 1
```

Estos tres diagramas son **especificación de cómo se decide**, no autorización para decidir. Nada acá abre la Etapa 1. Esa sigue bloqueada hasta `ACCEPTED`.

---

## Una sola cosa para cuando llegue el `DELIVERED`

Los tres fixes que aplicaste cambian la vara. Cuando el revisor mire el informe, ahora tiene que verificar **dos cosas por claim** (intento válido + evidencia reproducible), no una. Y cuando el auditor evalúe un plano, tiene que distinguir **capacidad real** de **acoplamiento accidental**, no solo "quitar rompe".

Eso son dos preguntas más por claim, y una más por plano. Si el informe no las responde, el informe está incompleto — no por diseño, sino porque la vara subió.

Nada más. El audit sigue esperando.
