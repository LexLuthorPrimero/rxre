# Refutación independiente — RXRE-AUDIT-AF-REVIEW-001

**Revisor:** instancia independiente, contexto fresco (sin historial del auditor).
**Objetivo:** intentar REFUTAR con pruebas reproducibles los claims `[CRITICAL]` del audit previo y
valorar el impacto de sus limitaciones. **No** corrijo defectos, no diseño arquitectura, no amplío trabajo técnico.
**Modo:** SOLO LECTURA. Únicos ficheros escritos: `./audit/review/**` y temporales en `/tmp/opencode/revAF`.
No se tocó producción, tests, docs, infra, ni `audit/STATE`. La BD por defecto **nunca** se abrió.

---

## 0. Estado previo y de integridad

### 0.1 `STATE=DELIVERED` ≠ aceptación
`audit/STATE` contiene `DELIVERED\n` (10 bytes). Tal como declara el propio auditor en `report.md` §1:
*"la aceptación corresponde a un revisor independiente posterior; **no** me autoasigno ACCEPTED"*.
**`DELIVERED` es trámite de entrega, no aceptación.** Este documento emite el estado final (§7).

### 0.2 Baseline git (registrado)
| Dato | Valor |
|---|---|
| `git rev-parse HEAD` | `0b063135d4f73d353846fc0936f9dae765c43953` |
| Rama | `main` |
| Modificados rastreados (`grep -v '^??' \| wc -l`) | **21** — idéntico al declarado por el auditor |
| Total `git status --short \| wc -l` | 218 = 217 (baseline pre-audit) + 1 (`?? audit/` creado por el auditor). **Sin discrepancia real.** |

### 0.3 Hashes recomputados por mí vs declarados
Recomputé SHA-256 de los seis ficheros que el informe declara y los comparé con `report.md`
y con `audit/evidence/tracked_hashes.txt`:

| Fichero | Declarado (auditor) | Recomputado por mí | ¿Coincide? |
|---|---|---|---|
| `tools/rxre/api/machine.py` | `efc3ae68…c7b49` | `efc3ae68…c7b49` | ✅ |
| `tools/rxre/core/store.py` | `2cdf9519…76271` | `2cdf9519…76271` | ✅ |
| `tools/rxre/backends/dispatch.py` | `bc698e60…b800e` | `bc698e60…b800e` | ✅ |
| `tools/rxre/backends/adapters/rz_xrefs.py` | `2078742d…2dc39` | `2078742d…2dc39` | ✅ |
| `tools/rxre/backends/adapters/rz_callgraph.py` | `3152f7a4…30d8a` | `3152f7a4…30d8a` | ✅ |
| `/bin/ls` == `/usr/bin/ls` | `54e936d3…71a0c` | `54e936d3…71a0c` | ✅ |
| `/usr/bin/rm` | `af8e6671…e8c7f` | `af8e6671…e8c7f` | ✅ |

Además verifiqué que los ficheros fuente tienen mtime **previo** al snapshot del auditor
(`machine.py` 06:46; `rz_xrefs.py` 2026-10-16) y que, tras el audit, solo cambió `.git`
(metadatos). **El árbol medido por el auditor es el árbol que yo mido.** → **Integridad: VERIFICADA.**

### 0.4 Reproducibilidad de las evidencias
Todas las salidas crudas del auditor siguen presentes en `audit/evidence/` y son legibles
(ej. `testA_oracle_start_disasm.txt` 2196 B, `testD_oracle_agCj_aaa.json` 15954 B,
`testA_xrefs_to_main.json`, `testC_xrefs_aa.json`, …). Dos ficheros están vacíos
(`testA_oracle_start.txt`, `testA_oracle_main.txt`); son restos de comandos abortados del auditor,
pero la evidencia sustantiva vive en los otros ficheros, así que **no** constituye pérdida material.

---

## 1. CLAIM CRÍTICO A3 — `main=0x1540` y arista `_start → main`

**Claim (claims.csv A3):** *"main = 0x1540 y _start = 0x3910; _start pasa main a `__libc_start_main`
(`lea rdi,[0x1540]` en 0x3928)"* — estado `PROVEN`.

