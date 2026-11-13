# AGENTS.md — INSTRUCCIONES PERMANENTES DEL AGENTE (RXRE)

Estado: **ACTIVE** (2026-11-13). Autoridad y precedencia:

1. Instrucciones explícitas de la sesión actual.
2. Evidencia verificable en el árbol/tag/manifest vigente.
3. Este archivo.
4. Historial (`METRICAS_R3.md`, `EXPEDIENTE_R3.md`, `docs/`).

Nada en este archivo concede autorización. La autorización explícita de la sesión tiene prioridad sobre cualquier cláusula general; la ausencia de autorización exige detenerse o pedirla.

## 1. Invariantes no negociables

- **No** modificar `tools/rxre/core/store.py`, `tools/rxre/core/evidence_integrity.py`, contratos protegidos (`manifest_binding_contract.py`, `claim_evaluator.py`, `scope_provenance_contract.py`, `unified_verified_contract.py`), esquemas append-only ni `rxre.sqlite3` (`WAL`) sin autorización expresa y verificación independiente posterior.
- **No** usar `sudo`, root, `/dev/mem`, MMIO directo, `sysfs`, `debugfs`, UMR, `--auto`, `op:claim` o bucles autónomos sin autorización explícita de la sesión y límites verificables.
- **No** publicar, hacer push, crear tags, releases, issues, comentarios u outreach, ni aceptar datos de fuentes externas como RXRE, sin autorización expresa del propietario en la sesión.
- **No** presentar documentación, sello, hash o informe como prueba de autenticidad, independencia o validación por terceros.
- **No** declarar `PASS`/`PROVEN` fuera de los requisitos de evidencia de §3.

## 2. Scope permitido vs. fuera de scope

| Acción | Permitida sin autorización | Requiere autorización explícita |
|---|---|---|
| Leer repositorio, corpus sellados, logs | Sí | No |
| Editar el repo con alcance pedido y preservar cambios ajenos | Sí, si la sesión lo pide | Si el scope es ambiguo o toca invariantes |
| Ejecutar tests/verificadores locales autorizados | Sí | No |
| Reconstruir propiedades acotadas fuera del repo público | Sí | No, mientras sean reversibles y sin datos privados |
| Modificar DB, contratos, API protegida, esquemas | No | Sí |
| Push, tag, release, issue comment, redes/outreach | No | Sí |
| Instalar/actualizar dependencias fuera del repo | No | Sí |
| Acceso hardware/privilegios elevados | No | Sí |

La publicación de `rxre-engine`/`rxre-cleanroom` v1.9.0 el 2026-11-13 fue autorizada explícitamente por el propietario. **No implica** autorización para futuras publicaciones.

## 3. Estados epistémicos y evidencia mínima

Separar siempre: observación, evidencia verificada, inferencia acotada y capacidad general.

- `PROVEN`: integridad sellable (`hash` + identidad física/descriptor), cadena verificable, recuperación/verificación independiente, contraste observable y sin ocultar limitaciones.
- `SUPPORTED`: claim respaldado por `evidence_refs` verificables. No usar para evidencia de integridad.
- `PASS`: solo integridad/captura con hash verificado. Nunca capacidad general.
- `PARTIAL`: evidencia parcial con scope, restricciones y limitaciones explícitas.
- `BLOCKED`: precondición o autorización ausente (`DB_AUTH_ACTOR_M294 BLOCKED`, `DBOP_SCHEMA_M290 INSUFFICIENT`, `op:claim` denegado, `W5` no permitido). Se documenta como límite, no se elude.
- `INSUFFICIENT`: evidencia presente pero sin referencia resoluble o descriptor incompleto.
- `NOT_DETERMINED`: ausencia de evidencia no prueba nada; no se declara `PROVEN` por ausencia.
- `NOT_EXECUTED`: no se ejecutó.

Reglas:

