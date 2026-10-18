# DOGFOOD-009 — IMPLEMENTACIÓN REAL DE FINDING_ID PERSISTENTE

## RESULTADO: `FINDING_ID_PHASE_A_VALIDATED`

## OBJETIVO

Implementar correctamente la FASE A del modelo de identidad validado en DOGFOOD-006.

El problema demostrado en DOGFOOD-008 era:

```text
FINDING_ID = SHA256(relative_path)[:16]
```

Esto está prohibido porque no es persistente (depende del path).

La nueva implementación utiliza un UUID v4 persistente en el finding.

---

# 1. IMPLEMENTACIÓN

### 1.1 GENERACIÓN DE UUIDV4

Para cada uno de los 5 findings piloto, se generó un UUIDv4 real usando `uuid.uuid4()`:

| Archivo | FINDING_ID | display_number |
|---|---|---|
| `023-pm4-count-convucion-medida.md` | `768010c9-606d-4597-a257-11705f237167` | 023 |
| `023-pte-productor-sdma-gfx8.md` | `3bd5d4d1-65a8-462c-9445-71f6805936ff` | 023 |
| `043-asercion-struct-mqd-contra-offsets.md` | `83c56b38-9da4-4e0e-9940-72cdf4a285f8` | 043 |
| `043-pll-bsp-asi-pasi.md` | `085e5602-0340-4afa-aeeb-e3df67810ef4` | 043 |
| `043-vuelta-atras-035-y-036-leian-el-asic-equivocado.md` | `9f26bc49-539b-4139-bb69-a68b17ead80c` | 043 |

### 1.2 PERSISTENCIA

El `FINDING_ID` se persiste en el frontmatter del finding:

```text
FINDING_ID: 768010c9-606d-4597-a257-11705f237167
```

### 1.3 relations.py

Se modificó `relations.py` para:
- **LEER** FINDING_ID en formato UUID (36 chars con guiones)
- **NO GENERAR** FINDING_ID (la generación ocurre al crear el finding)
- Mantener compatibilidad con resolución de `display_number` legacy

Regex actualizado:
```python
# UUID format: 8-4-4-4-12 hex chars (36 total)
FINDING_ID_RX = re.compile(r"^FINDING_ID:\s*([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\s*$")
# Also accept short 16-hex format for backward compatibility detection
FINDING_ID_SHORT_RX = re.compile(r"^FINDING_ID:\s*([0-9a-fA-F]{16})\s*$")
```

La función `resuelve_a_finding_id` ahora acepta UUIDs de 36 chars:

```python
# 1. FINDING_ID explicito (16 hex chars) y 36-char UUID
if re.fullmatch(r"[0-9a-fA-F]{16}|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", v):
    if v in por_id:
        return v
```

---

# 2. VERIFICACIÓN: FORMATO UUID

### ✓ Todos son UUIDv4 válidos

| Propiedad | Valor |
|---|---|
| Longitud | 36 caracteres |
| Bits | 128 bits |
| Formato UUID estándar | SÍ (8-4-4-4-12) |
| Versión | 4 (RFC 9562) |
| Variante | RFC 4122 |

Validación con `uuid.UUID()`:

```
768010c9-606d-4597-a257-11705f237167 is valid UUIDv4
3bd5d4d1-65a8-462c-9445-71f6805936ff is valid UUIDv4
83c56b38-9da4-4e0e-9940-72cdf4a285f8 is valid UUIDv4
085e5602-0340-4afa-aeeb-e3df67810ef4 is valid UUIDv4
9f26bc49-539b-4139-bb69-a68b17ead80c is valid UUIDv4
```

---

# 3. VERIFICACIÓN: INDEPENDENCIA DEL PATH

### ✓ NINGÚN FINDING_ID coincide con SHA256(path)[:16]

| Archivo | FINDING_ID (UUID) | SHA256(path)[:16] (path hash) | Match |
|---|---|---|---|
| `023-pm4-count-convencion-medida.md` | `768010c9-606d-4597-a257-11705f237167` | `94929378a93a757f` | ✗ (diferente) |
| `023-pte-productor-sdma-gfx8.md` | `3bd5d4d1-65a8-462c-9445-71f6805936ff` | `59d2582fcffa70b8` | ✗ (diferente) |
| `043-asercion-struct-mqd-contra-offsets.md` | `83c56b38-9da4-4e0e-9940-72cdf4a285f8` | `dab296d4eb72d972` | ✗ (diferente) |
| `043-pll-bsp-asi-pasi.md` | `085e5602-0340-4afa-aeeb-e3df67810ef4` | `4a01ac343ec6ba56` | ✗ (diferente) |
| `043-vuelta-atras-035-y-036-leian-el-asic-equivocado.md` | `9f26bc49-539b-4139-bb69-a68b17ead80c` | `9fd3d6252e986fcb` | ✗ (diferente) |

El UUID es independiente del path, filename, content y display_number.

---

# 4. TEST DE PERSISTENCIA

Todos los tests de persistencia pasan porque el UUID se almacena como literal en el frontmatter del finding:

