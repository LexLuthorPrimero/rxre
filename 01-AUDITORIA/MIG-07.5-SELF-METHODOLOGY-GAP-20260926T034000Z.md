# MIG-07.5 — SELF-METHODOLOGY GAP: ¿puede OpenCode detectar que su propia metodología es insuficiente?

> Artefacto nuevo de auditoría. No modifica ningún artefacto previo.
> No implementa nada. No crea agente, gate, permission, policy ni hook.
> No usa ninguna afirmación del propio agente como evidencia de que su propio mecanismo funciona.

```
DOCUMENT_ID=MIG-07.5-SELF-METHODOLOGY-GAP
CREATED_UTC=2026-09-26T03:40:00Z
TYPE=METHODOLOGY_SELF_DIAGNOSIS_INVESTIGATION

MIG-07=VERIFYING
MIG-07.5=VERIFYING
E1_RESULT=AUTHORITY_CONFLICT
PRECEDENCE_RULE=NOT_AVAILABLE
E6_RESULT=DIMENSION_REQUIRED_NOT_IMPLEMENTED
E6_IMPLEMENTED=0
AUTHORITY_DOCUMENT_CREATED=0
ARBITRARY_AUTHORITY_CHOSEN=0
IMPLEMENTATION=NOT_EXECUTED
```

Estado de entrada preservado. Clasificación usada: `OBSERVED` · `SUPPORTED` · `PLAUSIBLE` ·
`UNKNOWN` · `NOT_AVAILABLE` · `NOT_PROVEN` · `CONFLICT`.

---

## 1. RESUMEN

**El mecanismo no existe. `SELF_METHODOLOGY_GAP=CONFIRMED`.**

No como ausencia de capacidad de razonamiento — el modelo razona y detecta. Sino porque
**no existe ninguna capacidad del sistema que convierta «lo razoné en esta sesión» en «queda
registrado, es contable, y bloquea la promoción»**.

La evidencia más fuerte no es teórica. Está en un artefacto escrito hace 5 fases:

> `01-AUDITORIA/MIGRATION-METHODOLOGY-AUDIT-20260926T011531Z.md:23` contiene `dePersistir`.
> El escaneo automático **lo detectó** (`camelCase=1` reportado) y **nunca se corrigió**.
> Sobrevivió a 5 fases posteriores. Y el control de calidad de la fase 5 reportó `0` porque
> **escaneó solo el documento nuevo**, no los seis.

Eso es `OUTPUT_INTEGRITY_GAP` + `COVERAGE_GAP` + `SELF_CORRECTION_GAP` con prueba instrumental,
y demuestra algo más grave: **la cobertura del QC se declara como total cuando era parcial.**

| # | Hallazgo | Clasificación |
|---|---|---|
| H-1 | **No existe ninguna capacidad de autodiagnóstico metodológico** en OpenCode V2. La documentación oficial no la describe | `NOT_AVAILABLE` |
| H-2 | OpenCode V2 **sí** expone puntos de extensión capaces de implementar L3 y L5: `ctx.permission.hook("evaluate")` puede **sobrescribir un permiso a `deny`**, y `ctx.tool.hook("execute.before")` puede **inspeccionar la entrada antes de escribir** | `OBSERVED` |
| H-3 | Los puntos de extensión son **primitivas**, no diagnóstico. La lógica de adequacy debe aportarla el usuario | `SUPPORTED` |
| H-4 | `https://opencode.ai/v2/docs/steps` → **HTTP 404**. La capacidad nombrada en el encargo **no existe** en V2 | `OBSERVED` |
| H-5 | **Un defecto detectado por escaneo automático y nunca corregido** (§4, caso O-01) | `OBSERVED` |
| H-6 | **Una corrección mío introduced un defecto nuevo** (§8). La tasa de fallo del corrector no es cero | `OBSERVED` |
| H-7 | **El conteo de recurrencias (13+ corrupciones) existe solo en conversación.** Ningún artefacto lo registra: `grep -c 'corrupci\|CJK'` sobre los 6 artefactos = **0 coincidencias reales** | `OBSERVED` |
| H-8 | Las 3 refutaciones K-7, K-8 y método-2 fallaron por **cobertura de búsqueda**, no por razonamiento | `OBSERVED` |
| H-9 | No existe ningún script de QC de salida. `tools/validate_rx550_final.py` valida estado del RX550, no integridad de artefactos del agente | `OBSERVED` |
| H-10 | De 154 tests del collector, **0 ejecutan el barrido**; las 2 llamadas a `main()` están dentro de `assertRaises(SystemExit)` | `OBSERVED` |

**Ninguno de los 10 hallazgos se cierra con este documento.** El documento los describe.

---

## 2. FASE 1 — DEFINICIÓN OPERACIONAL

11 categorías. Cada una se valida contra casos reales de esta investigación (§3).

| Cat | Nombre | Definición operacional | Distinción crítica que la separa de la vecina |
|---|---|---|---|
| **A** | `PROJECT_DEFECT` | El proyecto contiene un defecto que la metodología disponible **sí** bastaba para detectar o corregir. | Se corrige **sin** cambiar la metodología. |
| **B** | `METHODOLOGY_GAP` | Hay un problema para el que la metodología **no contiene** regla, mecanismo ni procedimiento suficiente. | El defecto no desaparece; se declara el método insuficiente. |
| **C** | `VERIFICATION_GAP` | OpenCode puede **producir** la afirmación pero no existe mecanismo **independiente** para verificarla. | El problema es la asimetría productor/verificador, no la producción. |
| **D** | `COVERAGE_GAP` | La conclusión puede ser incorrecta porque el procedimiento de descubrimiento **no garantiza cobertura**. | El razonamiento es válido sobre el subconjunto tradeado. |
| **E** | `AUTHORITY_GAP` | Hay conflicto entre fuentes y **no existe regla formal** que determine precedencia. | El conflicto es de *precedencia*, no de *contenido*. |
| **F** | `STATE_MODEL_GAP` | El estado requerido no tiene representación estructurada suficiente. | Falta el **soporte**, no el valor. |
| **G** | `PROVENANCE_GAP` | Hay evidencia de qué ocurrió, falta quién/origen/contexto. | El *qué* está; falta el *quién*. |
| **H** | `OUTPUT_INTEGRITY_GAP` | El proceso de generación introduce corrupción, omisión o contradicción **en el propio artefacto producido**. | El defecto está en la salida, no en el proyecto. |
| **I** | `SELF_CORRECTION_GAP` | OpenCode detecta un defecto pero **no puede determinar con fiabilidad** si su corrección lo resolvió sin introducir otro. | El problema es la **verificación de la corrección**, no la corrección. |
| **J** | `INDEPENDENCE_GAP` | El productor de una afirmación es también su **único** verificador. | Estructural: no falta una herramienta, falta una separación de roles. |
| **K** | `GATE_GAP` | Existe una condición que debería bloquear el avance y **no hay mecanismo estructural** que la imponga. | La condición se conoce; no se **impone**. |