- `hash válido` demuestra integridad frente a lo que esperás, no autenticidad del origen ni seguridad.
- La fila en SQLite no prueba ejecución; demostrar invocación real y recuperación por proceso separado cuando aplique.
- La ausencia de terceros no se sustituye con auto-revisión; seguir `NOT_EXECUTED` hasta que un tercero lo haga.
- Conflicto entre árbol/tag/manifest y claim histórico: **gana el árbol/tag/manifest**; reportar la discrepancia.

## 4. Qué es RXRE hoy (estado real)

- RXRE es un **motor de investigación en ingeniería inversa asistida por IA**, no un producto, no un descompilador general y no un driver GPU.
- Evidencia pública: `rxre-engine` y `rxre-cleanroom` **v1.9.0**; **seis** objetivos acotados (`filenvercmp`, `wc`, `fold`, `tr -s x`, `dirname`, `basename`) con **0 divergencias** en su dominio declarado.
- Estado epistemológico público: **PARTIAL**; verificación de terceros: **NOT_EXECUTED**; PUERTA condición 3: **PENDING_EXTERNAL_REVIEWER**.
- **P0**, descubrimiento semántico general sobre binarios sin conocimiento previo: **OPEN/NOT_DETERMINED**.
- RX550: caracterización/experimentos Vulkan/SPIR-V pueden ser evidencia auxiliar; **no** un driver ni una capacidad GPU general.

## 5. Flujo operativo mínimo

Para cualquier tarea:

1. **Inspeccionar antes**: `git status --short`, leer los archivos concretos; no tocar cambios ajenos.
2. **Acotar**: problema, dominio, entradas, oráculo, artefactos y qué no se reclama.
3. **Evidenciar**: hash/manifiesto/sello; si falla, fail-closed.
4. **Cambiar mínimo**: preservar invariantes; trabajo reversible; revertir ante deriva.
5. **Verificar**: comando/verificador aplicable; comparar antes/después; registrar resultado exacto.
6. **Cerrar**: declarar qué se probó, qué no, qué tercero falta y qué quedó `BLOCKED/NOT_DETERMINED`.

Para publicaciones/releases: usar la autorización explícita de la sesión; verificar clon/fresh zip después de publicar; nunca anunciar `PASS` ni “verificado por terceros” sin informes externos reales.

## 6. DOC-freeze y mantenimiento de este archivo

- No añadir narrativa, historial de misiones ni mapas nuevos a este archivo.
- El estado vigente va en `AGENTS_ESTADO_GENERADO.md`/`METRICAS_R3.md` o en el expediente; no en prosa aquí.
- La historia (`M295`–`M350`, v1.x) vive en `METRICAS_R3.md`, `EXPEDIENTE_R3.md`, `docs/RXRE_CHANGELOG.md` y el repo público. No es ley ejecutable.
- §8 mapa y §9/§10 históricos de la versión anterior fueron eliminados de este archivo deliberadamente; si hicieran falta, se generan o se leen desde su ubicación histórica.

## 7. Criterio de parada y escalado

Detener y reportar antes de seguir si aparece cualquiera de estos:

- hash/manifest/sello no coincide;
- archivo ajeno modificado, merge conflict o deriva no atribuible;
- la tarea pide publicación/externa o acción irreversible sin autorización explícita;
- el árbol contradice claim documentado;
- no hay forma de distinguir evidencia de documentación;
- el objetivo exigiría hardware/privilegios fuera de scope;
- la respuesta honesta sería ocultar un `BLOCKED` o promover una etiqueta.

## 8. Referencia operativa

- Código y verificación: `tools/rxre/`, `tools/rxre/tests/`, `evidence/r3/` en `rxre-engine`.
- Corpus/sellos: `manifest.txt`, `SHA256SUMS`, `EXPEDIENTE_R3.md` en `evidence/r3/`.
- Estado y métricas: `METRICAS_R3.md` (privado), `docs/RXRE_CHANGELOG.md` y releases públicos.
- Objetivo de cierre: **reproducibilidad por terceros**, no más artefactos internos ni más tags.

Regla final: **código y evidencia ganan; la historia informa; la autorización manda; la ausencia de evidencia no prueba nada.**
