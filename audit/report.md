# Auditoría independiente RXRE — Test A–F (RXRE-1637 §4)

- **Estado emitido por este auditor:** `DELIVERED` (trámite; la aceptación corresponde a un revisor
  independiente posterior; **no** me autoasigno `ACCEPTED`).
- **Modo:** SOLO LECTURA del código. Únicos ficheros creados: `./audit/**`. No commits, ramas,
  worktrees ni `git add`. No se tocó `storage/rxre.sqlite3` ni la BD por defecto (todo con `RXRE_DB`
  aislada en `/tmp/opencode/auditAF*.sqlite3`).
- **Fecha:** 2026-10-17. **CWD:** `/home/lucas/Escritorio/rxre`.
- **Protocolo leído por mí:** `RESEARCH/RXRE-1637-evaluacion-autonomía.md` §4 (líneas 118–184).

## 1. Baseline reproducible (git)

| Dato | Valor |
|---|---|
| `git rev-parse HEAD` | `0b063135d4f73d353846fc0936f9dae765c43953` (rama `main`) |
| `git status --short \| wc -l` | `217` entradas (21 ficheros rastreados modificados + untracked preexistente) |
| Modificados rastreados al inicio | 21 (incluye `machine.py`, `store.py`, `dispatch.py`, adapters…) — **preexistente, no tocado** |
| `sha256 machine.py` | `efc3ae684f9973e4476a72a5bdbaf84cf980bc642fa50e2363974dea3a4c7b49` |
| `sha256 store.py` | `2cdf9519875e7a0bf83837ba3c77da1ef5028503dd4eeb67ff0a26d161a76271` |
| `sha256 dispatch.py` | `bc698e6038432bbb4e5ea62e7096ebd19a70e6897680980fb59d25fb4bab800e` |
| `sha256 rz_xrefs.py` | `2078742d0d14df2f2715e47025ef27d935b102c32e20e985448bc8701882dc39` |
| `sha256 rz_callgraph.py` | `3152f7a4583018b80e6f9cd815912317a55e3188a24eae2a1675fc2e71230d8a` |
| `sha256 /bin/ls` (= `/usr/bin/ls`) | `54e936d37decdad9ecaf189b1de347605a0a99037ec87bd17679b6cbde871a0c` |
| `sha256 /usr/bin/rm` | `af8e667181be4f25e27740c1c9ab16190b1b818bada52c42d0a1b3a450de8c7f` |
| Verificación final | `git status --short \| grep -v '^??' \| wc -l` = **21** (idéntico); solo aparece `?? audit/` |

Detalle completo y todas las salidas crudas en `audit/commands.log` y `audit/evidence/`.

## 2. Herramientas — presentes / ausentes (corregido respecto al encargo)

| Herramienta | Estado real medido | Nota |
|---|---|---|
| `objdump` 2.46.1 | presente | oráculo independiente de Test A/D |
| `rizin` 0.7.4 | presente | producer `binary.*` (default rizin) |
| `radare2` 5.9.8 | presente | producer `binary.callgraph`/`cfg` |
| `capstone` 5.0.7 | presente (python) | producer `binary.disassemble*` |
| `spatch` = "coccinelle" 1.3.1 | **PRESENTE** (`/usr/bin/spatch`) | el binario `coccinelle` no existe, pero el producer sí |
| Ghidra `analyzeHeadless`/`ghidraRun` | **no en PATH**, **pero Ghidra 12.1.4 instalado por rpm funciona** | `binary.decompile` con `backend_id=ghidra` → `ok` (ver Test E) |
| `/bin/ls`, `/usr/bin/ls`, `/usr/bin/rm` | presentes | `/bin/ls` y `/usr/bin/ls` son el mismo inodo/hash |

**Corrección al encargo:** el encargo asumía `ghidraRun` y `coccinelle` **ausentes** y pedía tratarlos
como observable `not_available`. La medición refuta esa premisa: `spatch` está presente y **Ghidra
decompila de verdad** (`ok`, 5 funciones de `/bin/ls`). Por tanto el caso "backend indisponible" del
Test E **no pudo ejecutarse como estaba descrito** (claim E5 = `NOT_EXECUTED`).

