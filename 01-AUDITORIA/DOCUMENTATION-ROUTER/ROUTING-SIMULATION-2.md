# ROUTING-SIMULATION-2 — Segunda simulación sobre el router implementado

**Fecha:** 2026-09-25T23:40Z
**Router bajo prueba:** `01-AUDITORIA/DOCUMENTATION-ROUTER/DOCUMENTATION-ROUTER.md`
**Metodología:** traza de diseño, ejecutada contra las rutas reales del repositorio. No es una
medición de rendimiento de un agente. Ver `ROUTING-SIMULATION.md` (simulación 1) para el
metodólogo y `../DOCUMENTATION-ROUTER-DESIGN/DOCUMENTATION-ROUTER-DESIGN.md` §13 para las métricas.

**Consultas:** las 18 de la simulación 1, más 10 nuevas (19–28).

---

## Bloque A — las 18 consultas originales

| # | QUERY | NAV_DEPTH | FILES_READ | PRIMARY | SECONDARY | RAW | WEB | TEMPORALITY | HOST_SCOPE | RESULT_CLASS |
|---:|---|---:|---:|---|---|---|---|---|---|---|
| 1 | ¿Estado actual de la RX 550? | 1 | 3 | `README.md` | `PROBLEM-STATUS-FINAL.md` · `PATCH-SOURCES.md` | no | no | `STALE` | B d vs **C d** | `STALE` + `CURRENT_EVIDENCE=NOT_AVAILABLE` |
| 2 | ¿Qué sabemos de runtime PM? | 1 | 2 | `P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md` | `rx550-torneo/README-FASE1.md` | no | no | `HISTORICAL_OLD_DISK` | A d | `CURRENT_EVIDENCE=NOT_AVAILABLE` |
| 3 | ¿Qué pasó con DPM? | 1 | 3 | `AUDIT-001/ERRATA.md` | `RESULTADOS-FASE-A.md` · `R0-2-POWERPLAY-MCLK-SMU7.md` | no | no | `MIXED` | A i | `RESOLVED` (etiquetado) + `UNRESOLVED` (causalidad) |
| 4 | ¿Qué sabemos del HDD? | 1 | 2 | `P0-…GATE-2026-09-24.md` | `knowledge.md` | no | no | `HISTORICAL_OLD_DISK` | A i | `CURRENT_EVIDENCE=NOT_AVAILABLE` |
| 5 | ¿Qué evidencia existe de Btrfs? | 1 | 3 | `PROBLEM-STATUS-FINAL.md` (P-012) | `WORKLOAD-SINTETICO/RESEARCH.md` · `DOCUMENTARY-RECONCILIATION-2026-09-25.md` | `WORKLOAD-SINTETICO/src/graphics.cpp` | no | `MIXED` | ? d | `CONFLICT` C6 |
| 6 | ¿Qué pasó con R4B? | 1 | 2 | `EXP-F4-A-RESULTADOS-v2.3.md` | `MASTER-RESEARCH-STATUS.md` §Addenda D6 | `FASE-R4B-GOVERNOR/results/v23/` | no | `HISTORICAL_OLD_DISK` | ? i | `INCONCLUSIVE` |
| 7 | ¿R4C está validado? | 1 | 2 | `EXP-F1-A-RESULTADOS.md` | `FASE-R4C-…/README.md` | `FASE-R4C-…/results/` | no | `HISTORICAL_OLD_DISK` | ? i | `VALIDADO_EN_HOST-A` |
| 8 | ¿Qué sabemos de Mesa? | 1 | 4 | `PATCH-REGISTRY-FINAL.md` | `R0-3-MESA-WORKAROUNDS-POLARIS12.md` · `DOCUMENTARY-RECONCILIATION-2026-09-25.md` · `PATCH-REGISTRY-RECOVERED.md` | no | no | `MIXED` | A+B+C | `CONFLICT` C2 |
| 9 | ¿Qué pasó con C1? | 1 | 4 | `C1-ISOLATION-DESIGN-v1.0.md` | `C1-ISOLATION-AUTOMATOR.md` · `DOCUMENTARY-RECONCILIATION-2026-09-25.md` · `C1-TECHNICAL-RECORD.md` | `C1-PREFLIGHT-…-PRIV.json` | no | `MIXED` | A d | `CONFLICT` C1 + `DEFERRED` |
| 10 | ¿Qué sabemos del ownership? | 1 | 3 | `P0-…GATE-2026-09-24.md` | `C1-PREFLIGHT-…-PRIV.md` · `AGENTS.md` | `C1-PREFLIGHT-…-PRIV.json` | no | `HISTORICAL_OLD_DISK` | A d | `PARTIAL` + `CURRENT_EVIDENCE=NOT_AVAILABLE` |
| 11 | ¿Qué patches fueron recuperados? | 1 | 2 | `PATCH-REGISTRY-RECOVERED.md` | `PATCH-RECOVERY-REPORT.md` | no | no | `CURRENT_NEW_DISK` | **C d** | `COMPLETO_CON_GAPS` |
| 12 | ¿Qué patches son de sistema? | 1 | 2 | `PATCH-REGISTRY-RECOVERED.md` §B | `PATCH-SOURCES.md` | no | no | `CURRENT_NEW_DISK` | **C d** | `NEW_DISK_APPLIED=NO` |
| 13 | ¿Qué sabemos del nuevo disco? | 1 | 1 | `PATCH-SOURCES.md` §3 | — | no | no | `CURRENT_NEW_DISK` | **C d** | `ANSWERED` (HOST-C) |
| 14 | ¿Por qué un resultado antiguo no es actual? | 1 | 3 | `DOCUMENTATION-CENSUS.md` §5 | `PATCH-SOURCES.md` §3 · `FINAL-VALIDATION-…md` | no | no | `MIXED` | los 3 | `EXPLICADO` |
| 15 | ¿Qué evidencia existe sobre GRUB? | **0** | **0** | `NOT_AVAILABLE` | — | — | no | `NOT-APPLICABLE` | n/a | `NOT_AVAILABLE` |
| 16 | ¿Por qué PowerPlay sube MCLK y baja SCLK? | 1 | 2 | `R0-2-POWERPLAY-MCLK-SMU7.md` | `RESULTADOS-EP06.md` | `ep06-soak-cap-…/` | no | `HISTORICAL_OLD_DISK` | A i | `UNKNOWN` (atribución local) |
| 17 | ¿Listo para publicar en GitHub? | 1 | 3 | `RELEASE-CANDIDATE.md` | `FINAL-RELEASE-REPORT.md` · `RELEASE-EXCLUSIONS.md` | no | no | `CURRENT_NEW_DISK` | B d | `READY_FOR_GITHUB=NO` |
| 18 | ¿Algo se rompió? | 1 | 2 | `PROBLEM-STATUS-FINAL.md` | `PATCH-REGISTRY-FINAL.md` | — | no | `CURRENT_NEW_DISK` | B i | `CURRENT_EVIDENCE=NOT_AVAILABLE` |

