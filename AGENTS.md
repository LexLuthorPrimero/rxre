# AGENTS.md — INSTRUCCIONES PERMANENTES DEL AGENTE (RXRE)

Estado: `ACTIVE` / `PRESERVED` (archivo creado para M284A; no sustituye controles ejecutables ni concede autorización).
No sustituye `tools/rxre/core/store.py`, contratos protegidos, esquemas (`operations`, `results`, `findings`), ni los mecanismos de `DB_AUTH_ACTOR_M294` / `DBOP_SCHEMA_M290`.

## IDENTIDAD DEL PROYECTO (2026-11-12 — `RXRE_IDENTIDAD.md`)
RXRE es un proyecto de investigación y autoría de método para la ingeniería inversa asistida por IA. Método: contribución primaria (método reproducible por terceros). Motor: línea experimental falsable; eficacia medida por binarios reales con cero divergencias y verificación autónoma por terceros, sin intervención del autor original. Para el estado real ver `RXRE_ESTADO.md`. Esta nota no sustituye §IDENTIDAD ARQUITECTÓNICA ni el resto de este documento.

## IDENTIDAD ARQUITECTÓNICA (definición canónica — M294)

RXRE es un motor de ingeniería inversa asistida por IA, de extremo a extremo, quirúrgico y automatizado. Sus principios operativos son: `extremo a extremo` (integración sin confundir integración con validación); `quirúrgico` (cambios mínimos, alcance delimitado, protección preservada); `automatizado` (planificación, ejecución, evaluación, validación y continuidad controladas); `asistido por IA` (razonamiento y decisión con evidencia verificable obligatoria); `epistemológicamente riguroso` (`PROVEN`/`PARTIAL`/`BLOCKED`/`INSUFFICIENT`/`NOT_DETERMINED` según corresponda; ausencia no prueba); `autonomía controlada` (la automatización nunca concede permisos que los controles de autorización deniegan).

Su objetivo arquitectónico es desarrollar un ciclo integrado de investigación que abarque: `1.` observación de sistemas y captura de evidencia; `2.` formulación de hipótesis causales; `3.` diseño de pruebas discriminantes; `4.` selección y ejecución controlada de herramientas; `5.` análisis de resultados y corrección de defectos; `6.` verificación de integridad, procedencia, alcance y reproducibilidad; `7.` persistencia de conocimiento con incertidumbre explícita; `8.` integración de conclusiones y planificación de nuevas investigaciones.

## IDENTIDAD OFICIAL — ARQUITECTURA ELEMENTAL DE RXRE

**Identidad oficial:** RXRE es un motor de ingeniería inversa asistida por IA, de extremo a extremo, quirúrgico y automatizado. Nombre de la arquitectura: **Arquitectura Elemental de RXRE**. Propósito: investigar, comprender, reconstruir y validar sistemas mediante un ciclo integrado de ingeniería inversa asistida por IA.

## LOS OCHO ELEMENTOS (funciones interdependientes de una sola arquitectura, no proyectos separados)

- **Cuerpo — Observación:** obtiene evidencia del objeto real (`m303_evidence_snapshot`, `capstone`, `readelf`, `sha256`, `dev`/`ino`).
- **Mente — Razonamiento:** formula hipótesis (`m322_claim_evaluator`), compara explicaciones (`benchmark_polari12`) y selecciona pruebas discriminantes (`test_` existente).
- **Alma — Propósito:** mantiene el objetivo (`mission_criteria`), criterios de éxito (`PASS`/`PASS PARTIAL`/`BLOCKED`/`NOT_DETERMINED`) y condiciones de cierre (`audit_log`, `execution_events`).
- **Tierra — Verificación:** valida integridad (`hash` + identidad física), procedencia (`store.conectar()` con `WAL`), alcance (`map_instr` `121` / `98785`) y respaldo de las afirmaciones (`evidence_refs` resoluble).
- **Fuego — Intervención:** realiza cambios mínimos (`m280_supervisor.py`, `AGENTS.md`), controlados (`autonomous_loop=False`, `max_iter_default=3`, `op_claim=False`) y reversibles (`reversibilidad` documentada; sin `DELETE`/`UPDATE` sobre `DB`).
- **Aire — Orquestación:** conecta decisiones (`capability_registry.select_capability`), herramientas (`m303`, `m322`, `m280`), acciones (`op:select`, `op:run` con `permissions="prompt"`) y resultados reales (`snap.decision`, `decisions` de `results`).
- **Agua — Aprendizaje:** conserva conocimiento verificable (`operations` + `results` con `row_hash`) y experiencia reutilizable (`AGENTS.md`; `m330_integration.py`; `test_m280_supervisor.py`).
- **Éter — Integración:** combina hallazgos (`M335`-`M349` `PASS PARTIAL`) y brechas (`NOT_DETERMINED` documentado; `0` referencias confirmadas con respaldo completo) para actualizar el modelo (`map_instr` + `graph` + `basic_block_map`) y orientar la siguiente misión (`M350`/`CONTINUE`).

## Regla operativa

Los ocho elementos son funciones interdependientes de una sola arquitectura, no ocho proyectos separados. Ciclo de referencia: `OBJETIVO -> OBSERVACION -> HIPOTESIS -> PRUEBA -> ACCION -> VALIDACION -> APRENDIZAJE -> INTEGRACION`. La IA debe reutilizar capacidades existentes (`m303`, `m322`, `m280`, `store.conectar()`, `map_instr`, contratos protegidos), identificar la brecha operativa real (`NOT_DETERMINED` documentado; `DB_AUTH_ACTOR_M294 BLOCKED`; `DBOP_SCHEMA_M290 INSUFFICIENT`; referencia completa `0` con respaldo completo `map_instr` + `RELA`/`GOT`/`PLT`) y conectar el flujo (`m330_integration.py` actualizado; `rx550_drv/M350_CIERRE.md` creado) antes de crear subsistemas nuevos. No afirmar autonomía integral hasta demostrar un ciclo completo con acciones efectivamente ejecutadas (`NOT_EXECUTED` documentado; `VERIFIED` con archivo creado), resultados observados (`PASS PARTIAL` con restricciones), validación independiente (`NOT_DETERMINED` para `DB_AUTH_ACTOR_M294`; `DBOP_SCHEMA_M290`) y cierre reproducible (`rx550_drv/M349_CIERRE.md`; `rx550_drv/M350_CIERRE.md`; determinismo verificado con archivo fijo `sha256=54e936d...`).

Preservar la distinción entre `VERIFIED`, `PASS PARTIAL`, `BLOCKED`, `NOT_DETERMINED` y `NOT_EXECUTED`. Nunca presentar simulación o documentación como ejecución real. `AGENTS.md` no sustituye `tools/rxre/core/store.py`, contratos protegidos, mecanismos de `DB` (`operations`, `results`, `findings`, `execution_events`, `audit_log`, `missions`, `mission_tasks`), ni controles ejecutables (`opencode` CLI, `store.conectar()`). No concede autorización (`DB_AUTH_ACTOR_M294` sigue `BLOCKED`); cualquier intento de persistencia que requiera `VERIFIED` (`M306`) debe documentar el bloqueo (`limitations`). No inicia bucles desatendidos (`autonomous_loop=False`; `max_iter_default=3`; `op_claim=False`); cualquier ejecución prolongada requiere autorización específica (`DB_AUTH_ACTOR_M294`). No inventa interfaces (`select_capability` existente; `capturar_evidencia` existente; `store.conectar()` existente); `m280_supervisor.py` es capa mínima sin reemplazar `tools/rxre/core/store.py`. No modifica `store.py`, esquemas, contratos protegidos, `DB` protegida (`rxre.sqlite3` con `WAL`). No afirma `PASS` sin verificación (`hash` + identidad física para `m303`; `evidence_refs` resoluble para `m322`); no afirma `PROVEN` sin cadena completa (`EVIDENCE` + `SEMANTICS` + `SCHEMA` + `DISCRIMINATING TEST` + `VALIDATION`).

## 1. MÉTODO (obligatorio para todas las misiones)

`EVIDENCE → SEMANTICS → SCHEMA → DISCRIMINATING TEST → IMPLEMENTATION → VALIDATION`

- `EVIDENCE`: captura real (`m303_evidence_snapshot` o equivalente existente); hash (`sha256`) + identidad física (`dev`/`ino`); nunca inventado ni inferido como evidencia.
- `SEMANTICS`: evaluación de claim (`m322_claim_evaluator` o contrato existente); `SUPPORTED`/`REFUTED`/`INSUFFICIENT`; no `PASS` a menos que corresponda a captura de integridad (`m303`).
- `SCHEMA`: registro en mecanismo existente (`operations` + `results` en SQLite WAL); `row_hash` verificado; `operation_id` y `result_id` recuperables por proceso independiente (`store.conectar()` con conexión separada).
- `DISCRIMINATING TEST`: regresión (`test_` existente); comparación con baseline (`benchmark_polari12`); no se afirma `PROVEN` sin contraste observable.
- `IMPLEMENTATION`: cambio mínimo en archivo permitido (`m280_supervisor.py`, `AGENTS.md`); sin modificación de `tools/rxre/core/store.py`, `tools/rxre/core/evidence_integrity.py`, contratos protegidos.
- `VALIDATION`: verificación independiente (`hash` coincide con manifest; `row_hash` coincide con `raw_json`; `decision` recuperado igual al original; `restrictions` documentadas; `limitations` no ocultadas).

