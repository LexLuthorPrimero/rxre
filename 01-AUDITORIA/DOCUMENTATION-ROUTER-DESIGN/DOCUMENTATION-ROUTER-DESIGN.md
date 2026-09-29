# DOCUMENTATION-ROUTER-DESIGN — Diseño del sistema de navegación documental

**Fecha:** 2026-09-25T23:10Z
**Fase:** diseño del router,basado exclusivamente en `01-AUDITORIA/DOCUMENTATION-CENSUS/`.
**Estado:** DISEÑO. Nada implementado. `AGENTS.md` no modificado. Ningún archivo histórico tocado.

## Documentos de esta fase

| Fichero | Función |
|---|---|
| `DOCUMENTATION-ROUTER-DESIGN.md` | Este documento: arquitectura, decisión de nº de ficheros, AGMENTS integration |
| `ROUTING-SCHEMA.md` | vocabulario reutilizado de R2 + extensiones mínimas + esquema de campos |
| `ROUTING-SIMULATION.md` | 18 consultas reales resueltas con el router propuesto |
| `ROUTING-GAPS.md` | huecos del diseño, riesgos y lo que no se puede resolver aquí |

---

## 1. El problema que resuelve el router

El censo estableció tres hechos que determinan el diseño:

1. **1444 de 1576 filas son `HISTORICAL_OLD_DISK`.** Solo 16 son `CURRENT`. El fallo por
   defecto de cualquier buscador es servir el disco viejo como estado actual.
2. **El documento con más referencias entrantes (30) no contiene el estado vigente.**
   `MASTER-RESEARCH-STATUS.md` delega en 4 documentos de la raíz que suman 51 entrantes. La
   jerarquía de referencias está invertida respecto a la jerarquía de autoridad.
3. **1321 artefactos (84 %) dependen de un `.md` de experimento para ser interpretados.** Un
   artefacto suelto no significa nada.

Y un cuarto hecho discovered durante el diseño de este router:

4. **229 de 256 documentos `.md` no contienen ningún marcador de host en su contenido.** Solo 27
   citan `fc44`/`7.2.x` (HOST-A) o `fc43`/`6.18.2` (HOST-B). El 89 % del repositorio **no es
   auto-identificable** respecto al host. `HOST_SCOPE` no puede deducirse del documento: tiene que
   venir del censo, y cuando el censo no lo pudo determinar, `HOST_SCOPE=UNKNOWN`.

**Consecuencia de diseño:** el router no puede ser un índice de ficheros. Tiene que ser un
**procedimiento de decisión** que,~ dado un `DOMAIN` y un `TOPIC`, elija un `PRIMARY` y declare
`TEMPORALITY` + `HOST_SCOPE` antes de devolver nada.

---

## 2. Arquitectura

La arquitectura propuesta en el encargo era:

```
AGENTS.md → ROUTER → DOMAIN INDEX → PRIMARY → RAW → SECONDARY → WEB
```

**Adaptación al censo real.** El censo muestra que un "DOMAIN INDEX" intermedio no aporta: los
dominios son 12 y cada uno tiene entre 1 y 15 topics, y el `PRIMARY` de cada topic ya está
determinado y verificado en `DOCUMENTATION-TOPICS.md`. Un índice de dominios sería una capa de
 indirección más que mantener.

**Arquitectura adoptada (5 saltos, un nivel menos):**

```
                    ┌──────────────────────────────────────────┐
   pregunta ──────► │  AGENTS.md  §PROPOSED_AGENTS_ROUTING_   │  1. punto de entrada
                    │  RULES  (≈25 líneas, carga permanente)  │
                    └───────────────────┬──────────────────────┘
                                        │ "consulta el router primero"
                    ┌───────────────────▼──────────────────────┐
                    │  DOCUMENTATION-ROUTER.md                 │  2. tabla de decisión
                    │  (≈120 líneas: DOMAIN → TOPIC →         │     única, cabe en un
                    │   PRIMARY + TEMPORALITY + HOST + ESC)   │     contexto
                    └───────────────────┬──────────────────────┘
                                        │
        ┌───────────────────────────────┼───────────────────────────────┐
        ▼                               ▼                               ▼
┌───────────────┐          ┌────────────────────────┐        ┌────────────────────┐
│PRIMARY        │          │ESCALATION si PRIMARY   │        │TERMINALES         │
│(1 fichero)    │          │no alcanza              │        │UNKNOWN /          │
│CURRENT o      │          │  ├→ SECONDARY (censo)  │        │NOT_AVAILABLE /    │
│HISTORICAL     │          │  ├→ RAW (via EXPERIMENT│        │CONFLICT /         │
│declarado     │          │  │   DIR)                │        │WEB                │
└───────┬───────┘          │  └→ WEB                │        └────────────────────┘
        │                  └────────────────────────┘
        ▼
┌───────────────────────────────────────────────────────────────┐
│  RAW_EVIDENCE  (nunca se lee en el primer salto)              │
│  ruta: TOPIC → EXPERIMENT_DIR → EXPERIMENT_MD → artefacto    │
│  fuente del mapa: DOCUMENTATION-INVENTORY.tsv + census §8     │
└───────────────────────────────────────────────────────────────┘
```

