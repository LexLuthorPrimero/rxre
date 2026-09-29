# DECISIONES D1–D10 — Auditoría documental post-reparación

**Fecha**: 2026-09-23 · **Raíz**: `/home/lucas/Escritorio/RX550-INVESTIGACION/`
**Informe de origen**: `01-AUDITORIA/POST-REPARACION-DOCUMENTAL-AUDIT.md` (aceptado como checkpoint)
**Modo**: READ-ONLY. Este es el **único** fichero creado. No se modificó ningún otro, no se movió nada, no se hizo commit.
**Natureza de este documento**: NO decide nada. Presenta las 10 decisiones con su evidencia, sus opciones y sus consecuencias, y espera al usuario.

---

## 0. Corrección previa (afecta a D5)

Al verificar D5 con datos propios se encontró que **la premisa de la auditoría post-reparación era errónea**. No se corrigió el informe anterior (queda congelado como checkpoint); se documenta aquí la corrección:

| Afirmación en `POST-REPARACION-DOCUMENTAL-AUDIT.md` (sección I) | Realidad verificada |
|---|---|
| «3 ficheros `M` con hash **idéntico** al manifiesto pre-movimiento» | **FALSO.** Los 3 tienen hash **distinto** del manifiesto. El error fue del script de re-mapeo, que no incluía `04-IMPLEMENTACION/<basename>` como destino candidato y por eso los clasificó como “sin destino”, no como “idénticos” |
| «Inconsistencia de historial que requiere decisión» | **No hay inconsistencia.** Correspondencia perfecta: 33 ficheros “changed” + 3 no mapeados = **36 = exactamente los 36 `M` de git**. Los mismos 36 difieren del estado pre-movimiento |

Consecuencia: **D5 se reenumbrella** (ver D5). El resto de la auditoría se mantiene.

---

## ESTADO DE DECISIONES (reconciliación documental 2026-09-24; Addenda D6 original 2026-09-23)

| Decisión | Estado | Acuerdo registrado |
|---|---|---|
| **D1** `00-INDICE/README.md` | ✅ **RECONCILIADO DOCUMENTALMENTE** | Es el índice de navegación actual; las referencias históricas se marcan como tales |
| **D2** `R2-GLOBAL-DOCUMENTATION-MAP.md` | ✅ **RECONCILIADO DOCUMENTALMENTE** | Mapa de navegación `DRAFT/CONFLICT`; no es fuente de verdad experimental |
| **D3** Estado de benchmarks | ✅ **RECONCILIADO DOCUMENTALMENTE** | `BENCHMARK-INVENTORY.md` separa descarga/instalación externa/ejecución/elegibilidad; no autoriza nuevas corridas |
| **D4** `MASTER-PLAN.md:781` | ✅ **RECONCILIADO DOCUMENTALMENTE** | La frase `experiments/` es snapshot/prosa histórica; las rutas activas se expresan con prefijos actuales |
| **D5** Hashes contradictorios | ✅ **CERRADA — FALSO POSITIVO** | Los 3 ficheros tienen correspondencia 1:1 con `04-IMPLEMENTACION/` y forman parte de los 36 modificados. **No modificar contenido ni hashes** |
| **D6** Estado canónico R-4B | ✅ **ADOPTADA** | S1 v2.3 EJECUTADA/COMPLETADA · S2 v2.3 INICIADA/PARADA D · veredicto global **INCONCLUSO/INCONCLUSIVE** · la causa de la parada no está verificada · **no borrar historia**, **no convertir S2 en resultado válido**, **no elevar a SUPPORTED** |
| **D7** Evidencia `/tmp` | ✅ **ADOPTADA** | Los 13 PERDIDOS quedan **PERDIDOS / NO VERIFICABLES** · **no reconstruir** · **no inferir** de nombres/referencias · `gpa311/` = PARCIALMENTE RECUPERABLE solo por el extracto R0-1 · la telemetría principal en disco permanece como evidencia **independiente** |
| **D8** Set H | ✅ **ADOPTADA** | 10/10 SHA256 intactos · **PROTEGIDO** · no modificar scripts, hashes, contenido ni mtimes · el NO-GO operativo se documenta como **estado de ejecución/dependencias**, no como pérdida de integridad |
| **D9** Localizadores `/tmp` | ✅ **ADOPTADA** | Marcar **HISTÓRICOS / NO VERIFICABLES** cuando el artefacto no exista · mantener explícita cualquier recuperación parcial · **no sustituir rutas históricas por rutas inventadas** |
| **Power sweeps** | ✅ **ADOPTADO** | `132309` conservar = evidencia histórica **NO UTILIZABLE** para conclusiones RX550 (contiene datos Intel HD 4600) · `140527` conservar = evidencia RX550 **HISTÓRICA pero NO UTILIZABLE CUANTITATIVAMENTE** (columnas desalineadas) · no borrar ninguno de los 388 ficheros · no reconstruir columnas sin evidencia primaria |
| **D10** Commit | ✅ **ADOPTADA** | **No commit todavía** · primero cerrar decisiones documentales y ejecutar reparaciones autorizadas · al final **un commit de reparación documental coherente**, salvo razón técnica para separarlo |

### Reconciliación documental de D1–D4 (2026-09-24)

Estas cuatro decisiones quedan harmonizadas solo en el ámbito documental y no autorizan
acciones externas. Las opciones, consecuencias y referencias históricas de las Partes 1–4
se conservan como registro; la fila de estado superior es la precedencia vigente.

- D1: `00-INDICE/README.md` es un índice de navegación actual; no es estado experimental.
- D2: `R2-GLOBAL-DOCUMENTATION-MAP.md` es una vista `DRAFT/CONFLICT`; los resultados y
  estados canónicos tienen precedencia.
- D3: `BENCHMARK-INVENTORY.md` es la fuente de verdad del inventario documental, con cuatro
  ejes separados; `README.md` y `SOURCES-AND-EXECUTION.md` tienen alcance de descargas.
- D4: la mención `experiments/` de `MASTER-PLAN.md` es histórica/prosa; no se interpreta
  como localizador actual.

---

# PARTE 1 — LAS 10 DECISIONES

> **Nota de precedencia:** los problemas, opciones y la etiqueta «mapa vivo» que aparecen
> abajo son el análisis histórico previo a la reconciliación. La decisión vigente está
> en la tabla de estado superior: el mapa es `DRAFT/CONFLICT`, no una vista `LIVE`;
> no reabre ninguna decisión ni autoriza edición.

## D1 — Papel de `00-INDICE/README.md`: índice vivo o snapshot histórico

**Problema concreto.** `00-INDICE/README.md` (34 líneas, mtime 20-sep) lista 5 experimentos con el prefijo `experiments/` (`:25-29`) y sitúa `RX550_BUILD_SPECIFICATION.txt` en `00-INDICE` (`:8`). Todos esos destinos se movieron: los 5 experimentos están ahora en `03-EXPERIMENTOS/` y el fichero de build en `02-ARQUITECTURA/`. El documento no declara si describe el árbol actual o el anterior.

**Archivos afectados.** `00-INDICE/README.md` (5 referencias, líneas 25-29) · el propio `README.md` raíz, que lo presenta como índice · referencias C1–C5 de la tabla de la auditoría.

**Evidencia disponible.**
- `README.md:5-15` declara la estructura nueva como oficial.
- `REGISTRO-DE-MOVIMIENTOS.md:3-5,16-24` documenta el movimiento como ejecutado y verificado (1.651 ficheros, 1.645/1.645 del manifiesto).
- `POST-REORGANIZATION-REFERENCE-REPAIR-PLAN.md:87-105,137-148` ya lo marcaba como «decisión pendiente» sobre el papel de este README.
- Los 5 destinos correctos existen verificados (`test -e`).

**Opciones posibles.**
1. **Reparar como índice vivo**: sustituir las 5 rutas por `03-EXPERIMENTOS/…` y `RX550_BUILD_SPECIFICATION.txt` → `02-ARQUITECTURA/…`.
2. **Congelar como snapshot**: añadir una cabecera que declare “refleja el árbol anterior a la reorganización del 23-sep” y no tocar las rutas.
3. **Eliminarlo y dejar solo el README raíz** como índice único.
4. **Reescribirlo** como índice real de `00-INDICE/` (los 20 documentos que contiene).

**Consecuencias.**
- Opción 1: coherencia inmediata; se pierde la huella del árbol previo, pero esa huella ya está en `REGISTRO-DE-MOVIMIENTOS.md` y en el manifiesto.
- Opción 2: preserva historia; un lector nuevo puede seguir rutas rotas creyendo que son actuales.
- Opción 3: reduce ambigüedad, pero borra un documento y rompe cualquier referencia a él.
- Opción 4: mayor trabajo y riesgo de introducir rutas nuevas sin verificar.

**Opción que recomienda la documentación existente.** Ninguna explícitamente para el README; sí hay precedente equivalente: la auditoría de referencias trata los documentos de_bitácora como históricos y exige declarar su rol. La decisión de fondo (índice vivo vs snapshot) estaba explícitamente diferida.

**Qué debe decidir el usuario.** Si `00-INDICE/README.md` es el índice de `00-INDICE/` (y entonces reescribirlo), un snapshot histórico (y entonces marcarlo), o un duplicado innecesario del README raíz (y entonces retirarlo).

**Riesgo de elegir mal.** Bajo si se marca como histórico; **medio** si se repara sin decidir el rol, porque se consolidan dos índices con el mismo propósito y se perpetuate la ambigüedad en futuras auditorías.

---

## D2 — U2: `00-INDICE/R2-GLOBAL-DOCUMENTATION-MAP.md`

**Problema concreto.** El mapa se autodeclara “mapa de navegación para un investigador nuevo” (`:10-15`) pero `:23` declara como raíz `/home/lucas/Escritorio/RX550_Iterative_Research/`, `:44` describe una capa `experiments/`, y hay **18 coincidencias** de rutas antiguas en total (líneas 23, 31, 40, 44, 130, 134, 138-144, 166, 172-175). De esas, `RX550_Iterative_Research/projects/` y `RX550_Iterative_Research/rx550-torneo/` **no existen**; `experiments/` existe pero está **vacío** (0 ficheros).

