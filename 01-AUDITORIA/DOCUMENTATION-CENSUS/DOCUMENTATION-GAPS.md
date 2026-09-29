# DOCUMENTATION-GAPS — Huecos, contradicciones, roturas y duplicados

**Fecha:** 2026-09-25T22:40Z
**Fase:** FASE 0 — censo. **Nada se reparó, se renombró ni se eliminó.**

Clasificación usada: `CONFLICT`, `SUPERSEDED`, `STALE`, `BROKEN_REFERENCE`, `UNRESOLVED`, y
además `MISSING_DOCUMENT`, `NO_PRIMARY`, `ORPHAN`, `DUPLICATE`, `RAW_ONLY`, `MIXED_CONTAMINATION`.

---

## 1. CONFLICT — La evidencia de host no describe el host (crítico)

`STALE` + `CONFLICT`. Detalle comparativo en `DOCUMENTATION-CENSUS.md` §5 y
`PATCH-SOURCES.md` §3.

| Contexto | SO | Kernel | Mesa | RX550 | Fuente |
|---|---|---|---|---|---|
| Disco viejo (1444 docs) | Nobara 44 | `7.2.4` / `7.2.6` | 26.2.2 / 26.2.3 | `card1` | Gate P0, `knowledge.md`, `C1-PREFLIGHT-*` |
| Captura 2026-09-25T13:58Z | Nobara 43 | `6.18.2-…fc43` | 25.3.2 | `card2` | `FINAL-VALIDATION-*`, `README.md`, `PATCH-REGISTRY-FINAL.md`, `INSTALL.md` |
| **Host vivo 2026-09-25T22:22Z** | **Nobara 44** | **`7.1.3-…fc44`** | **26.2.3** | **`card1`** | lectura directa |

**Documentos afectados por la versión obsoleta** (los 16 `CURRENT` más los de la raíz):

| Documento | Qué queda obsoleto |
|---|---|
| `README.md:13-16` | SO, kernel, Mesa, LLVM, libdrm, firmware, `card2` |
| `INSTALL.md` §2 | paquetes y versiones |
| `PATCH-REGISTRY-FINAL.md:73` | versiones de todas las correcciones |
| `FINAL-VALIDATION-*.md` / `.json` | toda la captura |
| `ROLLBACK.md:43-44` | la advertencia menciona Nobara 43 como "producción" |
| `TESTING.md` | criterios derivados de la captura |

**Verificado además:**

1. El kernel vivo (`7.1.3`) es **más antiguo** que el del disco viejo (`7.2.4`/`7.2.6`).
2. `mesa-vulkan-drivers` **no está instalado** en el host vivo; sí lo estaba en ambas capturas.
3. `/opt/mesa-26.2.2-rx550-haswell` no existe en el host vivo.
4. La raíz del host vivo es `/dev/sdb3` **ext4**; el disco viejo tenía HDD `SAMSUNG HM500JI`
   con Btrfs según la documentación.
5. Ninguna prueba se ha re-ejecutado desde el cambio de host. Los resultados
   `64/64`, `110/110`, `54+1` corresponden al host de la captura.

**No resuelto por esta fase.** Requiere re-ejecutar `tools/validate_rx550_final.py` y las tres
suites, en fase separada.

---

## 2. CONFLICT — Hechos con fuentes incompatibles

Cinco contradicciones sustantivas. Detalle y fuentes en `DOCUMENTATION-RELATIONSHIPS.md` §8.

| # | Hecho | Valores en conflicto | Declarado en |
|---:|---|---|---|
| C1 | Tests de C1 | `24/24` vs `37/37` vs `44/44` vs `54+skip` | `DOCUMENTARY-RECONCILIATION-2026-09-25.md:187` `C1_TESTS=CONFLICT` |
| C2 | Versión de Mesa | 26.2.2 vs 26.2.3 vs **25.3.2** (raíz) vs **26.2.3 vivo** | `MESA_PROVENANCE=CONFLICT` |
| C3 | Versión de kernel | 7.2.6 vs 7.2.4 vs 6.18.2-fc43 vs **7.1.3 vivo** | `C1-TECHNICAL-RECORD.md:48` |
| C4 | `cardN` de la RX550 | `card2` vs `card1` | `PATCH-REGISTRY-FINAL.md` lo resuelve como regla, no como valor |
| C5 | Estado de H12-4 | implementado vs `DOC_NOT_EXECUTED` vs `NOT_REPRODUCED` | `H12-4_PROVENANCE=CONFLICT` |
| C6 | Btrfs | `CONFLICT` + host actual en ext4 | `AGENTS.md:136`, `DOCUMENTARY-RECONCILIATION-2026-09-25.md` |

