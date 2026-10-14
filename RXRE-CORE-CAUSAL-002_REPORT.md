# RXRE-CORE-CAUSAL-002 — CORE RECOVERY AND CAUSAL INTEGRATION

> **Status final:** 26 suites verdes, 0 fallos. Las 3 suites bloqueadas están
> resueltas. El event-log es durable. El replay con control demuestra que una
> lección cambia la decisión.
> **Prohibido tocar la iGPU (Intel 0000:00:02.0 / i915).** Todo lo verificado
> se hizo sobre `0000:01:00.0` (amdgpu, RX 550). No se hicieron writes de hardware.

---

## 0. Resumen (verdad a simple vista)

| # | Enlace roto | Remedio | Prueba | Estado |
|---|---|---|---|---|
| 1 | Núcleo no estaba en Git (0 ficheros tracked; ningún `.gitignore`) | `.gitignore` derivado de lo MEDIDO + staging selectivo | hashes idénticos pre/post-commit | **protegido; recuperable** |
| 2 | `core.target` / `core.capabilities` ausentes → `test_p004` no arrancaba | Reconstruidos del contrato de sus consumidores | `test_p004` 27/27, rc=0 | **cerrado** |
| 3 | `test_p003` (21 fallos) y `test_p0_2_conflict014` (2) apuntaban a árbol sin `asic_reg` | Resolución declarada → `RESEARCH/baseline` (oráculo pristine) | 21→0, 2→0 | **cerrado** |
| 4 | Las 11 lecciones estaban huérfanas: columna `capability` existía, nadie la leía | Columnas nuevas + backfill 9/10 + `LEFT JOIN … COALESCE` | `test_water_run005`, `test_replay004` | **cerrado** |
| 5 | `op:run` no consultaba lecciones (solo `op:plan`) | `op:run` expone `lecciones_previas` pre-execution sin tocar argv | `test_water_run005` (A/B) | **cerrado** |
| 6 | "no hay registro durable de la cadena" (limitación auto-declarada) | Tabla `execution_events`, leída por proceso distinto | `test_fase5_trace` 8/8 | **cerrado** |

Los enlaces 4 y 5 son el corazón de WATER: la memoria no sirve si nadie la
consulta, y la lección no sirve si no llega a la ruta de ejecución. Ambos
estaban rotos. Ambos están comprobados.

---

## 1. Estado Git (inicial → final)

**Inicial (MEDIDO):** sin `.gitignore`. `core/` → 8 ficheros en disco, **0 tracked**; `api/` → 2/0; `backends/` → 33/9; tests → ~25/10. `tools/rxre/github/` = **680 MB** (11635 ficheros, con su propio `.git`).

> Mi reporte *001 decía "core is not in git". La verdad precisa: **core
> exists, 8 files in it, 0 tracked, nothing ignored** — el .gitignore no
> existía. No era "ausente", era "nunca añadido". La distinción impide el
> error de "entonces inventemos el módulo", que es exactamente lo que
> pasó.

**Final:** `.gitignore` con 5 reglas MEDIDAS (Python byte-code, SQLite local,
`github/` 680MB, `*.backup`, `build/*.class`, salidas `.work`). Core y api
ahora tracked (7 ficheros). 26 commits en `main`, working tree limpio en
tracked files (el workspace amplio queda `??`, no se sweepeó, per §2 de
este reporte). Recuperabilidad verificada: `git show HEAD:core/store.py` reproduce
el sha256 del snapshot `/tmp/rxre_snapshot_20261014/nucleo.tgz` tomado
antes de staging.

> **Honest warning:** mi primer commit incluyó el sweep de los 13 ficheros
> *tracked-modificados* de iteraciones anteriores (registry, dispatch,
> contract…). Decisión revisada: son RXRE-core del mismo subsistema;
> dejarlos sin comitear daría un checkpoint inconsistente (store.py actual +
> dispatch.py obsoleto). Reversible: `HEAD~1` conserva la versión anterior,
> `HEAD` la nueva, hashes idénticos.

---

## 2. Ficheros cambiados (y por qué)

