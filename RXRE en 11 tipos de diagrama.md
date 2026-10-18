# RXRE en 11 tipos de diagrama

Antes de mostrarlos, una regla que se aplica a todos:

> **Son hipótesis, no descripciones verificadas.** Ninguno reemplaza al audit. Ninguno autoriza Etapa 1. Sirven para que cuando el audit diga qué existe, tengamos el vocabulario para mapearlo.

Y una distinción importante: los diagramas 1–5 describen **el sistema** (lo que el audit verifica). Los diagramas 6–11 describen **el proyecto** (cómo trabajamos sobre el sistema). Son tipos de verdad distintos.

---

## 1. Flowchart — arquitectura

Lo que muestra: la topología. ÉTER es hub async, AIRE/TIERRA son transversales, los 4 planos de acción se hablan sync.

```
                       ┌──────────────┐
                       │     ALMA     │
                       │  propósito   │
                       └──────┬───────┘
                              │ define criterio
                              ▼
                       ┌──────────────┐
                       │     ÉTER     │
                       │  hub async   │
                       └──┬───┬───┬───┘
                          │   │   │
              ┌───────────┘   │   └───────────┐
              │               │               │
              ▼               ▼               ▼
         ┌─────────┐     ┌─────────┐     ┌─────────┐
         │  AIRE   │     │ TIERRA  │     │  (otros)│
         │ traza   │     │evidencia│     │         │
         └────┬────┘     └────┬────┘     └─────────┘
              │ observa        │ registra
              │                │
              ▼                ▼
    ┌──────────────────────────────────────────────┐
    │          PLANOS DE ACCIÓN (sync)             │
    │                                              │
    │   ┌───────┐  sync  ┌────────┐  sync  ┌─────┐│
    │   │ MENTE │◄──────►│ CUERPO │◄──────►│FUEGO││
    │   │causal.│        │observa.│        │trans││
    │   └───┬───┘        └───┬────┘        └──┬──┘│
    │       │                │                │   │
    │       └──────sync──────┼────────sync────┘   │
    │                        │                    │
    │                   ┌────▼────┐               │
    │                   │  AGUA   │               │
    │                   │ aprende │               │
    │                   └─────────┘               │
    └──────────────────────────────────────────────┘

   ÉTER recibe eventos async de los 4 planos de acción.
   ÉTER NO media las llamadas sync.
   Si ÉTER cae, sync sigue funcionando.
```

---

## 2. Sequence — un ciclo en el tiempo

Lo que muestra lo que el flowchart oculta: **el orden** de interacción en una investigación real.

```
ALMA   MENTE   CUERPO   FUEGO   TIERRA   AIRE   AGUA   ÉTER
 │       │       │        │        │       │      │      │
 ├──────►│       │        │        │       │      │      │  define criterio
 ├───────┼───────┼────────┼────────┼───────┼──────┼─────►│  evento
 │       │       │        │        │       │      │      │
 │       ├──────►│        │        │       │      │      │  proponer obs
 │       │       ├───────►│        │       │      │      │  registrar + hash
 │       │       │        ├───────►│       │      │      │
 │       │       ├───────►│        │       │      │      │
 │       │◄──────┤        │        │       │      │      │  obs bruta
 │       │       │        │        │       │      │      │
 │       ├───┐   │        │        │       │      │      │  hipótesis rivales ≥2
 │       │◄──┘   │        │        │       │      │      │
 │       │       │        │        │       │      │      │
 │       ├──────►│        │        │       │      │      │  prueba discriminante
 │       │       ├───┐    │        │       │      │      │  ejecutar
 │       │       │◄──┘    │        │       │      │      │
 │       │       ├───────►│        │       │      │      │  resultado + límites
 │       │       │        ├───────►│       │      │      │
 │       │       │        │        │       │      │      │
 │       │  [resultado confirma]   │       │      │      │
 │       ├───────┼────────┼───────►│       │      │      │  transformación
 │       │       │        │        ├───────┼──────┼─────►│  cambio + rollback
 │       │       │        ├───────►│       │      │      │  verificar efecto
 │       │       │        │        │       │      │      │
 ├───────┼───────┼────────┼────────┼───────┼──────┼─────►│  ¿criterio?
 │       │       │        │        │       │      │      │
 │       │       │        │        │       │      │◄─────┤  no → ciclo
 │       │       │        │        │       │      │      │
```

---

## 3. State — ciclo de vida de un CLAIM

Lo que muestra: los 5 estados y sus transiciones legales. Sin este diagrama, `PROVEN_ABSENT` y `DEFERRED` son solo nombres.