**Archivos afectados.** `00-INDICE/R2-GLOBAL-DOCUMENTATION-MAP.md` (18 referencias) · consumidores del mapa: `PROJECT-DOCUMENTATION-STATUS.md:9` y `MASTER-PLAN.md:781` / `MASTER-RESEARCH-STATUS.md:175`.

**Evidencia disponible.** Verificación directa de las 18 coincidencias y de la existencia/inexistencia de los 3 subdirectorios antiguos. `POST-REORGANIZATION-REFERENCE-REPAIR-RESULT.md:109-116,132-140` registra U2 como pendiente; `:171` la lista como bloqueada hasta autorización.

**Opciones posibles.**
1. **Actualizar como mapa vivo**: reescribir las 18 referencias a la estructura de 6 directorios.
2. **Congelar como snapshot**: cabecera de estado + las rutas se conservan como registro de cómo se veía el repo el 22-sep.
3. **Dividir**: un mapa vivo nuevo + el actual como histórico.

**Consecuencias.**
- Opción 1: el mapa cumple su función declarada; es el cambio más grande de los 10 (afecta a un documento de 175 líneas con 18 referencias).
- Opción 2: se pierde la utilidad de navegación, que es su propósito explícito.
- Opción 3: máxima claridad, añade un documento nuevo.

**Opción que recomienda la documentación existente.** Ninguna. U2 está explícitamente diferida y su resolución condiciona a D1 (ambos son índices).

**Qué debe decidir el usuario.** Si el mapa se actualiza, se congela o se divide; y si su consumidor `PROJECT-DOCUMENTATION-STATUS.md:9` debe apuntar al mapa vivo o al congelado.

**Riesgo de elegir mal.** **Alto** si se actualiza sin revisar: el mapa es el índice de navegación del proyecto y un error suyo puede inducir a editar rutas equivocadas en 10+ documentos.

---

## D3 — U4: `05-FUENTES-EXTERNAS/RX550_Benchmarks/`

**Problema concreto.** Tres documentos del mismo directorio se contradicen sobre el estado de los benchmarks, y dos referencias están rotas.

| Fichero | Afirmación |
|---|---|
| `RX550_Benchmarks/README.md:3,7-24` | el directorio contiene descargas sin instalar; solo GravityMark descargado |
| `docs/SOURCES-AND-EXECUTION.md:5-10,23-27` | solo GravityMark terminó; **Superposition cancelado** |
| `BENCHMARK-INVENTORY.md:62-72,184-197` | **4 instaladores instalados** y ejecuciones registradas |
| `BENCHMARK-INVENTORY.md:195,197` | rutas rotas `experiments/EXPLORATORIO-GravityMark/runs/…` |
| `MASTER-PLAN.md:82,104,109-120`, `MASTER-RESEARCH-STATUS.md:50,388` | presentan 4 instalaciones |

**Estado real en disco (verificado).** Solo hay `official-downloads/gravitymark/GravityMark_1.89.run` y `cancelled-downloads/Unigine_Superposition-1.1.run.partial`. Las instalaciones bajo `/home/lucas/Escritorio/berchmark/instalados/` **existen** pero están fuera del repo (la auditoría central NO pudo certificarlas; la auditoría de referencias confirma que la ruta existe).

**Archivos afectados.** `BENCHMARK-INVENTORY.md` (C7, C8, M6, M7) · `RX550_Benchmarks/README.md` · `docs/SOURCES-AND-EXECUTION.md` · `MASTER-PLAN.md:82,104` · `MASTER-RESEARCH-STATUS.md:50,388` · `PROJECT-DOCUMENTATION-STATUS.md:61` (instalación-only).

**Evidencia disponible.** Contenido real de `official-downloads/` y `cancelled-downloads/`; existencia de la ruta externa; evidencia de ejecución real en `03-EXPERIMENTOS/EXPLORATORIO-GravityMark/runs/RESULTADO-Superposition.md` y `RESULTADO.md`; `docs/DOWNLOAD-MANIFEST.sha256`.

**Opciones posibles.**
1. **Reconciliar**: `BENCHMARK-INVENTORY` pasa a “descargado / instalado / ejecutado / elegible” con 4 estados separados, reflejando lo verificado.
2. **Congelar los 3** como snapshots y crear un estado vigente nuevo.
3. **Reparar solo C7-C8** y dejar las contradicciones semánticas para el índice maestro.

**Consecuencias.**
- Opción 1: elimina la contradicción y permite decidir M2 con base fiable; requiere verificar el estado de las 4 instalaciones externas.
- Opción 2: preserva historia pero el benchmark queda sin fuente de verdad.
- Opción 3: deja la contradicción viva (afecta a la decisión de M2).

**Opción que recomienda la documentación existente.** `SOURCES-AND-EXECUTION.md` es el documento de estado de ejecución, lo que sugiere que sea la fuente canónica; `BENCHMARK-INVENTORY` parece un inventario de disponibilidad. Ninguno lo declara.

**Qué debe decidir el usuario.** Cuál de los 3 documentos es la fuente de verdad del estado de benchmarks, y si se certifican las instalaciones externas.

**Riesgo de elegir mal.** **Medio**: una estado de benchmarks erróneo puede llevar a planning sobre Superposition (cuyo installer está en `cancelled-downloads/`) o a descartarlo por licencia cuando quizá sí es elegible.

---

## D4 — U5: `MASTER-PLAN.md:781`

**Problema concreto.** La línea 781 contiene la descripción conceptual `experiments/ A–D/R-0/R-1/sintético`, con el prefijo de la raíz antigua. Está clasificada como **U5** y fue **excluida explícitamente** del Set I (no es una de las 15 referencias reparadas).

**Archivos afectados.** `00-INDICE/MASTER-PLAN.md:781` (una línea) y su consumidor `R2-GLOBAL-DOCUMENTATION-MAP.md:28-29`.

**Evidencia disponible.** `POST-REORGANIZATION-REFERENCE-REPAIR-RESULT.md:109-116,132-140` la marca como excluido; `MASTER-PLAN.md:781` es una frase de prosa, no un locator (`test -e` no aplica); los destinos reales (`03-EXPERIMENTOS/…`) existen.

**Opciones posibles.**
1. **Corregir el prefijo** a `03-EXPERIMENTOS/`.
2. **Dejarla como está** por decisión previa (es una descripción, no un enlace).
3. **Reescribir la frase** para que no use ruta alguna.

**Consecuencias.** Opción 1: coherencia total pero cierra una decisión que ya se había abierto. Opción 2: inconsistencia menorKnown. Opción 3: elimina la ambigüedad sin tocar la semántica.

**Opción que recomienda la documentación existente.** La reparación pasada la **excluyó deliberadamente**; mantener la exclusión es la opción con menos sorpresa, pero deja una coincidencia de raíz antigua en un documento maestro.

**Qué debe decidir el usuario.** Si cerrar U5 ahora o mantenerla excluida.

**Riesgo de elegir mal.** **Bajo**: es una línea de prosa; el riesgo es de coherencia, no de operación.

---

## D5 — [REEMBROLLADA] Estado de los 36 ficheros modificados: no hay contradicción de hashes

**Problema concreto.** La auditoría anteriorProposed una “inconsistencia” en 3 ficheros. La verificación propia demuestra que **la premisa era falsa**: sus hashes difieren del manifiesto pre-movimiento, igual que los otros 33. La correspondencia es **1:1 y perfecta**: los mismos **36** ficheros que git marca como modificados son los que difieren del estado pre-movimiento.

**Archivos implicados (los tres erróneamente señalados).** `04-IMPLEMENTACION/FASE-E-REAL-GAME-BASELINE-DESIGN.md` (actual `089290bd…` vs manifiesto `40de3e2c…`) · `FASE-F-GEOMETRY-INVESTIGATION-DESIGN.md` (`9b0c0263…` vs `0640f5f5…`) · `SYNTHETIC-WORKLOAD-DESIGN.md` (`04c21154…` vs `12992954…`).

**Evidencia disponible.** Hashes actuales, entradas del manifiesto, blobs `HEAD` vs working, y `git diff` por fichero: los tres difieren del manifiesto **y** de HEAD.

**Opciones posibles.**
1. **Dar por resuelta la falsa alarma** y no abrir más investigación (recomendado: la evidencia es concluyente).
2. **Auditar el contenido de los 3** para saber qué cambió exactamente (posible referencia reparada o edición de contenido).
3. **Investigar el orden temporal** manifest→commit→cambios para documentar la secuencia.

**Consecuencias.** Opción 1: cierra el ítem con la evidencia actual. Opción 2: trabajo extra con valor documental (saber qué se cambió tras la reorganización). Opción 3: solo trazabilidad.

**Opción que recomienda la documentación existente.** No aplica: la auditoría se basó en un error de script.

**Qué debe decidir el usuario.** Si acepta la corrección y cierra D5, o si quiere el contenido-diff de los 3 (opción 2).

**Riesgo de elegir mal.** **Muy bajo**. La única consecuencia de no cerrar es arrastrar un error propio en la documentación de auditoría.

---

## D6 — Estado canónico de R-4B

**Problema concreto.** Dos documentos dan estados incompatibles para el mismo experimento.

| Fuente | Afirmación |
|---|---|
| `MASTER-RESEARCH-STATUS.md:3,278,310,332,387,406-424` | S1 **v2.2** finalizada; Phase 2 `DIAGNOSTIC/THERMALly CONFOUNDED`; **propuesta v2.3 preparada (NO EJECUTADA)**; **S2 NO iniciada**; sin veredicto global. Referencia `EXP-F4-A-PROTOCOL-v2.3-PROPUESTA.md` y `results/session1-v22/` |
| `EXP-F4-A-RESULTADOS-v2.3.md:3-5,11-32,152-166` | S1-v2.3 **completa**; S2-v2.3 **`PARADA D`** (rc=9); muestra formal incompleta; R1–R6 no evaluables; R7 `INCONCLUSIVE/NOT FOR VERDICT`; **veredicto global `INCONCLUSO`**. Evidencia en `results/v23/` |

Comprobación: `results/session1-v22/` y `results/v23/` **existen ambos**; `results/session2/` **no existe**; `verdict.json` **no existe** (coherente con INCONCLUSO).