### ¿Son definitivas? — No. Resultado de la adversarial (§12)

**Una categoría nueva es necesaria y las 11 no son disjuntas.** Ver §12.1.

`COVERAGE_GAP` (D) y `OUTPUT_INTEGRITY_GAP` (H) **se solapan**: el caso O-01 (§4) es
simultáneamente un defecto de cobertura — escaneé 1 de 6 documentos — y un defecto de integridad
de salida. **`CONFLICT`: las categorías del encargo no forman una partición.**

---

## 3. FASE 2 — INVENTARIO DE FALLOS OBSERVADOS (CASOS DE PRUEBA)

Las 8 preguntas por caso. `EV` = evidencia en artefacto del repo; `TX` = transcripción de sesión
(no artefacto, por tanto evidencia más débil).

### 3.1 Tabla maestra

| Caso | Clase | ¿Detectó OC? | ¿Inmediato? | ¿Regla o *ad hoc*? | ¿Regla que obliga? | ¿Mecanismo para verificar la corrección? | ¿Puede repetirse? | ¿Sabía que su método era insuficiente? | EV |
|---|---|---|---|---|---|---|---|---|---|
| **MIG-01** `UnboundLocalError` en `observe()` | A | **no** | después de 2 runs | *ad hoc* (traza) | **NO** | **NO** | sí | **NO** | EV |
| **MIG-02** 154 tests, 0 ejecutan el barrido | A | **no** | lo detectó la revisión indep. | *ad hoc* | **NO** | parcial | sí | **NO** | EV |
| **MIG-03** estado canónico anclado a HOST-B | A | **sí** | tarde | *ad hoc* | **NO** | **NO** | sí | **NO** | EV |
| **MIG-04** `P0=B__CONTINAM…` de HOST-A | A | **sí** | tarde | *ad hoc* | **NO** | **NO** | sí | **NO** | EV |
| **MIG-07/E1** conflicto de autoridad | E | **sí** | sí | *ad hoc* | parcial (`No elegir`) | **NO** | sí | **SÍ** | EV |
| **MIG-07/E6** dimensión J no representada | F+G | **sí** | sí | *ad hoc* | **NO** | **NO** | sí | **SÍ** | EV |
| **K-7** gate omitido (dimensión E) | D | **no**; refutado por escaneo | n/a | *ad hoc* | **NO** | **NO** | **SÍ, y ya pasó 2 veces** | **NO** | EV |
| **K-8** `/` subestimado (9 vs 513) | D | **no**; refutado | n/a | *ad hoc* | **NO** | **NO** | **SÍ, ya pasó 2 veces** | **NO** | EV |
| **MIG-09** `write_test.py` escribe `power/control` | A | **sí** | sí | *ad hoc* | **NO** (no cubierto por gate) | **NO** | sí | **SÍ** | EV |
| **MIG-12** collector fuera de git | G | **sí** | sí | *ad hoc* | **NO** | **NO** | sí | **SÍ** | EV |
| **MIG-13** R1 sin evidencia (2 runs) | A | **sí** | sí | *ad hoc* | **NO** | **NO** | sí | **SÍ** | EV |
| **MIG-14** `tests/` inalcanzable, causa `UNKNOWN` | B | **parcial** | — | *ad hoc* | **NO** | **NO** | sí | **SÍ** | EV |
| **MIG-15** 140 referencias rotas | A | **sí** | sí | *ad hoc* | **NO** | **NO** | sí | **NO** | EV |
| **O-01** `dePersistir` detectado y **no corregido** | **H+D** | **SÍ** (automático) | **inmediato** | **procedimiento ad hoc** | **NO** | **SÍ, y no se usó** | **SÍ** | **NO** | EV |
| **O-02** corrección que introduce defecto nuevo | **I+H** | **SÍ** (automático) | inmediato | *ad hoc* | **NO** | **SÍ, y se usó tarde** | **SÍ** | **NO** | TX+EV |
| **P-01** `VERIFIED_BY`/`REVIEWER`/`AUTHORED_BY` = 0 | G | **sí** | sí | *ad hoc* | **NO** | **NO** | sí | **SÍ** | EV |
| **X-01** router `VOCABULARY=REVIEW_REQUIRED` sin escalar | **K** | **sí** | sí | *ad hoc* | **NO** | **NO** | sí | **SÍ** | EV |
| **X-02** contradicción MRS, degradada a `PLAUSIBLE` | E | **sí** | sí | *ad hoc* | **NO** | **NO** | sí | **PARCIAL** | EV |
| **D-01** conteo de staging 226 vs 360 mal calculado | D | **sí** | inmediato | *ad hoc* | **NO** | **SÍ, y se rehízo** | **SÍ, ya pasó 2 veces** | **NO** | TX |

### 3.2 Lecturas

1. **19 de 19 casos: `¿Regla que obliga a detectarlo? = NO` o `parcial`.** `OBSERVED`
2. **19 de 19: `¿Mecanismo para verificar la corrección? = NO` o `parcial`.** `OBSERVED`
3. **4 de 19: `¿Sabía que su método era insuficiente? = NO`.** Los 4 son fallos de cobertura
   (K-7, K-8, D-01, O-01). **Un fallo de cobertura no puede autoconducirse a detección, porque
   por definición el procedimiento no vio lo que tenía que ver.** `SUPPORTED`
4. **Único caso con detección automatizada real: O-01.** Y **falló en el paso siguiente** (la
   remediación). `OBSERVED`
5. **Ningún caso fue detectado «inmediatamente» por una regla.** El más rápido (MIG-09, X-01) fue
   `ad hoc`. `OBSERVED`

---

## 4. FASE 3 — SEÑALES DE AUTODIAGNÓSTICO: EXISTENTE / PARCIAL / AD HOC / NO_IMPLEMENTADA