**Cambio de fondo respecto al encargo:** la flecha `PRIMARY → RAW` **no es automática**. El
censo establece que 84 % de las filas son artefactos cuya interpretación depende de un `.md`. Por
tanto la ruta real es siempre `TOPIC → EXPERIMENT_DIR → EXPERIMENT_MD → RAW_ARTIFACT`, y
`EXPERIMENT_MD` es un documento redactado, no un artefacto. El router necesita un campo
`EXPERIMENT_DIR` que el TSV actual no tiene explícito (ver §5).

---

## 3. Decisión de diseño: cuántos ficheros

**Decisión: 3 ficheros nuevos, todos en `01-AUDITORIA/DOCUMENTATION-ROUTER-DESIGN/`, más 1
modificación de inventario opcional.**

| Fichero | Tamaño objetivo | Cuándo se carga |
|---|---:|---|
| `DOCUMENTATION-ROUTER.md` (a crear en fase de implementación) | ≤130 líneas | **Siempre**, al recibir una pregunta |
| `ROUTING-SCHEMA.md` (este diseño) | ~300 líneas | Al needing definir o verificar el vocabulario |
| `ROUTING-SIMULATION.md` | ~250 líneas | Al validar el router o al depurar una ruta |
| `ROUTING-GAPS.md` | ~120 líneas | Al buscar un hueco conocido |

**Por qué NO se crea un `DOMAIN-INDEX.md`:** los 12 dominios × 68 topics ya están tabulados y
verificados en `01-AUDITORIA/DOCUMENTATION-CENSUS/DOCUMENTATION-TOPICS.md` §15. Un índice de
dominios sería duplicarlo.

**Por qué NO se crea un `PRIMARY-SOURCES.md`:** lo mismo. `DOCUMENTATION-TOPICS.md` §15 ya tiene
la tabla `TOPIC | FIRST_DOCUMENT | SECOND_DOCUMENT | RAW_EVIDENCE | ESCALATION_CONDITION`. El
router solo necesita **copiar esa tabla al formato de decisión** y añadirle `TEMPORALITY` y
`HOST_SCOPE`, que el censo no tenía por topic.

**Por qué NO se tocan los 5 mecanismos de navegación existentes:** están en `DRAFT/CONFLICT` o son
históricos. Reemplazarlos requiere una decisión editorial que no está autorizada. El router se
posiciona **por encima** de ellos y declara explícitamente que no los sustituye.

**Por qué NO se reparan las 140 referencias rotas en esta fase:** prohibido por el encargo. El
router expone `REFERENCE_STATUS=BROKEN` con su razón.

---

## 4. Dimensiones de routing

Ocho dimensiones, con vocabulario cerrado. Detalle en `ROUTING-SCHEMA.md`.

| Dimensión | Valores | Origen |
|---|---|---|
| `DOMAIN` | 12 dominios | **Nuevo**, derivado de la agrupación de topics del censo |
| `TOPIC` | 68 | **Censo** (`DOCUMENTATION-TOPICS.md` §0) |
| `QUESTION_TYPE` | 21 | **Nuevo**, los 18 del encargo + 3 del censo |
| `TEMPORALITY` | 7 | **Nuevo** (amplía los 4 del censo con `HOST_SCOPE`) |
| `HOST_SCOPE` | 5 | **Nuevo** (HOST-A / HOST-B / HOST-C / UNKNOWN / N-A) |
| `EVIDENCE_TYPE` | 16 | **R2 reutilizado** + 5 extensiones mínimas |
| `SOURCE_PRIORITY` | 4 | **Censo** (`PRIMARY`/`SECONDARY`/`TERTIARY`/`RAW_EVIDENCE`) |
| `CONFIDENCE` | 2 | **Censo** (`HIGH` 253/256, `MEDIUM` 3/256) |

### 4.1 `TEMPORALITY` — 7 valores