```
                    ┌───────────────────┐
                    │  NOT_DETERMINED   │◄──── [inicio]
                    └─────────┬─────────┘
                              │
              ┌───────────────┼────────────────┐
              │               │                │
              ▼               ▼                ▼
    ┌───────────────┐  ┌──────────────┐  ┌────────────┐
    │    PARTIAL    │  │PROVEN_ABSENT │  │  DEFERRED  │
    └───────┬───────┘  └──────┬───────┘  └─────┬──────┘
            │                 │                │
       ┌────┴────┐            │                │
       │         │            │                │
       ▼         ▼            ▼                ▼
   ┌───────┐ ┌────────┐  ┌──────────┐   ┌───────────┐
   │PROVEN │ │NOT_DET.│  │NOT_DET.  │   │NOT_DET.   │
   └───┬───┘ └────────┘  └──────────┘   └───────────┘
       │
       ▼
    [final]

   Reglas:
   - PROVEN requiere obligaciones resueltas
   - PROVEN_ABSENT requiere búsqueda exhaustiva
   - PARTIAL puede volver a NOT_DETERMINED si evidencia se invalida
```

---

## 4. Class — schema del CLAIM

Lo que muestra: la estructura de datos que el documento de TIERRA propuso. Si esto no existe en el repo, TIERRA no existe.

```
┌───────────────────────────────┐
│            Claim              │
├───────────────────────────────┤
│ + id                          │
│ + statement                   │
│ + object_id                   │
│ + scope                       │
│ + status                      │
│ + falsification_test          │
└───┬───────┬────────┬──────┬───┘
    │       │        │      │
    │1..*   │1..*    │1..*  │1..*
    │       │        │      │
    ▼       ▼        ▼      ▼
┌────────┐┌────────┐┌──────────┐┌───────────┐
│Evidence││Derivat.││Contradic.││Obligation │
├────────┤├────────┤├──────────┤├───────────┤
│+type   ││+tool   ││+id       ││+id        │
│+source ││+version││+claims[] ││+descript. │
│+hash   ││+in_hash││+reason   ││+blocked_by│
│+producer││+out_has││          ││           │
└────────┘└────────┘└──────────┘└───────────┘

Relaciones:
  Claim "1" ── "1..*" Evidence       (evidence_refs)
  Claim "1" ── "1..*" Derivation     (derivation_refs)
  Claim "1" ── "1..*" Contradiction  (contradiction_refs)
  Claim "1" ── "1..*" Obligation     (unresolved_obligations)
```

---

## 5. ER — persistencia del grafo de evidencia

Lo que muestra: cómo se guarda el CLAIM en una base. Distinto del Class (que muestra relaciones lógicas): este muestra **filas y claves**.

```
        ┌──────────┐       ┌──────────┐       ┌──────────┐
        │  CLAIM   │       │ EVIDENCE │       │ ARTIFACT │
        ├──────────┤       ├──────────┤       ├──────────┤
        │ id (PK)  │──┐    │ id (PK)  │──┐    │hash_sha256│
        │ status   │  │   │ type     │  │   │ path     │
        │ scope    │  │   │ hash_ref │──┼──►│ producer │
        └──────────┘  │   └──────────┘  │   │ version  │
             │        │                 │   └──────────┘
             │        │                 │        ▲
             │        └─────────────────┼────────┘
             │                          │
             ▼                          ▼
        ┌──────────┐       ┌──────────┐
        │DERIVATION│       │  CONTRA- │
        ├──────────┤       │  DICTION │
        │ id (PK)  │       ├──────────┤
        │ tool     │       │ id (PK)  │
        │ in_hash  │──┐    │ reason   │
        │ out_hash │──┼──► │ claim_a  │
        └──────────┘  │    │ claim_b  │
             │        │    └──────────┘
             │        │
             ▼        │
        ┌──────────┐  │
        │OBLIGATION│  │
        ├──────────┤  │
        │ id (PK)  │  │
        │ descript.│  │
        │ blocked  │  │
        └──────────┘  │
                      │
        ┌─────────────┴──────────┐
        │  ARTIFACT (retomado)   │
        └────────────────────────┘
```

---

## 6. Mindmap — los 8 como capacidades, no módulos

Lo que muestra: que los 8 no son cajas, son **verbos**. Si el audit no encuentra el verbo, el plano no existe.