## 2. ESTADOS DE EVIDENCIA (definidos; no convertibles)

- `PROVEN`: evidencia completa con integridad (`hash` + identidad física igual al descriptor), contraste discriminante (`PASS` en captura; `VALID` en contrato), recuperación independiente confirmada, y sin ocultación de limitaciones.
- `PARTIAL`: evidencia parcial con limitaciones documentadas (`restrictions` + `limitations`); no se afirma `PROVEN` ni se oculta `BLOCKED`.
- `BLOCKED`: precondición necesaria ausente o autorización denegada (`DB_AUTH_ACTOR_M294 BLOCKED`, `DBOP_SCHEMA_M290 INSUFFICIENT`, `op:claim` denegado, `MMIO` no permitido); se documenta como límite observado, no como defecto oculto.
- `INSUFFICIENT`: evidencia insuficiente para apoyar o refutar (`evidence_refs` vacío o no resoluble; manifest sin hash; `hash_esperado_registro` no coincidente); no se inventa evidencia ni se afirma ausencia como prueba.
- `NOT_DETERMINED`: no hay evidencia suficiente; no se declara `PROVEN` ni `REFUTED` por ausencia; no se afirma independencia GPUVM sin evidencia dinámica. Para GPU: validación de shaders SPIR-V vía `require_gpu()` es `PROVEN` acotado (E2E-006–E2E-019), pero `MMIO` directo, `sysfs`/`debugfs`, `UMR` permanecen sin verificar.

Regla: `PASS` solo para captura de integridad (`m303` o equivalente existente con `hash` + identidad física); `SUPPORTED` solo para claim (`m322` o contrato existente con `evidence_refs` verificadas); nunca `PROVEN` automático para ninguna capacidad sin cadena completa.

## 3. PROCEDENCIA (distinguida explícitamente, nunca inferida)

Para cada registro (`operation_id`, `result_id`):
- `SELECCIÓN`: `capability_registry.select_capability` o mecanismo existente (`op:select` en `machine.py`); no inventado por nombre de archivo.
- `INVOCACIÓN REAL`: llamada observable al mecanismo (`capturar_evidencia()` para `m303`; `evaluate_claim_evaluator()` para `m322`; `run_cycle()` del supervisor para `m280`); no construcción manual de datos sin invocación real.
- `RESULTADO DEVUELTO`: `decision` generado por mecanismo existente (`snap.decision` para `m303`; `DECISION_SUPPORTED`/`DECISION_REFUTED`/`DECISION_INSUFFICIENT` para `m322`); no asignación manual sin ejecución.
- `AUTORIZACIÓN`: `authorization_needed` verificado en `capability_registry`; `DB_AUTH_ACTOR_M294` verificado antes de afirmar persistencia; `DBOP_SCHEMA_M290` verificado; no se afirma autorización general por `authorization_needed=False`.
- `PERSISTENCIA`: `store.conectar()` (o `DB` existente con `WAL`); `operations` + `results` insertados con transacción (`commit`); `row_hash` verificado; `raw_json` recuperable.
- `RECUPERACIÓN INDEPENDIENTE`: segunda conexión (`store.conectar()` separada) que lee `results` por `result_id`; confirma `status`, `decision`, `hash_capturado` (si aplica), `restrictions`, `limitations`; sin volver a invocar mecanismo.

Regla: la existencia de una fila en SQLite (`results`) no prueba ejecución real; la ejecución real debe demostrarse por invocación observable al mecanismo (`m303`, `m322`, `m280`) y recuperación independiente confirmada.

## 4. AUTORIZACIÓN (no delegada por registro)

- `authorization_needed=False` (`capability_registry`) solo indica que la capacidad no requiere autorización para su evaluación; **no autoriza** la persistencia como `VERIFIED` ni la ejecución de `op:claim`, ni la modificación de `DB_AUTH_ACTOR_M294` / `DBOP_SCHEMA_M290`.
- **`DB_AUTH_ACTOR_M294`** — Estado actualizado (VERIFIER-001 a VERIFIER-005, 2026-11-05):
  - **IMPLEMENTADO**: Sistema de autorización con `authorize_and_consume()`, ledger hash-chained (`consumed.jsonl`), `audit_ledger`, `CONSUMER` whitelist, `fcntl flock` para exclusión mutua, re-derivación de decisión cross-process, escritura atómica (tmp+rename+fsync+dir.sync), permisos 0700/0600, validación estricta de esquema VR.
  - **PERMITIDO**: Autorización atómica de dictámenes en la ruta de promoción (R1–R7), consumo idempotente, anti-replay por operación, cross-process binding.
  - **BLOQUEADO**: Autenticidad independiente del emisor; protección contra reconstrucción total por mismo UID; acceso `root`. Estos límites permanecen documentados como `BLOCKED`.
  - `DB_AUTH_ACTOR_M294` **no es autorización general de escritura**: cualquier persistencia que requiera `VERIFIED` debe documentar el bloqueo (`limitations`). No se oculta ni se declara `PASS` sin autorización.
  - `AGENTS.md` no concede autorización. Cualquier intento de persistencia que requiera `VERIFIED` (`M306`) debe documentar el bloqueo.
- `DBOP_SCHEMA_M290 INSUFFICIENT`: cualquier operación que modifique esquema (`ALTER TABLE`, `CREATE TRIGGER` sobre `findings`, `results`, etc.) debe documentar la insuficiencia; no se declara `PASS` sin verificación del esquema.
- `op:claim`: no se activa (`DB_AUTH_ACTOR_M294 BLOCKED`); cualquier afirmación que requiera `VERIFIED` debe documentar el bloqueo, no eludirlo con `--auto` ni con construcción manual de datos.
- `op:run` con `--auto`: no se usa (`cli.json`: `session.permissions: "prompt"`); cualquier intento de bypass debe documentarse como `BLOCKED` o `INSUFFICIENT`, no como `PASS`.

Regla: `PASS` solo para captura de evidencia (`m303` con `hash` + identidad física verificada) o para evaluación de claim (`m322`) con `evidence_refs` verificables y `limitations` documentadas; no para autorización general ni para ejecución sin verificación.

## 5. SEGURIDAD (no eludible por registro ni por ausencia de verificación)

- `tools/rxre/core/store.py`: no modificable (`PROVEN` por ausencia de cambios en `git` / `md5sum` / `sha256` de archivo original); cualquier cambio debe ser `NOT_DETERMINED` hasta verificación independiente del archivo.
- `DB` protegida (`rxre.sqlite3` con `WAL`): no se borra (`DELETE` prohibido por `trg_results_no_delete`); no se actualiza (`UPDATE` prohibido por `trg_results_no_update`); solo `INSERT` (`APPEND_ONLY`) con `raw_json` completo y `row_hash` verificado.
- `tools/rxre/core/evidence_integrity.py`: no modificable (`PROVEN` por verificación de archivo original); cualquier cambio requiere `NOT_DETERMINED`.
- Contratos protegidos (`manifest_binding_contract.py`, `claim_evaluator.py`, `scope_provenance_contract.py`, `unified_verified_contract.py`): no se reemplazan; cualquier extensión debe ser archivo nuevo (`m280_supervisor.py`, `AGENTS.md`) sin modificar contratos protegidos.
- `op:claim`: no se activa (`DB_AUTH_ACTOR_M294 BLOCKED`); cualquier afirmación que requiera `VERIFIED` debe documentar el bloqueo, no eludirlo.
- **GPU / MMIO / debugfs / UMR** — Matriz de operaciones (actualizada M439, verificada por E2E-006–E2E-019):
  - **VALIDADO**: Ejecución de shaders SPIR-V mediante `require_gpu()` en RX 550/RADV Polaris12 (E2E-006 a E2E-019, 120+ targets, 0 fallos). Validación GPU=Oracle con oráculos independientes.
  - **PERMITIDO**: Compilación y ejecución de shaders Vulkan/SPIR-V a través de `vk_cf_test` y `require_gpu()`. No se modifica hardware.
  - **BLOQUEADO**: `MMIO` directo, `/dev/mem`, `sysfs`, `debugfs`, `UMR` en `amdgpu`, acceso `root`. Requiere privilegios que no existen en el entorno actual. `reproduce_verified.sh` no se invoca. Cualquier intento debe documentarse como `BLOCKED` o `INSUFFICIENT`, no como `PASS`.
  - **NO PROBADO**: Acceso a registradores de hardware sin API Vulkan. GPU UAPI independiente. Modificación de firmware o drivers.
  - **No se confunde** validación de shaders con autorización de MMIO. Una ejecución GPU exitosa no habilita acceso a `/dev/mem`, `sysfs` o `debugfs`.
