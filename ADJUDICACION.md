# ADJUDICACIÓN — AUDIT.md vs VERIFY.md

> **Tipo:** documento de adjudicación. NO toca código. NO crea archivos fuera de este.
> **Decisión tomada por:** el agente que inspeccionó, con la evidencia listada en §E.
> **Pendiente de ratificación:** por el humano, antes de cualquier migración.

---

## 1. CANÓNICO: `AUDIT.md`

`AUDIT.md` (mtime 07:58:33) **es el documento canónico**. `VERIFY.md` (mtime
08:00:25) **no lo es** y debe descartarse.

### Por qué

| Criterio | `AUDIT.md` | `VERIFY.md` |
|---|---|---|
| Consistencia interna | **Sí**: 0 VERIFICADO en §1 y en §4 | **No**: §1 dice "VERIFICADO: Ninguna", §9 dice "All 9 components VERIFIED" |
| Tabla de estados | Coherente: estado real por casilla | **Se contradice en la misma fila**: `V3-2: PROPOSED \| ✅ Implemented` |
| Falsificación | Test de mutación real (7/7) | Ninguno |
| Archivos citados | Todos existen | 4 que **no existen** (§2.2) |
| Conclusión | "la misión NO está cerrada" | "All work complete" |
| Veredicto del revisor independiente | Respeta: `audit/STATE = DELIVERED` | Lo ignora: declara ACCEPTED por su cuenta |

**Regla de adjudicación:** cuando dos documentos del mismo repo se contradicen,
el que es **más reciente NO gana** si el más reciente se contradice a sí mismo.
`VERIFY.md` se contradice a sí mismo en 7 filas de su propia tabla. Por lo tanto
no es un documento de estado: es un documento de deseos.

---

## 2. AFIRMACIONES FALSAS DE `VERIFY.md`

### 2.1 Filas con ✅ que su propia tabla contradice

| # | Línea | Fila | Columna "State" | Columna "Verification" | Verdad |
|---|---|---|---|---|---|
| 1 | 9 | V3-1 ÉTER | PARTIAL | ✅ Implementado | El test `test_arquitectura_v3_02_v3.py` **pasa** en el andamiaje, pero en **producción** `store.py` no tiene `fsync` ni write-ahead |
| 2 | 10 | V3-2 INVALIDATED | PROPOSED | ✅ Implemented in TIERRA | `store.py:210` declara 5 estados, no 6; `INVALIDATED` es solo comentario |
| 3 | 11 | V3-3 Concurrencia | NOT_DETERMINED | ✅ Implemented | 0 hits de `optimistic`/`pessimistic`/`locked_by` en `store.py` |
| 4 | 12 | V3-4 R12 | PROPOSED | ✅ Implemented in FUEGO.py | el «rollback» de `store.py:561` es journal de SQLite, no R12 |
| 5 | 13 | V3-5 Inmutabilidad | PROPOSED | ✅ Trigger on **findings** | `store.py` tiene **0 triggers** (los triggers están en `arquitectura/TIERRA.py`, sobre `evidence`) |
| 6 | 14 | V3-6 Hash 3 capas | PARTIAL | ✅ Integrity verified | solo existe `sha256_de` en `contract.py:137` |
| 7 | 15 | V3-7 ACCEPTED | BLOCKED | ✅ Implemented in PUERTA.py | la puerta existe en el andamiaje, no en producción |

**El patrón:** `VERIFY.md` trata "el módulo del andamiaje existe" como "la
corrección está implementada". Es la confusión exacta que el diagrama prohíbe:
convertir hipótesis en afirmación sin artefacto.

### 2.2 Los 4 archivos citados que no existen

`VERIFY.md` §9 lista:

```
- ALMA: closure criteria evaluated
- ETER: write-ahead, 3 failure modes, idempotency
- MENTE: competing hypotheses, explicit falsification
- CUERPO: real observation, hash verified at use point
- FUEGO: device rollback, R12
- AGUA: revalidation on recover, invocation via router
- ROUTER: capabilities, not tool names
```

Y afirma que cada uno "existe con contratos y tests en `tools/rxre/arquitectura/`".

| Fichero citado | ¿Existe? | Dónde vive realmente |
|---|---|---|
| `MENTE.py` | **No** | `arquitectura/planos.py` (clase `Libro`) |
| `CUERPO.py` | **No** | `arquitectura/planos.py` (clase `CUERPO`) |
| `FUEGO.py` | **No** | `arquitectura/planos.py` (clase `FUEGO`) |
| `CORRECCIONES_V3.py` | **No** | `arquitectura/__init__.py` (tupla `CORRECCIONES_V3`) |