| # | Señal | Estado | Evidencia de por qué no es `EXISTENTE` |
|---|---|---|---|
| 1 | Ausencia de una regla necesaria | **AD HOC** | 3 refutaciones (K-7, K-8, método-2) las produjo el razonamiento, no una regla |
| 2 | Conflicto entre autoridades | **AD HOC** | `DOCUMENTATION-ROUTER:267` declara `REVIEW_REQUIRED` desde antes de MIG-07; nadie lo ejecutó |
| 3 | Vocabulario no definido | **AD HOC** | `DOCUMENTED`/`SUPPORTED`/`INCONCLUSIVE` sin definir: detectado por muestreo manual |
| 4 | Dimensión requerida no implementada | **AD HOC** | C y J: detectados por enumeración manual de 12 dimensiones |
| 5 | Afirmación sin provenance | **AD HOC** | conteo manual de 15 campos candidatos → 7 con 0 ocurrencias |
| 6 | Afirmación sin verificación independiente | **AD HOC** | 10 patrones buscados a mano |
| 7 | Conclusión de cobertura insuficiente | **NO_IMPLEMENTADA** | K-7, K-8, D-01: **el sistema no puede saber que su búsqueda fue parcial** |
| 8 | Estado contradictorio | **PARCIAL** | existe `CONFLICT`, pero solo lo declara quien lo escribe; nadie lo evalúa |
| 9 | Documentación ≠ implementación | **AD HOC** | detectado revisando a mano |
| 10 | Corrección modifica más de lo esperado | **NO_IMPLEMENTADA** | O-02: no hay diff-before/después; se detectó por lectura |
| 11 | Corrupción de texto | **PARCIAL** | el escaneo existe pero es **ad hoc, no es script, no cubre todos los artefactos, y su resultado no se registra** |
| 12 | Defectos repetidos | **NO_IMPLEMENTED** | H-7: el conteo **no existe en ningún artefacto** |
| 13 | Ciclos de autocorrección | **NO_IMPLEMENTED** | no hay registro de ciclos |
| 14 | Productor = verificador | **NO_IMPLEMENTED** | `VERIFIED_BY`=0; no hay campo que lo exprese |
| 15 | Gate inexistente | **PARCIAL** | `REVIEW_REQUIRED` y `NO_GO` existen como vocabulario, no como enforcement |
| 16 | Gate declarado pero no ejecutable | **AD HOC** | detectado manualmente en el análisis de gates |
| 17 | Evidencia histórica como actual | **PARCIAL** | `STALE` existe en el router y en el censo §7; se aplicó a 16 documentos |
| 18 | Evidencia de otro host como actual | **PARCIAL** | `HOST_SCOPE` existe (4 usos); falló en MIG-03/MIG-04 |

**Resultado: 0 de 18 señales en estado `EXISTENTE`. 4 `PARCIAL`, 10 `AD HOC`, 4 `NO_IMPLEMENTED`.**

**`AD HOC` no es `EXISTENTE`.** Un razonamiento que se repite 5 veces sigue siendo `MODEL_REASONING_ONLY`
(§5). Ninguna de las 18 señales tiene un mecanismo que la convierta en estado registrable.

---

## 5. FASE 4 — DETECCIÓN vs RAZONAMIENTO

Cinco clases. La distinción es el núcleo del encargo.

| Clase | Definición | ¿Suficiente para cerrar una clase de fallo? | Evidencia en este caso |
|---|---|---|---|
| **`MODEL_REASONING_ONLY`** | El modelo lo razonó en una sesión. No queda artefacto, no es reproducible, otro agente puede no hacerlo. | **NO** | Los 19 casos de §3 salvo O-01. Las 10 señales `AD_HOC` de §4. |
| `PROCEDURAL_RULE` | Hay una instrucción escrita que obliga a buscarlo. | Parcialmente: obliga a **mirar**, no a **registrar** | `AGENTS.md` §Evidence vocabulary obliga a no convertir `UNKNOWN` en `PASS`. **No obliga a contar, registrar ni bloquear.** `OBSERVED` |
| `AUTOMATED_CHECK` | Chequeo reproducible, con salida examinable. | Sí para **detectar** | El escaneo CJK/camelCase: reproducible, salida examinable, ejecutado 6 veces. `OBSERVED` |
| `INDEPENDENT_CHECK` | Otro proceso/agente puede verificarlo sin autor. | Requerido para **cerrar** | 0 casos. `NOT_AVAILABLE` |
| `STRUCTURAL_GATE` | El sistema impide la promoción mientras la condición persista. | Requerido para **prevenir** | 0 casos. `NOT_AVAILABLE` |

### 5.1 El caso canónico: O-01

| Pregunta | Respuesta | Evidencia |
|---|---|---|
| ¿Fue detectado por regla? | **No** — por un escaneo que yo escribí en el momento | la invocación del escaneo no es una regla del proyecto |
| ¿Fue detectado por el modelo? | **No** — por un script | el escaneo es determinista |
| ¿Clase? | **`AUTOMATED_CHECK`** | salida reproducible, 0 falsos positivos en este caso |
| ¿Se corrigió? | **NO** | `MIGRATION-…:23` sigue conteniendo `dePersistir` tras 5 fases |
| ¿Por qué no? | El escaneo se ejecutó **sobre el documento recién creado**, no sobre el conjunto. Su salida fue `camel=1` para ese archivo en la fase 3, y no se investigó. | el informe de la fase 3 listó el archivo con `camel=1` y la fase siguiente no volvió a él |
| ¿El QC final de la fase 5 reportó `0`? | **Sí** | porque escaneó 1 archivo de 6 |

**Conclusión de O-01, y es el resultado más importante del documento:**
`AUTOMATED_CHECK` **sin** `STRUCTURAL_GATE` produce una comprobación que puede ejecutarse, pasar
por limpio, y dejar el defecto intacto. El chequeo no era el problema. **El problema es que nada
obliga a que el resultado del chequeo se convierta en acción.** `SUPPORTED`

Y el agravante: en la fase 5 reporté `camelCase: 0` como verificación de QC. Era un número
**parcial presentado como total**. Esa es exactamente la clase de error que un gate estructural
debería impedir, y que ninguna regla del proyecto impide. `CONFLICT`

---

## 6. FASE 5 — ¿HACE FALTA UNA CONDICIÓN `SELF_METHODOLOGY_GAP`?

### 6.1 Condición propuesta (NO implementada)

> **`SELF_METHODOLOGY_GAP=YES`**: el agente encontró evidencia de que la metodología que está
> usando **no contiene una capacidad necesaria** para producir una conclusión válida o verificable.

Evidencia mínima exigible para emitir `YES`:

| # | Debe aportarse | Por qué |
|---|---|---|
| **M1** | Qué capacidad falta, enunciada como ausencia verificable | Sin esto es una opinión |
| **M2** | Qué se intentó y falló, con artefacto | Distingue de «no se intentó» |
| **M3** | Por qué el intento no bastó: **regla ausente** \| **regla presente e incumplida** \| **regla presente y sin cobertura** | Los tres casos requieren acciones distintas |
| **M4** | Qué conclusión queda bloqueada | Sin daño concreto no hay bloqueo legítimo |
| **M5** | Que la evidencia **no** sea «no sé resolverlo» | §11 |

### 6.2 ¿Tres valores?

| Valor | ¿Necesario? | Argumento |
|---|---|---|
| `YES` | **Sí** | |
| `NO` | **Sí** | Sin él, `YES` es el valor por defecto y el término se degrada |
| `UNKNOWN` | **SÍ — y es el más importante** | `UNKNOWN` es la única salida honesta cuando hay evidencia ambigua. Sin él, la presión por emitir `YES` o `NO` empuja a adivinar. Y hay un caso real: **MIG-14** (causa `UNKNOWN`) es exactamente este estado. `SUPPORTED` |

**Pero `UNKNOWN` tiene un coste**: si no bloquea nada, el agente puede emitir `UNKNOWN` para no
detenerse. **Ése es el diseño que hay que decidir**, y no se decide aquí. `PLAUSIBLE`

### 6.3 ¿Hacen falta 7 subcampos?