- `sudo`: no se usa (`DB_AUTH_ACTOR_M294 BLOCKED`; `cli.json`: `session.permissions: "prompt"`).
- `opencode run --auto`: no se activa; `cli.json`: `permissions: "prompt"`; cualquier uso debe documentarse como `BLOCKED` o `INSUFFICIENT`.
- `AGENTS.md`: no sustituye `tools/rxre/core/store.py`, contratos protegidos, mecanismos de `DB` (`operations`, `results`, `findings`, `execution_events`, `audit_log`, `missions`, `mission_tasks`), ni controles ejecutables (`opencode` CLI, `store.conectar()`). No concede autorización (`DB_AUTH_ACTOR_M294` sigue `BLOCKED`).

Regla: cualquier registro (`op_...`, `res_...`) debe preservar `restrictions` + `limitations` con referencias a contratos existentes (`M306`, `DB_AUTH_ACTOR_M294`, `DBOP_SCHEMA_M290`); no se ocultan ni se declaran `PASS` sin verificación.

## 5-A. SANDBOX OBLIGATORIO Y SEAL-BEFORE-REVEAL

### Sandbox obligatorio

El módulo `tools/rxre/verifier/sandbox.py` implementa contención técnica real mediante `bwrap` (v0.12.0, rootless):

- **Configuración**: namespace de usuario + namespace de montaje; `--remount-ro /`; `--disable-userns`; HOME aislado y fresco; `/tmp` inexistente (TMPDIR=/scratch, borrado post-run); evidencia montada read-only en `/evidence`; resultados en `/out`; escritura permitida solo en `/out` y un HOME aislado.
- **Pruebas**: `tools/rxre/tests/test_independent_verifier.py` (6/6 PASS). T8 cerrado: 10/10 PASS reales (uid=1000, ns=user:[4026532718]): escritura solo en `/out` y `/home/vf`; evidencia/repo/tmp/sistema denegados; nested userns rc=1; remount de evidencia denegado.
- **Límite**: protege contra escritura fuera del directorio permitido, pero no garantiza independencia física ni root. Modo fail-closed: si `bwrap` no está disponible o falla, la operación se rechaza.

### Seal-Before-Reveal

Orden obligatorio (VERIFIER-001 a VERIFIER-008, 2026-11-05):

1. Capturar evidencia y calcular hash SHA-256.
2. Sellar (hash + timestamp + referencia de procedencia) antes de procesar el contenido.
3. Verificar integridad del sello.
4. Revelar o procesar el contenido solo tras verificación del sello.
5. Registrar cualquier transformación posterior como artefacto derivado, nunca como evidencia original.

El sello garantiza orden causal, no autenticidad externa. No se presenta el sello como prueba de que el contenido es auténtico por sí mismo.

### Admisión a TIERRA

La admisión a TIERRA utiliza exclusivamente la ruta autorizada existente:

- `scope_provenance == "EXPLICIT"` (obligatorio; `INFERRED`, `UNKNOWN` y scope ausente son rechazados).
- Referencias de procedencia resolubles.
- Correspondencia entre finding, productor y claim.
- Integración con la autorización del actor (`DB_AUTH_ACTOR_M294`).
- Prohibido: inserciones directas, promociones manuales, adaptadores alternativos, bypasses de la ruta de admisión.

La autorización para persistir, la admisión semántica a TIERRA, la autenticidad de la evidencia y la validez del claim son mecanismos distintos; no se sustituyen entre sí.

## 5-B. LÍMITE DE INDEPENDENCIA FÍSICA (E2E-039)

- Mientras exista un solo host físico independiente validado (`kalm`), la replicación externa completa permanece `BLOCKED`.
- Contenedores, namespaces, procesos y máquinas virtuales locales pueden servir para pruebas de aislamiento, pero no demuestran independencia física.
- No se crean identidades, hosts ni infraestructura para simular una segunda raíz de confianza.
- Distinción preservada: concurrencia multiproceso ≠ aislamiento multiUID ≠ independencia de host ≠ replicación externa.
- El límite E2E-039 no se elimina por el cierre de misiones E2E-006 a E2E-019; esas misiones validan generalización metodológica, no independencia física.

## 6. CAMBIOS MÍNIMOS, REGRESIONES, REVERSIBILIDAD Y CIERRE

- Cambios mínimos: `m280_supervisor.py` (nuevo archivo, no modifica `store.py`); `AGENTS.md` (nuevo archivo en raíz); `test_m280_supervisor.py` (pruebas aisladas, sin modificación de `tools/rxre/core/store.py`).
- Regresiones (`tests/` existentes): `test_integridad_adv_final.py` (8/8 `PASS`); `test_contrato_uniforme.py` (5/5 `PASS`); `test_reproducibilidad_end2end.py` (2/2 `PASS`); `test_semantica_estructural_contraste.py` (5/5 `PASS`). Cualquier cambio debe documentar `NOT_DETERMINED` si las regresiones fallan.
- Reversibilidad: cualquier cambio debe ser reversible (`AGENTS.md` puede eliminarse sin afectar `tools/rxre/core/store.py`; `m280_supervisor.py` puede eliminarse sin afectar `store.py`); `DB` no se modifica (solo `INSERT` con `OR IGNORE`, sin `DELETE`/`UPDATE`).
- Cierre auditable (`audit_log`): cada `register`, `create_finding`, `create_relation` debe registrar `actor` (`capability`, `producer`, `system`), `entity_type`, `entity_id`, `action`, `timestamp`. `execution_events` registra `op`, `capability`, `exit_status`, `persistido`, `trace_id`, `lecciones_json`.
- Cierre de misión (`missions` + `mission_criteria` + `mission_tasks`): cada misión debe tener `status` (`PENDING`/`COMPLETED`/`BLOCKED`/`FAILED`), `completed_at`, `last_checkpoint` recuperable; `research` debe documentar hipótesis, evidencia (`refs_json`), estado (`PROVEN`/`PARTIAL`/`NOT_DETERMINED`/`BLOCKED`).

Regla: `PASS` solo para captura de evidencia con integridad verificada (`hash` + identidad física); `PARTIAL` para evaluación de claim con limitaciones documentadas (`M306`, `DB_AUTH_ACTOR_M294`); `BLOCKED` para autorización denegada o precondición ausente; `NOT_DETERMINED` para ausencia de evidencia sin ocultación; `INSUFFICIENT` para evidencia sin referencia resoluble. No `PASS` sin verificación; no `PROVEN` sin cadena completa; no ocultación de `BLOCKED`.

## 7. DECLARACIÓN EXPLÍCITA (no sustituye controles ejecutables)

`AGENTS.md` no sustituye los controles ejecutables (`tools/rxre/core/store.py`, `tools/rxre/core/evidence_integrity.py`, contratos protegidos, `DB` con `WAL`, `opencode` CLI, mecanismos de autorización `DB_AUTH_ACTOR_M294` / `DBOP_SCHEMA_M290`). No concede autorización (`DB_AUTH_ACTOR_M294` sigue `BLOCKED`); cualquier intento de persistencia que requiera `VERIFIED` (`M306`) debe documentar el bloqueo (`limitations`). No inicia bucles desatendidos (`max_duration_s`, `max_iter` configurables en `m280_supervisor.py`); cualquier ejecución prolongada requiere autorización específica (`DB_AUTH_ACTOR_M294`). No inventa interfaces (`select_capability` existente; `capturar_evidencia` existente; `store.conectar()` existente); `m280_supervisor.py` es capa mínima sin reemplazar `tools/rxre/core/store.py`. No modifica `store.py`, esquemas, contratos protegidos, `DB` protegida (`rxre.sqlite3` con `WAL`). No afirma `PASS` sin verificación (`hash` + identidad física para `m303`; `evidence_refs` resoluble para `m322`); no afirma `PROVEN` sin cadena completa (`EVIDENCE` + `SEMANTICS` + `SCHEMA` + `DISCRIMINATING TEST` + `VALIDATION`).

## 8. MAPA ESTRUCTURAL DEL REPOSITORIO (v1)

Esta sección documenta la estructura real del repositorio basándose en el código existente, no en especificaciones futuras. Cada entrada está etiquetada con su estado epistemológico: `VERIFICADO` (confirmado en código/repositorio), `PARCIAL` (documentado pero con limitaciones), `NOT_DETERMINED` (insuficiente evidencia), o `BLOCKED` (restricción concreta).

### 8.1 Identidad del proyecto

- `VERIFICADO`: RXRE es un motor de ingeniería inversa asistida por IA, de extremo a extremo, quirúrgico y automatizado (AGENTS.md L8). Propósito: investigar, comprender, reconstruir y validar sistemas mediante un ciclo integrado de ingeniería inversa asistida por IA (AGENTS.md L14).
- `VERIFICADO`: Arquitectura Elemental de RXRE con 8 elementos (Cuerpo, Mente, Alma, Tierra, Fuego, Aire, Agua y Éter) + Puerta (AGENTS.md L16-25).
- `VERIFICADO`: Principios operativos: extremo a extremo, quirúrgico, automatizado, asistido por IA, epistemológicamente riguroso, autonomía controlada (AGENTS.md L8).

### 8.2 Árbol estructural (directorios principales)