---

## 3. TEST A — Reconstrucción causal

**Pregunta real:** *"¿Qué función de entrada lee y escribe el primer argumento de programa en /bin/ls?"*

### 3.1 Procedimiento ejecutado
1. Baseline y hash del artefacto (`binary.inspect` → `stripped=true`, hash `54e936d3…`).
2. Descubrir candidatos: `binary.symbols` (323 símbolos) y `binary.functions` (202 funciones).
3. Seguir transformaciones: `binary.functions` (regvars de `main`), `binary.xrefs`.
4. Conectar `symbols → functions → xrefs`: `binary.xrefs inicio=5440`.
5. Comparar con el oráculo independiente `objdump` (otro proveedor, no rizin/r2).

### 3.2 Hallazgo crítico del oráculo
El oráculo **tal como lo especifica el protocolo falla**:

```
$ objdump -d /usr/bin/ls | grep -A30 '<main>'   →  rc=1, SIN SALIDA
$ file /usr/bin/ls  →  ... stripped
$ objdump -t /usr/bin/ls | grep -Ei ' main$| _start$'  →  SIN SALIDA
```
`/usr/bin/ls` está **stripped** (no hay `.symtab` → `objdump -t` no ve `main`). El oráculo del
protocolo es inejecutable por nombre. Construí un **oráculo independiente equivalente** con `objdump`:

```
$ objdump -f /usr/bin/ls                     →  dirección de inicio 0x3910   (entry point)
$ objdump -d --start-address=0x3910 …        →  3928: lea -0x23ef(%rip),%rdi # 1540
                                                392f: call *…  <__libc_start_main@GLIBC_2.34>
```
→ El argumento `rdi` de `__libc_start_main` es **main = 0x1540**. Es una derivación independiente de
rizin/radare2 (reloj de `_start`). Ese `main` en `0x1540` es donde el binario guarda el nombre del
programa (`mov (%rsi),%rbx`; `strrchr`; `program_invocation_name`).

### 3.3 La cadena, enlace por enlace

| # | Enlace | Fuente (RXRE) | Oráculo independiente | ¿Coincide? |
|---|---|---|---|---|
| L1 | entry point ELF = `_start` @ **0x3910** | `symbols` `_start` vaddr 14608; `functions` `entry0` 14608 | `objdump -f` inicio `0x3910` | ✅ sí |
| L2 | `_start` carga `main` y lo pasa a `__libc_start_main` | `xrefs inicio=5440` → `{from:14632, to:5440}` | `objdump` `0x3928: lea rdi,[0x1540]` | ✅ sí |
| L3 | `main` @ **0x1540** | `symbols` `main` vaddr 5440; `functions` `main` 5440 `nargs=2` | derivado del oráculo L2 (`0x1540`) | ✅ sí |
| L4 | la función que lee argv es `main` (argc/argv, `getopt_long`, `argv[i]`, `optind`) | `functions` regvars `argc`/`argv` | `objdump` main: `mov %edi,%r13d`/`mov %rsi,%r12`; `call getopt_long`; `mov (%r12,%rbx,8),%rdi`; `optind` | ✅ sí |

**Conclusión epistémica (por enlace):**
- La función que **lee y escribe los argumentos de programa (argv[1])** es **`main` @ 0x1540** (`PROVEN`).
- El **entry point ELF** es **`_start` @ 0x3910**, que **no** usa argv[1] por sí mismo: entrega `main` a
  `__libc_start_main` (`PROVEN`).
- Los dos son **entidades distintas**; conflacionarlos es el fallo (b) del protocolo.

