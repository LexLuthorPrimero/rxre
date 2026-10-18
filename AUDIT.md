# AUDIT A-F — RXRE arquitectura v3+unificado

> **ESTADO: HIPÓTESIS.** Ninguna casilla de este documento es una afirmación
> sobre el repositorio hasta que hay un artefacto que lo respalde. Este
> documento registra lo que se **comprobó**, lo que **se comprobó que falta**,
> y lo que **no se pudo comprobar**.

El diagrama consolidado dice **qué debería ser**. Este audit dice **qué es**.
Ninguno reemplaza al otro.

- **Mapa**: `tools/rxre/arquitectura/` + `docs/RXRE-ARQUITECTURA-v3-unificado.md`
- **Andamiaje verificable**: `tools/rxre/arquitectura/` (9 componentes, 7 v3)
- **Territorio**: este documento
- **Fase**: FASE 1 (andamiaje). Cerrada. FASE 2 requiere autorización.

---

## 0. CORRECCIÓN DE ESTE DOCUMENTO

Una versión anterior de este `AUDIT.md` fue sustituida durante la sesión por
un texto que **no era de este audit** y queDeclaraba:

- «la implementación técnica de las 7 correcciones v3 está completa y verificada»
  cuando, en su propia tabla, cuatro de las siete constan como PROPOSED,
  NOT_DETERMINED o BLOCKED;
- los 9 componentes como **VERIFICADO**, confundiendo *el fichero existe en el
  andamiaje* con *la arquitectura está en el repo*;
- cuatro módulos (`MENTE.py`, `CUERPO.py`, `FUEGO.py`, `CORRECCIONES_V3.py`)
  que **no existen**: MENTE, CUERPO y FUEGO viven en `planos.py`, y las
  correcciones se declaran en `__init__.py`;
- tests de falsificación **invertidos** («el agente falla si INVALIDATED
  aparece en el código»): añadir la corrección provocaba el fallo.

Se registra porque es exactamente el fallo que el diagrama prohíbe —
convertir hipótesis en afirmación sin artefacto — y porque un audit que no
denuncia sus propios errores no sirve para detectar los de nadie.

---

## 1. RESUMEN

| | Casillas |
|---|---|
| **Total en el diagrama** | 19 |
| **VERIFICADO** | **0** |
| **PARTIAL** | **7** |
| **PROVEN_ABSENT** | **9** |
| **NOT_DETERMINED** | **3** |

**Cero casillas VERIFICADO.** El diagrama describe una arquitectura que RXRE
no tiene todavía. Eso no es un defecto del audit: es su resultado.

### La distinción que este audit no aplana

| Concepto | Dónde vive | Recuento |
|---|---|---|
| ¿el **módulo** existe en el andamiaje? | `tools/rxre/arquitectura/` | 10/10 |
| ¿el **componente** está integrado en RXRE? | este documento | **0/10** |
| ¿la **corrección v3** existe en RXRE? | §3 | **0/7** |

Las tres filas son distintas. La versión anterior de este documento las
mezcló y por eso declaró «VERIFICADO» a cosas que no lo están.

---

## 2. QUÉ ES Y QUÉ NO ES EL ANDAMIAJE

| | Construido aquí | ¿Es RXRE? |
|---|---|---|
| Contrato con entrada/salida/fallo | ✅ | — |
| Test que **falla** si se borra la corrección | ✅ (89 aserciones + 7/7 mutaciones) | — |
| Integrado en el pipeline de RXRE | ❌ | — |
| Usado por los producers reales (`rz_*`) | ❌ | — |
| Con schema en la base de desarrollo | ❌ | — |

**El paquete es un andamiaje verificable, no una migración.** Importarlo en
`store.py` o `dispatch.py` es FASE 2 y requiere autorización.

---

## 3. LAS 7 CORRECCIONES v3

### 3.1 ¿Existen en el ANDAMIAJE? — sí, y por mutación