```
                              ┌─────────┐
                              │  RXRE   │
                              └────┬────┘
         ┌────────────┬────────────┼────────────┬────────────┐
         │            │            │            │            │
         ▼            ▼            ▼            ▼            ▼
    ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
    │CUERPO  │  │MENTE   │  │ALMA    │  │TIERRA  │  │FUEGO   │
    ├────────┤  ├────────┤  ├────────┤  ├────────┤  ├────────┤
    │ leer   │  │hipóte. │  │objetivo│  │ hash   │  │transf. │
    │ejecutar│  │rivales │  │cierre  │  │proced. │  │rollback│
    │ medir  │  │discrim.│  │ voz    │  │incert. │  │validar │
    └────────┘  └────────┘  └────────┘  └────────┘  └────────┘

         ┌────────────┬────────────┐
         │            │            │
         ▼            ▼            ▼
    ┌────────┐  ┌────────┐  ┌────────┐
    │AIRE    │  │AGUA    │  │ÉTER    │
    ├────────┤  ├────────┤  ├────────┤
    │ trazar │  │aprender│  │integrar│
    │reconst.│  │ olvidar│  │detectar│
    └────────┘  └────────┘  └────────┘
```

---

## 7. Journey — la experiencia del investigador

Lo que muestra el flowchart no puede: **el costo cognitivo** de cada paso. Un diagrama de flujo dice "CUERPO observa". Un journey dice "CUERPO observar es el paso 3 de dificultad".

```
Sección       Paso                          Dificultad (1=fácil, 5=difícil)   Actor
─────────────────────────────────────────────────────────────────────────────

DEFINIR       ALMA define criterio          █████ (5)                         ALMA
              MENTE propone hipótesis       ████  (4)                         MENTE

OBSERVAR      CUERPO lee artefacto          ███   (3)                         CUERPO
              TIERRA registra hash          ████  (4)                         TIERRA

DISCRIMINAR   MENTE diseña test             ███   (3)                         MENTE
              CUERPO ejecuta                ██    (2)                         CUERPO
              TIERRA registra resultado     ████  (4)                         TIERRA

TRANSFORMAR   FUEGO aplica cambio           ███   (3)                         FUEGO
              FUEGO verifica rollback       ████  (4)                         FUEGO

APRENDER      AGUA extrae lección           ████  (4)                         AGUA
              ÉTER detecta nueva pregunta   ███   (3)                         ÉTER

CERRAR        ALMA verifica criterio        █████ (5)                         ALMA
```

---

## 8. Timeline — secuencia del proyecto

Lo que muestra: el estado real. Bloqueado → Autorizado → Condicionado → Peligroso. Sin esto, no se ve por qué Etapa 5 es distinta de Etapa 1.

```
                                            │
   ─────────────┬──────────────┬────────────┼────────────┬───────────
                │              │            │            │
            BLOQUEADO     AUTORIZADO     CONDICIONADO  PELIGROSO
                │              │            │            │
                ▼              ▼            ▼            ▼
           ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
           │ Etapa 0  │  │ Etapa 1  │  │ Etapa 3  │  │ Etapa 5  │
           │ Audit    │  │ 1 plano  │  │ ciclo    │  │iniciativa│
           │ A-F      │  │ 1 test   │  │ completo │  │  acotada │
           │          │  │ 1 commit │  │          │  │          │
           │ Verif.   │  │          │  │ Etapa 4  │  │ Etapa 6  │
           │ indep.   │  │ Etapa 2  │  │ A vs B   │  │ multi-   │
           │          │  │ 2 planos │  │          │  │ instancia│
           │          │  │          │  │          │  │          │
           │          │  │          │  │          │  │ Etapa 7  │
           │          │  │          │  │          │  │ exterior │
           └──────────┘  └──────────┘  └──────────┘  └──────────┘
                │              │            │            │
                ▼              ▼            ▼            ▼
              NO SE          PUERTA      COSTO        RIESGO
              PUEDE          BÁSICA      ALTO         CRÍTICO
              EMPEZAR        DE          MANTENER
                             ACEPTACIÓN
```

---

## 9. Quadrant — impacto × incertidumbre

Lo que muestra: qué plano atacar primero, no por "importancia" abstracta sino por **relación entre impacto y desconocimiento**. Las posiciones son hipótesis hasta el audit.

```
                    ALTO IMPACTO
                        ▲
                        │
          ┌─────────────┼─────────────┐
          │             │             │
          │   ATACAR    │  VERIFICAR  │
          │   PRIMERO   │  RÁPIDO     │
          │             │             │
          │             │             │
          │  TIERRA ●   │   ● ÉTER    │
          │  CUERPO ●   │             │
          │             │   ● MENTE   │
          │             │             │
          │   ● AIRE    │   ● FUEGO   │
          │             │             │
          │             │             │
          │  IGNORAR    │  DOCUMENTAR │
          │  POR AHORA  │             │
          │             │   ● AGUA    │
          │             │             │
          │             │   ● ALMA    │
          │             │             │
          └─────────────┼─────────────┘
                        │
                        ▼
                  BAJO IMPACTO
   BAJA                                    ALTA
   INCERTIDUMBRE                    INCERTIDUMBRE
```

---

## 10. Gantt — dependencias entre etapas