### Comparación con la simulación 1

| Métrica | Sim. 1 (diseño) | Sim. 2 (implementado) | Δ |
|---|---:|---:|---|
| `NAV_DEPTH` máxima | 1 | **1** | = |
| Consultas con `NAV_DEPTH=0` | 1 (Q15) | 1 (Q15) | = |
| `FILES_READ` máximo | 4 | **4** (Q9) | = |
| `FILES_READ` medio | 2.44 | **2.39** | −0.05 |
| Consultas con `FILES_READ ≥ 3` | 7 | **8** | +1 |
| Consultas que barrenan el repo | 0 | **0** | = |
| RAW sin `EXPERIMENT_MD` previo | 0 | **0** | = |
| Histórico presentado como actual | 0 | **0** | = |
| `CONFLICT` preservados | 4 | **4** | = |
| `NOT_AVAILABLE` terminals | 1 | 1 | = |
| Respuestas sin `TEMPORALITY` | 0 | **0** | = |
| Respuestas sin `HOST_SCOPE` | 0 | **0** | = |

**Diferencia real:** Q9 pasó de 3 a 4 ficheros porque el router ahora nombra
`C1-TECHNICAL-RECORD.md` explícitamente para el conflicto C1, donde antes quedaba implícito.
Es un coste aceptable a cambio de que el conflicto sea trazable a un fichero concreto.