**Ninguna resuelta.** Un router por intención debe poder devolver "hay conflicto, consulta A y B"
en lugar de elegir una.

---

## 3. MISSING_DOCUMENT — Temas del vocabulario sin ninguna fuente

| Tema | Menciones | Por qué no hay fuente | Respuesta correcta |
|---|---:|---|---|
| **BACO** | 8 | Solo aparece de paso en `PROBLEM-STATUS-FINAL.md`, `PATCH-REGISTRY-FINAL.md`, `RELEASE-CANDIDATE.md`, `FINAL-RELEASE-REPORT.md`. Ningún documento define qué se midió ni con qué resultado. | `NOT_AVAILABLE` |
| **FIREFOX** | 5 | Solo como cliente de GPU en el Gate P0 y en auditorías de background. | `NOT_AVAILABLE` |
| **GRUB** | 34 | Existe **solo como prohibición** en `README.md`, `AGENTS.md`, `ROLLBACK.md`, `INSTALL.md`. | `NOT_AVAILABLE` + prohibición |
| **UDEV** | 11 | Idem. Las reglas udev del backup están en `PATCH-REGISTRY-RECOVERED.md` `RX550-UD-01/02` pero **no aplicadas**. | `NOT_AVAILABLE` + prohibición |

**Otros temas sin fuente primaria pero con contexto parcial:**

- `FIREFOX` y `BACO` no aparecen en el vocabulario `TOPICS` de ningún documento de estado.
- `IOMMU` (4 menciones) solo se trata dentro de `VFIO-FEASIBILITY-AUDIT` y `ROLLBACK.md`.
- `PSI` (17) y `D_STATE` (16) solo existen dentro de Gate P0 y C1. No hay documento de
  almacenamiento dedicado.

---

## 4. MISSING_DOCUMENT — Requisitospedidos por el proyecto que no existen

| Documento esperado | Estado | Nota |
|---|---|---|
| Ejecución de `PROTOCOLO-AB-LIMPIEZA-BACKGROUND.md` | **No existe** | El protocolo A/B de `system-autopilot` y `kalm` nunca se ejecutó. El propio documento lo dice: "No se ha ejecutado ninguna desactivación". **Irrelevante para el host actual**: las unidades no existen. |
| `DOCUMENT-HASHES.txt` del paquete R5 | **No existe** | Citado por `DIAGRAMAS/00-MAESTRO-PROYECTO.md` y `12-MATRIZ-TRAZABILABILITY.md` como "presente pero histórico". No está en el árbol. |
| Sidecar C1 con `44/44` | **No localizado** | `DOCUMENTARY-RECONCILIATION` lo cita como `CURRENT_SIDECAR_RECORD` pero el fichero no está en el repo. |
| `RX550_BUILD_SPECIFICATION.txt` referenciado como `00-INDICE/…` | Ruta rota | Existe en `02-ARQUITECTURA/`, no en `00-INDICE/`. Ver §5 causa C. |
| Documento de release post-censo | Pendiente | No existe. Se creará cuando se diseñe el router. |
| Bitácora de la migración al disco nuevo | **Ausente** | No hay ningún documento que registre el cambio de host. `PATCH-SOURCES.md` §3 es lo más cercano. |

---

## 5. BROKEN_REFERENCE — 140 referencias rotas, por causa

