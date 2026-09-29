# ROUTING-SIMULATION — 18 consultas resueltas con el router propuesto

**Fecha:** 2026-09-25T23:10Z
**Estado:** simulación de diseño. **El router NO está implementado.** Se traza lo que haría.

## Formato de cada traza

```
QUERY         pregunta literal
ROUTING       DOMAIN / TOPIC / QUESTION_TYPE / TEMPORALITY demanded / HOST_SCOPE demanded
FIRST_READ    1 fichero (o NOT_AVAILABLE)
SECOND_READ   0-3 ficheros, solo si FIRST no alcanza
RAW_IF_NEEDED ruta vía EXPERIMENT_DIR -> EXPERIMENT_MD -> artefacto
EXPECTED_RESULT   lo que el router debe devolver
TEMPORALITY   del documento devuelto
HOST_SCOPE    del documento devuelto
NAV_DEPTH     saltos hasta PRIMARY (objetivo de diseño: 1)
```

**Regla aplicada en las 18:** el router declara `TEMPORALITY` y `HOST_SCOPE` en cada salida, y
nunca presenta `HISTORICAL` como actual.

---

## 1. ¿Cuál es el estado actual de la RX 550?

```
ROUTING        D1 / PROJECT_STATUS / Q1 STATUS / CURRENT demanded / HOST-C demanded
FIRST_READ     README.md                    CURRENT, HOST-B  → declares Nobara 43 / 6.18.2 / Mesa 25.3.2
SECOND_READ    PROBLEM-STATUS-FINAL.md      CURRENT, HOST-B  → 22 filas de problemas
               PATCH-SOURCES.md §3          CURRENT, HOST-C  → tabla de las 3 identidades
RAW_IF_NEEDED  ninguno
EXPECTED_RESULT  STATUS=STALE
                El documento CURRENT de estado describe HOST-B, no HOST-C.
                CURRENT_EVIDENCE=NOT_AVAILABLE para el host vivo.
                Histórico disponible: los 15 documentos CURRENT describen HOST-B.
                Host-C solo está documentado en PATCH-SOURCES.md §3:
                  Nobara 44 · kernel 7.1.3-200.nobara.fc44 · Mesa 26.2.3 · LLVM 22.1.8
                  · libdrm 2.4.134 · firmware 20260810 · RX550 = card1 (era card2 en HOST-B)
                Acción requerida: re-ejecutar tools/validate_rx550_final.py.
TEMPORALITY    CURRENT_NEW_DISK (documento) / pero HOST_B ≠ HOST_C
HOST_SCOPE     B-DECLARED (lo que dice README) vs C-DECLARED (lo que dice PATCH-SOURCES)
NAV_DEPTH      1
```

**Lección:** esta es la pregunta que más se hace y la que más engaña. Sin la regla de
temporalidad, el router devolvería "Nobara 43, Mesa 25.3.2" como estado actual.

---

## 2. ¿Qué sabemos de runtime PM?

```
ROUTING        D5 / RUNTIME_PM / Q1 STATUS / HISTORICAL aceptado / HOST-A
FIRST_READ     01-AUDITORIA/FASE-P0-EXPERIMENTAL-VALIDITY-GATE/
               P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md   §runtime PM
SECOND_READ    04-IMPLEMENTACION/rx550-torneo/README-FASE1.md §Estado persistente
RAW_IF_NEEDED  ninguno (el Gate P0 resume; los valores concretos están en su cuerpo)
EXPECTED_RESULT  Gate P0 observó power/control y runtime_status en el HOST-A.
                NO hay lectura equivalente en HOST-C.
                VERDICT: PM_EFFECT=UNKNOWN (DOCUMENTARY-RECONCILIATION).
                Causalidad DPM/PM = UNRESOLVED (PROBLEM-STATUS-FINAL).
TEMPORALITY    HISTORICAL_OLD_DISK
HOST_SCOPE     A-DECLARED (el Gate cita fc44 / 7.2.6 explícitamente)
NAV_DEPTH      1
```

---

## 3. ¿Qué pasó con DPM?