| Directorio | Contenido verificado | Estado |
|---|---|---|
| `tools/rxre/arquitectura/` | 11 archivos: `__init__.py`, `AGUA.py`, `ALMA.py`, `ETER.py`, `AIRE.py`, `planos.py`, `PUERTA.py`, `ROUTER.py`, `schemas.py`, `TIERRA.py`, `mundo_real.py`. Los 8 componentes + __init__ + schemas. | `VERIFICADO` |
| `tools/rxre/arquitectura/planos.py` | MENTE (Hipotesis, Libro), CUERPO (medir/verificar_en_uso), FUEGO (Dispositivo, RollbackGlobalProhibido, FUEGO.aplicar/rollback). 3 planos sync directos. | `VERIFICADO` |
| `rx550_drv/` | M300_CIERRE.md a M397_CIERRE.md + `src/` (amdgpu_backend.c, bo.c, command.c, compute.c, core.c, device.c, diagnostics.c, gpuvm.c, index.md, queue.c, runtime.c, sync.c), `stages/`, `include/`, scripts (`reproduce_verified.sh`, `test_*.sh`), benchmarks, `M369_CIERRE.md`. 79 líneas de cierre M369 con cadena de llamadas comprobada. | `VERIFICADO` |
| `rx550_drv/src/` | 12 fuentes C: amdgpu_backend.c, bo.c, command.c, compute.c, core.c, device.c, diagnostics.c, gpuvm.c, queue.c, runtime.c, sync.c. No incluye capstone/objdump automático. | `PARCIAL` |
| `findings/` | 57 archivos: 1589.md a 1640.md + RXRE-PS5-001 a PS5-005. Hallazgos técnicos sobre RX550 (CP idle, VRAM, rings, etc.). | `PARCIAL` |
| `tests/` | 41 archivos de test (.py): test_301 a test_330 + test_323, test_324, test_325, test_326, test_327, test_329, test_330. Regresiones: integridad 8/8, contrato 5/5, reproducibilidad 2/2, semántica 5/5. | `PARCIAL` |
| `.rxre/audit.db` | Claims históricas + EV-VERIFICACION-V3-001 + EV-AUTORIDAD-LUCAS-001. Claims NOT_PROVEN. | `PARCIAL` |
| `.rxre/re/` | directorios capture_* (199 carpetas) + gpu0 + ingest_* + storage. Sin acceso hardware root (W5 bloqueado). | `BLOCKED` |
| `results/` | DOGFOOD_SESSION_1621.md (7627 bytes). | `PARCIAL` |
| `operations/` | bo_cpu_operations.md (486 bytes), index.md (215 bytes). | `PARCIAL` |
| `evidence/` | bo_cpu_evidence.md (1072 bytes), index.md (334 bytes). | `PARCIAL` |
| `06-INGENIERIA-INVERSA/` | Subdirectorio con findings. | `PARCIAL` |
| `04-IMPLEMENTACION/` | Subdirectorio rx550-driver. | `PARCIAL` |
| `08-ARQUITECTURA/` | AGENT-RE-TOOLING.md, FILTROS-REPARO-2.md, GRAFO-CLAVE-NO-UNICA.md, TOOLCAT-000-*.md, tools/. | `NOT_DETERMINED` (contexto externos) |
| `docs/` | INFORME_RXRE_PUB_001-016, DECISIONES_ESTRUCTURALES.md, PUERTA_CORR7.md, CONSOLIDADA V3.MD-V6.MD, etc. | `PARCIAL` |
| `core/` | No existe en la raíz del repositorio (script `store.py` localizado por `m330_integration.py` L94). | `NOT_DETERMINED` (ruta variable) |

### 8.3 Componentes de la Arquitectura Elemental y sus ubicaciones

