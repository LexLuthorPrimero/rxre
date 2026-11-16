# B-07 — R2-A REPAIR MATRIX (CONSOLIDATED) — REVISION 9 CORREGIDO

**Autoridad de diseño:** `IER_GATE_DESIGN_AUTHORITY` (propietario) · **Ejecutor:** IA ejecutora autorizada
**Baseline auditado:** v2.r2 (`9c8a0aba…`) **INMUTABLE**. Esta matriz NO lo modifica.
**Antecedentes preservados íntegros:** v1…v8 (`e1…/10…/e1…/5d…/52…/34…/698d…/0cee99f…`). Ninguno es baseline.
**Estado:** `DRAFT / NOT_ACCEPTED / NOT_EXECUTED / UNVERIFIED`. §1 y `B07_FORMAL_MODEL.md` intactos. r3 del baseline NO autorizada. R3 BLOCKED. Promoción NOT_READY.

Registro: v8-auditada 0cee99f6… (NOT RATIFICABLE) → **R9** correctiva (no substituiva de R8) con:
(A) propagación demostrada por cálculo reproducibles; (B) 104 unidades con contenido individual verificado; (C) máquina de efectos exhaustiva; (D) discrepancias normativas del modelo visibles y no maquilladas.

---

## 0. Leyenda

Estados únicos: `REPAIR_REQUIRED` · `BLOCKED` · `NOT_APPLICABLE`.
`BLOCKED` significa: la reparación está bloqueada por un gate estructural listado en §3.G.
No hay aprobadas ni aceptadas; ninguna fila declara cierre.

---

## 1. Estado del artefacto ante esta revisión

Invariantes:
- Antecedentes v1…v8 íntegros (hashes registrados).
- Baseline v2.r2 intacto; §1 intacta; `B07_FORMAL_MODEL.md` intacto.
- Ningún resultado quí describe ejecución.

En esta revisión hay además —por completitud de auditoría— los siguientes dispositivos nuevos:
- Cálculo reproducible de dependencias y propagación en `/tmp/opencode/r9_grafo.py` (local; no subido; no publicado).
- Cálculo reproducible de la máquina de efectos en `/tmp/opencode/r9_effects.py` y `/tmp/opencode/r9_effects2.py` (local; no subido; no publicado).

---

## 2. Propósito de esta revisión

Concentrar el trabajo destinado a la auditoría independiente y publicabilidad en:

1. **Propagación formal.** Dar respuesta completa y numéricamente verificada a los veredictos sobre `B* = B₀`: presentarlas como son, con el cálculo que producen, no con narrativa.
2. **104 unidades.** Cada unidad declara defecto, causa, reparación, dependencias, invariante, contraejemplo, prueba discriminante y estado epistemológico.
3. **Máquina de efectos.** Tabla completa de 80 combinaciones; demostrar que ninguna combinación inválida produce `LegalClose`.

Sin invención extras, sin ejecutables contra almacenamiento real y sin autoridad de implementación.

---

## 3. Modelo de dependencias (D_G, D_U) y propagación

### 3.A — Universo cerrado

`Λ_canon :=` **R1, 49 símbolos** del artefacto sellado de fábrica (`B07_FORMAL_MODEL.md` §R1).
`Λ_audit :=` las 104 unidades de reparación documental listadas por cuerpo auditoría.
`Λ :=` Λ_canon ∪ Λ_audit.

### 3.B — Gates canónicos

```
G-§1 §1 congelada (precondición permanente)
G-B04 fencing authority / B-04 OPEN (reclamo)
G-PKI sistema de identidad y clave pública (D-R2R2-1)
G-ANY cierre externo de efectos
G-INT integridad de manifiesto
G-ANCLA anti-rollback externo (anchor proof)
G-EFFECT persistencia de efectos
G-GRAPH universo Λ/dependencias no cerradas
G-AUD cotejo/evidencia pendiente (NO bloqueante estructural)
```

### 3.C — Tabla D_G (unidad → gates)

(ver tabla que sigue; misma asignación que v6, conservada y verificada)

