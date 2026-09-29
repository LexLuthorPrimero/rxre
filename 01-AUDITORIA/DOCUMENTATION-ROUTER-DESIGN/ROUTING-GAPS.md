# ROUTING-GAPS — Huecos, riesgos y límites del diseño del router

**Fecha:** 2026-09-25T23:10Z
**Estado:** diseño. Nada implementado, ningún archivo histórico modificado.

---

## 1. Huecos de los que el router no puede escaparse

Estos no son defectos del router: son huecos de la documentación que el router debe **exponer**,
no rellenar.

| # | Hueco | Efecto en el router | Lo que haría falta |
|---:|---|---|---|
| G1 | **No existe fuente HOST-C salvo 1 documento.** `PATCH-SOURCES.md` §3 | 15 de 16 documentos CURRENT describen HOST-B. Toda consulta de «estado actual» termina en `STALE` o `CURRENT_EVIDENCE=NOT_AVAILABLE` | Re-ejecutar `tools/validate_rx550_final.py` |
| G2 | **Los 16 CURRENT cubren poco.** Solo 8 de 68 topics tienen documento CURRENT | `DOMAIN` D4 (arquitectura GPU), D5 (potencia), D7 (medición), D8 (C1), D9 (storage), D10 (background) **no tienen ninguna fuente CURRENT** | Re-verificar esos dominios en HOST-C, o declararlos `HISTORICAL_ONLY` de forma explícita |
| G3 | **229 de 256 documentos no declaran su host** | `HOST_SCOPE=UNKNOWN` para el 89 % del repositorio. Un `HISTORICAL_OLD_DISK` atribuido por procedencia, no por declaración | Un `HOST_SCOPE` en el inventario (columna propuesta) + revisión manual de los `A-INFERRED` |
| G4 | **4 topics sin primaria** (`BACO`, `FIREFOX`, `GRUB`, `UDEV`) | Terminal `NOT_AVAILABLE` sin escalada posible | Nada. El router no crea documentación. Correcto por diseño |
| G5 | **6 conflictos sin resolver** | El router devuelve 2 fuentes y se detiene | Decisión editorial, no técnica |
| G6 | **140 referencias rotas** | El router las expone con `REASON` | Reparación autorizada (no en esta fase) |
| G7 | **No hay bitácora de la migración al disco nuevo** | No se puede responder «qué cambió al migrar» salvo por `PATCH-SOURCES.md` §3 | Un documento de migración. No creado aquí |
| G8 | **`MASTER-RESEARCH-STATUS.md` se contradice a sí mismo** (snapshots vs addenda vigentes) | El router debe leer el addenda, no el cuerpo. Un lector humano que lo abra sin contexto puede leer mal | Separar snapshots en un archivo aparte. Requiere decisión editorial |
| G9 | **3 posibles duplicados sin verificar** (`C1-PREFLIGHT-055714Z` y `060029Z` miden 2725 bytes cada uno) | El router podría leer el equivocado | Comparación byte a byte |
| G10 | **59 documentos sin referencia entrante** | El router los alcanza por topic, no por enlace. Riesgo de que un topic sin entrada en la tabla quede inalcanzable | Enlazarlos o incluirlos explícitamente en la tabla de 68 topics |

---

## 2. Riesgos del diseño

