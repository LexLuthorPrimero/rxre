# DIAGNÓSTICO RXRE — estado de duplicación

> **Alcance:** solo lectura. No se modificó, creó ni borró ningún archivo del
> repo durante este diagnóstico. Este documento es el único artefacto creado.
>
> **Fecha:** 2026-10-18 · **HEAD:** `0b06313` · **commits:** 673

---

## FASE 3 — ESTADO DEL REPO

```
Audit A-F:          CORRIÓ (y hay revisión independiente)
STATE:              DELIVERED  (audit/STATE, 10 bytes)
Implementación:     TRES implementaciones parciales de TIERRA, ninguna integrada
Tests:              37 pasan (esqueleto) · 3 suites arquitectura pasan · 89 archivos en tools/rxre/tests/
Documentación:      ~200 .md en raíz · 3 AUDIT/VERIFY contradictorios · requiere decisión humana
```

### El audit A-F **sí corrió**, y está completo

| Artefacto | Estado |
|---|---|
| `audit/STATE` | `DELIVERED` |
| `audit/claims.csv` | **38 claims**, 7 columnas, 48 ficheros en `audit/evidence/` |
| `audit/report.md` | 19 KB, informe del auditor |
| `audit/review/report.md` | 24 KB, **revisión independiente** con contexto fresco declarado |
| `audit/STATE_CHANGELOG.md` | corrección administrativa documentada |
| `audit/STATE_PROVENANCE_VERDICT.md` | veredicto de procedencia |

Distribución de las 38 claims: `PROVEN` 28 · `OBSERVED` 5 · `CORROBORATED` 2 ·
`INFERRED` 1 · `NOT_EXECUTED` 1 · **`REFUTED` 1** (`F6`: "los stubs de rz…").

La revisión independiente **sí emitió ACCEPTED** (`audit/review/report.md` §7,
línea 340). Ver CONFLICTO 1.

---

## DUPLICACIÓN

### Hay **tres** implementaciones de TIERRA. Ninguna es la canónica.

| | Ubicación | Tamaño | Qué es | ¿Integrada? |
|---|---|---|---|---|
| **A** | `tools/rxre/core/store.py` | 3.5 MB BD | **Producción.** 19 tablas: `findings`, `results`, `execution_events`, `audit_log` | **Sí** — es la que corre |
| **B** | `tools/rxre/arquitectura/TIERRA.py` | 557 líneas | Fase 1: grafo de evidencia con triggers, 3 capas de hash, 6 estados | **No** — andamiaje aislado |
| **C** | `rxre-esqueleto/rxre/db.py` | 332 líneas | Esqueleto: `claims` + `evidence` con `row_hash` y `supersedes_ref` | **No** — otra base de datos |

**Duplicado parcial exacto:** las tres implementan la tabla de evidencia
append-only. Ninguna comparte código. Ninguna habla con las otras dos.

```
store.py  findings(epistemic, evidence_ids, provenance, limitations)
          evidence_ids = JSON de result_id        <- SIN row_hash, SIN supersedes_ref
          0 triggers en la BD

arquitectura/TIERRA.py  evidence(row_hash, supersedes_ref, claim_id)
                       3 triggers, 6 estados, hash 3 capas

esqueleto/db.py         evidence(id, row_hash, supersedes_ref, claim_ref)
                        2 triggers, 6 estados con CHECK
```

**Duplicado de los 7 planos:**

| Componente | `arquitectura/` (Fase 1) | `rxre-esqueleto/planes/` |
|---|---|---|
| ALMA | `ALMA.py` funcional | `alma.py` stub |
| ÉTER | `ETER.py` funcional (316 líneas) | `eter.py` stub |
| AIRE | `AIRE.py` funcional | `aire.py` stub |
| MENTE | `planos.py::Libro` funcional | `mente.py` stub |
| CUERPO | `planos.py::CUERPO` funcional | `cuerpo.py` stub |
| FUEGO | `planos.py::FUEGO` funcional | `fuego.py` stub |
| AGUA | `AGUA.py` funcional | `agua.py` stub |

### Veredicto sobre el prompt anterior

**El prompt anterior duplicó, no Painter nada nuevo.** Todo lo que el
esqueleto contiene ya existía en `tools/rxre/arquitectura/` con **más**
funcionalidad y tests que lo verifican por mutación:

- El esqueleto tiene 37 tests. La Fase 1 tiene 89 aserciones **más una suite
  que rompe cada corrección v3 y verifica que se detecta** (7/7 mutaciones
  detectadas). El esqueleto no tiene equivalente.