```
ROUTING        D5 / DPM / Q6 CAUSALITY / HISTORICAL / HOST-A
FIRST_READ     01-AUDITORIA/AUDIT-001/ERRATA.md   §ERRATUM-002  (primero, no AUDIT-001)
SECOND_READ    03-EXPERIMENTOS/fase-a-discriminacion-20260919-114241/RESULTADOS-FASE-A.md
               05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-2-POWERPLAY-MCLK-SMU7.md
RAW_IF_NEEDED  03-EXPERIMENTOS/fase-a-discriminacion-20260919-114241/  (76 artefactos)
EXPECTED_RESULT  power1_input es W_SMU, no un medidor independiente → RESOLVED (etiquetado).
                El régimen E1/E3/E5 → NOT_REPRODUCED en HOST-B/C (PATCH-REGISTRY-FINAL P-002).
                La política DPM de MCLK en SMU7 está documentada upstream (R0-2);
                el trigger local es UNKNOWN.
                NO se puede afirmar causalidad DPM↔rendimiento: UNRESOLVED.
TEMPORALITY    MIXED (ERRATA es HISTORICAL; el veredicto NOT_REPRODUCED es CURRENT)
HOST_SCOPE     A-INFERRED (ERRATA no cita host)
NAV_DEPTH      1
```

**Nota de orden:** el router elige `ERRATA.md` antes que `AUDIT-001.md` porque el censo lo
registra como `SUPERSEDES`. Leer `AUDIT-001.md` primero daría conclusiones que el propio
proyecto corrige.

---

## 4. ¿Qué sabemos del HDD?

```
ROUTING        D9 / HDD / Q11 STORAGE / HISTORICAL / HOST-A
FIRST_READ     01-AUDITORIA/FASE-P0-EXPERIMENTAL-VALIDITY-GATE/P0-...-2026-09-24.md
SECOND_READ    02-ARQUITECTURA/knowledge.md
RAW_IF_NEEDED  ninguno
EXPECTED_RESULT  HOST-A: HDD SAMSUNG HM500JI (i7-4790, 12 GB).
                HDD_FAILURE=NOT_PROVEN · HDD_HEALTHY=UNKNOWN (AGENTS.md).
                HOST-C: raíz /dev/sdb3 ext4. NO es el mismo hardware.
                CURRENT_EVIDENCE=NOT_AVAILABLE para el disco del host vivo.
                SMART y scrub NO ejecutados y NO autorizados.
TEMPORALITY    HISTORICAL_OLD_DISK
HOST_SCOPE     A-INFERRED
NAV_DEPTH      1
```

---

## 5. ¿Qué evidencia existe de Btrfs?

```
ROUTING        D9 / BTRFS / Q5 RESULT / MIXED / HOST-A y HOST-B
FIRST_READ     PROBLEM-STATUS-FINAL.md   (P-012 R-11)
SECOND_READ    03-EXPERIMENTOS/WORKLOAD-SINTETICO/RESEARCH.md  §R-11
               01-AUDITORIA/DOCUMENTARY-RECONCILIATION-2026-09-25.md
RAW_IF_NEEDED  03-EXPERIMENTOS/WORKLOAD-SINTETICO/src/graphics.cpp  (bloque de upload)
EXPECTED_RESULT  STATUS=CONFLICT  (CONFLICT_ID=C6)
                BTRFS=CONFLICT · BTRFS_CAUSE=UNKNOWN · REQUIRED=matched_identity_same_window.
                R-11: imageStore a storage IMAGE producía VM faults deterministas en GFX8/RADV;
                corregido por upload host. Estado: PARTIALLY_RESOLVED.
                OBSOLETE para HOST-C: el host vivo usa ext4, no Btrfs.
                PRECEDENCE_DECLARED=NONE.
TEMPORALITY    MIXED
HOST_SCOPE     A-INFERRED (evidencia) / C-DECLARED (sistema de ficheros actual)
NAV_DEPTH      1
```

---

## 6. ¿Qué pasó con R4B?