| # | Riesgo | Probabilidad | Impacto | Mitigación en el diseño |
|---:|---|---|---|---|
| R1 | **El router se lee como índice y se cumple su propósito sin las reglas.** Alguien lo usa como lista de archivos y lee 40 | Alta | Alto | Las 14 reglas propuestas en `AGENTS.md` son la única defensa. Sin ellas el router es decorativo |
| R2 | **`HOST_SCOPE=UNKNOWN` se normaliza a un valor por defecto** | Media | **Crítico** | `UNKNOWN` es terminal, no un valor por defecto. Regla 14 de la propuesta |
| R3 | **La tabla de 68 topics queda desactualizada** cuando se añada un documento | Alta | Medio | `CONFIDENCE` + regla: si el topic no está en la tabla, escalar al censo, no improvisar |
| R4 | **El router da `NOT_AVAILABLE` de más** y el agente busca por su cuenta | Media | Medio | `NOT_AVAILABLE` debe ir acompañado de la lista de menciones, para que el agente sepa que sí las hay |
| R5 | **Se confunde `HOST-B` con el host vivo** otra vez | Media | **Crítico** | `STALE` es un terminal de primer nivel, no una nota. Regla 4 de la propuesta |
| R6 | **El diseño se implementa sin la cadena de RAW** y el agente abre artefactos a ciegas | Media | Alto | La cadena `EXPERIMENT_DIR → EXPERIMENT_MD → artefacto` es la regla 6 |
| R7 | **Los 5 mecanismos de navegación existentes compiten** con el router | Alta | Medio | El router declara que no los sustituye. Si en el futuro se fusionan, es otra decisión |
| R8 | **La taxonomía R2 ampliada se vuelve inestable** si se añaden tokens | Baja | Medio | 5 extensiones justificadas una por una. Cualquier token nuevo requiere justificación escrita |
| R9 | **El cambio de host se normaliza sin dejar rastro** | Media | **Crítico** | `HOST_SCOPE` es dimensión de primera clase, no un campo opcional |
| R10 | **Un agente nuevo no encuentra el router** porque no está enlazado desde `README.md` | Media | Alto | Enlazado desde `README.md` en la fase de implementación. Sin eso el router es inaccesible |

---

## 3. Lo que el diseño NO puede hacer

| No puede | Razón |
|---|---|
| Responder «¿qué versión de Mesa tiene el host?» sin re-medir | G1 |
| Saber si un documento histórico es válido en HOST-C | G3: el 89 % no declara host |
| Elegir entre las 2 fuentes de un `CONFLICT` | Fuera de su función. Un router no arbitra evidencia |
| Reparar las 140 referencias | Fuera de alcance |
| Detectar que un documento `.md` **miente** sobre su propio estado | El router confía en el documento; no verifica sus afirmaciones contra el sistema |
| Convertir `RAW_EVIDENCE` en evidencia interpretable | Requiere el `.md` del experimento. Es el diseño, no una limitación |
| Sustituir a `AGENTS.md` | El router es un mecanismo de descubrimiento, no un conjunto de instrucciones |

---

## 4. Verificación de que el diseño evita lecturas innecesarias

La simulación de 18 consultas demuestra:

| Verificación | Resultado |
|---|---|
| `NAV_DEPTH` > 1 en alguna consulta | **0** |
| Consultas que leen > 3 ficheros | **0** |
| Consultas que barreen el directorio | **0** |
| Consultas que abran artefactos sin pasar por su `.md` | **0** (6 rutas de RAW, 6 correctas) |
| Consultas que presentes histórico como actual | **0** |
| Consultas que inventen un valor para un `CONFLICT` | **0** |
| Consultas que terminan en 0 lecturas | 1 (GRUB, terminal `NOT_AVAILABLE`) |
| Respuestas sin `TEMPORALITY` declarada | **0** de 18 |
| Respuestas sin `HOST_SCOPE` declarado | **0** de 18 |

**Esto es diseño, no medición.** No hay número de latencia ni de tokens. Ver la nota de
honestidad en `ROUTING-SIMULATION.md`.

---

## 5. Ficheros que la implementación tendría que crear

| Fichero | Acción | Tamaño | Nota |
|---|---|---:|---|
| `DOCUMENTATION-ROUTER.md` | **Crear** | ≤130 líneas | La tabla de 68 topics en formato de decisión |
| `01-AUDITORIA/DOCUMENTATION-CENSUS/DOCUMENTATION-INVENTORY.tsv` | **Modificar**: +3 columnas | 1576×23 | `EXPERIMENT_DIR`, `EXPERIMENT_MD`, `HOST_SCOPE` |
| `AGENTS.md` | **Modificar**: +sección | ~25 líneas | `PROPOSED_AGENTS_ROUTING_RULES`, 14 reglas |
| `README.md` | **Modificar**: +1 enlace | ~2 líneas | Enlace al router en §Documentos finales |
| `03-EXPERIMENTOS/AGENTS.md` | **Crear** (opcional) | ~10 líneas | Enlace al topico de experimentos. Optimización, no requisito |

**No se crearán:** índice de dominios, `PRIMARY-SOURCES.md`, `TOPIC-INDEX.md`, ni copies del
censo. Toda esa información ya existe en `DOCUMENTATION-CENSUS/DOCUMENTATION-TOPICS.md` §15 y
`DOCUMENTATION-INVENTORY.tsv`.

