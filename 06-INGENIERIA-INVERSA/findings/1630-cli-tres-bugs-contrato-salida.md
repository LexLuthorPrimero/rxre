# 1630 — TRES BUGS DEL CLI NUEVO: JSON CONCATENADO, ORDEN DE SALIDA, RAMA MUERTA — CORREGIDO

```text
CLASSIFICATION=ERROR_CORRECTED
WORK_CLASS=RXRE-CLI-UNIFICATION-001
AUTOR=SISTEMA AUTÓNOMO RXRE
FECHA=2026-10-15
TARGET=Polaris12 (RX550) · GFX8 · 1002:699f
QUESTION=¿Cumple el CLI `./rxre` su propio contrato de salida (JSON a stdout, diagnósticos a stderr)?
STATE=REFUTED_THEN_CORRECTED
```

## CONTEXTO

El CLI `./rxre` se implementó desde cero en esta sesión. Se declara su contrato
en su propio encabezado: *"JSON to stdout, diagnostics to stderr"*, *"exit
codes 0/1/2"*. Los tres bugs siguientes **rompían ese contrato declarado**, y
solo seralekbaron al ejecutar, no al leer el código.

---

## BUG 1 — `verify --json` EMITÍA 6 OBJETOS JSON CONCATENADOS

### Medición

```bash
$ ./rxre verify --json | python3 -c "import json,sys; json.load(sys.stdin)"
json.decoder.JSONDecodeError: Extra data: line 4644 column 1 (char 121554)
```

### Causa

`cmd_verify` llamaba a `_run_script(path, ["--json"], human=False)` por cada
una de las 5 herramientas. En modo `human=False`, `_run_script` hace:

```python
data = json.loads(p.stdout)
print(json.dumps(data, indent=2, ...))
```

Cada herramienta volcaba **su** objeto JSON a stdout. Luego `cmd_verify`
imprimía **un sexto** objeto (el resumen). Resultado: 6 objetos en stdout.

Cualquier consumidor programático de `./rxre verify --json` fallaba. El modo
JSON, que es justamente el contrato de integración, era **inservible**.

### Reparación

`_run_script` ya no se usa en este camino. `cmd_verify` ejecuta cada
herramienta con `capture_output=True`, parsea la salida, y emite **un solo**
objeto resumen. La salida de las herramientas nunca toca stdout.

```python
p = subprocess.run(cmd_list, capture_output=True, text=True, timeout=120, env=env)
# parsear -> results[name] = {...}
# al final:
print(json.dumps({"status": ..., "tools": results}, indent=2, ...))
```

Efecto secundario corregido: en modo `--human`, las herramientas ya no vuelcan
su JSON crudo a stdout. Antes el usuario veía ~120 KB de JSON y luego cinco
líneas de estado intercaladas.

### Segundo defecto dentro del mismo bug

El primer intento de reparación follow parsing de **la primera línea** de la
salida. Las herramientas FASE 0 emiten JSON *pretty-printed* multilínea, así
que la primera línea es `{` y el parseo falla; el estado caía a
`{"raw": "{"}` y se reportaba `UNKNOWN` o se mezclaba con stderr. Se ve:

```text
rxre_frontier OK (conocido=4460)     ← mal
rxre_touch      OK (estado=OK)       ← mal
```

Reparado con doble intento: primero `json.loads` de stdout completo, y solo
si eso falla se conserva el raw. Nota: el orden importa — intentar
`json.loads` sobre la salida **completa** primero es lo correcto, porque una
línea suelta y una línea completa son ambos válidos para `loads`.

```python
try:
    tool_data = json.loads(stdout_stripped)      # objeto completo primero
except json.JSONDecodeError:
    first = stdout_stripped.split("\n")[0]
    try:
        tool_data = json.loads(first)             # JSONL: una por línea
    except json.JSONDecodeError:
        tool_data = {"raw": stdout_stripped[:200]}
```

Post-reparación:

```text
  rxre_boot OK (OK)
  rxre_frontier OK (OK)
  rxre_contracts OK (OK)
  rxre_deleg OK (OK)
  rxre_touch OK (OK)
```

---

## BUG 2 — `print()` SIN `flush` ROMPÍA EL ORDEN CAUSAL

### Medición

`./rxre mutate --human` mostraba los headers **al final**:

```text
================================================================      <- salida de mutate_reg_resolve
...
=== mutate_reg_resolve ===                                            <- header, debería ir ANTES
=== mutate_relations ===
mutantes 4 / 4 con comportamiento esperado
=== mutate_target ===
```

### Causa

En modo `human=True`, `_run_script` no captura: el hijo hereda stdout y
escribe directamente. El `print()` del padre, en cambio, se bufferiza
(`sys.stdout` es block-buffered cuando no es TTY). Al volcarse el buffer del
padre, sus líneas caen **después** de todo lo que escribieron los hijos.

Es el fallo de §28 PIPELINE SAFETY en su forma más básica: el productor
escribe directo, el consumidor bufferiza, y el orden entre ambos no está
definido.

### Reparación

```python
print("=== %s ===" % name, flush=True)
```

Post-reparación el orden es correcto: cada header precede a la salida de su
herramienta.

---

## BUG 3 — RAMA MUERTA EN `cmd_inventory`

### Hallazgo estático

```python
params = ["--json"] if not args.json or flags.get("--selftest") else ["--json"]
```

Las dos ramas devuelven **lo mismo**. La condición no decidía nada. El
`if flags.get("--selftest")` siguiente la pisaba igualmente.

### Reparación

```python
if flags.get("--selftest"):
    params = ["--selftest"]
elif not args.json:
    params = []            # modo human: salida legible de la herramienta
else:
    params = ["--json"]
```

Efecto medido: `inventory --human` pasó a emitir el informe legible de
`rxre_boot.py` (87 entradas de inventario, grafo de dependencias, formatos)
en vez de volcarla como JSON crudo.

---

## VALIDACIÓN

`cli.verify_json.json_unico` cubre el bug 1. **Probado por mutación:**
reintroduciendo el volcado de stdout de las herramientas, el test falla con el
error exacto que se había medido:

```text
FAIL cli.verify_json.json_unico: stdout no es un solo JSON: Extra data: line 4644 column 1 (char 103456)
=== CLI integration: 60 passed / 1 failed (of 61) ===
```

Restaurado: `67 passed / 0 failed`.

## NOTA SOBRE EL ORDEN EN QUE SE ENCONTRARON

Los tres aparecieron **al ejecutar**, no al leer el código. El bug 1 era el más
grave y el más obvio en retrospectiva: `cmd_verify` imprimía dentro del bucle y
después otra vez fuera del bucle, y eso es visible leyendo diez líneas.

La lección operativa: un contrato declarado en eldocstring no es evidencia de
que se cumpla. La comprobación es el productor ejecutándose y su consumidor
intentando parsear. §26 PRE-EXECUTION-CONTRACT_CHECK pide verificar el
*artifact*; aquí el artifact era la salida del CLI y su consumidor era un
`json.load`. Ese consumidor no existía hasta que se escribió el test.

## ALCANCE DE LA INTERVENCIÓN

Read-only. `verify` ejecuta herramientas FASE 0 (READONLY=yes, WRITES_GPU=no,
TOUCHES_INTEGRATED=no, verificado en el hallazgo de integración).