**Sin cambios:** ninguna consulta nueva complementó, ninguna profundiza, ninguna abre artefactos
sin pasar por su `.md`.

---

## Bloque B — las 10 consultas nuevas

### 19 · ¿Cuál es el estado actual de Mesa?

```
ROUTING        D6 / MESA / Q1 STATUS / CURRENT demanded / HOST-C demanded
FIRST_READ     PATCH-REGISTRY-FINAL.md  §Mesa
SECOND_READ    05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-3-MESA-WORKAROUNDS-POLARIS12.md
               01-AUDITORIA/DOCUMENTARY-RECONCILIATION-2026-09-25.md  §MESA_*
               01-AUDITORIA/PATCH-RECOVERY/PATCH-REGISTRY-RECOVERED.md  RX550-MP-01
RAW_IF_NEEDED  ninguno
NAV_DEPTH      1   FILES_READ 4
EXPECTED_RESULT  STATUS=CONFLICT   CONFLICT_ID=C2
                Cuatro valores, tres declarados y uno no:
                  26.2.2   MESA_CANONICAL  (HOST-A, investigación)
                  26.2.3   MESA_EXTERNAL   (HOST-A, investigación)
                  25.3.2   documentos raíz  (HOST-B, NO figura en la declaración de precedencia)
                  26.2.3   HOST-C, host vivo  (PATCH-SOURCES.md)
                PRECEDENCE_DECLARED=PARTIAL — la declaración de precedencia solo cubre
                  26.2.2 vs 26.2.3. El 25.3.2 de la raíz NO está reconciliado.
                Workarounds aplicables a Polaris12: ya upstream (ALREADY_FIXED_UPSTREAM).
                EP05 con Mesa CUSTOM: NO reprodujo E5 (NOT_REPRODUCED).
                RX550-MP-01 (commit 583c5d2f44152ed70d6f9aff58fbca5abcf7376d):
                  cambio de LOGGING, no funcional. ORIGINAL_APPLIED=UNKNOWN.
                  NEW_DISK_APPLIED=NO. SYSTEM_CHANGE_REQUIRED=SI.
                mesa-vulkan-drivers NO instalado en HOST-C → cualquier afirmación sobre
                  RADV necesita re-verificación.
TEMPORALITY    MIXED
HOST_SCOPE     A + B + C (los cuatro valores)
```

**Demostración:** el router devuelve 4 valores y declara que la precedencia solo cubre 2 de
ellos. No elige.

### 20 · ¿Cuál es el estado actual de la RX 550 en el nuevo disco?

```
ROUTING        D3 / HOST_IDENTITY / Q19 HOST_IDENTITY / CURRENT demanded / HOST-C demanded
FIRST_READ     01-AUDITORIA/PATCH-RECOVERY/PATCH-SOURCES.md  §3
SECOND_READ    ninguno necesario: §3 ya contiene la tabla comparativa de las 3 identidades
RAW_IF_NEEDED  01-AUDITORIA/FINAL-VALIDATION/FINAL-VALIDATION-20260925T135831Z.json
               → TEMPORALITY=CURRENT_NEW_DISK_STALE_HOST, HOST_SCOPE=B DECLARED → STALE
NAV_DEPTH      1   FILES_READ 1 (+1 si se inspecciona el JSON marcado STALE)
EXPECTED_RESULT  HOST-C, medido 2026-09-25T22:22Z:
                  OS       Nobara Linux 44 (KDE Plasma), PLATFORM_ID=platform:f44
                  kernel   7.1.3-200.nobara.fc44.x86_64
                  Mesa     mesa-dri-drivers 26.2.3-1.fc44
                  LLVM     22.1.8-4.fc44
                  libdrm   2.4.134-1.fc44
                  firmware linux-firmware-20260810-1.fc44
                  root     /dev/sdb3 ext4
                  GPU      Intel  card0 / 0000:00:02.0 / i915 / renderD128
                           RX550  card1 / 0000:01:00.0 / amdgpu / renderD129 / hwmon1
                  mesa-vulkan-drivers  NO INSTALADO
                  kalm* 0 unidades · system-autopilot* 0 unidades
                PCI 1002:699f y BDF 0000:01:00.0 NO cambiaron entre HOST-B y HOST-C.
                NO re-verificado en HOST-C: validador, 64/64, 110/110, 54+1.
                Éstos siguen siendo resultados de HOST-B.
TEMPORALITY    CURRENT_NEW_DISK
HOST_SCOPE     C DECLARED
```

