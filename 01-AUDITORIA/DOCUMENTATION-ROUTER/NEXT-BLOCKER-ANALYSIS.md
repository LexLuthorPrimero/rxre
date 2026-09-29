# NEXT-BLOCKER-ANALYSIS — Siguiente bloqueo técnico real

**Fecha:** 2026-09-26T00:50Z
**Estado:** análisis. Ninguna acción ejecutada.
**Consultas fuente:** `RT-0021..RT-0024` en `ROUTING-LOG.jsonl`, enrutadas por el router.
**Vocabulario de clasificación:** `OBSERVED` · `SUPPORTED` · `PLAUSIBLE` · `UNKNOWN` ·
`NOT_AVAILABLE` · `CONFLICT`.

---

## 1. Cómo se determinó el bloqueo siguiente

No se eligió por conveniencia. El orden de derivación:

1. **`MASTER-RESEARCH-STATUS.md`** (línea 13) declara el gate vigente:
   `B. CONTAMINATED_REQUIRES_ISOLATION` + `OWNERSHIP=PARTIAL` +
   **«no se autoriza un nuevo A/B hasta aislar clientes y agentes automáticos»**.
2. **`MASTER-PLAN.md` §F** define la secuencia de ejecución. Los pasos 6 (M2 formal 35 W vs
   30 W) y 7 (análisis de bottleneck) **requieren un A/B autorizado**.
3. **`MASTER-PLAN.md` §F.5** pone la condición previa: un workload con `W_SMU ≥27 W @35 W`,
   repetible, `temp <90 °C`, sin reset/hang. El gate que lo valida es el gate de potencia.
4. Por tanto el **primer** bloqueo de la cadena es la condición que impide autorizar el A/B:
   el aislamiento y la prueba de `OWNERSHIP`.

**Conclusión:** el siguiente bloqueo no es «medir la GPU» ni «tocar Mesa». Es
**`OWNERSHIP` no demostrado**, que es la precondición del gate que bloquea el A/B, que es la
precondición del M2, que es el primer experimento de la cadena.

---

## 2. El bloqueo siguiente — ficha

```
BLOCKER_ID=          BLK-01
TOPIC=               OWNERSHIP  (dominio D8 ISOLATION_AND_C1)
CURRENT_STATE=       OWNERSHIP=PARTIAL
CLASSIFICATION=      OBSERVED  (el valor) / SUPPORTED  (que bloquea la cadena)
TEMPORALITY=         HISTORICAL_OLD_DISK
HOST_SCOPE=          A-DECLARED  (7.2.6-201.nobara.fc44, host lex-luthor)
DEPENDENCIES=        BLK-04 (C1 gate design) y BLK-05 (recovery) por debajo;
                     BLK-02 (G1) lo impide cerrar en HOST-C
WHY_BLOCKING=        MASTER-RESEARCH-STATUS l.13: no se autoriza nuevo A/B mientras
                     ownership no sea FULL. MASTER-PLAN §F.6 (M2) y §F.7 (bottleneck)
                     dependen de ese A/B. §F.5 exige antes un workload validado por gate
                     de potencia, lo que exige un A/B limpio.
NEXT_REQUIRED_EVIDENCE=
                     ownership FULL con evidencia completa y atribuible en el host donde
                     se vaya a medir:
                       - inventario de clientes DRM de renderD129 y del card de la RX550
                       - FDs cerrados y verificados, incluidos namespaces de root
                       - sin PermissionError ni visibilidad parcial de /proc
                       - escritores (IRQ, scheduler, read-ahead, governor, PM, storage)
                         atribuidos a un proceso o unidad concreta
                       - ausencia de agentes automaticos escribiendo durante la ventana
                     TODO en una misma ventana temporal, con identidad de host declarada.
RISK=                ALTO si se declara OWNERSHIP=FULL sin evidencia completa: un A/B
                     contaminado produce un veredicto no atribuible, que es exactamente lo
                     que inutilizo la corrida R-4B S2 (PARADA_D) y el Phase 2 clasificado
                     THERMALLY CONFOUNDED.
ACTION_AVAILABLE=    NO sin autorizacion runtime. NO requiere sudo para el diseno;
                     la recoleccion de FDs de root SI requiere privilegio y esta prohibida
                     en esta etapa.
```

