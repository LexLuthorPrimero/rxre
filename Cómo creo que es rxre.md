# Cómo creo que es rxre

Una línea antes de los diagramas:

> **rxre no es ocho módulos. Es un motor de investigación donde cada plano es una capacidad demostrable, atravesada por dos capas transversales (traza y evidencia), coordinada por un bus asíncrono que no media las llamadas, y gobernada por una disciplina epistémica que ningún paso puede saltear.**

Esto es **hipótesis** hasta que el audit confirme qué contratos son reales. Los diagramas muestran mi modelo mental, no la arquitectura verificada.

---

## Mermaid

```mermaid
flowchart TB
    ALMA["ALMA<br/>propósito · criterio de cierre"]
    ETER{{"ÉTER<br/>hub async<br/>NO media sync"}}

    MENTE["MENTE<br/>causalidad"]
    CUERPO["CUERPO<br/>observación real"]
    FUEGO["FUEGO<br/>transformación"]
    AGUA["AGUA<br/>aprendizaje"]

    AIRE["AIRE ▓▓▓<br/>traza transversal"]
    TIERRA["TIERRA ▓▓▓<br/>evidencia transversal"]

    ALMA ==>|define| ETER

    MENTE <-->|sync| CUERPO
    CUERPO <-->|sync| FUEGO
    MENTE <-->|sync| AGUA
    FUEGO <-->|sync| AGUA

    MENTE -.->|async| ETER
    CUERPO -.->|async| ETER
    FUEGO -.->|async| ETER
    AGUA -.->|async| ETER

    ETER -.->|notifica| AIRE
    ETER -.->|notifica| TIERRA

    AIRE -.->|observa| MENTE
    AIRE -.->|observa| CUERPO
    AIRE -.->|observa| FUEGO
    AIRE -.->|observa| AGUA

    TIERRA -.->|registra| MENTE
    TIERRA -.->|registra| CUERPO
    TIERRA -.->|registra| FUEGO
    TIERRA -.->|registra| AGUA

    style ALMA fill:#ffe6e6,stroke:#c0392b,stroke-width:2px
    style ETER fill:#fff2e6,stroke:#d35400,stroke-width:2px
    style AIRE fill:#e6f2ff,stroke:#2980b9,stroke-width:2px
    style TIERRA fill:#f0e6ff,stroke:#7d3c98,stroke-width:2px
    style MENTE fill:#f8f8f8,stroke:#555
    style CUERPO fill:#f8f8f8,stroke:#555
    style FUEGO fill:#f8f8f8,stroke:#555
    style AGUA fill:#f8f8f8,stroke:#555
```

---

## ASCII

```
┌──────────────────────────────────────────────────────────────────┐
│                            ALMA                                  │
│                   propósito · criterio de cierre                 │
└────────────────────────────┬─────────────────────────────────────┘
                             │ define
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                            ÉTER                                  │
│              hub de eventos ASYNC (NO media sync)                │
│              si cae, los contratos sync siguen funcionando       │
└────────────────────────────┬─────────────────────────────────────┘
                             │ notifica (async)
         ┌───────────────────┴───────────────────┐
         ▼                                       ▼
┌──────────────────┐                   ┌──────────────────┐
│      AIRE        │                   │     TIERRA       │
│  traza cada paso │                   │ evidencia + hash │
└────────┬─────────┘                   └────────┬─────────┘
         │ observa                              │ registra
         │                                      │
         ▼                                      ▼
    ┌──────────────────────────────────────────────────┐
    │              PLANOS DE ACCIÓN                    │
    │         (contratos SÍNCRONOS directos)           │
    │                                                  │
    │   MENTE ◄══sync══► CUERPO ◄══sync══► FUEGO       │
    │     ▲                                    ▲       │
    │     │                                    │       │
    │     └─────────sync────► AGUA ────────────┘       │
    │                                                  │
    │   Si un plano falla, los otros tres siguen       │
    │   (no hay bus en el camino crítico)              │
    └──────────────────────────────────────────────────┘

    ┌──────────────────────────────────────────────────┐
    │         DISCIPLINA POR PASO (no negociable)      │
    │                                                  │
    │  EVIDENCE → SEMANTICS → SCHEMA                   │
    │           → DISCRIMINATING TEST                  │
    │           → IMPLEMENTATION                       │
    │           → VALIDATION → nueva evidencia         │
    └──────────────────────────────────────────────────┘

    ┌──────────────────────────────────────────────────┐
    │         PUERTA GLOBAL (antes de escalar)         │
    │                                                  │
    │  AUDIT A–F → DELIVERED → CHALLENGED              │
    │            ↔ CONTESTED → ACCEPTED                │
    │            → ETAPA 1 (un plano, un test)         │
    │                                                  │
    │  Sin ACCEPTED, ETAPA 1 está BLOQUEADA            │
    └──────────────────────────────────────────────────┘
```

---

## Lo que este diagrama dice (y lo que no)

**Dice:**

- **ALMA** no es un módulo que "piensa": es la que define el criterio de cierre. Sin criterio, ningún ciclo termina.
- **ÉTER** es un hub **async**. No media las llamadas entre planos. Si cae, las llamadas directas siguen. Esto elimina el punto único de falla que se discutió.
- **MENTE, CUERPO, FUEGO, AGUA** son los cuatro planos de **acción**. Se comunican por **contratos síncronos directos** — explícitos, verificables, sin pasar por el bus.
- **AIRE y TIERRA** son **capas transversales**. No son pasos del ciclo. Atraviesan cada transición de cada plano. Si las quitás, perdés trazabilidad y evidencia, pero el ciclo sigue corriendo (y deja de ser verificable).
- La **disciplina epistémica** es el contrato de cada paso. Un plano que se saltea `DISCRIMINATING TEST` no es un plano: es una caja negra con nombre.
- La **puerta global** bloquea la Etapa 1 hasta `ACCEPTED`. No hay atajo.

**No dice (y no debe decir):**

- Cuáles contratos son síncronos y cuáles async en el rxre real. Eso lo decide el audit.
- Cuántos planos están implementados. Puede que 0, 3 u 8.
- Que el modelo de 8 elementos mejora nada. Eso se mide en Etapa 4 (A vs B), no acá.
- Que esta arquitectura es la correcta. Es la **hipótesis más razonable** dado lo discutido, sujeta a refutación por el audit.

---

## La diferencia con los diagramas anteriores

Los diagramas lineales (`ALMA → ÉTER → MENTE → CUERPO → ...`) convierten a rxre en un agente común con nombres poéticos. **Este no.**

La diferencia concreta:

```
Diagrama lineal (malo):    los planos son ETAPAS del ciclo
Diagrama hub (este):       los planos son CAPAS que se atraviesan

En el lineal, si quitás AIRE, el ciclo se corta.
En el hub, si quitás AIRE, el ciclo sigue pero perdés la traza.

En el lineal, ÉTER es un paso más.
En el hub, ÉTER es un canal de observabilidad que no bloquea.

En el lineal, TIERRA persiste "al final".
En el hub, TIERRA persiste cada transición.
```

Esa diferencia es la que separa "agente con 8 adjetivos" de "motor de investigación con 8 capacidades demostrables".

---

**Nada de esto abre la Etapa 1.** El audit sigue esperando. Estos diagramas son la vara con la que el revisor va a mirar el informe: si el rxre real no se parece a esto, la pregunta es *por qué no*, no *cómo forzarlo*.