**Demostración:** el router entrega el host vivo y marca explícitamente que los tests no se
han re-ejecutado. `cardN` cambió de `card2` a `card1` y el router no lo normaliza.

### 21 · ¿Qué parches del sistema existen pero NO están aplicados?

```
ROUTING        D2 / PATCHES / Q8 PATCH / CURRENT / HOST-C
FIRST_READ     01-AUDITORIA/PATCH-RECOVERY/PATCH-REGISTRY-RECOVERED.md  §B (13 entradas)
SECOND_READ    01-AUDITORIA/PATCH-RECOVERY/PATCH-SOURCES.md  §5 (hashes del backup)
RAW_IF_NEEDED  ninguno — los artefactos están en el backup, fuera del repo
               → HISTORICAL_OTHER_HOST
NAV_DEPTH      1   FILES_READ 2
EXPECTED_RESULT  PATCH_CLASS=SYSTEM_PATCH. 13 entradas. NEW_DISK_APPLIED=NO en TODAS.
                Verificado por lectura del sistema 2026-09-25T22:22Z:
                  systemctl list-unit-files 'kalm*'        → 0
                  systemctl list-unit-files 'system-autopilot*' → 0
                  /opt/kalm                                   → ausente
                  /usr/local/bin/kalm*                        → ausente
                  /opt/mesa-26.2.2-rx550-haswell              → ausente
                SYSTEM_CHANGE_REQUIRED=SI en las 13.
                Riesgo ALTO: PM-01 (kalm-gpu escribe power1_cap y DPM),
                              PM-02 (power-sweep escribe el cap),
                              SCP-03 (instalador: 10 sysctl + disable + enable),
                              SD-01 (kalm-gpu.service, Nice=-5).
                Parciales (unidad exacta, payload ausente): SD-02, SD-03, SD-04.
                Sin fuente: UNK-01 (system-autopilot, solo 12 hex de hash).
                CONCLUSIÓN CONSERVADA: Kalm NO explica el régimen E1/E3/E5.
                El router NO aplica ninguno, no hace cherry-pick, no construye nada.
TEMPORALITY    CURRENT_NEW_DISK
HOST_SCOPE     C DECLARED
```

### 22 · ¿Qué evidencia pertenece al disco viejo?