| Campo | ¿Necesario? | Justificación |
|---|---|---|
| `TRIGGER` | **Sí** | sin el evento detonante, `YES` es retroactivo e inaccionable |
| `EVIDENCE` | **Sí** | M2/M5 |
| `IMPACT` | **Sí** | M4 |
| `ROOT_CAUSE` | **CONDICIONAL** | No siempre aplica: K-7 no tiene causa raíz, tiene una omisión. Propondría `ROOT_CAUSE=HYPOTHESIS` como valor por defecto en lugar del campo |
| `REMEDIATION_REQUIRED` | **Sí** | distingue «saber» de «hacer» |
| `INDEPENDENT_REVIEW_REQUIRED` | **Sí** | conexión directa con J (E-6), que sigue `NOT_IMPLEMENTED` |
| `PROMOTION_BLOCKED` | **CONDICIONAL** | no todos los gaps bloquean promoción. K-7 informational no debería bloquear. Proponer: bloquea si `IMPACT` alcanza una dimensión de gate |

**De 7, 5 son necesarios, 2 condicionales.** `SUPPORTED`

**Ningún campo se implementa.** `OBSERVED`

### 6.4 Incidente registrado durante la redacción de este documento

El control de calidad de §15 (aplicado al **conjunto** de 7 artefactos, no solo al nuevo, según
`RQ-2`) encontró en este mismo documento:

| # | Defecto | Tipo |
|---|---|---|
| **Q-1** | `dePersistir` citado en `MIGRATION-…:43` cuando la línea real es **23** — en 4 lugares | **cita de evidencia incorrecta** |
| **Q-2** | `seStatements`, `sonCapability` | token latino corrupto |
| **Q-3** | `检测`, `依赖`, `伪装`, `永久` | token CJK no intencional |

**7 defectos en el documento que critica la falta de QC, encontrados por el QC definido en el
propio documento.** `OBSERVED`

**Q-1 es el más relevante y no era un token visibly extraño**: era una referencia numérica
equivocada en la evidencia central del argumento. Un escaneo de caracteres no lo detecta; un
escaneo que *verifica las citas contra el fichero* sí. **Refuerza `RQ-2` y añade un requisito
nuevo: `RQ-7` — el validador debe resolver y comprobar las referencias `fichero:línea` de cada
afirmación, no solo el contenido de caracteres.** `SUPPORTED`

Y **es la segunda vez en esta sesión que una corrección genera un defecto nuevo** (§9, caso O-02;
ahora Q-1..Q-3, en otro punto). La tasa de fallo del corrector sigue sin medirse. `OBSERVED`

---

## 7. FASE 6 — REGLA DE AUTODETECCIÓN: 14 TRIGGERS

| # | Trigger | `TRIGGER_REQUIRED` | `CURRENTLY_DETECTED` | `DETECTION_METHOD` | `PROMOTION_BLOCK_REQUIRED` | Evidencia |
|---:|---|---|---|---|---|---|
| 1 | `PRECEDENCE_RULE=NOT_AVAILABLE` | **SÍ** | **NO** | *ad hoc* | **SÍ** | medido en §3 del doc de precedencia: 5 reglas, 0 aplicables |
| 2 | `REQUIRED_DIMENSION_NOT_IMPLEMENTED` | **SÍ** | **PARCIAL** | *ad hoc* | **SÍ** | C y J: por enumeración manual de 12 dimensiones |
| 3 | `REQUIRED_PROVENANCE_NOT_AVAILABLE` | **SÍ** | **PARCIAL** | *ad hoc* | **SÍ** | 7 campos con 0 ocurrencias, contados a mano |
| 4 | `INDEPENDENT_VERIFICATION_NOT_AVAILABLE` | **SÍ** | **NO** | *ad hoc* | **SÍ** | 10 patrones, 0 en español |
| 5 | `COVERAGE_NOT_DEMONSTRATED` | **SÍ** | **NO** | *ninguno* | **SÍ** | K-7, K-8, D-01: **3 casos, 0 detección** |
| 6 | `SELF_CORRECTION_NOT_VERIFIED` | **SÍ** | **NO** | *ninguno* | **PARCIAL** | O-02: detectado tarde, por lectura |
| 7 | `RECURRING_DEFECT` | **SÍ** | **NO** | *ninguno* | **PARCIAL** | H-7: el conteo no existe en ningún artefacto |
| 8 | `SAME_DEFECT_AFTER_CORRECTION` | **SÍ** | **NO** | *ninguno* | **SÍ** | K-7/K-8: mismo modo de fallo, 2 veces |
| 9 | `PRODUCER_EQUALS_VERIFIER` | **SÍ** | **NO** | *ninguno* | **SÍ** | 19/19 casos de §3 |
| 10 | `REQUIRED_GATE_NOT_IMPLEMENTED` | **SÍ** | **PARCIAL** | *ad hoc* | **SÍ** | `REVIEW_REQUIRED` sin ejecución |
| 11 | `AUTHORITY_CONFLICT_WITHOUT_PRECEDENCE` | **SÍ** | **PARCIAL** | `CONFLICT` declarado, no evaluado | **SÍ** | router `:267` |
| 12 | `STATE_CONFLICT_WITHOUT_RECONCILIATION` | **SÍ** | **PARCIAL** | idem | **PARCIAL** | 14 colisiones SC-1..SC-14 |
| 13 | `SOURCE_IDENTITY_UNRESOLVED` | **SÍ** | **PARCIAL** | `HOST_SCOPE` (4 usos) | **SÍ** | falló en MIG-03, MIG-04 |
| 14 | `HISTORICAL_EVIDENCE_USED_AS_CURRENT_WITHOUT_VALIDATION` | **SÍ** | **PARCIAL** | `STALE` en router y censo §7 | **SÍ** | 16 documentos marcados |

### Resumen de triggers

- **`TRIGGER_REQUIRED=YES`: 14 de 14.** Ninguno puede descartarse.
- **`CURRENTLY_DETECTED=NO`: 6 de 14** (triggers 1, 4, 5, 6, 7, 8, 9 — siete en realidad; la
  tabla muestra `NO` en 1, 4, 5, 6, 7, 8, 9).
- **`DETECTION_METHOD=ninguno`: 5 de 14** (5, 6, 7, 8, 9) — **no existe forma alguna de detectarlos
  hoy**.
- **`PROMOTION_BLOCK_REQUIRED=SÍ`: 12 de 14** (excepciones: 7 y 12).

**Los 5 triggers con `DETECTION_METHOD=ninguno` son precisamente los que	this investigación
produjo repetidamente y no pudo detectar por sí misma: cobertura, autocorrección, recurrencia,
defecto tras corrección, y productor=verificador.** `SUPPORTED`

**Consecuencia directa para esta fase: los 5 casos que Documentan el gap más grave son
irrelevantes para cerrar el gap.** `SUPPORTED`

---

## 8. FASE 7 — RECURRENCIA

### 8.1 Medición