- `esqueleto/hash.py` (155 líneas) es un subconjunto de
  `arquitectura/TIERRA.py::verificar_hash`, que además distingue
  autenticidad por referencia confiable.
- El esqueleto **no sabe** de `INVALIDATED` reversible, `supersedes` con
  verificador de ciclos, ni `PROVEN_ABSENT` como puerta unidireccional: esa
  máquina de estados está completa en `state.py` del esqueleto pero **no** en
  `store.py`.

Lo **único** que el esqueleto aporta que no existía: el SQL con `CHECK` de
6 estados sobre `evidence`, y `optimistic locking` expuesto como API pública.

### No es duplicado (contra lo que sugiere el nombre)

- **`rxre`** es un **script** de 1115 líneas y 31 funciones (CLI JSONL), no
  un directorio. `mkdir rxre` falla por eso. No hay conflicto con
  `rxre-esqueleto/rxre/`.
- **`RXRE/`** es otra cosa: 5 ficheros de bootstrap (`rxre_boot.py`,
  `rxre_touch.py`, `rxre_contracts.py`…) y un README de 24 KB. No comparte
  código con ninguna de las tres TIERRA.
- **No hay `./tests/`** en la raíz. Los tests viven en `tools/rxre/tests/`
  (89 archivos) y `rxre-esqueleto/rxre/tests/` (4).

---

## CONFLICTOS

### CONFLICTO 1 — `ACCEPTED` vs `DELIVERED`

| Fuente | Dice | Fecha |
|---|---|---|
| `audit/review/report.md` §7 | **`# ACCEPTED`** (con reserva de alcance) | 2026-10-17 07:56 |
| `audit/STATE` | **`DELIVERED`** | 2026-10-18 06:03 |

`audit/STATE_CHANGELOG.md` documenta que el cambio a `DELIVERED` fue una
**corrección administrativa** porque la condición de autoridad de aceptación
no está satisfecha, y que la procedencia del `ACCEPTED` previo es
`NOT_DETERMINED`.

**No resuelvo cuál es canónico. Requiere decisión humana.**

### CONFLICTO 2 — `AUDIT.md` vs `VERIFY.md`

| | `AUDIT.md` (07:58:33) | `VERIFY.md` (08:00:25) |
|---|---|---|
| TIERRA/INVALIDATED en `store.py` | **PROVEN_ABSENT** | `PROPOSED` ✅ "Implementado" |
| V3-5 triggers | **PROVEN_ABSENT** — 0 triggers | `PROPOSED` ✅ "trigger on findings" |
| V3-3 concurrencia | **PROVEN_ABSENT** | `NOT_DETERMINED` ✅ "Implemented" |
| Veredicto | 19 casillas medidas: **0 VERIFICADO** | "IMPLEMENTATION COMPLETE AND VERIFIED" |

`VERIFY.md` es **posterior** y **se contradice en su propia tabla**: marca con
✅ filas cuyo estado declara `PROPOSED` / `NOT_DETERMINED` / `BLOCKED`.

Además cita **4 ficheros que no existen** (`MENTE.py`, `CUERPO.py`,
`FUEGO.py`, `CORRECCIONES_V3.py` — los tres primeros viven en `planos.py`).

`tools/rxre/README.md` (07:54:52) repite el mismo patrón y **borró 404 líneas
de documentación** del contrato de `machine.py`. Todo bajo `lucas:lucas 644`,
sin atribución.

**Autor no identificado.** No está en git, no hay commit, los permisos no
distinguen. Registrado como riesgo abierto en §RIESGO.

### CONFLICTO 3 — INVALIDATED está en el comentario, no en el CHECK

```
core/store.py:210   epistemic TEXT, -- PROVEN, …, DEFERRED, INVALIDATED
```
La columna **no tiene CHECK**. `findings.epistemic` acepta cualquier cadena.
El estado está **documentado pero no impuesto**. La tabla `claims` del
esqueleto sí lo impone con `CHECK(... IN (...))`. Divergencia de rigor entre
las dos implementaciones.

### CONFLICTO 4 — el nombre `evidence` significa cosas distintas

- `store.py` → `results` (artefactos de producers) + `findings.evidence_ids` (JSON de result_id)
- `arquitectura/TIERRA.py` → tabla `evidence` con `row_hash`
- `esqueleto/db.py` → tabla `evidence` con `row_hash`

**Ningún `row_hash` ni `supersedes_ref` existe en el código de producción.**
Cero ocurrencias fuera de `arquitectura/` y `rxre-esqueleto/`.