**Archivos afectados.** `MASTER-RESEARCH-STATUS.md` (estado) · `EXP-F4-A-PROTOCOL-v2.3.md` (snapshot pre-run, ya marcado no vigente) · `EXP-F4-A-RESULTADOS-v2.3.md` (canónico) · documentos heredados de protocolo/pre-run (se conservan como `SNAPSHOT HISTÓRICO`).

**Evidencia disponible.** `results/v23/session1/` completo y `results/v23/session2/` parcial · `results/logs/v23.done` (`PARADA`, rc=9) · `manifest.json:3-5` (`version 2.1`, `T_ms=9.153`) frente a protocolo `T=9.168 ms` (Δ 0,16%, explicado en `EXP-F4-A-RESULTADOS-v2.3.md:130-135`).

**Opciones posibles.**
1. **Addenda fechada** en `MASTER-RESEARCH-STATUS.md` que registre el estado v2.3 conservando el texto previo como historial.
2. **Reescritura** de la sección R-4B al estado v2.3.
3. **Congelar** el maestro como snapshot y crear un `ESTADO-VIVO.md` nuevo.
4. **No tocar** el maestro y marcar `EXP-F4-A-RESULTADOS-v2.3.md` como canónico en un documento aparte.

**Consecuencias.**
- Opción 1: el maestro deja de ser fuente de error sin perder historia. **Es la que la propia documentación sugiere** (`POST-REORGANIZATION-REFERENCE-REPAIR-RESULT.md:109-116` recomienda “añadir addenda fechada”).
- Opción 2: más limpia, pero pierde el rastro de por qué se cambió.
- Opción 3: añade un documento maestro más (la ambigüedad ya es alta).
- Opción 4: el error de estado persiste en el índice principal.

**Opción que recomienda la documentación existente.** **Opción 1 (addenda fechada)**: es la práctica ya usada en la auditoría de reorganización.

**Qué debe decidir el usuario.** Qué documento es la fuente canónica del estado R-4B y si se promueve `INCONCLUSO` (nunca `SUPPORTED` con n=1..3).

**Riesgo de elegir mal.** **Alto**: un índice que diga “no ejecutado” cuando la corrida existe (y viceversa) es exactamente el tipo de contradicción que destruye la confianza en todo el proyecto. Y promover a `SUPPORTED` sería sobreinterpretar n≤3.

---

## D7 — Evidencia de R-4B perdida en `/tmp/opencode/`

**Problema concreto.** La PARADA D de S2-v2.3 coincided con una firma de carga externa
y un logger independiente citado en `/tmp/opencode/`; la atribución/causa raíz no está
verificada. **Los 13 localizadores están PERDIDOS** (verificado uno por uno).

| Elemento | Estado | Citado en |
|---|---|---|
| `/tmp/opencode/micro12/vkmark30-telemetry.csv` | **PERDIDO** | `EXP-F4-A-RESULTADOS-v2.3.md:18,165` |
| `/tmp/opencode/marcar_ventanas.py` | **PERDIDO** | `EXP-F4-A-RESULTADOS-v2.3.md:166` |
| `/tmp/opencode/audit_p2_thermal.py` | **PERDIDO** | `EXP-F4-A-PROTOCOL-v2.3-PROPUESTA.md:323` |
| `/tmp/opencode/audit_power_win.py` | **PERDIDO** | `EXP-F4-A-PROTOCOL-v2.3-PROPUESTA.md:324` |
| `/tmp/opencode/analyze_minitest_ramp.py` | **PERDIDO** | `RESULTADOS-MINITEST-7.3-B.md:163` |
| `/tmp/opencode/run_variant.sh` | **PERDIDO** | ES-01 (workload sintético) |
| `/tmp/opencode/rt_idle.csv` | **PERDIDO** | `FASE-D-ETAPA-3-PRECHECK.md:32,239` |
| `/tmp/opencode/ep05_base.txt` | **PERDIDO** | `ep05…/scripts/{ab-e5,ab-e5-vk,env-check}.sh:3` |
| `/tmp/opencode/ep06_base.txt` | **PERDIDO** | `soak-final.sh:3`, `soak-probe.sh:3` (**Set H**) |
| `/tmp/opencode/fase_b_base.txt` | **PERDIDO** | `fase-b…/driver.sh:3` |
| `/tmp/opencode/fakehome/.drirc` | **PERDIDO** | R-11 / workload |
| `/tmp/opencode/f4a-smoke/`, `/tmp/opencode/f4a-s/` | **PERDIDO** | `PRE-FLIGHT-CALIBRACION-EXP-F4-A.md:15,27` |
| `/tmp/opencode/gpa311/` | **PERDIDO** | fuente upstream GFX8 (sí sobrevive `R0-1-GFX8-EVENT-ID-REFERENCE.txt`) |

**Archivos afectados.** `EXP-F4-A-RESULTADOS-v2.3.md:18,165-166` (la explicación de la PARADA D) · `EXP-F4-A-PROTOCOL-v2.3-PROPUESTA.md:323-324` · `RESULTADOS-MINITEST-7.3-B.md:163` · `FASE-D-ETAPA-3-PRECHECK.md:32,239` · 5 scripts de `ep05`/`fase-b` · 2 scripts de Set H.

**Evidencia disponible.** Lo que **sí** es reproducible en disco: `results/v23/session1/` (completo), `results/v23/session2/` (parcial), `results/logs/v23.done`, `manifest.json`, `frozen.sha256`, telemetría de `results/logs/`. Lo perdido son **analizadores y el logger externo**, no la telemetría principal.

**Opciones posibles.**
1. **No reconstruir** y rebajar la afirmación a “causa probable no verificable en el estado actual del repo”.
2. **Reconstruir** los analizadores desde los documentos (no recomendado: no se debe reconstruir evidencia).
3. **Reetiquetar** los resultados v2.3 como “INCONCLUSO por muestra incompleta” sin causa atribuida, y dejar la PARADA D como observación.
4. **Buscar** en backups si existen (ninguno identificado).

**Consecuencias.** Opción 1: honesta y verificable. Opción 2: prohibida por el encargo (“NO reconstruir evidencia perdida”). Opción 3: más fuerte que la evidencia permite. Opción 4: sin candidatos conocidos.

**Opción que recomienda la documentación existente.** La propia `EXP-F4-A-RESULTADOS-v2.3.md:137-155` ya declara muestra incompleta y sin veredicto;rebajar la causalidad es coherente con `AUDIT-001/ERRATA.md` (uso prudente del sensor SMU).

**Qué debe decidir el usuario.** Si se acepta la pérdida y se reetiqueta la causa, o si se deja el texto actual asumiendo que solo es “probable”.

**Riesgo de elegir mal.** **Alto** si se mantiene la atribución fuerte sin evidencia: una causalidad no verificable puede underlies una decisión de implementación. **Medio** si se reetiqueta sin indicarlo: se pierde el registro de lo que seAFFIRMÓ en su momento.

---

## D8 — Reparación estática de Set H (10 scripts protegidos)

**Problema concreto.** Set H (10 scripts) contiene 8 rutas absolutas operativas a `RX550_Iterative_Research/experiments/…` (raíz que existe pero está **vacía**), más dependencias ausentes. La reparación pasada lo excluyó deliberadamente y lo dejó **intacto**.

**Integridad del archivo (verificada, 10/10).**

| ID | SHA256 | MD5 | mtime |
|---|---|---|---|
| H1 telemetria_gravitymark | `20102c31eae590e6…` | `14824e5e6b895840deecaa6e11608f13` | 20-sep |
| H2 analizar_etapa2 | `b76c531e8a9b129b…` | `754fa90c2b266021d9b8e8a813e20d55` | 21-sep |
| H3 auditoria_reconstruccion | `5574b6769c76aa02…` | `631748027927ab3f002d9dbc7a475e2e` | 21-sep |
| H4 orquestador | `8026df2212e79c0…` | `b512cef35e802cd0ae8ef60debf44786` | 21-sep |
| H5 telemetria_gov | `922c429b9a78e006…` | `e1e9dd0b3d74f401ff5a7532ca338ef3` | 22-sep |
| H6 run_thermal_replicate | `8933187601426f1d…` | `7ed392af2452bfb8ef99e7cb7e2c898d` | 22-sep |
| H7 run_all_jitter | `d0e94ef55cc60ae6…` | `d6c89367a96a4309f1a3ff5a694ec7ef` | 22-sep |
| H8 run_superposition | `0ed5f34ff67fcdcf…` | `1ed55f9e866df679a7c0072127c5f912` | 21-sep |
| H9 soak-final | `8d666328d6e956b1…` | `8265d324489bb4a95e2889951f951922` | 19-sep |
| H10 soak-probe | `4d6a12b8bb2f38d7…` | `9c4401921d0589eb5a2611120771d366` | 19-sep |

**Posibilidad de ejecución actual: NO-GO.** Dependencias/runtime ausentes: raíz antigua vacía · `/tmp/opencode/ep06_base.txt` PERDIDO · `/dev/dri/renderD129` ausente · `$H` sin declarar en `soak-probe.sh:10` · `soak-final.sh:8,13` **escribe** `power1_cap` vía `sudo tee` (no es read-only).

**Opciones posibles.**
1. **No tocar** (recomendado): Set H es evidencia histórica; se registra NO-GO.
2. **Reparación estática solo de rutas** (cambiar `RX550_Iterative_Research/experiments/` por la ruta actual), sin ejecutar nada.
3. **Congelar** los 10 con una cabecera de “histórico, no reejecutable”.

**Consecuencias.** Opción 1: preserva la reproducibilidad histórica; los scripts no se pueden usar. Opción 2: los hace ejecutables en principio, pero **rompe la línea histórica** y podría dar una falsa sensación de ejecutabilidad (siguen faltando `ep06_base.txt` y `renderD129`). Opción 3: intermediario, añade marca de agua.

**Opción que recomienda la documentación existente.** **Opción 1**: `POST-REORGANIZATION-REFERENCE-REPAIR-RESULT.md:142-165` deja constancia de que Set H no se modificó, y la auditoría de readiness recomienda NO-GO.

**Qué debe decidir el usuario.** Si Set H se congela como evidencia, se repara estáticamente o se deja intacto. En cualquier caso: **no ejecutar**.