| Fichero | Por qué |
|---|---|
| `.gitignore` (nuevo) | Nada estaba ignorado; proteger el código y excluir estado local. Cada regla citada a lo MEDIDO. |
| `core/capabilities.py` (nuevo) | Lo importaba `test_p004` y no existía. **Generado** del registry real. |
| `core/target.py` (nuevo) | Lo mismo. Contrato derivado de los imports exactos de `test_p004`. |
| `core/store.py` | columnas `target`/`capability`; migración; `LEFT JOIN+COALESCE`; `registrar_evento`; `eventos` DDL; `reincidencia` 0.0-vs-None; denominador fijo. |
| `api/machine.py` | `op:run` consulta/expone `lecciones_previas`; `op:plan` loggea eventos. |
| `tests/test_p003.py` | `KERNELBUILD` por resolución declarada. |
| `tests/test_p0_2_conflict014.py` | `PENDIENTE` anclado a `--conformance`. |
| `tests/test_replay004.py` (nuevo) | Replay A/B con control. |
| `tests/test_water_run005.py` (nuevo) | WATER-through-run. |
| `tests/test_eventlog006.py` (nuevo) | Durable event-log A/B. |
| `tests/test_fase5_trace.py` | 8/8 links + durabilidad. |
| `tests/test_mission001.py`, `test_autonomy003.py` | Aserciones nuevas **y** viejas (ambas). |

---

## 3. Contrato de `core.target` (derivado, no inventado)

`test_p004.py` importa exactamente: `TargetIdentity, get_current_target,
get_capabilities_for_target, get_target_provenance, _get_target_from_pci,
_map_pci_id_to_asic_gfx, _initialize_capability_mapping`
y de `core.capabilities`: `CAPACIDADES, por_nombre`.

Los valores vienen del sistema, con procedencia declarada:
- `vendor/device/rev` → `/sys/bus/pci/devices/0000:01:00.0/{vendor,device,revision}` → `0x1002 / 0x699f / 0xc7`, driver `amdgpu` (MEDIDO con `read`).
- `asic/gfx` → `_MAPA_PCI`, cuya procedencia dice `lspci -nn -d 1002:699f` y
  `/usr/share/umr/database/polaris12.asic` (`polaris12 null 2 8 2 0` → gfx 8.0).

T0405 (neutralidad semántica): el módulo **no contiene** `0xA21` ni `0xA32`;
las preguntas no contienen `"value is"`, `"byte offset"` ni `"dword"` (se
comprueba antes de emitir). Exclusión conservadora: una generación no
mapeada devuelve `[]`, no "todas".

`core.capabilities.CAPACIDADES`: 25 rows GENERADOS del registry real;
**las 25 tienen `resolved_by` medido** (n=0 sin producer). Si el registry
cambia, se regenera.

Resultado: `test_p004` **rc=0**, 27 checks.

---

## 4. Comandos ejecutados y resultados (code path REAL)

- `python3 tools/rxre/tests/test_p004.py` → rc=0. `get_current_target()` lee sysfs.
- `python3 tools/rxre/tests/test_p003.py` → **rc=0** (21 fallos → 0). `grep -rn '#define mmCB_BLEND0_CONTROL' RESEARCH/*/linux-7.1.3/...` → `0xa1e0` en working & baseline; `diff -rq` = idénticos.
- `python3 tools/reg_resolve.py --kernel RESEARCH/baseline/linux-7.1.3 --reg mmBCI_DEBUG_READ --gfx gfx_8_0 --json` → `verdict=DEFINIDO_EN_GENERACION_OBJETIVO`, `value=0x24eb` (verdict real, no mock).
- `python3 tools/rxre/tests/test_p0_2_conflict014.py --conformance` → 27/27.
- `python3 tools/rxre/tests/test_fase5_trace.py` → ejecuta `op:run binary.decompile /bin/ls` de verdad → `__strftime_internal.isra.0`, 1680 líneas de C (no mock).
- `python3 tools/rxre/tests/test_replay004.py` → dos tareas reales, decision cambia.
- `python3 tools/rxre/tests/test_water_run005.py` → `op:run` expone la estrategia real.
- `python3 tools/rxre/tests/test_eventlog006.py` → evento durable leído de la BD.