No basta con que el test pase. Un test pasa igual con la corrección, sin ella
y con la mecánica al revés. `test_arquitectura_v3_03_mutacion.py` **rompe cada
corrección** y exige que el suite la detecte:

| # | Corrección | Mutación aplicada | Fails detectados |
|---|---|---|---|
| 1 | ÉTER write-ahead + descarte contado | descarte deja de contarse; fsync se declara hecho cuando falló | 1 |
| 2 | INVALIDATED no automático | la contradicción invalida sola | 1 |
| 3 | Concurrencia por operación | la PK del lock pasa a `'LOCK_GLOBAL'` | 2 |
| 4 | Rollback por dispositivo | la prohibición de rollback global desaparece | 2 |
| 5 | Inmutabilidad como mecanismo | se borran los dos triggers de `evidence` | 1 |
| 6 | Hash en 3 capas | autenticidad := integridad; validez deducida del hash | 1 |
| 7 | ACCEPTED con autoridad | `faltan = []` — acepta sin evaluar condiciones | 7 |

**Control**: 89 PASS / 0 FAIL sin mutar.
**Resultado**: **7/7 discriminan**.

Una mutación no detectada habría hecho fallar este criterio, y así consta en
el histórico: las dos primeras pasadasasinserciones (5/7) porque los patrones
de mutación no coincidían con el fuente. Se corrigieron y se volvió a pasar.

### 3.2 ¿Existen en RXRE? — ninguna

| # | Corrección | En RXRE | Evidencia de la comprobación |
|---|---|---|---|
| 1 | ÉTER: 3 fallos + write-ahead | **PROVEN_ABSENT** | sin hub; `fsync`/`journal`/`write-ahead` → 0 en `dispatch.py` |
| 2 | INVALIDATED con reevaluación | **PROVEN_ABSENT** | `store.py:210` declara **5** estados; `INVALIDATED` → 0 ocurrencias |
| 3 | Concurrencia por operación | **PROVEN_ABSENT** | sin columnas `version` / `row_count` / `locked_by` / `expires` |
| 4 | Rollback por dispositivo (R12) | **PROVEN_ABSENT** | el «rollback» de `store.py:561` es el **journal de SQLite**, no R12 |
| 5 | Inmutabilidad como mecanismo | **PROVEN_ABSENT** | `TRIGGER` → 0; `store.py:870` usa `INSERT OR REPLACE` |
| 6 | Hash: integridad ≠ autenticidad ≠ validez | **PROVEN_ABSENT** | `contract.py:137` expone una sola función, `sha256_de` |
| 7 | ACCEPTED con autoridad declarada | **PROVEN_ABSENT** | `audit/STATE` = `DELIVERED`; sin evaluación de condiciones |

**0 de 7 en RXRE.**

### El detalle que más cuesta ver: #5

`results` se persiste con `INSERT OR REPLACE` (`store.py:870`). Un `result_id`
repetido **sobrescribe el contenido anterior sin dejar rastro**. Es el modo de
fallo que la v3-5 prohíbe, y es el mismo que sostiene los siete resultados
huérfanos y los eventos `COLISION:` de misiones anteriores. La corrección no es
estilo: es la diferencia entre un grafo de evidencia y un registro que se pisa.

---

## 4. LAS 19 CASILLAS

