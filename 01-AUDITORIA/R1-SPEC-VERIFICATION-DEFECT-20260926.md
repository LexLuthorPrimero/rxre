# R1-SPEC-VERIFICATION-DEFECT-20260926

`DOCUMENT_KIND` = `VERIFICATION` + `DEFECT_RECORD` · `VERDICT` = **`DEFECT_FOUND`**
Verifica `R1-REPAIRED-TECHNICAL-REQUIREMENTS-20260926.md`. No re-deriva ninguna propiedad.
`CODE_CHANGE_ALLOWED = NO` · `READ_ONLY` · **el defecto NO se corrige aquí**.

---

## D-01 · `RT-3 MUTABILITY` sobreafirma la inmutabilidad de `drm-client-id`

- `CLASSIFICATION` = `NON_BLOCKER` — no reconstruye el compuesto defectuoso; acota un campo de una
  propiedad ya correctamente separada. Razón: la separación no depende de este campo, y ningún
  predicado, nombre ni decisión del proyecto lo consume hoy.

### Ubicación (6 ocurrencias, 2 documentos)

| Fichero | Línea | Texto |
|---|---|---|
| `R1-REPAIRED-TECHNICAL-REQUIREMENTS-20260926.md` | 33 | *"`drm-client-id`, 1:1, inmutable"* |
| `R1-REPAIRED-TECHNICAL-REQUIREMENTS-20260926.md` | 130 | *"`MUTABILITY`: **`client_id` inmutable**"* |
| `R1-TECHNICAL-SEMANTIC-MODEL-v3-20260926.md` | 103 | *"`client_id` y `minor` **inmutables**"* |
| `R1-TECHNICAL-SEMANTIC-MODEL-v3-20260926.md` | 118 | *"`MUTABILITY`: **inmutable**"* |
| `R1-TECHNICAL-SEMANTIC-MODEL-v3-20260926.md` | 340 | *R-04 `MUTABILITY`: **inmutable*** |
| `R1-TECHNICAL-SEMANTIC-MODEL-v3-20260926.md` | 373, 489 | *"R-04 … `u64` inmutable frente a `struct pid` mutable"* |

### Causa

Observación de una implementación elevada a contrato de interfaz. Es la
misma clase de error que `C-4` y que el error previo **#8** ("generalizar una implementación a la
spec"), cometido **en mi propio documento**.

### Evidencia de falsuración del defecto

1. **Una sola escritura en todo el core leído**:
   `drm_file.c:142 file->client_id = atomic64_inc_return(&ident);` — en `drm_file_alloc`.
   Las otras dos coincidencias son la lectura (`:943 drm_printf`) y la declaración.
2. **El campo es público y escribible**: `drm_file.h:281-282` — `/** @client_id: A unique id for
   fdinfo */ u64 client_id;`. No hay `const`, ni campo privado, ni protección. **Un driver puede
   escribirlo.**
3. **La spec promete unicidad, no estabilidad**: `drm-usage-stats.rst:64-72` dice *"Unique value"*,
   *"should map 1:1"* y el alcance de unicidad. **No dice en ningún punto que el valor sea estable
   durante la vida del `drm_file`.**

### Por qué importa

`inmutable` sin alcance Lee dos cosas distintas: (a) que el **core** no lo reasigna — `ESTABLISHED`;
(b) que la **interfaz** lo garantiza — `NOT_ESTABLISHED`. La diferencia es exactamente la que separa
`client_id` de `pid`, y por tanto la que sostiene la no-colapsión `drm-client-id ≠ PID`. Sin
acotarla, la línea 33 y la 373 presentan la distinción como si descansara en una inmutabilidad
contrastada, y no en la evidencia que realmente la sostiene.

### Corrección mínima propuesta (NO aplicada)

Sustituir el enunciado de inmutabilidad por uno con alcance explícito, en las 6 ubicaciones:

> `MUTABILITY`: **el core lo asigna una vez**, en `drm_file_alloc`, y no lo reasigna en ninguna
> ruta del core leído. El campo es **público**, de modo que la inmutabilidad **no** es un contrato
> de la interfaz; la spec promete **unicidad**, no estabilidad. No es la misma clase de atributo que
> `drm_file.pid`, que el core **sí** reasigna en una condición documentada.

Requiere autorización aparte. **No se aplica en esta tarea.**

---

## Verificación de la separación — resultado

| Punto | `STATUS` |
|---|---|
| RT-1..RT-8 son propiedades independientes | **`VERIFIED_SEPARATED`** — 8 unidades distintas; ninguna definida como conjunción de otras (grep `RT-[1-8] ∧` → 0 coincidencias) |
| Ninguna definición reintroduce "attributable" como compuesta | **`VERIFIED`** — 0 apariciones de `attributable` como nombre de propiedad |
| Sin `any(RT-*)` / `all(RT-*)` / `RT-1 ∧ RT-3` / `RT-3 ∧ RT-7 ∧ RT-8` | **`VERIFIED`** en los documentos técnicos; **el compuesto sigue vivo en el collector** (`PROJECT_ONLY`, ver `R1-SPEC-VERIFICATION-20260926.md` §residuales) |
| RT-3 no se describe como "12 clientes" | **`VERIFIED`** en el doc reparado; el residuo "12 clients" queda en `R1-C1-CORRECTION-CLOSURE-20260926.md:326` como **evidencia histórica no reescribible** (`AGENTS.md:240-243`) |
| `PASID` observado no prueba `PASID`→PID | **`VERIFIED`** — `RT-7 WHAT_IT_DOES_NOT_PROVE` lo dice; la co-ocurrencia `pasid 43`/PID 1923 es un `join` de `AGENT_FORMALIZATION` |
| Ausencia de `drm-engine-*` = `NOT_OBSERVED`, nunca "sin actividad" | **`VERIFIED`** — `RT-6 CURRENT_STATE = NOT_OBSERVED`; la spec **sí** está disponible, luego no es `SOURCE_INCOMPLETE` |
| Modelo técnico separado de los requisitos del proyecto | **`VERIFIED`** — `PROJECT_MAPPING = DEFERRED_PENDING_SPEC_CLOSURE`; `PROJECT_DOCUMENT` no aparece como semántica del kernel |
| `PROJECT_MAPPING` no ejecutado | **`VERIFIED`** |