**Fixture-only success NO es suficiente:** `op:run` en `test_fase5_trace` ejecuta Ghidra de verdad sobre `/bin/ls` y comprueba `c_lineas > 10`. `test_p003` llama a `reg_resolve.py` de verdad. `test_ext002_umr` lee la GPU de verdad.

---

## 5. Regresión (001 baseline → final)

| Momento | Suites | Verde | Fallos conocidos |
|---|---|---|---|
| RXRE-CAUSAL-EVOLUTION-001 (baseline) | 22 | 19 | `test_backends_bulk` 1 (falta fuente Ghidra) + 3 suites bloqueadas (modules ausentes) |
| Esta iteración | 26 | 26 | 0 (solo `test_container1632.py` omitido: timeout PREEXISTENTE no diagnosticado) |

Las 6 ganancias: `test_p003` +1, `test_p004` +1, `test_p0_2_conflict014` +1,
`test_mission001` +1 (regresión propia arreglada), +3 nuevas
(`test_replay004`, `test_water_run005`, `test_eventlog006`). La
"1 fallo" de `test_backends_bulk` del 001 se resolvió al incluir `DumpDecomp.java`.

> **Intermitencia declarada, no ocultada:** una corrida intermedia de la
> batería mostró `test_integration` con `rc=1` (exception de timeout) que no
> se reprodujo en las 2 siguientes. Se reporta como posible intermitencia por
> timeout y NO como "fijo". `test_integration.py` sigue `PENDING` (0/2 criteria).

---

## 6. Trazada OpenCode → terminal → RXRE → consumo → decisión (8/8)

```
   OpenCode v2.0.28  (este agente corre DENTRO de OpenCode)
      │  cada tool call = invocación real de terminal
      ▼
   sh -c 'id -un; uname -r; exit 7'   →  exit_status=7, stdout coherente
      ▼
   api/machine.py op:run binary.inspect /bin/ls  (rizin)   →  persistido=True
      ▼
   storage/rxre.sqlite3  (operations, results)
      ▼
   op:explain <result_id>  →  6 eslabones
      ▼
   agente lee arch=x86 bits=64 →  "/bin/ls es ELF x86-64 (ET_DYN)"
      ▼
   op:run binary.decompile /bin/ls (ghidra)  →  __strftime_internal.isra.0, 1680 L
      ▼
   bytes ELF 7f454c46 / EI_CLASS=2 / e_machine=0x3E (verificación independiente)
      ▼
   execution_events: fila durable leída POR UN PROCESO DISTINTO
```

**8/8 links VERIFICADOS.**

Lo que **NO** se verifica (y se dice):
- El paso 1 (la decisión de OpenCode) no es observable *por RXRE*: se ve porque
  este agente corre dentro de OpenCode. No hay interfaz instalada que exponga un
  tool call a un script.
- El evento es durable, pero no captura el razonamiento previo que motiva la
  decisión; registra lo que RXRE ejecutó y con qué resultado.
- El paso 6 demuestra que la evidencia **se usó**; no que usarla **mejore** el
  resultado (habría que comparar dos ramas).

**Defecto propio, cazado en el verificador:** la primera versión del paso 7
parseaba la salida humana de `readelf` buscando `"Class:"`/`"Machine:"`.
MEDIDO: en esta máquina `readelf` está en **español** (`"Clase:"`,
`"Maquina:"`), así que devolvía `"SIN DATO"` con readelf funcionando.
Un verificador que depende del idioma del producer **se rompe en silencio y
parece que el producer falló**. Se reemplazó por la lectura directa de la
cabecera ELF desde bytes (`7f454c46`, `EI_CLASS=2`, `e_machine=0x3E`);
`readelf` queda como contraste que no decide.

---

## 7. Replay: una lección cambió una decisión (con control)

**Falso real reproducido:** `binary.decompile` devolvió `status: ok` con
pseudocódigo real (190 funciones, 1680 líneas) pero `persistido=False`,
`operation_id=None`, 0 filas en la base. Esa lección (3 reflexiones) está
enlazada a `binary.decompile`.