```
ROUTING        D1 / HISTORY / Q18 HISTORY / HISTORICAL / HOST-A
FIRST_READ     01-AUDITORIA/DOCUMENTATION-CENSUS/DOCUMENTATION-CENSUS.md  §2.2
SECOND_READ    01-AUDITORIA/DOCUMENTATION-ROUTER/DOCUMENTATION-INVENTORY-ROUTING.tsv
               (columna HOST_SCOPE; filtrar HOST_SCOPE=HOST-A)
RAW_IF_NEEDED  ninguno
NAV_DEPTH      1   FILES_READ 2
EXPECTED_RESULT  HOST-A = disco anterior: Nobara 44, kernel 7.2.4/7.2.6,
                Mesa 26.2.2/26.2.3, RX550=card1.
                1444 de 1576 filas del censo son HISTORICAL_OLD_DISK.
                En el inventario de routing:
                  HOST-A DECLARED  15 documentos  (el texto nombra el host)
                  HOST-A INFERRED 113 documentos  (atribución por procedencia)
                  + 1320 artefactos RAW con HOST_SCOPE=UNKNOWN
                Documentos DECLARED más citados:
                  02-ARQUITECTURA/knowledge.md
                  00-INDICE/MASTER-RESEARCH-STATUS.md
                  01-AUDITORIA/FASE-P0-EXPERIMENTAL-VALIDITY-GATE/P0-…-2026-09-24.md
                  01-AUDITORIA/FASE-R5-C1-TECHNICAL-DOCUMENTATION/C1-TECHNICAL-RECORD.md
                  03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT/*
                  04-IMPLEMENTACION/C1-ISOLATION-AUTOMATOR.md
                  00-INDICE/AUDITORIA-CONSUMO-SEGUNDO-PLANO.md
                  00-INDICE/PROTOCOLO-AB-LIMPIEZA-BACKGROUND.md
                El backup externo ~/Escritorio/RX550_Modo_Torneo_Backup_2026-09-19_0836/
                es HISTORICAL_OTHER_HOST: fuera del repositorio, no figura en el inventario.
                ADVERTENCIA: 229 de 256 documentos NO declaran su host. HOST-A INFERRED es
                más débil que HOST-A DECLARED y el router lo marca así.
TEMPORALITY    HISTORICAL_OLD_DISK
HOST_SCOPE     A (declarado e inferido, distinguiendo ambos)
```

### 23 · ¿Qué evidencia pertenece al host vivo?

```
ROUTING        D3 / HOST_IDENTITY / Q19 HOST_IDENTITY / CURRENT demanded / HOST-C
FIRST_READ     01-AUDITORIA/PATCH-RECOVERY/PATCH-SOURCES.md  §3
SECOND_READ    01-AUDITORIA/DOCUMENTATION-ROUTER/DOCUMENTATION-INVENTORY-ROUTING.tsv
               (filtrar HOST_SCOPE=HOST-C)
RAW_IF_NEEDED  ninguno
NAV_DEPTH      1   FILES_READ 2
EXPECTED_RESULT  SOLO 2 filas del inventario tienen HOST_SCOPE=HOST-C, ambas DECLARED:
                  01-AUDITORIA/PATCH-RECOVERY/PATCH-SOURCES.md
                  01-AUDITORIA/PATCH-RECOVERY/PATCH-REGISTRY-RECOVERED.md
                Los 7 documentos CURRENT con HOST_B DECLARED (README.md,
                PROBLEM-STATUS-FINAL.md, INSTALL.md, CHANGELOG.md, RELEASE-CANDIDATE.md,
                FINAL-VALIDATION-*.md, PATCH-RECOVERY-REPORT.md) describen un host
                que YA NO ES el vivo → STATUS=STALE, no usables como estado actual.
                2 documentos declaran más de un host → UNKNOWN DECLARED:
                  PATCH-REGISTRY-FINAL.md, ROLLBACK.md
                1406 filas con HOST_SCOPE=UNKNOWN, de ellas 1320 artefactos RAW.
                Conclusión: la evidencia del host vivo es mínima y se reduce a un
                documento comparativo. Todo lo demás requiere re-medición.
TEMPORALITY    CURRENT_NEW_DISK
HOST_SCOPE     C DECLARED
```

### 24 · ¿Qué sabemos de BACO?

```
ROUTING        D11 / BACO / Q2 HARDWARE / no aplica
FIRST_READ     NOT_AVAILABLE
SECOND_READ    ninguno — no hay fuente primaria
RAW_IF_NEEDED  ninguno
NAV_DEPTH      terminal en 0   FILES_READ 0
EXPECTED_RESULT  PRIMARY_SOURCE=NOT_AVAILABLE
                TERMINAL=NOT_AVAILABLE — no hay escalada posible.
                8 menciones en el repositorio, TODAS de paso:
                  PROBLEM-STATUS-FINAL.md, PATCH-REGISTRY-FINAL.md,
                  RELEASE-CANDIDATE.md, FINAL-RELEASE-REPORT.md,
                  P0-…GATE-2026-09-24.md, VFIO-FEASIBILITY-AUDIT-…md,
                  y 2 más.
                Ningún documento define qué se midió de BACO, con qué método,
                ni con qué resultado.
                El router NO crea documentación para este hueco.
                Si el usuario necesita el estado de BACO en el host vivo: no hay
                fuente local; medir requeriría autorización runtime.
TEMPORALITY    n/a    HOST_SCOPE    n/a
```

