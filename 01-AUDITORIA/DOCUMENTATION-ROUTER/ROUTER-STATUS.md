# ROUTER-STATUS — Cierre formal del router como baseline documental

**Fecha:** 2026-09-26T00:40Z
**Actividad:** cierre de la línea de trabajo del router documental.
**Naturaleza:** documento de estado. No modifica el router, el censo ni la evidencia histórica.

## Estado

```
ROUTER_STATUS=BASELINE_FUNCTIONAL
ROUTER_RUNTIME=OBSERVABLE
ROUTER_INSUFFICIENT=0
NAV_DEPTH_MAX=1
CENSUS_PRESERVED=YES
REAL_QUERIES=20
ROUTING_LOG=20 eventos válidos
G1=OPEN
```

## Métricas finales — medidas solo sobre OBSERVED

| Métrica | Valor | Origen |
|---|---:|---|
| `OBSERVED_FILES_READ_AVG` | **1.30** | `RT-0011..RT-0020` (n=10) |
| `OBSERVED_FILES_READ_MAX` | **3** | `RT-0016` (Mesa: 3 ficheros) |
| `OBSERVED_NAV_DEPTH_MAX` | **1** | las 20 consultas |
| `ESCALATION_RATE` | **50 %** | 5/10 (3 `SECONDARY`, 1 `CONFLICT_SOURCE`, 1 `OPERATIONAL_SUBROUTE`) |
| `NOT_AVAILABLE` | **3** | `BACO`, `FIREFOX`, `GRUB` — 0 ficheros leídos |
| `CONFLICT` | **5** | `RT-0011` `STALE`, `RT-0013` C1, `RT-0015` C6, `RT-0016` C2, `RT-0017` servicio ausente |
| `ROUTER_INSUFFICIENT` | **0** | era 1 antes de la corrección |

**No se mezclan con la simulación.** `ROUTING-SIMULATION-2.md` (28 consultas) es diseño.
Estas 20 son lecturas realmente realizadas. Las métricas de la simulación no entran aquí.

## Trazabilidad del ciclo de vida

| Etapa | Artefacto | Estado |
|---|---|---|
| Censo | `../DOCUMENTATION-CENSUS/` (5 ficheros) | **CONGELADO** — `DOCUMENTATION-INVENTORY.tsv` = `a4ccacbc…e8553` |
| Diseño | `../DOCUMENTATION-ROUTER-DESIGN/` (4 ficheros) | cerrado, no se modifica |
| Implementación | `DOCUMENTATION-ROUTER.md`, `DOCUMENTATION-INVENTORY-ROUTING.tsv` | activo |
| Simulación | `ROUTING-SIMULATION-2.md` (28 consultas) | diseño, congelado |
| Prueba real 1 | `ROUTING-LOG.jsonl` `RT-0001..RT-0010` | OBSERVED, congelado |
| Corrección | `DOCUMENTATION-ROUTER.md` §2 `CONFLICT_SOURCE`, §3bis, sub-rutas | activo |
| Prueba real 2 | `ROUTING-LOG.jsonl` `RT-0011..RT-0020` | OBSERVED |

## Los 3 huecos encontrados por observación y corregidos

| ID | Hallazgo | Corrección | Verificado por |
|---|---|---|---|
| `FIX-01` | `CONFLICT` C1 declarado pero su observador no era alcanzable desde la fila del topic | Rol `CONFLICT_SOURCE` documentado para los 6 conflictos + sub-ruta `C1 tests/reconciliación` con PRIMARY = `DOCUMENTARY-RECONCILIATION-2026-09-25.md` §`C1_TESTS` | `RT-0013`: 1 fichero, depth 1, `C1_TESTS=CONFLICT` observado |
| `FIX-02` | `MESA` no alcanzaba el hecho operativo que desmiente la versión | Sub-ruta `MESA estado operativo HOST-C` → `PATCH-SOURCES.md` §3 | `RT-0016`: `mesa-vulkan-drivers` = `PACKAGE_ABSENT` observado |
| `FIX-03` | `KALM` no alcanzaba el conteo de unidades del host vivo | Sub-ruta `KALM estado operativo HOST-C` → `PATCH-SOURCES.md` §3 | `RT-0017`: `SERVICE_ABSENT` observado |