El encargo exige distinguir explícitamente `CURRENT`, `HISTORICAL_OLD_DISK`,
`HISTORICAL_OTHER_HOST`, `NEW_DISK`, `EXTERNAL`, `MIXED`, `UNKNOWN`. Mapeo desde el censo:

| Valor del router | Origen en el censo | Filas |
|---|---|---:|
| `CURRENT_NEW_DISK` | `SOURCE_STATUS=CURRENT_NEW_DISK` | 15 |
| `CURRENT_NEW_DISK_STALE_HOST` | `SOURCE_STATUS=CURRENT_NEW_DISK_STALE_HOST` | 1 (+1 RAW) |
| `HISTORICAL_OLD_DISK` | `SOURCE_STATUS=HISTORICAL_OLD_DISK` | 1444 |
| `HISTORICAL_OTHER_HOST` | No existe en el censo como valor propio | 0 (nuevo, vacío) |
| `MIXED` | `SOURCE_STATUS=MIXED` | 110 |
| `EXTERNAL` | `CATEGORY=EXTERNAL_SOURCE` (10 docs) | 10 |
| `UNKNOWN` | `SOURCE_STATUS=UNKNOWN` | 4 |

`HISTORICAL_OTHER_HOST` se crea **vacío** porque el backup `~/Escritorio/RX550_Modo_Torneo_Backup_2026-09-19_0836/`
está **fuera del repositorio** y por tanto no figura en el TSV. El router lo necesita para las
referencias que apuntan ahí (`code/rx550-power-sweep.sh`, `system/kalm-gpu`, `audit-history/shell-history-rx550-kalm.txt`).

### 4.2 `HOST_SCOPE` — 5 valores

| Valor | Definición | Cómo se asigna |
|---|---|---|
| `HOST-A` | Disco anterior. Nobara 44, kernel `7.2.4`/`7.2.6`, Mesa 26.2.2/26.2.3 | Solo 18 docs citan `fc44`/`7.2.x` en su texto. El resto se atribuye por `SOURCE_STATUS=HISTORICAL_OLD_DISK` |
| `HOST-B` | Captura del 2026-09-25T13:58Z. Nobara 43, kernel `6.18.2-…fc43`, Mesa 25.3.2, RX550=`card2` | 8 docs citan `fc43`/`6.18.2`; más `FINAL-VALIDATION-*` |
| `HOST-C` | Host vivo medido el 2026-09-25T22:22Z. Nobara 44, kernel `7.1.3-…fc44`, Mesa 26.2.3, RX550=`card1` | Solo `PATCH-SOURCES.md` §3 y lo que se mida en el futuro |
| `UNKNOWN` | El documento no declara host y el censo no pudo atribuirlo | **229 de 256 docs** |
| `NOT-APPLICABLE` | Documento de diseño, taxonomía o índice que no afirma estado de hardware | `AGENTS.md`, `HYPOTHESIS-REGISTER.md`, `ESTADOS-ES-EN.md` |

**Este es el dato más incómodo del censo y el router debe exponerlo, no esconderlo:** el 89 % de
los documentos no es auto-identificable respecto al host. Un lector que abra
`TEST-TERMICO-READONLY.md` no tiene forma de saber si describe el disco viejo o el actual salvo
que cruce la fecha con el mapa de hosts.

### 4.3 `EVIDENCE_TYPE` — taxonomía R2 reutilizada + 5 extensiones

R2 (`00-INDICE/R2-GLOBAL-DOCUMENTATION-MAP.md` §0) ya define 7 abreviaturas: **REP**, **DISEÑO**,
**PLAN**, **ESTADO**, **REF**, **AUDIT**, **CIERRE**, más **MAPA**, **ÍNDICE**, **ADDENDA**,
**CÓDIGO**, **SPEC**, **DIAGRAMA**, **REGISTRO**. **Se reutilizan tal cual.** El router añade
solo 5, cada unafills un hueco que R2 no cubre y que el censo demuestra necesario:

| Extensión | Por qué hace falta | Nº de filas |
|---|---|---:|
| `RAW` | Artefacto de medición. R2 lo llama `REF` pero no distingue un `.md` de un `stdout.txt`. Sin esta distinción el router no puede cumplir "no leer 1320 artefactos" | 1321 |
| `PATCH` | R2 no tiene tipo para registros de corrección. El censo tiene `CATEGORY=PATCH` | 1 doc + 3 de `PATCH-RECOVERY/` |
| `TEST` | R2 no distingue un documento de pruebas de un de resultados | 2 |
| `RECOVERY` | R2 no tiene tipo para preflight/recovery, que en este proyecto es un eje de gates completo | 12 |
| `CONFLICT` | Documento cuyo propósito es registrar discrepancias. Sin él, un `AUDIT` con conflicto se lee como `AUDIT` fiable | ~6 |