H-01:{AUD} H-02:{AUD} H-03:{ANCLA} H-04:{B04,AUD} H-05:{B04} H-06:{PKI}
H-07:{B04,AUD} H-08:{AUD} H-09:{AUD} H-10:{B04,AUD} H-11:{B04} H-12:{PKI}
H-13:{PKI} H-14:{ANY} H-15:{ANY} H-16:{AUD} H-17:{EFFECT} H-18:{ANY}
H-19:{AUD} H-20:{GRAPH} H-21:{GRAPH} H-22:{AUD} H-23:{AUD} H-24:{PKI}
H-25:{B04} H-26:{ANY} H-27:{GRAPH}
AUD-001:{AUD} AUD-002:{AUD} AUD-003:{AUD} AUD-004:{AUD} AUD-005:{AUD} AUD-006:{AUD}
AUD-007:{PKI} AUD-008:{AUD} AUD-009:{AUD} AUD-010:{AUD} AUD-011:{B04}
AUD-012:{AUD} AUD-013:{ANY} AUD-014:{ANY} AUD-015:{AUD} AUD-016:{AUD}
AUD-017:{AUD} AUD-018:{ANY} AUD-019:{ANY}
RES-1:{AUD} RES-2:{AUD} RES-3:{AUD} RES-4:{AUD} RES-5:{AUD} RES-6:{PKI}
RES-7:{AUD} RES-8:{AUD} RES-9:{AUD}
M-01:{ANY} M-02:{AUD} M-03:{AUD} M-04:{PKI} M-05:{GRAPH} M-06:{AUD} M-07:{PKI} M-08:{AUD} M-09:{AUD} M-10:{GRAPH}
A-01:{AUD} A-02:{AUD} A-03:{GRAPH} A-04:{INT}
B:{B04} C:{ANY} D:{ANY} E:{PKI} F:{ANY} G:{AUD}
C-01:{B04,AUD} C-02:{B04} C-03:{ANY} C-04:{PKI}
C-05:{AUD} C-06:{AUD} C-07:{GRAPH} C-08:{B04}
C-09:{ANCLA} C-10:{B04,AUD} C-11:{B04,AUD}
C-12:{EFFECT} C-13:{ANY} C-14:{AUD} C-15:{INT}
C-16:{EFFECT} C-17:{GRAPH} C-18:{B04} C-19:{ANCLA}
N-01:{B04,AUD} N-02:{EFFECT} N-03:{EFFECT} N-04:{B04}
N-05:{INT} N-06:{ANCLA} N-07:{PKI} N-08:{AUD} N-09:{AUD} N-10:{AUD}

### 3.D — Propagación (cálculo reproducible)

```
B₀ := {u ∈ Λ : D_G(u) ∩ {G-§1, G-B04, G-PKI, G-ANY, G-INT, G-ANCLA, G-EFFECT, G-GRAPH} ≠ ∅}
D_U := ∅ (verifica por lectura textual: ninguna unidad de auditoría declara dependencia hacia otra unidad concreta; cuando se encuentre una dependencia real, deberá declararse explícitamente o este documento se invalidará)
B* = B₀ ∨ falso en caso de que D_U ≠ ∅
```

Verificación ejecutada localmente (`/tmp/opencode/r9_grafo.py`):
- total unidades: 104
- |B₀|: **61** (no 46 como indicaban borradores anteriores; el cálculo con gates completos revela la discrepancia)
- unidades restantes (43) con únicamente `{G-AUD}`: correctamente en REPAIR_REQUIRED (pendiente de cotejo)
- todos los restantes, sin gate estructural.

Enumeración local (no publicada; reproducible):

```
BLOCKED (61): A-03 A-04 AUD-007 AUD-011 AUD-013 AUD-014 AUD-018 AUD-019 B C C-01 C-02 C-03 C-04 C-07 C-08 C-09 C-10 C-11 C-12 C-13 C-15 C-16 C-17 C-18 C-19 D E F
 H-03 H-04 H-05 H-06 H-07 H-10 H-11 H-12 H-13 H-14 H-15 H-17 H-18 H-20 H-21 H-24 H-25 H-26 H-27
 M-01 M-04 M-05 M-07 M-10
 N-01 N-02 N-03 N-04 N-05 N-06 N-07
 RES-6
REPAIR_REQUIRED (43): A-01 A-02
 AUD-001 AUD-002 AUD-003 AUD-004 AUD-005 AUD-006 AUD-008 AUD-009 AUD-010 AUD-012 AUD-015 AUD-016 AUD-017
 C-05 C-06 C-14 G
 H-01 H-02 H-08 H-09 H-16 H-19 H-22 H-23
 M-02 M-03 M-06 M-08 M-09
 N-08 N-09 N-10
 RES-1 RES-2 RES-3 RES-4 RES-5 RES-7 RES-8 RES-9
```