| Test | Result | Detalle |
|---|---|---|
| Rename | ✅ PASS | UUID survive rename |
| Move | ✅ PASS | UUID survive move |
| Content edit | ✅ PASS | UUID survive content edit |
| Serialization | ✅ PASS | UUID survives JSON round-trip |

**Nota crítica**: Los tests de persistencia verifican que el TEXTO almacenado sobrevive a la operación. El UUID es un valor aleatorio de 128 bits — no se regenera, se almacena una vez y persiste. A diferencia del path hash, el UUID NO es determinista a partir del path, por lo que un rename no lo invalida.

---

# 5. COLISIONES

### ✓ 023: 2 findings con mismo display_number → 2 UUIDs diferentes

- `023-pm4-count-convencion-medida.md` → `768010c9-606d-4597-a257-11705f237167`
- `023-pte-productor-sdma-gfx8.md` → `3bd5d4d1-65a8-462c-9445-71f6805936ff`

### ✓ 043: 3 findings con mismo display_number → 3 UUIDs diferentes

- `043-asercion-struct-mqd-contra-offsets.md` → `83c56b38-9da4-4e0e-9940-72cdf4a285f8`
- `043-pll-bsp-asi-pasi.md` → `085e5602-0340-4afa-aeeb-e3df67810ef4`
- `043-vuelta-atras-035-y-036-leian-el-asic-equivocado.md` → `9f26bc49-539b-4139-bb69-a68b17ead80c`

---

# 6. RESOLUCIÓN DE RELACIONES

### ✓ relations.py puede resolver UUIDs únicos

```text
can_resolve_023_A = True (768010c9-...)
can_resolve_023_B = True (3bd5d4d1-...)
can_resolve_043_A = True (83c56b38-...)
can_resolve_043_B = True (085e5602-...)
can_resolve_043_C = True (9f26bc49-...)
```

### ✓ display_number legacy mantiene ambigüedad

```text
legacy_023 = "023"  (amibiguo — 2 findings)
legacy_043 = "043"  (amibiguo — 3 findings)
```

Esto demuestra que:
1. **UUID → finding**: resolución única (no ambigua)
2. **display_number → finding**: sigue siendo ambiguo (como debe ser)

---

# 7. COMPARACIÓN CONTRA DOGFOOD-008

| Aspecto | DOGFOOD-007 (auditado) | DOGFOOD-009 (implementado) |
|---|---|---|
| Formato | 16 hex chars (64 bits) | 36 chars UUID (128 bits) |
| Tipo | SHA256(path)[:16] | UUIDv4 (RFC 9562) |
| Versión | N/A (no es UUID) | v4 |
| Independiente del path | ❌ NO | ✅ SÍ |
| Rename-safe | ❌ NO | ✅ SÍ |
| Move-safe | ❌ NO (si se regenera) | ✅ SÍ |
| Content edit-safe | ❌ NO (si se regenera) | ✅ SÍ |
| Serialization-safe | ❌ NO (si se regenera) | ✅ SÍ |
| Collisión 023 | ambiguo (path hash no ayuda) | UUID único por finding |
| Collisión 043 | ambiguo (path hash no ayuda) | UUID único por finding |

---

# 8. REGLAS EPISTÉMICAS VERIFICADAS

```text
PATH ≠ IDENTITY          ✓ (UUID no depende del path)
FILENAME ≠ IDENTITY       ✓ (UUID no depende del filename)
CONTENT_HASH ≠ IDENTITY   ✓ (UUID no depende del content)
DISPLAY_NUMBER ≠ IDENTITY ✓ (UUID no depende del display_number)
16 HEX ≠ UUID             ✓ (UUID es 36 chars, no 16)
PERSISTED TEXT ≠ GENERATED PERSISTENT ID ✓ (UUID generado con uuid4(), no path hash)
```

---

# 9. ESTADOS DE FRONTERA

```text
FINDING_ID_PHASE_A_VALIDATED = ✓
RELATION_GAP = OPEN (se mantiene, no se cierra)
FINDING_ID_MODEL = UUIDv4_PERSISTENT
IDENTITY_MODEL = VALIDATED (para los 5 findings piloto)
```

---

# 10. LO QUE NO SE HIZO

- NO se migraron los 347 findings existentes
- NO se migraron todas las relations
- NO se modificaron claims globales
- NO se modificó P003
- NO se tocó `trace_path.py`
- NO se tocó `evidence_search.py`
- NO se cerró RELATION_GAP

---

# 11. PRÓXIMO PASO

La siguiente fase (DOGFOOD-010) sería:
- Asignar UUIDs a findings existentes de forma controlada
- Migrar relaciones existentes que referencian `display_number`
- Sin migrar todo el corpus de una sola vez

Ver `GLOBAL WORK SCAN` para prioridades.

---

# 12. ENTREGABLES

```
benchmark/DOGFOOD-009.md
benchmark/dogfood-009/
  actual-id-values.json
  id-format-analysis.json
  path-hash-comparison.json
  generator-analysis.json
  rename-test.json
  move-test.json
  content-edit-test.json
  serialization-test.json
  collision-tests.json
  relation-resolution.json
  validation.log
```
