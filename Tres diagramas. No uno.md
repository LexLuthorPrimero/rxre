# Tres diagramas. No uno.

Un solo diagrama miente. Tres, cada uno con una pregunta distinta, no.

---

## 1. Arquitectura: hub, no pipeline

Esta es la corrección al diagrama lineal del doc anterior. ÉTER es hub, AIRE y TIERRA son transversales, no pasos.

```mermaid
flowchart TB
    ALMA["ALMA<br/>propósito · criterio de cierre"]
    ETER{{"ÉTER<br/>hub integrador<br/>relaciones y brechas"}}

    MENTE["MENTE<br/>hipótesis rivales<br/>prueba discriminante"]
    CUERPO["CUERPO<br/>observación real<br/>artefacto + hash"]
    FUEGO["FUEGO<br/>transformación<br/>con rollback"]
    AGUA["AGUA<br/>aprendizaje<br/>con procedencia"]

    AIRE["AIRE<br/>traza transversal<br/>de cada paso"]
    TIERRA["TIERRA<br/>evidencia transversal<br/>cadena de hashes"]

    ALMA --> ETER
    ETER <--> MENTE
    ETER <--> CUERPO
    ETER <--> FUEGO
    ETER <--> AGUA

    MENTE -.- AIRE
    CUERPO -.- AIRE
    FUEGO -.- AIRE
    AGUA -.- AIRE

    MENTE -.- TIERRA
    CUERPO -.- TIERRA
    FUEGO -.- TIERRA
    AGUA -.- TIERRA

    AIRE -.-|"ambas capas se atraviesan<br/>entre sí"| TIERRA

    style ALMA fill:#ffe6e6,stroke:#c0392b,stroke-width:2px
    style ETER fill:#fff2e6,stroke:#d35400,stroke-width:2px
    style AIRE fill:#e6f2ff,stroke:#2980b9,stroke-width:2px
    style TIERRA fill:#f0e6ff,stroke:#7d3c98,stroke-width:2px
    style MENTE fill:#f8f8f8,stroke:#555
    style CUERPO fill:#f8f8f8,stroke:#555
    style FUEGO fill:#f8f8f8,stroke:#555
    style AGUA fill:#f8f8f8,stroke:#555
```

**Lo que cambia respecto al lineal**:

- ÉTER no es un paso después de ALMA: es el hub al que todo se conecta
- AIRE y TIERRA no son pasos: son capas que atraviesan a los cuatro planos de acción
- Los planos de acción no están en secuencia: MENTE↔CUERPO, CUERPO↔FUEGO, etc. se llaman entre sí a través de ÉTER

---

## 2. Puertas: el audit no termina, pasa

Una vez `ACCEPTED`, recién hay Etapa 1. Antes no.

```mermaid
flowchart LR
    AUDIT["AUDIT A–F<br/>(solo lectura)"]
    DELIV["DELIVERED<br/>informe entregado"]
    CHAL["CHALLENGED<br/>revisor intenta refutar"]
    CONT["CONTESTED<br/>refutación reproducible"]
    ACC["ACCEPTED<br/>3 claims sin refutar"]
    E1["ETAPA 1<br/>un plano"]

    AUDIT --> DELIV
    DELIV --> CHAL
    CHAL -->|"refutación exitosa"| CONT
    CONT -->|"corregido"| CHAL
    CHAL -->|"3 intentos sin refutar"| ACC
    ACC --> E1

    style AUDIT fill:#e8e8e8,stroke:#333
    style DELIV fill:#fff2cc,stroke:#b7950b
    style CHAL fill:#fdebd0,stroke:#d35400
    style CONT fill:#fadbd8,stroke:#c0392b
    style ACC fill:#d5f5e3,stroke:#229954,stroke-width:2px
    style E1 fill:#d6eaf8,stroke:#2874a6,stroke-width:2px
```

**Lo que cambia respecto a la secuencia original**: `CONTESTED → CHALLENGED` existe. Un informe puede rebotar. Sin esa flecha, `ACCEPTED` es "nadie se quejó", no "nadie pudo refutar".

---

## 3. Micro-loop: cada etapa es este ciclo

No es un diagrama de fases. Es el ciclo interno que se repite **una vez por plano** dentro de cada etapa.

```mermaid
flowchart TB
    START([plano con peor estado<br/>en el audit])
    TEST["escribir test adversarial<br/>(el caso donde el comando miente)"]
    RUN1["correr test → falla<br/>(el plano no es real todavía)"]
    IMPL["escribir comando mínimo<br/>que lo haga pasar"]
    RUN2["correr test → pasa"]
    REMOVE["quitar el plano<br/>y ver si algo se rompe"]
    DECIDE{"¿quitar rompe<br/>una capacidad?"}

    KEEP["commit<br/>(plano real)"]
    FIX["bug: el test miente<br/>(volver al test)"]
    REVERT["rollback<br/>(no era un plano)"]

    START --> TEST
    TEST --> RUN1
    RUN1 --> IMPL
    IMPL --> RUN2
    RUN2 --> REMOVE
    REMOVE --> DECIDE
    DECIDE -->|"sí"| KEEP
    DECIDE -->|"no"| REVERT
    RUN2 -->|"el test nunca falló"| FIX
    FIX --> TEST

    style START fill:#e8e8e8,stroke:#333
    style KEEP fill:#d5f5e3,stroke:#229954,stroke-width:2px
    style REVERT fill:#fadbd8,stroke:#c0392b
    style FIX fill:#fdebd0,stroke:#d35400
    style DECIDE fill:#fff2cc,stroke:#b7950b
```

**Lo que cambia respecto a "un plano, un test, un commit"**: hay **dos flechas de salida que no son éxito**. `REVERT` es válido. `FIX` es válido. Sin esas dos, el diagrama sería propaganda.

---

## Cómo se usan juntos

```
┌─────────────────────────────────────────────────────┐
│  Diagrama 1 (arquitectura) → ¿QUÉ es rxre?          │
│  Diagrama 2 (puertas)      → ¿CUÁNDO se escala?     │
│  Diagrama 3 (micro-loop)   → ¿CÓMO se hace un paso? │
└─────────────────────────────────────────────────────┘
```

Cada uno responde una pregunta distinta. Ninguno reemplaza a los otros.

**Si tuvieras que quedarte con uno solo**, quedate con el 2. Es el único que dice **cuándo no empezar**. Los otros dos dicen qué hacer, pero el 2 dice cuándo está permitido hacerlo.