**Riesgo de elegir mal.** **Alto** si se reparan y luego alguien los ejecuta: `soak-final.sh` escribe en sysfs (`power1_cap`) y podría modificar la GPU, contra la frontera de seguridad del proyecto.

---

## D9 — Los 13 localizadores `/tmp/opencode/` fuera de Set H

**Problema concreto.** 11 localizadores `/tmp` (de los 13, dos son Set H) están en scripts y documentos que **no** están protegidos. Cuestan dos decisiones: reubicarlos al repo, o marcarlos históricos.

**Archivos afectados.** `ep05…/scripts/{ab-e5,ab-e5-vk,env-check}.sh:3` · `fase-b…/driver.sh:3` · `FASE-D-ETAPA-3-PRECHECK.md:32,239` · `RESULTADOS-MINITEST-7.3-B.md:163` · `EXP-F4-A-PROTOCOL-v2.3-PROPUESTA.md:323-324` · `EXP-F4-A-RESULTADOS-v2.3.md:18,165-166` · (`run_variant.sh`, `fakehome/.drirc` citados en ES-01/R-11).

**Evidencia disponible.** Los 11 están **PERDIDOS**; el backup de `/tmp/opencode` del 23-sep 15:03 ya no está. Los destinos equivalentes en el repo (telemetría de FASE D, runs del workload) **sí** existen.

**Opciones posibles.**
1. **Reemplazar por la ruta actual equivalente** en los scripts (si el destino canónico está claro).
2. **Marcar como histórico** («el fichero base ya no existe; el experimento se ejecutó con él en su día»).
3. **Reconstruir** el fichero base (no recomendado: implicaría inventar el estado de una corrida).
4. **Eliminar** la referencia (perder trazabilidad).

**Consecuencias.** Opción 1: los scripts quedan apuntando al sitio correcto pero **siguen sin poder ejecutarse** sin el fichero base. Opción 2: honesto. Opción 3: fabricar evidencia. Opción 4: pierde el vínculo con la corrida.

**Opción que recomienda la documentación existente.** Para **documentos**: la auditoría de referencias exige declarar explícitamente lo histórico. Para **scripts**: no se ejecutan, luego reescribir su ruta no aporta y sí altera la línea histórica → marcar como históricos.

**Qué debe decidir el usuario.** Qué localizadores se reubican y cuáles se marcan históricos; y si los scripts de `ep05`/`fase-b` entran en la categoría protegida (como Set H) o se pueden tocar.

**Riesgo de elegir mal.** **Medio**: si se reescriben rutas de scripts sin fuente, se crea laillusion de re-ejecutabilidad.

---

## D10 — Commit diferido de los 36 M + 10 ??

**Problema concreto.** Hay 36 ficheros modificados y 10 untracked sin commit desde el commit `c614678` (23-sep 06:40). Incluyen la reorganización, Set A–G, Set I, Set H (intacto), las 4 auditorías de background, el registro de reparación y este informe de decisiones.

**Antes de poder commitear una “reparación” falta resolver:**
1. D1–D9 (cada cambio de contenido debe decidirse antes de commitearlo).
2. Decidir si el commit incluye **Set H intacto** (10 scripts con rutas antiguas) — si se commitean así, el commit documenta scripts no reejecutables; si se excluyen, el árbol queda inconsistente con el manifiesto.
3. Verificar que los 3 documentos de `REORGANIZACION-MANIFEST.sha256` (pre-movimiento) sigan siendo coherentes.
4. Decidir el mensaje y si se hace 1 commit o varios (reorganización / reparación / auditoría).

**Opciones posibles.**
1. **Un commit** con todo (reorganización + reparaciones + auditorías).
2. **Varios commits** temáticos (movimiento / Set A–G / Set I / auditorías / informe).
3. **Ninguno** hasta cerrar D1–D10.

**Consecuencias.** Opción 1: simple, pero mezclaipeline. Opción 2: trazable, más trabajo. Opción 3: es el estado actual.

**Opción que recomienda la documentación existente.** La reorganización ya se commiteó como `c614678` (“verificación global de integridad”). Las reparaciones A–G y Set I están documentadas en sus propios informes; un commit por set parece el patrón existente.

**Qué debe decidir el usuario.** Cuántos commits, qué incluye cada uno, y si Set H entra intacto.

**Riesgo de elegir mal.** **Medio**: un commit único puede hacer irreversibles decisiones que aún no se han tomado (p. ej. congelar Set H).

---

# PARTE 2 — TABLA DE CATEGORÍAS

| CATEGORÍA | ARCHIVO | ESTADO ACTUAL | ACCIÓN PROPUESTA | ¿REQUIERE DECISIÓN HUMANA? |
|---|---|---|---|---|
| **A — reparación mecánica segura** | `00-INDICE/README.md` | índice de navegación actual; rutas experimentales corregidas | mantener como índice, no estado experimental | **No** (D1 reconciliado) |
| A | `R2-HISTORICAL-EXPERIMENT-INVENTORY.md:54` | `/home/lucas/RX550_Modo_Torneo_Backup…` (falta `/Escritorio`) | insertar `/Escritorio` | No |
| A | `BENCHMARK-INVENTORY.md:195,197` (C7, C8) | `experiments/EXPLORATORIO-GravityMark/runs/…` | prefijo `03-EXPERIMENTOS/` | No (mecánico) |
| A | `FASE-G-MEMORY-VRAM-GTT-DESIGN.md:7` (C9) | `projects/GHOST/…` sin `04-IMPLEMENTACION/` | anteponer `04-IMPLEMENTACION/` | No |
| A | `R4C/PRIOR-ART.md:99` (C10) | `projects/JITTER-REPROJECTION/PRIOR-ART.md` | anteponer `04-IMPLEMENTACION/` | No |
| B | `MASTER-RESEARCH-STATUS.md` | Addenda D6 vigente; snapshot pre-D6 conservado como histórico | mantener precedencia D6 | **No** (D6 reconciliado) |
| B | `MASTER-PLAN.md` | `PROJECT-ROADMAP.md` inexistente; nota de reconciliación y benchmarks por ejes | mantener roadmap canónico en `IMPLEMENTATION-ROADMAP.md` | **No** (D3/D4 reconciliados) |
| B | `PROJECT-DOCUMENTATION-STATUS.md` | índice con nota de alcance;Benchmark/Map scope separated | mantener como índice de ecosistema | **No** |
| B | `R2-GLOBAL-DOCUMENTATION-MAP.md` | mapa `DRAFT/CONFLICT`; navegación y conflictos marcados | mantener como vista, no fuente de estado | **No** (D2 reconciliado) |
| B | `README.md` raíz | dice que la reorganización está pendiente | reescribir narrativa | **Sí** (D1) |
| B | `R1-5-DOCUMENTATION-STATUS.md:60-63` | aliases R0 que no existen | reescribir a los 4 nombres actuales | No (mecánico, pero verificar intención) |
| B | `FINAL-RESEARCH-STATUS.md` | snapshot histórico; terminología `draw real` etiquetada como W_SMU en la addenda | no usar como estado vivo | **No** (terminología) |
| B | `POLARIS12-MAP.md` | capacidad/negociación/UNKNOWN separados; ACEs y CU reservation no confirmados | mantener como mapa con `UNKNOWN` | **No** (P1 reconciliado) |
| B | `EXP-F4-A-RESULTADOS-v2.3.md` | t90 por condición y manifest v2.3 trazable | corrección incorporada | **No** (D6) |
| B | `RESULTADOS-MINITEST-7.3-B.md:100-115` | `t90≈221 s` marcado como extrapolación; valores reales 171,9/134,8 | corrección incorporada | **No** |
| B | `R-14-SUPERPOSITION-DISSECTION.md:94-105,121-132` | correlación direccional, no causalidad | corrección incorporada | **No** |
| B | `RESULTADOS-FASE-A.md`, `RESULTADOS-FASE-B.md`, `EXP-F3-A-BANDWIDTH-REAL.md` | faltan objetivo/metodología/evidencia/estado | completar campos | No |
| B | 11 cabeceras `04-IMPLEMENTACION/projects/*/README.md` + 4 `*-DESIGN.md` | prefijo `projects/…` | anteponer `04-IMPLEMENTACION/` | No (12 cabeceras, cosmético) |
| **C — documento nuevo** | `00-INDICE/FUENTES-FALTANTES.md` | ya existe; inventario de UNKNOWN | mantener y reauditar | **No** |
| C | `04-IMPLEMENTACION/IMPLEMENTATION-ROADMAP.md` | existe; F/G/K sin ciclo de diseño | mantener documental | **No** |
| C | `04-IMPLEMENTACION/IMPLEMENTATION-SAFETY-RULES.md` | existe; no autoriza acciones | mantener como frontera | **No** |
| C | informe de `rx550-power-sweep-20260918-132309` | sin `.md`; datos **Intel** | redactar nota “no utilizable (Intel)” | **Sí** (D-list) |
| C | informe de `rx550-power-sweep-20260918-140527` | sin `.md`; CSV desalineado | redactar nota “no utilizable (CSV desalineado)” | **No** (nota existente) |
| C | nota de estado de `03-EXPERIMENTOS/results/` | solo `session1.log` con BUILD FAILED | nota “build fallido, no es experimento” | No |
| C | sección de índice para auditorías de background | 4 auditorías no indexadas | añadir a `MASTER-RESEARCH-STATUS.md` | No |
| C | `00-INDICE/ESTADOS-ES-EN.md` | vocabulario ampliado y нормаizado | mantener como taxonomía | **No** |
| **D — contradicción documental** | `MASTER-RESEARCH-STATUS.md` ↔ `EXP-F4-A-RESULTADOS-v2.3.md` | addenda D6 ya vigente; snapshot pre-D6 identificado | mantener precedencia D6 | **No** |
| D | `EXP-F4-A-PROTOCOL-v2.3.md` | snapshot pre-ejecución; threshold uniforme 50 °C y autorización histórica | mantener como histórico no normativo | **No** |
| D | `EXP-F4-A-RESULTADOS.md` (heredado) | marcado histórico; no usar `TBD` como estado actual | mantener como snapshot | **No** |
| D | `README.md` raíz ↔ `REGISTRO-DE-MOVIMIENTOS.md` | reconciliado; ambas capas distinguibles | mantener alcance | **No** (D1) |
| D | `BENCHMARK-INVENTORY` ↔ `README`/`SOURCES-AND-EXECUTION` | cuatro ejes separados | mantener alcance | **No** (D3) |
| D | `POLARIS12-MAP` ↔ R-4A | Gen3×8 vs Gen2×4; 501 vs 96–112 GB/s | separar capas | **Sí** |
| D | `FASE-G` ↔ R-4A | 501 GB/s vs 96–112 GB/s | marcar FASE-G como teórico | No |
| D | `POST-REORGANIZATION-REFERENCES-AUDIT.md:362` vs plan/result | Set H = 9 vs 10 | corregir el conteo a 10 | No |
| D | `manifest.json` (v2.1, T=9.153) vs protocolo (T=9.168) | Δ 0,16% | ya explicado en resultados v2.3 | No |
| **E — evidencia perdida** | `/tmp/opencode/micro12/vkmark30-telemetry.csv` | PERDIDO | no reconstruir; rebajar a “no verificable” | **Sí** (D7) |
| E | `/tmp/opencode/marcar_ventanas.py` | PERDIDO | ídem | **Sí** (D7) |
| E | `/tmp/opencode/audit_p2_thermal.py`, `audit_power_win.py` | PERDIDO | ídem | **Sí** (D7) |
| E | `/tmp/opencode/analyze_minitest_ramp.py` | PERDIDO | ídem | **Sí** (D7) |
| E | `/tmp/opencode/run_variant.sh` | PERDIDO | ídem | **Sí** (D9) |
| E | `/tmp/opencode/rt_idle.csv` | PERDIDO | ídem | **Sí** (D9) |
| E | `/tmp/opencode/{ep05_base,ep06_base,fase_b_base}.txt` | PERDIDO | ídem (ep06_base en Set H) | **Sí** (D9) |
| E | `/tmp/opencode/fakehome/.drirc` | PERDIDO | ídem | **Sí** (D9) |
| E | `/tmp/opencode/f4a-smoke/`, `f4a-s/` | PERDIDO | ídem | **Sí** (D9) |
| E | `/tmp/opencode/gpa311/` | PERDIDO | sobrevive solo `R0-1-…REFERENCE.txt` | No |
| E | `FASE-R4B-GOVERNOR/results/session2/` | NO EXISTE | mark como no aplicable (S2 en v23) | **Sí** (D6) |
| E | `…/v23/session2/fase1/manifest.json`, `fase2/metrics.json` | NO EXISTEN | coherentes con PARADA D | No |
| E | `**/verdict.json` | NO EXISTE | coherente con INCONCLUSO | No |
| E | `GravityMark/runs/200k/{times,stats}_200k.txt` | ausentes | justificado por timeout documentado | No |
| **F — protegido** | 10 scripts Set H | 10/10 SHA256 intactos | **NO TOCAR**; registrar NO-GO | **Sí** (D8) |
| F | `00-INDICE/REORGANIZACION-MANIFEST.sha256` | evidencia de integridad pre-movimiento | NO TOCAR | No |
| F | 6 documentos de auditoría/reparación (`REORGANIZATION-AUDIT`, `POST-REORGANIZATION-*`, `REGISTRO-*`) | bitácora A–G + Set I | NO TOCAR | No |
| F | artefactos CMake/Ninja de 2 harnesses | generados | NO EDITAR (regenerar) | No |
| F | `m1-schedule.json`, `state_*.txt`, `manifest.*`, `audit.json`, logs | evidencia de corridas | NO TOCAR | No |
| F | 2 power sweeps (388 ficheros) | datos no utilizables | **CONSERVAR** como histórico | **Sí** (¿nota o borrar?) |
| F | 50 copias NotebookLM | copia plana, no symlinks | **NO TOCAR / NO CONVERTIR EN SYMLINKS** | No |
| **G — histórico a conservar** | `/home/lucas/Escritorio/RX550_Iterative_Research/` | existe, `experiments/` vacío | conservar (raíz B) | No |
| G | `RX550_Modo_Torneo_Backup_2026-09-19_0836/` | existe | conservar | No |
| G | `EXP-F4-A-RESULTADOS.md` (heredado, con TBD) | anterior a v2.3 | conservar como histórico (con marca) | **Sí** (D6) |
| G | `EXP-F4-A-PROTOCOL-v2.3-PROPUESTA.md` | anterior a v2.3 final | conservar | No |
| G | `FASE-R2-FINAL-REPORT.md`, `R3-MASTER-PLAN-INTEGRATION-PROPOSAL.md` | registran `experiments/` en su momento | conservar | No |