| Causa | N | Reparable sin decisión editorial | Naturaleza |
|---|---:|---|---|
| A — citan ficheros del host viejo (`kalmd.py`, `kalm-lite.py`, `/usr/local/bin/system-autopilot.sh`) | ≈30 | No: el fichero no existe en ningún sitio | **No es error**; cita de provenance |
| B — artefactos de runtime no versionados (`state.json`, `stdout.txt`, `m1-schedule.json`) | ≈25 | No: se crean al ejecutar | **No es error**; cita de salida esperada |
| C — rutas previas a la reorganización del 2026-09-23 | ≈70 | Sí, mecánicamente | **Error real de ruta**; la reparación ya está documentada en `SET-I-REPAIR-RESULT.md` y `REGISTRO-DE-REPARACION-REFERENCIAS.md` pero **no se aplicó de nuevo** |
| D — código citado sin ruta | ≈15 | Parcialmente | **Ambigüedad** |

Detalle completo con cada referencia y cada documento que la cita en
`DOCUMENTATION-RELATIONSHIPS.md` §5.

**Referencia faltante noteworthy:** `PATCH-REGISTRY-FINAL.md` **no menciona**
`01-AUDITORIA/PATCH-RECOVERY/`, aunque este último se declare complementario. Se escribieron en
la misma sesión, el segundo después. Un lector que solo lea la raíz no sabrá que existe el
registro de recuperación.

---

## 6. DUPLICATE — Solapamientos reales (no resolubles por decisión trivial)

| # | Solapamiento | Docs | ¿Duplicado o complementario? |
|---:|---|---|---|
| 1 | Estado del proyecto | `MASTER-RESEARCH-STATUS.md` (63 KB) vs `PROBLEM-STATUS-FINAL.md` (8 KB) vs `FINAL-RESEARCH-STATUS.md` (4.6 KB) vs `README.md` (3.9 KB) | **Solapamiento real.** El maestro delega en los otros dos vía overlay; `FINAL-RESEARCH-STATUS` es snapshot declarado. |
| 2 | Mapa documental | `R2-GLOBAL-DOCUMENTATION-MAP.md` vs `PROJECT-DOCUMENTATION-STATUS.md` vs `DIAGRAMAS/README.md` vs `R1-5-DOCUMENTATION-STATUS.md` | **Solapamiento real**, y 3 de 4 se declaran no vivos. |
| 3 | Registro de parches | `PATCH-REGISTRY-FINAL.md` vs `PATCH-REGISTRY-RECOVERED.md` | **Complementario**, no duplicado. Declarado en ambos. |
| 4 | Correcciones de kernel (7.2.6 vs 7.2.4) | `C1-TECHNICAL-RECORD.md` vs `P0-…GATE` vs `knowledge.md` | **Contradicción, no duplicado.** |
| 5 | Fases de `rx550-torneo` | `README-FASE1.md`, `README-FASE2.md`, `README-FASE3.md`, `README-M1.md` | **Secuencial, no duplicado**, pero sin índice que las encadene. |
| 6 | Auditorías de background | `AUDITORIA-CANDIDATOS-BACKGROUND-v2.md`, `AUDITORIA-CONSUMO-SEGUNDO-PLANO.md`, `AUDITORIA-ACTUALIZACIONES-AUTOMATICAS.md`, `PROTOCOLO-AB-LIMPIEZA-BACKGROUND.md` | **Solapamiento parcial**: las 4 miden el host viejo desde ángulos distintos; ninguno se declaracanónico. |
| 7 | Preflight C1 (3 snapshots del mismo minuto) | `C1-PREFLIGHT-…055714Z.md`, `…060029Z.md`, `…060029Z-SUPPLEMENT.md` | **Secuencial**, pero `055714Z` y `060029Z` tienen **tamaño y estructura casi idénticos** (2725 bytes ambos). Posible duplicado no resuelto. |
| 8 | Documentos PRE/POST de C1 | `C1-TTY3-*-PRE.md` ×2, `C1-RECOVERY-…-PRE.md`, `C1-TTY3-INTERACTIVE-…-PRE.md` | **Complementario**: el PRE solo tiene sentido con su POST. Ningún índice los empareja. |

Comprobación adicional: `C1-PREFLIGHT-20260925T055714Z.md` y `C1-PREFLIGHT-20260925T060029Z.md`
miden **2725 bytes cada uno**. No se comparó el contenido byte a byte; se marca como
`POSSIBLE_DUPLICATE` para revisión, no como duplicado confirmado.

---

## 7. STALE / SUPERSEDED — Documentos que no deben ser fuente de estado