### Por qué no se elige otro

| Candidato | Por qué no es el siguiente |
|---|---|
| M2 35 W vs 30 W | Es el primer experimento ejecutable, pero **depende** del A/B que `OWNERSHIP` bloquea. No se puede ordenar antes. |
| Estabilidad DPM/PM `UNRESOLVED` | Es un problema abierto, no una precondición de la cadena. Se atacaría *después* de tener un entorno donde medir. |
| Mesa CUSTOM | `OBSOLETE` como hipótesis de causa (EP05 no reprodujo E5). Cerrado, no bloquea. |
| Kalm / `system-autopilot` | En HOST-C hay **0 unidades** (`SERVICE_ABSENT`). El agente que contaminaba HOST-A **no existe aquí**. Bloqueo de HOST-A, no de HOST-C. |
| VFIO `UNRESOLVED` | Requiere H81 sin VT-d utilizable y compositor dependiente de la RX550. Es un callejón sin salida con la evidencia actual, no el camino principal. |
| Publicación GitHub | `READY_FOR_GITHUB=NO` por `SECURITY_REVIEW` y falta de remoto. Es bloqueo de release, no técnico, y no depende de la GPU. |
| R-11 | `PARTIALLY_RESOLVED` con workaround en el workload. No bloquea la cadena. |

---

## 3. Los 4 candidatos, uno a uno

### BLK-01 — `OWNERSHIP=PARTIAL`  ← **SIGUIENTE BLOQUEO**

| Campo | Valor | Clase |
|---|---|---|
| `TOPIC` | `OWNERSHIP` (D8) | `OBSERVED` |
| `CURRENT_STATE` | `OWNERSHIP=PARTIAL` | `OBSERVED` |
| `EVIDENCE` | `P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md` §ownership; `C1-PREFLIGHT-20260925T061932Z-PRIV.md`/`.json` (780 KB); `AGENTS.md` §Ownership | `OBSERVED` |
| `TEMPORALITY` | `HISTORICAL_OLD_DISK` | `OBSERVED` |
| `HOST_SCOPE` | `A-DECLARED` (`7.2.6-201.nobara.fc44`) | `OBSERVED` |
| `DEPENDENCIES` | `BLK-02` (evidencia HOST-C), `BLK-04` (gate design), `BLK-05` (recovery) | `SUPPORTED` |
| `WHY_BLOCKING` | cita textual de `MASTER-RESEARCH-STATUS.md:13` | `SUPPORTED` |
| `NEXT_REQUIRED_EVIDENCE` | ver ficha §2 | `SUPPORTED` |
| `RISK` | ver ficha §2 | `SUPPORTED` |
| `ACTION_AVAILABLE` | `NO` sin autorización runtime | `OBSERVED` |

**Lo que la evidencia dice literalmente:** el gate no es `A. CLEAN_ENOUGH_FOR_EXPERIMENT`; se
observaron clientes DRM de usuario sobre la RX550 **y** controladores automáticos que escribieron
realmente sobre CPU/IRQ/storage/procesos. No es un veredicto de que un resultado histórico sea
falso: es una condición de validez.

**Lo que NO se puede afirmar:** que `OWNERSHIP` siga siendo `PARTIAL` en HOST-C. No hay
lectura de ownership en HOST-C. `UNKNOWN`.

### BLK-02 — `G1`: evidencia HOST-C insuficiente

| Campo | Valor | Clase |
|---|---|---|
| `TOPIC` | `HOST_IDENTITY` (D3) | `OBSERVED` |
| `CURRENT_STATE` | 2 documentos con `HOST_SCOPE=HOST-C` | `OBSERVED` |
| `EVIDENCE` | `PATCH-SOURCES.md` §3; `PATCH-REGISTRY-RECOVERED.md` | `OBSERVED` |
| `TEMPORALITY` | `CURRENT_NEW_DISK` | `OBSERVED` |
| `HOST_SCOPE` | `C-DECLARED` | `OBSERVED` |
| `DEPENDENCIES` | ninguna (es raíz) | `OBSERVED` |
| `WHY_BLOCKING` | todo `NOT_REPRODUCED` y `PARTIALLY_RESOLVED` se apoya en evidencia HOST-B o HOST-A; sin HOST-C no se puede afirmar estado actual | `SUPPORTED` |
| `NEXT_REQUIRED_EVIDENCE` | re-ejecutar `tools/validate_rx550_final.py` (read-only) y las 3 suites estáticas sobre HOST-C | `SUPPORTED` |
| `RISK` | declarar `CURRENT` sin re-verificar = exactamente el fallo que el router previene | `SUPPORTED` |
| `ACTION_AVAILABLE` | **SÍ**, y es de solo lectura | `OBSERVED` |