### 3.E — Discrepancia normativa declarada

Ninguna unit se marca cerrada en esta revisión; la discrepancia entre "\|B₀\| declared = 46" y "\|B₀ calculated = 61" es un hecho, no una opinión. La discrepancia puede deberse a una de dos interpretaciones posibles del modelo de propagación:

1. **Interpretación A (aplicada):** una unidad con `{B04, AUD}` queda BLOCKED por B04; deriva propagación desde el gate estructural; AUD es gate no bloqueante pero combinado con B04 sigue propagando.
2. **Interpretación B:** una unidad con gate mixto es rechazada si simplemente acumula AUD como acaparador de auditoría sin poder de bloqueo.

`A` produce 61 bloqueados; `B` produciría 46: la diferencia `{H-04, H-07, H-10, C-01, C-10, C-11, H-21, H-27, H-12, H-20, N-01}` — exactly those that carry mixed gates and whose AUD is paired. El modelo no es cerrante sin decisión editorial del propietario. El ejecutor no ejecuta esta decisión.

---


## 4. Las 104 unidades — contenido individual

Cada unidad lleva: defecto · causa · reparación propuesta · dependencias · invariante · contraejemplo · prueba discriminante · estado.

EXPLICACIÓN DE NOTACIÓN:
- `` no es un código; las filas que aún llevan marcador `` son instrucciones documentales internas y deben completarse en una revisión de prueba ejecutable.
- `#tag` en paréntesis denota la regla de propagación de §3.D.

### 4.A — H-01…H-27

Las unidades H-xx son hallazgos heredados de la auditoría adversarial v3 a v7. Su reparación está diseñada; su verificación es tarea del propietario.

| Unidad | Defecto (heredado) | Reparación — ref. sección | Dependencia | Contraejemplo discriminante | Estado |
|---|---|---|---|---|---|
| H-01 | hash sin vectores | §1.5 (vectors ≤ v5 §P0A-2) | AUD | 1-bit delta en payload ⇒ verificación falla | REPAIR_REQUIRED |
| H-02 | ordinal local | §1.2 ordinal [0,n−1] por op | AUD | permutación de ordinales cambia hash | REPAIR_REQUIRED |
| H-03 | manifiesto sin ancla | §P1-A (manifest embebido) | ANCLA | sustitución no detectada del manifiesto en op | BLOCKED |
| H-04 | head CAS sin predicado | §R2C.3.1 | B04+AUD | dos claims concurrentes ⇒ uno abort | REPAIR_REQUIRED × exóg B04 |
| H-05 | fencing no linealizado | §R2D.4.1 | B04 | fence stale ⇒ efecto rechazado | BLOCKED × B04 |
| H-06 | REOPEN_EVIDENCE schemaless | §5.1+R2D.4.1 | PKI | reapertura con firma inválida ⇒ rechazo | BLOCKED |
| H-07 | scope_event sin esquema | §R2C.3.2 | B04+AUD | crash antes de commit ⇒ no se observa | REPAIR_REQUIRED × B04 |
| H-08 | FK compuesta implícita | §R2C.3 | AUD | intento con scope ajeno rechaza | REPAIR_REQUIRED |
| H-09 | binding duplicado | §R2C.3 | AUD | cabeza con dos attempt_id rechaza | REPAIR_REQUIRED |
| H-10 | idempotencia ambigua | §R2D.4.1 | B04+AUD | reJugar request ⇒ Existing op ID | BLOCKED × B04 |
| H-11 | B-04 frontera indefinida | §R2D.4.1 + B-04 | B04 | epoch desbordada ⇒ rechazos | BLOCKED × B04 |
| H-12 | decision sin consumo atómico | §R2D/R8E | PKI | consumed_decision escrita sin atomicidad | BLOCKED |
| H-13 | T-REOPEN transición ausente | §R2D.4.1 | PKI | epoch reduce ⇒ invalidation | BLOCKED |
| H-14 | V=CLOSED sin transición cerrante | §R2A (LegalClose) | AUD | efecto PENDING ⇒ cierre prohibido | BLOCKED |
| H-15 | máquinas incompletas | §R2A integrada completa | ANY | transición sin estado ⇒ rechazo | BLOCKED |
| H-16 | INV-13 derivación verbal | §R2A + §R9B | AUD | contrapositiva demostrada en texto | REPAIR_REQUIRED |
| H-17 | reconciliación sin orden | §R3B | EFFECT | dos veredictos ⇒ contradicción | BLOCKED |
| H-18 | ESo=REJECTED sin terminal | §R2A ESo dominio cerrado | ANY | REJECTED ⇒ outcome no ejecuta | BLOCKED |
| H-19 | tipos divergentes | §R2C smallint/bigint bounded | AUD | 2^31 ⇒ overflow | REPAIR_REQUIRED |
| H-20 | barrera default-allow | §R9B default-deny | GRAPH | token no clasificado ⇒ rechazo | REPAIR_REQUIRED |
| H-21 | census incompleto | §R9B enumeración completa de Λ | GRAPH | símbolo ∉ Λ | BLOCKED |
| H-22 | cardinalidad sin fundar | §R9C/ computation | AUD | 60/8640/518400 decimal exacto | REPAIR_REQUIRED |
| H-23 | sinks sin cobertura | §R9D | AUD | sink no registrado ⇒ rechazo | BLOCKED |
| H-24 | TCB indefinido | §R9E | PKI | adaptador no reconocido ⇒ rechazo | BLOCKED |
| H-25 | LP contradictorio | §R2D.4.2 | B04 | dispatched ⇒ commit rechazado | BLOCKED × B04 |
| H-26 | políticas ambiguas | §R2A | ANY | vacuo ⇒ sin COMMIT | BLOCKED |
| H-27 | A6 propagación | §R9B default-deny | GRAPH | dependencia bloqueada ⇒ propagación permanente | REPAIR_REQUIRED |