Lo que muestra el Timeline no puede: **qué bloquea qué**. Fechas ilustrativas — el punto es la cadena de dependencias.

```
                    Semana 1    Semana 2    Semana 3    Semana 4    Semana 5
                    ─────────   ─────────   ─────────   ─────────   ─────────
BLOQUEANTE
  Audit A-F         ████████████████
  Verificación                     ████████████████
  independiente

AUTORIZADO
  Etapa 1                                       ████████████
  (1 plano, 1 test)
  Etapa 2                                                   ████████████
  (2 planos)

CONDICIONADO
  Etapa 3                                                              ████████
  Etapa 4                                                              ████████

PELIGROSO
  Etapa 5                                                              (después)
  Etapa 6                                                              (después)
  Etapa 7                                                              (después)

  ─────────────────────────────────────────────────────────────────────
  CRÍTICO (bloquea todo):
    ■ Audit A-F  →  Verificación independiente  →  Etapa 1

  Solo cuando Etapa 1 pasa la puerta se puede empezar Etapa 2.
  Etapa 3 y 4 condicionadas a Etapa 2.
  Etapa 5+ solo después de Etapa 4.
  ─────────────────────────────────────────────────────────────────────
```

---

## 11. Requirement — restricciones como requisitos

Lo que muestra: el protocolo convertido en requisitos verificables. Cada uno tiene método de verificación. Si un requisito no se verifica, el protocolo no se cumplió.

```
┌────────────────────────────────────────────────────────────────────┐
│                       REQUISITOS RXRE                              │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ R1: Audit A-F ACCEPTED antes de implementar                  │  │
│  │                                                              │  │
│  │ id: R1  ─  risk: high  ─  verificación: test                 │  │
│  │                                                              │  │
│  │ Cómo se verifica:                                            │  │
│  │   - audit/STATE == ACCEPTED                                  │  │
│  │   - sin refutaciones críticas pendientes                     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              │                                     │
│                              ▼                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ R2: Una sola capacidad por etapa                             │  │
│  │                                                              │  │
│  │ id: R2  ─  risk: medium  ─  verificación: inspección         │  │
│  │                                                              │  │
│  │ Cómo se verifica:                                            │  │
│  │   - 1 commit por capacidad                                   │  │
│  │   - 1 test adversarial asociado                              │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              │                                     │
│                              ▼                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ R3: Test adversarial falla primero                           │  │
│  │                                                              │  │
│  │ id: R3  ─  risk: high  ─  verificación: test                 │  │
│  │                                                              │  │
│  │ Cómo se verifica:                                            │  │
│  │   - log del primer run: FAIL                                 │  │
│  │   - log del segundo run (post-fix): PASS                     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              │                                     │
│                              ▼                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ R4: Toda transformación tiene rollback                       │  │
│  │                                                              │  │
│  │ id: R4  ─  risk: medium  ─  verificación: test               │  │
│  │                                                              │  │
│  │ Cómo se verifica:                                            │  │
│  │   - aplicar cambio → revertir → diff = 0 bytes               │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              │                                     │
│                              ▼                                     │
│                                                                    │
│                        ┌──────────┐                                │
│                        │  RXRE    │                                │
│                        │ (system) │                                │
│                        └──────────┘                                │
│                                                                    │
│  Cada Rn ──satisfies──► RXRE                                       │
└────────────────────────────────────────────────────────────────────┘
```

---

## Los que no hice, y por qué

```
✗ Pie chart     — nada de RXRE es proporcional a un todo
✗ Git graph     — no hay commits significativos todavía
✗ Sankey        — forzaría flujos que no están definidos
✗ Kanban        — es gestión de trabajo, no del sistema
✗ C4            — solaparía con flowchart + class
✗ Block         — idem
```

Mostrar 17 diagramas sería ruido. Estos 11 dicen algo distinto cada uno. Los que faltan serían variaciones.

---

## Lo que estos 11 diagramas NO son

```
✗ No son la descripción de rxre
✗ No reemplazan al audit
✗ No autorizan Etapa 1
✗ No prueban que los 8 planos existan
✗ No prueban que la arquitectura sea correcta
```

Son **el vocabulario** con el que el audit va a hablar cuando llegue. Si un claim del audit dice "TIERRA existe", el diagrama 3 dice qué estados debería tener. Si el claim dice "TIERRA no existe", el diagrama 6 dice qué verbo falta.

**La regla operativa no cambió:**

```
AUDIT A-F:       esperando artefactos
ETAPA 1:         BLOQUEADA
IMPLEMENTACION:  NO AUTORIZADA
```

Estos 11 diagramas son una biblioteca de preguntas. La evidencia sigue siendo la misma de siempre: no llegó.