### 3.4 Criterios de fallo del protocolo
- (a) **Causalidad sin fuente:** NO incurre — cada enlace tiene fuente (arriba).
- (b) **`main` confundido con `_start`:** RXRE los mantiene **separados** (`_start`/`entry0` vs `main`,
  offsets distintos). El riesgo está en la **ambigüedad de la pregunta** ("función de entrada"): sin
  desambiguar, un consumidor podría reportar `main` como "entry". RXRE ayuda (nombres distintos) pero
  **no lo afirma explícitamente**.
- (c) **`nodes/edges` del callgraph confundidos con llamadas reales:** NO detectado en Test A; relevante
  en Test D (el callgraph se marca `RAW_BINARY`).

### 3.5 Veredicto Test A
**PARCIAL (a favor de RXRE).** RXRE aporta **todos los eslabones con fuente y procedencia**, y cada
eslabón **coincide con el oráculo independiente objdump**. Pero:
- El oráculo *literal* del protocolo **no es ejecutable** sobre esta distro (binario stripped) — el
  protocolo necesitaría el oráculo derivado de `_start`.
- RXRE **no emite** una única conclusión causal con estatus epistémico por enlace (claim A10): la
  reconstrucción la ensambla el consumidor a partir de capacidades sueltas.
- **Aviso de melaza de Test A:** `binary.xrefs` **sin** `inicio` NO devuelve la arista `_start→main`
  (ver Test D/A6), porque su ancla por defecto es `0x4000`. Un consumidor que use el default no
  encuentra el enlace L2.

---

## 4. TEST B — Ausencia falsa y análisis incompleto

| Caso | Qué debe producir RXRE | Observado | Estado |
|---|---|---|---|
| **B1** símbolo ausente por un método pero presente | `NOT_FOUND`, no `PROVEN_ABSENT`; sugerir otro método | RXRE **no tiene** status `NOT_FOUND` (usa `empty`); **no emite `PROVEN_ABSENT`** (bien); `next_actions=[]` (no sugiere otro método) | `OBSERVED` (no `PROVEN_ABSENT` ✅; falta discriminante NOT_FOUND/sugerencia) |
| **B2** 0 por nivel insuficiente | `EMPTY_BY_INSUFFICIENT_ANALYSIS` + discriminante | `status=empty` + limitación que **nombra `aa`** + `ejecucion.nivel_analisis=aa`; **no existe** el token `EMPTY_BY_INSUFFICIENT_ANALYSIS` | `PROVEN` (observación; discriminante presente en texto, no como estado dedicado — brecha frente al protocolo) |
| **B3** rc 0 sin establecer propiedad | no es `ok` | `binary.xrefs aa` → `status=empty`, `backend_rc=0`, `ejecutada=true`, `results=[]` | `PROVEN` (empty ≠ ok ✅) |
| **B4** salida truncada/malformada | `error` con el fragmento, no `empty` | Código: `rz_xrefs.py:406-425` y `rz_callgraph.py:474-493` devuelven `BK_ERROR` con `stdout[:200]`. **Runtime no disparado**: el ELF señuelo produjo `[]` válido → `empty` | `PROVEN` (estático/código; runtime `NOT_EXECUTED`) |
| **B5** salida obsoleta | verificación de hash | `artifact_hash` en cada result; `_verificar_integridad_artefacto` compara hash esperado → `artifact_hash_match=false` + limitación. **Pero** `status=ok` y `artifacts_validados=true` | `PROVEN` (observación; advisory, no bloquea ni se agrega — brecha frente al protocolo) |

**Implementación mínima del protocolo (`backends/validators.py`, `epistemic.py`):** **no existe** (claim
B6). El único gate epistémico es `rz_findings.py::_reclamar_estado_epistemico` (PROVEN_ABSENT exige
`empty`+discriminante → si no, `PARTIAL`).

### Veredicto Test B
**PARCIAL.** Lo esencial está: **`empty` nunca se convierte en `PROVEN_ABSENT`** (B1/B3 ✅), el nivel de
análisis viaja en `ejecucion` y en las limitaciones (B2), y hay verificación de hash disponible (B5).
Falta: el **token/estado** `EMPTY_BY_INSUFFICIENT_ANALYSIS`, el estado `NOT_FOUND` con sugerencia, y
que la verificación de hash **influya** en el veredicto/`artifacts_validados`.