**Cubre / no cubre la evidencia HOST-C:**

| Cubre | No cubre |
|---|---|
| SO, kernel, Mesa, LLVM, libdrm, firmware, `cardN`, PCI/BDF, raíz | Que Mesa/radeonsi funcione |
| Ausencia: `kalm*` 0, `system-autopilot*` 0 | Cualquier lectura de DPM / runtime PM |
| Ausencia: `mesa-vulkan-drivers` no instalado | Journal de HOST-C (RA24, ring timeout) |
| Ausencia: `/opt/mesa-26.2.2-rx550-haswell` | Ownership en HOST-C |
| — | Re-ejecución de 64/64, 110/110, 54+1 |

### BLK-03 — `C1=DEFERRED`

| Campo | Valor | Clase |
|---|---|---|
| `TOPIC` | `C1` (D8) | `OBSERVED` |
| `CURRENT_STATE` | `ISOLATION_DESIGN=PREPARED_FOR_REVIEW`, `Ejecución=NONE`, `C1_RUNTIME_VALIDATED=NO` | `OBSERVED` |
| `EVIDENCE` | `C1-ISOLATION-DESIGN-v1.0.md`; `CONFLICT_SOURCE` C1 en `DOCUMENTARY-RECONCILIATION-2026-09-25.md` | `OBSERVED` |
| `TEMPORALITY` | `MIXED` | `OBSERVED` |
| `HOST_SCOPE` | `UNKNOWN-INFERRED` | `OBSERVED` |
| `DEPENDENCIES` | `BLK-01` (ownership), `BLK-05` (recovery), `BLK-02` | `SUPPORTED` |
| `WHY_BLOCKING` | C1 no es el siguiente bloqueo: es la *herramienta* que produciría la evidencia de ownership. Depende, no bloquea la cadena | `SUPPORTED` |
| `NEXT_REQUIRED_EVIDENCE` | para C1 en sí: autorización runtime separada + `OWNERSHIP=FULL` + guard estable + restore verificado | `SUPPORTED` |
| `RISK` | ejecutar C1 sin restore validado: `ABORT_RESTORE` deja el sistema en estado indeterminado | `SUPPORTED` |
| `ACTION_AVAILABLE` | `NO` | `OBSERVED` |

**Conflicto de recuento de tests, preservado:** `24/24=HISTORICAL` · `37/37=DERIVED/STALE` ·
`44/44=CURRENT_SIDECAR_RECORD` · `44/44_REEXECUTED_THIS_AUDIT=NO`. `CONFLICT`. No resuelto.

### BLK-04 — Recovery no validada

| Campo | Valor | Clase |
|---|---|---|
| `TOPIC` | `RECOVERY` (D8) | `OBSERVED` |
| `CURRENT_STATE` | `PREVIOUS_RECOVERY=FAIL`, `RECOVERY=UNKNOWN`, `RECOVERY_PRESENT=PARTIAL`, `RECOVERY_ACCESSIBLE=UNKNOWN`, `RECOVERY_INDEPENDENT=SUPPORTED_FOR_RESCUE_EMERGENCY_BY_UNIT_SEMANTICS; NOT_RUNTIME_VERIFIED` | `OBSERVED` |
| `EVIDENCE` | `C1-RECOVERY-INDEPENDENCE-VALIDATION-20260925T063810Z.md` (HOST-A, 2026-09-25T06:38Z, `READ_ONLY_RECOVERY_VALIDATION`) | `OBSERVED` |
| `TEMPORALITY` | `HISTORICAL_OLD_DISK` | `OBSERVED` |
| `HOST_SCOPE` | `A-DECLARED` | `OBSERVED` |
| `DEPENDENCIES` | `BLK-02` (¿existe recovery en HOST-C?) | `SUPPORTED` |
| `WHY_BLOCKING` | regla de `AGENTS.md`: nunca iniciar aislamiento sin vía de recuperación independiente documentada | `SUPPORTED` |
| `NEXT_REQUIRED_EVIDENCE` | TTY/getty usable en HOST-C, con lectura read-only que lo demuestre; la validación de independencia es `NOT_RUNTIME_VERIFIED` | `SUPPORTED` |
| `RISK` | `ALTO`: `PREVIOUS_RECOVERY=FAIL` es el peor valor observado | `OBSERVED` |
| `ACTION_AVAILABLE` | `NO`. No ejecutar C1 ni pruebas de reboot | `OBSERVED` |

