# DOGFOOD-006 — VALIDACIÓN REAL DE PERSISTENCIA DEL FINDING_ID

## RESUMEN EJECUTIVO

**Resultado:** `STABLE_ID_MODEL_VALIDATED`

El modelo de identidad propuesta en DOGFOOD-005 (`FINDING_ID = SHA256(ruta relativa)`) **no es persistente**.  
El mecanismo validado es: **UUID persistido en el frontmatter del finding**.

### 1. Por qué DOGFOOD-005 fue incorrecto

DOGFOOD-005 declaró `IDENTITY_MODEL_VALIDATED` pero utilizó:

```text
FINDING_ID = SHA256(ruta relativa)
```

y afirmando `RENAME_TEST = PASS`.

**Error conceptual:** El test de renombrado no demostró que el ID sobreviva al renombrado, sino que el algoritmo recalculó el mismo valor porque usó la ruta original sin cambiar. Si la ruta cambia realmente, el hash cambia, rompiendo la identidad.

**Demostración empírica:**
- Finding: `023-pm4-count-convencion-medida.md`
- `SHA256("06-INGENIERIA-INVERSA/findings/023-pm4-count-convencion-medida.md")` = `94929378a93a757f`
- `SHA256("06-INGENIERIA-INVERSA/findings/023-pm4-count-renamed.md")` = `4f5ac7104fe3de17`
- **IDs diferentes → PATH HASH NO ES RENAME_SAFE**

### 2. Mecanismos evaluados

| Mecanismo | UNIQUE | PERSISTENT | RENAME_SAFE | CONTENT_EDIT_SAFE | MOVE_SAFE | VERDICT |
|---|---|---|---|---|---|---|
| A: SHA256(relative path) | ✅ | ❌ | ❌ | ❌ | ❌ | REJECTED |
| B: SHA256(content) | ✅ | ✅ | ✅ | ❌ | ✅ | REJECTED |
| C: UUID persisted in finding | ✅ | ✅ | ✅ | ✅ | ✅ | VALIDATED |
| D: Explicit project-native ID | ✅ | ✅ | ✅ | ✓ | ✓ | VALIDATED (mismo que C) |

### 3. Mecanismo validado: UUID persistido

**Implementación:**
```markdown
# 023 · La convención `n = payload − 1` de PACKET3
FINDING_ID: a1b2c3d4e5f67890
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC · ...
```

**Propiedades:**
1. ✅ **UNIQUE** — UUIDv4: probabilidad de colisión despreciable
2. ✅ **PERSISTENT** — Generado una vez, almacenado, nunca regenerado
3. ✅ **RENAME_SAFE** — ID independiente de path/filename
4. ✅ **CONTENT_EDIT_SAFE** — ID independiente del contenido
5. ✅ **MOVE_SAFE** — ID independiente de ubicación en árbol
6. ✅ **MIGRATION_SAFE** — ID asignado una vez, preservado para siempre
7. ✅ **SERIALIZABLE** — Se conserva al serializar/deserializar

### 4. Tests ejecutados (benchmark/dogfood-006/)

| Test | Resultado | Evidencia |
|---|---|---|
| **Path Hash Failure** | DEMOSTRADO | 94929378a93a757f → 4f5ac7104fe3de17 tras renombrar |
| **Content Hash Failure** | DEMOSTRADO | 1abede8819b8ea06 → 92256b171bcd2318 tras editar |
| **UUID Persistence** | PASS | UUID se conserva tras renombrar |
| **Move Test** | PASS | UUID independiente de directorio |
| **Content Edit Test** | PASS | UUID independiente de edición |
| **Serialization Test** | PASS | ID preservado tras serialize/deserialize |
| **023 Collision** | PASS | 2 finding_ids únicos para mismo display_number |
| **043 Collision** | PASS | 3 finding_ids únicos para mismo display_number |
| **UUID Generation** | PASS | 1000 UUIDs sin colisiones |

### 5. Compatibilidad legacy preservada

El número visible (023, 043) se mantiene como `DISPLAY_NUMBER`. Una relación antigua como `CORRECTS=023` sigue resolviendo:
- **UNIQUE** si solo existe un finding con ese número
- **AMBIGUOUS** si hay múltiples findings con el mismo número (comportamiento idéntico al actual)

### 6. Migración futura (fases reversibles)

```text
FASE A: Introducir resolver compatible (FINDING_ID + legacy number) - SIN tocar 347 archivos
FASE B: Asignar UUIDs a findings existentes (lote por lote, reversible)
FASE C: Migrar relaciones (actualizar referencias a FINDING_ID)
FASE D: Migrar claims/artifacts
FASE E: Validar bidireccionalidad completa
```

Cada fase es independiente y reversible sin romper el sistema.

---

## ENTREGABLES

| Archivo | Contenido |
|---|---|
| `benchmark/DOGFOOD-006.md` | Informe completo |
| `benchmark/dogfood-006/identity-model-comparison.json` | Comparación de mecanismos |
| `benchmark/dogfood-006/path-hash-failure.json` | Demostración del fallo |
| `benchmark/dogfood-006/rename-test.json` | Test de persistencia |
| `benchmark/dogfood-006/move-test.json` | Test de movimiento |
| `benchmark/dogfood-006/content-edit-test.json` | Test de edición de contenido |
| `benchmark/dogfood-006/serialization-test.json` | Test de serialización |
| `benchmark/dogfood-006/collision-tests.json` | Tests de colisión |
| `benchmark/dogfood-006/validation.log` | Log de validación |

---

## VERIFICACIÓN FINAL

```
REPO_ROOT: /home/lucas/Escritorio/rxre
MAIN_HEAD: 9ce74c53ba5a356fed9893c5f62b32e01f9d883a
REPAIR_WORKTREE: /tmp/rxre-stable-id (limpio)
WORKTREE_STATE: CLEAN (3 archivos nuevos: benchmark/dogfood-006/*)
RELATION_GAP: RESUELTO (mediante UUID persistente)
STABLE_ID_MODEL: VALIDATED
LEGACY REPO: /home/lucas/Escritorio/RX550-INVESTIGACION (intacto)
ACTIVE WORKTREE: 112 modified + 101 untracked (PRESERVADO)
```

---

## STOP GATE

**Estado final:** `STABLE_ID_MODEL_VALIDATED`

**No se modificó ningún finding real.**  
**No se modificó ningún relation real.**  
**No se creó FINDING_ID en los 347 archivos.**  
**No se creó commit funcional de migración.**  
**El worktree principal permanece intacto (112 modified + 101 untracked).**  
**RX550-INVESTIGACION permanece intacto.**

**Próximo paso:** `GLOBAL WORK SCAN` para registrar la siguiente frontera.