### 1.1 Procedimiento reconstruido
1. Fijar entry point y código de arranque (`objdump -f`, `readelf -h`).
2. Desensamblar el arranque y localizar el `lea`/`call` que carga `main`.
3. Identificar `main` por **motor distinto** (capstone sobre bytes crudos).
4. Contrastar con RXRE (`binary.symbols`, `binary.functions`, `binary.xrefs inicio=5440`).
5. Confirmar que `main` lee `argc/argv` (el requisito L4 del protocolo).

### 1.2 Hipótesis rival
*H1 (refutable):* el `lea` de 0x3928 no carga `main`, o `0x1540` es una función distinta de `main`;
o objdump y rizin coinciden por un error compartido (p.ej. `lea` mal resuelto). En tal caso A3 sería falso.

### 1.3 Evidencia buscada y prueba discriminante
Busqué un **tercer motor** independiente (capstone) que decodifique los bytes crudos sin usar
la anotación de objdump ni el simbolismo de rizin:

```
[rc=0] objdump -d --start-address=0x3910 --stop-address=0x3936 /bin/ls
    3928: lea -0x23ef(%rip),%rdi   # 1540
    392f: call *0x2163b(%rip)      # 24f70 <__libc_start_main@GLIBC_2.34>

[rc=0] python3 /tmp/opencode/revAF/capstone_oracle.py /bin/ls 0x3910 0x1540
    0x3928: lea rdi,[rip-0x23ef]   -> 0x392f - 0x23ef = 0x1540   (coincide con objdump)
    0x392f: call qword ptr [rip+0x2163b] -> 0x3935 + 0x2163b = 0x24f70
    0x154e: mov r13d,edi  ; 0x155b: mov rbx,[rsi] ; 0x156b: mov r12,rsi

[rc=0] run binary.xrefs /bin/ls aaa inicio=5440
    status ok; 1 result {from:14632(=0x3928), to:5440(=0x1540), type:DATA}
```

`0x3928 → 0x1540` está verificado **por bytes** (capstone), **por anotación** (objdump) y
**por simbolismo** (rizin: `main@5440`, `_start@14608`). `0x24f70` es `__libc_start_main`;
por ABI SysV el **primer argumento (`rdi`) de `__libc_start_main` es `main`**.

El eslabón L4 (main lee argv) lo confirmo en el desensamblado de `0x1540`:
`mov %edi,%r13d` (argc), `mov (%rsi),%rbx` (argv[0]), `call getopt_long@plt`,
`mov …,%rax # optind`, `mov (%r12,%rbx,8),%rdi` (argv[i]).

### 1.4 Veredicto A3 → **RESISTE**
La hipótesis rival H1 queda refutada: tres motores independientes coinciden en la dirección y en el
destino del `lea`; la identificación de `main` no depende de que objdump pueda nombrarlo (no puede).

### 1.5 Limitaciones de A3
- El **nombre** `main` solo lo aporta rizin desde `.gnu_debugdata` (verificado: `.symtab` ausente,
  `.gnu_debugdata` presente). El objetivo de `main` se sostiene por la ABI, no por el nombre.
- La arista `_start→main` es de tipo **DATA** (un `lea` que referencia la dirección de `main`),
  no un CALL. RXRE la clasifica como `DATA` y el auditor no la trata como CALL. Correcto.
- La arista **solo** aparece con `inicio=5440`; con el default `0x4000` se omite (ver §5.3).

---

## 2. CLAIM CRÍTICO C2 — semántica de `PROVEN_ABSENT` en nivel `aa`

**Claim (claims.csv C2):** *"RXRE NO declara `PROVEN_ABSENT` con nivel `aa`; etiqueta el nivel de
análisis"* — estado `PROVEN`.

### 2.1 Procedimiento reconstruido
1. Ejecutar `binary.xrefs` con `nivel_analisis=aa` y leer el envelope (estado, epistemic, limitations).
2. Inspeccionar `rz_xrefs.py`: ¿existe alguna ruta a `PROVEN_ABSENT`?
3. Inspeccionar el único gate epistémico (`rz_findings._reclamar_estado_epistemico`).
4. **Intentar activamente** crear un hallazgo `PROVEN_ABSENT` (refutación activa, no pasiva).

### 2.2 Hipótesis rival
*H1:* el sistema **sí** puede emitir `PROVEN_ABSENT` a partir de una consulta `aa` vacía
(adapter de binario, o el gate `rz_findings` aceptando un `empty` de `aa` como evidencia),
lo que sería una **ausencia falsa** (el fallo epistémico que Test C debe detectar).