---

# PARTE 3 — LOS 10 PUNTOS EXIGIDOS

## 1. R-4B — documentos que contradicen el estado v2.3

**Afirman que NO se ejecutó (contradicen la existencia de la corrida):**
- `00-INDICE/MASTER-RESEARCH-STATUS.md:3` — “PROPUESTA v2.3 PREPARADA (NO EJECUTADA) … S2 NO iniciada”
- `MASTER-RESEARCH-STATUS.md:278,310,332,387,406-424` — repetido
- `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/EXP-F4-A-PROTOCOL-v2.3.md:3-4` — “ninguna trial ejecutada”
- `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/AUDITORIA-PRE-RUN-v2.3.md:78-95` — dice que `results/v23` no existía
- `03-EXPERIMENTOS/FASE-R4B-GOVERNOR/EXP-F4-A-RESULTADOS.md:11-15,27-40` — heredado, `TBD`, “S2 no inició”
- `PRE-FLIGHT-CALIBRACION-EXP-F4-A.md:15,27` — rutas `/tmp` de preparativos

**Evidencia de S1 (reproducible en disco):** `results/v23/session1/` con `fase1/blocks/…` (15 bloques), `fase2/{gov1,gov2,gov3,dist1,dist2,fixed1-3}` completos, `manifest.json`, `frozen.sha256`, `results/logs/` (40 ficheros). **EXISTE y es verificable.**

**Evidencia de S2 (parcial):** `results/v23/session2/fase1/blocks/…` y `fase2/` incompletos; `results/logs/v23.done` con `PARADA`, rc=9. **EXISTE parcialmente.**

**Veredicto INCONCLUSIVE:** `EXP-F4-A-RESULTADOS-v2.3.md:27-32,69,83,152-155` — R7 `INCONCLUSIVE / NOT FOR VERDICT`; R1–R6 no evaluables; global `INCONCLUSO`. **Coherente** (no hay `verdict.json`).

**Evidencia perdida en `/tmp`:** las 13 rutas de la tabla D7. Afectan a la **explicación de la causa** de la PARADA D, no a la telemetría principal.

**Lo que sigue siendo reproducible/verificable:** toda la telemetría de `results/v23/`, los hashes congelados, el log de PARADA, y la clasificación formal (`INCONCLUSO`). **Lo que no:** la causa atribuida de la PARADA D.

## 2. Evidencia `/tmp` — estado exacto

Clasificación solicitada: **EXISTENTE / PERDIDO / PARCIALMENTE RECUPERABLE / REFERENCIADO PERO NO VERIFICABLE**.

| Elemento | Clasificación | Detalle |
|---|---|---|
| `micro12/vkmark30-telemetry.csv` | **PERDIDO** | citado en 2 sitios; logger externo de la PARADA D |
| `marcar_ventanas.py` | **PERDIDO** | script de análisis de ventanas |
| `audit_p2_thermal.py` | **PERDIDO** | auditoría de cronología térmica |
| `audit_power_win.py` | **PERDIDO** | auditoría de potencia por ventana |
| `analyze_minitest_ramp.py` | **PERDIDO** | análisis del mini-test |
| `run_variant.sh` | **PERDIDO** | runner de ES-01 |
| `rt_idle.csv` | **PERDIDO** | sanity idle de FASE D |
| `ep05_base.txt` | **PERDIDO** | base de EP-05 |
| `ep06_base.txt` | **PERDIDO** | base de EP-06 (**Set H**) |
| `fase_b_base.txt` | **PERDIDO** | base de FASE B |
| `fakehome/.drirc` | **PERDIDO** | config temporal |
| `f4a-smoke/`, `f4a-s/` | **PERDIDO** | directorios de preflight |
| `gpa311/` | **PARCIALMENTE RECUPERABLE** | el árbol fuente no está, pero sobrevive el extracto `R0-1-GFX8-EVENT-ID-REFERENCE.txt` (IDs GFX8) |
| telemetría principal R-4B (`results/v23/`) | **EXISTENTE** | en disco, no en /tmp |
| `verdict.json` | **REFERENCIADO PERO NO VERIFICABLE** | coherente con INCONCLUSO; no se emitió |
| `results/session2/` | **REFERENCIADO PERO NO VERIFICABLE** | citado por el informe heredado; no existe |
| `GravityMark 200k times/stats` | **REFERENCIADO PERO NO VERIFICABLE** | pérdida justificada por timeout documentado |

## 3. Set H — 10 SHA256 confirmados y protegidos

Los 10 SHA256 constan en la tabla de D8. **Confirmados byte a byte**; mtimes 19–22 sep, anteriores a la reorganización. **No se propone ninguna modificación de contenido.**

Separado en tres ejes, como se pide:
- **Integridad del archivo:** ✅ 10/10 coinciden con los documentados en `POST-REORGANIZATION-REFERENCE-REPAIR-RESULT.md:144-155` y con el manifiesto.
- **Posibilidad de ejecución actual:** ❌ NO-GO (raíz antigua vacía, 4 dependencias ausentes, 1 script escribe sysfs).
- **Dependencias/runtime ausentes:** `/home/lucas/Escritorio/RX550_Iterative_Research/experiments/*` (vacío) · `/tmp/opencode/ep06_base.txt` (PERDIDO) · `/dev/dri/renderD129` (ausente) · variable `$H` sin declarar.

## 4. READMEs — qué es cada uno (18 en total)

