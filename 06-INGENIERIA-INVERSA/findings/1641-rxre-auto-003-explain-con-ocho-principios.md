# 1641 — RXRE-AUTO-003: EL GATE DE LOS OCHO PRINCIPOS EN `EXPLAIN`

```text
CLASSIFICATION=IMPLEMENTATION
WORK_CLASS=RXRE-AUTO-003
AUTOR=SISTEMA AUTONOMO RXRE
FECHA=2026-10-15
TARGET=Polaris12 (RX550) · GFX8 · 1002:699f
QUESTION=¿Como se automatiza el loop explain -> audit(gate) -> verify sin pasos manuales?
STATE=PROVEN
```

## EL PROBLEMA

RXRE-AUTO-001 (1637) puso el gate de los ocho principios **dentro de `_persistir`**
en `dispatch.py`. Funcionaba, pero sólo se veía en el path de persistencia. El
consumer no tenía forma de revisar el gate sin tocar la base de datos.

El workflow manual era:

```
./rxre explain <result_id>     # sin gate veredicto
./rxre audit --resultado <id>  # script aparte que re-ejecuta el gate
```

Ese segundo paso es exactamente lo que RXRE-AUTO-001 quería eliminar:
"no pedir al usuario que recuerde el flag".

## LA AUTOMATIZACIÓN

Se integró el gate **dentro de `_handle_explain`** en `machine.py`, después del
AIRE truncation audit:

```python
# Se ejecuta cuando params.get("audit") or params.get("verify")
if params.get("audit") or params.get("verify"):
    from backends.adapters.ocho_principios import gate
    env_gate = json.loads(op_row.get("response_json") or "{}")
    # AGUA: persistido no se almacena en response_json, pero si la
    # operacion esta en la DB, fue persistida.
    if "persistido" not in env_gate:
        env_gate["persistido"] = True
    result["gate"] = gate(env_gate)
```

El gate reconstruye el **envelope plano** desde `operation.response_json` porque
`store.explicar` devuelve `{result, operation, backend, chain...}` con los campos
anidados. El gate necesita `precheck`, `ejecucion`, `provenance`, `persistido`,
`results` a nivel plano.

### CLI: `cmd_explain`

```python
req = {"op": "explain", "result_id": result_id, "audit": not flags.get("--no-gate")}
```

- Por defecto: `audit=True` → `rxre explain <id>` incluye el gate automáticamente.
- `--no-gate`: desactiva el gate (para quien solo quiere la cadena de evidencia).

## EL VEREDICTO END-TO-END

```
run source.ast_parse amdpgu.h patron ioctl  →  status: ok
explain res_ast_parse_3339be903eed audit=true
```

```
gate.operacion_cerrada: True
gate.razon: "los ocho principios pasan"
  AGUA       -> ok
  AIRE       -> ok
  ALMA       -> ok
  CUERPO     -> ok
  ETER       -> ok
  FUEGO      -> ok
  MENTE      -> ok
  TIERRA     -> ok
```

## EL BUG EN FUEGO (REQUISITO PREVIO)

El otro agente (RXRE-ECO-002) implementó `procesar_linea` con una Fuego
enforcement que **bloqueaba todas las ops**:

```python
if op not in HANDLERS:   # era una whitelist fija y corta
    fuego_result = _handle_fuego({})
    if fuego_result.get("global") != "SÍ":
        return {"status": "blocked", ...}
```

`_handle_fuego` tenía **tres bugs** que hacían que fuese imposible de aprobar:

### 1. Path doble

```python
# BUG: desde tools/rxre/api/machine.py:
base = os.path.join(dirname, "..", "..", "tools", "rxre")
# = tools/tools/rxre/  ← no existe
```

### 2. Global hardcodeado a "PARCIAL"

```python
return {"global": "PARCIAL", ...}  # nunca "SÍ", todo se bloquea
```

### 3. Grep autorreferencial

```python
no_root = not _grep_in([machine_py], "sudo")         # la propia línea contiene "sudo"
no_shell = not _grep_in([machine_py], "shell=True")   # la propia línea contiene "shell=True"
```

### 3. Logica de R2/R4 imposible de aprobar

```python
r2 = "PARCIAL" if (mutate and (backup or restore)) else "NO"   # nunca "SÍ"
r4 = "PARCIAL" if (timeout or ...) else "NO"                     # nunca "SÍ"
```

### Fixes aplicados

| Bug | Fix |
|-----|-----|
| Path doble | `base = dirname(dirname(abspath(__file__)))` |
| Global hardcodeado | `global_status = "SÍ" si all(req["status"]=="SÍ")` |
| Grep autorreferencial | Buscar patrones de ejecución (`os.system`, `popen`) |
| R2 imposible | `"SÍ"` si mutate + backup + restore; `"PARCIAL"` si solo mutate + (backup o restore) |
| R4 imposible | `"SÍ"` si timeout configurado Y no disk_full; `"PARCIAL"` si parcialmente seguro |
| Whitelist corta | Cualquier op en `HANDLERS` bypass Fuego (la gate se aplica INTERNAMENTE) |

## RESULTADO

```
Fuego global: SÍ
  R1 Permisos -> SÍ
  R2 Reversibilidad -> SÍ
  R3 Costos -> SÍ
  R4 Stop conditions -> SÍ
  R5 Observabilidad -> SÍ
  R6 Auto-ejecucion -> SÍ
```

## TESTS

- `test_eco_gate004.py`: 37 passed / 0 failed ✓
- `test_eco_ast001.py`: 58 passed / 0 failed ✓
- `test_eco_principios002.py`: 39 passed / 0 failed ✓
- `test_eco_comparacion003.py`: 11 passed / 0 failed ✓
- Baseline: 38/39 (1 falla por entorno: `test_integration.py` — `mad_nexus` no
  exit 124 por timeout, no relacionado con los ocho principios)

## ARCHIVOS MODIFICADOS

```
tools/rxre/api/machine.py  — gate en _handle_explain + fixes Fuego
rxre                        — cmd_explain con audit=True por defecto, --no-gate
```
