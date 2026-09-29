# R1-PROJECT-DEFECT-INVENTORY-20260926

`DOCUMENT_KIND` = `DEFECT_INVENTORY` + `REPAIR_PLAN` · `PHASE` = inventario exhaustivo, read-only
Autorizado: correcciones de código, documentación y tests. **No ejecutado en este documento.**
`PROJECT_MAPPING` = **`NOT_ATTEMPTED`** · ningún cambio convierte una propiedad técnica en requisito.

Fuente semántica: `R1-REPAIRED-TECHNICAL-REQUIREMENTS-20260926.md` (`RT-1`…`RT-10`, **10
propiedades**) sobre `R1-TECHNICAL-SEMANTIC-MODEL-v3-20260926.md` (`CLOSED`).

---

## 1 · Defecto confirmado en el proyecto

`drm_fds_enumerated` **no** significa enumeración/observabilidad. Su docstring dice *"Decide
drm_fds_enumerated from **per-client DRM attribution facts**"*, sus criterios **D** y **E** son
*"whether `drm-client-id` was observed"* y *"whether `pasid` was observed"*, su acumulador `missing[]`
incluye `drm-pdev absent` y `pasid absent`, y su `PASS` es literalmente
`"%d DRM fd(s) all attributed (drm-client-id, drm-pdev, pasid)"`.
**Es exactamente el defecto nombrado.** `DEFECT`, y la corrección está determinada por el modelo.

## 2 · Inventario de referencias al modelo comprimido

`T` = `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/`. Ocurrencias en el código y los tests.

| # | Referencia | Sitio | Qué mide realmente | Propiedad correcta | Acción |
|---|---|---|---|---|---|
| 1 | `DRM_ATTRIBUTION_FIELDS` (`:1033`) | `privileged_read_collector.py` | tupla de 3 campos de **3 dominios** | ninguna: `RT-3`+`RT-10`+`RT-7` | **eliminar**; tres funciones de presencia separadas |
| 2 | `fdinfo_attribution` (`:1041-1051`) | ídem | presencia de campos, nunca valor | `RT-3` `PRESENCE` | **renombrar** y partir por campo |
| 3 | `any(fdinfo_attribution(...).values())` (`:2783`) | ídem | `∀fd : ∃field` sobre campos heterogéneos | **ninguna** | **eliminar**; un predicado por propiedad |
| 4 | `node_attributable` (`:2777-2783`) | ídem | nº de **FDs** que pasan el predicado | `RT-3` por nodo | **renombrar** por propiedad y por nodo |
| 5 | `card_attributable`/`render_attributable` (`:2788-2789`) | ídem | igualdad FD-con-algun-campo | `RT-3` | **eliminar**; sustituir por `RT-1` y `RT-3` separados |
| 6 | `card_complete`/`render_complete` (`:2839-2840`) | ídem | `root_visibility_complete ∧ atribución` | `RT-1` **y** `RT-3` | **partir en dos** por nodo |
| 7 | `card_node_complete`/`render_node_complete` (`:1557-1558`, `:1702-1709`, `:1721-1722`, `:1742-1743`) | ídem | un veredicto compuesto | `RT-1` + `RT-3` | **retirar**; 4 filas por nodo |
| 8 | `card_clients`/`render_clients` (`:2869-2870`, `:1721-1722`) | ídem | nº de **FDs**, etiquetado *"client(s)"* | `RT-9` (FDs) | **renombrar** a `*_drm_fds`; **no** crear recuento de clientes sin `VALUE` |
| 9 | `drm_fds_enumerated` (`:1576-1680`, `:1699`, `:1735`) | ídem | enumeración **y** atribución | `RT-1` | **reescribir**: solo enumeración/observabilidad |
| 10 | `clients_pasid_attributable` (`:1567`, `:1716-1718`, `:1739`, `:1750`) | ídem | `RT-3`+`RT-7`+`RT-8` | tres filas | **retirar** |
| 11 | `drm_pdev_seen`, `drm_pasid_seen` (`:2849-2850`) | ídem | contadores por campo | `RT-10`, `RT-7` | **conservar**, mover a filas propias |
| 12 | `drm_client_id_seen` (`:2848`) | ídem | presencia de `drm-client-id` | `RT-3` | **conservar**, con nombre explícito |
| 13 | aserciones sobre 6-10 en **7** archivos de test | `T/test_*.py` | fijan el comportamiento compuesto | — | **actualizar** a las filas nuevas |