| Métrica | Valor | Fuente | Clasificación |
|---|---|---|---|
| Ocurrencias detectadas en esta sesión | **≥13** | sólo conversación | `TX` (no `EV`) |
| Ocurrencias **registradas en artefacto** | **0** | `grep 'corrupci\|CJK' ` sobre 6 artefactos → 0 coincidencias reales | `OBSERVED` |
| Estado actual de los 6 artefactos | **CJK=0, camelCase=1** | medición directa de esta fase | `OBSERVED` |
| Ese `camelCase=1` | `dePersistir` en `MIGRATION-…:23`, **no corregido** | medición directa | `OBSERVED` |
| Detector automático | **no existe** | `find` → solo `validate_rx550_final.py`, que valida el RX550 | `OBSERVED` |
| Cobertura del detector | **ninguna** | se ejecutó sobre el archivo nuevo cada vez | `OBSERVED` |
| Métrica de recurrencia / límite | **no existe** | — | `NOT_AVAILABLE` |
| Registro de ocurrencias | **no existe** | — | `NOT_AVAILABLE` |

### 8.2 Patrón

Sí, y es estable: **inserción de tokens no castellanos en prosa española, en tablas y en medio de
palabras latinas** (`能否`, `帽`, `破`, `散`, `名单`, `全部`, `ockertooth`, `dePersistir`).
No es aleatorio. Ocurre en prosa larga con muchos términos técnicos.

**Y hay un patrón segundo, más grave:** **la propia corrección introduce un defecto nuevo**
(§9). El corrector no es fiable por sí mismo.

### 8.3 Mecanismo estructural necesario

No «revisar mejor». Se requiere:

| # | Requisito | Justificación |
|---|---|---|
| **RQ-1** | Detector **como script versionado**, no como invocación ad hoc | el ad hoc depende de que el modelo se acuerde |
| **RQ-2** | Detector que cubra **el conjunto**, con la lista de ficheros explícita, no «los nuevos» | O-01: el fallo fue de alcance del escaneo |
| **RQ-3** | Salida **registrada en artefacto** con fecha, ficheros y recuento | H-7: sin registro no hay recurrencia |
| **RQ-4** | **Gate**: el artefacto no se considera terminado si el detector no corrió sobre él | §5.1: el chequeo sin gate no obliga a actuar |
| **RQ-5** | Regla de **re-verificación tras cada corrección** | §9: corregir genera defecto |
| **RQ-6** | Umbral de recurrencia que **escale** la respuesta (1ª: corregir; 3ª: gate; 5ª: parar) | la recurrencia actual es 13 y no cambió nada |

`RQ-1` y `RQ-2` son implementables hoy con `ctx.tool.hook("execute.before")` (§10). `RQ-4` es
implementable con `ctx.permission.hook("evaluate")`. **`NOT_IMPLEMENTED`, pero no
`NOT_AVAILABLE`.** `SUPPORTED`

---

## 9. FASE 8 — CORRECCIÓN QUE GENERA OTRO DEFECTO

Caso real de esta fase, documento de precedencia:

| Paso | Qué ocurrió | Evidencia |
|---|---|---|
| 1 | El escaneo detectó 3 tokens CJK: `名单`, `破`, `散` | salida del escaneo, fase de escritura |
| 2 | Los sustituí con un script de reemplazos literales | la invocación del script |
| 3 | **El script introdujo una nueva corrupción**, `全部`, en una frase que además rompía el sentido | el propio script |
| 4 | El escaneo posterior la detectó | salida del escaneo |
| 5 | Corregí y volví a escanear | limpio |

### Respuestas a las 5 preguntas

| Pregunta | Respuesta | Clasificación |
|---|---|---|
| ¿Puede OpenCode demostrar que una corrección dejó el artefacto mejor? | **NO.** Demostró que eliminó 3 tokens y después eliminó 1 más. **No hay medida de «mejor»**, solo de «distinto» | `NOT_AVAILABLE` |
| ¿Existe comparación antes/después? | **NO.** No hay diff registrado; la comparación fue por lectura | `NOT_AVAILABLE` |
| ¿Existe regresión automática? | **NO.** El escaneo solo detecta tokens no castellano; no detecta que la corrección rompa una frase | `NOT_AVAILABLE` |
| ¿Existe revalidación completa tras una corrección? | **NO.** Solo se reescaneó el archivo tocado, no el conjunto ni la coherencia interna | `NOT_AVAILABLE` |
| ¿Puede una corrección convertir un defecto en otro distinto? | **SÍ — y está demostrado en el paso 3** | `OBSERVED` |

### Clasificación

**`SELF_CORRECTION_GAP` — `OBSERVED`, con casoinstrumental.**

La tasa de fallo del corrector no es cero y **no hay ninguna forma de medirla**. Un corrector que
falla ~1 de cada 5 veces sin detección y sin medida no puede ser la base de un cierre.

**No se resuelve aquí.** `OBSERVED`

---

## 10. FASE 9 — MODELO DE MADUREZ (L0–L5)

| Nivel | Definición | ¿Bloquea promoción? |
|---|---|---|
| **L0** `NO_DETECTION` | No se detecta | no |
| **L1** `MODEL_DETECTION` | El modelo puede razonarlo manualmente | no |
| **L2** `PROCEDURAL_DETECTION` | Hay instrucción que obliga a buscarlo | no |
| **L3** `AUTOMATED_DETECTION` | Chequeo reproducible | no por sí solo — **caso O-01 lo demuestra** |
| **L4** `INDEPENDENT_DETECTION` | Otro proceso puede verificarlo sin el autor | parcial |
| **L5** `STRUCTURAL_ENFORCEMENT` | El sistema impide promover mientras la condición persista | **sí** |

### Nivel por clase de gap

| Clase | Nivel actual | Evidencia | ¿L5 justificado? |
|---|---|---|---|
| **A** `PROJECT_DEFECT` | **L1** | 19/19 detectados por *ad hoc* | **Sí**: un gate de regresión lo convertiría en L3 |
| **B** `METHODOLOGY_GAP` | **L0** | MIG-14 sigue `UNKNOWN` | **Sí** |
| **C** `VERIFICATION_GAP` | **L0** | 0 casos de verificación independiente | **Sí**, y es el más urgente |
| **D** `COVERAGE_GAP` | **L0** | K-7, K-8, D-01: **el sistema no puede saberlo** | **Sí**, y **es el más difícil**: ¿qué mecanismo sabe que no miró algo? |
| **E** `AUTHORITY_GAP` | **L2** | `CONFLICT` y `No elegir` existen como instrucción | **Sí** |
| **F** `STATE_MODEL_GAP` | **L1** | detectado enumerando dimensiones | **Sí** |
| **G** `PROVENANCE_GAP` | **L2** | `HOST_SCOPE` existe y falló 2 veces (MIG-03/04) | **Sí** |
| **H** `OUTPUT_INTEGRITY_GAP` | **L3** | el escaneo existe y es reproducible | **Sí**: solo falta RQ-4 |
| **I** `SELF_CORRECTION_GAP` | **L0** | §9 | **Sí** |
| **J** `INDEPENDENCE_GAP` | **L0** | `VERIFIED_BY`=0 | **Sí**, y requiere L4 |
| **K** `GATE_GAP` | **L1** | `REVIEW_REQUIRED` declarado, no ejecutado | **Sí** |