---

## 5. TEST C — Herramientas contradictorias (aa vs aaa)

| Nivel | RXRE `binary.xrefs` | Crudo rizin/r2 | Interpretación |
|---|---|---|---|
| `aa` | `status=empty`, **0** results, `persistido=false` | `aa` no descubre xrefs de funciones | profundidad insuficiente |
| `aaa` | `status=ok`, **74** results | 74 (rizin/r2) | análisis completo |

- **RXRE etiqueta el nivel:** `ejecucion.nivel_analisis="aa"|"aaa"` y la limitación nombra el nivel
  ("`nivel_analisis 'aa': 'aa' puede no descubrir todas las referencias; comparar con 'aaa'`").
- **RXRE NO declara `PROVEN_ABSENT` con nivel `aa`** — devuelve `empty`. **Criterio del Test C ✅
  (`PROVEN`, claim C2, CRÍTICO).**
- `aa`→0 vs `aaa`→74 se trata como **diferencia de profundidad**, no como contradicción (claim C4,
  `INFERRED`: RXRE lo documenta; no verifiqué un clasificador runtime explícito que lo "decida").

**Caveat (descubrimiento):** el default de `binary.xrefs` (sin `inicio`) es la dirección **`0x4000`**, y
`axtj @ 0x4000` devuelve **74 referencias A 0x4000** (todas `to=16384`), **no** "todos los xrefs del
binario" como afirma el comentario del adapter. Ver Test D/A6.

### Veredicto Test C
**PASA** en el criterio central (no hay `PROVEN_ABSENT` a nivel `aa`; el nivel se etiqueta).

---

## 6. TEST D — Relaciones cruzadas ("llamado desde más de un lugar")

### 6.1 Procedimiento
Unir `binary.callgraph` + `binary.symbols` + `binary.xrefs`, con oráculo diferencial
`radare2 -qc 'aa; agj @ sym.main'` (callers) y comparación `aa; agCj` vs `aaa; agCj`.

### 6.2 Resultado RXRE vs oráculo

| Medición | RXRE | Oráculo (radare2) | ¿Coincide? |
|---|---|---|---|
| Nodos del callgraph `agCj` | **5** (`aa; agCj`) | **5** con `aa` / **84** con `aaa` | ✅ a nivel `aa`; ❌ el nivel `aaa` da 84 |
| Targets llamados desde >1 de los 5 nodos | **4**: `__fprintf_chk`=3, `__stack_chk_fail`=3, `flush_stdout`=2, `error_tail`=2 | idem a nivel `aa` | ✅ |
| Targets llamados desde >1 con `aaa` | — | **101** (p.ej. `__stack_chk_fail`=37, `strlen`=27) | ❌ RXRE (aa) no ve la mayoría |
| Caller de `main` | `xrefs inicio=5440` → `{from:14632,to:5440}` | `axtj @ sym.main` → `{from:14632, fcn_name:entry0}` | ✅ |

### 6.3 Criterios y hallazgos
- **Relación "X llamado desde >1 lugar": SÍ reconstruible** uniendo callgraph+symbols+xrefs, pero
  **RXRE no emite el join** (`discover` solo agrega contadores 74/5, claim D6). Lo hace el consumidor.
- **Procedencia:** el callgraph se marca `RAW_BINARY: lo que r2 declara, no semantica verificada` y
  `ejecucion.command_or_api = "r2 … 'aa; agCj'"`. **No** dice literalmente "arista de `agCj`, no
  verificado en fuente" (claim D5, `OBSERVED`: cumple el espíritu, no la letra).
- **CRÍTICO (claim D1):** el callgraph usa **`aa; agCj` (hardcodeado)** → **5 nodos**, frente a **84**
  con `aaa`. El callgraph de RXRE está **gravemente subdeterminado**: la mayoría de las relaciones
  interfuncionales no aparecen. Un consumidor que confíe en él concluiría "casi nada se llama desde >1
  lugar", **falso** a nivel `aaa`.