**No se crea una segunda taxonomía.** El router usa los 13 tokens de R2 más estos 5. El campo
`EVIDENCE_TYPE` del router **no** duplica el `CATEGORY` del censo: se mapea en
`ROUTING-SCHEMA.md` §3 y la razón del mapeo está escrita.

---

## 5. `EXPERIMENT_DIR` — campo que falta

El encargo pide añadir `EXPERIMENT_DIR` al inventario. **Verificado: es necesario y es derivable.**

```
Filas RAW_EVIDENCE:                          1321
  con EXPERIMENT_DIR derivable de PATH:       1297  (bajo 03-EXPERIMENTOS/)
  sin EXPERIMENT_DIR:                           24  (JSON de auditoría en 01-AUDITORIA)
  buckets más grandes:
     302  03-EXPERIMENTOS/FASE-R4B-GOVERNOR
     194  03-EXPERIMENTOS/rx550-power-sweep-20260918-132309
     194  03-EXPERIMENTOS/rx550-power-sweep-20260918-140527
     143  03-EXPERIMENTOS/fase-b-cap-probe-20260919-122038
     102  03-EXPERIMENTOS/WORKLOAD-SINTETICO
      76  03-EXPERIMENTOS/fase-a-discriminacion-20260919-114241
      58  03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT
      51  03-EXPERIMENTOS/ep05-mesa-custom-20260919-212249
      47  03-EXPERIMENTOS/M1-cap-35-30
      46  03-EXPERIMENTOS/FASE-R4B-THERMAL-TEST
      43  03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY
      24  03-EXPERIMENTOS/ep06-soak-cap-20260919-205645
      14  03-EXPERIMENTOS/EXPLORATORIO-GravityMark
       2  03-EXPERIMENTOS/R-14-SUPERPOSITION-DISSECTION
       1  03-EXPERIMENTOS/results
```

**Los 15 buckets son exactamente los 15 directorios de `03-EXPERIMENTOS/` que contienen `.md`.**
Es una correspondencia 1:1 limpia: cada directorio de experimento tiene su documento de entrada en
la raíz del directorio. Esto hace que `EXPERIMENT_DIR` sea un campo de **routing**, no de
clasificación: es la clave que permite saltar de un topic a su evidencia sin buscarla.

**Modificación propuesta al inventario (fase de implementación, no en esta fase):**

```
Añadir 3 columnas a DOCUMENTATION-INVENTORY.tsv:
  EXPERIMENT_DIR    directorio de experimento o "" si no aplica
  EXPERIMENT_MD     .md de entrada de ese experimento o "" si no aplica
  HOST_SCOPE        HOST-A | HOST-B | HOST-C | UNKNOWN | NOT-APPLICABLE
```

Justificación de `EXPERIMENT_MD` además de `EXPERIMENT_DIR`: sin el `.md` asociado, el router
sabría dónde está el artefacto pero no quién lo interpreta. Con ambos, la cadena
`TOPIC → EXPERIMENT_DIR → EXPERIMENT_MD → artefacto` queda cerrada y verificable.

**Nota sobre `HOST_SCOPE`:** se propone como columna nueva en vez de derivarse de
`SOURCE_STATUS`, porque `SOURCE_STATUS` mezcla temporalidad (`HISTORICAL_OLD_DISK`) con
procedencia (`CURRENT_NEW_DISK`) y no puede expresar «documento actual que describe un host que ya
cambió» — que es exactamente el caso de `FINAL-VALIDATION-*`
(`CURRENT_NEW_DISK_STALE_HOST`).

---

## 6. Regla de temporalidad en la resolución

El encargo es explícito: si se pide estado actual y solo hay histórico,
`CURRENT_EVIDENCE=NOT_AVAILABLE`. El router lo implementa como **precondición**, no como nota al
pie.