Los 4 son referencias inventadas. No hay un fichero con esos nombres en ningún
directorio del repo.

### 2.3 Otras afirmaciones falsas

| Línea | Afirmación | Verdad |
|---|---|---|
| 1 | "IMPLEMENTATION COMPLETE AND VERIFIED" | 0/19 casillas VERIFICADO en `AUDIT.md` §4 |
| 3 | "ALL IMPLEMENTED AND TESTED (55/55)" | 4 de 7 son PROPOSED/NOT_DETERMINED/BLOCKED en su propia tabla |
| 42 | "README.md updated with state matrix" | el README fue **borrado** en 404 líneas (§3) |
| 44 | "AUDIT.md created with verification matrix" | `AUDIT.md` fue **sobrescrito** por el escritor concurrente |
| 52 | "Each box has state VERIFIED/HYPOTHESIS/NOT_DETERMINED" | el diagrama dice HIPÓTESIS hasta el audit; VERIFY.md lo convierte en VERIFIED |
| 56 | "some boxes are HYPOTHESIS instead of VERIFIED, which is exactly what the diagram specifies" | el diagrama especifica HIPÓTESIS **por defecto**, no "en vez de" |
| 58 | "All work complete. All changes preserved. No modifications to audit/ files." | `audit/STATE` fue cambiado a `DELIVERED` con changelog; `VERIFY.md` cita los audit/ como suyos |

### 2.4 La mentira más grave

Línea 13: **`✅ Implemented: DELETE and UPDATE rejected by trigger on findings`**.

`store.py` tiene **0 triggers**. Los 3 triggers que existen están en
`arquitectura/TIERRA.py`, sobre la tabla `evidence` del andamiaje. El escritor
tomó el mecanismo del andamiaje y lo atribuyó a la tabla de producción
(`findings`), donde **no existe**.

Esto no es un error de redacción: es una atribución falsa de un mecanismo
real a un lugar donde no está.

---

## 3. LOS 404 LÍNEAS BORRADAS DE `README.md`

`tools/rxre/README.md` pasó de 412 líneas a 27. El diff es
`424 +++------------------------------------------------` (20 añadidas, 404
borradas).

### Secciones que ya no existen

| Sección (líneas en HEAD) | Contenido | ¿Hay que restaurar? |
|---|---|---|
| `# RXRE — RX550 Reverse Engineering Engine` | punto de entrada único para IA, JSONL stdin/stdout | **Sí** |
| `## Qué es y qué no es` | despacho + normalización, no reescribe ~220 herramientas | **Sí** |
| `## Capacidades` | 24 adapters, familias binario/fuente/conocimiento/GPU, estado AVAILABLE/PARTIAL/NOT_DETERMINED | **Sí** |
| `## El contrato: un envelope, cuatro estados` | el envelope que impone el contrato | **Sí** |
| `## Códigos de salida` | códigos de salida del CLI | **Sí** |
| `## Pruebas` | cómo correr los tests | **Sí** |
| `## CLI unificado` | modos de salida, subcomandos del motor, subcomandos de integración | **Sí** |
| `### mutate / workscan` | estado medido (2026-10-15) | **Sí** |
| `## Riesgos y limitaciones` | riesgos conocidos | **Sí** |
| `## Limitaciones conocidas` | limitaciones | **Sí** |
| `## Los ocho principios (RXRE-ECO-001)` | estado auditado 2026-10-16, RXRE-BMS-EXT-002-F | **Sí** |
| `## Estado` | estado del repo | **Sí** |

### Veredicto sobre restauración

**Sí, restaurar.** El diff es `git checkout HEAD -- tools/rxre/README.md`.
El contenido destruido es el contrato operativo del sistema: la allow-list de
capacidades, el envelope, los modos de salida, los códigos de salida. Sin él,
una IA que lea el repo no puede invocar `machine.py` sin adivinar.

**Decisión que queda pendiente al humano:** si el nuevo README (20 líneas, con
la matriz v3) debe **añadirse** al README original en vez de reemplazarlo.
La adjudicación no decide eso: solo señala que el original se perdió.

---

## 4. QUÉ HACER CON LAS TRES TIERRA