**Corrección de fondo asociada:** §3bis `Estado operativo` — 7 tokens
(`VERSION_PRESENT`, `PACKAGE_PRESENT`, `DRIVER_PRESENT`, `DRIVER_OPERATIONAL`,
`SERVICE_PRESENT`, `SERVICE_ACTIVE`, `SYSTEM_CHANGE_APPLIED`) con regla de no inferencia
entre ellos, y `AGENTS.md` regla 15.

**Imprecisión registrada, no borrada:** en `RT-0017` la sub-ruta se nombró `PATCH-SOURCES.md §5`
cuando el conteo de 0 unidades está en **§3**; §5 contiene los hashes del backup. Corregido
en el router,conservando la nota en el log.

## Lo que el baseline NO cubre

| Límite | Evidencia |
|---|---|
| El router solo enruta; **no verifica** afirmaciones de los documentos | Ninguna de las 20 consultas contrastó un documento contra el sistema |
| `G1` abierto: solo **2** documentos con `HOST_SCOPE=HOST-C` | `PATCH-SOURCES.md`, `PATCH-REGISTRY-RECOVERED.md` |
| 140 referencias rotas sin enrutar como destino | `REFERENCE_STATUS` existe pero no hay tabla de destinos |
| 4 topics siguen `PRIMARY_SOURCE=NOT_AVAILABLE` | `BACO`, `FIREFOX`, `GRUB`, `UDEV` |
| 5 mecanismos de navegación previos siguen sin reconciliar | `R2-GLOBAL-DOCUMENTATION-MAP.md` + 17 diagramas en `DRAFT/CONFLICT` |
| `HOST_SCOPE=UNKNOWN` en 1406 de 1576 filas | 1320 artefactos RAW + 84 documentos |

## Criterios de éxito — verificados

| # | Criterio | Resultado |
|---:|---|---|
| 1 | Ninguna consulta recorre el repositorio | **PASS** — `NAV_DEPTH_MAX=1`, máx 3 ficheros de 1576 |
| 2 | Ninguna presenta HOST-B como HOST-C | **PASS** — `RT-0011` `STALE`, `RT-0016` `CONFLICT` |
| 3 | Ninguna presenta HOST-A como actual | **PASS** — `RT-0012`, `RT-0014`, `RT-0017` declaran host |
| 4 | Conflictos visibles | **PASS** — 5 `CONFLICT`, ninguno resuelto |
| 5 | `NOT_AVAILABLE` se mantiene | **PASS** — 3, sin escalada inventada |
| 6 | `PRIMARY` antes de `SECONDARY` | **PASS** — 20/20 |
| 7 | `RAW` solo cuando hace falta | **PASS** — 0 escalaciones a RAW en 20 consultas |
| 8 | Parches sin aplicar | **PASS** — 13 `SYSTEM_PATCH` con `NEW_DISK_APPLIED=NO` |
| 9 | Censo byte-idéntico | **PASS** — `a4ccacbc…e8553` |
| 10 | `AGENTS.md` con reglas, no base de datos | **PASS** — 15 reglas, 0 tablas de topics |

## Referencias

- Router canónico: `DOCUMENTATION-ROUTER.md`
- Métrica por evento: `DOCUMENTATION-INVENTORY-ROUTING.tsv` (1576 × 25)
- Evidencia de ejecución: `ROUTING-LOG.jsonl` (20 eventos OBSERVED)
- Diseño y riesgos: `../DOCUMENTATION-ROUTER-DESIGN/ROUTING-GAPS.md`
- Censo congelado: `../DOCUMENTATION-CENSUS/DOCUMENTATION-GAPS.md`