| Documento | Motivo | Quién lo marca |
|---|---|---|
| `00-INDICE/FINAL-RESEARCH-STATUS.md` | snapshot; el propio `10-NAVEGACION-DOCUMENTAL.md` dice "No usar como estado vivo" | `DIAGRAMAS/10` §HISTORICAL |
| `01-AUDITORIA/AUDIT-001/AUDIT-001.md` | corregido por `ERRATA.md` (Kalm, `power1_input`) | `ERRATA.md` §ERRATUM-001/002 |
| `01-AUDITORIA/POST-REPARACION-DOCUMENTAL-AUDIT.md` | auditoría histórica | `DIAGRAMAS/10` §HISTORICAL |
| `01-AUDITORIA/REPARATION-PLAN.md` | plan/checkpoint histórico | `DIAGRAMAS/10` §HISTORICAL |
| `00-INDICE/POST-REORGANIZATION-*.md` (5 docs) | snapshots de reorganización | su propio encabezado `HISTORICAL` |
| `00-INDICE/REGISTRO-DE-*.md` (2 docs) | trazabilidad, no estado | — |
| `03-EXPERIMENTOS/rx550-power-sweep-*/ESTADO-HISTORICO-NO-UTILIZABLE.md` (2) | los datos **no son utilizables** | el propio nombre |
| `03-EXPERIMENTOS/…/ab-e5*.sh`, `env-check.sh`, `driver.sh` | `HISTÓRICO / NO VERIFICABLE` en su cabecera | el propio comentario |
| 16 de 17 `00-INDICE/DIAGRAMAS/*.md` | `DRAFT/CONFLICT` | su propio `STATUS:` |
| `00-INDICE/R2-GLOBAL-DOCUMENTATION-MAP.md` | `DRAFT/CONFLICT`, "no es una vista `LIVE`" | su propio `STATUS:` |
| `00-INDICE/HYPOTHESIS-REGISTER.md` | "registro textual provisional; no es un veredicto" | `DIAGRAMAS/10` §DRAFT |
| `00-INDICE/ESTADOS-ES-EN.md` | taxonomía ampliada "provisional" | `DIAGRAMAS/10` §CONFLICT |
| `01-AUDITORIA/FINAL-VALIDATION-*` (2) | `CURRENT_NEW_DISK_STALE_HOST` | §1 de este documento |
| `02-ARQUITECTURA/knowledge.md` | kernel 7.2.4 obsoleto | este censo |
| `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/C1-RECOVERY-RUNTIME-TEST-…-POST.md` | registra cambio de kernel pre/post reboot **sin corregir** | `:31` |

---

## 8. NO_PRIMARY — Temas con demasiadas fuentes y ninguna jerarquía

| Tema | N docs | Problema |
|---|---:|---|
| `MESA` | 149 | 3 versiones en conflicto, 4 documentos con affirmedworkaround status distinto, 1 commit externo. Ningún doc dice "esta es la versión vigente". |
| `POWER_CAP` | 80 | 3 experimentos (M1, Fase B, EP-06) + 2 power-sweep marcados no utilizables + `PATCH-REGISTRY-FINAL` que dice `NOT_REPRODUCED`. El lector no sabe si M1 o Fase B es el canónico. |
| `KERNEL` | 137 | 4 valores de kernel distintos. |
| `SYSTEMD` | 112 | 4 documentos de background, ninguno canónico, y todos sobre unidades que ya no existen. |
| `C1` | 68 | 4 flavour de recuento de tests, 3 de kernel, 2 de restore. |
| `COUNTERS` | 97 | 6 documentos con concluded status distinto (Resultado B, Etapa 2, Etapa 3, R0-1, R1-1, addendum). |
| `FRAME` | 104 | R-4C, R-4B, workload sintético, y las 69 `*.md` de `04-IMPLEMENTACION/projects/` mezclan feasibilidad con resultados. |
| `EXPERIMENTS` | 169 | `MASTER-RESEARCH-STATUS` y `RESEARCH.md` son ambos índices y se solapan. |
| `REPRODUCIBILITY` | 99 | No hay documento que defina el protocolo de reproducibilidad. `TESTING.md` cubre pruebas estáticas, no experiments. |

---

## 9. RAW_ONLY — Información que solo existe en evidencia cruda