```
ROUTING        D7 / R4B / Q5 RESULT / HISTORICAL / HOST-A
FIRST_READ     03-EXPERIMENTOS/FASE-R4B-GOVERNOR/EXP-F4-A-RESULTADOS-v2.3.md
SECOND_READ    00-INDICE/MASTER-RESEARCH-STATUS.md  §Addenda D6  (§Precedencia)
RAW_IF_NEEDED  03-EXPERIMENTOS/FASE-R4B-GOVERNOR/results/v23/   (metrics.json 38 KB)
EXPECTED_RESULT  S1 EJECUTADA/COMPLETADA: 15/15 bloques con SCLK 1071 MHz sostenido.
                S2 INICIADA y PARADA_D durante el cooldown p2→p3, antes de Phase 2.
                VEREDICT=INCONCLUSO / INCONCLUSIVE. Nunca SUPPORTED.
                Phase 2 = DIAGNOSTIC / THERMALLY CONFOUNDED — NOT FOR VERDICT.
                Kalm NO intervino. No se reintenta S2.
                ADVERTENCIA: 13 localizadores /tmp canónicos están perdidos/no verificables.
TEMPORALITY    HISTORICAL_OLD_DISK
HOST_SCOPE     A-INFERRED
NAV_DEPTH      1
```

**Aviso que el router debe incluir:** el `MASTER-RESEARCH-STATUS.md` contiene secciones
anteriores que dicen «NO EJECUTADA» / «S2 no iniciada», que son snapshots y **contradicen** el
estado post-addenda. El router debe leer el addenda, no el cuerpo.

---

## 7. ¿R4C está validado?

```
ROUTING        D7 / R4C / Q21 VALIDITY / HISTORICAL / HOST-A
FIRST_READ     03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/EXP-F1-A-RESULTADOS.md
SECOND_READ    03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/README.md
RAW_IF_NEEDED  03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/results/metrics/*.json
               03-EXPERIMENTOS/FASE-R4C-JITTER-OBSERVABILITY/results/gt/*_gt.json
EXPECTED_RESULT  COMPLETADA. NIVEL A MAE=0.0 px · NIVEL B MAE=3.66e-10 px · 8/8 celdas PASS.
                PERO: ANV sin devices → NO EJECUTADO.
                Y: no se ha re-ejecutado en HOST-C.
                Respuesta a "¿validado?": validado en HOST-A, no re-verificado en HOST-C.
TEMPORALITY    HISTORICAL_OLD_DISK
HOST_SCOPE     A-INFERRED
NAV_DEPTH      1
```

---

## 8. ¿Qué sabemos de Mesa?

```
ROUTING        D6 / MESA / Q1 STATUS / MIXED / HOST-B y HOST-C
FIRST_READ     PATCH-REGISTRY-FINAL.md  §Mesa
SECOND_READ    05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-3-MESA-WORKAROUNDS-POLARIS12.md
               01-AUDITORIA/DOCUMENTARY-RECONCILIATION-2026-09-25.md  §MESA_*
               01-AUDITORIA/PATCH-RECOVERY/PATCH-REGISTRY-RECOVERED.md  RX550-MP-01
RAW_IF_NEEDED  ninguno
EXPECTED_RESULT  STATUS=CONFLICT  (CONFLICT_ID=C2)
                Tres valores en el repositorio:
                  26.2.2  MESA_CANONICAL  (investigación HOST-A)
                  26.2.3  MESA_EXTERNAL   (investigación HOST-A)
                  25.3.2  documentos raíz (HOST-B)
                + host vivo HOST-C: mesa-dri-drivers 26.2.3
                PRECEDENCE_DECLARED=PARTIAL (DOCUMENTARY-RECONCILIATION:225-227)
                Workarounds aplicables: ya upstream (ALREADY_FIXED_UPSTREAM).
                Mesa CUSTOM (EP05) NO reprodujo E5 → NOT_REPRODUCED.
                Commit 583c5d2f (RX550-MP-01): cambio de LOGGING, no funcional.
                  ORIGINAL_APPLIED=UNKNOWN · NEW_DISK_APPLIED=NO.
                mesa-vulkan-drivers NO instalado en HOST-C.
TEMPORALITY    MIXED
HOST_SCOPE     A + B + C (los tres aparecen)
NAV_DEPTH      1
```