### 2.3 Evidencia buscada y prueba discriminante

**Prueba 2a — el adapter no lo emite:**
```
[rc=0] run binary.xrefs /bin/ls aa
    status='empty'  epistemic=None  backend_rc=0  ejecutada=true  results=[]
    persistido=false  operation_id=None  next_actions=[]
    limitations[1] = "nivel_analisis 'aa': 'aa' puede no descubrir todas las referencias; comparar con 'aaa'…"
    ejecucion.nivel_analisis = 'aa'
```
No hay campo `epistemic`/`PROVEN_ABSENT`. El nivel **sí** va etiquetado en `limitations` y en `ejecucion`.

**Prueba 2b — el gate lo rechaza si la evidencia no es `empty` (refutación activa):**
```
[rc=0] run rxre.create_finding claim="no hay xref a main",
       evidence_ids=[res_xref_3f81…(status ok)], epistemic=PROVEN_ABSENT
    status=ok  epistemic='PARTIAL'
    motivo="PROVEN_ABSENT requiere al menos un resultado empty; su evidencia tiene: ok"

[rc=0] run rxre.create_finding … evidence_ids=[res_xref_DOES_NOT_EXIST], epistemic=PROVEN_ABSENT
    status=error  epistemic='NOT_DETERMINED'
    motivo="ninguno de los result_id de evidencia existe"
```
El gate exige evidencia cuya operación tenga `status=empty`. **Pero los `empty` no se persisten**
(`dispatch.py:1022` solo llama a `_persistir` si `env["results"]`, y un `empty` tiene `results=[]`)
→ **no existe `result_id` de un `empty`** → `PROVEN_ABSENT` es **esencialmente inalcanzable**.
La ausencia falsa por esta ruta **no puede materializarse** en el árbol actual.

### 2.4 Veredicto C2 → **RESISTE**
RXRE no declara `PROVEN_ABSENT` para `binary.xrefs` en `aa`, el nivel queda etiquetado, y además
ni el adapter ni el gate llegan a emitirlo. H1 refutada por doble vía (negativa + intento activo).

### 2.5 Limitaciones de C2 (alcance)
- La protección es en parte **accidental**: no existe el token `EMPTY_BY_INSUFFICIENT_ANALYSIS`
  (ya señalado por el auditor en B2); el "discriminante" es solo texto libre en `limitations`.
- El docstring `rz_findings.py` afirma *"PROVEN_ABSENT requiere al menos un empty **Y un discriminante**"*,
  pero el código solo chequea `has_empty` (líneas 410–417): **el discriminante y el nivel nunca se verifican**.
  Hoy es inocuo porque `PROVEN_ABSENT` es inalcanzable; sería crítico si algún adapter empezara a
  persistir `empty`. **Defecto registrado, NO corregido.**

---

## 3. CLAIM CRÍTICO D1 — subdeterminación del callgraph (`aa`→5 vs `aaa`→84)

**Claim (claims.csv D1):** *"`binary.callgraph` usa `'aa; agCj'` (hardcodeado) → 5 nodos; el oráculo
`'aaa; agCj'` → 84 nodos; el callgraph está gravemente subdeterminado"* — estado `PROVEN`.

### 3.1 Procedimiento reconstruido
1. Releer `rz_callgraph.py`: ¿dónde se fija el nivel y si acepta parámetro?
2. Ejecutar `binary.callgraph` (RXRE) y contar nodos.
3. **Refutación activa:** pasar `nivel_analisis=aaa` para ver si eleva la profundidad.
4. Correr el oráculo crudo `radare2 'aa; agCj'`, `'aaa; agCj'` y `'aaaa; agCj'`.

### 3.2 Hipótesis rival
*H1:* el nivel es fijable por la API (o `aa` es suficiente), y **o** 5 vs 84 es un artefacto de parseo
del adapter (no una diferencia real de análisis). Si H1 se sostuviera, D1 sería refutado.

### 3.3 Evidencia buscada y prueba discriminante

**Código** (`rz_callgraph.py`): `def callgraph(artefacto, **kwargs)` solo lee
`backend_id/timeout/inicio/longitud/fixture_json` → **no hay parámetro de nivel**;
`cmd_str = "aa; agCj"` hardcodeado en las líneas 312 (fixture) y 398 (producción);
`precheck["verb"] = "aa"` en la 241.