### 25 · ¿Qué sabemos de UDEV?

```
ROUTING        D12 / UDEV / Q3 CONFIGURATION / no aplica
FIRST_READ     NOT_AVAILABLE
SECOND_READ    ninguno
RAW_IF_NEEDED  ninguno
NAV_DEPTH      terminal en 0   FILES_READ 0
EXPECTED_RESULT  PRIMARY_SOURCE=NOT_AVAILABLE
                TERMINAL=NOT_AVAILABLE — respuesta doble:
                  (a) No hay fuente que documente una configuración udev de este sistema.
                      11 menciones, todas como prohibición.
                  (b) Modificar udev está PROHIBIDO (AGENTS.md §Safety,
                      README.md §Reglas de seguridad).
                CONTEXTO ADEMÁS: las reglas udev del disco viejo existen en
                01-AUDITORIA/PATCH-RECOVERY/PATCH-REGISTRY-RECOVERED.md
                  RX550-UD-01  60-kalm-bbr.rules  SHA-256 4c254b05…e7e4009
                  RX550-UD-02  60-kalm-io.rules   SHA-256 dc31580a…32fc6f
                y tienen NEW_DISK_APPLIED=NO. Son PATCH_CLASS=SYSTEM_PATCH, no evidencia.
                Si el usuario necesita saber cómo escribir una regla udev:
                  eso es WEB → resultado marcado EXTERNAL, y NO es estado de este sistema.
                El router NO crea documentación para este hueco.
TEMPORALITY    n/a    HOST_SCOPE    n/a
```

### 26 · ¿Qué sabemos de GRUB?

```
ROUTING        D12 / GRUB / Q2 HARDWARE / no aplica
FIRST_READ     NOT_AVAILABLE
SECOND_READ    ninguno
RAW_IF_NEEDED  ninguno
NAV_DEPTH      terminal en 0   FILES_READ 0
EXPECTED_RESULT  PRIMARY_SOURCE=NOT_AVAILABLE
                TERMINAL=NOT_AVAILABLE
                34 menciones, TODAS como prohibición. Ninguna documenta una
                configuración de GRUB de este sistema.
                CONTEXTO: RX550-GR-01 = NOT_AVAILABLE (sin copia de /etc/default/grub
                ni grubenv, sin evidencia de cmdline editada).
                Web → EXTERNAL, no estado del sistema.
                El router NO crea documentación.
TEMPORALITY    n/a    HOST_SCOPE    n/a
```

### 27 · ¿Qué evidencia contradice el estado actual?