| Casilla | Estado | Evidencia |
|---|---|---|
| **ETER-1** 3 modos de fallo | **PROVEN_ABSENT** | no hay hub asíncrono |
| **ETER-2** write-ahead + fsync | **PROVEN_ABSENT** | `synchronous=NORMAL` es journal de BD, no WAL de eventos |
| **ETER-3** descarte contado | **NOT_DETERMINED** | no hay cola: no se puede medir un descarte que no ocurre |
| **TIERRA-1** claim, 10 campos | **PARTIAL** | `findings` tiene `claim, epistemic, evidence_ids, provenance, limitations`; faltan `falsification_test`, `unresolved_obligations`, `derivation_refs`, `contradiction_refs` |
| **TIERRA-2** 6 estados | **PROVEN_ABSENT** | `store.py:210` lista 5; `INVALIDATED` no existe |
| **TIERRA-3** contradicción no invalida | **PROVEN_ABSENT** | sin el estado INVALIDATED, la regla no puede existir |
| **TIERRA-4** concurrencia por operación | **PROVEN_ABSENT** | sin `version` / `row_count` / `locked_by` / `expires` |
| **TIERRA-5** hash en 3 capas | **PROVEN_ABSENT** | una sola función de hash |
| **EVIDENCE-1** append-only por permiso | **PROVEN_ABSENT** | 0 triggers; escritura con `REPLACE` |
| **EVIDENCE-2** `supersedes_ref` | **PARTIAL** | `finding_relations` tiene la relación `RETRACTA`: vínculo, no sustitución con hash |
| **FUEGO-1** rollback por dispositivo | **PROVEN_ABSENT** | homonimia con el rollback de SQLite |
| **AIRE-1** traza completa | **PARTIAL** | hay trazas (`lessons.py`, `rz_inspect.py`) pero sin `tool_hash` obligatorio |
| **ROUTER-1** capacidades | **PARTIAL** | `dispatch.py` tiene tabla `CAPACIDADES`, pero es un **mapa** con `backend_por_defecto`, no resolución por contrato |
| **MENTE-1** hipótesis rivales | **PARTIAL** | el término aparece (`ts_ast.py`, `umr_read.py`) sin falsificación obligatoria |
| **CUERPO-1** hash en punto de uso | **PROVEN_ABSENT** | «punto de uso» → 0 resultados |
| **AGUA-1** revalidar al recuperar | **PARTIAL** | aparece en `dispatch.py` y `ts_ast.py`; no se comprobó si revalida |
| **ALMA-1** criterio de cierre | **PARTIAL** | `audit_operacion.py` y `P0.2_CLOSURE.md`; no se comprobó si es evaluable |
| **PUERTA-1** ACCEPTED con autoridad | **PROVEN_ABSENT** | no hay evaluación de las 4 condiciones |
| **PUERTA-2** sin autoridad → CONTESTED | **PARTIAL** | `audit/STATE` existe; `STATE_CHANGELOG.md` documenta el cambio |

---

## 5. LO QUE NO SE PUDO COMPROBAR

Se nombra en vez de rellenarse:

1. **ETER-3 (descarte contado).** Sin cola no hay modo de fallo que medir. No
   se puede afirmar «descarta de forma contada» sobre un sistema que no tiene
   dónde descartar.
2. **AGUA-1 (revalidación).** El término aparece en el código; comprobar si
   *revalida* o solo *recupera* exige ejercitar el camino con un artefacto
   mutado. No se hizo, y no se cuenta como si se hubiera hecho.
3. **ALMA-1 (criterio de cierre).** Que exista un documento de cierre no
   significa que el cierre sea *evaluable*.

---

## 6. PASOS DE MIGRACIÓN (FASE 2) Y SU RIESGO

Cada paso toca `store.py` o `dispatch.py`. **Ninguno se ha ejecutado.**

| # | Paso | Archivo | Riesgo | Reversible |
|---|---|---|---|---|
| 1 | `INVALIDATED` como 6.º estado | `store.py` | **ALTO** — migración de datos; 6 estados donde hay 5 | sí (columna) |
| 2 | `INSERT OR REPLACE` → append + `supersedes_ref` | `store.py` | **MUY ALTO** — rompe todo `registrar()` que reescriba; afecta los 7 huérfanos | **no** |
| 3 | Triggers que prohíban `DELETE` en evidencia | `store.py` | **ALTO** — bloquea cualquier poda/retención existente | sí (drop trigger) |
| 4 | Concurrencia por operación | `store.py` | **MEDIO** — todos los escritores pasan a versión | sí |
| 5 | R12 por dispositivo | `store.py` | **MEDIO** — no hay noción de dispositivo en el modelo | parcial |
| 6 | Mapa → resolución por contrato | `dispatch.py` | **MEDIO** — cambia qué producer se elige | sí |