**Prueba discriminante (¿se puede pedir `aaa`?):**
```
[rc=0] run binary.callgraph /bin/ls
    status ok; 5 nodos [entry0, sym.error_at_line, sym.error, main, entry.fini0]
    command "r2 … 'aa; agCj'"; precheck.verb='aa'

[rc=0] run binary.callgraph /bin/ls nivel_analisis=aaa
    status ok; 5 nodos (idénticos); command "r2 … 'aa; agCj'"
    ejecucion.nivel_analisis = None      <-- el parámetro se DESCARTA en silencio
```

**Oráculo crudo (mismo nivel vs nivel superior):**
```
[rc=0] radare2 -c 'aa;  agCj' /bin/ls -> n=5     (idéntico a RXRE)
[rc=0] radare2 -c 'aaa; agCj' /bin/ls -> n=84
[rc=0] radare2 -c 'aaaa;agCj' /bin/ls -> n=120   <-- extra: ni 84 es el techo
```
Los **nombres** de los 5 nodos de RXRE coinciden uno a uno con los de `r2 'aa; agCj'`:
**5 == 5**, y el conteo `84` con `aaa` está verificado de forma independiente.
No es artefacto de parseo: es una diferencia real de análisis.

**Impacto (D2/D3), indegree calculado por mí:**
- `aa` (5 nodos): **4** targets con indegree>1 (`__fprintf_chk=3, __stack_chk_fail=3, flush_stdout=2, error_tail=2`) ✅
- `aaa` (84 nodos): **101** targets con indegree>1 (`__stack_chk_fail=37, strlen=27, __errno_location=23, malloc=21, free=16…`) ✅

### 3.4 Veredicto D1 → **RESISTE** (e incluso se **fortalece**)
La hipótesis rival H1 queda refutada: el nivel **no** es fijable, y la diferencia 5 vs 84 es real.
Aún más: `aaaa` da **120** nodos → el callgraph de RXRE es **aún más** subdeterminado de lo que
declaró el auditor, y el consumidor **no tiene ninguna palanca** para pedir otro nivel.

### 3.5 Limitaciones de D1
- El claim original habla de "84 con aaa"; verifiqué que el techo real es **120** (`aaaa`), lo que
  **amplía**, no contradice, la conclusión.
- El número de nodos depende de la versión de r2 (5.9.8) — reproducible en este host.

---

## 4. Veredicto de los claims críticos (síntesis)

| Claim | Veredicto | Prueba clave |
|---|---|---|
| **A3** main=0x1540 + `_start→main` | **RESISTE** | capstone (3ª motor) sobre bytes crudos: `lea rdi,[rip-0x23ef]→0x1540`; RXRE `xrefs inicio=5440 → {14632→5440}`; `main` lee argv |
| **C2** no `PROVEN_ABSENT` en `aa` | **RESISTE** | `run xrefs aa → status 'empty', epistemic=None`; gate `create_finding PROVEN_ABSENT` con evidencia non-empty → `PARTIAL`; empty nunca persistido → inalcanzable |
| **D1** callgraph `aa`→5 vs `aaa`→84 | **RESISTE** | `nivel_analisis=aaa` descartado (sigue 5 nodos, `'aa; agCj'`); r2 crudo aa=5 / aaa=84 / aaaa=120 |

**Los tres claims críticos resisten la refutación activa independiente.**

---

## 5. Las 4 investigaciones extra (impacto real)

### 5.1 (a) Diferencias registry ↔ adapters (ghidra `existe=false` pero `decompile ok`)
```
[rc=0] op backends
    ghidra      {exe:analyzeHeadless, path:null, existe:false, version_verificada:false}
    coccinelle  {exe:spatch, path:/usr/bin/spatch, existe:true, spatch 1.3.1}
[rc=0] run binary.decompile /bin/ls backend_id=ghidra
    status ok; 5 results tool=ghidra; repository_commit=local:rpm-ghidra-12.1.4
```
**Causa raíz (identificada por mí):** el probe de disponibilidad del registry usa el nombre `exe`
(`analyzeHeadless`) buscado en `PATH`; `which ghidraRun analyzeHeadless` → **no encontrado** (rc=2).
El **adapter** `gh_decompile.py` usa `GHIDRA_INSTALL_DIR/support/analyzeHeadless`
(`=/usr/lib64/ghidra/support/analyzeHeadless`, existe). Falso negativo del `existe`, no un fallo de ejecución.