---

## 9. ¿Qué pasó con C1?

```
ROUTING        D8 / C1 / Q1 STATUS / MIXED / HOST-A
FIRST_READ     04-IMPLEMENTACION/C1-ISOLATION-DESIGN-v1.0.md
SECOND_READ    04-IMPLEMENTACION/C1-ISOLATION-AUTOMATOR.md
               01-AUDITORIA/DOCUMENTARY-RECONCILIATION-2026-09-25.md  §C1
               01-AUDITORIA/FASE-R5-C1-TECHNICAL-DOCUMENTATION/C1-TECHNICAL-RECORD.md
RAW_IF_NEEDED  01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/*.json  (14 ficheros, hasta 780 KB)
EXPECTED_RESULT  C1=DEFERRED · GO_C1=NOT_AVAILABLE · C1_RUNTIME_VALIDATED=NO · C1_READY=NO.
                DISEÑO: PREPARED_FOR_REVIEW · DESIGN_ONLY=YES · EXECUTION=NONE.
                STATUS=CONFLICT en el recuento de tests (CONFLICT_ID=C1):
                  24/24 = HISTORICAL (R5)
                  37/37 = DERIVED/STALE (diagramas)
                  44/44 = CURRENT_SIDECAR_RECORD  ← PRECEDENCE_DECLARED
                Restore: existe restore_units(), pero PROCESS_RESTORE_NOT_DEFINED
                  para clientes de sesión → un restore de unidades NO es restore verificable.
                La existencia de la implementación NO significa que C1 esté listo.
TEMPORALITY    MIXED
HOST_SCOPE     A-DECLARED (C1-TECHNICAL-RECORD cita 7.2.6)
NAV_DEPTH      1
```

---

## 10. ¿Qué sabemos del ownership?

```
ROUTING        D8 / OWNERSHIP / Q1 STATUS / HISTORICAL / HOST-A
FIRST_READ     01-AUDITORIA/FASE-P0-EXPERIMENTAL-VALIDITY-GATE/P0-...-2026-09-24.md
SECOND_READ    01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/C1-PREFLIGHT-20260925T061932Z-PRIV.md
               AGENTS.md  §Ownership
RAW_IF_NEEDED  01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/C1-PREFLIGHT-20260925T061932Z-PRIV.json  (780 KB)
EXPECTED_RESULT  OWNERSHIP=PARTIAL. NO es FULL.
                Gate P0 = B__CONTAMINATED_REQUIRES_ISOLATION.
                Motivos: FD visibility incompleta, PermissionError, namespaces root no cubiertos,
                clientes activos, writers sin resolver.
                Regla: lsof/fuser parcial NO prueba ownership.
                CURRENT_EVIDENCE=NOT_AVAILABLE para HOST-C.
TEMPORALITY    HISTORICAL_OLD_DISK
HOST_SCOPE     A-DECLARED
NAV_DEPTH      1
```

---

## 11. ¿Qué patches fueron recuperados?

```
ROUTING        D2 / PATCHES / Q8 PATCH / CURRENT / HOST-C
FIRST_READ     01-AUDITORIA/PATCH-RECOVERY/PATCH-REGISTRY-RECOVERED.md
SECOND_READ    01-AUDITORIA/PATCH-RECOVERY/PATCH-RECOVERY-REPORT.md   (informe L1, clasificación A/B/C/D)
RAW_IF_NEEDED  01-AUDITORIA/PATCH-RECOVERY/PATCH-SOURCES.md   (procedencia y hashes)
EXPECTED_RESULT  28 entradas.
                A) PROYECTO  12: PP-01..07, TP-01, C1-01/02, DP-01/02
                   RECOVERED_EXACT=YES · NEW_DISK_APPLIED=YES (en el árbol)
                   PP-05 y PP-07 requieren rebuild; C1-01/02 nunca ejecutados.
                B) SISTEMA   13: SD-01..04, PM-01/02, UD-01/02, SCP-01/02/03, MP-01, UNK-01
                   RECOVERED_EXACT=YES en 12 · PARCIAL en 3 (payload ausente) · NOT_AVAILABLE en 1
                   NEW_DISK_APPLIED=NO en TODOS.
                Sin fuente: 3 slots (KERNEL_PATCH, AMDGPU_PATCH, GRUB_PATCH) = NOT_AVAILABLE.
                CONTENIDO NO INVENTADO: system-autopilot solo tiene 12 hex de hash.
TEMPORALITY    CURRENT_NEW_DISK
HOST_SCOPE     C-DECLARED
NAV_DEPTH      1
```