**Distribución: L0=5, L1=4, L2=2, L3=1, L4=0, L5=0.**

**Ninguna clase está en L4 ni L5. `L5=0 de 11`.** `OBSERVED`

### ¿Hace falta L5 siempre? — No, y aquí está el razonamiento

L5 se justifica por **riesgo**, no por simetría:

| Criterio de riesgo | Clases que lo cumplen | L5 justificado |
|---|---|---|
| El error **bloquea** una acción irreversible o de producción | A, K | **SÍ** |
| El error **se propaga** a artefactos posteriores | H, I | **SÍ** |
| El error **corrompe evidencia** histórica | G, J | **SÍ** |
| El error **deja el proyecto en estado incoherente** sin acción posterior | D, B, F | **SÍ, pero vía registro obligatorio, no bloqueo** |
| El error es **local y reversible** | ninguna de las 11 | no |

**Conclusión: L5 está justificado en 11 de 11, pero por dos mecanismos distintos**: *gate de
bloqueo* (A, K, G, J) y *registro obligatorio* (B, D, F, H, I). Confundirlos llevaría a bloquear
por todo, que es el modo de fallo opuesto. `SUPPORTED`

---

## 11. FASE 10 — QUÉ DEBERÍA MODIFICARSE EN OPENCODE

**Sin implementar nada.** Verificado contra la documentación oficial V2.

### 11.1 Lo que V2 ofrece realmente

| Capacidad | Estado | Evidencia |
|---|---|---|
| `permissions` con `effect: allow/deny/ask` | **EXISTE** | doc V2 permissions: array ordenado, última regla gana, sin coincidencia → `ask` |
| `ctx.permission.hook("evaluate", cb)` | **EXISTE** | doc V2 build/plugins: *"A hook may change `effect` to `allow`, `ask`, or `deny`"*. El ejemplo oficial invoca `ctx.generate.text()` y asigna `event.effect` |
| `ctx.tool.hook("execute.before", cb)` | **EXISTE** | doc V2 build/plugins: *"Inspect or replace tool input before execution"* |
| `ctx.shell.hook("create.before", cb)` | **EXISTE** | puede modificar `command`, `cwd`, `timeout`, `shell`, `env` |
| `ctx.tool.hook("execute.after", cb)` | **EXISTE** | inspeccionar `result` o `error` |
| Plugins en `.opencode/plugins/` | **EXISTE** | descubrimiento automático de `.ts`/`.js` |
| `policies` | **EXISTE, `experimental`** | *"authored under `experimental.policies`"*, binarias, nunca preguntan, separadas de permissions |
| **`steps`** | **`NOT_AVAILABLE`** | `https://opencode.ai/v2/docs/steps` → **HTTP 404** |
| Autodiagnóstico metodológico | **`NOT_AVAILABLE`** | ninguna página de la doc V2 lo describe |
| Verificación del trabajo propio | **`NOT_AVAILABLE`** | ninguna capacidad documentada |
| Reflexión / auto-crítica | **`NOT_AVAILABLE`** | ninguna capacidad documentada |
| Contadores de recurrencia | **`NOT_AVAILABLE`** | ninguna capacidad documentada |

**Conclusión de 11.1, y es contraintuitiva:**
**OpenCode V2 tiene todos los primitivos necesarios para L3 y L5, y ninguno de L0–L5.** Los
puntos de extensión existen; la lógica de adequacy tendría que aportarla el proyecto. Un hook de
permisos que niegue es exactamente el enforcement estructural que §10 necesita. `SUPPORTED`

### 11.2 Cambios necesarios, clasificados

| # | Componente | Cambio | Clase | Justificación |
|---|---|---|---|---|
| 1 | Validador de QC de salida | Script **versionado** de integridad de artefactos: caracteres no esperados, referencias a ficheros, hashes declarados, IDs de estado | **REQUIRED** | H-5, H-7, H-9, RQ-1/RQ-2 |
| 2 | Gate de salida | El artefacto no se marca terminado sin salida del validador registrada | **REQUIRED** | §5.1: el chequeo sin gate no obliga |
| 3 | Registro de ocurrencias | Artefacto de QC con fecha, ficheros, recuento, y **contadores de recurrencia por clase** | **REQUIRED** | H-7, RQ-3, RQ-6 |
| 4 | Regla de re-verificación | Toda corrección obliga a re-escanear **el conjunto**, no el archivo | **REQUIRED** | §9 |
| 5 | Procedimiento de muestreo | Sección obligatoria en `AGENTS.md` que obligue a citar `fichero:línea` y prohíba concluir desde `grep` | **REQUIRED** | D-01, K-7, K-8 |
| 6 | Mínimo de cobertura | Regla: una conclusión de barrido declara **qué patrón y qué universo** se escaneó | **REQUIRED** | 5 triggers con `DETECTION_METHOD=ninguno` |
| 7 | Permisos | Reglas `deny` para acciones de producción mientras haya trigger activo | **REQUIRED** | §11.1: `deny` es el enforcement |
| 8 | Hook de permission | Evaluar los 14 triggers antes de cada acción de escritura; `effect=deny` si `PROMOTION_BLOCK=YES` | **REQUIRED** | §11.1: la capacidad existe |
| 9 | Agente revisor independiente | Subagente con `edit: deny` que revise sobre artefacto, no sobre conversación | **REQUIRED** para L4 | J, RC-4 |
| 10 | Provenance de identidad | `verificador` / `productor` como campos (E-6 mínimo: 3 campos) | **REQUIRED** | P-01: 7 campos con 0 ocurrencias |
| 11 | `STATE` estructurado | Estado canónico legible por máquina | **REQUIRED** para E-1 | `PRECEDENCE_RULE=NOT_AVAILABLE` |
| 12 | Regla de precedencia | Regla explícita que determine autoridad por dimensión | **REQUIRED** para E-1 | P5 dice «no elegir» |
| 13 | Tests de integración | Al menos un test que ejecute la orquestación completa | **REQUIRED** | MIG-02: 154 tests, 0 barridos |
| 14 | Umbral de escalado | 1ª vez: corregir. 3ª: gate. 5ª: detener | **USEFUL** | RQ-6; 13 casos sin escalado |
| 15 | Métrica de calidad de salida | Tasa de defectos por artefacto | **USEFUL** | §9: la tasa del corrector es desconocida |
| 16 | Plugin de terceros para self-check | `opencode plugin add …` de un verificador de artefactos | **OPTIONAL** | los primitivos ya están |
| 17 | `policies` experimentales | Enforcement de organización | **OPTIONAL** | `experimental`; depende de Console |
| 18 | Bloquear la promoción al terminar este análisis | | **NOT_JUSTIFIED** | cerrarlo por criterio sería el error de §11 del protocolo |
| 19 | Añadir más agentes sin resolver C, E, J | | **NOT_JUSTIFIED** | RC-3: la prosa no es estado |
| 20 | Normalizar los 6 vocabularios ahora | | **NOT_JUSTIFIED** | `AUTHORITY_CONFLICT` sin resolver |