---

## 4. Separación de bloqueos (no mezclados)

### A. Documentales

| ID | Bloqueo | Clase | Host |
|---|---|---|---|
| `DOC-01` | 3 identidades de host sin reconciliar; `HOST_SCOPE=UNKNOWN` en 1406/1576 filas | `OBSERVED` | todos |
| `DOC-02` | 140 referencias rotas, 4 familias, sin reparar | `OBSERVED` | todos |
| `DOC-03` | 6 conflictos abiertos (C1–C6) | `CONFLICT` | todos |
| `DOC-04` | `MASTER-PLAN` §F.3 desfasado: dice que el workload sintético está «sin código» cuando ya existe implementado | `OBSERVED` | n/a |
| `DOC-05` | 5 mecanismos de navegación previos sin reconciliar (`DRAFT/CONFLICT`) | `OBSERVED` | n/a |
| `DOC-06` | 4 topics sin primaria (`BACO`, `FIREFOX`, `GRUB`, `UDEV`) | `NOT_AVAILABLE` | n/a |
| `DOC-07` | 59 documentos huérfanos sin referencia entrante | `OBSERVED` | n/a |

**Ninguno de estos bloquea la cadena técnica.** El router es la excepción: ya cerrado como
baseline.

### B. Ownership / isolation

| ID | Bloqueo | Clase | Host |
|---|---|---|---|
| **BLK-01** | **`OWNERSHIP=PARTIAL` → no se autoriza A/B** | `SUPPORTED` | `A-DECLARED` |
| `B-02` | P0 = `B. CONTAMINATED_REQUIRES_ISOLATION` | `OBSERVED` | `A-DECLARED` |
| `B-03` | Agentes automáticos escribiendo CPU/IRQ/storage | `OBSERVED` | `A-DECLARED` |
| `B-04` | Ownership en HOST-C: sin medir | `NOT_AVAILABLE` | `C` |

### C. Recuperación

| ID | Bloqueo | Clase | Host |
|---|---|---|---|
| **BLK-04** | `PREVIOUS_RECOVERY=FAIL`, `RECOVERY_ACCESSIBLE=UNKNOWN` | `OBSERVED` | `A-DECLARED` |
| `C-02` | `RECOVERY_INDEPENDENT` solo por semántica de unidad, `NOT_RUNTIME_VERIFIED` | `OBSERVED` | `A-DECLARED` |
| `C-03` | TTY/getty en HOST-C: sin verificar | `NOT_AVAILABLE` | `C` |

### D. C1

| ID | Bloqueo | Clase | Host |
|---|---|---|---|
| **BLK-03** | `C1=DEFERRED`, `EXECUTION=NONE` | `OBSERVED` | `UNKNOWN` |
| `D-02` | Recuento de tests `24/24` vs `37/37` vs `44/44` | `CONFLICT` | — |
| `D-03` | `PROCESS_RESTORE_NOT_DEFINED` para clientes de sesión | `OBSERVED` | — |
| `D-04` | Gaps de implementación del diseño: `IMPLEMENTATION_GAPS_CLOSED=0` | `OBSERVED` | — |

### E. GPU / RX550