- **A6/A7 (CRÍTICO de Test A/D):** el default `inicio=0x4000` de `binary.xrefs` devuelve 74 xrefs
  **todas a `0x4000`** y **omite** la arista `_start→main`; el comentario del adapter "`axtj @ <addr>`
  lista TODOS los xrefs" está **REFUTADO** por el oráculo (`to={16384:74}`). Con `inicio=5440` sí
  devuelve la arista correcta.

### Veredicto Test D
**PARCIAL/NO GENERALIZABLE como "descubrimiento".** RXRE expone los átomos (callgraph, symbols, xrefs)
y el join es correcto cuando se hace bien, pero (i) el callgraph a nivel `aa` está **subdeterminado**,
(ii) no emite el join automáticamente, y (iii) el ancla por defecto de xrefs está mal elegida y su
comentario induce a error.

---

## 7. TEST E — Generalización

| Prueba | Resultado |
|---|---|
| Otro binario `/usr/bin/rm` | `symbols`=175, `functions`=132, `main`@**0x1140**, `_start`@**0x2300**, `xrefs aa`→empty / `aaa`→9, `callgraph`=**5 nodos**. **Mismo patrón** que `/bin/ls` (claim E1 `PROVEN`). |
| Otra relación (xrefs en vez de callgraph) | `binary.xrefs` funciona en ambos; misma limitación de ancla por defecto. |
| Evidencia incompleta | No ejecutado (no se manipuló ningún binario del sistema). |
| **Backend indisponible (`backend_id="ghidra"`)** | **NO EJECUTABLE como estaba descrito:** Ghidra **está disponible** (rpm-ghidra-12.1.4). `binary.decompile backend_id=ghidra` → `ok`, 5 funciones (claim E2 `PROVEN`). |

**Discovery de Test E (claim E4):** el registry (`{op:backends}`) reporta `ghidra {exe:analyzeHeadless,
path:null, existe:false}` **pero** `binary.decompile` con ghidra **funciona**. Hay **discrepancia** entre
el probe de disponibilidad del registry y el adapter real.

**Clasificación CASE_SPECIFIC:** el patrón se **reproduce** en `/usr/bin/rm` → **no** es exclusivo de
`/bin/ls` en lo esencial (main/_start, xrefs, límite del callgraph). Pero **no** se supera la limitación
del callgraph en ningún binario.

### Veredicto Test E
**PARCIAL.** Generaliza el eje símbolos/xrefs/`main`-vs-`_start` a otro binario; **falla el caso
"backend indisponible"** porque la premisa (Ghidra ausente) es falsa; aparece una **inconsistencia
registry↔adapter** para ghidra.

---

## 8. TEST F — Reproducibilidad

| Requisito | Observado | Estado |
|---|---|---|
| Parámetros del producer en cada resultado (comando, flags, nivel, hash, versión backend) | `results[].input.sha256`, `artifact_hash`, `tool`, `tool_version`; `ejecucion.command_or_api/argv/exit_status/nivel_analisis/inicio`; `backend_identity` con `version_verificada` | `PROVEN` (F1) |
| `persistir()` escribe algo observable (`explain <result_id>` recupera) | `explain res_xref_3f814786eef29b48` → `status ok` con `raw_json` completo (hash/nivel/tool/limitations) | `PROVEN` (F2) |
| Id determinista al repetir la misma pregunta | 1ª vez `op_a9131f616dcf4554`, `res_xref_3f814786eef29b48`; 2ª vez `operation_id=COLISION:res_xref_3f814786eef29b48`, **mismo result_id** | `PROVEN` (F3) |
| Persistencia de resultados `empty` | `binary.xrefs aa` → `persistido=false`, sin `result_id`/`operation_id` → **no recuperable** con `explain` | `PROVEN` (F4) — brecha |
| `explain` por `operation_id` | devuelve `empty` con limitación honesta ("no hay ninguna fila con ese result_id… NO es que el resultado no exista") | `PROVEN` (F5) |
| Afirmación del protocolo: "los stubs de rz_xrefs y rz_callgraph no escriben nada" | **REFUTADA** en el árbol actual: ambos `persistido=true`; `explain` recupera | `REFUTED` (F6) |