```
ROUTING        D1 / PROJECT_STATUS / Q14 DOCUMENTATION / MIXED / los 3
FIRST_READ     01-AUDITORIA/DOCUMENTATION-CENSUS/DOCUMENTATION-GAPS.md  §1-§2
SECOND_READ    01-AUDITORIA/PATCH-RECOVERY/PATCH-SOURCES.md  §3
               01-AUDITORIA/DOCUMENTARY-RECONCILIATION-2026-09-25.md
RAW_IF_NEEDED  ninguno
NAV_DEPTH      1   FILES_READ 3
EXPECTED_RESULT  STATUS=CONFLICT. Fuentes que contradicen el estado declarado:
                (1) IDENTIDAD DE HOST — 3 identidades, 1444 filas HOST-A,
                    7 documentos CURRENT en HOST-B, solo 2 en HOST-C.
                    Los documentos raíz afirman Nobara 43/Mesa 25.3.2; el host vivo
                    es Nobara 44/Mesa 26.2.3.
                (2) cardN — captura dice card2, host vivo dice card1, y los scripts
                    históricos fijan card1/hwmon2, que no coincide con ninguno.
                    Prueba: 03-EXPERIMENTOS/fase-b-cap-probe-…/driver.sh falla en HOST-C.
                (3) MESA — C2. Cuatro valores; la precedencia declarada cubre dos.
                (4) KERNEL — C3. 7.2.6 vs 7.2.4 vs 6.18.2 vs 7.1.3.
                (5) TESTS C1 — C1. 24/24 vs 37/37 vs 44/44 vs 54+skip.
                (6) H12-4 — C5. implementado vs no ejecutado vs NOT_REPRODUCED.
                (7) BTRFS — C6. CONFLICT, y el host vivo usa ext4.
                (8) mesa-vulkan-drivers — instalado en HOST-B, ausente en HOST-C.
                El router devuelve las 8. No resuelve ninguna.
TEMPORALITY    MIXED    HOST_SCOPE    A + B + C
```

### 28 · ¿Dónde están los artefactos RAW de R4B?

```
ROUTING        D7 / R4B / Q5 RESULT / HISTORICAL / HOST-A
FIRST_READ     03-EXPERIMENTOS/FASE-R4B-GOVERNOR/EXP-F4-A-RESULTADOS-v2.3.md
SECOND_READ    00-INDICE/MASTER-RESEARCH-STATUS.md  §Addenda D6  (§Precedencia)
RAW_IF_NEEDED  EXPERIMENT_DIR = 03-EXPERIMENTOS/FASE-R4B-GOVERNOR
               EXPERIMENT_MD  = EXP-F4-A-RESULTADOS-v2.3.md   ← leído ANTES
               artefactos:
                 results/v23/session1/fase2/metrics.json          (38 358 B)
                 results/v23/session1/fase1/manifest.json         (920 B)
                 results/v23/session1/fase2/order.json            (74 B)
                 results/v23/session2/fase2/omissions.json        (3 B)
                 results/session1-v22/fase2/metrics.json          (37 378 B)
                 results/session1-v22/fase1/manifest.json         (920 B)
                 + 302 artefactos más en el bucket (telemetry, state_initial/final,
                   journal_pres, manifest, run_m0 por bloque)
NAV_DEPTH      1 (al EXPERIMENT_MD) / 2 (al artefacto concreto)
EXPECTED_RESULT  La cadena se respeta: TOPIC → EXPERIMENT_DIR → EXPERIMENT_MD → artefacto.
                S1 EJECUTADA/COMPLETADA: 15/15 bloques con SCLK 1071 MHz sostenido.
                S2 INICIADA y PARADA_D durante el cooldown p2→p3, antes de Phase 2.
                VERDICT=INCONCLUSO / INCONCLUSIVE. Nunca SUPPORTED.
                Phase 2 = DIAGNOSTIC / THERMALLY CONFOUNDED — NOT FOR VERDICT.
                Kalm NO intervino. No se reintenta S2.
                ADVERTENCIA que el router debe incluir: los 13 localizadores /tmp
                canónicos están perdidos/no verificables.
                PRECAUCIÓN: hay 2 juegos de resultados (session1-v22 y v23). El
                canónico es v23 según EXP-F4-A-RESULTADOS-v2.3.md; session1-v22
                es la S1-v2.1 original. El router no los mezcla.
TEMPORALITY    HISTORICAL_OLD_DISK
HOST_SCOPE     A INFERRED
```

---

## Resumen de la segunda simulación

| Bloque | Consultas | `NAV_DEPTH` máx | `FILES_READ` máx | terminals `NOT_AVAILABLE` | `CONFLICT` | `CURRENT_EVIDENCE=NOT_AVAILABLE` |
|---|---:|---:|---:|---:|---:|---:|
| A (originales) | 18 | 1 | 4 | 1 | 4 | 6 |
| B (nuevas) | 10 | 1 | 4 | 3 | 1 | 2 |
| **Total** | **28** | **1** | **4** | **4** | **5** | **8** |

