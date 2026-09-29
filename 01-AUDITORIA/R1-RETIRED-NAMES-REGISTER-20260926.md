# R1-RETIRED-NAMES-REGISTER-20260926

`DOCUMENT_KIND` = `NAME_SUPERSESSION` · `ORIGINAL_REQUIREMENT` = **`MIXED/AMBIGUOUS`**
`TECHNICAL_PROPERTIES` = `RT-1`…`RT-8` · `PROJECT_MAPPING` = **`NOT_ATTEMPTED`**
Cierra `MIXED_REQUIREMENT_SEPARATED`. No modifica código, tests, `AGENTS.md` ni `README.md`.

Trazabilidad: este registro **añade** la supersesión. **No reescribe** los documentos que contienen
los nombres retirados, ni el collector, ni los tests. `AGENTS.md:240-243` (no sobrescribir evidencia
histórica) y `:250-251` (reportar referencias rotas, no repararlas) se respetan.

---

## 1 · El término humano, tal como queda

> `AGENTS.md:176-177` — "`FULL` requires complete attributable evidence for the RX550's card and
> render nodes, identified by PCI identity rather than by node name"

`ORIGINAL_REQUIREMENT` = **`MIXED/AMBIGUOUS`** — una formulación, **no** una propiedad.
El texto humano **no se modifica**. No se sustituye por una frase normativa inventada.

## 2 · Nombres retirados y qué los reemplaza

Cada fila nombra conceptos técnicos que ese nombre **pretendía** cubrir a la vez. Ninguna fila es una
norma; cada columna de la derecha es una propiedad técnica independiente con su propia unidad.

| Nombre retirado | `STATUS` | Donde vive todavía (sin tocar) | Reemplazado por |
|---|---|---|---|
| `ATTRIBUTABLE` / "attributable evidence" | **`RETIRED`** · `AMBIGUOUS` | `AGENTS.md:176-177` (**texto humano, preservado**) | `RT-1` + `RT-2` + `RT-3` + `RT-4` + `RT-5` + `RT-6` + `RT-7` + `RT-8` |
| `DRM_ATTRIBUTION_FIELDS` | **`RETIRED`** · `NAME_NOT_EVIDENCE` | collector `:1033`, `:2783`; `test_med_review_classifications.py` | `drm-client-id` → `RT-3` · `drm-pdev` → `RT-2` · `pasid` → `RT-7` |
| `clients_pasid_attributable` | **`RETIRED`** · `NAME_NOT_EVIDENCE` | collector `:1567`; `AGENTS.md:110` (ejemplo de nomenclatura) | `RT-3` + `RT-7` + `RT-8` |
| `card_node_complete` / `render_node_complete` | **`RETIRED`** como nombre de propiedad | collector `:1557-1558`, `:2839-2840`; 3 tests | `RT-1` (cobertura) **y** `RT-3` (identidad), con veredictos separados |
| `drm_fds_enumerated` | **`REFORMULADO`** · `PROJECT_ONLY` | collector `:1576` | `RT-1` por nodo; el agrupamiento **pooled** card+render no corresponde a ninguna propiedad |
| `card_clients` / `render_clients` | **`PROJECT_ONLY`** · `NAME_NOT_EVIDENCE` | collector `:2869-2870`; tests | recuento de **FDs** (no es una propiedad técnica) · `RT-3` `DISCRIMINATION` sería el recuento de `drm_file` distintos |
| `CLIENT_PROCESS_ASSOCIATION` | **`PROHIBIDO`** | no existe; declarado en `AGENTS.md` y en la especificación | **composición** de `RT-3` + `RT-4`; no es una propiedad nueva |

**Ningún nombre retirado se reinterpreta.** Se registra qué agravaba, y qué lo reemplaza.

## 3 · Nombres de la especificación, y por qué estos

| # | Nombre vigente | Unidad | Entidad caracterizada |
|---|---|---|---|
| `RT-1` | `NODE_COMPLETENESS` | proceso / descriptor | tabla de FDs de un proceso |
| `RT-2` | `DRM_NODE_PCI_IDENTITY` | nodo (`drm_minor`) | el nodo, por su PCI |
| `RT-3` | `DRM_FILE_CLIENT_IDENTITY` | `drm_file` | el fichero abierto DRM |
| `RT-4` | `DRM_FILE_PROCESS_ASSOCIATION` | par (`drm_file`, instante) | qué proceso usa el `drm_file` |
| `RT-5` | `DRM_CLIENT_MEMORY_STATS` | agregado por `drm_file` | consumo de memoria de ese cliente |
| `RT-6` | `DRM_CLIENT_ENGINE_ACTIVITY` | `drm_file` × engine | tiempo de engine dedicado a ese cliente |
| `RT-7` | `GPU_VM_PASID_PROCESS_RELATION` | vmid | vmid ↔ proceso, condicional |
| `RT-8` | `GPU_PAGE_FAULT_CLIENT_ID` | bloque del motor | la unidad de hardware que causó el fault |

**Dos nombres de la lista de partida se rechazaron, con motivo del modelo, no de preferencia**:

- `DRM_CLIENT_IDENTITY` → rechazado. El modelo establece (`C-2`) que *client* colisiona con al menos
  tres entidades (`drm_file`, master, page-fault de amdgpu). Usarlo como nombre reintroduciría la
  ambigüedad que esta separación elimina. La unidad demostrada es **`drm_file`**.
- `DRM_NODE_IDENTITY` → rechazado como propiedad distinta. En el modelo la **identidad del nodo es
  una precondición** (`gpu_proven`), no una propiedad: la propiedad del nodo es **cobertura**
  (`RT-1`), y su fuente es `/proc`, no sysfs. Añadir una tercera propiedad de nodo no está
  respaldado por el modelo.

## 4 · Criterio de terminación

No existe **ningún nombre vigente** que represente simultáneamente identidad de cliente, proceso,
nodo, dispositivo PCI, VM/PASID, memoria y engine. `RT-1`…`RT-8` tienen significado independiente, y
`GPU_PAGE_FAULT_CLIENT_ID` conserva `C-1` abierto sin fusionarse con `RT-3`.

El modelo técnico **no** decide el requisito de proyecto: `PROJECT_MAPPING = NOT_ATTEMPTED`.
Ninguna propiedad se cierra como exigida por `OWNERSHIP=FULL`.