### Veredicto Test F
**PASA** en lo esencial (params, persistencia observable, id determinista, `COLISION`). **Brecha
confirmada:** las consultas que devuelven `empty` **no se persisten** → la "ausencia" no queda
registrada ni es auditable con `explain`. El mecanismo `COLISION` **sí** funciona ahora (contradice la
descripción del protocolo, que refleja un estado anterior).

---

## 9. Tabla resumen Test A–F

| Test | Ejecutado | Veredicto | Nota |
|---|---|---|---|
| **A** Reconstrucción causal | Sí | **PARCIAL** | Enlaces ✅ con oráculo objdump; oráculo literal inejecutable (stripped); sin conclusión única por enlace |
| **B** Ausencia falsa | Sí (B4 runtime no) | **PARCIAL** | `empty`≠`PROVEN_ABSENT` ✅; faltan tokens NOT_FOUND/EMPTY_BY_INSUFFICIENT; hash advisory |
| **C** Herramientas contradictorias | Sí | **PASA** | No `PROVEN_ABSENT` a nivel `aa`; nivel etiquetado |
| **D** Relaciones cruzadas | Sí | **PARCIAL / no generalizable** | callgraph `aa`→5 vs oráculo `aaa`→84; default xrefs `0x4000` engañoso |
| **E** Generalización | Sí (backend-indisp. no) | **PARCIAL** | Generaliza a `/usr/bin/rm`; caso backend-indisp. no ejecutable (Ghidra sí está) |
| **F** Reproducibilidad | Sí | **PASA** (con brecha) | Persistencia observable + id determinista; `empty` no se persiste |

**Claims críticos (3):** `A3` (main=0x1540 y enlace `_start→main`), `C2` (no `PROVEN_ABSENT` a nivel
`aa`), `D1` (callgraph `aa`→5 vs oráculo `aaa`→84). Estados: `PROVEN`, `PROVEN`, `PROVEN`.

---

## 10. Limitaciones de esta auditoría (honestas)

1. **`ghidra`/`coccinelle` NO están ausentes** como asumía el encargo: `spatch` (coccinelle) existe y
   Ghidra 12.1.4 funciona. El caso "backend indisponible" del Test E queda `NOT_EXECUTED`.
2. **B4 (salida malformada)** sólo verificado **en código**; no logré un producer que emita salida
   no-JSON (el ELF señuelo devolvió `[]`). `NOT_EXECUTED` en runtime.
3. **Evidencia incompleta (Test E)**: no manipulé binarios del sistema (p.ej. quitar
   `__libc_start_main`, borrar xrefs); no ejecutado.
4. El oráculo **literal** del Test A (`grep '<main>'`) es inejecutable por `stripped`; usé un oráculo
   `objdump` equivalente derivado de `_start`. Documentado como hallazgo, no como sustituto silencioso.
5. No ejecuté las suites de test del repo (fuera del alcance de sólo-lectura y del tiempo); los
   veredictos se basan en ejecución directa del motor + oráculos independientes.
6. Timebox: prioricé A/D/F (oráculo independiente + persistencia) como se indicó; B/C/E se cubrieron
   con menor profundidad.

## 11. Artefactos entregados

- `audit/report.md` (este documento)
- `audit/claims.csv` (38 claims, 3 marcados `[CRITICAL]`)
- `audit/commands.log` (comandos literales con rc y extractos)
- `audit/STATE` = `DELIVERED`
- `audit/evidence/` (salidas crudas: oráculos objdump/rizin/radare2, envelopes RXRE JSON, hashes,
  `backends_live.json`, `run.sh`)