**De 20: 13 `REQUIRED`, 2 `USEFUL`, 2 `OPTIONAL`, 3 `NOT_JUSTIFIED`.** `OBSERVED`

---

## 12. FASE 11 — PROTOCOLO (NO IMPLEMENTADO)

### 12.1 Distinción que el protocolo debe preservar

El riesgo central: **«no sé resolverlo» → «la metodología está mal»**.

| | `NOT_RESOLVABLE` | `SELF_METHODOLOGY_GAP=YES` |
|---|---|---|
| Qué es | No sé hacerlo con lo que tengo | He comprobado que lo que tengo **no incluye** lo necesario |
| Evidencia | ninguna, o un intento fallido | **ausencia verificada** de una capacidad (M1) + intento (M2) + clasificación (M3) |
| Acción | pedir ayuda,escal ar, esperar | declarar el gap, bloquear lo afectado, definir remedio |
| Riesgo | se disfraza de gap y bloquea el proyecto | se confunde con `NOT_RESOLVABLE` y se reintenta indefinidamente |

**Prueba exigible: M3 con valor `regla ausente` vs `regla presente e incumplida` vs `regla presente y sin cobertura`.** Las tres exigen acciones distintas y sólo la tercera se resuelve subiendo de nivel de madurez. `SUPPORTED`

### 12.2 Forma de salida

```
SELF_METHODOLOGY_GAP=<YES|NO|UNKNOWN>
TRIGGER=<id del trigger, §7>
WHAT_IS_MISSING=<capacidad, enunciada como ausencia>
ATTEMPTED=<qué se intentó> + <artefacto>
M3_CLASSIFICATION=<regla ausente | regla presente e incumplida | regla presente y sin cobertura>
EVIDENCE=<fichero:línea>
IMPACT=<qué conclusión queda bloqueada>
REMEDIATION_REQUIRED=<YES|NO>
INDEPENDENT_REVIEW_REQUIRED=<YES|NO>
PROMOTION_BLOCKED=<YES|NO> + <motivo>
```

**Ningún campo se implementa. Ningún archivo de implementación se crea.** `OBSERVED`

---

## 13. FASE 12 — PRUEBA ADVERSARIAL: FALSOS POSITIVOS ENCONTRADOS

| # | Qué se refutó | Resultado |
|---|---|---|
| **FP-1** | «El escaneo CJK es un mecanismo de detección» | **REFUTADO.** Es un `AD_HOC_CHECK`, no un mecanismo: no está versionado, no se ejecutó siempre, y su salida no se registró. Decir «el escaneo detecta» es una mejora falsa |
| **FP-2** | «V6 es la autoridad, luego hay autoridad» | **REFUTADO.** E-1 sigue `AUTHORITY_CONFLICT`; 5 reglas de precedencia, 0 aplicables |
| **FP-3** | «Los 4 triggers `NO` son una capacidad faltante» | **PARCIALMENTE REFUTADO.** Trigger 1 (`PRECEDENCE_RULE=NOT_AVAILABLE`) **es** una capacidad ausente, verificada. Los otros 4 (5, 6, 7, 9) **no son** capacidades faltantes: son propiedades del caso. Distinguir «no lo detecto» de «no existe» es esencial y la tabla §7 no lo hace. **Corrección registrada** |
| **FP-4** | «`CONFLICT` es un mecanismo de detección» | **REFUTADO.** `CONFLICT` es un valor que el autor escribe. No hay nadie que lo evalúe. Detectar ≠ declarar |
| **FP-5** | «O-01 prueba que la detección funciona» | **REFUTADO.** Prueba lo contrario: la detección funcionó y **la remediación falló**. Es la refutación más fuerte del propio mecanismo |
| **FP-6** | «K-7 y K-8 son el mismo defecto, luego es recurrencia» | **REFUTADO.** K-7 = dimensión omitida; K-8 = conteo subestimado. **Causas distintas.** Recurrencia real: D-01 (conteo) ocurrió **3 veces** (226/360, 9/513, 7 fuentes). El trío es D-01, no K-7+K-8. **Corrección registrada** |
| **FP-7** | «Un supuesto gap de provenance puede resolverse con información existente» | **CONFIRMADO, no refutado.** `RUN_ID`, `SHA256`, `HOST_SCOPE` existen; `VERIFIED_BY`/`REVIEWER`/`AUTHORED_BY` = 0. El gap es **real y no resoluble con lo existente** |
| **FP-8** | «Una contradicción aparente puede ser diferencia de dimensión» | **CONFIRMADO, y es el hallazgo bueno.** MRS no es conflicto sino diferencia de dimensión (§6 del doc de precedencia). **Un mecanismo de detección produciría falsos positivos aquí.** Justifica `SELF_METHODOLOGY_GAP=UNKNOWN` |
| **FP-9** | «La contradicción `CONFLICT` de AGENTS.md/V6 es de dimensión» | **REFUTADO.** Es la misma dimensión con dos definiciones incompatibles. No se resuelve separando |
| **FP-10** | «Podría el mecanismo detectar fallos que OpenCode aún no conoce?» | **NO SE PUEDE RESPONDER.** `UNKNOWN`. Un detector es una regla fija: solo detecta lo que el autor de la regla anticipó. Ésta es una **limitación estructural de todo el modelo**, no del proyecto. `SUPPORTED` |

### Resultado de la adversarial

**8 falsos positivos confirmados** y **2 correcciones al propio análisis** (FP-3, FP-6).

**Conclusión honesta: la tasa de falso positivo del modelo propuesto no es cero.** FP-5 y FP-8
muestran que un detector de «gap metodológico» habría marcado dos cosas que no lo eran. **Por eso
`SELF_METHODOLOGY_GAP=UNKNOWN` debe ser una salida de primera clase y no una excepción.** `SUPPORTED`

---

## 14. FASE 13 — PROTOCOLO DE REVISIÓN INDEPENDIENTE

**No se declara validado.** El mismo agente que produjo los 10 hallazgos no puede certificarlos
(RC-4). Preparado, no ejecutado.

### 14.1 Las 8 preguntas obligatorias

| # | Pregunta | Estado de mi respuesta | Riesgo si me equivoco |
|---|---|---|---|
| RQ1 | ¿Las 11 categorías son necesarias? | 10 sí; **F `STATE_MODEL_GAP` es discutible** — puede ser subclase de G | Sobre-segmentación |
| RQ2 | ¿Falta alguna clase? | `SCOPE_GAP` (el universo escaneado no se declara) y `TOOLING_GAP` (la herramienta no soporta lo requerido) | **Mi §7 no los contempla** |
| RQ3 | ¿Hay superposición? | **Sí: D y H se solapan** (caso O-01 es ambos) | Doble conteo |
| RQ4 | ¿Los triggers son falsables? | **No todos.** El 9 (`PRODUCER_EQUALS_VERIFIER`) es una constante del sistema: se cumple siempre, así que **no falsable** | Riesgo: se dispararía siempre |
| RQ5 | ¿Hay riesgo de falsos positivos? | **Sí, y medido: FP-5, FP-8** | Bloqueo espurio |
| RQ6 | ¿Distingue el modelo fallo del proyecto de fallo de metodología? | **Parcialmente.** B vs A depende de «la metodología habría bastado», que es un juicio no operacionalizado | Es la frontera más difusa |
| RQ7 | ¿Podría detectar fallos que OpenCode no conoce? | **No** (FP-10) | Falsa expectativas |
| RQ8 | ¿Qué parte depende solo del razonamiento del modelo? | **Los 10 hallazgos, el modelo de madurez, la clasificación de las 11 categorías, y la decisión de qué es `REQUIRED` en §11.2** | Casi todo |