| Fichero | Rol propuesto | Estado |
|---|---|---|
| `README.md` (raíz) | **canónico** (estructura oficial) | OBSOLETO en narrativa (`21-29` dice reorg pendiente) |
| `00-INDICE/README.md` | **a decidir** (D1): índice de `00-INDICE/` o snapshot | 5 rutas `experiments/` rotas |
| `01-AUDITORIA/FASE-R3-1-…/README.md` | auxiliar (auditoría) | coherente |
| `03-EXPERIMENTOS/FASE-R4C-…/README.md` | auxiliar (experimento) | coherente |
| `03-EXPERIMENTOS/WORKLOAD-SINTETICO/README.md` | auxiliar (experimento) | coherente |
| `04-IMPLEMENTACION/projects/*/README.md` (7) | auxiliares (proyecto) | coherente |
| `04-IMPLEMENTACION/rx550-torneo/README-FASE{1,2,3}.md` + `README-M1.md` | auxiliares (fase) | coherentes |
| `05-FUENTES-EXTERNAS/RX550_Benchmarks/README.md` | auxiliar (fuente) | contradice a `BENCHMARK-INVENTORY` (D3) |

**Ninguno se modifica antes de D1.**

## 5. `R2-GLOBAL-DOCUMENTATION-MAP.md` — 18 referencias a la raíz antigua

| Línea(s) | Referencia antigua | Qué debe apuntar en la estructura nueva |
|---|---|---|
| 23 | raíz `/home/lucas/Escritorio/RX550_Iterative_Research/` | raíz `/home/lucas/Escritorio/RX550-INVESTIGACION/` |
| 31 | `RX550_BUILD_SPECIFICATION.txt` (en raíz) | `02-ARQUITECTURA/RX550_BUILD_SPECIFICATION.txt` |
| 40 | `experiments_proposed.md` | `00-INDICE/experiments_proposed.md` |
| 44 | capa `experiments/` | `03-EXPERIMENTOS/` |
| 130 | `projects/{BERRETA,GHOST,RX-COMPRESSION-ENGINE,ORCHESTRATOR}/` | `04-IMPLEMENTACION/projects/{…}/` |
| 134 | sección `rx550-torneo/` | `04-IMPLEMENTACION/rx550-torneo/` |
| 138-141 | `rx550-torneo/README-FASE{1,2,3}.md`, `README-M1.md` | `04-IMPLEMENTACION/rx550-torneo/…` |
| 142-144 | `rx550-torneo/{rx550-torneo,src/rx550_torneo,tests/}` | `04-IMPLEMENTACION/rx550-torneo/…` |
| 166 | `projects/` (BERRETA, GHOST, …) | `04-IMPLEMENTACION/projects/` |
| 172-175 | 4 capas: raíz, `experiments/`, `rx550-torneo/`, backup; `experiments/FASE-R2-…`, `projects/` | 6 directorios de la estructura actual |

**Verificación de existencia:** de esos destinos antiguos, solo `RX550_Iterative_Research/experiments/` existe y está **vacío**; `projects/` y `rx550-torneo/` **no existen**. Todos los destinos nuevos existen.

## 6. Los 4 documentos inexistentes

| Nombre esperado | Quién lo referencia | Para qué debería servir | ¿Evidencia suficiente para crearlo? | ¿Decisión humana? |
|---|---|---|---|---|
| `00-INDICE/FUENTES-FALTANTES.md` | `README.md:28`; `REORGANIZATION-AUDIT.md:156,260,294`; ambos `POST-REORGANIZATION-*RESULT.md:171` | inventariar los UNKNOWN activos y su fuente pendiente | **Sí**: los UNKNOWN ya están en `open_questions.md` y `R1-7-CRITICAL-GAPS.md` (según `REORGANIZATION-AUDIT.md:156`) | **Sí** (ubicación: `00-INDICE/` frente a otra) |
| `01-AUDITORIA/IMPLEMENTATION-READINESS/IMPLEMENTATION-ROADMAP.md` | `IMPLEMENTATION-READINESS-AUDIT.md:927-928`; `REORGANIZATION-AUDIT.md:257` (propone `04-IMPLEMENTACION/` o junto al audit) | hoja de ruta de implementación derivada del audit | **Parcial**: el audit tiene el contenido, pero la ubicación está sin decidir | **Sí** |
| `…/IMPLEMENTATION-SAFETY-RULES.md` | ídem | reglas de seguridad de implementación (frontera de escrituras) | **Sí**: las reglas ya están dispersas (`MASTER-RESEARCH-STATUS.md:348-357,393-400`) | **Sí** |
| `PROJECT-ROADMAP.md` | `MASTER-PLAN.md:5` (como “Norte”) | documento conceptual de norte (optimizar FPS, no vatios) | **No**: es una noción, no un artefacto; el `MASTER-PLAN.md` ya cumple la función | **Sí** (crear o declarar que el norte vive en `MASTER-PLAN.md`) |

## 7. Los 3 ficheros “con hashes contradictorios” — explicación

**No hay contradicción.** Los tres (`FASE-E-REAL-GAME-BASELINE-DESIGN.md`, `FASE-F-GEOMETRY-INVESTIGATION-DESIGN.md`, `SYNTHETIC-WORKLOAD-DESIGN.md`) tienen hash **distinto** del manifiesto pre-movimiento y git los ve modificados. La enumeración fue errónea: el script de re-mapeo noATTLE.include `04-IMPLEMENTACION/<basename>` como candidato, por eso los marcó “sin destino” y se interpretó como “idénticos”.

**Realidad:** 33 (mapeados, distintos) + 3 (no mapeados, distintos) = **36 = los 36 `M` de git**. Correspondencia 1:1. Ningún hash se sobrescribe ni se elige versión: solo se documenta.

## 8. Los 2 power sweeps y `results/` — por qué no utilizables

| Elemento | Evidencia | Conclusión |
|---|---|---|
| `rx550-power-sweep-20260918-132309` | 194 ficheros, 0 `.md`; 96 menciones de “Intel(R) HD Graphics 4600” y 48 de `0x8086`; `results.csv`: `sclk_avg=0.0`, `power_w_avg=0.0` | Datos de la **iGPU**, no de la RX550. Inservible |
| `rx550-power-sweep-20260918-140527` | 194 ficheros, 0 `.md`; 96 menciones de “AMD Radeon RX 550” y 48 de `0x1002`; `results.csv`: `sclk_avg=0.0` pero `sclk_max=1071`; `mclk_avg=915` pero `temp_avg=772` | Datos de la RX550, pero **columnas desalineadas**: `sclk_avg` nunca capturado; los valores de `temp_avg` parecen ser MCLK. Requiere reconstrucción y parser validado |
| `03-EXPERIMENTOS/results/` | 1 solo fichero: `results/logs/session1.log` con `[run_all:S1] BUILD FAILED` | No es un experimento; es un build fallido |

**¿Conservar como evidencia histórica?** Los 2 power sweeps **sí**: son 388 ficheros de telemetría única (cap=35.000.000 µW) que no se pueden regenerar y que muestran que se intentó barrer el cap. `results/` también conservarse (1 línea). Ninguno debe usarse para afirmar curvas de potencia. **Decisión humana: nota explicativa (C) vs.숨겨진 uso.**

## 9. NotebookLM — relación con el proyecto canónico

| Dato | Valor |
|---|---|
| Ruta | `/home/lucas/Escritorio/RX550-INVESTIGACION-NOTEBOOKLM/` |
| Contenido | **50 ficheros regulares, 0 symlinks, 0 directorios** |
| Hashes duplicados | 0 |
| Prefijos | `01-…`, `02-…` (sin colisión de nombres con el repo) |
| Fecha | 23-sep 03:44 → **anterior** a la reorganización (06:24) |
| Relación | **snapshot plano de 50 documentos del proyecto canónico en ese momento**, para carga a NotebookLM |
| Estado | **INTACTO. NO convertir en symlinks. NO mover. NO tocar.** |

Documentado como categoría **F**. Su relación con el canónico: es una **copia de fecha anterior**, no un espejo; por eso sus contenidos reflejan el árbol pre-movimiento.

## 10. Commit diferido — qué falta antes de poder commitear

1. **Resolver D1–D9** (D10 es el commit en sí).
2. **Decidir el destino de Set H** en el árbol: entra intacto (y el commit documenta scripts no reejecutables) o se excluye (y el manifiesto queda inconsistente).
3. **Verificar coherencia del manifiesto** `REORGANIZACION-MANIFEST.sha256` tras cualquier cambio.
4. **Decidir granularidad**: 1 commit vs. temáticos (movimiento / Set A–G / Set I / auditorías / informe).
5. **Verificar que ningún “F” se toca** en el diff.
6. **Auditar los 3 ficheros de D5** solo si se quiere documentar qué cambió (opcional).

---

# RESUMEN DE QUÉ DEBE DECIDIR EL USUARIO

| Decisión | Objeto | Riesgo si se elige mal |
|---|---|---|
| D1 | Rol de `00-INDICE/README.md` | Medio |
| D2 | U2: mapa global (actualizar/congelar/dividir) | **Alto** |
| D3 | U4: estado de benchmarks (fuente de verdad) | Medio |
| D4 | U5: `MASTER-PLAN.md:781` | Bajo |
| D5 | Cerrar la falsa alarma de hashes | Muy bajo |
| D6 | Estado canónico de R-4B | **Alto** |
| D7 | Evidencia `/tmp` de R-4B (no reconstruir) | **Alto** |
| D8 | Set H (no tocar / reparar estático / congelar) | **Alto** |
| D9 | Los 11 localizadores `/tmp` fuera de Set H | Medio |
| D10 | Commit (1 vs. varios, qué incluye) | Medio |

**No se toma ninguna decisión. Se espera al usuario.**

---

# PARTE 4 — AMPLIACIÓN READ-ONLY DE D1, D2, D3 y D4

> Ampliación solicitada tras la adopción de D5–D10. **No se ha modificado ningún documento del proyecto**: solo se amplió este fichero de decisiones.

---

## D1 — `00-INDICE/README.md` (34 líneas, mtime 20-sep)

### D1.1 Las 5 rutas `experiments/` exactas y sus destinos actuales