```
Petición de estado actual (QUESTION_TYPE ∈ {STATUS, CONFIGURATION, HARDWARE, REPRODUCIBILITY})
        │
        ├─ ¿El PRIMARY tiene TEMPORALITY ∈ {CURRENT_NEW_DISK} y HOST_SCOPE ≠ UNKNOWN?
        │     └─ SÍ  → responder, declarando TEMPORALITY y HOST_SCOPE
        │     └─ NO  → ↓
        │
        ├─ ¿Existe un CURRENT con HOST_SCOPE=HOST-C?
        │     └─ NO  → CURRENT_EVIDENCE=NOT_AVAILABLE
        │             + listar qué evidencia HISTÓRICA existe, marcada como tal
        │             + NO presentar el histórico como actual
        │     └─ SÍ  → ↓
        │
        └─ ¿El CURRENT tiene HOST_SCOPE=HOST-B y el host vivo es HOST-C?
              └─ SÍ  → STATUS=STALE
                       + citar el valor histórico
                       + indicar que requiere re-verificación en HOST-C
```

**Los 16 documentos CURRENT y su `HOST_SCOPE` implícito:**

| Documento | `HOST_SCOPE` | Nota |
|---|---|---|
| `README.md` | `HOST-B` | Declara Nobara 43 / 6.18.2 / Mesa 25.3.2. Host vivo es HOST-C |
| `PROBLEM-STATUS-FINAL.md` | `HOST-B` | Ídem |
| `PATCH-REGISTRY-FINAL.md` | `HOST-B` | Columnas «Estado anterior» (HOST-A) y «Estado posterior» (HOST-B) |
| `INSTALL.md` | `HOST-B` | Ídem |
| `TESTING.md` | `HOST-B` | Ídem |
| `ROLLBACK.md` | `HOST-B` + `HOST-A` | Menciona el backup (HOST-A) frente a Nobara 43 (HOST-B) |
| `RELEASE-CANDIDATE.md` | `NOT-APPLICABLE` | Gates de publicación, sin afirmación de host |
| `FINAL-RELEASE-REPORT.md` | `HOST-B` | Preguntas sobre el host instalado |
| `RELEASE-EXCLUSIONS.md` | `NOT-APPLICABLE` | Política de publicación |
| `CHANGELOG.md` | `NOT-APPLICABLE` | Cambios documentales |
| `AGENTS.md` | `NOT-APPLICABLE` | Reglas de agente |
| `PATCH-RECOVERY/PATCH-RECOVERY-REPORT.md` | `HOST-C` | Documenta la discrepancia de host |
| `PATCH-RECOVERY/PATCH-REGISTRY-RECOVERED.md` | `HOST-C` | Aplica al host vivo (verificado 0 unidades kalm) |
| `PATCH-RECOVERY/PATCH-SOURCES.md` | `HOST-C` | Única fuente de identidad HOST-C |
| `FINAL-VALIDATION-*.md` | `HOST-B` | `STALE`: describe HOST-B, el vivo es HOST-C |
| `VFIO-FEASIBILITY-AUDIT-*.md` | `HOST-B` o `UNKNOWN` |(require veryf) |

**Resultado: de los 16 CURRENT, solo 3 tienen `HOST_SCOPE=HOST-C`.** Siete son `HOST-B` y
requieren `STATUS=STALE`; cuatro son `NOT-APPLICABLE`; dos más requieren verificación. **El router
no puede afirmar el estado del host vivo con la documentación actual.** Esa es la conclusión
principal del diseño y hay que decirla con todas las letras.

---

## 7. Tratamiento de conflictos

Los 6 conflictos del censo se mantienen explícitos. El router **nunca** elige una fuente.

```
Consulta llega a un conflicto
        │
        ├─ STATUS=CONFLICT
        ├─ listar las fuentes enfrentadas con su TEMPORALITY y HOST_SCOPE
        ├─ indicar cuál prevalece SOLO si un documento lo declara
        │     (p. ej. DOCUMENTARY-RECONCILIATION declara MESA_CANONICAL vs MESA_EXTERNAL)
        ├─ si ninguna declara precedencia → NO_ELIJA: devolver ambas
        └─ si la pregunta pide un valor único → responder "hay conflicto", no un valor
```

| # | Conflicto | Precedencia declarada | Fuente que la declara |
|---:|---|---|---|
| C1 | Tests C1: 24/24 vs 37/37 vs 44/44 | Sí: `44/44=CURRENT_SIDECAR_RECORD` | `DOCUMENTARY-RECONCILIATION-2026-09-25.md:187-201` |
| C2 | Mesa: 26.2.2 vs 26.2.3 vs 25.3.2 | Parcial: `MESA_CANONICAL=26.2.2`, `MESA_EXTERNAL=26.2.3` | Ídem:225-227. **25.3.2 (raíz) no está en la declaración** |
| C3 | Kernel: 7.2.6 vs 7.2.4 vs 6.18.2 vs 7.1.3 | Parcial: «no se funden» | `C1-TECHNICAL-RECORD.md:48` |
| C4 | `cardN`: card1 vs card2 | Sí, como regla: «no son portables» | `PATCH-REGISTRY-FINAL.md`; `README.md:15-16` |
| C5 | H12-4: implementado vs no ejecutado | No | `DOCUMENTARY-RECONCILIATION-2026-09-25.md` |
| C6 | Btrfs: CONFLICT, y el host vivo es ext4 | No | `AGENTS.md:136-137` |