**Impacto:** la discrepancia **es real** y está bien documentada por el auditor (E4 `PROVEN`, E2 `PROVEN`,
E5 `NOT_EXECUTED`). **No invalida** los claims críticos. Sí es una limitación operativa: cualquier
consumidor que decida por `op:backends[ghidra].existe` llegará a la conclusión **equivocada** de
"backend no disponible" para una capacidad que **sí** funciona. El registry marca
`binary.decompile/ghidra = 'PARTIAL'` mientras un run concreto da `status ok`; no es contradicción
(`PARTIAL` refleja la clase ET_REL, no `ls`).

### 5.2 (b) El oráculo `objdump` — ¿es válido el sustituto del literal?
```
[rc=1] objdump -d /usr/bin/ls | grep -A30 '<main>'        -> sin salida
[rc=1] objdump -t /usr/bin/ls | grep -Ei ' main$| _start$' -> sin salida
[rc=0] LC_ALL=C readelf -S /bin/ls | grep -iE 'symtab|debugdata|dynsym'
        .dynsym ✓ ; .gnu_debugdata ✓ ; .symtab ✗   (binario stripped)
```
**Conclusión:** el oráculo **literal** del protocolo **no** es ejecutable en esta distro (sin `.symtab`,
el `grep '<main>'` no encuentra nada). El sustituto derivado del auditor (calcular `main` desde el
arranque de `_start`) **es válido**: no depende del nombre del símbolo, solo de la ABI
(1er argumento de `__libc_start_main`), y lo **corroboré con capstone** (motor ajeno a objdump y a rizin).
**Impacto:** `A2` RESISTE, y la derivación del auditor es honesta y correcta. Matiz: el rótulo objdump
`<error_at_line@@Base+0x1e8>` sobre `0x1540` es un artefacto del `.dynsym` precedente y **no** es `main`;
el auditor no cae en esa confusión. **No invalida ningún claim.**

### 5.3 (c) El ancla por defecto de `xrefs` (`0x4000` → 74 xrefs todas a `0x4000`)
```
[rc=0] run binary.xrefs /bin/ls aaa        (default) -> 74 results; to={16384(=0x4000):74}; from!=14632
[rc=0] rizin -c 'aaa; axtj @ 0x4000' -> n=74 (to 0x4000)
[rc=0] rizin -c 'aaa; axtj @ 0x1540' -> n=1  (to 0x1540)
[rc=0] rizin -c 'aaa; axtj @ 0x1550' -> n=0
[rc=0] rizin -c 'aaa; axtj @ 0x1000' -> n=14 (to 0x1000)
```
**Conclusión:** el comentario del adapter *"`axtj @ <addr>` lista **TODOS** los xrefs (quirk)"* está
**REFUTADO**: el `@ addr` **filtra por dirección destino** (74/1/0/14 según el ancla). El default `0x4000`
es **arbitrario** y devuelve 74 xrefs *hacia* `0x4000`, no "todos los xrefs del binario". El claim `A6`
del auditor queda **confirmado**, y se ve reforzado porque la ancla default **omite** la arista `_start→main`
(buscada en A3/A7). **Impacto:** real sobre el Test A (aviso de "melaza"); no invalida los claims críticos,
pero **limita** el uso de `binary.xrefs` sin `inicio`.

### 5.4 (d) Ausencia de persistencia para resultados `empty`
```
[rc=0] run xrefs aaa (1ª)  -> result_id=res_xref_3f814786eef29b48 (idéntico al auditor), persistido=true
[rc=0] run xrefs aaa (2ª)  -> operation_id=COLISION:res_xref_3f814786eef29b48, mismo result_id
[rc=0] run xrefs aa        -> status empty, persistido=false, operation_id=None
[rc=0] COUNT(*) results/operations tras 1ª+2ª+empty -> 1 / 1   (el empty NO añade fila)
[rc=0] explain op_1e6b7d… (por operation_id) -> status empty + limitación honesta
```
**Conclusión:** `F4` **CONFIRMADO** (los `empty` no se persisten → la "ausencia" no es auditable con
`explain`). `F2`/`F3`/`F5`/`F6` **reproducidos** (el `raw_json` está anidado en `result.raw_json`;
`result_id` determinista reproduce el mismo valor que el auditor). **Impacto:** es la brecha de
reproducibilidad declarada. Interacción **no señalada por el auditor** que yo destaco: esta misma
no-persistencia es la que hace **inalcanzable** `PROVEN_ABSENT` (§2.3), de modo que refuerza C2
pero **contradice** el docstring del gate (`rz_findings.py`) que promete validar "empty **Y** discriminante".