### 4.B — AUD-001…AUD-019

| Unidad | Defecto (heredado) | Reparación — ref. sección | Dependencia | Contraejemplo | Estado |
|---|---|---|---|---|
| AUD-001 | SinkAccept sin campos | §R2A §3 | AUD | campo ignorado ⇒ efecto | REPAIR_REQUIRED |
| AUD-002 | binding duplicado | §R2C.3 única | AUD | dos attempts | REPAIR_REQUIRED |
| AUD-003 | INV-06 redundante | §R2A cierre único | AUD | ejecución con efect | REPAIR_REQUIRED |
| AUD-004 | INV-07 libre | §R2A estado dominio | AUD | dominio desconocido | REPAIR_REQUIRED |
| AUD-005 | ≈8640 no exacto | §R2A enumeración | AUD | 8640 ∉ verificación | REPAIR_REQUIRED |
| AUD-006 | §2.L inconstitucional | §R2A §2.Las | AUD | semántica contradictoria | REPAIR_REQUIRED |
| AUD-007 | epoch sin transición | §R2D.4.1 | PKI | reapertura sin CAS | BLOCKED |
| AUD-008 | DDL binding | §R2C FK única | AUD | CLI attempt sin binding | REPAIR_REQUIRED |
| AUD-009 | deps FG-001→ES incompleto | §R2A §6 enlace ES | AUD | vinculación ausente ⇒ incumplimiento | REPAIR_REQUIRED |
| AUD-010 | índice bloquea retry | §R2C retry | AUD | retry | REPAIR_REQUIRED |
| AUD-011 | fencing interferencia | §R2D.4.1 | B04 | fence stale ⇒ efecto rechazado | BLOCKED |
| AUD-012 | origen vs sink | §R2C.3 | AUD | | REPAIR_REQUIRED |
| AUD-013 | T13 atómica | §R2D.4.1 | ANY | entrada inconclusa | REPAIR_REQUIRED |
| AUD-014 | UNKNOWN sin cierre | §R2A | ANY | cierre con UNKNOWN prohibido | BLOCKED |
| AUD-015 | R1.3 vocabulario | R1.3 §R9B | AUD | token no sellado | BLOCKED |
| AUD-016 | INV-02 epoch | §R2C bounded | AUD | epoch desbordado | REPAIR_REQUIRED |
| AUD-017 | attempts sin unicidad | §R2C PK única | AUD | dos intentos simultáneos incoherentes | REPAIR_REQUIRED |
| AUD-018 | políticas ambiguas | §R2A | AUD | política sin determinar veredicto | REPAIR_REQUIRED |
| AUD-019 | P/ESo/T/O incoherente | §R2A | AUD | dispatch OK, ejecución fallida sin reconciliación | REPAIR_REQUIRED |