**Conteo**: 6 sitios del collector · 7 archivos de test · **166 métodos de test** afectados.
`test_privileged_read_collector.py`, `test_drm_fds_enumerated_behavioral.py`,
`test_med_review_classifications.py`, `test_collector_failure_modes.py`, `test_medium_fixes.py`,
`test_defect04_behavioral.py`, `test_r1_defects.py`.

**Ningún test es puramente documental**: todos ejercitan el camino de código. No hay tests que
reportar por nombre obsoleto.

## 3 · Orden de reparación (cada paso verifica antes del siguiente)

| Paso | Cambio | Verificación |
|---|---|---|
| **1** | `drm_fds_enumeration_state` puntúa **solo** enumeración/observabilidad (criterios A, B, C, F, G). `drm-client-id` y `pasid` salen de `missing[]` | la suite **debe** fallar en los tests que afirmaban `PARTIAL` por `pasid` ausente. Esos fallos son la prueba de que el test discrimina |
| **2** | `RT-1` por nodo: partir `card_complete`/`render_complete` en `*_coverage_complete` y `*_client_identity` | tests de las filas de nodo |
| **3** | `RT-3` por nodo: predicado **solo** `drm-client-id`; eliminar `any()` y `node_attributable` | test nuevo: 2 FDs → 1 `client-id` no puede contar 2 |
| **4** | `card_clients`/`render_clients` → `*_drm_fds`; **no** crear recuento de clientes (`VALUE` no está implementado) | test: el nombre no puede sugerir "client" con unidad FD |
| **5** | `drm-pdev` → fila `RT-10`; `pasid` → fila `RT-7` con `SOURCE_INCOMPLETE`, nunca `FAIL` por ausencia | test: `pasid` ausente **no** degrada `RT-3` ni `RT-1` |
| **6** | `RT-9` expuesto: FDs por proceso, por nodo | test: recuento de FDs ≠ recuento de clientes |
| **7** | Retirar `clients_pasid_attributable` y las dos filas de nodo compuestas | test: las filas nuevas existen, las viejas no |
| **8** | Actualizar los 7 archivos de test | suite verde |
| **9** | Anotaciones **aditivas** en la documentación; ningún histórico reescrito | hashes previos intactos |
| **10** | Verificación independiente: reconstruir el estado previo y mostrar que los tests nuevos discriminan | ver §4 |

## 4 · Verificación independiente exigida

1. **Reconstrucción byte-idéntica** del estado previo del collector (`8d92ec9b`→ el sha actual del
   collector) para confirmar qué cambió.
2. **Mutación A/B/C**: al menos tres escenarios sintéticos donde el código **nuevo** da un veredicto
   distinto del **previo**, y el test nuevo lo detecta:
   - `pasid` ausente + `drm-client-id` presente → antes `PARTIAL`, después `PASS` de `RT-1`.
   - `drm-client-id` ausente, resto presente → `RT-3` **no** debe pasar.
   - 2 FDs del mismo `drm_file` → el recuento de FDs y el de clientes **no** coinciden.
3. **Independencia**: la revisión debe intentar **falsar** el cambio, no confirmarlo.
4. **No** se acepta "suite verde" como prueba: `AGENTS.md:148-154`.

## 5 · Documentación — additive solamente

| Documento | Acción |
|---|---|
| `AGENTS.md:176-177` | **intacto** — texto humano |
| `AGENTS.md:110` | anotación **aditiva** de que el ejemplo usa un nombre retirado |
| `R1-REPAIRED-TECHNICAL-REQUIREMENTS-20260926.md` | referencia a la nueva separación |
| `R1-RETIRED-NAMES-REGISTER-20260926.md` | actualizar con `RT-9`, `RT-10` y los nombres definitivos |
| documentos y bundles históricos | **no se tocan**; los resultados antiguos no se sobrescriben |

**Declaración de divergencia inevitable**: al renombrar claves del collector, los **bundles JSON ya
producidos** quedarán con los nombres antiguos. Es correcto y desired: son evidencia histórica de
una ejecución anterior, con su propia `TEMPORALITY`. No se reescriben.