| # | Línea | Ruta exacta antigua | Destino actual verificado | Estado del destino |
|---|---|---|---|---|
| 1 | `:25` | `experiments/fase-a-discriminacion-20260919-114241/` | `03-EXPERIMENTOS/fase-a-discriminacion-20260919-114241/` | **EXISTE** (15 runs + scripts + `RESULTADOS-FASE-A.md`) |
| 2 | `:26` | `experiments/fase-b-cap-probe-20260919-122038/` | `03-EXPERIMENTOS/fase-b-cap-probe-20260919-122038/` | **EXISTE** (28 runs + `RESULTADOS-FASE-B.md`) |
| 3 | `:27` | `experiments/ep06-soak-cap-20260919-205645/` | `03-EXPERIMENTOS/ep06-soak-cap-20260919-205645/` | **EXISTE** (4 réplicas + `RESULTADOS-EP06.md`) |
| 4 | `:28` | `experiments/ep05-mesa-custom-20260919-212249/` | `03-EXPERIMENTOS/ep05-mesa-custom-20260919-212249/` | **EXISTE** (12 runs + `RESULTADOS-EP05.md`) |
| 5 | `:29-30` | `experiments/M1-cap-35-30/` | `03-EXPERIMENTOS/M1-cap-35-30/` | **EXISTE** (10 corridas + `RESULTADOS-M1.md`) |

### D1.2 Bonus: los 10 ficheros que el README también cita (tabla “Cómo empezar” + “Archivos de investigación”)

**Todos existen, pero 6 de 10 cambiaron de directorio** y el README no lo refleja:

| Fichero citado | Ubicación real | ¿En `00-INDICE/`? |
|---|---|---|
| `FINAL-RESEARCH-STATUS.md` | `00-INDICE/FINAL-RESEARCH-STATUS.md` | ✅ sí |
| `RX550_BUILD_SPECIFICATION.txt` (`:8`) | `02-ARQUITECTURA/RX550_BUILD_SPECIFICATION.txt` | ❌ **movido** |
| `knowledge.md` | `02-ARQUITECTURA/knowledge.md` | ❌ **movido** |
| `evidence.md` | `02-ARQUITECTURA/evidence.md` | ❌ **movido** |
| `hypotheses.md` | `02-ARQUITECTURA/hypotheses.md` | ❌ **movido** |
| `decisions.md` | `00-INDICE/decisions.md` | ✅ sí |
| `open_questions.md` | `02-ARQUITECTURA/open_questions.md` | ❌ **movido** |
| `research_log.md` | `02-ARQUITECTURA/research_log.md` | ❌ **movido** |
| `experiments_proposed.md` | `00-INDICE/experiments_proposed.md` | ✅ sí |
| `rejected_ideas.md` | `02-ARQUITECTURA/rejected_ideas.md` | ❌ **movido** |

→ **11 rutas rotas en total** (5 `experiments/` + 6 ficheros sin prefijo), no solo 5. **Ningún fichero citado ha desaparecido**: todos existen en la estructura nueva.

**Cobertura:** el README describe 9 ficheros de los **20** que contiene `00-INDICE/`. Los 11 restantes no se listan (incluidos `MASTER-PLAN.md`, `MASTER-RESEARCH-STATUS.md`, `REGISTRO-DE-MOVIMIENTOS.md`, los 6 de reparación/reorganización y las 4 auditorías de background).

### D1.3 Históricas vs canónicas

| Referencia | ¿Histórica o canónica? | Razón |
|---|---|---|
| Las 5 `experiments/…` | **Deben ser canónicas** (con prefijo nuevo) | El contenido sigue vigente: FASE A/B, EP-05/06 y M1 son experimentos **cerrados pero documentados**; sus resultados se citan desde índices maestros |
| Los 6 ficheros movidos a `02-ARQUITECTURA/` | **Deben ser canónicos** (con prefijo nuevo) | `knowledge/evidence/hypotheses/open_questions/research_log/rejected_ideas` son el estado vivo del conocimiento |
| `RX550_BUILD_SPECIFICATION.txt` (`:8`) | **Canónico**, pero su ubicación cambió | El propio README lo llama “EL documento de ingeniería para implementar” |
| `~/Escritorio/RX550_Modo_Torneo_Backup_2026-09-19_0836/` (`:31`) | **Histórica declarada** (“Históricos 17/09, NO reproducibles”) | Correcta como está: el backup existe y se etiqueta explícitamente |

### D1.4 Qué documentos referencian este README

| Documento | Referencia | Naturaleza |
|---|---|---|
| `POST-REORGANIZATION-REFERENCES-AUDIT.md:324` | “sigue siendo índice de navegación útil pero describe la estructura antigua y ahora **duplica al nuevo `README.md` raíz**” | Diagnóstico que origina U1 |
| `POST-REORGANIZATION-REFERENCE-REPAIR-PLAN.md:22,87,144,293,311` | “rol: índice activo → se actualiza, o deprecado → no se toca” (**U1**) | Plan que excluyó el fichero |
| `POST-REORGANIZATION-REFERENCE-REPAIR-RESULT.md:11,112,136` | “**NO aplicado** … U1 sin decidir → excluido” | Registro de la exclusión |
| `REORGANIZATION-AUDIT.md` (tabla de movimientos) | no lo lista → seoqinferido que quedó fuera del plan de movimientos | — |

**Ningún documento operativo depende de él**: no aparece citado en `MASTER-PLAN.md`, `MASTER-RESEARCH-STATUS.md` ni `PROJECT-DOCUMENTATION-STATUS.md`. Solo lo mencionan los tres documentos de reparación. Esto reduce el coste de cualquier opción.

### D1.5 Qué se rompería al sustituir

| Si se sustituyen… | Qué se rompe | Qué NO se rompe |
|---|---|---|
| solo las 5 rutas `experiments/` | nada técnico; quedan 6 rutas sin prefijo todavía rotas | nada |
| las 11 rutas | nada técnico (todas las destinos existen) | nada |
| el contenido de los “datos experimentales crudos” (descripciones EP-05/06, M1) | requiere reescritura, no sustitución | — |
| si se retira el fichero | se pierde el punto de entrada “Cómo empezar” para quienUse `00-INDICE/`; **no hay referencias entrantes que se rompan** (verificado) | el README raíz sigue siendo el índice oficial |

**Riesgo residual:** al corregir rutas sin decidir el rol, este README y el README raíz quedarían **ambos como “el índice”**, perpetuando la ambigüedad que la auditoría de referencias ya finns señalo (`:324`).

### D1.6 Propuesta de estructura canónica (NO se aplica)

Sin elegir por el usuario, la forma mínima coherente sería:

```
00-INDICE/README.md
  1. Rol: índice de 00-INDICE/ (no del repo entero) → remitir al README raíz para el mapa global
  2. Cómo empezar: los 3 documentos de entrada con ruta completa
  3. Inventario: los 20 .md de 00-INDICE/ agrupados (índices maestros / estado / reparación / auditorías)
  4. Datos experimentales: los 5 experimentos con prefijo 03-EXPERIMENTOS/
  5. Nota: "Este índice no sustituye a ../README.md"
```

**Lo que debe decidir el usuario** (sigue abierto): (a) repararlo como índice de `00-INDICE/`, (b) congelarlo como histórico, (c) retirarlo y que solo exista el raíz. La evidencia sugiere (a) o (c); la reparación pasada lo dejó sin decidir.

---

## D2 — `R2-GLOBAL-DOCUMENTATION-MAP.md` (175 líneas) — 18 referencias

### D2.1 Tabla individual de las 18 referencias (sin reemplazo global)

| # | Línea | Referencia antigua exacta | Destino actual | Estado del destino | ¿Histórica o actualizar? | Corrección individual propuesta |
|---|---|---|---|---|---|---|
| 1 | `23` | Raíz `/home/lucas/Escritorio/RX550_Iterative_Research/` | `/home/lucas/Escritorio/RX550-INVESTIGACION/` | **EXISTE** (vacía de contenido, solo `experiments/`) | **Actualizar** | cambiar la raíz declarada |
| 2 | `31` | `RX550_BUILD_SPECIFICATION.txt` (en raíz) | `02-ARQUITECTURA/RX550_BUILD_SPECIFICATION.txt` | **EXISTE** | **Actualizar** | anteponer `02-ARQUITECTURA/` |
| 3 | `40` | `experiments_proposed.md` | `00-INDICE/experiments_proposed.md` | **EXISTE** | **Actualizar** | anteponer `00-INDICE/` |
| 4 | `44` | capa `experiments/` | `03-EXPERIMENTOS/` | **EXISTE** (16 subdirectorios) | **Actualizar** | renombrar la capa en la descripción |
| 5 | `130` | `projects/{BERRETA,GHOST,RX-COMPRESSION-ENGINE,ORCHESTRATOR}/` | `04-IMPLEMENTACION/projects/{…}/` | **EXISTE** (los 4 + 10 ideas) | **Actualizar** | anteponer `04-IMPLEMENTACION/` |
| 6 | `134` | `rx550-torneo/` | `04-IMPLEMENTACION/rx550-torneo/` | **EXISTE** | **Actualizar** | anteponer `04-IMPLEMENTACION/` |
| 7 | `138` | `rx550-torneo/README-FASE1.md` | `04-IMPLEMENTACION/rx550-torneo/README-FASE1.md` | **EXISTE** | **Actualizar** | prefijo |
| 8 | `139` | `rx550-torneo/README-FASE2.md` | ídem FASE2 | **EXISTE** | **Actualizar** | prefijo |
| 9 | `140` | `rx550-torneo/README-FASE3.md` | ídem FASE3 | **EXISTE** | **Actualizar** | prefijo |
| 10 | `141` | `rx550-torneo/README-M1.md` | ídem M1 | **EXISTE** | **Actualizar** | prefijo |
| 11 | `142` | `rx550-torneo/rx550-torneo` (ejecutable) | `04-IMPLEMENTACION/rx550-torneo/rx550-torneo` | **EXISTE** | **Actualizar** | prefijo |
| 12 | `143` | `rx550-torneo/src/rx550_torneo` | `04-IMPLEMENTACION/rx550-torneo/src/rx550_torneo` | **EXISTE** (9 ficheros) | **Actualizar** | prefijo |
| 13 | `144` | `rx550-torneo/tests/` | `04-IMPLEMENTACION/rx550-torneo/tests/` | **EXISTE** (4 ficheros) | **Actualizar** | prefijo |
| 14 | `166` | `projects/` (4 proyectos propios) | `04-IMPLEMENTACION/projects/` | **EXISTE** | **Actualizar** | prefijo |
| 15 | `172` | 4 capas: raíz, `experiments/`, `rx550-torneo/`, backup | raíz + `03-EXPERIMENTOS/` + `04-IMPLEMENTACION/rx550-torneo/` + backup (B) | raíz **vacía**; backup **EXISTE** | **Actualizar** (el backup sí es histórico válido) | reescribir el enumerado de capas |
| 16 | `173` | (continuación de 172) | ídem | ídem | **Actualizar** | ídem |
| 17 | `174` | `experiments/FASE-R2-PROJECT-DOCUMENTATION/` (diseños E–Q) | los 14 diseños están en `04-IMPLEMENTACION/`; **el directorio de fase ya no existe** | **NO EXISTE** como carpeta | **Actualizar** (la fase se dispersó) | describir la dispersión real |
| 18 | `175` | `projects/` (diseños de proyectos propios) | `04-IMPLEMENTACION/projects/` | **EXISTE** | **Actualizar** | prefijo |