---

## 8. Referencias rotas

El router expone la rotura en lugar de esconderla. Las 140 se clasifican en 4 familias según
`DOCUMENTATION-RELATIONSHIPS.md` §5:

| `REASON` | N aprox. | Qué hace el router |
|---|---:|---|
| `REORG-2026-09-23` | ~70 | Reporta la ruta real. `SET-I-REPAIR-RESULT.md` y `REGISTRO-DE-REPARACION-REFERENCIAS.md` documentan la reparación, pero **no se aplicó de nuevo** |
| `OLD-DISK-FILE` | ~30 | Reporta que cita un fichero del HOST-A que no está en el repo. **No es un error** |
| `RUNTIME-UNVERSIONED` | ~25 | Reporta que el fichero lo crea el runner al ejecutarse. **No es un error** |
| `AMBIGUOUS-PATH` | ~15 | Reporta la ambigüedad; pide contexto |

Ninguna se repara en esta fase. El formato de salida es:

```
REFERENCE_STATUS=BROKEN
REASON=REORG-2026-09-23
CITED_AS=projects/CLOSED-LOOP-QUALITY-GOVERNOR/EXPERIMENT-DESIGN.md
RESOLVES_TO=04-IMPLEMENTACION/projects/CLOSED-LOOP-QUALITY-GOVERNOR/EXPERIMENT-DESIGN.md
DOCUMENTED_FIX=00-INDICE/POST-REORGANIZATION-SET-I-REPAIR-RESULT.md
```

---

## 9. Los 4 temas sin fuente primaria

`BACO`, `FIREFOX`, `GRUB`, `UDEV`. El router **no crea documentación artificial** para ellos.

| Topic | `PRIMARY_SOURCE` | Respuesta del router | Contexto permitido |
|---|---|---|---|
| `BACO` | `NOT_AVAILABLE` | «No hay fuente. 8 menciones de paso, ninguna define qué se midió.» | Listar los 8 documentos donde aparece, marcados como mención |
| `FIREFOX` | `NOT_AVAILABLE` | «No hay fuente. 5 menciones, siempre como cliente de GPU.» | Ídem |
| `GRUB` | `NOT_AVAILABLE` | «No hay fuente; además está prohibido modificarlo.» | Citar `README.md` §Reglas, `AGENTS.md`, `ROLLBACK.md` como **prohibición**, no como evidencia |
| `UDEV` | `NOT_AVAILABLE` | «No hay fuente; está prohibido. Las reglas udev del backup existen en `PATCH-REGISTRY-RECOVERED.md` `RX550-UD-01/02` pero **no están aplicadas**.» | Ídem |

En los 4 casos el router devuelve `TERMINAL=NOT_AVAILABLE` y **no escala**: no hay a dónde
escalar. Escalar a web es válido para `GRUB`/`UDEV` (documentación oficial) pero el router debe
decir que la respuesta sería *externa al proyecto* y no *estado de este sistema*.

---

## 10. Parches

El router integra `01-AUDITORIA/PATCH-RECOVERY/` sin aplicar nada. Distingue 4 clases:

| Clase | `PATCH_ID` | Dónde | `APPLIED_ON_HOST_C` |
|---|---|---|---|
| `STATIC_PROJECT_PATCH` | `RX550-PP-01..07`, `TP-01`, `C1-01/02` | `PATCH-REGISTRY-RECOVERED.md` §A | `PARTIAL` — en el árbol; `PP-05` y `PP-07` requieren rebuild |
| `SYSTEM_PATCH` | `RX550-SD-01..04`, `PM-01/02`, `UD-01/02`, `SCP-01/02/03` | `PATCH-REGISTRY-RECOVERED.md` §B | **`NO`** — verificado 2026-09-25T22:22Z: 0 unidades `kalm*`, 0 `system-autopilot*`, sin `/opt/kalm`, sin `/opt/mesa-26.2.2-rx550-haswell` |
| `EVIDENCE` | El propio registro + `PATCH-SOURCES.md` | `PATCH-RECOVERY/` | `N-A` |
| `HYPOTHESIS` | `RX550-UNK-01` (`system-autopilot`), `RX550-KP-01`/`AG-01`/`GR-01` | `PATCH-REGISTRY-RECOVERED.md` | `NOT_AVAILABLE` — sin fuente |