---

## 12. ¿Qué patches son de sistema?

```
ROUTING        D2 / PATCHES / Q8 PATCH / CURRENT / HOST-C
FIRST_READ     01-AUDITORIA/PATCH-RECOVERY/PATCH-REGISTRY-RECOVERED.md  §B
SECOND_READ    01-AUDITORIA/PATCH-RECOVERY/PATCH-SOURCES.md  §5 (hashes del backup)
RAW_IF_NEEDED  ninguno (los artefactos están en el backup, fuera del repo → HISTORICAL_OTHER_HOST)
EXPECTED_RESULT  PATCH_CLASS=SYSTEM_PATCH. 13 entradas. NEW_DISK_APPLIED=NO para todas.
                Verificado por lectura del sistema el 2026-09-25T22:22Z:
                  0 unidades kalm*  ·  0 system-autopilot*  ·  /opt/kalm ausente
                  /usr/local/bin/kalm* ausente  ·  /opt/mesa-26.2.2-rx550-haswell ausente
                SYSTEM_CHANGE_REQUIRED=SI en las 13.
                Riesgo ALTO: PM-01 (kalm-gpu, escribe power1_cap y DPM),
                  PM-02 (power-sweep), SCP-03 (instalador), SD-01.
                CONCLUSIÓN CONSERVADA: Kalm NO explica el régimen E1/E3/E5.
                NINGÚN parche histórico se presenta como aplicado al host vivo.
TEMPORALITY    CURRENT_NEW_DISK
HOST_SCOPE     C-DECLARED
NAV_DEPTH      1
```

---

## 13. ¿Qué sabemos actualmente del nuevo disco?

```
ROUTING        D3 / HOST_IDENTITY / Q19 HOST_IDENTITY / CURRENT demanded / HOST-C demanded
FIRST_READ     01-AUDITORIA/PATCH-RECOVERY/PATCH-SOURCES.md  §3
SECOND_READ    ninguno necesario: §3 ya tiene la tabla comparativa de las 3 identidades
RAW_IF_NEEDED  01-AUDITORIA/FINAL-VALIDATION/FINAL-VALIDATION-20260925T135831Z.json
               TEMPORALITY=CURRENT_NEW_DISK_STALE_HOST  HOST_SCOPE=B  → STALE, no usar como actual
EXPECTED_RESULT  HOST-C (medido 2026-09-25T22:22Z):
                  OS      Nobara Linux 44 (KDE Plasma)
                  kernel  7.1.3-200.nobara.fc44.x86_64
                  Mesa    mesa-dri-drivers 26.2.3-1.fc44
                  LLVM    22.1.8-4.fc44
                  libdrm  2.4.134-1.fc44
                  firmware linux-firmware-20260810-1.fc44
                  raíz    /dev/sdb3 ext4
                  GPU     Intel card0 / 0000:00:02.0 / i915
                          RX550 card1 / 0000:01:00.0 / amdgpu / renderD129 / hwmon1
                  mesa-vulkan-drivers  NO INSTALADO
                  kalm*   0 unidades   ·  system-autopilot*  0 unidades
                Diferencias con HOST-B: SO, kernel, Mesa, LLVM, libdrm, firmware, cardN.
                PCI 1002:699f y BDF 0000:01:00.0 NO cambiaron.
                NO re-ejecutado: validador, 64/64, 110/110, 54+1.
TEMPORALITY    CURRENT_NEW_DISK
HOST_SCOPE     C-DECLARED
NAV_DEPTH      1
```

---

## 14. ¿Por qué un resultado antiguo no puede considerarse actual?