**Sobre la raíz antigua (ref. 1):** `/home/lucas/Escritorio/RX550_Iterative_Research/` **existe** y conserva `experiments/` **vacío** (0 ficheros), pero **`projects/` y `rx550-torneo/` ya no existen** bajo ella. Es decir, la raíz antigua es un **resto vacío**, no un destino utilizable.

### D2.2 Veredicto por tipo

- **17 de 18** son localizadores que deben **actualizarse** (el destino actual existe siempre, salvo la carpeta de fase deshecha).
- **0** deben conservarse como históricas dentro del mapa, **excepto** la mención al backup en `:172-173`, que sí es histórica válida.
- El mapa es el **único** documento que usa las 18; no hay ambigüedad de destino en ninguna (verificado 1:1).

### D2.3 Consumidores del mapa (impacto de una eventual actualización)

| Documento | Referencia al mapa | Si el mapa se actualiza |
|---|---|---|
| `MASTER-PLAN.md:781` | lo describe como entregable R-2.2 (contenido descrito en términos antiguos) | requiere actualizar también la descripción (D4) |
| `MASTER-RESEARCH-STATUS.md:175` | lo cita como entregable R-2.2 vivo | coherente tras actualizar |
| `PROJECT-DOCUMENTATION-STATUS.md:9` | lo declara “mapa de navegación” | coherente tras actualizar |
| `REGISTRO-DE-MOVIMIENTOS.md:9` | registra que el mapa se movió de `experiments/FASE-R2-…/` a `00-INDICE/` | sin impacto (registro histórico) |

**Lo que debe decidir el usuario** (sigue abierto): actualizar el mapa como navegación viva, congelarlo como histórico, o dividirlo. **No se hará reemplazo global**; si se actualiza, debe ser referencia por referencia (tabla D2.1).

---

## D3 — Estado de benchmarks: por qué existe la discrepancia “4 vs 1”

### D3.1 Los 4 benchmarks y su estado real (verificado en disco)

| # | Benchmark | Instalación externa | Descarga en repo | Evidencia de ejecución | Estado propuesto |
|---|---|---|---|---|---|
| 1 | **GravityMark 1.89** | `berchmark/instalados/GravityMark_1.89` (196 MB, 27 binarios) | `official-downloads/gravitymark/GravityMark_1.89.run` (**193 MB, descarga completa**) | `03-EXPERIMENTOS/EXPLORATORIO-GravityMark/runs/RESULTADO.md` + telemetría `200k/` | **VALID** (instalado, descargado en repo, ejecutado con resultado) |
| 2 | **UNIGINE Superposition 1.1** | `berchmark/instalados/Unigine_Superposition-1.1` (2,7 GB, 6 binarios) | `cancelled-downloads/Unigine_Superposition-1.1.run.partial` (**34 MB, descarga CANCELADA**) | `runs/RESULTADO-Superposition.md` (**score 804, ejecutado “correctamente”**, pero <27 W) | **INCONCLUSIVE** (ejecutado, pero no cumple el criterio de potencia; carga efectiva = config por defecto 1600×900 Medium) |
| 3 | **UNIGINE Heaven 4.0** | `berchmark/instalados/Unigine_Heaven-4.0` (337 MB, 25 binarios) | — (no en repo) | **0 documentos en `03-EXPERIMENTOS/`** | **HISTORICAL** (instalado, sin ejecución registrada) |
| 4 | **UNIGINE Valley 1.0** | `berchmark/instalados/Unigine_Valley-1.0` (520 MB, 25 binarios) | — (no en repo) | **0 documentos en `03-EXPERIMENTOS/`** | **HISTORICAL** (instalado, sin ejecución registrada) |

### D3.2 Por qué “4 vs 1”

No es una contradicción de hecho, sino **dos supuestos de qué se contaba**:

| Tesis | Afirmación | Verificación |
|---|---|---|
| **“1 descargado”** (`RX550_Benchmarks/README.md:3,7-24`, `docs/SOURCES-AND-EXECUTION.md:5-10,23-27`) | solo GravityMark terminó su descarga en el repo; Superposition fue cancelado | **CORRECTO si se refiere a las descargas dentro del repo**: hay 1 `.run` completo + 1 `.partial` |
| **“4 instalados”** (`BENCHMARK-INVENTORY.md:62-72,184-197`, `MASTER-PLAN.md:82,104,109-120`, `MASTER-RESEARCH-STATUS.md:50,388`) | 4 installers extraídos y disponibles | **CORRECTO**: los 4 directorios existen en `berchmark/instalados/` con binarios ejecutables |

**La discrepancia real es de granularidad del estado**: “descargado en el repo” ≠ “instalado fuera del repo” ≠ “ejecutado con resultado”. Los documentos mezclan los tres ejes. `BENCHMARK-INVENTORY.md` conserva ejecuciones históricas y deja Heaven/Valley sin resultado; ninguna ejecución autoriza repetirla.

### D3.3 Documentos que contienen cada afirmación

| Afirmación | Documento:línea |
|---|---|
| 1 descargado, sin instalar | `RX550_Benchmarks/README.md:3,7-24` |
| solo GravityMark descargado; Superposition cancelado | `docs/SOURCES-AND-EXECUTION.md:5-10,23-27` |
| 4 instalados | `BENCHMARK-INVENTORY.md:3,62,65,68` (`INSTALADO` por benchmark) |
| 4 instalados | `MASTER-PLAN.md:82,104,109-120` |
| 4 instalados | `MASTER-RESEARCH-STATUS.md:50,388` |
| instalación only (externa) | `PROJECT-DOCUMENTATION-STATUS.md:61` |
| ejecución real de Superposition | `03-EXPERIMENTOS/EXPLORATORIO-GravityMark/runs/RESULTADO-Superposition.md` |
| ejecución real de GravityMark | `runs/RESULTADO.md` |
| “Superposition cancelado” vs “candidato prioritario” dentro del mismo doc | `BENCHMARK-INVENTORY.md` (secciones contradictorias) |

### D3.4 Lo que debe decidir el usuario (sigue abierto)

1. Cuál documento es la **fuente de verdad** del estado de benchmarks (propuesta de la documentación: `SOURCES-AND-EXECUTION.md`, por ser el documento de estado de ejecución).
2. Si se **adopta la separación de 3 ejes** (descargado / instalado / ejecutado) en `BENCHMARK-INVENTORY.md`.
3. Si las **descargas** en repo y las **instalaciones** externas se inventory en un único sitio o se mantienen separadas (hoy están en sitios distintos y solo una es verificable desde el repo).
4. Si Superposition (INCONCLUSIVE) se mantiene como candidato para M2 o queda en espera, dado que se ejecutó pero no alcanzó 27 W.

**No se elige automáticamente cuál versión es la correcta.**

---

## D4 — `MASTER-PLAN.md:781` (referencia U5)

### D4.1 Contexto exacto de la línea

La línea 781 es una **fila de la tabla “Entregables (tracer a su archivo)”** de la fase R-2, no un localizador:

```
| R-2.2 | `R2-GLOBAL-DOCUMENTATION-MAP.md` | Mapa documental completo del repositorio
  (raíz, experiments/ A–D/R-0/R-1/sintético, rx550-torneo, backup, R-2)
  + rutas de navegación para investigador nuevo | COMPLETADA |
```

### D4.2 A qué evidencia apunta aparentemente

El texto “experiments/ A–D/R-0/R-1/sintético” **describe el contenido que el mapa tenía cuando se redactó** (antes del movimiento). No es un enlace: `test -e` no aplica, y el destino real (`R2-GLOBAL-DOCUMENTATION-MAP.md`) está en `00-INDICE/` y sí está bien citado en la misma fila.

### D4.3 ¿Sigue siendo válida?

- Como **descripción del entregable R-2.2 tal como se entregó en su momento**: **sí**, es histórica correcta.
- Como **descripción del estado actual del mapa**: **no**, porque el mapa ahora vive en `00-INDICE/` y sus 18 referencias apuntan a la raíz antigua (ver D2).

### D4.4 Alternativa actual que podría corresponderle

Si se actualizara la fila para reflejar el estado vigente, el texto podría decir “mapa del repositorio con 6 directorios (`00-INDICE/`…`05-FUENTES-EXTERNAS/`)”, pero eso **dependería de D2** (si el mapa se actualiza, se congela o se divide). **No se puede decidir D4 antes que D2.**

### D4.5 ¿Requiere decisión humana?

**Sí**, pero de riesgo **bajo** y con dependencia de D2. Opciones: (a) dejar como está (registro histórico de la entrega R-2.2), (b) actualizar la descripción si y solo si D2 se resuelve como “mapa vivo”, (c) reescribir como texto neutro sin ruta.

**`MASTER-PLAN.md` NO se modifica** hasta decisión.

---

## Nota de cierre de la ampliación

- D1: 11 rutas a corregir (5 `experiments/` + 6 ficheros movidos), rol del documento sigue abierto.
- D2: 18 referencias, 17 a actualizar + 1 histórica (backup); la raíz antigua es un resto vacío.
- D3: 4 benchmarks con estados **VALID / INCONCLUSIVE / HISTORICAL / HISTORICAL**; la discrepancia es de granularidad (descargado ≠ instalado ≠ ejecutado), no de hecho.
- D4: 1 fila de tabla, riesgo bajo, dependiente de D2.

**Nada fue modificado.** Este es el único fichero actualizado en esta ampliación.