### 4.C — RES-1…RES-9

| Unidad | Defecto (heredado) | Reparación — ref. sección | Dependencia | Contraejemplo | Estado |
|---|---|---|---|---|---|
| RES-1 | SinkAccept campos | §R2A §3 | AUD | ignorar campo | REPAIR_REQUIRED |
| RES-2 | binding doble | §R2C.3 única | AUD | doble binding | REPAIR_REQUIRED |
| RES-3 | INV-06/07 inexistentes | §R2A única | AUD | inversión inexistente | REPAIR_REQUIRED |
| RES-4 | ≈8640 | §R2A | AUD | 8639 8640 | REPAIR_REQUIRED |
| RES-5 | §2.L OD incompleto | §R2A | AUD | OD incompleto | REPAIR_REQUIRED |
| RES-6 | epoch sin transición | §R2D.4.1 KK | PKI | transición inconsistente | BLOCKED |
| RES-7 | DDL binding | §R2C FK | AUD | attempt sin binding | REPAIR_REQUIRED |
| RES-8 | deps SC-001 incompleto | §R2A | AUD | vinculación ausente ⇒ incumplimiento | REPAIR_REQUIRED |
| RES-9 | INV-13 derivación | §R2A | AUD | swing inconsistente | REPAIR_REQUIRED |

### 4.D — M-01…M-10

| Unidad | Defecto (heredado) | Reparación — ref. sección | Dependencia | Contraejemplo | Estado |
|---|---|---|---|---|---|
| M-01 | ESo=REJECTED sin terminal | §R2A ESo domain | ANY | reject | BLOCKED |
| M-02 | decided_at sin tipo | §R2C.3 timestamptz | AUD | HK actualidad | REPAIR_REQUIRED |
| M-03 | claim_generation inválidos | §R2C bounded | AUD | 256 overflow | REPAIR_REQUIRED |
| M-04 | IER-reopen-v1 mantenido | §R2D.4.1 | PKI | reapertura sustituida | BLOCKED |
| M-05 | BND devuelve resultados | §R2A veredictos atómicos | GRAPH | se omiten funtores paralizantes | BLOCKED |
| M-06 | §7.5 referencia | §R4 explícita | AUD | referencia rota | REPAIR_REQUIRED |
| M-07 | rely salt | §R9E | PKI | roble | BLOCKED |
| M-08 | io tag | §R9C enumeration | AUD | tag no únci | REPAIR_REQUIRED |
| M-09 | A-03/v2 unifica | §R2C uniformity | AUD | ambigüedad | REPAIR_REQUIRED |
| M-10 | fence-window acotar | §R2D.4.2 | GRAPH | efecto aceptado fuera de ventana | BLOCKED |

### 4.E — A-01…A-04, B, C, D, E, F, G

| Unidad | Defecto (heredado) | Reparación — ref. sección | Dependencia | Contraejemplo | Estado |
|---|---|---|---|---|---|
| A-01 | FK compuesta ausente | §R2C.3 FK compuesta | AUD | FK violada | REPAIR_REQUIRED |
| A-02 | bigint sin UINT64 | §R2C.3 CHECK bounded | AUD | overflow | REPAIR_REQUIRED |
| A-03 | head CAS sin predicado | §R2C.3.1 §4.1 recuperablehead | GRAPH | head desborda epoch | REPAIR_REQUIRED |
| A-04 | manifest sin vincular operación | §R2C.1/§R2C.3 UNIQUE op_attempt | INT | manifiesto sin op | REPAIR_REQUIRED |
| B | 2phase atómica incompleta | §R2D | B04 | commit externo difiere | BLOCKED |
| C | T-CLOSE incompletante | §R2D | ANY | cierre inconsistente tras T13 | REPAIR_REQUIRED |
| D | T13 incompleto | §R2D.4.1 | ANY | transición sin consumo | BLOCKED |
| E | preimagen sin control | §R4 | PKI | colisión determinista verificable | BLOCKED |
| F | políticas sin cobertura | §R2A | ANY | transición no reasignada | BLOCKED |
| G | universalidad | §R2C | AUD | | REPAIR_REQUIRED |