```
ROUTING        D1 / HISTORY / Q18 HISTORY / MIXED
FIRST_READ     01-AUDITORIA/DOCUMENTATION-CENSUS/DOCUMENTATION-CENSUS.md  §5
SECOND_READ    01-AUDITORIA/PATCH-RECOVERY/PATCH-SOURCES.md  §3
               01-AUDITORIA/FINAL-VALIDATION/FINAL-VALIDATION-20260925T135831Z.md
RAW_IF_NEEDED  ninguno
EXPECTED_RESULT  Tres identidades de host coexisten en la documentación:
                  HOST-A  disco viejo     Nobara 44 · 7.2.4/7.2.6 · Mesa 26.2.2/26.2.3 · card1
                  HOST-B  captura 13:58Z  Nobara 43 · 6.18.2-…fc43 · Mesa 25.3.2 · card2
                  HOST-C  host vivo 22:22Z Nobara 44 · 7.1.3-…fc44 · Mesa 26.2.3 · card1
                1444 de 1576 filas del censo son HISTORICAL_OLD_DISK; solo 16 son CURRENT.
                FINAL-VALIDATION describe HOST-B y se marca CURRENT_NEW_DISK_STALE_HOST.
                Los scripts históricos fijan card1/hwmon2, que no coincide con ningún
                estado observado (vivo: card1/hwmon1).
                PRUEBA PRÁCTICA: 03-EXPERIMENTOS/fase-b-cap-probe-.../driver.sh
                falla en HOST-C por la ruta hwmon2.
                CONCLUSIÓN: un resultado es evidencia de SU host y SU ventana temporal.
                Sin CURRENT_EVIDENCE no hay afirmación de estado actual.
TEMPORALITY    MIXED
HOST_SCOPE     los tres
NAV_DEPTH      1
```

---

## 15. ¿Qué evidencia existe sobre GRUB?

```
ROUTING        D12 / GRUB / Q2 HARDWARE / no aplica
FIRST_READ     NOT_AVAILABLE
SECOND_READ    ninguno — no hay fuente primaria
RAW_IF_NEEDED  ninguno
EXPECTED_RESULT  PRIMARY_SOURCE=NOT_AVAILABLE
                TERMINAL=NOT_AVAILABLE
                34 menciones, TODAS como prohibición ("no modificar GRUB"):
                  README.md §Reglas de seguridad
                  AGENTS.md §Safety and authorization
                  ROLLBACK.md, INSTALL.md, TESTING.md
                No existe ninguna fuente que documente una configuración de GRUB de este sistema.
                CONTEXTO ADEMÁS: RX550-GR-01 = NOT_AVAILABLE (sin copia de /etc/default/grub
                ni evidencia de cmdline editada).
                Si se necesita la respuesta: consultar web → se marcaría EXTERNAL,
                y NO sería estado de este sistema.
                El router NO crea documentación para rellenar el hueco.
TEMPORALITY    NOT-APPLICABLE
HOST_SCOPE     NOT-APPLICABLE
NAV_DEPTH      terminal en 0
```

---

## 16. ¿Por qué PowerPlay sube MCLK y baja SCLK?

```
ROUTING        D5 / MCLK / Q6 CAUSALITY / HISTORICAL / HOST-A
FIRST_READ     05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/R0-2-POWERPLAY-MCLK-SMU7.md
SECOND_READ    03-EXPERIMENTOS/ep06-soak-cap-20260919-205645/RESULTADOS-EP06.md
RAW_IF_NEEDED  03-EXPERIMENTOS/ep06-soak-cap-20260919-205645/  (24 artefactos)
EXPECTED_RESULT  La política de MCLK en SMU7 para bus 128-bit está documentada upstream
                (R0-2). Es un hecho de diseño de PowerPlay, no del proyecto.
                PERO el trigger local es UNKNOWN y el readout de R-4A (3/16/20) NO está
                reconciliado con la tabla upstream (5/16/20).
                EP06: a 25 W el presupuesto se redistribuye; SCLK cae.
                NO afirmar causalidad local: el mecanismo upstream es conocido,
                la atribución en ESTA máquina es UNKNOWN.
                Distinguir: observado (W_SMU 25-31 W, MCLK 1250-1500, SCLK bajo)
                vs interpretado (PowerPlay redistribuye) vs causal (por eso E1/E3/E5) → NO PROBADO.
TEMPORALITY    HISTORICAL_OLD_DISK
HOST_SCOPE     A-INFERRED
NAV_DEPTH      1
```