---

## GAPS — qué del diagrama NO está en el código de producción

Verificado contra `tools/rxre/core/store.py` y `backends/dispatch.py`:

| Corrección v3 | Diagrama | Producción | Evidencia |
|---|---|---|---|
| ÉTER: write-ahead + 3 fallos | sí | **PROVEN_ABSENT** | `fsync`/`journal`/`write-ahead` → 0 |
| INVALIDATED + reevaluación | sí | **PARTIAL** | `store.py:210` lo nombra; `:232` tabla `finding_reevaluations`; `:288` `reevaluation_id`. **Sin CHECK** |
| Contradicción no invalida sola | sí | **NOT_DETERMINED** | sin producer que exercise la ruta |
| Concurrencia por operación | sí | **PROVEN_ABSENT** | sin `version`/`row_count`/`locked_by`/`expires` |
| R12 rollback por dispositivo | sí | **PROVEN_ABSENT** | el «rollback» de `store.py:561` es journal de SQLite |
| Inmutabilidad como mecanismo | sí | **PROVEN_ABSENT** | **0 triggers** en las 19 tablas |
| Hash 3 capas | sí | **PROVEN_ABSENT** | `contract.py:137` expone una sola función |
| ACCEPTED con autoridad | sí | **PROVEN_ABSENT** | sin evaluación de condiciones |

**Router de capacidades:** `dispatch.py` tiene tabla `CAPACIDADES`, pero es un
**mapa** con `backend_por_defecto`, no resolución por contrato.

---

## RIESGO ABIERTO

**Escritor concurrente no identificado** entre 07:48 y 08:00 del 2026-10-18.
Escribió `AUDIT.md`, `VERIFY.md` y `tools/rxre/README.md` (este último
borrando 404 líneas). Todo con el mismo `lucas:lucas 644`.

No hay bloqueo de permisos, no hay commit, no hay attribution. Cualquier
trabajo de migración puede ser sobrescrito. **No pude determinar si sigue
activo.**

---

## RECOMENDACIÓN DE SIGUIENTE PASO

**Una sola acción, de documentación:**

> **Congelar y adjudicar `AUDIT.md` vs `VERIFY.md`.** Antes de tocar código,
> una persona decide cuál de los dos documentos de estado es canónico y qué
> se hace con el otro.

Razón: `VERIFY.md` es el **más reciente** y declara lo contrario que el
anterior. Cualquier migración que arranque ahora se apoyará en el documento
 equivocado — el que afirma que todo está implementado. Y el escritor
concurrente puede volver a sobrescribirlo mientras se migra.

**No propongo construir nada.** Tampoco borrar `rxre-esqueleto/`: contiene
trabajo (CHECK de 6 estados, optimistic locking público) que no está en otro
lugar.

Detrás de esa acción, en orden, y solo después:

2. Decidir canónica entre `store.py` (producción), `arquitectura/TIERRA.py` (557
   líneas, 3 triggers) y `esqueleto/db.py` (332 líneas, CHECK). **Requiere
   decisión humana.**
3. Resolver `ACCEPTED` vs `DELIVERED`.
4. Recién entonces, migración.

---

## CÓMO REPRODUCIR ESTE DIAGNÓSTICO

```bash
git rev-parse HEAD && git status --porcelain | wc -l      # HEAD y 275 entradas
cat audit/STATE                                            # DELIVERED
wc -l audit/claims.csv                                    # 39 (=38 claims)
ls audit/review/                                          # revisión independiente
ls tools/rxre/arquitectura/ rxre-esqueleto/rxre/          # las dos TIERRA no integradas
sqlite3 tools/rxre/storage/rxre.sqlite3 \
  "SELECT type, COUNT(*) FROM sqlite_master GROUP BY type;"  # 19 tablas, 0 triggers
cd rxre-esqueleto && python3 -m pytest -q                 # 37 passed
```

## ÍTEMS NO DETERMINADOS

| | |
|---|---|
| Autor del escritor concurrente | `NOT_DETERMINED` — no rastreable |
| Si el escritor sigue activo | `NOT_DETERMINED` |
| Cuál TIERRA es la canónica | `NOT_DETERMINED` — requiere decisión humana |
| Cuál documento de estado es canónico | `NOT_DETERMINED` — requiere decisión humana |
| Si `ACCEPTED` o `DELIVERED` es válido | `NOT_DETERMINED` — ver CONFLICTO 1 |
| Estado real de 89 suites en `tools/rxre/tests/` | `NOT_RUN` — no ejecutado en este diagnóstico |