| Información | Solo en | ¿Documentado en algún sitio? |
|---|---|---|
| Los 13 localizadores `/tmp` canónicos perdidos de R-4B | `EXP-F4-A-RESULTADOS-v2.3.md` | Sí, pero como lista, no como rutas de datos |
| 10 corridas de M1 con `gpu_reset_check` | `M1-cap-35-30/runs/20260919-235939/*/audit.json` | `RESULTADOS-M1.md` §0 lo resume |
| 8/8 celdas PASS de R-4C (NIVEL A/B) | `FASE-R4C-*/results/metrics/*.json` y `gt/*_gt.json` | `EXP-F1-A-RESULTADOS.md` lo resume |
| Matriz `metrics.json` de R-4B (37 KB ×2) | `FASE-R4B-GOVERNOR/results/{session1-v22,v23}/session1/fase2/` | `EXP-F4-A-RESULTADOS-v2.3.md` |
| Registros de las 47+47 `state_initial/state_final` | `FASE-R4B-GOVERNOR/results/**/fixed{1,2,3}/` | **No** |
| `resultados_etapa2.json` de FASE D | `FASE-D-COUNTERS-AUDIT/runs/etapa2/` | **No**, y el JSON está **malformado** (excluido del índice Git) |
| Hashes de artefactos críticos de R-4B | `AUDITORIA-PRE-RUN-v2.3.md` §1 | Sí, pero como pre-run (obsoleto tras la ejecución) |
| Salida de los runners EP05/EP06/fase-B | `*/runs/*/stdout.txt` | `RESULTADOS-*.md` los resume |
| Contenido de los ficheros `.run` de benchmarks | `RX550_Benchmarks/` | `RELEASE-EXCLUSIONS.md` los declara excluidos |

**Consecuencia para el router:** 51 % de las filas del inventario son artefactos whose
interpretation lives **solo** en un `.md` de experimento. Si ese `.md` se pierde o queda
inaccesible, el dato es irrecuperable sin leer 1321 ficheros.

---

## 10. MIXED_CONTAMINATION — Documentos que mezclan disco viejo y disco nuevo

110 documentos tienen `SOURCE_STATUS=MIXED`. Los más Hazardous son los que contienen **valores de
host concretos** y se leen como estado actual:

| Documento | Qué mezcla |
|---|---|
| `00-INDICE/MASTER-RESEARCH-STATUS.md` | Overlay de disco nuevo + historial R-4B de disco viejo + addenda de ambos. Las secciones de snapshot contradicen las vigentes. |
| `02-ARQUITECTURA/knowledge.md` | Arquitectura estable + `Kernel 7.2.4` + `DRM 3.64` + resultado del Gate P0 (disco viejo). |
| `04-IMPLEMENTACION/C1-ISOLATION-AUTOMATOR.md` | Diseño de disco viejo + expectativa de kernel 7.2.6 + correcciones de selector del disco nuevo. |
| `01-AUDITORIA/DECISIONES-D1-D10.md` | Decisiones de disco viejo + reconciliación del disco nuevo en §0. |
| `PATCH-REGISTRY-FINAL.md` | Correcciones del disco nuevo con columnas "Estado anterior" (disco viejo) y "Estado posterior" (disco nuevo). **Es el documento mejor construido para este problema.** |
| `01-AUDITORIA/DOCUMENTARY-RECONCILIATION-2026-09-25.md` | Marca precisamente los conflictos de provenance. |

---

## 11. UNRESOLVED — Problemas abiertos que el censo no puede cerrar

| # | Problema | Por qué el censo no lo cierra |
|---:|---|---|
| 1 | Identidad del host actual | Requiere re-ejecutar el validador (fuera de fase) |
| 2 | Estado de los tests en el host actual | Requiere re-ejecutar las 3 suites |
| 3 | Las 5 contradicciones C1–C6 | Requieren decisión editorial, no análisis |
| 4 | Las 140 referencias rotas | Reparar exige autorización de escritura |
| 5 | Los 59 documentos huérfanos | Enlazarlos exige decisión editorial |
| 6 | Los 4 solapamientos de estado | Fusionar requiere decisión editorial |
| 7 | `SECURITY_REVIEW=NOT_READY` (66 ficheros con rutas personales) | Fuera del alcance del censo |
| 8 | Historia pública del repositorio | Decisión de política |
| 9 | Los 3 payloads de Kalm ausentes | `NOT_AVAILABLE` sin fuente |
| 10 | Los 3 slots de sistema sin fuente (kernel/amdgpu/GRUB) | `NOT_AVAILABLE` |
| 11 | `system-autopilot` sin contenido recuperable | `NOT_AVAILABLE`; solo 12 hex de hash |
| 12 | 2 documentos `.md` posibles duplicados (`C1-PREFLIGHT-055714Z` vs `060029Z`) | Requiere comparación byte a byte |