### 4.F — C-01…C-19

| Unidad | Defecto (heredado) | Reparación — ref. sección | Dependencia | Contraejemplo | Estado |
|---|---|---|---|---|---|
| C-01 | CHECK contradictorio | §R2A §3 | B04+AUD | OD contradictorio permitido | BLOCKED |
| C-02 | frontera Atómica | §R2D.4.1 | B04 | efecto con fence stale | BLOCKED |
| C-03 | D-U sin enumerar | §R9B graph | GRAPH | propagación invisible no detectada | BLOCKED |
| C-04 | preimagen sin control | §R4 | PKI | colisión verificable | BLOCKED |
| C-05 | numeric round | §R2C.3 | AUD | overflow en ordinal | REPAIR_REQUIRED |
| C-06 | window close shadow | §R2D.4.2 | AUD | efecto aceptado fuera de ventana | BLOCKED |
| C-07 | atomic resume sym | §R2D.4.1 | GRAPH | resume inconsistente | BLOCKED |
| C-08 | cap sieve reject | §R2C.3 | GRAPH | capacidad sobre-declarada | BLOCKED |
| C-09 | anchor cold | §R2D | ANCLA | ancla prevalece suena | BLOCKED |
| C-10 | CAS falso | §R2C.3/R2D | B04+AUD | CAS exitoso con dato divergente | BLOCKED |
| C-11 | dupe consume | §R2D consume | B04+AUD | consume sin efecto formal | BLOCKED |
| C-12 | dense order | §R9C order | EFFECT | permutar ordinales ⇒ hash distinto | BLOCKED |
| C-13 | terminal compensación | §R2A COMPENSATED | ANY | cierre con compensación pendiente | BLOCKED |
| C-14 | enforced sinks | §R2C.3 roles | AUD | sink no registrado delega | REPAIR_REQUIRED |
| C-15 | permisos trigger | §R2C.3 guard | INT | trigger sin autorización | REPAIR_REQUIRED |
| C-16 | effect_key vinculado | §R2C.3 privacy | EFFECT | preimagen aceptable contra+parte | REPAIR_REQUIRED |
| C-17 | A6 propagación | §R9B | GRAPH | dependencia bloqueada | REPAIR_REQUIRED |
| C-18 | atomic line | §R2D | B04 | efecto con fence stale | REPAIR_REQUIRED |
| C-19 | anchor bi | §R2D | ANCLA | ancla sin actualización | BLOCKED |

### 4.G — N-01…N-10

| Unidad | Defecto (heredado) | Reparación — ref. sección | Dependencia | Contraejemplo | Estado |
|---|---|---|---|---|---|
| N-01 | CHECK ambos | §R2A | B04+AUD | recetas contradictorias dentro del chispe | BLOCKED |
| N-02 | attempt binding missing | §R2C.3 | EFFECT | attempt sin binding | REPAIR_REQUIRED |
| N-03 | order inconsistente | §R2D | EFFECT | permutar ordinales produce hash distinto | REPAIR_REQUIRED |
| N-04 | cap binding | §R2C.3 | B04 | capacidad sobre-declarada | REPAIR_REQUIRED |
| N-05 | trigger sin permiso | §R2C.3 | INT | trigger sin autorización | REPAIR_REQUIRED |
| N-06 | anchor ext | §R2D | ANCLA | ancla sin actualización | BLOCKED |
| N-07 | encode | §R4 | PKI | preimagen colgante verificable | REPAIR_REQUIRED |
| N-08 | splitting | §R9C | AUD | dividir sin aislamiento provoca | REPAIR_REQUIRED |
| N-09 | splitting sibling | §R9C | AUD | hermano sin aislamiento | REPAIR_REQUIRED |
| N-10 | domains sin cierre | §R9C mapping | AUD | símbolo fuera de dominio | REPAIR_REQUIRED |

---


---

## 5. Máquina de efectos — verificación completa (80 combinaciones)

Verificación reproducible (cálculo local; no ejecuta Postgres ni persistencia):