---

## 17. ¿Está el proyecto listo para publicar en GitHub?

```
ROUTING        D1 / RELEASE / Q16 GITHUB / CURRENT / NOT-APPLICABLE
FIRST_READ     RELEASE-CANDIDATE.md
SECOND_READ    FINAL-RELEASE-REPORT.md
               RELEASE-EXCLUSIONS.md
RAW_IF_NEEDED  ninguno
EXPECTED_RESULT  READY_FOR_GITHUB=NO
                Gates pendientes:
                  - No hay remote configurado. No se inventó URL.
                  - SECURITY_REVIEW=NOT_READY: 66 ficheros de texto con rutas
                    personales absolutas (/home/lucas, /root).
                  - Historia base conserva binarios, logs, dumps y rutas personales.
                  - 3 identidades de host sin resolver.
                  - Problemas abiertos: estabilidad, KWin/Intel, DPM/PM, VFIO, C1, RA24, R-11.
                El router NO puede cambiar ninguno de estos gates.
TEMPORALITY    CURRENT_NEW_DISK
HOST_SCOPE     NOT-APPLICABLE
NAV_DEPTH      1
```

---

## 18. ¿Qué se rompió? (búsqueda de regresión)

```
ROUTING        D1 / REGRESSION / Q7 REGRESSION / CURRENT demanded / HOST-C demanded
FIRST_READ     PROBLEM-STATUS-FINAL.md
SECOND_READ    PATCH-REGISTRY-FINAL.md
RAW_IF_NEEDED  01-AUDITORIA/FINAL-VALIDATION/FINAL-VALIDATION-20260925T135831Z.json  → STALE
EXPECTED_RESULT  P-002  régimen E1/E3/E5        NOT_REPRODUCED
                P-008  RA24 / little-endian     NOT_REPRODUCED  (RA24=0 en el journal del boot)
                P-016  firmware/VBIOS/estados   NOT_REPRODUCED
                P-021  HDD/Btrfs histórico     NOT_REPRODUCED
                P-022  H12 WSI                 NOT_REPRODUCED
                P-012  R-11 VM faults          PARTIALLY_RESOLVED
                Identidad/selectores           PARTIALLY_RESOLVED
                Estabilidad + causalidad DPM/PM UNRESOLVED
                PERO: el journal que respalda los NOT_REPRODUCED es de HOST-B.
                CURRENT_EVIDENCE=NOT_AVAILABLE para HOST-C:
                  no hay boot de HOST-C escaneado en busca de RA24/ring timeout.
TEMPORALITY    CURRENT_NEW_DISK (los veredictos) / HISTORICAL (la evidencia que los sostiene)
HOST_SCOPE     B-INFERRED
NAV_DEPTH      1
```

---

## Resumen de la simulación