**Regla dura del router:** ningún `SYSTEM_PATCH` puede presentarse como aplicado al host vivo.
El único que se puede verificar es el negativo: `NEW_DISK_APPLIED=NO`, comprobado por lectura
del sistema. `RX550-MP-01` (Mesa) se marca `SYSTEM_CHANGE_REQUIRED=SI` y
`ORIGINAL_APPLIED=UNKNOWN`.

---

## 11. Lazy loading vía OpenCode

El encargo menciona que `AGENTS.md` es el mecanismo de instrucciones persistentes de OpenCode V2
y que los anidados se descubren al explorar. Diseño:

| Nivel | Fichero | Tamaño | Cuándo se carga |
|---|---|---:|---|
| 0 (permanente) | `AGENTS.md` §`PROPOSED_AGENTS_ROUTING_RULES` | ~25 líneas | Siempre, al abrir el proyecto |
| 1 (bajo demanda) | `DOCUMENTATION-ROUTER.md` | ≤130 líneas | Primera pregunta de cada sesión |
| 2 (bajo demanda) | `DOCUMENTATION-CENSUS/DOCUMENTATION-TOPICS.md` | 702 líneas | Cuando el topic no está en el router, o para auditar una ruta |
| 3 (bajo demanda) | `DOCUMENTATION-CENSUS/DOCUMENTATION-INVENTORY.tsv` |machine | Solo para localizar un artefacto RAW concreto |
| 4 (bajo demanda) | El documento `PRIMARY` | 1 fichero | Siempre que el router resuelva |
| 5 (escalar) | `SECONDARY` / `RAW` / web | 1+ ficheros | Solo si el primario no alcanza |

**No se carga la documentación como instrucciones globales.** Solo nivel 0 es instrucción; el
nivel 1 es el mecanismo de descubrimiento. Esto evita el modo de fallo que el censo detectó: 1444
documentos históricos cargados como contexto tienen más peso que los 16 actuales.

**Propuesta de `AGENTS.md` anidados** (a evaluar en implementación): un
`03-EXPERIMENTOS/AGENTS.md` de ~10 líneas que enlace a `DOCUMENTATION-TOPICS.md` §15, de modo que
al explorar un directorio de experimento el agente sepa qué `.md` es la entrada. El router puede
funcionar sin ellos; son una optimización.

---

## 12. `PROPOSED_AGENTS_ROUTING_RULES`

Sección a añadir **en fase de implementación**. No se ha modificado `AGENTS.md`.

```markdown
## PROPOSED_AGENTS_ROUTING_RULES

Antes de leer documentación de este proyecto:

1. Consulta `01-AUDITORIA/DOCUMENTATION-ROUTER-DESIGN/DOCUMENTATION-ROUTER.md`
   y clasifica la pregunta por DOMAIN, TOPIC y QUESTION_TYPE.
2. Lee SOLO el PRIMARY que indique. No leas el repositorio completo
   para responder una pregunta localizada.
3. Declara siempre TEMPORALITY y HOST_SCOPE junto a la respuesta.
4. No uses un documento HISTORICAL como estado actual. Si se pide estado
   actual y solo hay histórico: `CURRENT_EVIDENCE=NOT_AVAILABLE`, e
   indica qué evidencia histórica existe sin presentarla como actual.
5. Usa PRIMARY antes de SECONDARY; TERTIARY solo para contexto.
6. Sigue RAW_EVIDENCE solo cuando el PRIMARY no alcanza, y siempre vía
   EXPERIMENT_DIR -> EXPERIMENT_MD -> artefacto.
7. No conviertas UNKNOWN, NOT_AVAILABLE ni CONFLICT en PASS.
8. No conviertas HISTORICAL en CURRENT.
9. Cuando la documentación local sea insuficiente para un hecho de
   interfaz o upstream, consulta documentacion oficial y marcala
   EXTERNAL. No la presentes como evidencia de este host.
10. Si no existe fuente primaria, declara `PRIMARY_SOURCE=NOT_AVAILABLE`.
    No crees documentacion para rellenar el hueco.
11. Si hay fuentes incompatibles, conserva CONFLICT y devuelve ambas.
    No elijas una arbitrariamente.
12. Las referencias rotas se reportan con `REFERENCE_STATUS=BROKEN` y su
    `REASON`. No las repares sin autorizacion.
13. Ningun parche historico se aplica al host actual. Los SYSTEM_PATCH de
    `PATCH-RECOVERY/` tienen `NEW_DISK_APPLIED=NO` verificado.
14. Este proyecto tiene tres identidades de host (HOST-A/B/C) y estan
    abiertas. No asumas que una evidencia pertenece al host vivo.
```