### Verificación de los 10 criterios de éxito

| # | Criterio | Verificación | Resultado |
|---:|---|---|---|
| 1 | Ninguna consulta recorre el repositorio completo | 28/28 con `NAV_DEPTH ≤ 1`; máximo 4 ficheros de 1576 filas | **PASS** |
| 2 | Ninguna presenta HOST-B como HOST-C | Q1, 13, 17, 18, 19, 20 declaran `HOST_B` y `HOST_C` por separado | **PASS** |
| 3 | Ninguna presenta HOST-A como estado actual | Q2, 4, 6, 7, 10, 12, 22 declaran `HISTORICAL_OLD_DISK` / `HOST-A` | **PASS** |
| 4 | Los conflictos permanecen visibles | 5 `CONFLICT` con ambas fuentes (Q5, Q8, Q9, Q19, Q27) | **PASS** |
| 5 | `NOT_AVAILABLE` se mantiene | 4 terminales (Q15, Q24, Q25, Q26) sin escalada inventada | **PASS** |
| 6 | `PRIMARY` antes de `SECONDARY` | 24/28 resuelven el `PRIMARY` primero; 0 al revés | **PASS** |
| 7 | `RAW` solo cuando hace falta | 6 consultas con RAW, las 6 con `EXPERIMENT_MD` leído antes | **PASS** |
| 8 | Los parches permanecen sin aplicar | `SYSTEM_PATCH` × 13, todas `NEW_DISK_APPLIED=NO`; router no aplica ni construye | **PASS** |
| 9 | El censo original permanece idéntico | SHA-256 `a4ccacbc…e8553` sin cambio | **PASS** |
| 10 | `AGENTS.md` contiene reglas, no la base documental | 14 reglas + tabla de 3 hosts; 0 rutas de topic copiadas | **PASS** |

**10/10 PASS.**

### Las 4 consultas que demuestran que no se confunde histórico con actual

| # | Consulta | Si el router no aplicara la regla temporalidad |
|---:|---|---|
| 1 | Estado actual de la RX 550 | «Nobara 43, Mesa 25.3.2, card2» — falsehood completo |
| 20 | Estado en el nuevo disco | Lo mismo, y omitiría que `mesa-vulkan-drivers` no está instalado |
| 22 | Evidencia del disco viejo | Presentaría 1444 filas históricas como si describieran el host vivo |
| 23 | Evidencia del host vivo | Declararía como «actual» lo que solo son 2 documentos |

### Consultas que terminan en 0 lecturas

`Q15` (GRUB) · `Q24` (BACO) · `Q25` (UDEV) · `Q26` (GRUB) — 4 de 28.

Las 4 son los topics sin fuente primaria. Un índice clásico las resolvería devolviendo una
lista de 8–34 menciones, que es exactamente el fallo que el router evita: **sabe que no hay
fuente** y lo dice, en lugar de simular que 34 menciones son 34 fuentes.

---

## Lo que NO se midió

| Métrica | Estado |
|---|---|
| Latencia real de lectura | No medida. Esto es traza de diseño. |
| Tokens consumidos | No medido. |
| Acierto humano de la ruta | No medido. Requiere ejecutar el router con un agente real. |
| `ROUTING-LOG.jsonl` | **No creado** (autorizado aplazar). Sin él, `FILES_READ_PER_QUERY` y `ESCALATION_RATE` no son medibles automáticamente. |
| Comparación con simulación 1 como benchmark | No es un benchmark. La simulación 1 era diseño sin rutas reales; la 2 verifica rutas. La diferencia en `FILES_READ` (2.44 → 2.39) no es una mejora medida, es un cambio de contabilidad. |

**Para medir de verdad:** implementar `ROUTING-LOG.jsonl` en una fase posterior y ejecutar las
28 consultas con el router en producción. Hasta entonces, estas cifras describen **lo que el
router especifica**, no lo que un agente consume.