| # | Query | `NAV_DEPTH` | Escaló a SECOND | Llegó a RAW | Terminal |
|---:|---|---:|---|---|---|
| 1 | estado actual RX550 | 1 | sí (2) | no | `STALE` + `CURRENT_EVIDENCE=NOT_AVAILABLE` |
| 2 | runtime PM | 1 | sí (1) | no | `UNKNOWN` (PM_EFFECT) |
| 3 | DPM | 1 | sí (2) | no | `RESOLVED` (etiquetado) + `UNRESOLVED` (causalidad) |
| 4 | HDD | 1 | sí (1) | no | `CURRENT_EVIDENCE=NOT_AVAILABLE` |
| 5 | Btrfs | 1 | sí (2) | sí (código) | `CONFLICT` |
| 6 | R4B | 1 | sí (1) | sí | `INCONCLUSIVE` |
| 7 | R4C validado | 1 | sí (1) | sí | `VALIDADO_EN_HOST-A / NO_REVERIFICADO` |
| 8 | Mesa | 1 | sí (3) | no | `CONFLICT` |
| 9 | C1 | 1 | sí (3) | sí (JSON) | `CONFLICT` + `DEFERRED` |
| 10 | ownership | 1 | sí (2) | sí (JSON) | `PARTIAL` |
| 11 | patches recuperados | 1 | sí (1) | no | `COMPLETO_CON_GAPS` |
| 12 | patches de sistema | 1 | sí (1) | no | `NEW_DISK_APPLIED=NO` |
| 13 | nuevo disco | 1 | no | no (JSON es STALE) | `HOST-C` |
| 14 | por qué histórico ≠ actual | 1 | sí (2) | no | `EXPLICADO` |
| 15 | GRUB | **0** | no | no | `NOT_AVAILABLE` |
| 16 | MCLK/SCLK | 1 | sí (1) | sí | `UNKNOWN` (atribución local) |
| 17 | publicar en GitHub | 1 | sí (2) | no | `READY_FOR_GITHUB=NO` |
| 18 | regresión | 1 | sí (1) | no (JSON STALE) | `CURRENT_EVIDENCE=NOT_AVAILABLE` |

### Verificación del objetivo de diseño

| Métrica de diseño | Valor observado en la simulación |
|---|---|
| `NAV_DEPTH` máxima | **1** en las 17 consultas resolubles; **0** en GRUB (terminal) |
| Consultas resueltas en 1 lectura | 3 de 18 (13, 14, 15 → 2 de ellas leen 2) |
| Consultas que leen >3 ficheros | **0** |
| Consultas que barrenan el repositorio | **0** |
| Consultas que leen artefactos RAW sin pasar por su `.md` | **0** |
| Consultas que presentan `HISTORICAL` como actual | **0** |
| Consultas que inventan un valor para un `CONFLICT` | **0** |
| Terminales `NOT_AVAILABLE` correctos | 1 de 4 topics sin primaria (§15) |
| Terminales `CONFLICT` preservados | 4 (queries 5, 8, 9, y la sub-pregunta de 1) |

### Lectura del resultado

**El router funciona en el caso difícil, no en el fácil.** 15 de 18 consultas necesitaron leer un
segundo documento, pero **ninguna pasó de 3 ficheros** y **ninguna/barrió el árbol**. El coste
real está entre 1 y 3 lecturas, no en 1576.

**Las 3 consultas que más engaña son 1, 13 y 18** — las tres piden estado actual y las tres
terminan en `CURRENT_EVIDENCE=NOT_AVAILABLE` o `STALE`. Es exactamente el fallo que el censo
detectó, y el router lo convierte en una salida explícita en lugar de un silencio.

**4 consultas escalan a RAW** (5, 6, 7, 9, 10, 16 = 6 en realidad), y **todas lo hacen por un
`.md` de experimento o auditoría primero**, nunca abriendo el artefacto a ciegas. La cadena
`TOPIC → EXPERIMENT_DIR → EXPERIMENT_MD → artefacto` se respetó en las 6.

**1 consulta termina en 0 lecturas** (GRUB) porque el router sabe que no hay fuente. Es el caso
que un índice clásico no puede resolver: devuelve una lista de 34 menciones como si fueran 34
fuentes.

---

## Nota de honestidad

Esta simulación **no es una medición de rendimiento**. Es una traza de diseño: muestra lo que el
router *propondría* leer, no lo que un agente *leyó*. No hay número de latencia, ni de tokens, ni
de acierto. Las métricas de `DOCUMENTATION-ROUTER-DESIGN.md` §13 definen cómo medirlas; medirlas
requiere implementar el router y registrar un `ROUTING-LOG.jsonl`, que no existe.

Lo que sí es verificable aquí:

- `NAV_DEPTH ≤ 1` en las 18 consultas.
- Las 6 rutas de RAW respetan la cadena `EXPERIMENT_DIR → EXPERIMENT_MD → artefacto`.
- Las 18 respuestas declaran `TEMPORALITY` y `HOST_SCOPE`.
- Las 4 rutas `CONFLICT` devuelven las dos fuentes.
- La ruta `GRUB` no lee ningún fichero.