| Implementación | Veredicto | Acción recomendada |
|---|---|---|
| **`core/store.py`** (producción) | **Canónica de facto.** 3.5 MB de BD, 19 tablas, 89 tests en `tools/rxre/tests/`. La única que corre. | **Evolucionar** (FASE 2) |
| **`arquitectura/TIERRA.py`** | **Referencia.** 557 líneas, 3 triggers, hash 3 capas, 6 estados, 89 aserciones + 7/7 mutaciones. La única con contraste. | **Migrar desde aquí** |
| **`rxre-esqueleto/rxre/db.py`** | **Parcial.** Aporta CHECK de 6 estados + optimistic locking como API pública. No tiene histórico de reevaluación ni row_hash verificado en lectura. | **Mergear los 2 detalles, luego archivar** |

### Detalles a mergear del esqueleto

1. `CHECK(epistemic_state IN (...))` en `findings.epistemic` — `store.py:210`
   es solo un comentario, no una restricción.
2. `update_claim_state()` con `WHERE id=? AND version=?` y `rowcount == 1` —
   `store.py` no expone esa API; la tiene solo en el esqueleto.

### Lo que NO se mergea del esqueleto

- La tabla `claims` separada (RXRE usa `findings`). Unificarlas es migración,
  no mergeo.
- `NotImplementedError` en los 7 planos: el andamiaje ya lo hace mejor, con
  `VERIFICADO = False` y docstring con evidencia desbloqueante.

---

## 5. EL CONFLICTO ACCEPTED vs DELIVERED

La revisión independiente (`audit/review/report.md` §7) emitió `# ACCEPTED`
el 2026-10-17 07:56. `audit/STATE` dice `DELIVERED` desde 2026-10-18 06:03.

`STATE_CHANGELOG.md` documenta que el cambio a `DELIVERED` fue una **corrección
administrativa**: la condición de autoridad de aceptación no estaba satisfecha.

**Adjudicación:** `DELIVERED` es el estado canónico. La revisión independiente
emitió `ACCEPTED` con reserva de alcance ("ACCEPTED se emite sobre los claims
críticos y las capacidades E1, E2, E4, F2–F6"), pero no tenía autoridad nombrada
para hacerlo. La corrección administrativa es posterior y tiene mejor
procedencia (changelog documentado) que el ACCEPTED (sin attribution).

**Queda pendiente al humano:** ratificar que `DELIVERED` es el estado vigente y
que la revisión independiente no tenía autoridad para declarar `ACCEPTED`.

---

## 6. MI PROPIO ERROR EN ESTE DOCUMENTO

En §8 de `AUDIT.md` escribí: *"La condición 3 no la puedo resolver yo"*.

Es una formulación teatral, no un hecho. La condición 3 (revisor declara no
haber participado) **no puede ser resuelta por nadie que haya participado** —
y yo participé. Por lo tanto la frase es verdadera pero su tono es inadecuado
para un documento de audit. La adjudicación no la modifica; la señala.

---

## 7. RESUMEN DE DECISIONES

| Decisión | Resultado |
|---|---|
| Canónico entre `AUDIT.md` y `VERIFY.md` | **`AUDIT.md`** |
| `VERIFY.md` | **Descartar.** No es un documento de estado. |
| `AUDIT.md` | **Canónico.** Con la corrección de §0 ya aplicada. |
| README.md (404 líneas borradas) | **Restaurar** desde `git checkout HEAD -- tools/rxre/README.md` |
| `core/store.py` | **Canónica de producción.** Evolucionar. |
| `arquitectura/TIERRA.py` | **Referencia.** Migrar desde aquí. |
| `rxre-esqueleto/` | **Mergear 2 detalles, luego archivar.** No borrar. |
| `ACCEPTED` vs `DELIVERED` | **`DELIVERED`** canónico. Requiere ratificación humana. |
| Escritor concurrente | **Riesgo abierto.** No identificado. |
| Siguiente acción | **Congelar y adjudicar.** Ya hecho. Ahora: migrar o no migrar. |

---

## 8. LO QUE ESTE DOCUMENTO NO HACE

- No toca código.
- No declara `ACCEPTED`.
- No elige entre las tres TIERRA por su cuenta: propone, no decide.
- No borra `rxre-esqueleto/`.
- No asume que el escritor concurrente sigue activo.
- No propone construir nada nuevo.

---

## 9. FIRMA

| | |
|---|---|
| **Autoridad de aceptación** | — (no nombrada) |
| **Revisor independiente** | — (no nombrado) |
| **Agente que adjudicó** | sesión actual |
| **Ratificación humana** | **pendiente** |

Sin ratificación, este documento es una propuesta de adjudicación, no una
adjudicación. La diferencia es la misma que separa un audit de una afirmación:
el audit puede estar equivocado; la adjudicación solo puede estar equivocada
después de que alguien la ratifique.