| ID | Bloqueo | Clase | Host |
|---|---|---|---|
| `E-01` | `RX550-01` identidad por `cardN` `PARTIALLY_RESOLVED` | `OBSERVED` | `B-DECLARED` |
| `E-02` | `RX550-09` KWin/Wayland usa RX550 con display en Intel `UNRESOLVED` | `OBSERVED` | `B-DECLARED` |
| `E-03` | `RX550-13` ring timeout/reset `PARTIALLY_RESOLVED`, sin prueba de carga | `OBSERVED` | `B-DECLARED` |
| `E-04` | Estabilidad y causalidad DPM/PM `UNRESOLVED` | `OBSERVED` | `B-DECLARED` |
| `E-05` | `RX550-19` VFIO `UNRESOLVED`: H81 sin VT-d utilizable, compositor depende de RX550 | `OBSERVED` | `A-DECLARED` |
| `E-06` | Registro RA24 en HOST-C | `NOT_AVAILABLE` | `C` |
| `E-07` | DPM / runtime PM leídos en HOST-C | `NOT_AVAILABLE` | `C` |

### F. Mesa / RADV

| ID | Bloqueo | Clase | Host |
|---|---|---|---|
| `F-01` | `MESA_PROVENANCE=CONFLICT` (26.2.2 vs 26.2.3) | `CONFLICT` | `A`/`B`/`C` |
| `F-02` | Documentación raíz dice Mesa 25.3.2; host vivo 26.2.3 | `CONFLICT` | `B` vs `C` |
| **F-03** | **`mesa-vulkan-drivers` `PACKAGE_ABSENT` → `DRIVER_OPERATIONAL` para RADV = `NOT_AVAILABLE`** | `OBSERVED` | `C-DECLARED` |
| `F-04` | `RX550-17` migración Mesa/LLVM/libdrm `PARTIALLY_RESOLVED` | `OBSERVED` | `B-DECLARED` |
| `F-05` | Workarounds GFX8 `ALREADY_FIXED_UPSTREAM` — cerrado, no bloquea | `OBSERVED` | — |
| `F-06` | `RX550-11` `MESA_VK_DEVICE_SELECT` no confiable `PARTIALLY_RESOLVED`; corrección aplicada pero no re-verificada en HOST-C | `OBSERVED` | `B` |

### G. Kalm

| ID | Bloqueo | Clase | Host |
|---|---|---|---|
| `G-01` | En HOST-A: `kalm.service` PID 4055, `kalm-lite` PID 4054, `kalm-gpu` | `OBSERVED` | `A-INFERRED` |
| **`G-02`** | **En HOST-C: `SERVICE_ABSENT`. 0 unidades `kalm*` y 0 `system-autopilot*`** | `OBSERVED` | `C-DECLARED` |
| `G-03` | `RX550-UNK-01` contenido de `system-autopilot` `NOT_AVAILABLE` (solo 12 hex de hash) | `NOT_AVAILABLE` | `A` |
| `G-04` | Payloads de `kalmd.py`, `kalm-cpu-apply.sh`, `kalm-lite.py` ausentes del backup | `NOT_AVAILABLE` | `A` |
| `G-05` | Parches de sistema Kalm: 13 con `NEW_DISK_APPLIED=NO` | `OBSERVED` | `C` |

**`G-02` es el hallazgo más relevante de esta sección:** el agente que contaminaba HOST-A
**no existe en el host actual**. El bloqueo B-03 («agentes automáticos escribiendo») es un
bloqueo **de HOST-A**. Si HOST-C genuinely no tiene esos servicios, la contaminación que
justificó el Gate P0 podría no aplicar — pero eso es `PLAUSIBLE`, no `OBSERVED`: nadie ha
medido ownership ni journal en HOST-C.

### H. Almacenamiento

| ID | Bloqueo | Clase | Host |
|---|---|---|---|
| `H-01` | `BTRFS=CONFLICT` y el host vivo es **ext4**, no Btrfs | `CONFLICT` | `A` vs `C` |
| `H-02` | `HDD_FAILURE=NOT_PROVEN`, `HDD_HEALTHY=UNKNOWN` | `OBSERVED` | `A-DECLARED` |
| `H-03` | SMART no ejecutado (frontera read-only/sin root) | `OBSERVED` | `A-DECLARED` |
| `H-04` | HOST-A: `sda` Samsung HM500JI 465.8 GiB. HOST-C: `/dev/sdb3` — hardware distinto | `OBSERVED` | `A` vs `C` |
| `H-05` | Salud del almacenamiento de HOST-C | `NOT_AVAILABLE` | `C` |
| `H-06` | `RX550-21` HDD/Btrfs histórico `NOT_REPRODUCED` | `OBSERVED` | `B` |