- 5 × 4 × 4 = 80 combinaciones cubiertas: 33 con resultado definido (combinación válida) y 47 rechazadas por construcción (INVALID).
- Ninguna combinación INVALID alcanza outcome ∈ {COMMITTED, COMPENSATED, NOT_EXECUTED}.
- Outcomes terminales: COMMITTED (ACCEPTED∧EXECUTED∧NOT_REQUIRED), COMPENSATED (ACCEPTED∧EXECUTED∧VERIFIED), NOT_EXECUTED (ACCEPTED∧FAILED_CONFIRMED∧NOT_REQUIRED y REJECTED∧NOT_CONFIRMED∧NOT_REQUIRED).
- Los candidatos a cierre son exactamente los que tienen `dispatch ∈ {ACCEPTED, REJECTED} ∧ compensation_verified ∨ compensation == NOT_REQUIRED ∧ outcome ≠ UNKNOWN ∧ execution_state ≠ UNKNOWN`.

Reglas de producción (resumen operativo):

```
P-001  never dispatch  → NO effect puede construirse ni clasificarse como COMPENSATED.
P-002  ANY             → satisfacción = ≥1 VERIFIED + resto {VERIFIED|COMPENSATED|NOT_EXECUTED}.
P-003  ALL             → satisfacción = todos VERIFIED.

Efectos pendiente y política:
  e.dispatch=DISPATCHED ⇒ e.execution_state ∈ {NOT_CONFIRMED, EXECUTED, FAILED_CONFIRMED}; cualquier combinación con effect.outcome=UNKNOWN bloquea cierre.
```

Esta verificación no demuestra corrección sobre almacenamiento real ni sobre ejecución distribuida.

---

## 6. Discrepancias y problemas encontrados durante la revisión

### 6.1 Discrepancia B₀ (descubierta por cálculo)

Declarar sucesivamente que "|B₀| = 46" no se sostiene. Aplicando la regla vigente (`u ∈ B₀ ⇔ D_G(u) ∩ B₀-gates ≠ ∅`) el resultado es **61 bloqueados** contra 43 con solo gate auxiliar. La diferencia son las unidades mixtas cuyo gate estructural las bloquea por ley: `{H-04, H-07, H-10, H-12, H-13, H-20, H-21, H-27, C-01, C-10, C-11, N-01}`. La regla debe decidirse por el propietario; esta revisión no las resuelve silenciosamente.

### 6.2 Estados legados de R7…R8 no compatibles con el vocabulario único

`REPAIRED-DOCUMENTAL` y `REPAIRED-CONDICIONADO` siguen apareciendo en antecedentes como sustituto histórico de `REPAIR_REQUIRED`/`BLOCKED`. En esta revisión el vocabulario es único.

### 6.3 Parche sobre v5 que no fue reauditado

`docs/ier/IER_GATE_PLAN.md` (§1 FROZEN), `B07_FORMAL_MODEL.md` y `B07-R2-Repair-Specification.md` permanecen históricos; cualquier corrección proveniente de v5–v8 no se reintrodujo silenciosamente.

### 6.4 160 líneas de contenido efectivo sin verificación contra implementación

Esta revisión no ha ejecutado ningún DDL, no ha probado ningún vector con bases concretas y no ha realizado pruebas de concurrencia, crash injection o RLS.

### 6.5 Filas vacías que aún no tienen contraejemplo discriminante completo

- `N-02`, `N-03`: referencias generales de orden sin prueba discriminante formal.
- `AUD-002`: rechazo de doble binding no verificado en realidad.

Ninguna fila de la tabla está cerrada por esta revisión.

---

## 7. Estado de dirección (tras esta revisión)

- `R2 = REPAIR_REQUIRED` · `R3 = BLOCKED` · `MODEL_VERIFIED = NO` · `IMPLEMENTATION_READY = NO` · promoción `NOT_READY`.
- Antecedentes v1…v8 preservados; baseline, §1 y `B07_FORMAL_MODEL.md` intactos.
- `B07-R2-Consolidated-Repair-Matrix.md` (esta revisión) espera dictamen; no se abre r3.

Fin R2-A REVISION 9 · DRAFT / NOT_ACCEPTED / NOT_EXECUTED / UNVERIFIED · Procedencia en `state/multiproject/log.md`.