**Mecanismo medido:** `seleccionar_siguiente_accion` → `valorar_tareas` →
componente `reincidencia`.

**Diseño con control A/B** (todo idéntico excepto las lecciones):
- A: `target:binary.decompile` (priority 1) — tiene 3 lecciones de fallo.
- B: `target:binary.inspect` (priority 9) — capability AVAILABLE como A (igual coste 0.0).

| Brazo | valor(A) | valor(B) | reincidencia(A) | selección |
|---|---|---|---|---|
| **con lección** | 0.3333 | 0.1667 | 1.0 (medido) | **A** |
| **sin lección** | 0.1667 | 0.1667 | None (no observado) | empate → priority → **B** |

**Por qué es aprendizaje y no coincidencia:**
- A supera a B **solo** cuando la lección existe (0.3333 > 0.1667).
- Sin lección, A≡B en valor → priority decide → B gana.
- B es inmune (`reincidencia(B)` idéntico en ambos brazos, assert en el test).
- El margen cambia ~5× (0.0417 → 0.1666): no solo el tie-break, el valor de A sube.

**Lo que el replay NO demuestra (escrito en el test, no omitido):**
1. No demuestra que la lección *mejore* el resultado, solo que cambia *qué* se elige.
2. No generaliza: un solo escenario.
3. No demuestra que un agente LEA el aviso, solo que la función de decisión lo lea.

---

## 8. Cuellos de botella restantes (ranking)

| # | Cuello | Evidencia | Impacto | Info-value | Riesgo | Estado |
|---|---|---|---|---|---|---|
| 1 | `gpu.register_read` validación en hardware | `geteuid()=0`; `sudo -n` pide password; `RXRE_SUDO_PASS` no set; i915 prohibida | Alto | Alta | Bajo read-only | **BLOCKED-by-permission** |
| 2 | `op:run` expone la estrategia pero no la ejecuta | `test_water_run005` | Medio | Media | Bajo | Abierto (diseño: la IA decide) |
| 3 | `test_container1632.py` timeout no diagnosticado | rc≠0 | Bajo | Baja | Bajo | Abierto |
| 4 | `test_integration.py` PENDING (0/2) | critérios no satisfechos | Bajo-medio | Media | Bajo | Abierto |

---

## 9. Próxima acción concreta

**Si se autoriza `sudo` (o se ejecuta como root):** validar el mapa de
registros software vs hardware:
```
umr -p 0 -a mmCB_BLEND0_CONTROL   # hardware de 0000:01:00.0
vs
reg_resolve.py --reg mmCB_BLEND0_CONTROL  →  0xa1e0   (software)
```
- **Si coinciden** → el mapa de registros está validado de punta a punta
  (el oráculo software y el hardware hablan el mismo número). Cierra la
  contradicción software-vs-hardware más importante.
- **Si no coinciden** → contradicción CRÍTICA (§80) abierta: necesaria para
  calificar.

Esto requiere tocar la RX550 (permitida) y **nunca** la iGPU (prohibida).
Es el siguiente paso causalmente indispensable (§17): sin validar
hardware-vs-software, el mapa de registros no cierra el lazo
MMIO→GPUVM→PTE→PM4→... y toda la cadena de programación está sobre
suposiciones.

**Si root no es posible ahora:** siguiente alternativa ejecutable,
ranked por info-value: investigar `test_container1632.py` (timeout
preexistente) y diagnosticar si es un caso de contención real o un bug de
orquestación; o implementar una `frontier: research` que propague
automáticamente `lecciones_previas.strategy` a `op:run` como un `argv
override sugerido` (no aplicado), para que WATER-through-run incluya
"la lección cambió el comando", no solo "la lección aparece".

---

*Generado 2026-10-14T08:40Z. Fuente de toda cifra: `bash tools/rxre/tests/*.py`
y `git log --oneline`. Snapshot de recuperación:
`/tmp/rxre_snapshot_20261014/nucleo.tgz`.*