### I. Reproducibilidad

| ID | Bloqueo | Clase | Host |
|---|---|---|---|
| `I-01` | 13 localizadores `/tmp` canónicos de R-4B perdidos, no reconstruidos | `OBSERVED` | `A` |
| `I-02` | 2 power-sweep marcados `ESTADO-HISTORICO-NO-UTILIZABLE` | `OBSERVED` | `A` |
| `I-03` | `resultados_etapa2.json` malformado, excluido del índice | `OBSERVED` | `A` |
| `I-04` | Suites 64/64, 110/110, 54+1 no re-ejecutadas en HOST-C | `OBSERVED` | `B` |
| `I-05` | `RX550-12` R-11 no repetido en la instalación actual | `OBSERVED` | `B` |
| `I-06` | Sin protocolo de reproducibilidad para experimentos (solo para pruebas estáticas) | `NOT_AVAILABLE` | n/a |

### J. Seguridad / release

| ID | Bloqueo | Clase |
|---|---|---|
| `J-01` | `SECURITY_REVIEW=NOT_READY`: 66 ficheros de texto con rutas personales absolutas | `OBSERVED` |
| `J-02` | `REMOTE=NOT_AVAILABLE`; no se inventó URL | `OBSERVED` |
| `J-03` | `COMMIT`/`TAG` = `NOT_AVAILABLE`; `PUSH=NOT_AUTHORIZED_OR_NOT_READY` | `OBSERVED` |
| `J-04` | Historia base conserva binarios, logs, dumps y rutas personales; política pública sin decidir | `OBSERVED` |
| `J-05` | `READY_FOR_GITHUB=NO` | `OBSERVED` |

---

## 5. Grafo de dependencias

```
BLK-02 (G1, evidencia HOST-C)          ← raíz. Sin ella nada se afirma sobre HOST-C.
    │
    ├──► BLK-01 (OWNERSHIP) ──┐
    │                          │
BLK-05 (RECOVERY) ─────────────┤   ambos son precondición de C1
    │                          │
    └──────────────────────────┴──► BLK-03 (C1)  [herramienta, no es el camino]
                                        │
                                        ▼
                              A/B autorizado (MASTER-PLAN §F)
                                        │
                                        ▼
                              gate de potencia §F.5 (W_SMU ≥27 W, repetible)
                                        │
                                        ▼
                              §F.6 M2 formal 35 W vs 30 W
                                        │
                                        ▼
                              §F.7 análisis de bottleneck
```

**Observación de secuencia:** `BLK-02` es la única raíz del grafo y **también** la única con
`ACTION_AVAILABLE=YES` sin autorización runtime. `BLK-01` y `BLK-05` requieren autorización.
Ejecutar `BLK-01` antes de `BLK-02` produciría ownership de un host cuyo estado no se ha
re-verificado, que es el mismo error dePEAT que la documentación ya registra.

---

## 6. Lo que esta etapa NO hace

| No hizo | Razón |
|---|---|
| Medir ownership en HOST-C | Requiere autorización runtime |
| Re-ejecutar el validador o las suites | Fase siguiente, requiere autorización de fase |
| Probar TTY/recovery en HOST-C | Prohibido en esta etapa |
| Ejecutar C1 | Prohibido |
| Aplicar los 13 parches de sistema | Prohibido; y `NEW_DISK_APPLIED=NO` |
| Resolver los 6 conflictos | Fuera de alcance |
| Reparar las 140 referencias | Fuera de alcance |
| Cerrar `G1` | Falta evidencia HOST-C |
| Declarar `OWNERSHIP` en HOST-C | No medido: `NOT_AVAILABLE` |
| Afirmar que HOST-C está «limpio» | `PLAUSIBLE`, no `OBSERVED` |