---

## 6. Separación: hechos observados / inferencias / contradicciones / preguntas abiertas

### Hechos observados (reproducibles)
- Los 7 hashes declarados por el auditor **coinciden** con los míos; baseline `0b06313` / rama `main`; modificados rastreados = 21.
- `main=0x1540` y `_start=0x3910` en `/bin/ls`; `0x3928 lea→0x1540` verificado por objdump **y** capstone.
- `binary.xrefs inicio=5440 → {14632→5440}`; default `0x4000 → 74` con `to={16384:74}` y **sin** `from=14632`.
- `binary.xrefs aa → status 'empty'`, `epistemic=None`, nivel etiquetado, `persistido=false`.
- `binary.xrefs aa inicio=5440 → status 'ok'` (¡`aa` **sí** descubre xrefs!).
- `binary.callgraph → 5 nodos` con `'aa; agCj'` hardcodeado; `nivel_analisis=aaa` **descartado**; r2 `aa=5 / aaa=84 / aaaa=120`.
- Indegree: `aa`→4 targets >1 llamador; `aaa`→101 (`__stack_chk_fail=37`, `strlen=27`).
- registry `ghidra existe=false` pero `decompile` → `ok` (5 funcs).
- Literal oracle `grep '<main>'` → rc=1 (stripped, sin `.symtab`).
- `spatch 1.3.1` presente; `analyzeHeadless` no está en `PATH` pero vive en `/usr/lib64/ghidra/support/`.

### Inferencias (sustentadas, no directamente medidas)
- Por ABI SysV, el 1er argumento de `__libc_start_main` es `main` → `0x1540` **es** `main` (aunque no podamos nombrarlo por `.symtab`).
- `PROVEN_ABSENT` es **inalcanzable** en la práctica (no hay `result_id` de un `empty`). Deducción de `dispatch.py:1022` + `_reclamar_estado_epistemico`; probado empíricamente, no exploré **todos** los adapters por exhaustividad.
- El techo real del callgraph (120 con `aaaa`) sugiere que ni `aaa` es completo.

### Contradicciones (reproducibles)
1. **C1 del auditor (parcialmente refutado):** el informe interpreta `aa → empty` como *"aa no descubre xrefs de funciones → profundidad insuficiente"*. **Es falso como causa categórica:** `aa; axtj @ 0x1540 → 1` y `binary.xrefs aa inicio=5440 → ok`. El `empty` del Test C es **ancla-dependiente** (default `0x4000`), no prueba de incapacidad del nivel. → `C1 = LIMITADO`.
2. **Docstring vs código en `rz_findings`:** *"PROVEN_ABSENT requiere empty **Y discriminante**"* — el código solo chequea `has_empty`; el nivel y el discriminante **nunca** se verifican.
3. **Comentario del adapter `rz_xrefs`** (*"axtj @ <addr> lista TODOS los xrefs"*) **refutado** por medición cruda (ya señalado por el auditor en A6; lo confirmo).
4. **Declaración del protocolo** (`RXRE-1637 §4`: *"rz_xrefs y rz_callgraph no escriben nada"*) **refutada** — ambos persisten (`F6`).

### Preguntas abiertas
- ¿Existe **algún** adapter capaz de persistir un resultado con `status=empty`? Si lo hubiera, `PROVEN_ABSENT` dejaría de ser inalcanzable y el gate (sin chequear nivel ni discriminante) emitiría ausencia falsa desde una consulta `aa`. No lo agoté por exhaustividad.
- ¿El `existe=false` del registry afecta a otros backends además de ghidra (p.ej. rutas fuera de `PATH`)?
- ¿Habría que reclasificar la arista `_start→main` como relación de arranque, no como `DATA`? (cuestión de semántica, no de corrección)

---

## 7. ESTADO FINAL