**Orden obligatorio**: 1 → 3 → 2 → 4 → 5 → 6. El paso 2 es el caro y no es
reversible; por eso va después de instalar el trigger que protege la evidencia,
no antes.

---

## 7. LA PUERTA

```
AUDIT A-F  ──►  STATE=DELIVERED  ──►  REVISIÓN INDEPENDIENTE
                                                    │
                                    ┌───────────────┴───────────────┐
                                    ▼                               ▼
                               CONTESTED                        ACCEPTED
                                    │                               │
                        vuelve a CHALLENGED             ETAPA 1 (bloqueada)
```

Estado actual: **`DELIVERED`** (`audit/STATE`).

| # | Condición de ACCEPTED | ¿Se cumple? |
|---|---|---|
| 1 | artefactos íntegros | **NO** — refutaciones críticas sobre el sistema de evidencia |
| 2 | 0 refutaciones críticas pendientes | **NO** — §3.2: las 7 v3 no existen en RXRE |
| 3 | revisor declara no haber participado | **NO** — quien construyó esto no puede revisarlo |
| 4 | autoridad de aceptación nombrada | **NO** — nadie nombrado |

`PUERTA.aceptar()` evalúa las cuatro y devuelve `CONTESTED` nombrando cuál
falta. **No existe forma de declararlo a mano**, y eso es deliberado: una
función que escribiera «ACCEPTED» sería el string manual que la v3-7 prohíbe.

> **La condición 3 no la puedo resolver yo.** Este agente construyó FASE 1 y
> por tanto no puede ejecutar FASE 3. Si se pide cerrar la puerta desde aquí,
> la respuesta es la que fija la v3-7: no puedo, el revisor debe declarar no
> haber participado.

---

## 8. LOS 7 CRITERIOS DE CIERRE

`ALMA.evaluar_cierre()` sobre el repo real:

| Criterio | Estado |
|---|---|
| `EVIDENCIA_CADA_CASILLA` | NOT_DETERMINED |
| `SIN_HECHOS_SIN_ARTEFACTO` | NOT_DETERMINED |
| `IDEMPOTENCIA` | NOT_DETERMINED |
| `REPRODUCTIBILIDAD` | NOT_DETERMINED |
| `LAS_7_V3` | NOT_DETERMINED |
| `FALSIFICACION_ASOCIADA` | NOT_DETERMINED |
| `NO_INVENTAR` | NOT_DETERMINED |

**7 de 7 sin evaluar.** Ninguno tiene función de evaluación contra el repo.
Un cierre con deuda no declarada sería peor que no cerrar, porque se pierde la
información de lo que faltó.

---

## 9. REPRODUCIR

```bash
# Contratos de los 9 componentes
python3 tools/rxre/tests/test_arquitectura_v3_01_contracts.py

# Las 7 v3 con contraste
python3 tools/rxre/tests/test_arquitectura_v3_02_v3.py

# Las 7 v3 por MUTACIÓN (rompe cada corrección y exige detección)
python3 tools/rxre/tests/test_arquitectura_v3_03_mutacion.py
```

Bases temporales fuera del repositorio. No tocan `storage/rxre.sqlite3` ni
ningún archivo protegido.

---

## 10. QUIÉN FIRMA

| | |
|---|---|
| **Autoridad de aceptación** | — (no nombrada) |
| **Revisor independiente** | — (no nombrado) |
| **Constructor** | agente de ingeniería, sesión actual |

Por la condición 3, quien construyó esto **no puede ser quien lo revise**.
Por eso este documento no se declara `ACCEPTED`, y no es un olvido.