---

## 12. Observación sobre `.md` de contenido no-docUMENTAL

`00-INDICE/README.md:25` ofrece `02-ARQUITECTURA/RX550_BUILD_SPECIFICATION.txt` como
"especificación técnica de construcción de `rx550-torneo` (45 secciones)".

**Es un `.txt`, no un `.md`, y por tanto no entró en el inventario documental** de esta fase
(siguiendo la regla de no listar automáticamente todo lo no-Markdown). Sin embargo tiene función
documental inequívoca. Consta aquí para que la fase siguiente lo considere.

Otros ficheros con función partially documental fuera del inventario:
`00-INDICE/experiments_proposed.md` (sí está), y los `.json` de auditoría (sí están, como
`RAW_EVIDENCE` con `PRIORITY=RAW_EVIDENCE`).

---

## 13. Verificación de integridad de este censo

| Comprobación | Resultado |
|---|---|
| Rutas del TSV que existen en disco | **1576 / 1576** |
| Rutas inventadas | **0** |
| `.md` en el TSV ausentes del disco | **0** |
| `.md` del disco ausentes del TSV | **0** (256/256) |
| TSV parseable | Sí — 1576 filas, 20 campos, 0 líneas malformadas |
| Relaciones `REFERENCES` verificadas contra el árbol | 613 |
| Temas con fuente real | 53 de 57; 4 sin primaria (§3) |
| Archivos modificados fuera de `01-AUDITORIA/DOCUMENTATION-CENSUS/` | **0** |
| Commit / tag / push / remote | **0** |
| Cambio de sistema | **0** |

### SHA-256 de los informes de esta fase

```
3f1bf9ec92c5ca41164c65b7b74a7b6b08a2145be2f45de92e7bce26deefa9d0  DOCUMENTATION-CENSUS.md
a4ccacbca3d8f50d89d0b086e72e76915a4a3ec5f2d18b2811292cc9936e8553  DOCUMENTATION-INVENTORY.tsv
bb2cb3f8c96d569424af7d9975ef84f9935b08da8ce4d7c253ecba4074996810  DOCUMENTATION-TOPICS.md
8ff51b2dc6766294800a12c593f63a5d16cbf2046f98175ee8eff94f357c5e01  DOCUMENTATION-RELATIONSHIPS.md
d51ed22f05c691e8a236876c857b876c9bba6bbd8309d546e77c388d7016811b  DOCUMENTATION-GAPS.md
```

**Nota sobre el hash de `DOCUMENTATION-GAPS.md`:** el valor de arriba es el del fichero con esta
sección ya insertada, es decir **cambió** al escribir estas líneas. Verificación reproducible:

```bash
sha256sum 01-AUDITORIA/DOCUMENTATION-CENSUS/*
```

El hash de los otros cuatro ficheros sí es estable respecto al contenido final.

### Verificación de no-efecto sobre el repositorio

| Comprobación | Resultado |
|---|---|
| Ficheros modificados en el working tree | **0** (`git diff --name-only` → 0) |
| Rutas preparadas en el índice | **360**, las mismas de antes de esta fase |
| Rutas preparadas bajo `DOCUMENTATION-CENSUS/` | **0** |
| Ficheros nuevos (`??`) | 5 del censo + 3 de `PATCH-RECOVERY/` (fase anterior) |
| `HEAD` | `c6146788e0d4fb12d9b0ec1209fa2840692de0c5` (sin cambios) |
| Remotes / tags | 0 / 0 |
| `.md` en disco no inventariados | 4, y son los `.md` de este mismo censo |