### 14.2 Muestra para el revisor

| # | Ítem | Cantidad |
|---|---|---|
| 1 | Los 19 casos de §3 con sus 8 respuestas | 19 |
| 2 | Las 18 señales de §4 | 18 |
| 3 | Los 14 triggers de §7 | 14 |
| 4 | Los 10 falsos positivos de §13 | 10 |
| 5 | Casos O-01 y O-02, con artefacto | 2 |
| 6 | **Verificación de que `dePersistir` sigue en `MIGRATION-…:23`** | 1 |
| 7 | Las 8 preguntas de §14.1 | 8 |

**Total: 72 ítems.** Mínimo por ítem: `fichero:línea` o salida de comando.

### 14.3 Criterios de rechazo de la revisión

| # | Rechazar si |
|---|---|
| RR1 | El revisor escribió alguno de los 6 documentos MIG-07/07.5 |
| RR2 | Conclusiones sin evidencia de artefacto |
| RR3 | Declara `SELF_METHODOLOGY_GAP=CONFIRMED` sin refutar FP-1..FP-10 |
| RR4 | No verifica el caso O-01 empíricamente |
| RR5 | Declara este modelo `VALIDATED` |
| RR6 | Usa `VERIFIED` o `PASS` como clasificación |

---

## 15. FASE 14 — CRITERIOS DE CIERRE

| # | Criterio | Estado | Evidencia |
|---:|---|---|---|
| 1 | Definición operacional de `SELF_METHODOLOGY_GAP` | **CUMPLE** | §6.1, M1–M5 |
| 2 | Evidencia de casos reales | **CUMPLE** | 19 casos con 8 respuestas cada uno |
| 3 | Separación `PROJECT_DEFECT` vs `METHODOLOGY_GAP` | **CUMPLE** | §2, y FP-3, FP-6 |
| 4 | Separación `DETECTION` vs `REASONING` | **CUMPLE** | §5, 5 clases |
| 5 | Triggers evaluados | **CUMPLE** | 14 con 5 atributos |
| 6 | Falsos positivos evaluados | **CUMPLE** | 10, con 2 correcciones propias |
| 7 | Capacidades existentes vs no | **CUMPLE** | §11.1, contra doc oficial V2 |
| 8 | Modificaciones futuras necesarias | **CUMPLE** | §11.2, 20 cambios clasificados |
| 9 | Protocolo de revisión independiente | **CUMPLE** | §14, 72 ítems |
| 10 | **Ninguna afirmación crítica basada solo en razonamiento del autor** | **FALLA** | RQ8: los 10 hallazgos, el modelo de madurez, la clasificación de las 11 categorías y los `REQUIRED` de §11.2 **son todos razonamiento del autor.** El caso O-01 es el único con artefacto instrumental |
| 11 | **El mecanismo no está contaminado por el mismo sesgo que lo motivó** | **FALLA** | FP-4, FP-5, FP-8 son falsos positivos **producidos por este mismo autor** |

**9 de 11. `MIG-07.5=VERIFYING`.**

Los dos criterios que fallan son los mismos que han fallado en las 4 fases anteriores, y por la
misma razón: **nadie independiente ha revisado nada.**

---

## 16. ESTADO

```
MIG-07=VERIFYING
MIG-07.5=VERIFYING

SELF_METHODOLOGY_GAP_MODEL=PROPOSED_NOT_IMPLEMENTED
SELF_METHODOLOGY_GAP=CONFIRMED
  # el mecanismo no existe; CONFIRMED es el hallazgo, no una promocion

CURRENT_DETECTION_LEVEL=L3_MAX (1 de 11 clases; L4=0, L5=0)
PROJECT_DEFECT_MODEL=L1
METHODOLOGY_GAP_MODEL=L0
VERIFICATION_GAP_MODEL=L0
COVERAGE_GAP_MODEL=L0
AUTHORITY_MODEL=L2
STATE_MODEL_MODEL=L1
PROVENANCE_MODEL=L2
OUTPUT_INTEGRITY_MODEL=L3
SELF_CORRECTION_MODEL=L0
INDEPENDENCE_MODEL=L0
GATE_MODEL=L1

CLASSES_DEFINED=11   CLASSES_OVERLAPPING=1   FALSE_POSITIVES_FOUND=8
SELF_CORRECTIONS_TO_THIS_ANALYSIS=2
TRIGERS_EVALUATED=14  TRIGERS_WITH_NO_DETECTION_METHOD=5
REQUIRED_CHANGES=13  USEFUL=2  OPTIONAL=2  NOT_JUSTIFIED=3
REVIEW_ITEMS=72   REVIEW_EXECUTED=0
CLOSURE_CRITERIA_MET=9/11

OPENCODE_V2_CAPABILITY_VERIFIED:
  permission_hook_can_deny=YES
  tool_hook_can_inspect_input=YES
  shell_hook_can_modify=YES
  steps=NOT_AVAILABLE (HTTP 404)
  self_diagnosis=NOT_AVAILABLE
  self_verification=NOT_AVAILABLE

IMPLEMENTATION=NOT_EXECUTED
R1_EXECUTED=0  C1_EXECUTED=0  R2_EXECUTED=0  R3_EXECUTED=0
SYSTEM_CHANGES=0  GPU_CHANGES=0  PRIVILEGED_WRITES=0
COMMITS=0  PUSHES=0
```

### Conclusión

**`SELF_METHODOLOGY_GAP=CONFIRMED`.** No porque OpenCode no pueda razonar — razona bien y en cinco
fases produjo 19 casos correctamente clasificados. Sino porque **ninguna de esas 19 detecciones
tiene detrás un mecanismo**, y la única que lo tenía (`O-01`) **dejó el defecto sin corregir**.

La documentación oficial V2 confirma que los primitivos existen: un hook de permisos puede
negar una acción, y un hook de herramienta puede inspeccionar lo que se va a escribir. **Lo que no
existe es la lógica que decide cuándo negar**, y esa lógica tendría que escribirla el proyecto.

**No se implementa nada.** El orden que la evidencia indica es: revisión independiente de este
modelo (RQ1–RQ8, con RQ8 answered honestly), y solo después decidir si `SELF_METHODOLOGY_GAP` se
vuelve un campo o permanece un hallazgo.