14 reglas, ~25 líneas. Ninguna concede autorización de ejecución; todas son de navegación.

---

## 13. Métricas propuestas

**No se inventa rendimiento.** Solo se define cómo medirlo.

| Métrica | Definición | Fuente de medición | Línea base known? |
|---|---|---|---|
| `FILES_READ_PER_QUERY` | nº de ficheros abiertos para responder una consulta | Conteo de lecturas del agente | **No** |
| `NAV_DEPTH` | saltos desde la pregunta hasta el `PRIMARY` | Traza del router | **Sí, por diseño: 1** |
| `SOURCES_CONSULTED` | nº de documentos distintos | Traza | **No** |
| `PRIMARY_RESOLUTION_RATE` | % de consultas resueltas sin pasar de `PRIMARY` | Traza | **No** |
| `ESCALATION_RATE` | % que llegan a `SECONDARY` | Traza | **No** |
| `RAW_TRAVERSAL_RATE` | % que llegan a artefacto | Traza | **No** |
| `TERMINAL_UNKNOWN` | consultas que terminan en `UNKNOWN` | Clasificación de salida | **No** |
| `TERMINAL_CONFLICT` | consultas que terminan en `CONFLICT` | Ídem | **Parcial: 6 conflictos conocidos** |
| `TERMINAL_NOT_AVAILABLE` | consultas que terminan en `NOT_AVAILABLE` | Ídem | **Parcial: 4 topics** |
| `WEB_REQUIRED` | consultas que requieren fuente externa | Ídem | **No** |
| `TEMPORALITY_MISCLASSIFIED` | veces que un doc `HISTORICAL` se sirió como actual | Auditoría de respuestas | **0 requerida** |
| `HOST_SCOPE_UNKNOWN_RATE` | % de respuestas cuyo `HOST_SCOPE` quedó `UNKNOWN` | Traza | **Baseline: 229/256 docs** |

**Instrumentación propuesta:** un fichero de traza opcional
`01-AUDITORIA/DOCUMENTATION-ROUTER-DESIGN/ROUTING-LOG.jsonl` con una línea por consulta
(`query`, `domain`, `topic`, `question_type`, `primary_read`, `escalations[]`,
`terminal`, `temporality`, `host_scope`). Sin él, las seis primeras métricas no son medibles.
**No se crea en esta fase**: implicaría escribir en el repositorio durante consultas normales, lo
que ensuciaría el árbol publicable.

**Métrica de diseño (verificable sin traza):** `NAV_DEPTH=1` para toda consulta que resuelva el
`PRIMARY`. Si alguna necesita 2+, es un defecto del router. Verificable en
`ROUTING-SIMULATION.md`.

---

## 14. Lo que este diseño NO hace

| No hace | Por qué |
|---|---|
| No implementa el router | Esta fase es diseño |
| No modifica `AGENTS.md` | El encargo lo prohíbe explícitamente |
| No repara las 140 referencias | Prohibido |
| No resuelve los 6 conflictos | Prohibido y no corresponde a un router |
| No corrige contradicciones de host | Requieren re-medición, no edición |
| No toca los 5 mecanismos de navegación existentes | Requieren decisión editorial |
| No crea índice de dominios | Duplicaría `DOCUMENTATION-TOPICS.md` §15 |
| No aplica ningún parche | Prohibido |
| No crea documentación para `BACO`/`FIREFOX`/`GRUB`/`UDEV` | Prohibido por el encargo |
| No inventa métricas | Solo define cómo medirlas |

---

## 15. Validación de este diseño

| Comprobación | Resultado |
|---|---|
| Rutas citadas en el diseño que existen | Verificado en `ROUTING-SIMULATION.md` §fuentes |
| Ficheros modificados fuera de `01-AUDITORIA/DOCUMENTATION-ROUTER-DESIGN/` | **0** |
| Ficheros históricos modificados | **0** |
| Código modificado | **0** |
| Sistema modificado | **0** |
| `AGENTS.md` modificado | **0** |
| Commit / tag / push / remote | **0** |
| `git diff` (unstaged) | **0** |
| Índice de 360 rutas | Intacto |
| `HEAD` | `c6146788e0d4fb12d9b0ec1209fa2840692de0c5` |

Detalle y hashes en `ROUTING-GAPS.md` §7.