**Verificación de que el router no duplica el censo:**

| Dato | ¿Dónde vive? | ¿Se copia al router? |
|---|---|---|
| Las 68 filas de topic con FIRST/SECOND/RAW/ESCALATION | `DOCUMENTATION-TOPICS.md` §15 | **Sí**, reformateado + 4 columnas nuevas. Es la tabla de decisión |
| Los 1576 registros con categoría/temporalidad/prioridad | `DOCUMENTATION-INVENTORY.tsv` | **No**. El router apunta a él |
| Las 140 referencias rotas con su clasificación | `DOCUMENTATION-RELATIONSHIPS.md` §5 | **No**. El router declara el `REASON`, no la lista |
| Los 6 conflictos con sus fuentes | `DOCUMENTATION-GAPS.md` §2 | **No**. El router declara `CONFLICT_ID` y devuelve las fuentes |
| La taxonomía R2 | `R2-GLOBAL-DOCUMENTATION-MAP.md` §0 | **No**. Se referencia y se amplía con 5 tokens justificados |

---

## 6. Dependencias de la fase de implementación

```
  1. DECISIÓN: ¿se acepta HOST_SCOPE como dimensión obligatoria?
       └─ Sin esto, R2 y R5 son críticos.

  2. Modificar el inventario: +3 columnas
       └─ Requiere regenerar el TSV y re-hashear.
       └─ Los hashes de DOCUMENTATION-GAPS.md §13 quedarán obsoletos.

  3. Crear DOCUMENTATION-ROUTER.md con los 68 topics
       └─ Los 4 sin primaria (BACO, FIREFOX, GRUB, UDEV) con PRIMARY=NOT_AVAILABLE.

  4. Modificar AGENTS.md con las 14 reglas
       └─ No autorizado en esta fase.

  5. Enlazar el router desde README.md
       └─ Sin esto el router es inaccesible (R10).

  6. Verificar con una segunda simulación
       └─ Comparar NAV_DEPTH y nº de lecturas.
```

El paso 2 invalida los hashes del censo. Es un coste conocido: los SHA-256 de
`DOCUMENTATION-CENSUS/*`Scannerán obsoletos y habrá que recomputarlos. **No se ha hecho ahora**
para no invalidar un censo recién validado.

---

## 7. Validación de esta fase

| Comprobación | Resultado |
|---|---|
| Ficheros creados | 4, todos en `01-AUDITORIA/DOCUMENTATION-ROUTER-DESIGN/` |
| Ficheros modificados fuera del directorio nuevo | **0** |
| Ficheros históricos modificados | **0** |
| `AGENTS.md` modificado | **0** |
| Código modificado | **0** |
| Sistema modificado | **0** |
| Commit / tag / push / remote | **0** |
| `git diff` (unstaged) | **0** |
| Índice de 360 rutas | Intacto |
| `HEAD` | `c6146788e0d4fb12d9b0ec1209fa2840692de0c5` |
| Parches aplicados | **0** |

### Rutas citadas en estos documentos — verificadas

Todas las rutas `FIRST_READ` y `SECOND_READ` de `ROUTING-SIMULATION.md` existen. Verificado
programáticamente: 18 consultas, 0 rutas inexistentes.

Rutas de los `PRIMARY` principales:

```
README.md                                                            existe
PROBLEM-STATUS-FINAL.md                                              existe
PATCH-REGISTRY-FINAL.md                                              existe
RELEASE-CANDIDATE.md                                                 existe
FINAL-RELEASE-REPORT.md                                              existe
RELEASE-EXCLUSIONS.md                                                existe
INSTALL.md                                                           existe
ROLLBACK.md                                                          existe
TESTING.md                                                           existe
CHANGELOG.md                                                         existe
AGENTS.md                                                            existe
01-AUDITORIA/PATCH-RECOVERY/PATCH-RECOVERY-REPORT.md                 existe
01-AUDITORIA/PATCH-RECOVERY/PATCH-REGISTRY-RECOVERED.md              existe
01-AUDITORIA/PATCH-RECOVERY/PATCH-SOURCES.md                         existe
01-AUDITORIA/FINAL-VALIDATION/FINAL-VALIDATION-20260925T135831Z.md   existe
01-AUDITORIA/FINAL-VALIDATION/FINAL-VALIDATION-20260925T135831Z.json existe
01-AUDITORIA/FASE-VFIO-PASSTHROUGH/VFIO-FEASIBILITY-AUDIT-…md        existe
01-AUDITORIA/FASE-P0-EXPERIMENTAL-VALIDITY-GATE/P0-…-2026-09-24.md   existe
01-AUDITORIA/DOCUMENTARY-RECONCILIATION-2026-09-25.md                existe
01-AUDITORIA/FASE-R5-C1-TECHNICAL-DOCUMENTATION/C1-TECHNICAL-RECORD.md existe
01-AUDITORIA/AUDIT-001/ERRATA.md                                     existe
01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/C1-PREFLIGHT-…-061932Z-PRIV.md  existe
01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/C1-PREFLIGHT-…-061932Z-PRIV.json existe
02-ARQUITECTURA/knowledge.md                                         existe
03-EXPERIMENTOS/fase-a-discriminacion-20260919-114241/RESULTADOS-FASE-A.md existe
03-EXPERIMENTOS/fase-b-cap-probe-20260919-122038/EP08-…              existe
03-EXPERIMENTOS/FASE-R4B-GOVERNOR/EXP-F4-A-RESULTADOS-v2.3.md        existe
03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/EXP-F1-A-RESULTADOS.md existe
03-EXPERIMENTOS/WORKLOAD-SINTETICO/RESEARCH.md                       existe
03-EXPERIMENTOS/WORKLOAD-SINTETICO/src/graphics.cpp                  existe
03-EXPERIMENTOS/ep06-soak-cap-20260919-205645/RESULTADOS-EP06.md     existe
04-IMPLEMENTACION/C1-ISOLATION-DESIGN-v1.0.md                        existe
04-IMPLEMENTACION/C1-ISOLATION-AUTOMATOR.md                          existe
04-IMPLEMENTACION/rx550-torneo/README-FASE1.md                       existe
05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-2-POWERPLAY-MCLK-SMU7.md existe
05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-3-MESA-WORKAROUNDS-POLARIS12.md existe
00-INDICE/MASTER-RESEARCH-STATUS.md                                  existe
00-INDICE/R2-GLOBAL-DOCUMENTATION-MAP.md                              existe
01-AUDITORIA/DOCUMENTATION-CENSUS/DOCUMENTATION-CENSUS.md            existe
01-AUDITORIA/DOCUMENTATION-CENSUS/DOCUMENTATION-TOPICS.md            existe
01-AUDITORIA/DOCUMENTATION-CENSUS/DOCUMENTATION-RELATIONSHIPS.md     existe
01-AUDITORIA/DOCUMENTATION-CENSUS/DOCUMENTATION-GAPS.md             existe
01-AUDITORIA/DOCUMENTATION-CENSUS/DOCUMENTATION-INVENTORY.tsv       existe
tools/validate_rx550_final.py                                        existe
```

### SHA-256 de esta fase

Se imprimen al cierre de la fase en la salida L1 y son verificables con:

```bash
sha256sum 01-AUDITORIA/DOCUMENTATION-ROUTER-DESIGN/*
```

Un fichero no puede contener su propio hash: los cuatro están en la salida L1, no aquí.

---

## 8. Confirmación de restricciones

| Restricción | Cumplida |
|---|---|
| No aplicar patches | **Sí** — 0 |
| No modificar sistema | **Sí** — 0 |
| No modificar Mesa | **Sí** — 0 |
| No modificar kernel | **Sí** — 0 |
| No modificar amdgpu | **Sí** — 0 |
| No modificar power | **Sí** — 0 |
| No modificar DPM | **Sí** — 0 |
| No ejecutar C1 | **Sí** — 0 |
| No modificar systemd | **Sí** — 0 |
| No modificar GRUB | **Sí** — 0 |
| No modificar udev | **Sí** — 0 |
| No commit | **Sí** — 0 |
| No push | **Sí** — 0 |
| No remote | **Sí** — 0 |
| No reescribir historia | **Sí** — 0 |
| No modificar contenido histórico | **Sí** — 0 |
| No reparar referencias | **Sí** — 0 |
| No corregir contradicciones | **Sí** — 0 |
| No modificar `AGENTS.md` | **Sí** — 0 |
| No crear `DOCUMENTATION-ROUTER.md` | **Sí** — solo diseño |
| No continuar con la implementación | **Sí** — esperando autorización |