# `ACCEPTED`

**Justificación.** Los **tres claims críticos** (`A3`, `C2`, `D1`) fueron seleccionados y
**refutados activamente** con hipótesis rivales propias y pruebas discriminantes reproducibles, y
**los tres resisten**:

- **A3 — RESISTE**: corroborado por tres motores independientes (objdump, capstone sobre bytes crudos, rizin/RXRE), incluido el eslabón de argv. La hipótesis de "error compartido" queda refutada.
- **C2 — RESISTE**: por prueba positiva (`status='empty'`, `epistemic=None`, nivel etiquetado) **y** por intento activo de forzar `PROVEN_ABSENT` (el gate lo degrada a `PARTIAL`; los `empty` no se persisten, con lo que es inalcanzable).
- **D1 — RESISTE**: incluso fortalecido — `nivel_analisis=aaa` se descarta en silencio y el techo real es `aaaa=120`, no 84.

Las **limitaciones** del audit **NO invalidan** sus conclusiones principales:
- Las 4 investigaciones extra se evaluaron por **impacto real** y **no** derriban ningún claim crítico:
  (a) discrepancia registry↔adapter es verdadera pero **no** bloquea `decompile`; (b) el sustituto del oráculo literal es **válido** (corroborado con capstone); (c) la ancla `0x4000` **confirma** `A6` en lugar de debilitarlo; (d) la no-persistencia de `empty` es real y, lejos de invalidar `C2`, **refuerza** su inalcanzabilidad de `PROVEN_ABSENT`.
- La única **contradicción reproducible** sobre un claim del auditor es `C1` (el "vacío por profundidad" es en realidad **ancla-dependiente**), que **refina la explicación** del Test C **sin** alterar su conclusión central (no hay `PROVEN_ABSENT` a nivel `aa`), ni los demás veredictos.
- Los defectos detectados (gate `PROVEN_ABSENT` sin chequeo de nivel/discriminante; comentario erróneo de `rz_xrefs`; `nivel_analisis` ignorado en `callgraph`; persistencia inexistente en `empty`; `existe=false` falso negativo) quedan **registrados** en este documento y en `claims.csv`, **NO corregidos** (fiel a la consigna).

**Reserva de alcance (honestidad):** `ACCEPTED` se emite **sobre los claims críticos y las
conclusiones principales del audit**, no como validación del 100 % de sus 38 claims. Los claims
secundarios `C1` es **LIMITADO** y el resto de los analizados (`A2`, `A6`, `A7`, `B3`, `B5`, `D2–D6`,
`E1`, `E2`, `E4`, `F2–F6`) son **RESISTE**. Ninguno quedó `REFUTADO` ni `INCONCLUSIVO`.

---

## 8. Limitaciones / bloqueos de mi revisión

1. No ejecuté las suites de test del repo (fuera del alcance de solo-lectura y del propósito de refutación); los veredictos se basan en ejecución directa del motor + oráculos independientes.
2. No agoté **todos** los adapters para demostrar por exhaustividad que ningún `status=empty` es persistible; mi conclusión de "PROVEN_ABSENT inalcanzable" se apoya en la lectura del código (`dispatch.py:1022`) + 2 pruebas empíricas, no en una prueba universal.
3. El nombre `main` no puede confirmarse con un oráculo literal en binario `stripped`; depende de `.gnu_debugdata` (rizin) y de la ABI de `__libc_start_main`.
4. La discrepancia de `git status --short | wc -l` (217 vs 218) se **resolvió**: es el `?? audit/` creado por el auditor sobre el baseline pre-audit; el conteo de modificados rastreados (21) y todos los hashes coinciden → sin pérdida de integridad.
5. Ficheros vacíos `audit/evidence/testA_oracle_start.txt` y `testA_oracle_main.txt`: restos de comandos abortados del auditor; la evidencia sustantiva está en `testA_oracle_start_disasm.txt` y `testA_oracle_main_full.txt` (1972 líneas).

## 9. Artefactos entregados
- `audit/review/report.md` (este documento)
- `audit/review/claims.csv` (3 críticos + 17 extras)
- `audit/review/commands.log` (comandos literales con rc y extractos)
- `audit/review/evidence/` (salidas crudas del revisor)
- `audit/STATE` **no modificado**; producción, tests, docs e infra **no tocados**.