| Componente | Archivo(s) principal(es) | Responsabilidad verificada | Estado |
|---|---|---|---|
| **Cuerpo** | `tools/rxre/arquitectura/planos.py` L144-174 (`class CUERPO`) | Observación real, hash verificado en punto de uso (`sha256` + `dev`/`ino`). `medir(ruta)` devuelve hash + bytes + etiqueta. `verificar_en_uso(m_id)` revalida hash vivo. | `VERIFICADO` |
| **Mente** | `tools/rxre/arquitectura/planos.py` L36-125 (`class Hipotesis`, `class Libro`) | Hipótesis rivales con falsificación explícita. Libro con preguntas, N respuestas, cada una con test. `decidir()` actualiza estado. `sin_resolver()` lista hipótesis sin resolver. | `VERIFICADO` |
| **Alma** | `tools/rxre/arquitectura/ALMA.py` L69-132 (`criterios_del_proposito()`, `evaluar_cierre()`) | Criterios de cierre evaluables (7 criterios v3: EVIDENCIA_CADA_CASILLA, SIN_HECHOS_SIN_ARTEFACTO, IDEMPOTENCIA, REPRODUCTIBILIDAD, LAS_7_V3, FALSIFICACION_ASOCIADA, NO_INVENTAR). `evaluar_cierre()` devuelve `NOT_DETERMINED` si algún criterio no es `PROVEN`. | `VERIFICADO` |
| **Tierra** | `tools/rxre/arquitectura/TIERRA.py` L196-585 (`class Grafo`) | Grafo de evidencia: claims (tabla `claims`), evidence (tabla `evidence`, append-only con triggers que prohíben DELETE/UPDATE), contradictions, reevaluations, claim_locks (concurrencia por operación, no global). `afirmar()` valida claim con `falsification_test`. `aportar()` agrega evidencia con `row_hash`. `reevaluar()` decide INVALIDATED/REVERTED/PARTIAL (NO automático). | `VERIFICADO` |
| **Fuego** | `tools/rxre/arquitectura/planos.py` L198-278 (`class FUEGO`, `class Dispositivo`) | Transformación controlada. Rollback por dispositivo (NO global: R12 prohíbe rollback global). `alcance_rollback()` compara pedido vs conocido. `aplicar()` transforma dispositivo, deja rastro. `rollback()` deshace UN dispositivo. | `VERIFICADO` |
| **Aire** | `tools/rxre/arquitectura/AIRE.py` L37-72 (`class Traza`) | Capa transversal que observa/registra todo. `Traza.decidir()`, `Traza.invocar()`, `Traza.producir()`. `emitir_traza()`, `reconstruir_traza()`, `tool_hash()`. Registra decisiones, invocaciones, resultados con hash SHA-256. | `VERIFICADO` |
| **Agua** | `tools/rxre/arquitectura/AGUA.py` L65-163 (`class Agua`, `class Aprendizaje`) | Aprendizaje con procedencia. `aprender()` guarda sin afirmar verdad (verificado_ok=NULL). `revalidar()` vuelve a comprobar contra mundo real (`a.reverificar()`). `recuperar()` == `revalidar()`. Fallo de revalidación devuelve `NOT_DETERMINED` (no `falso`). | `PARCIAL` (revalidar implementado; frontera TIERRA §22#5 pendiente) |
| **Router** | `tools/rxre/arquitectura/ROUTER.py` L60-143 (`class Router`, `class Productor`) | Resuelve capacidades, no nombres de herramientas. `resolver(capacidad)` devuelve estado + elegido. `candidatos(capacidad)` filtra producers disponibles. `cobertura()` mapa capacidad→productores. `invocar()` ejecuta productor si existe executor. | `PARCIAL` (resolver/invocar OK; scoring §22#4 pendiente) |
| **Puerta** | `tools/rxre/arquitectura/PUERTA.py` L1-260 (audit A-F → DELIVERED → revisión independiente → ACCEPTED; archivo real 260 líneas) | Gate de aceptación con 4 condiciones: artefactos_integros (hash SHA-256), cero_refutaciones_criticas, revisor_sin_participacion, autoridad_aceptacion_nombrada. Estado actual: **CONTESTED** (cond.1-2 cumplen; cond.3 pendiente revisor formal; cond.4 declarada lucas 2026-10-19). | `CONTESTED` (4 cond. evaluadas; cond.3 pendiente) |
| **Verificador Independiente** | `tools/rxre/verifier/` (`independent_verifier.py`, `sandbox.py`, `promotion.py`, `acceptance_policy.py`, `mission_closure.py`, `rxre_run.py`, `e2e_integrated.py`) | Verificación aislada con bwrap (user+mount ns, `--remount-ro`, `--disable-userns`), seal-before-reveal, 7 rutas de promoción (R1–R7) protegidas con `authorize_and_consume()`, ledger anti-replay, política fail-closed (`PROVEN`→ACCEPT_WITH_DOMAIN, `PARTIAL`→ACCEPT_LIMITED, `NOT_DETERMINED`→WITHHOLD, `BLOCKED`→DETACH). Integración E2E: VERIFIER-001 a VERIFIER-005 (PASS/PASS_PARTIAL), E2E-006 a E2E-019 (PASS_PARTIAL). | `PARTIAL_ACCEPTABLE` (VERIFIER-001: PROVEN 8/9 dims; VERIFIER-003: PASS 7/7 routes; VERIFIER-005: PASS con alcance; E2E: PARTIAL por host/UID/modelo compartidos) |

### 8.4 Flujos principales (codificados en el método)

`EVIDENCE → SEMANTICS → SCHEMA → DISCRIMINATING TEST → IMPLEMENTATION → VALIDATION`

| Flujo | Ubicación | Estado |
|---|---|---|
| `EVIDENCE` (m303) | `tools/rxre/arquitectura/planos.py` L144 (`CUERPO.medir()`) + `TIERRA.py` L293 (`Grafo.aportar()`) | `VERIFICADO` |
| `SEMANTICS` (m322) | `tools/rxre/arquitectura/ALMA.py` L52 (`Criterio.evaluar()`) + `TIERRA.py` L230 (`Grafo.afirmar()`) | `VERIFICADO` |
| `SCHEMA` (DB WAL) | `TIERRA.py` L76-177 (`SCHEMA_SQL`): claims tabla, evidence tabla con triggers `trg_evidence_no_delete`/`trg_evidence_no_update`/`trg_evidence_no_reparent`. `store.conectar()` con `isolation_level=None`. | `VERIFICADO` |
| `DISCRIMINATING TEST` | `tests/` (test_335/test_342 PASS, test_arquitectura_v3_03_mutacion.py 7/7 DISCRIMINA). `ALMA.evaluar_cierre()` verifica LAS_7_V3. | `PARCIAL` (tests existen; cobertura total depende de contexto) |
| `IMPLEMENTATION` | `m280_supervisor.py` (archivo nuevo, no modifica `store.py`). `autonomous_loop=False`; `max_iter_default=3`; `op_claim=False`. | `NOT_EXECUTED` (no aplicado en esta sesión) |
| `VALIDATION` | Recuperación independiente (`store.conectar()` separada lee `results` por `result_id`). `hash` coincide con `raw_json`; `row_hash` verificado. | `PARCIAL` (verificación independiente posible; DB_AUTH_ACTOR_M294 BLOCKED persiste) |
| `INDEPENDENT VERIFICATION` (VERIFIER-001 a VERIFIER-005) | `tools/rxre/verifier/`: `verify()` (bwrap sandbox), `authorize_and_consume()` (ledger anti-replay), `acceptance_policy.guard_promotion()` (gate fail-closed), `register_dictamen()`, `audit_ledger()`. | `PARTIAL_ACCEPTABLE` (8/9 dimensiones PROVEN; MODEL_DIVERSITY PARTIAL; same-UID BLOCKED; root BLOCKED) |

### 8.5 Puntos de entrada (dónde comenzar)

| Tarea | Punto de entrada | Justificación |
|---|---|---|
| Capturar evidencia de archivo | `CUERPO.medir(ruta)` en `planos.py` o `TIERRA.Grafo.aportar(...)` | Hash SHA-256 + dev/ino verificables |
| Evaluar claim | `Criterio.evaluar()` en `ALMA.py` o `Grafo.afirmar(...)` en `TIERRA.py` | Requiere `falsification_test` |
| Reevaluar claim (post-contradicción) | `Grafo.reevaluar(...)` en `TIERRA.py` | Decide INVALIDATED/REVERTED/PARTIAL, NO automático |
| Publicar evento crítico | `Eter.publicar(tipo, carga, critico=True)` en `ETER.py` | Write-ahead con fsync, idempotencia |
| Resolver capacidad de análisis | `Router.resolver(capacidad)` en `ROUTER.py` | Busca producer por capacidad declarada |
| Aprender lección | `Agua.revalidar(aprendizaje_id)` en `AGUA.py` | Vuelve a comprobar contra mundo real |
| Cerrar misión (gate) | `PUERTA.aceptar()` tras auditoría A-F | 4 condiciones; estado actual CONTESTED |

### 8.6 Persistencia y evidencia (ubicación de datos)

| Elemento | Ubicación | Restricciones verificadas |
|---|---|---|
| `claims` (tabla) | `TIERRA.Grafo` con `ruta` arbitraria (por defecto `:memory:` o archivo .sqlite3) | 6 estados epistemicos; triggers prohiben DELETE/UPDATE en evidence |
| `evidence` (tabla) | Mismo Grafo TIERRA; append-only con triggers `trg_evidence_no_delete`/`trg_evidence_no_update`/`trg_evidence_no_reparent` | `row_hash` verificado al leer; `supersedes_ref` para correcciones |
| `rxre.sqlite3` | `/home/lucas/Escritorio/rxre/rxre.sqlite3` (266240 bytes, 2026-10-19 intacto) | WAL mode; APPEND_ONLY; triggers `trg_results_no_delete`/`trg_results_no_update`; solo INSERT con `raw_json` y `row_hash` |
| `.rxre/audit.db` | `/home/lucas/Escritorio/rxre/.rxre/audit.db` | Claims históricos; EV-VERIFICACION-V3-001; EV-AUTORIDAD-LUCAS-001; NOT_PROVEN |
| `.rxre/re/capture_*` | 199 carpetas de captura | Sin acceso root (W5 UMR/MMIO/debugfs bloqueado) |
| `results/` | `/home/lucas/Escritorio/rxre/results/DOGFOOD_SESSION_1621.md` | Hallazgos de sesión; no modificado por M369 |
| `operations/` | `/home/lucas/Escritorio/rxre/operations/bo_cpu_operations.md` | Registro de operaciones booleanas |
| `evidence/` | `/home/lucas/Escritorio/rxre/evidence/bo_cpu_evidence.md` | Evidencia de CPU |

### 8.7 Pruebas (dónde estan y qué comportan)

| Test | Verificado | Comportamiento |
|---|---|---|
| `test_integridad_adv_final.py` | `PASS 8/8` | Integridad de evidencia (hash + dev/ino) |
| `test_contrato_uniforme.py` | `PASS 5/5` | Contrato uniforme de claims/evidence |
| `test_reproducibilidad_end2end.py` | `PASS 2/2` | Reproducibilidad determinista |
| `test_semantica_estructural_contraste.py` | `PASS 5/5` | Contraste estructural |
| `test_arquitectura_v3_02_v3.py` | `55 PASS, 0 FAIL` | Contratos v3 completos |
| `test_arquitectura_v3_01_contracts.py` | `35 PASS, 0 FAIL` | Contratos v3 básicos |
| `test_arquitectura_v3_03_mutacion.py` | `7/7 DISCRIMINA` + 90 PASS control | Mutación discrimina correcciones |
| `test_322_claim_evaluator.py` | Evaluator reclamacional | `SUPPORTED`/`REFUTED`/`INSUFFICIENT` |
| `test_323_research_integration.py` | `DB_TEST` temporal | Sin modificar DB operativa |

### 8.8 Documentación relacionada (referencias)

| Documento | Contenido | Referencia |
|---|---|---|
| `AGENTS.md` | Instrucciones vigentes, restricciones, 8 elementos, método, estados, seguridad | L1-250 (104 líneas originales + 146 de sección 8) |
| `RXRE_DIAGRAMA_REAL.md` | Diagrama de 10 componentes + Puerta basado en código | Archivo separado |
| `INVESTIGACION_E2E_RX550.md` | Investigación e2e RX550 con evidencia real | Archivo separado |
| `M369_CIERRE.md` | Cierre M369: ruta reutilizable análisis estático ELF | `rx550_drv/M369_CIERRE.md` |
| `M368_CIERRE.md` | Cierre anterior M368: sha256/readelf/stat sobre `/usr/bin/ls` | `rx550_drv/M368_CIERRE.md` |
| `PUERTA_CORR7.md` | Gate con declaración autoridad | `docs/PUERTA_CORR7.md` |
| `CONSOLIDADA V3.MD` | Especificación de referencia (intacta) | `CONSOLIDADA V3.MD` |
| `AUDIT_FINAL.md` | 219 líneas, apéndices subagentes | `AUDIT_FINAL.md` |
| `TRABAJO_EJECUTADO.md` | Log detallado de ejecución | `TRABAJO_EJECUTADO.md` |
| `CONSOLIDADO_EJECUTADO.md` | Resumen de ejecuciones | `CONSOLIDADO_EJECUTADO.md` |

### 8.9 Límites conocidos (restricciones operativas)

| Limitación | Fuente | Impacto |
|---|---|---|
| `DB_AUTH_ACTOR_M294 BLOCKED` | `AGENTS.md L69`; `m330_integration.py` L37 | Persistencia `VERIFIED` bloqueada; mecanismo autorizador no encontrado |
| `DBOP_SCHEMA_M290 INSUFFICIENT` | `AGENTS.md L70` | Cualquier `ALTER TABLE`/`CREATE TRIGGER` debe documentar insuficiencia |
| `W5` (UMR/MMIO/debugfs) | `AGENTS.md L88-93`; `RXRE_DIAGRAMA_REAL.md` L191 | `BLOCKED`: MMIO directo, `/dev/mem`, `sysfs`, `debugfs`, `UMR` en `amdgpu`, acceso `root` bloqueados. Validación GPU vía shaders SPIR-V `require_gpu()` es `PROVEN` acotado (E2E-006–E2E-019). |
| `54/72 sub-casillas` V6.MD | Sin tests ejecutables | Fuera de alcance de sesión actual |
| `op:claim` no activado | `AGENTS.md L4,48-49,69` | `DB_AUTH_ACTOR_M294 BLOCKED` impide activación |
| `autonomous_loop=False` | `AGENTS.md L94` | Sin bucles desatendidos; `max_iter_default=3` |
| `opencode run --auto` prohibido | `AGENTS.md L85` | `cli.json: permissions="prompt"` |
| `tools/rxre/core/store.py` no modificable | `AGENTS.md L78` | `PROVEN` por ausencia de cambios en git/md5sum/sha256 |
| `rxre.sqlite3` protegida | `AGENTS.md L79` | Solo INSERT con `OR IGNORE`; `DELETE`/`UPDATE` prohibidos por triggers |
| `Contratos protegidos` | `AGENTS.md L81` | `manifest_binding_contract.py`, `claim_evaluator.py`, `scope_provenance_contract.py`, `unified_verified_contract.py` |
| `GPU/MMIO/debugfs/UMR` | `AGENTS.md L88-93` | Matriz: shaders SPIR-V `require_gpu()` `PROVEN` acotado; MMIO directo, `/dev/mem`, `sysfs`, `debugfs`, `UMR` `BLOQUEADO`. |
| `Sin sudo` | `AGENTS.md L84` | `DB_AUTH_ACTOR_M294 BLOCKED`; `cli.json: session.permissions: "prompt"` |

### 8.10 Orientación para una IA nueva (secuencia mínima de lectura)

Para comprender RXRE antes de proponer cambios:

1. **Leer `AGENTS.md`** L1-250: identidad, 8 elementos, método, estados de evidencia, procedencia, autorización, seguridad, cambios, declaración, mapa estructural (sección 8). (`VERIFICADO`)
2. **Inspeccionar `tools/rxre/arquitectura/`**: `__init__.py` declara 11 componentes; cada archivo implementa uno de los 8 elementos + __init__ + schemas. (`VERIFICADO`)
3. **Revisar `planos.py`**: MENTE (Hipotesis/Libro), CUERPO (medir/verificar_en_uso), FUEGO (Dispositivo/Rollback). Estos 3 planos tienen sync directo. (`VERIFICADO`)
4. **Leer `TIERRA.py`**: Schema claims/evidence con triggers append-only; 6 estados; concurrencia por operación; `reevaluar()` NO automático. (`VERIFICADO`)
5. **Leer `ALMA.py`**: 7 criterios de cierre evaluables; `evaluar_cierre()` devuelve `NOT_DETERMINED` si algún criterio no es `PROVEN`. (`VERIFICADO`)
6. **Leer `ETER.py`**: Hub async con write-ahead, 3 modos fallo, cola acotada, estadísticas contadas. (`VERIFICADO`)
7. **Leer `AGUA.py`**: Aprendizaje con procedencia; `revalidar()` vuelve a comprobar; `NOT_DETERMINED` si no se puede revalidar. (`PARCIAL`)
8. **Leer `ROUTER.py`**: Resuelve capacidades, no nombres; `resolver()` devuelve estado + elegido; `invocar()` ejecuta productor. (`PARCIAL`)
9. **Leer `PUERTA.py`**: Gate con 4 condiciones; estado actual CONTESTED (cond.3 pendiente revisor formal). (`CONTESTED`)
10. **Ejecutar tests** solo cuando el alcance de la tarea y la autorización vigente (`DB_AUTH_ACTOR_M294 BLOCKED`, `DBOP_SCHEMA_M290 INSUFFICIENT`) lo permitan: `test_integridad_adv_final.py` (`PASS 8/8`, antecedente documentado); `test_contrato_uniforme.py` (`PASS 5/5`, antecedente); `test_reproducibilidad_end2end.py` (`PASS 2/2`, antecedente). No habilita ejecución automática ni privilegios de hardware (`autonomous_loop=False`; `max_iter_default=3`; `op_claim=False`). (`PARCIAL`)

---

Hash anterior: `3428847c85539d745c1fb4ab4c06538845aa3efc3e93adfbcbefe9ae0b0aed39`



### 8.11 Reconocimiento tecnológico exterior (2026-11-12)

Existe un reconocimiento sistemático repositorio-level en `RECONOCIMIENTO-TECNOLOGICO/` (añadido el 2026-11-12 durante rodaje anónimo sin ventana operativa). Contiene:

- `INVENTARIO.md` — 74 fichas tecnologías (28 propias, 30 externas, 4 adaptadas, 6 compuestas, 6 experimentales), con estado `IMPLEMENTADA → INVOCABLE → INTEGRADA → VALIDADA`.
- `RESUMEN.md`, `DEPENDENCIAS.md`, `CAPACIDADES.md`, `EVIDENCIAS.md`, `LIMITACIONES.md`, `SYNC.md`, `manifest.sha256`.

Datos operativos que añade:

- Los inventarios históricos **27/24/13 tecnologías NO se ratifican**; el repositorio contiene ~6 GB de clones vendorizados (mlflow, semgrep, llvm-project, linux, VK-GL-CTS, mesa, piglit…) **sin consumidor de primer nivel observado**.
- La ruta real del núcleo es `tools/rxre/core/store.py`, no `core/store.py` (raíz, inexistente) referido en versiones antiguas de §8.2.
- Las cifras `tests 55/55` etc. citadas en §8.7 son **documentales**; este reconocimiento **no re-ejecutó** ninguna suite.
- La herramienta `rea-agents` (instalada fuera del repo, `/home/lucas/Escritorio/rea-install`) **no está integrada al pipeline**; `tools/rea/` vendorizado permanece sin consumidor.

Ningún elemento de este anexo autoriza integración, promoción de estados ni ejecución fuera de lo ya permitido en `§5`/`§7`.

## 9. ARQUITECTURA RXRE + REA — FUSION INTEGRADA (v1, actualizado 2026-10-24)

### 9.1 Identidad del motor fusionado (VERIFICADO por AGENTS.md L8, L16-25, L104-250)
RXRE + REA es un motor de ingeniería inversa asistida por IA, de extremo a extremo, quirúrgico y automatizado. Los ocho elementos operan como capacidades funcionales de un mismo sistema, no proyectos independientes. No sustituye `tools/rxre/core/store.py`, contratos protegidos, mecanismos de DB (`DB_AUTH_ACTOR_M294 BLOCKED`; `DBOP_SCHEMA_M290 INSUFFICIENT`), ni `AGENTS.md`. Estado: `PASS PARTIAL` para diseño (`M397`); `NOT_DETERMINED` para `0x366 -> 0x6e80`; `BLOCKED` para resolución dinámica.
### 9.2 Restricciones preservadas
- `DB_AUTH_ACTOR_M294 BLOCKED`; `DBOP_SCHEMA_M290 INSUFFICIENT` (`VERIFICADO`); `autonomous_loop=False`; `max_iter_default=3`; `op_claim=False`.
- `fixture_synthetic=True`; `fixture_evidence_labeled=True`.
- `NOT_DETERMINED`: `0x366 -> 0x6e80` (archivo `.rela.dyn` confirma `0x6fb8`; `.rela.plt` confirma `0x6e78`/`0x6e80`; destino `.plt` sin cadena completa).
- `BLOCKED`: dinámica (`DB_AUTH_ACTOR_M294`); `W5` (`UMR/MMIO/debugfs`); GPU UAPI independiente; ejecución binario; `op:claim`; `op:run --auto`; `sudo`; `GPU/MMIO/UMR/debugfs`; `/dev/mem`.
### 9.3 Cierre M397
M397 cerrado (`PASS PARTIAL`): entregables (`rx550_drv/M397_DISENO_FUSION.md` `7003` bytes; `/tmp/m397_resultado.json` `3389` bytes); restricciones intactas; `M388` `NO INICIADO`; `DB` `266240` operativa; contratos protegidos intactos (`5aa0f244...`/`dbcb9674...`); `fixture_synthetic` documentado; `fixture_evidence_labeled` documentado; `AGENTS.md` actualizado con esta sección 9; sin invento; sin ocultación; sin modificación código/DB; `NOT_DETERMINED` preservado; `BLOCKED` documentado.
Nota M432: integracion E2E con flujo existente (e2e_integrated.py) reutilizando M427-M431; desconexiones reales documentadas (sim_memory M426, find M430, langgraph/letia/qdrant/ofrak NO INSTALADAS); capacidad general NOT_DETERMINED; PROVEN solo para ciclos observados; bases protegidas intactas; restricciones preservadas.
Nota M433 (2026-10-26): Reconstruccion y validacion diferencial completada sobre /tmp/m431_target (rebuild gcc -O0, rollback guardado, 6 casos diferenciales IDENTICOS, persistencia res_m433_e01, PROVEN solo para equivalencia de comportamiento concreto, NOT_DETERMINED general, restricciones preservadas, sin invento ni ocultacion).
Nota M434 (2026-10-26): Reconstruccion guiada por descubrimiento sobre /tmp/m434_target (hash 0e245fff...); especificacion derivada (clasificacion HIGH/MID/LOW + caso limite SHORT); reconstruccion reversible (/tmp/m434_rebuilt_433) validada diferencialmente; reproducibilidad confirmada; persistencia res_m434_e01 recuperada con integridad; PROVEN solo para objetivo concreto; NOT_DETERMINED para capacidad general; restricciones preservadas.
Nota M435 (2026-10-26): Transferencia a estructura nueva (2 bytes comparacion /tmp/m435_target, hash bdf81bd...); especificacion derivada (MATCH/GT/LT/EQ/SHORT); reconstruccion reversible (/tmp/m435_rebuilt_435); validacion diferencial con limite y reproducibilidad; persistencia res_m435_e01; PROVEN solo objetivo concreto; NOT_DETERMINED capacidad general; sin transferencia indebida de reglas M434; restricciones preservadas.
Nota M436 (2026-10-26): Reconstruccion de control de flujo sobre /tmp/m436_target (hash 0a648a4d...); ramas anidadas/combinadas (AA->sub-rama b1>55, BB, OTHER, SHORT) descubiertas con evidencia; H2 (solo primer byte) refutada; H3 NOT_DETERMINED; especificacion derivada; reconstruccion reversible (/tmp/m436_rebuilt_436); validacion diferencial; persistencia res_m436_e01; restricciones preservadas.
Nota M437 (2026-10-26): Poder discriminante sobre /tmp/m437_target (hash cb3a577b...); tres hipotesis rivales con predicciones previas (H1/H2/H3); H2 refutada por evidencia; H3 NOT_DETERMINED; especificacion derivada post-evaluacion; reconstruccion reversible (/tmp/m437_rebuilt_437); validacion diferencial con cobertura justificada; persistencia res_m437_e01; restricciones preservadas.

Nota M437-REFLEXIVE (2026-10-26): Ciclo reflexivo en modo sombra (PASS_PARTIAL). ALMA propone revision de criterios de cierre (bloqueada DB_AUTH_ACTOR_M294); MENTE registra metodo/predicciones/resultado/confianza=no_calibrada; TIERRA documenta hechos/inferencias/decisiones/incertidumbres sin sustituir evidencia; AGUA recupera M437 (operativo.sqlite3) y rechaza transferencia de reglas especificas a M436 (irrelevante incluido); integracion registra reflexion sin modificar decisiones operativas (autonomous_loop=False, max_iter_default=3). PROVEN solo si cambio observable de decision respaldado; PASS_PARTIAL confirmado; NOT_DETERMINED para interioridad/capacidad general/activacion automatica. Restricciones preservadas; rollback documentado.

Nota M438 (2026-10-26): Transferencia reflexiva controlada sobre /tmp/m436_target (hash 0a648a4d...; diferente de M437). PROVEN: reflexion cambia decision concreta (predicciones previas registradas, NOT_DETERMINED preservado, transferencia rechazada con M434/M436, propuesta ALMA registrada, restricciones intactas) respaldada por evidencia; NO PROVEN capacidad general de aprendizaje operativo. PASS_PARTIAL. Restricciones preservadas; rollback documentado.
Nota M439 (2026-10-26): M439 PASS_PARTIAL; linea base estatica (Warframe.x64.exe hash=eec0d..., 45521792 bytes, PE32+; Heroic/Steam dual-install; RX550/11GB/1366x768; RADV/Mesa 26.2.4, Vulkan 1.4.341); juego no iniciado (BLOCKED/NOT_EXECUTED; launcher.exe ausente; intento seguro timeout 15s fallido); restricciones intactas; H1-H6 documentadas (NOT_DETERMINED); optimizaciones propuestas reversibles; rollback documentado; persistencia res_m439_e01 verificada; AGENTS.md/M414 actualizados; sin subsistema nuevo; sin modificacion de bases protegidas.

## Biblioteca externa RXRE-RESEARCH

**Ubicación:** `/home/lucas/Escritorio/RXRE-RESEARCH` (absoluta), `../RXRE-RESEARCH` (relativa desde RXRE). Material externo de investigación para ACRE/EDICT/AASE; **no** núcleo ejecutable de RXRE.

**Estructura:** `01_ACRE_BINARY_SURGERY/` (P2Patch, CodeHawk, KALPA, BRAVADO), `02_EDICT_BINARY_COMPILATION/` (BASIL, BIRD, Cozy, Ghidra-PCode), `03_AASE_AUTONOMOUS_SCIENCE/` (Kosmos, AutoLabs, AutoDNA, CoScientist, Chemist-X), `04_ADVERSARIAL_VERIFICATION/`, `05_PAPERS_AND_DOCUMENTATION/`, `06_DATASETS_AND_BENCHMARKS/`, `07_LICENSES_AND_PROVENANCE/`, `INVENTORY.md`.

**Reglas operativas:**
1. No ejecutar código descargado sin evaluación previa de seguridad, licencia, dependencias y aislamiento.
2. No instalar dependencias externas durante auditorías documentales.
3. No copiar código a RXRE sin análisis de licencia, procedencia, necesidad y compatibilidad arquitectónica.
4. No confiar en las conclusiones de una herramienta al evaluar esa misma herramienta.
5. Toda reutilización debe tener mecanismo de validación independiente.
6. Hash válido demuestra integridad respecto del manifiesto, **no** autenticidad del autor ni seguridad del contenido.
7. Distinguir estrictamente: `DESCARGADO / INTEGRIDAD_VERIFICADA / PROCEDENCIA_VERIFICADA / LICENCIA_VERIFICADA / ANALIZADO / EJECUTABLE / EVALUADO / INTEGRADO / VALIDADO`.
8. `NOT_VERIFIED` significa no verificado, **no** inexistente ni no disponible.
9. No alterar repositorios externos originales durante su evaluación. Informes propios en área de resultados separada.
10. No modificar bibliotecas privadas como dependencias del núcleo (no promover licencias sin verificación).

**Integración documental (M325-DOC):** rel. a ACRE (causal, parche mínimo, diferencial, rollback), EDICT (lifting/IR, flujo, reconstrucción, instrucción↔comportamiento), AASE (reproducibilidad, automatización, ejecutor↔verificador, falsación adversarial).

## Trazabilidad M295–M329 (índice)
- M295–M306 (§40–§51 §41.2659 … §63B418) · compara: Plan Maestro co-locado + /tmp/m295…m306. Resinstein: ls/grep/find `54e936d3…/f0320b67…/2d805195…`
- M307 §52 · §53 M308 lab→/tmp/m308_lab (certificate `de6b3163…`) · M309–M316 §54–§61 contratos (M311 `/tmp/m311_diff 47e9e037…`, M312 `/tmp/m312_cert 54efe235…`) · M313–M317 §58–§62 trans. (M317 `/tmp/m317_cert c51be87a…`)
- M318–M322 §63–§67 (M318 tx aislada memoria; M319 log persistido test37 /tmp/m319_txlog; M320 flock; M321 PREPARE≠COMMITTED; M322 tmpfs `DURABILITY_PARTIAL`)
- M323–M324 §68–§69 (M323 `/tmp/m323_sem4` corrupto `STATE_TRANSITION_INVALID`; M324 `/tmp/m324_oracle/two-axis`; métricas 12)
- M325 §70 lab `/tmp/m325_lab a3a91cbf…` · M325-DOC / pre-M326 §71 biblioteca (AGENTS § Biblioteca) · M326 §72 (`/tmp/m326_audit d0cab0e1…`) · M326-STRUCTURE §71 corr. (8 áreas objetivo vs árbol físico)
- M327–M329 §73–§75 EDICT (M327 `/tmp/m327_lab_target e98a815d…`, M328 `/tmp/m328_pcode_eval 5832d600…`, M329 `/tmp/m329_cert 917781ec…`)
- **Plan §75 `05276d3b… MD5 da18b515…` 3 copias OK | M308+M311/M312 intactos**
regla vigente: M330 cierra con Plan §75 (sin §76 admitido M326-STRUCTURE); si mañana se entrega actualización total, se evalúa su compatibilidad en misional

## Trazabilidad M295–M336 (índice M337-DOC — §82 M336 PASS_PARTIAL)
- M295–M306 (§40–§51; Plan `bfc333af…` ver histórico; /tmp/m295…m306 pers.
- M307 §52 · §53 M308 lab→/tmp/m308_lab (certificate `de6b3163…`) · M309–M316 §54–§61 contratos (M311 `/tmp/m311_diff 47e9e037…`, M312 `/tmp/m312_cert 54efe235…`) · M313–M317 §58–§62 trans. (M317 `/tmp/m317_cert c51be87a…`)
- M318–M322 §63–§67 (M318 tx aislada memoria; M319 log persistido test37 /tmp/m319_txlog; M320 flock; M321 PREPARE≠COMMITTED; M322 tmpfs `DURABILITY_PARTIAL`)
- M323–M324 §68–§69 (M323 `/tmp/m323_sem4` corrupto `STATE_TRANSITION_INVALID`; M324 `/tmp/m324_oracle/two-axis`; métricas 12)
- M325 §70 lab `/tmp/m325_lab a3a91cbf…` · M325-DOC / pre-M326 §71 biblioteca 8 áreas objetivo (AGENTS § Biblioteca) · M326 §72 (`/tmp/m326_audit d0cab0e1…`) · M326-STRUCTURE §71 corr. (8 áreas objetivo vs árbol físico)
- M327–M329 §73–§75 EDICT (M327 `/tmp/m327_lab_target e98a815d…`, M328 `/tmp/m328_pcode_eval 5832d600…`, M329 `/tmp/m329_cert 917781ec…`)
- M330 §76 blueprint · M331 §77 recorrido (`/tmp/m331_path`; §438CAF04… vrd? — ref.)
- M332 §78 generalizado (segunda `27acbc92…`; CONFLICT ref. CR-Ls64 vs 438CAF04… preservado campo)
- M333 §79 ciego (`/tmp/m333_lab d714786b…`) · M334 §80 (oráculo math)
- M335 §81 stress cableado (`/tmp/m335_stress 9fedfa4d…`)
- M336 §82 EDICT (`/tmp/m336_contract e2b9e0fd…`, `/tmp/m336_eval 778d5329…`; idiosincrasia CR-Ls64→438CAF04… M332 reubicada; CRificar resolución hacia M337)
- **Plan §82 `a500ef61… MD5 ace8cd2e…` 3 copias OK | M308+M311/M312 intactos**

## Trazabilidad M295–M336 (único índice vigente M337-DOC — §82 M336 PASS_PARTIAL; histórico M295–M329 preservado)
- M295–M306 (§40–§51; /tmp/m295…m306 PRESENT_PERSISTENT/TEMPORARY MISSING según lot)
- M307 §52 · M308 lab→/tmp/m308_lab (certificate `de6b3163…`) PRESENT_PERSISTENT
- M309–M316 §54–§61 contratos (M311 `47e9e037…`, M312 `54efe235…`) PRESENT_TEMPORARY
- M313–M317 §58–§62 trans. (M317 `c51be87a…`) PRESENT_TEMPORARY
- M318–M322 §63–§67 (M318 tx memoria; M319 `/tmp/m319_txlog`; M320 flock; M321; M322 tmpfs `DURABILITY_PARTIAL`) PRESENT_TEMPORARY
- M323–M324 §68–§69 (`/tmp/m323_sem4`, `/tmp/m324_oracle`) PRESENT_TEMPORARY
- M325 §70 `/tmp/m325_lab a3a91cbf…` PRESENT_TEMPORARY
- M325-DOC §71 biblioteca 8 áreas (AGENTS § Biblioteca) PERSIST
- M326 §72 (`/tmp/m326_audit d0cab0e1…`) PRESENT_TEMPORARY · M326-STRUCTURE §71 corr. PERSIST
- M327 §73 `/tmp/m327_lab_target e98a815d…`, cert `/tmp/m327_cert.json` MISSING
- M328 §74 `/tmp/m328_pcode_eval 5832d600…` PRESENT_TEMPORARY
- M329 §75 `/tmp/m329_cert 917781ec…` PRESENT_TEMPORARY
- M330 §76 blueprint · M331 §77 recorrido (`/tmp/m331_path`; SHA `438CAF04… vrd` ref. histórico)
- M332 §78 generalizado (segunda `27acbc92…`; CONFLICT ref. CR-Ls64 vs 438CAF04… preservado campo)
- M333 §79 ciego (`/tmp/m333_lab d714786b…`) · M334 §80 (oráculo math)
- M335 §81 stress cableado (`/tmp/m335_stress 9fedfa4d…`)
- M336 §82 EDICT (`/tmp/m336_contract e2b9e0fd…`, `/tmp/m336_eval 778d5329…`; idiosincrasia CR-Ls64→438CAF04… reubicada)
- **Plan §82 `2f882456… MD5 ea54a792…` 3 copias OK | M308+M311/M312 intactos**


## 10. PRINCIPIOS OPERATIVOS — AMPLIACIÓN ARQUITECTÓNICA (ACRE/EDICT/AASE/Hardware Bridge/Autonomous Capability Discovery)

**Estado:** anexo operativo autorizado explícitamente (consolidación documental 2026-11-07, opción 2, usuario). **No** sustituye controles ejecutables (`tools/rxre/core/store.py`, contratos protegidos, DB/WAL/triggers, mecanismos `DB_AUTH_ACTOR_M294`/`DBOP_SCHEMA_M290`, `opencode` CLI, sandbox). **No** concede autorización, **no** activa TIERRA/`op:claim`/`--auto`/`sudo`, **no** inicia bucles desatendidos, **no** modifica esquemas/contratos/código por sí mismo.

- **Separación de niveles:** `RXRE_PLAN_MAESTRO.md` = visión, arquitectura objetivo y evolución (con madurez etiquetada). `AGENTS.md` = principios operativos e invariantes para agentes. Cualquier capacidad descrita como objetivo debe tratarse como `OBJECTIVE_NOT_IMPLEMENTED`/`PARTIAL`/`NOT_DETERMINED`/`BLOCKED` hasta evidencia verificable en el alcance afirmado.
- **Madurez honesta (ACRE/EDICT/AASE/Hardware Bridge/Discovery):** no declarar integrado, automático, universal o `PROVEN` sin cadena completa, alcance explícito y validación independiente. Demos acotadas ≠ capacidad general. Componente presente ≠ capacidad demostrada.
- **Descubrimiento de capacidad (invariante):** antes de crear subsistema nuevo o integrar, demostrar la brecha con evidencia, reutilizar mecanismos existentes, y aplicar cambio mínimo auditable/reversible. Si la brecha no está evidenciada, **no** modificar pipeline/código protegido “por previsión”.
- **Integración verificable:** ruta aditiva ≠ hook automático end-to-end demostrado. `/tmp`/artefacto de demo ≠ capacidad persistente integrada. Probar integración o certificar `NOT_IMPLEMENTED`/`PARTIAL` con límites explícitos.
- **Separación epistémica (refuerzo):** observación directa ≠ inferencia acotada ≠ nominal. Llamada/valor observado ≠ atribución matemática/causal probada (aj.3). Candidato (`TRANSFORM`/`OUTPUT`/dataflow) ≠ relación probada. Coincidencia finita ≠ equivalencia/causalidad/OOB. Prohibida promoción injustificada de `PARTIAL`/`NOT_DETERMINED`.
- **Autorización, hardware y seguridad:** preservar `DB_AUTH_ACTOR_M294`/`DBOP_SCHEMA_M290`, TIERRA, matriz GPU/MMIO/UMR/debugfs/`/dev/mem`/root (AGENTS §5), sin `sudo`/`--auto`/bypass. Autonomía controlada ≠ permiso implícito. `autonomous_loop=False`; `max_iter_default=3`; `op_claim=False` salvo autorización específica verificable.
- **Reutilización acotada:** caso evidenciado (p. ej. GMP/`write_counts` u otros dominios acotados) **no** generaliza a otros binarios/operaciones sin discriminantes, evidencia adicional y validación diferencial.

## 11. CONGELAMIENTO DOCUMENTAL Y CIERRE DE EXPEDIENTE (2026-11-12)
Decisión del propietario: `autorizo todo` (plan de remediación completo). Regla vigente:
- **Doc-freeze**: no se aceptan documentos narrativos nuevos ni secciones nuevas hasta que exista verificación autónoma de terceros para RXRE R3. El estado vive en `AGENTS_ESTADO_GENERADO.md` (generado por `tools/rxre/verify_integrity.sh`), este archivo y el expediente `/tmp/rxre-r3/EXPEDIENTE_R3.md`.
- `tools/rxre/verify_integrity.sh` añadido (solo lectura); ejecutado 2026-11-12: **fallos=0**.
- Suites citadas **re-ejecutadas 2026-11-12** (rc=0): `test_integridad_adv_final` 8/8, `test_contrato_uniforme` 5/5, `test_reproducibilidad_end2end` 2/2, `test_semantica_estructural_contraste` 5/5, `test_arquitectura_v3_02_v3` 55/55, `test_arquitectura_v3_01_contracts` 35/35, `test_arquitectura_v3_03_mutacion` 7/7. Las citas "tests/ existentes" se refieren a `tools/rxre/tests/`.
- Rutas canónicas corregidas: `tools/rxre/core/store.py`, `tools/rxre/core/evidence_integrity.py`.
- Clones vendorizados archivados fuera del repo: `tools/rxre/github/` → `/home/lucas/Escritorio/RXRE-ARCHIVE-2026-11/rxre-tools-github-clones` (6,9 GB; **no borrados**; manifiesto `MANIFEST_2026-11-12.txt` con tamaño y HEAD de cada clon). Sin consumidor de primer nivel observado. Repo 14 GB → 6,5 GB.
- `tools/rea/`: **NO INTEGRADO** (sin consumidor de pipeline; `rea-agents` externo no integrado).
- Inventarios históricos 27/24/13: **NOT_RATIFIED**; base = `RECONOCIMIENTO-TECNOLOGICO/` (74 tecnologías).
- `KytyPS5-Source/build` (3,2 GB) y `RESEARCH/working` (521 MB): presentes, sin consumidor de pipeline verificado; no se borran.
- PUERTA: condición 3 pendiente desde 2026-10-19 → estado `PENDING_EXTERNAL_REVIEWER` (bloqueado hasta revisor humano externo; nombre y fecha pendientes del propietario).
- Tercera copia física del Plan Maestro: **NO LOCALIZADA** → discrepancia permanente aceptada; ediciones futuras solo de las dos copias verificadas por `cmp`.
- `import angr` roto (finding 1573): no se afirma capacidad angr.
- RXRE R3: **OPEN** — cero divergencias en generación 1 y 2 (selladas, 34.145×2), clean-room 6/6, caja negra 250/250 (`ls -v`); verificación de terceros **NOT_EXECUTED**. Ninguna etiqueta promovida; ningún PASS hasta terceros + revisión humana.
- Hash vigente de este archivo: ver `sha256sum AGENTS.md`; histórico preservado.
